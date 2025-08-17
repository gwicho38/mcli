import asyncio
import base64
import json
import logging
import os
import shutil
import signal
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# CLI Commands
import click
import numpy as np
import psutil
import requests

# Model loading and inference
import torch
import transformers
import uvicorn

# FastAPI for REST API
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer

# Import existing utilities
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

from .lightweight_embedder import LightweightEmbedder

# Import lightweight model server
from .lightweight_model_server import LIGHTWEIGHT_MODELS, LightweightModelServer
from .pdf_processor import PDFProcessor

logger = get_logger(__name__)

# Configuration
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "models_dir": "./models",
    "temp_dir": "./temp",
    "max_concurrent_requests": 4,
    "request_timeout": 300,
    "model_cache_size": 2,
    "enable_cors": True,
    "cors_origins": ["*"],
    "log_level": "INFO",
}


@dataclass
class ModelInfo:
    """Represents a loaded model"""

    id: str
    name: str
    model_type: (
        str  # 'text-generation', 'text-classification', 'translation', 'image-generation', etc.
    )
    model_path: str
    tokenizer_path: Optional[str] = None
    device: str = "auto"  # 'cpu', 'cuda', 'auto'
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    is_loaded: bool = False
    memory_usage_mb: float = 0.0
    parameters_count: int = 0
    created_at: datetime = datetime.now()  # Do not assign None; let __post_init__ handle default

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class ModelDatabase:
    """Manages model metadata storage"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".local" / "mcli" / "model_service" / "models.db")
        else:
            db_path = str(db_path)
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Models table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                model_type TEXT NOT NULL,
                model_path TEXT NOT NULL,
                tokenizer_path TEXT,
                device TEXT DEFAULT 'auto',
                max_length INTEGER DEFAULT 512,
                temperature REAL DEFAULT 0.7,
                top_p REAL DEFAULT 0.9,
                top_k INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_loaded BOOLEAN DEFAULT 0,
                memory_usage_mb REAL DEFAULT 0.0,
                parameters_count INTEGER DEFAULT 0
            )
        """
        )

        # Inference history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inferences (
                id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                request_type TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                execution_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (model_id) REFERENCES models (id)
            )
        """
        )

        conn.commit()
        conn.close()

    def add_model(self, model_info: ModelInfo) -> str:
        """Add a new model to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO models 
                (id, name, model_type, model_path, tokenizer_path, device,
                 max_length, temperature, top_p, top_k, created_at, is_loaded,
                 memory_usage_mb, parameters_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    model_info.id,
                    model_info.name,
                    model_info.model_type,
                    model_info.model_path,
                    model_info.tokenizer_path,
                    model_info.device,
                    model_info.max_length,
                    model_info.temperature,
                    model_info.top_p,
                    model_info.top_k,
                    model_info.created_at.isoformat(),
                    model_info.is_loaded,
                    model_info.memory_usage_mb,
                    model_info.parameters_count,
                ),
            )

            conn.commit()
            return model_info.id

        except Exception as e:
            logger.error(f"Error adding model: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, name, model_type, model_path, tokenizer_path, device,
                       max_length, temperature, top_p, top_k, created_at, is_loaded,
                       memory_usage_mb, parameters_count
                FROM models WHERE id = ?
            """,
                (model_id,),
            )

            row = cursor.fetchone()
            if row:
                return self._row_to_model_info(row)
            return None

        finally:
            conn.close()

    def get_all_models(self) -> List[ModelInfo]:
        """Get all models"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, name, model_type, model_path, tokenizer_path, device,
                       max_length, temperature, top_p, top_k, created_at, is_loaded,
                       memory_usage_mb, parameters_count
                FROM models ORDER BY name
            """
            )

            return [self._row_to_model_info(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    def update_model(self, model_info: ModelInfo) -> bool:
        """Update model information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE models 
                SET name = ?, model_type = ?, model_path = ?, tokenizer_path = ?,
                    device = ?, max_length = ?, temperature = ?, top_p = ?, top_k = ?,
                    is_loaded = ?, memory_usage_mb = ?, parameters_count = ?
                WHERE id = ?
            """,
                (
                    model_info.name,
                    model_info.model_type,
                    model_info.model_path,
                    model_info.tokenizer_path,
                    model_info.device,
                    model_info.max_length,
                    model_info.temperature,
                    model_info.top_p,
                    model_info.top_k,
                    model_info.is_loaded,
                    model_info.memory_usage_mb,
                    model_info.parameters_count,
                    model_info.id,
                ),
            )

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating model: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_model(self, model_id: str) -> bool:
        """Delete a model"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def record_inference(
        self,
        model_id: str,
        request_type: str,
        input_data: str = str(),
        output_data: str = str(),
        execution_time_ms: int = int(),
        error_message: str = str(),
    ):
        """Record inference request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            inference_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO inferences 
                (id, model_id, request_type, input_data, output_data, 
                 execution_time_ms, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    inference_id,
                    model_id,
                    request_type,
                    input_data,
                    output_data,
                    execution_time_ms,
                    error_message,
                ),
            )

            conn.commit()

        except Exception as e:
            logger.error(f"Error recording inference: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _row_to_model_info(self, row) -> ModelInfo:
        """Convert database row to ModelInfo object"""
        return ModelInfo(
            id=row[0],
            name=row[1],
            model_type=row[2],
            model_path=row[3],
            tokenizer_path=row[4],
            device=row[5],
            max_length=row[6],
            temperature=row[7],
            top_p=row[8],
            top_k=row[9],
            created_at=datetime.fromisoformat(row[10]),
            is_loaded=bool(row[11]),
            memory_usage_mb=row[12],
            parameters_count=row[13],
        )


class ModelManager:
    """Manages model loading, caching, and inference"""

    def __init__(self, models_dir: str = "./models", max_cache_size: int = 2):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = max_cache_size
        self.loaded_models: Dict[str, Any] = {}
        self.model_lock = threading.Lock()
        self.db = ModelDatabase()

        # Device detection
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

    def load_model(self, model_info: ModelInfo) -> bool:
        """Load a model into memory"""
        with self.model_lock:
            try:
                logger.info(f"Loading model: {model_info.name}")

                # Check if model is already loaded
                if model_info.id in self.loaded_models:
                    logger.info(f"Model {model_info.name} already loaded")
                    return True

                # Manage cache size
                if len(self.loaded_models) >= self.max_cache_size:
                    self._evict_oldest_model()

                # Load model based on type
                if model_info.model_type == "text-generation":
                    model, tokenizer = self._load_text_generation_model(model_info)
                elif model_info.model_type == "text-classification":
                    model, tokenizer = self._load_text_classification_model(model_info)
                elif model_info.model_type == "translation":
                    model, tokenizer = self._load_translation_model(model_info)
                elif model_info.model_type == "image-generation":
                    model, tokenizer = self._load_image_generation_model(model_info)
                else:
                    raise ValueError(f"Unsupported model type: {model_info.model_type}")

                # Store loaded model
                self.loaded_models[model_info.id] = {
                    "model": model,
                    "tokenizer": tokenizer,
                    "model_info": model_info,
                    "loaded_at": datetime.now(),
                }

                # Update model info
                model_info.is_loaded = True
                model_info.memory_usage_mb = self._get_model_memory_usage(model)
                model_info.parameters_count = sum(p.numel() for p in model.parameters())
                self.db.update_model(model_info)

                logger.info(f"Successfully loaded model: {model_info.name}")
                return True

            except Exception as e:
                logger.error(f"Error loading model {model_info.name}: {e}")
                return False

    def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory"""
        with self.model_lock:
            if model_id in self.loaded_models:
                del self.loaded_models[model_id]

                # Update model info
                model_info = self.db.get_model(model_id)
                if model_info:
                    model_info.is_loaded = False
                    model_info.memory_usage_mb = 0.0
                    self.db.update_model(model_info)

                logger.info(f"Unloaded model: {model_id}")
                return True
            return False

    def _load_text_generation_model(self, model_info: ModelInfo):
        """Load a text generation model"""
        tokenizer = AutoTokenizer.from_pretrained(
            model_info.tokenizer_path or model_info.model_path, trust_remote_code=True
        )

        model = AutoModelForCausalLM.from_pretrained(
            model_info.model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True,
        )

        if self.device == "cpu":
            model = model.to(self.device)

        return model, tokenizer

    def _load_text_classification_model(self, model_info: ModelInfo):
        """Load a text classification model"""
        tokenizer = AutoTokenizer.from_pretrained(
            model_info.tokenizer_path or model_info.model_path
        )

        model = AutoModel.from_pretrained(
            model_info.model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
        )

        if self.device == "cpu":
            model = model.to(self.device)

        return model, tokenizer

    def _load_translation_model(self, model_info: ModelInfo):
        """Load a translation model"""
        tokenizer = AutoTokenizer.from_pretrained(
            model_info.tokenizer_path or model_info.model_path
        )

        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_info.model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
        )

        if self.device == "cpu":
            model = model.to(self.device)

        return model, tokenizer

    def _load_image_generation_model(self, model_info: ModelInfo):
        """Load an image generation model (placeholder)"""
        # This would be implemented based on specific image generation frameworks
        # like Stable Diffusion, DALL-E, etc.
        raise NotImplementedError("Image generation models not yet implemented")

    def _evict_oldest_model(self):
        """Evict the oldest loaded model from cache"""
        if not self.loaded_models:
            return

        oldest_id = min(self.loaded_models.keys(), key=lambda k: self.loaded_models[k]["loaded_at"])
        self.unload_model(oldest_id)

    def _get_model_memory_usage(self, model) -> float:
        """Get model memory usage in MB"""
        try:
            if self.device == "cuda":
                return torch.cuda.memory_allocated() / 1024 / 1024
            else:
                # Rough estimation for CPU
                total_params = sum(p.numel() for p in model.parameters())
                return total_params * 4 / 1024 / 1024  # 4 bytes per float32
        except:
            return 0.0

    def generate_text(
        self,
        model_id: str,
        prompt: str,
        max_length: int = int(),
        temperature: float = float(),
        top_p: float = float(),
        top_k: int = int(),
    ) -> str:
        """Generate text using a loaded model"""
        if model_id not in self.loaded_models:
            raise ValueError(f"Model {model_id} not loaded")

        model_data = self.loaded_models[model_id]
        model = model_data["model"]
        tokenizer = model_data["tokenizer"]
        model_info = model_data["model_info"]

        # Use provided parameters or defaults
        max_length = max_length or model_info.max_length
        temperature = temperature or model_info.temperature
        top_p = top_p or model_info.top_p
        top_k = top_k or model_info.top_k

        try:
            # Tokenize input
            inputs = tokenizer(prompt, return_tensors="pt")
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Remove input prompt from output
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt) :].strip()

            return generated_text

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise

    def classify_text(self, model_id: str, text: str) -> Dict[str, float]:
        """Classify text using a loaded model"""
        if model_id not in self.loaded_models:
            raise ValueError(f"Model {model_id} not loaded")

        model_data = self.loaded_models[model_id]
        model = model_data["model"]
        tokenizer = model_data["tokenizer"]

        try:
            # Tokenize input
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get predictions
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)

            # Convert to dictionary
            probs = probabilities[0].cpu().numpy()
            return {f"class_{i}": float(prob) for i, prob in enumerate(probs)}

        except Exception as e:
            logger.error(f"Error classifying text: {e}")
            raise

    def translate_text(
        self, model_id: str, text: str, source_lang: str = "en", target_lang: str = "fr"
    ) -> str:
        """Translate text using a loaded model"""
        if model_id not in self.loaded_models:
            raise ValueError(f"Model {model_id} not loaded")

        model_data = self.loaded_models[model_id]
        model = model_data["model"]
        tokenizer = model_data["tokenizer"]

        try:
            # Prepare input
            if hasattr(tokenizer, "lang_code_to_token"):
                # For models like mBART
                inputs = tokenizer(text, return_tensors="pt")
                inputs["labels"] = tokenizer(f"{target_lang} {text}", return_tensors="pt").input_ids
            else:
                # For other translation models
                inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate translation
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=512)

            # Decode output
            translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translated_text

        except Exception as e:
            logger.error(f"Error translating text: {e}")
            raise

    def download_model_from_url(
        self, model_url: str, tokenizer_url: Optional[str] = None
    ) -> tuple[str, Optional[str]]:
        """Download model and tokenizer from URLs and return local paths"""
        try:
            # Parse URLs
            model_parsed = urlparse(model_url)
            model_filename = os.path.basename(model_parsed.path) or "model"

            # Create model directory
            model_dir = self.models_dir / model_filename
            model_dir.mkdir(parents=True, exist_ok=True)

            # Download model
            logger.info(f"Downloading model from: {model_url}")
            model_response = requests.get(model_url, stream=True)
            model_response.raise_for_status()

            model_path = model_dir / "model"
            with open(model_path, "wb") as f:
                for chunk in model_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Download tokenizer if provided
            tokenizer_path = None
            if tokenizer_url:
                logger.info(f"Downloading tokenizer from: {tokenizer_url}")
                tokenizer_response = requests.get(tokenizer_url, stream=True)
                tokenizer_response.raise_for_status()

                tokenizer_path = model_dir / "tokenizer"
                with open(tokenizer_path, "wb") as f:
                    for chunk in tokenizer_response.iter_content(chunk_size=8192):
                        f.write(chunk)

            logger.info(f"Model downloaded to: {model_path}")
            return str(model_path), str(tokenizer_path) if tokenizer_path else None

        except Exception as e:
            logger.error(f"Error downloading model from URL: {e}")
            raise

    def add_model_from_url(
        self,
        name: str,
        model_type: str,
        model_url: str,
        tokenizer_url: Optional[str] = None,
        device: str = "auto",
        max_length: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
    ) -> str:
        """Add a model from URL by downloading it first"""
        try:
            # Download model and tokenizer
            model_path, tokenizer_path = self.download_model_from_url(model_url, tokenizer_url)

            # Create model info
            model_info = ModelInfo(
                id=str(uuid.uuid4()),
                name=name,
                model_type=model_type,
                model_path=model_path,
                tokenizer_path=tokenizer_path,
                device=device,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
            )

            # Add to database
            model_id = self.db.add_model(model_info)

            # Try to load the model
            if self.load_model(model_info):
                logger.info(f"Successfully added and loaded model from URL: {name}")
            else:
                logger.warning(f"Model added from URL but failed to load: {name}")

            return model_id

        except Exception as e:
            logger.error(f"Error adding model from URL: {e}")
            raise

    def get_models_summary(self) -> Dict[str, Any]:
        """Get a summary of all models with statistics"""
        models = self.db.get_all_models()

        summary = {
            "total_models": len(models),
            "loaded_models": len([m for m in models if m.is_loaded]),
            "total_memory_mb": sum(m.memory_usage_mb for m in models if m.is_loaded),
            "models_by_type": {},
            "models": [],
        }

        for model in models:
            # Add to type statistics
            model_type = model.model_type
            if model_type not in summary["models_by_type"]:
                summary["models_by_type"][model_type] = {"count": 0, "loaded": 0, "memory_mb": 0.0}
            summary["models_by_type"][model_type]["count"] += 1
            if model.is_loaded:
                summary["models_by_type"][model_type]["loaded"] += 1
                summary["models_by_type"][model_type]["memory_mb"] += model.memory_usage_mb

            # Add model details
            summary["models"].append(
                {
                    "id": model.id,
                    "name": model.name,
                    "type": model.model_type,
                    "loaded": model.is_loaded,
                    "memory_mb": model.memory_usage_mb,
                    "parameters_count": model.parameters_count,
                    "created_at": model.created_at.isoformat(),
                }
            )

        return summary


