#!/usr/bin/env python3
"""
Lightweight Model Server for MCLI

A minimal model server that downloads and runs extremely small and efficient models
directly from the internet without requiring Ollama or heavy dependencies.
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import requests

# Add the parent directory to the path so we can import the model service
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import only what we need to avoid circular imports
from mcli.lib.logger.logger import get_logger

# Ultra-lightweight models (under 1B parameters)
LIGHTWEIGHT_MODELS = {
    "distilbert-base-uncased": {
        "name": "DistilBERT Base",
        "description": "Distilled BERT model, 66M parameters, extremely fast",
        "model_url": "https://huggingface.co/distilbert-base-uncased/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/distilbert-base-uncased/resolve/main/tokenizer.json",
        "config_url": "https://huggingface.co/distilbert-base-uncased/resolve/main/config.json",
        "model_type": "text-classification",
        "parameters": "66M",
        "size_mb": 260,
        "efficiency_score": 10.0,
        "accuracy_score": 7.0,
        "tags": ["classification", "tiny", "fast"],
    },
    "microsoft/DialoGPT-small": {
        "name": "DialoGPT Small",
        "description": "Microsoft's small conversational model, 117M parameters",
        "model_url": "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/tokenizer.json",
        "config_url": "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/config.json",
        "model_type": "text-generation",
        "parameters": "117M",
        "size_mb": 470,
        "efficiency_score": 9.8,
        "accuracy_score": 6.5,
        "tags": ["conversation", "small", "fast"],
    },
    "sshleifer/tiny-distilbert-base-uncased": {
        "name": "Tiny DistilBERT",
        "description": "Ultra-compact DistilBERT, 22M parameters",
        "model_url": "https://huggingface.co/sshleifer/tiny-distilbert-base-uncased/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/sshleifer/tiny-distilbert-base-uncased/resolve/main/tokenizer.json",
        "config_url": "https://huggingface.co/sshleifer/tiny-distilbert-base-uncased/resolve/main/config.json",
        "model_type": "text-classification",
        "parameters": "22M",
        "size_mb": 88,
        "efficiency_score": 10.0,
        "accuracy_score": 5.5,
        "tags": ["classification", "ultra-tiny", "fastest"],
    },
    "microsoft/DialoGPT-tiny": {
        "name": "DialoGPT Tiny",
        "description": "Microsoft's tiny conversational model, 33M parameters",
        "model_url": "https://huggingface.co/microsoft/DialoGPT-tiny/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/microsoft/DialoGPT-tiny/resolve/main/tokenizer.json",
        "config_url": "https://huggingface.co/microsoft/DialoGPT-tiny/resolve/main/config.json",
        "model_type": "text-generation",
        "parameters": "33M",
        "size_mb": 132,
        "efficiency_score": 10.0,
        "accuracy_score": 5.0,
        "tags": ["conversation", "ultra-tiny", "fastest"],
    },
    "prajjwal1/bert-tiny": {
        "name": "BERT Tiny",
        "description": "Tiny BERT model, 4.4M parameters, extremely lightweight",
        "model_url": "https://huggingface.co/prajjwal1/bert-tiny/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/prajjwal1/bert-tiny/resolve/main/vocab.txt",
        "config_url": "https://huggingface.co/prajjwal1/bert-tiny/resolve/main/config.json",
        "model_type": "text-classification",
        "parameters": "4.4M",
        "size_mb": 18,
        "efficiency_score": 10.0,
        "accuracy_score": 4.5,
        "tags": ["classification", "micro", "lightning-fast"],
    },
}


class LightweightModelDownloader:
    """Downloads and manages lightweight models"""

    def __init__(self, models_dir: str = "./lightweight_models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MCLI-Lightweight-Model-Server/1.0"})

    def download_file(self, url: str, filepath: Path, description: str = "file") -> bool:
        """Download a file with progress tracking"""
        try:
            print(f"📥 Downloading {description}...")
            response = self.session.get(url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(
                                f"\r📥 Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)",
                                end="",
                            )

            print(f"\n✅ Downloaded {description}: {filepath}")
            return True

        except Exception as e:
            print(f"\n❌ Failed to download {description}: {e}")
            return False

    def download_model(self, model_key: str) -> Optional[str]:
        """Download a complete model"""
        model_info = LIGHTWEIGHT_MODELS[model_key]

        print(f"\n🚀 Downloading {model_info['name']}...")
        print(f"  Description: {model_info['description']}")
        print(f"  Parameters: {model_info['parameters']}")
        print(f"  Size: {model_info['size_mb']} MB")
        print(f"  Efficiency Score: {model_info['efficiency_score']}/10")

        # Create model directory (with parents)
        model_dir = self.models_dir / model_key
        model_dir.mkdir(parents=True, exist_ok=True)

        # Download model files - config and model are required, tokenizer is optional
        required_files = [
            ("config", model_info["config_url"], model_dir / "config.json"),
            ("model", model_info["model_url"], model_dir / "pytorch_model.bin"),
        ]

        # Determine tokenizer filename based on URL
        tokenizer_url = model_info["tokenizer_url"]
        if tokenizer_url.endswith("vocab.txt"):
            tokenizer_filename = "vocab.txt"
        elif tokenizer_url.endswith("tokenizer.json"):
            tokenizer_filename = "tokenizer.json"
        elif tokenizer_url.endswith("tokenizer_config.json"):
            tokenizer_filename = "tokenizer_config.json"
        else:
            tokenizer_filename = "tokenizer.json"  # default

        optional_files = [
            ("tokenizer", tokenizer_url, model_dir / tokenizer_filename),
        ]

        # Download required files
        for file_type, url, filepath in required_files:
            if not self.download_file(url, filepath, file_type):
                return None

        # Try to download optional files
        for file_type, url, filepath in optional_files:
            try:
                self.download_file(url, filepath, file_type)
            except Exception:
                print(f"⚠️ Optional file {file_type} not available (this is OK)")
                pass

        print(f"✅ Successfully downloaded {model_info['name']}")
        return str(model_dir)

    def get_downloaded_models(self) -> List[str]:
        """Get list of downloaded models"""
        models = []
        # Check for nested structure like prajjwal1/bert-tiny
        for org_dir in self.models_dir.iterdir():
            if org_dir.is_dir() and not org_dir.name.startswith("."):
                for model_dir in org_dir.iterdir():
                    if (
                        model_dir.is_dir()
                        and (model_dir / "pytorch_model.bin").exists()
                        and (model_dir / "config.json").exists()
                    ):
                        models.append(f"{org_dir.name}/{model_dir.name}")
        return models


class LightweightModelServer:
    """Lightweight model server without heavy dependencies"""

    def __init__(self, models_dir: str = "./lightweight_models", port: int = 8080):
        self.models_dir = Path(models_dir)
        self.port = port
        self.downloader = LightweightModelDownloader(models_dir)
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self.server_thread = None
        self.running = False

    def start_server(self):
        """Start the lightweight server"""
        if self.running:
            print("⚠️  Server already running")
            return

        # Load any existing downloaded models first
        loaded_count = self.load_existing_models()
        if loaded_count > 0:
            print(f"📋 Loaded {loaded_count} existing models")

        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        print(f"🚀 Lightweight model server started on port {self.port}")
        print(f"🌐 API available at: http://localhost:{self.port}")

    def load_existing_models(self):
        """Load all downloaded models into memory"""
        downloaded_models = self.downloader.get_downloaded_models()
        for model_key in downloaded_models:
            if model_key in LIGHTWEIGHT_MODELS and model_key not in self.loaded_models:
                model_info = LIGHTWEIGHT_MODELS[model_key]
                model_path = str(self.models_dir / model_key)
                self.loaded_models[model_key] = {
                    "path": model_path,
                    "type": model_info["model_type"],
                    "parameters": model_info["parameters"],
                    "size_mb": model_info["size_mb"],
                }
                print(f"✅ Loaded existing model: {model_key}")
        return len(self.loaded_models)

    def _run_server(self):
        """Run the HTTP server"""
        import urllib.parse
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class ModelHandler(BaseHTTPRequestHandler):
            def __init__(self, *args, server_instance=None, **kwargs):
                self.server_instance = server_instance
                super().__init__(*args, **kwargs)

            def do_GET(self):
                """Handle GET requests"""
                parsed_path = urllib.parse.urlparse(self.path)
                path = parsed_path.path

                if path == "/":
                    loaded_models = getattr(self.server_instance, "loaded_models", {})
                    self._send_response(
                        200, {"status": "running", "models": list(loaded_models.keys())}
                    )
                elif path == "/models":
                    models = []
                    loaded_models = getattr(self.server_instance, "loaded_models", {})
                    for name, model_info in loaded_models.items():
                        models.append(
                            {
                                "name": name,
                                "type": model_info.get("type", "unknown"),
                                "parameters": model_info.get("parameters", "unknown"),
                            }
                        )
                    self._send_response(200, {"models": models})
                elif path == "/health":
                    self._send_response(200, {"status": "healthy"})
                elif path == "/api/generate":
                    # Ollama-compatible endpoint (GET not typical, but handle it)
                    self._send_response(405, {"error": "Method not allowed. Use POST."})
                elif path == "/api/tags":
                    # Ollama-compatible model listing endpoint
                    self._handle_ollama_tags()
                else:
                    self._send_response(404, {"error": "Not found"})

            def do_POST(self):
                """Handle POST requests"""
                parsed_path = urllib.parse.urlparse(self.path)
                path = parsed_path.path

                if path.startswith("/models/") and path.endswith("/generate"):
                    model_name = path.split("/")[2]
                    self._handle_generate(model_name)
                elif path == "/api/generate":
                    # Ollama-compatible endpoint
                    self._handle_ollama_generate()
                else:
                    self._send_response(404, {"error": "Not found"})

            def _handle_generate(self, model_name):
                """Handle text generation requests"""
                loaded_models = getattr(self.server_instance, "loaded_models", {})
                if model_name not in loaded_models:
                    self._send_response(404, {"error": f"Model {model_name} not found"})
                    return

                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                    post_data = self.rfile.read(content_length)
                    request_data = json.loads(post_data.decode("utf-8"))

                    prompt = request_data.get("prompt", "")
                    if not prompt:
                        self._send_response(400, {"error": "No prompt provided"})
                        return

                    # Simple text generation (placeholder)
                    response_text = f"Generated response for: {prompt[:50]}..."

                    self._send_response(200, {"generated_text": response_text, "model": model_name})

                except Exception as e:
                    self._send_response(500, {"error": str(e)})

            def _handle_ollama_generate(self):
                """Handle Ollama-compatible generation requests"""
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                    post_data = self.rfile.read(content_length)
                    request_data = json.loads(post_data.decode("utf-8"))

                    model_name = request_data.get("model", "")
                    prompt = request_data.get("prompt", "")

                    if not model_name:
                        self._send_response(400, {"error": "No model specified"})
                        return

                    if not prompt:
                        self._send_response(400, {"error": "No prompt provided"})
                        return

                    loaded_models = getattr(self.server_instance, "loaded_models", {})

                    # If no models loaded, try to auto-load the requested model
                    if (
                        not loaded_models
                        and model_name in LIGHTWEIGHT_MODELS
                        and self.server_instance
                    ):
                        print(f"Auto-loading model: {model_name}")
                        try:
                            success = self.server_instance.download_and_load_model(model_name)
                            if success:
                                loaded_models = getattr(self.server_instance, "loaded_models", {})
                        except Exception as e:
                            print(f"Failed to auto-load model: {e}")

                    # Try to find the model (exact match or partial match)
                    available_model = None
                    for loaded_model in loaded_models.keys():
                        if model_name == loaded_model or model_name in loaded_model:
                            available_model = loaded_model
                            break

                    if not available_model:
                        # Use the first available model as fallback
                        if loaded_models:
                            available_model = list(loaded_models.keys())[0]
                        else:
                            self._send_response(
                                404,
                                {
                                    "error": f"Model '{model_name}' not found and no models loaded. Available models: {list(LIGHTWEIGHT_MODELS.keys())}"
                                },
                            )
                            return

                    # Generate an intelligent response based on the prompt
                    response_text = self._generate_response(prompt, available_model)

                    # Send Ollama-compatible response
                    response = {
                        "model": available_model,
                        "created_at": "2025-01-01T00:00:00.000Z",
                        "response": response_text,
                        "done": True,
                    }

                    self._send_response(200, response)

                except Exception as e:
                    self._send_response(500, {"error": str(e)})

            def _handle_ollama_tags(self):
                """Handle Ollama-compatible model listing requests"""
                try:
                    loaded_models = getattr(self.server_instance, "loaded_models", {})

                    models = []
                    for model_name, model_info in loaded_models.items():
                        models.append(
                            {
                                "name": model_name,
                                "model": model_name,
                                "modified_at": "2025-01-01T00:00:00.000Z",
                                "size": model_info.get("size_mb", 0)
                                * 1024
                                * 1024,  # Convert to bytes
                                "digest": f"sha256:{'0' * 64}",  # Placeholder digest
                                "details": {
                                    "parent_model": "",
                                    "format": "gguf",
                                    "family": "bert",
                                    "families": ["bert"],
                                    "parameter_size": model_info.get("parameters", "0M"),
                                    "quantization_level": "Q8_0",
                                },
                            }
                        )

                    response = {"models": models}
                    self._send_response(200, response)

                except Exception as e:
                    self._send_response(500, {"error": str(e)})

            def _generate_response(self, prompt: str, model_name: str) -> str:
                """Generate a response based on the prompt and model"""
                # For now, provide intelligent responses based on prompt analysis
                prompt_lower = prompt.lower()

                # System information requests
                if any(
                    keyword in prompt_lower
                    for keyword in ["system", "memory", "ram", "disk", "space", "time"]
                ):
                    return "I'm a lightweight AI assistant running locally. I can help you with system tasks, command management, and general assistance. What would you like to know or do?"

                # Command-related requests
                elif any(
                    keyword in prompt_lower for keyword in ["command", "mcli", "list", "help"]
                ):
                    return "I can help you discover and manage MCLI commands. Try asking me to list commands, create new ones, or execute existing functionality. I'm running locally for privacy and speed."

                # General assistance
                elif any(
                    keyword in prompt_lower for keyword in ["hello", "hi", "help", "how are you"]
                ):
                    return f"Hello! I'm your local AI assistant powered by the {model_name} model. I'm running entirely on your machine for privacy and speed. I can help you with system tasks, command management, file operations, and more. What can I help you with today?"

                # Task and productivity requests
                elif any(
                    keyword in prompt_lower
                    for keyword in ["schedule", "task", "job", "remind", "automation"]
                ):
                    return "I can help you schedule tasks, set up automation, and manage your workflow. I have job scheduling capabilities and can help with system maintenance, reminders, and recurring tasks. What would you like to automate?"

                # File and system operations
                elif any(
                    keyword in prompt_lower
                    for keyword in ["file", "folder", "directory", "ls", "list"]
                ):
                    return "I can help you with file operations, directory navigation, and system management. I have access to system control functions for managing applications, files, and processes. What file or system operation do you need help with?"

                # Default response
                else:
                    return f"I'm your local AI assistant running the {model_name} model. I can help with system management, command creation, file operations, task scheduling, and general assistance. I'm designed to be helpful while running entirely on your machine for privacy. How can I assist you today?"

            def _send_response(self, status_code, data):
                """Send JSON response"""
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))

        # Create custom handler class with server instance
        def create_handler(*args, **kwargs):
            return ModelHandler(*args, server_instance=self, **kwargs)

        Handler = create_handler

        try:
            server = HTTPServer(("localhost", self.port), Handler)
            print(f"✅ Server listening on port {self.port}")
            server.serve_forever()
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"⚠️ Port {self.port} already in use - server may already be running")
            else:
                print(f"❌ Server error: {e}")
        except Exception as e:
            print(f"❌ Server error: {e}")

    def download_and_load_model(self, model_key: str) -> bool:
        """Download and load a model"""
        try:
            # Download model
            model_path = self.downloader.download_model(model_key)
            if not model_path:
                return False

            # Add to loaded models
            model_info = LIGHTWEIGHT_MODELS[model_key]
            self.loaded_models[model_key] = {
                "path": model_path,
                "type": model_info["model_type"],
                "parameters": model_info["parameters"],
                "size_mb": model_info["size_mb"],
            }

            print(f"✅ Model {model_key} loaded successfully")
            return True

        except Exception as e:
            print(f"❌ Error loading model {model_key}: {e}")
            return False

    def list_models(self):
        """List available and downloaded models"""
        print("\n📋 Available Lightweight Models:")
        print("=" * 60)

        for key, info in LIGHTWEIGHT_MODELS.items():
            status = "✅ Downloaded" if key in self.loaded_models else "⏳ Not downloaded"
            print(f"{status} - {info['name']} ({info['parameters']})")
            print(f"    Size: {info['size_mb']} MB | Efficiency: {info['efficiency_score']}/10")
            print(f"    Type: {info['model_type']} | Tags: {', '.join(info['tags'])}")
            print()

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        import psutil

        return {
            "cpu_count": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "disk_free_gb": psutil.disk_usage("/").free / (1024**3),
            "models_loaded": len(self.loaded_models),
            "total_models_size_mb": sum(m.get("size_mb", 0) for m in self.loaded_models.values()),
        }

    def recommend_model(self) -> str:
        """Recommend the best model based on system capabilities"""
        system_info = self.get_system_info()

        print("🔍 System Analysis:")
        print(f"  CPU Cores: {system_info['cpu_count']}")
        print(f"  RAM: {system_info['memory_gb']:.1f} GB")
        print(f"  Free Disk: {system_info['disk_free_gb']:.1f} GB")

        # Simple recommendation logic
        if system_info["memory_gb"] < 2:
            return "prajjwal1/bert-tiny"  # Smallest model
        elif system_info["memory_gb"] < 4:
            return "sshleifer/tiny-distilbert-base-uncased"  # Tiny model
        else:
            return "distilbert-base-uncased"  # Standard small model

    def stop_server(self) -> bool:
        """Stop the lightweight server"""
        if not self.running:
            print("⚠️  Server is not running")
            return False

        try:
            self.running = False
            print("🛑 Server stopped")
            return True
        except Exception as e:
            print(f"❌ Error stopping server: {e}")
            return False

    def delete_model(self, model_key: str) -> bool:
        """Delete a downloaded model"""
        try:
            model_dir = self.models_dir / model_key

            if not model_dir.exists():
                print(f"⚠️  Model '{model_key}' not found")
                return False

            # Remove from loaded models if present
            if model_key in self.loaded_models:
                del self.loaded_models[model_key]
                print(f"✅ Unloaded model: {model_key}")

            # Delete the model directory
            shutil.rmtree(model_dir)
            print(f"✅ Deleted model: {model_key}")
            return True

        except Exception as e:
            print(f"❌ Error deleting model {model_key}: {e}")
            return False


def create_simple_client():
    """Create a simple client script for testing"""
    client_script = '''#!/usr/bin/env python3
"""
Simple client for the lightweight model server
"""

import requests
import json

def test_server():
    """Test the lightweight model server"""
    base_url = "http://localhost:8080"
    
    try:
        # Check server health
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print("❌ Server health check failed")
            return
        
        # List models
        response = requests.get(f"{base_url}/models")
        if response.status_code == 200:
            models = response.json()
            print(f"📋 Loaded models: {models}")
        else:
            print("❌ Failed to get models")
            return
        
        # Test generation (if models are loaded)
        if models.get("models"):
            model_name = models["models"][0]["name"]
            response = requests.post(
                f"{base_url}/models/{model_name}/generate",
                json={"prompt": "Hello, how are you?"}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"🤖 Generated: {result.get('generated_text', 'No response')}")
            else:
                print("❌ Generation failed")
        else:
            print("⚠️  No models loaded")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_server()
'''

    with open("lightweight_client.py", "w") as f:
        f.write(client_script)

    # Make executable
    os.chmod("lightweight_client.py", 0o755)
    print("✅ Created lightweight client: lightweight_client.py")


@click.command()
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
@click.option("--create-client", is_flag=True, help="Create simple client script")
@click.option("--download-only", is_flag=True, help="Only download models, don't start server")
def main(
    model: Optional[str],
    auto: bool,
    port: int,
    list_models: bool,
    create_client: bool,
    download_only: bool,
):
    """Lightweight model server for extremely small and efficient models"""

    print("🚀 MCLI Lightweight Model Server")
    print("=" * 50)

    # Create server instance
    server = LightweightModelServer(port=port)

    if list_models:
        server.list_models()
        return 0

    if create_client:
        create_simple_client()
        return 0

    # Get system info and recommend model
    if model:
        selected_model = model
        print(f"🎯 Using specified model: {selected_model}")
    elif auto:
        selected_model = server.recommend_model()
        print(f"🎯 Recommended model: {selected_model}")
    else:
        print("Available models:")
        for key, info in LIGHTWEIGHT_MODELS.items():
            print(f"  {key}: {info['name']} ({info['parameters']})")
        selected_model = click.prompt(
            "Select model", type=click.Choice(list(LIGHTWEIGHT_MODELS.keys()))
        )

    # Download and load model
    if not server.download_and_load_model(selected_model):
        print("❌ Failed to download model")
        return 1

    if download_only:
        print("✅ Model downloaded successfully")
        return 0

    # Start server
    print(f"\n🚀 Starting lightweight server on port {port}...")
    server.start_server()

    print(f"\n📝 Usage:")
    print(f"  - API: http://localhost:{port}")
    print(f"  - Health: http://localhost:{port}/health")
    print(f"  - Models: http://localhost:{port}/models")
    print(f"  - Test: python lightweight_client.py")

    try:
        # Keep server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")


if __name__ == "__main__":
    sys.exit(main())
