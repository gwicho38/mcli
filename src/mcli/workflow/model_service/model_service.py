import os
import sys
import json
import time
import uuid
import base64
import asyncio
import threading
import signal
import psutil
from pathlib import Path
from typing import Optional, Dict, List, Any, Union, Callable
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
import sqlite3
import tempfile
import shutil

# FastAPI for REST API
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from contextlib import asynccontextmanager

# Model loading and inference
import torch
import transformers
from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM, AutoModelForSeq2SeqLM
import numpy as np
from PIL import Image
import requests

# Import existing utilities
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

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
    "log_level": "INFO"
}

@dataclass
class ModelInfo:
    """Represents a loaded model"""
    id: str
    name: str
    model_type: str  # 'text-generation', 'text-classification', 'translation', 'image-generation', etc.
    model_path: str
    tokenizer_path: Optional[str] = None
    device: str = "auto"  # 'cpu', 'cuda', 'auto'
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    created_at: datetime = None
    is_loaded: bool = False
    memory_usage_mb: float = 0.0
    parameters_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class ModelDatabase:
    """Manages model metadata storage"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path.home() / ".local" / "mcli" / "model_service" / "models.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Models table
        cursor.execute('''
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
        ''')
        
        # Inference history
        cursor.execute('''
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
        ''')
        
        conn.commit()
        conn.close()
    
    def add_model(self, model_info: ModelInfo) -> str:
        """Add a new model to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO models 
                (id, name, model_type, model_path, tokenizer_path, device,
                 max_length, temperature, top_p, top_k, created_at, is_loaded,
                 memory_usage_mb, parameters_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model_info.id, model_info.name, model_info.model_type,
                model_info.model_path, model_info.tokenizer_path, model_info.device,
                model_info.max_length, model_info.temperature, model_info.top_p,
                model_info.top_k, model_info.created_at.isoformat(),
                model_info.is_loaded, model_info.memory_usage_mb, model_info.parameters_count
            ))
            
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
            cursor.execute('''
                SELECT id, name, model_type, model_path, tokenizer_path, device,
                       max_length, temperature, top_p, top_k, created_at, is_loaded,
                       memory_usage_mb, parameters_count
                FROM models WHERE id = ?
            ''', (model_id,))
            
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
            cursor.execute('''
                SELECT id, name, model_type, model_path, tokenizer_path, device,
                       max_length, temperature, top_p, top_k, created_at, is_loaded,
                       memory_usage_mb, parameters_count
                FROM models ORDER BY name
            ''')
            
            return [self._row_to_model_info(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def update_model(self, model_info: ModelInfo) -> bool:
        """Update model information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE models 
                SET name = ?, model_type = ?, model_path = ?, tokenizer_path = ?,
                    device = ?, max_length = ?, temperature = ?, top_p = ?, top_k = ?,
                    is_loaded = ?, memory_usage_mb = ?, parameters_count = ?
                WHERE id = ?
            ''', (
                model_info.name, model_info.model_type, model_info.model_path,
                model_info.tokenizer_path, model_info.device, model_info.max_length,
                model_info.temperature, model_info.top_p, model_info.top_k,
                model_info.is_loaded, model_info.memory_usage_mb, model_info.parameters_count,
                model_info.id
            ))
            
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
            cursor.execute('DELETE FROM models WHERE id = ?', (model_id,))
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def record_inference(self, model_id: str, request_type: str, input_data: str = None,
                        output_data: str = None, execution_time_ms: int = None,
                        error_message: str = None):
        """Record inference request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            inference_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO inferences 
                (id, model_id, request_type, input_data, output_data, 
                 execution_time_ms, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (inference_id, model_id, request_type, input_data, output_data,
                  execution_time_ms, error_message))
            
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
            parameters_count=row[13]
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
                    "loaded_at": datetime.now()
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
            model_info.tokenizer_path or model_info.model_path,
            trust_remote_code=True
        )
        
        model = AutoModelForCausalLM.from_pretrained(
            model_info.model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True
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
            device_map="auto" if self.device == "cuda" else None
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
            device_map="auto" if self.device == "cuda" else None
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
        
        oldest_id = min(self.loaded_models.keys(), 
                       key=lambda k: self.loaded_models[k]["loaded_at"])
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
    
    def generate_text(self, model_id: str, prompt: str, max_length: int = None,
                     temperature: float = None, top_p: float = None, top_k: int = None) -> str:
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
                    pad_token_id=tokenizer.eos_token_id
                )
            
            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove input prompt from output
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):].strip()
            
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
    
    def translate_text(self, model_id: str, text: str, source_lang: str = "en", 
                      target_lang: str = "fr") -> str:
        """Translate text using a loaded model"""
        if model_id not in self.loaded_models:
            raise ValueError(f"Model {model_id} not loaded")
        
        model_data = self.loaded_models[model_id]
        model = model_data["model"]
        tokenizer = model_data["tokenizer"]
        
        try:
            # Prepare input
            if hasattr(tokenizer, 'lang_code_to_token'):
                # For models like mBART
                inputs = tokenizer(text, return_tensors="pt")
                inputs['labels'] = tokenizer(f"{target_lang} {text}", return_tensors="pt").input_ids
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
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.model_manager = ModelManager(
            models_dir=self.config["models_dir"],
            max_cache_size=self.config["model_cache_size"]
        )
        self.running = False
        self.pid_file = Path.home() / ".local" / "mcli" / "model_service" / "model_service.pid"
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        
        # FastAPI app
        self.app = FastAPI(
            title="MCLI Model Service",
            description="A service for hosting and providing inference APIs for language models",
            version="1.0.0"
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
                "models_loaded": len(self.model_manager.loaded_models)
            }
        
        @self.app.get("/models")
        async def list_models():
            """List all available models"""
            models = self.model_manager.db.get_all_models()
            return [asdict(model) for model in models]
        
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
                    top_k=request.top_k
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
        
        @self.app.post("/models/{model_id}/generate")
        async def generate_text(model_id: str, request: TextGenerationRequest):
            """Generate text using a model"""
            try:
                start_time = time.time()
                
                generated_text = self.model_manager.generate_text(
                    model_id=model_id,
                    prompt=request.prompt,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k
                )
                
                execution_time = int((time.time() - start_time) * 1000)
                
                # Record inference
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-generation",
                    input_data=request.prompt,
                    output_data=generated_text,
                    execution_time_ms=execution_time
                )
                
                return {
                    "generated_text": generated_text,
                    "execution_time_ms": execution_time
                }
                
            except Exception as e:
                # Record error
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-generation",
                    input_data=request.prompt,
                    error_message=str(e)
                )
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/models/{model_id}/classify")
        async def classify_text(model_id: str, request: TextClassificationRequest):
            """Classify text using a model"""
            try:
                start_time = time.time()
                
                classifications = self.model_manager.classify_text(
                    model_id=model_id,
                    text=request.text
                )
                
                execution_time = int((time.time() - start_time) * 1000)
                
                # Record inference
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-classification",
                    input_data=request.text,
                    output_data=json.dumps(classifications),
                    execution_time_ms=execution_time
                )
                
                return {
                    "classifications": classifications,
                    "execution_time_ms": execution_time
                }
                
            except Exception as e:
                # Record error
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="text-classification",
                    input_data=request.text,
                    error_message=str(e)
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
                    target_lang=request.target_lang
                )
                
                execution_time = int((time.time() - start_time) * 1000)
                
                # Record inference
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="translation",
                    input_data=request.text,
                    output_data=translated_text,
                    execution_time_ms=execution_time
                )
                
                return {
                    "translated_text": translated_text,
                    "execution_time_ms": execution_time
                }
                
            except Exception as e:
                # Record error
                self.model_manager.db.record_inference(
                    model_id=model_id,
                    request_type="translation",
                    input_data=request.text,
                    error_message=str(e)
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
                )
            }
    
    def start(self):
        """Start the model service"""
        if self.running:
            logger.info("Model service is already running")
            return
        
        # Check if already running
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    logger.info(f"Model service already running with PID {pid}")
                    return
            except Exception:
                pass
        
        # Start service
        self.running = True
        
        # Write PID file
        with open(self.pid_file, 'w') as f:
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
                log_level=self.config["log_level"].lower()
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
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                is_running = psutil.pid_exists(pid)
            except Exception:
                pass
        
        return {
            'running': is_running,
            'pid': pid,
            'pid_file': str(self.pid_file),
            'models_loaded': len(self.model_manager.loaded_models),
            'api_url': f"http://{self.config['host']}:{self.config['port']}"
        }

