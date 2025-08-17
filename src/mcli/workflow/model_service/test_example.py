#!/usr/bin/env python3
"""
Test example for the MCLI Model Service

This script demonstrates how to:
1. Start the model service
2. Load a simple language model
3. Make inference requests
4. Test different model types
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client import ModelServiceClient


def check_service_running(url: str = "http://localhost:8000") -> bool:
    """Check if the model service is running"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def start_service():
    """Start the model service if not running"""
    if check_service_running():
        print("✅ Model service is already running")
        return True

    print("🚀 Starting model service...")
    try:
        # Start the service in the background
        process = subprocess.Popen(
            [sys.executable, "model_service.py", "start"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait a bit for the service to start
        time.sleep(5)

        if check_service_running():
            print("✅ Model service started successfully")
            return True
        else:
            print("❌ Failed to start model service")
            return False

    except Exception as e:
        print(f"❌ Error starting service: {e}")
        return False


def test_text_generation():
    """Test text generation with a simple model"""
    print("\n" + "=" * 60)
    print("🧪 Testing Text Generation")
    print("=" * 60)

    client = ModelServiceClient()

    try:
        # Load a simple text generation model
        print("📥 Loading GPT-2 model...")
        model_id = client.load_model(
            name="GPT-2 Test",
            model_type="text-generation",
            model_path="gpt2",  # This will download from Hugging Face
            temperature=0.7,
            max_length=50,
        )
        print(f"✅ Model loaded with ID: {model_id}")

        # Test text generation
        test_prompts = [
            "Hello, how are you?",
            "The future of artificial intelligence is",
            "Once upon a time, there was a magical",
            "The best way to learn programming is",
        ]

        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n📝 Test {i}: {prompt}")
            result = client.generate_text(model_id, prompt)
            print(f"🤖 Generated: {result['generated_text']}")
            print(f"⏱️  Time: {result['execution_time_ms']} ms")

        # Clean up
        client.unload_model(model_id)
        print(f"\n🧹 Model {model_id} unloaded")

    except Exception as e:
        print(f"❌ Error in text generation test: {e}")


def test_text_classification():
    """Test text classification with a sentiment model"""
    print("\n" + "=" * 60)
    print("🧪 Testing Text Classification")
    print("=" * 60)

    client = ModelServiceClient()

    try:
        # Load a sentiment classification model
        print("📥 Loading BERT sentiment model...")
        model_id = client.load_model(
            name="BERT Sentiment",
            model_type="text-classification",
            model_path="nlptown/bert-base-multilingual-uncased-sentiment",
        )
        print(f"✅ Model loaded with ID: {model_id}")

        # Test text classification
        test_texts = [
            "I love this product! It's amazing!",
            "This is the worst experience ever.",
            "The service was okay, nothing special.",
            "Absolutely fantastic and wonderful!",
        ]

        for i, text in enumerate(test_texts, 1):
            print(f"\n📝 Test {i}: {text}")
            result = client.classify_text(model_id, text)
            print("🏷️  Classifications:")
            for class_name, probability in result["classifications"].items():
                print(f"   {class_name}: {probability:.4f}")
            print(f"⏱️  Time: {result['execution_time_ms']} ms")

        # Clean up
        client.unload_model(model_id)
        print(f"\n🧹 Model {model_id} unloaded")

    except Exception as e:
        print(f"❌ Error in text classification test: {e}")


def test_translation():
    """Test translation with a translation model"""
    print("\n" + "=" * 60)
    print("🧪 Testing Translation")
    print("=" * 60)

    client = ModelServiceClient()

    try:
        # Load a translation model
        print("📥 Loading Marian translation model...")
        model_id = client.load_model(
            name="Marian EN-FR", model_type="translation", model_path="Helsinki-NLP/opus-mt-en-fr"
        )
        print(f"✅ Model loaded with ID: {model_id}")

        # Test translation
        test_texts = [
            "Hello, how are you?",
            "The weather is beautiful today.",
            "I love learning new languages.",
            "Technology is advancing rapidly.",
        ]

        for i, text in enumerate(test_texts, 1):
            print(f"\n📝 Test {i}: {text}")
            result = client.translate_text(model_id, text, source_lang="en", target_lang="fr")
            print(f"🌐 Translation: {result['translated_text']}")
            print(f"⏱️  Time: {result['execution_time_ms']} ms")

        # Clean up
        client.unload_model(model_id)
        print(f"\n🧹 Model {model_id} unloaded")

    except Exception as e:
        print(f"❌ Error in translation test: {e}")


def test_batch_operations():
    """Test batch operations and performance"""
    print("\n" + "=" * 60)
    print("🧪 Testing Batch Operations")
    print("=" * 60)

    client = ModelServiceClient()

    try:
        # Load a model for batch testing
        print("📥 Loading model for batch testing...")
        model_id = client.load_model(
            name="GPT-2 Batch Test",
            model_type="text-generation",
            model_path="gpt2",
            temperature=0.8,
            max_length=30,
        )

        # Generate multiple prompts
        prompts = [
            "The quick brown fox",
            "In a galaxy far away",
            "The best time to plant a tree",
            "Life is what happens when",
            "Success is not final, failure",
        ]

        print(f"🔄 Processing {len(prompts)} prompts...")
        start_time = time.time()

        results = []
        for i, prompt in enumerate(prompts, 1):
            print(f"  Processing {i}/{len(prompts)}: {prompt[:20]}...")
            result = client.generate_text(model_id, prompt)
            results.append(
                {
                    "prompt": prompt,
                    "generated": result["generated_text"],
                    "time": result["execution_time_ms"],
                }
            )

        total_time = time.time() - start_time

        # Display results
        print(f"\n📊 Batch Results:")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average time per request: {total_time/len(prompts):.2f} seconds")

        for i, result in enumerate(results, 1):
            print(f"\n{i}. Prompt: {result['prompt']}")
            print(f"   Generated: {result['generated']}")
            print(f"   Time: {result['time']} ms")

        # Clean up
        client.unload_model(model_id)
        print(f"\n🧹 Model {model_id} unloaded")

    except Exception as e:
        print(f"❌ Error in batch operations test: {e}")


def test_service_management():
    """Test service management functions"""
    print("\n" + "=" * 60)
    print("🧪 Testing Service Management")
    print("=" * 60)

    client = ModelServiceClient()

    try:
        # Get service status
        print("📊 Getting service status...")
        status = client.get_status()
        health = client.get_health()

        print(f"Service: {status['service']}")
        print(f"Version: {status['version']}")
        print(f"Status: {status['status']}")
        print(f"Models loaded: {status['models_loaded']}")
        print(f"Memory usage: {health.get('memory_usage_mb', 0):.1f} MB")

        # List models
        print("\n📋 Listing models...")
        models = client.list_models()
        if models:
            print(f"Found {len(models)} models:")
            for model in models:
                status_icon = "✅" if model.get("is_loaded") else "⏳"
                print(f"  {status_icon} {model['name']} ({model['model_type']})")
        else:
            print("No models found")

        print("\n✅ Service management test completed")

    except Exception as e:
        print(f"❌ Error in service management test: {e}")


def main():
    """Main test function"""
    print("🚀 MCLI Model Service Test Suite")
    print("=" * 60)

    # Check if service is running
    if not check_service_running():
        print("❌ Model service is not running")
        print("Please start the service first:")
        print("  python model_service.py start")
        return

    print("✅ Model service is running")

    # Run tests
    test_service_management()
    test_text_generation()
    test_text_classification()
    test_translation()
    test_batch_operations()

    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