# Pydantic models for API
class ModelLoadRequest(BaseModel):
    name: str
    model_type: str
    model_path: str
    tokenizer_path: Optional[str] = None
    device: str = "auto"
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50


class ModelLoadFromUrlRequest(BaseModel):
    name: str
    model_type: str
    model_url: str
    tokenizer_url: Optional[str] = None
    device: str = "auto"
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50


class TextGenerationRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None


class TextClassificationRequest(BaseModel):
    text: str


class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "fr"


class ModelService:
    """Main model service daemon"""

    def __init__(self, config: Dict[str, Any] = dict[str(), object()]()):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.model_manager = ModelManager(
            models_dir=self.config["models_dir"], max_cache_size=self.config["model_cache_size"]
        )

        # Initialize lightweight server
        self.lightweight_server = LightweightModelServer(
            models_dir=f"{self.config['models_dir']}/lightweight",
            port=self.config["port"] + 1,  # Use next port
        )

        # Initialize PDF processor
        self.pdf_processor = PDFProcessor(
            models_dir=f"{self.config['models_dir']}/lightweight",
            port=self.config["port"] + 2,  # Use next port after lightweight server
        )

        # Initialize lightweight embedder
        self.embedder = LightweightEmbedder(models_dir=f"{self.config['models_dir']}/embeddings")

        self.running = False
        self.pid_file = Path.home() / ".local" / "mcli" / "model_service" / "model_service.pid"
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

        # FastAPI app
        self.app = FastAPI(
            title="MCLI Model Service",
            description="A service for hosting and providing inference APIs for language models",
            version="1.0.0",
        )

        # Add CORS middleware
        if self.config["enable_cors"]:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config["cors_origins"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes"""

        @self.app.get("/")
        async def root():
            return {
                "service": "MCLI Model Service",
                "version": "1.0.0",
                "status": "running",
                "models_loaded": len(self.model_manager.loaded_models),
            }

        @self.app.get("/models")
        async def list_models():
            """List all available models"""
            models = self.model_manager.db.get_all_models()
            return [asdict(model) for model in models]

        @self.app.get("/models/summary")
        async def get_models_summary():
            """Get a summary of all models with statistics"""
            return self.model_manager.get_models_summary()

        @self.app.post("/models")
        async def load_model(request: ModelLoadRequest):
            """Load a new model"""
            try:
                model_info = ModelInfo(
                    id=str(uuid.uuid4()),
                    name=request.name,
                    model_type=request.model_type,
                    model_path=request.model_path,
                    tokenizer_path=request.tokenizer_path,
                    device=request.device,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                )

                # Add to database
                model_id = self.model_manager.db.add_model(model_info)

                # Load model
                success = self.model_manager.load_model(model_info)

                if success:
                    return {"model_id": model_id, "status": "loaded"}
                else:
                    # Remove from database if loading failed
                    self.model_manager.db.delete_model(model_id)
                    raise HTTPException(status_code=500, detail="Failed to load model")

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/models/from-url")
        async def load_model_from_url(request: ModelLoadFromUrlRequest):
            """Load a new model from URL"""
            try:
                model_id = self.model_manager.add_model_from_url(
                    name=request.name,
                    model_type=request.model_type,
                    model_url=request.model_url,
                    tokenizer_url=request.tokenizer_url,
                    device=request.device,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                )

                return {"model_id": model_id, "status": "loaded"}

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/models/{model_id}")
        async def unload_model(model_id: str):
            """Unload a model"""
            try:
                success = self.model_manager.unload_model(model_id)
                if success:
                    return {"status": "unloaded"}
                else:
                    raise HTTPException(status_code=404, detail="Model not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put("/models/{model_id}")
        async def update_model(model_id: str, request: Dict[str, Any]):
            """Update model configuration"""
            try:
                # Get current model info
                model_info = self.model_manager.db.get_model(model_id)
                if not model_info:
                    raise HTTPException(status_code=404, detail="Model not found")

                # Update model info with new values
                for key, value in request.items():
                    if hasattr(model_info, key):
                        setattr(model_info, key, value)

                # Update in database
                success = self.model_manager.db.update_model(model_info)
                if success:
                    return {"status": "updated", "model_id": model_id}
                else:
                    raise HTTPException(status_code=500, detail="Failed to update model")

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/models/{model_id}/remove")
        async def remove_model(model_id: str):
            """Remove a model from the database"""
            try:
                # First unload if loaded
                self.model_manager.unload_model(model_id)

                # Remove from database
                success = self.model_manager.db.delete_model(model_id)
                if success:
                    return {"status": "removed", "model_id": model_id}
                else:
                    raise HTTPException(status_code=404, detail="Model not found")

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/models/{model_id}/generate")
        async def generate_text(model_id: str, request: TextGenerationRequest):
            """Generate text using a model"""
            try:
                start_time = time.time()

                generated_text = self.model_manager.generate_text(
                    model_id=model_id,
                    prompt=request.prompt,
                    max_length=request.max_length or 512,
                    temperature=request.temperature or 0.7,
                    top_p=request.top_p or 0.9,
                    top_k=request.top_k or 50,
                )

                execution_time = int((time.time() - start_time) * 1000)

                # Record inference
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-generation",
                    input_data=request.prompt,
                    output_data=generated_text,
                    execution_time_ms=execution_time,
                )

                return {"generated_text": generated_text, "execution_time_ms": execution_time}

            except Exception as e:
                # Record error
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-generation",
                    input_data=request.prompt,
                    error_message=str(e),
                )
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/models/{model_id}/classify")
        async def classify_text(model_id: str, request: TextClassificationRequest):
            """Classify text using a model"""
            try:
                start_time = time.time()

                classifications = self.model_manager.classify_text(
                    model_id=model_id, text=request.text
                )

                execution_time = int((time.time() - start_time) * 1000)

                # Record inference
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-classification",
                    input_data=request.text,
                    output_data=json.dumps(classifications),
                    execution_time_ms=execution_time,
                )

                return {"classifications": classifications, "execution_time_ms": execution_time}

            except Exception as e:
                # Record error
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-classification",
                    input_data=request.text,
                    error_message=str(e),
                )
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/models/{model_id}/translate")
        async def translate_text(model_id: str, request: TranslationRequest):
            """Translate text using a model"""
            try:
                start_time = time.time()

                translated_text = self.model_manager.translate_text(
                    model_id=model_id,
                    text=request.text,
                    source_lang=request.source_lang,
                    target_lang=request.target_lang,
                )

                execution_time = int((time.time() - start_time) * 1000)

                # Record inference
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="translation",
                    input_data=request.text,
                    output_data=translated_text,
                    execution_time_ms=execution_time,
                )

                return {"translated_text": translated_text, "execution_time_ms": execution_time}

            except Exception as e:
                # Record error
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="translation",
                    input_data=request.text,
                    error_message=str(e),
                )
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "models_loaded": len(self.model_manager.loaded_models),
                "memory_usage_mb": sum(
                    model_data["model_info"].memory_usage_mb
                    for model_data in self.model_manager.loaded_models.values()
                ),
            }

        # Lightweight server endpoints
        @self.app.get("/lightweight/models")
        async def list_lightweight_models():
            """List available lightweight models"""
            return {
                "models": LIGHTWEIGHT_MODELS,
                "downloaded": self.lightweight_server.downloader.get_downloaded_models(),
                "loaded": list(self.lightweight_server.loaded_models.keys()),
            }

        @self.app.post("/lightweight/models/{model_key}/download")
        async def download_lightweight_model(model_key: str):
            """Download a lightweight model"""
            if model_key not in LIGHTWEIGHT_MODELS:
                raise HTTPException(status_code=404, detail="Model not found")

            try:
                success = self.lightweight_server.download_and_load_model(model_key)
                if success:
                    return {"status": "downloaded", "model": model_key}
                else:
                    raise HTTPException(status_code=500, detail="Failed to download model")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/lightweight/start")
        async def start_lightweight_server():
            """Start the lightweight server"""
            try:
                self.lightweight_server.start_server()
                return {
                    "status": "started",
                    "port": self.lightweight_server.port,
                    "url": f"http://localhost:{self.lightweight_server.port}",
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/lightweight/status")
        async def lightweight_status():
            """Get lightweight server status"""
            return {
                "running": self.lightweight_server.running,
                "port": self.lightweight_server.port,
                "loaded_models": list(self.lightweight_server.loaded_models.keys()),
                "system_info": self.lightweight_server.get_system_info(),
            }

        # PDF processing endpoints
        @self.app.post("/pdf/extract-text")
        async def extract_pdf_text(request: Dict[str, Any]):
            """Extract text from PDF"""
            try:
                pdf_path = request.get("pdf_path")
                if not pdf_path:
                    raise HTTPException(status_code=400, detail="PDF path is required")

                result = self.pdf_processor.extract_text_from_pdf(pdf_path)
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/pdf/process-with-ai")
        async def process_pdf_with_ai(request: Dict[str, Any]):
            """Process PDF with AI analysis"""
            try:
                pdf_path = request.get("pdf_path")
                model_key = request.get("model_key")

                if not pdf_path:
                    raise HTTPException(status_code=400, detail="PDF path is required")

                # Handle optional model_key parameter
                if model_key:
                    result = self.pdf_processor.process_pdf_with_ai(pdf_path, str(model_key))
                else:
                    result = self.pdf_processor.process_pdf_with_ai(pdf_path)
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/pdf/status")
        async def pdf_processor_status():
            """Get PDF processor status"""
            return self.pdf_processor.get_service_status()

        # Embedding endpoints
        @self.app.post("/embed/text")
        async def embed_text(request: Dict[str, Any]):
            """Embed text using lightweight embedder"""
            try:
                text = request.get("text")
                method = request.get("method")

                if not text:
                    raise HTTPException(status_code=400, detail="Text is required")

                # Handle optional method parameter
                if method:
                    result = self.embedder.embed_text(text, str(method))
                else:
                    result = self.embedder.embed_text(text)
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/embed/document")
        async def embed_document(request: Dict[str, Any]):
            """Embed document using lightweight embedder"""
            try:
                text = request.get("text")
                chunk_size = request.get("chunk_size", 1000)

                if not text:
                    raise HTTPException(status_code=400, detail="Text is required")

                result = self.embedder.embed_document(text, chunk_size)
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/embed/search")
        async def search_embeddings(request: Dict[str, Any]):
            """Search similar documents using embeddings"""
            try:
                query = request.get("query")
                embeddings = request.get("embeddings", [])
                top_k = request.get("top_k", 5)

                if not query:
                    raise HTTPException(status_code=400, detail="Query is required")

                results = self.embedder.search_similar(query, embeddings, top_k)
                return {"results": results}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/embed/status")
        async def embedder_status():
            """Get embedder status"""
            return self.embedder.get_status()

    def start(self):
        """Start the model service"""
        if self.running:
            logger.info("Model service is already running")
            return

        # Check if already running
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    logger.info(f"Model service already running with PID {pid}")
                    return
            except Exception:
                pass

        # Start service
        self.running = True

        # Write PID file
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        logger.info(f"Model service started with PID {os.getpid()}")
        logger.info(f"API available at http://{self.config['host']}:{self.config['port']}")

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Start FastAPI server
        try:
            uvicorn.run(
                self.app,
                host=self.config["host"],
                port=self.config["port"],
                log_level=self.config["log_level"].lower(),
            )
        except KeyboardInterrupt:
            logger.info("Model service interrupted")
        finally:
            self.stop()

    def stop(self):
        """Stop the model service"""
        if not self.running:
            return

        self.running = False

        # Unload all models
        for model_id in list(self.model_manager.loaded_models.keys()):
            self.model_manager.unload_model(model_id)

        # Remove PID file
        if self.pid_file.exists():
            self.pid_file.unlink()

        logger.info("Model service stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def status(self) -> Dict[str, Any]:
        """Get service status"""
        is_running = False
        pid = None

        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                is_running = psutil.pid_exists(pid)
            except Exception:
                pass

        return {
            "running": is_running,
            "pid": pid,
            "pid_file": str(self.pid_file),
            "models_loaded": len(self.model_manager.loaded_models),
            "api_url": f"http://{self.config['host']}:{self.config['port']}",
        }


# CLI Commands
import click


@click.group(name="model-service")
def model_service():
    """Model service daemon for hosting language models"""
    pass


@model_service.command()
@click.option("--config", help="Path to configuration file")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--models-dir", default="./models", help="Directory for model storage")
def start(config: Optional[str], host: str, port: int, models_dir: str):
    """Start the model service daemon"""
    # Load config if provided
    service_config = DEFAULT_CONFIG.copy()
    if config:
        try:
            config_data = read_from_toml(config, "model_service")
            if config_data:
                service_config.update(config_data)
        except Exception as e:
            logger.warning(f"Could not load config from {config}: {e}")

    # Override with command line options
    service_config["host"] = host
    service_config["port"] = port
    service_config["models_dir"] = models_dir

    service = ModelService(service_config)
    service.start()


@model_service.command()
def stop():
    """Stop the model service daemon"""
    pid_file = Path.home() / ".local" / "mcli" / "model_service" / "model_service.pid"

    if not pid_file.exists():
        click.echo("Model service is not running")
        return

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        # Send SIGTERM
        os.kill(pid, signal.SIGTERM)
        click.echo(f"Sent stop signal to model service (PID {pid})")

        # Wait a bit and check if it stopped
        time.sleep(2)
        if not psutil.pid_exists(pid):
            click.echo("Model service stopped successfully")
        else:
            click.echo("Model service may still be running")

    except Exception as e:
        click.echo(f"Error stopping model service: {e}")


@model_service.command()
def status():
    """Show model service status"""
    service = ModelService()
    status_info = service.status()

    if status_info["running"]:
        click.echo(f"✅ Model service is running (PID: {status_info['pid']})")
        click.echo(f"🌐 API available at: {status_info['api_url']}")
        click.echo(f"📊 Models loaded: {status_info['models_loaded']}")
    else:
        click.echo("❌ Model service is not running")

    click.echo(f"📁 PID file: {status_info['pid_file']}")


@model_service.command()
@click.option("--summary", is_flag=True, help="Show summary statistics")
def list_models(summary: bool = False):
    """List all models in the service"""
    service = ModelService()

    try:
        if summary:
            # Show summary
            summary_data = service.model_manager.get_models_summary()
            click.echo("📊 Model Service Summary")
            click.echo("=" * 50)
            click.echo(f"Total Models: {summary_data['total_models']}")
            click.echo(f"Loaded Models: {summary_data['loaded_models']}")
            click.echo(f"Total Memory: {summary_data['total_memory_mb']:.1f} MB")
            click.echo()

            if summary_data["models_by_type"]:
                click.echo("Models by Type:")
                for model_type, stats in summary_data["models_by_type"].items():
                    click.echo(
                        f"  {model_type}: {stats['loaded']}/{stats['count']} loaded ({stats['memory_mb']:.1f} MB)"
                    )
            click.echo()
        else:
            # Show detailed list
            models = service.model_manager.db.get_all_models()

            if not models:
                click.echo("📝 No models found in the service")
                return

            click.echo(f"📝 Found {len(models)} model(s):")
            click.echo("=" * 80)

            for model in models:
                status_icon = "🟢" if model.is_loaded else "⚪"
                click.echo(f"{status_icon} {model.name} (ID: {model.id})")
                click.echo(f"   Type: {model.model_type}")
                click.echo(f"   Path: {model.model_path}")
                if model.tokenizer_path:
                    click.echo(f"   Tokenizer: {model.tokenizer_path}")
                click.echo(f"   Device: {model.device}")
                click.echo(f"   Loaded: {'Yes' if model.is_loaded else 'No'}")
                if model.is_loaded:
                    click.echo(f"   Memory: {model.memory_usage_mb:.1f} MB")
                    click.echo(f"   Parameters: {model.parameters_count:,}")
                click.echo(f"   Created: {model.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing models: {e}")


@model_service.command()
@click.argument("model_path")
@click.option("--name", required=True, help="Model name")
@click.option(
    "--type",
    "model_type",
    required=True,
    help="Model type (text-generation, text-classification, translation)",
)
@click.option("--tokenizer-path", help="Path to tokenizer (optional)")
@click.option("--device", default="auto", help="Device to use (cpu, cuda, auto)")
def add_model(
    model_path: str, name: str, model_type: str, tokenizer_path: str = str(), device: str = "auto"
):
    """Add a model to the service"""
    service = ModelService()

    try:
        model_info = ModelInfo(
            id=str(uuid.uuid4()),
            name=name,
            model_type=model_type,
            model_path=model_path,
            tokenizer_path=tokenizer_path,
            device=device,
        )

        # Add to database
        model_id = service.model_manager.db.add_model(model_info)
        click.echo(f"✅ Model '{name}' added with ID: {model_id}")

        # Try to load the model
        if service.model_manager.load_model(model_info):
            click.echo(f"✅ Model '{name}' loaded successfully")
        else:
            click.echo(f"⚠️  Model '{name}' added but failed to load")

    except Exception as e:
        click.echo(f"❌ Error adding model: {e}")


@model_service.command()
@click.argument("model_url")
@click.option("--name", required=True, help="Model name")
@click.option(
    "--type",
    "model_type",
    required=True,
    help="Model type (text-generation, text-classification, translation)",
)
@click.option("--tokenizer-url", help="URL to tokenizer (optional)")
@click.option("--device", default="auto", help="Device to use (cpu, cuda, auto)")
@click.option("--max-length", default=512, help="Maximum sequence length")
@click.option("--temperature", default=0.7, help="Temperature for generation")
@click.option("--top-p", default=0.9, help="Top-p for generation")
@click.option("--top-k", default=50, help="Top-k for generation")
def add_model_from_url(
    model_url: str,
    name: str,
    model_type: str,
    tokenizer_url: str = str(),
    device: str = "auto",
    max_length: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
):
    """Add a model from URL to the service"""
    service = ModelService()

    try:
        click.echo(f"🌐 Downloading model from: {model_url}")
        if tokenizer_url:
            click.echo(f"🌐 Downloading tokenizer from: {tokenizer_url}")

        model_id = service.model_manager.add_model_from_url(
            name=name,
            model_type=model_type,
            model_url=model_url,
            tokenizer_url=tokenizer_url,
            device=device,
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )

        click.echo(f"✅ Model '{name}' downloaded and added with ID: {model_id}")

    except Exception as e:
        click.echo(f"❌ Error adding model from URL: {e}")


@model_service.command()
@click.argument("model_id")
@click.option("--name", help="New model name")
@click.option("--temperature", type=float, help="New temperature value")
@click.option("--max-length", type=int, help="New max length value")
@click.option("--top-p", type=float, help="New top-p value")
@click.option("--top-k", type=int, help="New top-k value")
@click.option("--device", help="New device setting")
def update_model(
    model_id: str,
    name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_length: Optional[int] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    device: Optional[str] = None,
):
    """Update model configuration"""
    service = ModelService()

    try:
        # Get current model info
        model_info = service.model_manager.db.get_model(model_id)
        if not model_info:
            click.echo(f"❌ Model {model_id} not found")
            return

        # Build updates
        updates = {}
        if name is not None:
            updates["name"] = name
        if temperature is not None:
            updates["temperature"] = temperature
        if max_length is not None:
            updates["max_length"] = max_length
        if top_p is not None:
            updates["top_p"] = top_p
        if top_k is not None:
            updates["top_k"] = top_k
        if device is not None:
            updates["device"] = device

        if not updates:
            click.echo("❌ No updates specified. Use --help to see available options.")
            return

        # Update model
        for key, value in updates.items():
            setattr(model_info, key, value)

        success = service.model_manager.db.update_model(model_info)
        if success:
            click.echo(f"✅ Model {model_id} updated successfully!")
            click.echo("Updated parameters:")
            for key, value in updates.items():
                click.echo(f"  {key}: {value}")
        else:
            click.echo(f"❌ Failed to update model {model_id}")

    except Exception as e:
        click.echo(f"❌ Error updating model: {e}")


@model_service.command()
@click.argument("model_id")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def remove_model(model_id: str, force: bool = False):
    """Remove a model from the service"""
    service = ModelService()

    try:
        # Get model info first
        model_info = service.model_manager.db.get_model(model_id)
        if not model_info:
            click.echo(f"❌ Model {model_id} not found")
            return

        if not force:
            click.echo(f"Model to remove:")
            click.echo(f"  Name: {model_info.name}")
            click.echo(f"  Type: {model_info.model_type}")
            click.echo(f"  Path: {model_info.model_path}")
            click.echo(f"  Loaded: {'Yes' if model_info.is_loaded else 'No'}")

            if not click.confirm("Are you sure you want to remove this model?"):
                click.echo("Operation cancelled.")
                return

        # First unload if loaded
        if model_info.is_loaded:
            service.model_manager.unload_model(model_id)
            click.echo(f"✅ Model {model_id} unloaded")

        # Remove from database
        success = service.model_manager.db.delete_model(model_id)
        if success:
            click.echo(f"✅ Model {model_id} removed successfully!")
        else:
            click.echo(f"❌ Failed to remove model {model_id}")

    except Exception as e:
        click.echo(f"❌ Error removing model: {e}")


# Lightweight server commands
@model_service.command()
@click.option("--list", is_flag=True, help="List available lightweight models")
@click.option("--download", help="Download a specific lightweight model")
@click.option("--auto", is_flag=True, help="Automatically select best model for your system")
@click.option("--start-server", is_flag=True, help="Start the lightweight server")
@click.option("--port", default=8080, help="Port for lightweight server")
def lightweight(list: bool, download: str, auto: bool, start_server: bool, port: int):
    """Manage lightweight models and server"""
    service = ModelService()

    if list:
        click.echo("🚀 Available Lightweight Models:")
        click.echo("=" * 60)

        for key, info in LIGHTWEIGHT_MODELS.items():
            status = (
                "✅ Downloaded"
                if key in service.lightweight_server.loaded_models
                else "⏳ Not downloaded"
            )
            click.echo(f"{status} - {info['name']} ({info['parameters']})")
            click.echo(
                f"    Size: {info['size_mb']} MB | Efficiency: {info['efficiency_score']}/10"
            )
            click.echo(f"    Type: {info['model_type']} | Tags: {', '.join(info['tags'])}")
            click.echo()
        return

    if download:
        if download not in LIGHTWEIGHT_MODELS:
            click.echo(f"❌ Model '{download}' not found")
            click.echo("Available models:")
            for key in LIGHTWEIGHT_MODELS.keys():
                click.echo(f"  {key}")
            return

        click.echo(f"📥 Downloading {download}...")
        success = service.lightweight_server.download_and_load_model(download)
        if success:
            click.echo(f"✅ Model '{download}' downloaded successfully!")
        else:
            click.echo(f"❌ Failed to download model '{download}'")
        return

    if auto:
        recommended = service.lightweight_server.recommend_model()
        click.echo(f"🎯 Recommended model: {recommended}")
        click.echo(f"📥 Downloading {recommended}...")
        success = service.lightweight_server.download_and_load_model(recommended)
        if success:
            click.echo(f"✅ Model '{recommended}' downloaded successfully!")
        else:
            click.echo(f"❌ Failed to download model '{recommended}'")
        return

    if start_server:
        click.echo(f"🚀 Starting lightweight server on port {port}...")
        service.lightweight_server.port = port
        service.lightweight_server.start_server()

        click.echo(f"✅ Server started!")
        click.echo(f"🌐 API: http://localhost:{port}")
        click.echo(f"📊 Health: http://localhost:{port}/health")
        click.echo(f"📋 Models: http://localhost:{port}/models")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n🛑 Server stopped")
        return

    # Show help if no options provided
    click.echo("Lightweight model server commands:")
    click.echo("  --list          List available models")
    click.echo("  --download MODEL Download a specific model")
    click.echo("  --auto          Download recommended model for your system")
    click.echo("  --start-server  Start the lightweight server")


@model_service.command()
@click.option(
    "--model",
    type=click.Choice(list(LIGHTWEIGHT_MODELS.keys())),
    help="Specific model to download and run",
)
@click.option(
    "--auto", is_flag=True, default=True, help="Automatically select best model for your system"
)
@click.option("--port", default=8080, help="Port to run server on")
@click.option("--list-models", is_flag=True, help="List available models")
@click.option("--download-only", is_flag=True, help="Only download models, don't start server")
def lightweight_run(
    model: Optional[str], auto: bool, port: int, list_models: bool, download_only: bool
):
    """Run lightweight model server (standalone mode)"""
    service = ModelService()

    click.echo("🚀 MCLI Lightweight Model Server")
    click.echo("=" * 50)

    if list_models:
        service.lightweight_server.list_models()
        return 0

    # Get system info and recommend model
    if model:
        selected_model = model
        click.echo(f"🎯 Using specified model: {selected_model}")
    elif auto:
        selected_model = service.lightweight_server.recommend_model()
        click.echo(f"🎯 Recommended model: {selected_model}")
    else:
        click.echo("Available models:")
        for key, info in LIGHTWEIGHT_MODELS.items():
            click.echo(f"  {key}: {info['name']} ({info['parameters']})")
        selected_model = click.prompt(
            "Select model", type=click.Choice(list(LIGHTWEIGHT_MODELS.keys()))
        )

    # Download and load model
    if not service.lightweight_server.download_and_load_model(selected_model):
        click.echo("❌ Failed to download model")
        return 1

    if download_only:
        click.echo("✅ Model downloaded successfully")
        return 0

    # Start server
    click.echo(f"\n🚀 Starting lightweight server on port {port}...")
    service.lightweight_server.port = port
    service.lightweight_server.start_server()

    click.echo(f"\n📝 Usage:")
    click.echo(f"  - API: http://localhost:{port}")
    click.echo(f"  - Health: http://localhost:{port}/health")
    click.echo(f"  - Models: http://localhost:{port}/models")

    try:
        # Keep server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\n🛑 Server stopped")


# PDF processing commands
@model_service.command()
@click.argument("pdf_path")
@click.option("--model", help="Specific model to use for AI analysis")
@click.option("--extract-only", is_flag=True, help="Only extract text, no AI analysis")
def process_pdf(pdf_path: str, model: str, extract_only: bool):
    """Process PDF with AI analysis"""
    service = ModelService()

    try:
        if extract_only:
            click.echo(f"📄 Extracting text from: {pdf_path}")
            result = service.pdf_processor.extract_text_from_pdf(pdf_path)
        else:
            click.echo(f"🤖 Processing PDF with AI: {pdf_path}")
            if model:
                click.echo(f"🎯 Using model: {model}")
                result = service.pdf_processor.process_pdf_with_ai(pdf_path, model)
            else:
                result = service.pdf_processor.process_pdf_with_ai(pdf_path)

        if result.get("success"):
            if extract_only:
                click.echo(f"✅ Text extracted: {result['text_length']} characters")
                click.echo(f"📝 Preview: {result['text'][:200]}...")
            else:
                analysis = result["pdf_analysis"]["ai_analysis"]
                click.echo(f"✅ PDF processed successfully!")
                click.echo(f"📊 Document type: {analysis['document_type']}")
                click.echo(f"📝 Summary: {analysis['summary'][:200]}...")
                click.echo(f"🔑 Key topics: {', '.join(analysis['key_topics'])}")
                click.echo(f"📈 Complexity score: {analysis['complexity_score']:.2f}")
        else:
            click.echo(f"❌ Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        click.echo(f"❌ Error processing PDF: {e}")


@model_service.command()
@click.option("--port", default=8080, help="Port for PDF processing service")
def start_pdf_service(port: int):
    """Start PDF processing service"""
    service = ModelService()

    try:
        click.echo(f"🚀 Starting PDF processing service on port {port}...")
        success = service.pdf_processor.start_pdf_processing_service(port)

        if success:
            click.echo(f"✅ PDF processing service started!")
            click.echo(f"🌐 API: http://localhost:{port}")
            click.echo(f"📊 Status: http://localhost:{port}/status")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                click.echo("\n🛑 PDF processing service stopped")
        else:
            click.echo("❌ Failed to start PDF processing service")

    except Exception as e:
        click.echo(f"❌ Error starting PDF service: {e}")


# Embedding commands
@model_service.command()
@click.argument("text")
@click.option("--method", help="Embedding method (sentence_transformers, tfidf, simple_hash)")
def embed_text(text: str, method: str):
    """Embed text using lightweight embedder"""
    service = ModelService()

    try:
        click.echo(f"🔤 Embedding text: {text[:50]}...")
        if method:
            click.echo(f"🎯 Using method: {method}")
            result = service.embedder.embed_text(text, method)
        else:
            result = service.embedder.embed_text(text)

        if result:
            click.echo(f"✅ Text embedded successfully!")
            click.echo(f"📊 Method: {result['method']}")
            click.echo(f"📏 Dimensions: {result['dimensions']}")
            click.echo(f"📝 Text length: {result['text_length']}")
        else:
            click.echo("❌ Failed to embed text")

    except Exception as e:
        click.echo(f"❌ Error embedding text: {e}")


@model_service.command()
@click.argument("text")
@click.option("--chunk-size", default=1000, help="Chunk size for document embedding")
def embed_document(text: str, chunk_size: int):
    """Embed document using lightweight embedder"""
    service = ModelService()

    try:
        click.echo(f"📄 Embedding document: {text[:50]}...")
        result = service.embedder.embed_document(text, chunk_size)

        if result.get("success"):
            doc_embedding = result["document_embedding"]
            click.echo(f"✅ Document embedded successfully!")
            click.echo(f"📊 Method: {doc_embedding['method']}")
            click.echo(f"📄 Total chunks: {doc_embedding['total_chunks']}")
            click.echo(f"📏 Text length: {doc_embedding['total_text_length']}")
        else:
            click.echo(f"❌ Failed to embed document: {result.get('error', 'Unknown error')}")

    except Exception as e:
        click.echo(f"❌ Error embedding document: {e}")


@model_service.command()
def embedder_status():
    """Show embedder status"""
    service = ModelService()

    try:
        status = service.embedder.get_status()
        click.echo("🔤 Lightweight Embedder Status")
        click.echo("=" * 40)
        click.echo(f"Current method: {status['current_method']}")
        click.echo(f"Models directory: {status['models_dir']}")
        click.echo(f"Cache size: {status['cache_size']}")
        click.echo("\nAvailable methods:")
        for method, available in status["available_methods"].items():
            status_icon = "✅" if available else "❌"
            click.echo(f"  {status_icon} {method}")

    except Exception as e:
        click.echo(f"❌ Error getting embedder status: {e}")


if __name__ == "__main__":
    model_service()
