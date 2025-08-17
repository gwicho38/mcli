#!/usr/bin/env python3
"""
Test script for lightweight model server integration with MCLI model service
"""

import json
import sys
import time
from pathlib import Path

import requests

# Add the parent directory to the path so we can import the model service
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcli.workflow.model_service.model_service import LIGHTWEIGHT_MODELS, ModelService


def test_lightweight_integration():
    """Test the lightweight server integration"""
    print("🧪 Testing Lightweight Model Server Integration")
    print("=" * 60)

    # Create service instance
    service = ModelService()

    # Test 1: List available lightweight models
    print("\n1. Testing lightweight models listing...")
    try:
        models = service.lightweight_server.downloader.get_downloaded_models()
        print(f"✅ Downloaded models: {models}")

        print("Available lightweight models:")
        for key, info in LIGHTWEIGHT_MODELS.items():
            status = (
                "✅ Downloaded"
                if key in service.lightweight_server.loaded_models
                else "⏳ Not downloaded"
            )
            print(f"  {status} - {info['name']} ({info['parameters']})")
    except Exception as e:
        print(f"❌ Error listing models: {e}")

    # Test 2: System analysis
    print("\n2. Testing system analysis...")
    try:
        system_info = service.lightweight_server.get_system_info()
        print(f"✅ System info: {system_info}")

        recommended = service.lightweight_server.recommend_model()
        print(f"✅ Recommended model: {recommended}")
    except Exception as e:
        print(f"❌ Error analyzing system: {e}")

    # Test 3: Download a small model
    print("\n3. Testing model download...")
    try:
        # Use the smallest model for testing
        test_model = "prajjwal1/bert-tiny"
        print(f"📥 Downloading {test_model}...")

        success = service.lightweight_server.download_and_load_model(test_model)
        if success:
            print(f"✅ Successfully downloaded {test_model}")
        else:
            print(f"❌ Failed to download {test_model}")
    except Exception as e:
        print(f"❌ Error downloading model: {e}")

    # Test 4: API endpoints (if server is running)
    print("\n4. Testing API endpoints...")
    try:
        # Test lightweight models endpoint
        response = requests.get("http://localhost:8000/lightweight/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Lightweight models API: {len(data.get('models', {}))} models available")
        else:
            print(f"⚠️  Lightweight models API returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠️  Model service not running, skipping API tests")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

    print("\n✅ Integration test completed!")


def test_cli_commands():
    """Test CLI commands"""
    print("\n🧪 Testing CLI Commands")
    print("=" * 40)

    print("Available CLI commands:")
    print("  mcli model-service lightweight --list")
    print("  mcli model-service lightweight --auto")
    print("  mcli model-service lightweight --download prajjwal1/bert-tiny")
    print("  mcli model-service lightweight --start-server --port 8080")
    print("  mcli model-service lightweight-run --auto --port 8080")
    print("  mcli model-service lightweight-run --list-models")


def main():
    """Main test function"""
    print("🚀 MCLI Lightweight Model Server Integration Test")
    print("=" * 70)

    test_lightweight_integration()
    test_cli_commands()

    print("\n📝 Usage Examples:")
    print("1. List available lightweight models:")
    print("   mcli model-service lightweight --list")
    print()
    print("2. Download recommended model:")
    print("   mcli model-service lightweight --auto")
    print()
    print("3. Start lightweight server:")
    print("   mcli model-service lightweight --start-server --port 8080")
    print()
    print("4. Run standalone lightweight server:")
    print("   mcli model-service lightweight-run --auto --port 8080")
    print()
    print("5. API endpoints (when service is running):")
    print("   GET  /lightweight/models")
    print("   POST /lightweight/models/{model_key}/download")
    print("   POST /lightweight/start")
    print("   GET  /lightweight/status")


if __name__ == "__main__":
    main()
