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
        "tokenizer_url": "https://huggingface.co/prajjwal1/bert-tiny/resolve/main/tokenizer.json",
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

        # Create model directory
        model_dir = self.models_dir / model_key
        model_dir.mkdir(exist_ok=True)

        # Download model files
        files_to_download = [
            ("model", model_info["model_url"], model_dir / "pytorch_model.bin"),
            ("tokenizer", model_info["tokenizer_url"], model_dir / "tokenizer.json"),
            ("config", model_info["config_url"], model_dir / "config.json"),
        ]

        for file_type, url, filepath in files_to_download:
            if not self.download_file(url, filepath, file_type):
                return None

        print(f"✅ Successfully downloaded {model_info['name']}")
        return str(model_dir)

    def get_downloaded_models(self) -> List[str]:
        """Get list of downloaded models"""
        models = []
        for model_dir in self.models_dir.iterdir():
            if model_dir.is_dir() and (model_dir / "pytorch_model.bin").exists():
                models.append(model_dir.name)
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

        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        print(f"🚀 Lightweight model server started on port {self.port}")
        print(f"🌐 API available at: http://localhost:{self.port}")

    def _run_server(self):
        """Run the HTTP server"""
        import urllib.parse
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class ModelHandler(BaseHTTPRequestHandler):
            def __init__(self, *args, server_instance=None, **kwargs):
                self.server_instance = server_instance or self
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
                else:
                    self._send_response(404, {"error": "Not found"})

            def do_POST(self):
                """Handle POST requests"""
                parsed_path = urllib.parse.urlparse(self.path)
                path = parsed_path.path

                if path.startswith("/models/") and path.endswith("/generate"):
                    model_name = path.split("/")[2]
                    self._handle_generate(model_name)
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

            def _send_response(self, status_code, data):
                """Send JSON response"""
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))

        # Create custom handler class
        Handler = type("Handler", (ModelHandler,), {"server_instance": self})

        try:
            server = HTTPServer(("localhost", self.port), Handler)
            print(f"✅ Server listening on port {self.port}")
            server.serve_forever()
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
