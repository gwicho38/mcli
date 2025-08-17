#!/usr/bin/env python3
"""
Test script for the new model service features:
1. List models functionality
2. Add model from URL functionality
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the model service
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcli.workflow.model_service.model_service import ModelManager, ModelService


def test_list_models():
    """Test the list models functionality"""
    print("🧪 Testing list models functionality...")

    try:
        service = ModelService()
        models = service.model_manager.db.get_all_models()

        print(f"📝 Found {len(models)} models in database")

        if models:
            print("Models:")
            for model in models:
                status = "🟢 Loaded" if model.is_loaded else "⚪ Not Loaded"
                print(f"  {status} - {model.name} ({model.model_type})")
        else:
            print("No models found in database")

        # Test summary
        summary = service.model_manager.get_models_summary()
        print(f"\n📊 Summary:")
        print(f"  Total models: {summary['total_models']}")
        print(f"  Loaded models: {summary['loaded_models']}")
        print(f"  Total memory: {summary['total_memory_mb']:.1f} MB")

        print("✅ List models test passed!")

    except Exception as e:
        print(f"❌ List models test failed: {e}")
        return False

    return True


def test_add_model_from_url():
    """Test the add model from URL functionality"""
    print("\n🧪 Testing add model from URL functionality...")

    try:
        service = ModelService()

        # Test with a simple model URL (this is just a test URL)
        test_model_url = (
            "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/pytorch_model.bin"
        )
        test_tokenizer_url = (
            "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/tokenizer.json"
        )

        print(f"🌐 Testing with URL: {test_model_url}")

        # Note: This would actually download the model, so we'll just test the function exists
        # In a real scenario, you'd want to test with a smaller model or mock the download

        # Test that the method exists and can be called
        if hasattr(service.model_manager, "add_model_from_url"):
            print("✅ add_model_from_url method exists")
        else:
            print("❌ add_model_from_url method not found")
            return False

        if hasattr(service.model_manager, "download_model_from_url"):
            print("✅ download_model_from_url method exists")
        else:
            print("❌ download_model_from_url method not found")
            return False

        print("✅ Add model from URL test passed!")

    except Exception as e:
        print(f"❌ Add model from URL test failed: {e}")
        return False

    return True


def test_api_endpoints():
    """Test that the new API endpoints are properly defined"""
    print("\n🧪 Testing API endpoints...")

    try:
        service = ModelService()

        # Check if the new endpoints are defined
        routes = [route.path for route in service.app.routes]

        expected_routes = ["/models", "/models/summary", "/models/from-url"]

        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} found")
            else:
                print(f"❌ Route {route} not found")
                return False

        print("✅ API endpoints test passed!")

    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

    return True


def main():
    """Run all tests"""
    print("🚀 Testing new model service features...")
    print("=" * 50)

    tests = [test_list_models, test_add_model_from_url, test_api_endpoints]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