# CLI Commands
import click

@click.group(name="model-service")
def model_service():
    """Model service daemon for hosting language models"""
    pass

@model_service.command()
@click.option('--config', help='Path to configuration file')
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--models-dir', default='./models', help='Directory for model storage')
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
        with open(pid_file, 'r') as f:
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
    
    if status_info['running']:
        click.echo(f"✅ Model service is running (PID: {status_info['pid']})")
        click.echo(f"🌐 API available at: {status_info['api_url']}")
        click.echo(f"📊 Models loaded: {status_info['models_loaded']}")
    else:
        click.echo("❌ Model service is not running")
    
    click.echo(f"📁 PID file: {status_info['pid_file']}")

@model_service.command()
@click.argument('model_path')
@click.option('--name', required=True, help='Model name')
@click.option('--type', 'model_type', required=True, help='Model type (text-generation, text-classification, translation)')
@click.option('--tokenizer-path', help='Path to tokenizer (optional)')
@click.option('--device', default='auto', help='Device to use (cpu, cuda, auto)')
def add_model(model_path: str, name: str, model_type: str, tokenizer_path: str = None, device: str = 'auto'):
    """Add a model to the service"""
    service = ModelService()
    
    try:
        model_info = ModelInfo(
            id=str(uuid.uuid4()),
            name=name,
            model_type=model_type,
            model_path=model_path,
            tokenizer_path=tokenizer_path,
            device=device
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

if __name__ == '__main__':
    model_service() 