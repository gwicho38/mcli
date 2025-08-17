#!/usr/bin/env python3
"""
Script to download and run efficient models from Ollama using MCLI model service.

This script identifies the most efficient models in terms of compute and accuracy,
downloads them, and runs them using the MCLI model service.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import click
import requests

# Add the parent directory to the path so we can import the model service
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcli.workflow.model_service.model_service import ModelManager, ModelService

# Efficient models from Ollama search results
EFFICIENT_MODELS = {
    "phi3-mini": {
        "name": "Phi-3 Mini",
        "description": "Microsoft's lightweight 3.8B model with excellent reasoning",
        "model_url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct/resolve/main/tokenizer.json",
        "model_type": "text-generation",
        "parameters": "3.8B",
        "efficiency_score": 9.5,
        "accuracy_score": 8.5,
    },
    "gemma3n-1b": {
        "name": "Gemma3n 1B",
        "description": "Google's efficient 1B model for everyday devices",
        "model_url": "https://huggingface.co/google/gemma3n-1b/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/google/gemma3n-1b/resolve/main/tokenizer.json",
        "model_type": "text-generation",
        "parameters": "1B",
        "efficiency_score": 9.8,
        "accuracy_score": 7.5,
    },
    "tinyllama-1.1b": {
        "name": "TinyLlama 1.1B",
        "description": "Compact 1.1B model trained on 3 trillion tokens",
        "model_url": "https://huggingface.co/jzhang38/TinyLlama-1.1B-Chat-v1.0/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/jzhang38/TinyLlama-1.1B-Chat-v1.0/resolve/main/tokenizer.json",
        "model_type": "text-generation",
        "parameters": "1.1B",
        "efficiency_score": 9.7,
        "accuracy_score": 7.0,
    },
    "phi4-mini-reasoning": {
        "name": "Phi-4 Mini Reasoning",
        "description": "Lightweight 3.8B model with advanced reasoning",
        "model_url": "https://huggingface.co/microsoft/Phi-4-mini-reasoning/resolve/main/pytorch_model.bin",
        "tokenizer_url": "https://huggingface.co/microsoft/Phi-4-mini-reasoning/resolve/main/tokenizer.json",
        "model_type": "text-generation",
        "parameters": "3.8B",
        "efficiency_score": 9.3,
        "accuracy_score": 8.8,
    },
}


def get_system_info():
    """Get system information for model selection"""
    import psutil

    # Get CPU info
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    memory_gb = psutil.virtual_memory().total / (1024**3)

    # Check for GPU
    try:
        import torch

        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        else:
            gpu_name = "None"
            gpu_memory = 0
    except ImportError:
        gpu_available = False
        gpu_name = "PyTorch not available"
        gpu_memory = 0

    return {
        "cpu_count": cpu_count,
        "cpu_freq_mhz": cpu_freq.current if cpu_freq else 0,
        "memory_gb": memory_gb,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "gpu_memory_gb": gpu_memory,
    }


def recommend_model(system_info: Dict) -> str:
    """Recommend the best model based on system capabilities"""
    print("🔍 Analyzing system capabilities...")
    print(f"  CPU Cores: {system_info['cpu_count']}")
    print(f"  CPU Frequency: {system_info['cpu_freq_mhz']:.0f} MHz")
    print(f"  RAM: {system_info['memory_gb']:.1f} GB")
    print(f"  GPU: {system_info['gpu_name']}")
    print(f"  GPU Memory: {system_info['gpu_memory_gb']:.1f} GB")

    # Simple recommendation logic
    if system_info["gpu_available"] and system_info["gpu_memory_gb"] >= 4:
        # Good GPU available
        if system_info["memory_gb"] >= 16:
            return "phi3-mini"  # Best balance for good hardware
        else:
            return "gemma3n-1b"  # More memory efficient
    elif system_info["memory_gb"] >= 8:
        # CPU-only with decent RAM
        return "phi3-mini"
    else:
        # Limited resources
        return "tinyllama-1.1b"


def download_and_setup_model(model_key: str, service: ModelService) -> Optional[str]:
    """Download and setup a model using the MCLI service"""
    model_info = EFFICIENT_MODELS[model_key]

    print(f"\n🚀 Setting up {model_info['name']}...")
    print(f"  Description: {model_info['description']}")
    print(f"  Parameters: {model_info['parameters']}")
    print(f"  Efficiency Score: {model_info['efficiency_score']}/10")
    print(f"  Accuracy Score: {model_info['accuracy_score']}/10")

    try:
        # Add model to service
        model_id = service.model_manager.add_model_from_url(
            name=model_info["name"],
            model_type=model_info["model_type"],
            model_url=model_info["model_url"],
            tokenizer_url=model_info["tokenizer_url"],
            device="auto",
            max_length=2048,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
        )

        print(f"✅ Model {model_info['name']} successfully added with ID: {model_id}")
        return model_id

    except Exception as e:
        print(f"❌ Error setting up model {model_info['name']}: {e}")
        return None


def test_model(service: ModelService, model_id: str, model_name: str):
    """Test the model with sample prompts"""
    print(f"\n🧪 Testing {model_name}...")

    test_prompts = [
        "Explain quantum computing in simple terms.",
        "Write a Python function to calculate fibonacci numbers.",
        "What are the benefits of renewable energy?",
        "Translate 'Hello, how are you?' to Spanish.",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📝 Test {i}: {prompt}")

        try:
            start_time = time.time()

            # Generate response
            response = service.model_manager.generate_text(
                model_id=model_id, prompt=prompt, max_length=512, temperature=0.7
            )

            execution_time = time.time() - start_time

            print(f"⏱️  Response time: {execution_time:.2f} seconds")
            print(f"🤖 Response: {response[:200]}{'...' if len(response) > 200 else ''}")

        except Exception as e:
            print(f"❌ Error generating response: {e}")


def start_model_service():
    """Start the MCLI model service"""
    print("🔧 Starting MCLI model service...")

    try:
        # Check if service is already running
        service = ModelService()
        status = service.status()

        if status["running"]:
            print(f"✅ Model service already running at {status['api_url']}")
            return service
        else:
            print("🚀 Starting model service...")
            # Start service in background
            import threading

            service_thread = threading.Thread(target=service.start, daemon=True)
            service_thread.start()

            # Wait for service to start
            time.sleep(3)
            print("✅ Model service started")
            return service

    except Exception as e:
        print(f"❌ Error starting model service: {e}")
        return None


@click.command()
@click.option(
    "--model",
    type=click.Choice(list(EFFICIENT_MODELS.keys())),
    help="Specific model to download and run",
)
@click.option(
    "--auto", is_flag=True, default=True, help="Automatically select best model for your system"
)
@click.option("--test", is_flag=True, default=True, help="Run test prompts after setup")
@click.option(
    "--service-only", is_flag=True, help="Only start the model service without downloading models"
)
def main(model: Optional[str], auto: bool, test: bool, service_only: bool):
    """Download and run efficient models from Ollama using MCLI"""

    print("🚀 MCLI Efficient Model Runner")
    print("=" * 50)

    # Start model service
    service = start_model_service()
    if not service:
        print("❌ Failed to start model service")
        return 1

    if service_only:
        print("✅ Model service is running. Use the API or CLI to manage models.")
        return 0

    # Get system info and recommend model
    system_info = get_system_info()

    if model:
        selected_model = model
        print(f"🎯 Using specified model: {selected_model}")
    elif auto:
        selected_model = recommend_model(system_info)
        print(f"🎯 Recommended model: {selected_model}")
    else:
        print("Available models:")
        for key, info in EFFICIENT_MODELS.items():
            print(f"  {key}: {info['name']} ({info['parameters']})")
        selected_model = click.prompt(
            "Select model", type=click.Choice(list(EFFICIENT_MODELS.keys()))
        )

    # Download and setup model
    model_id = download_and_setup_model(selected_model, service)
    if not model_id:
        print("❌ Failed to setup model")
        return 1

    # Test the model
    if test:
        model_name = EFFICIENT_MODELS[selected_model]["name"]
        test_model(service, model_id, model_name)

    print(f"\n🎉 Setup complete! Model {EFFICIENT_MODELS[selected_model]['name']} is ready to use.")
    print(f"📊 Model ID: {model_id}")
    print(f"🌐 API available at: http://localhost:8000")
    print(f"📝 Use 'mcli model-service list-models' to see all models")

    return 0


if __name__ == "__main__":
    sys.exit(main())
