#!/usr/bin/env python3
"""
Test script for the efficient model runner functionality.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")

    try:
        import requests

        print("✅ requests imported")
    except ImportError as e:
        print(f"❌ requests import failed: {e}")
        return False

    try:
        import click

        print("✅ click imported")
    except ImportError as e:
        print(f"❌ click import failed: {e}")
        return False

    try:
        import psutil

        print("✅ psutil imported")
    except ImportError as e:
        print(f"❌ psutil import failed: {e}")
        return False

    try:
        from mcli.workflow.model_service.model_service import ModelService

        print("✅ ModelService imported")
    except ImportError as e:
        print(f"❌ ModelService import failed: {e}")
        return False

    return True


def test_system_analysis():
    """Test system analysis functionality"""
    print("\n🧪 Testing system analysis...")

    try:
        import psutil

        # Get basic system info
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)

        print(f"✅ CPU cores: {cpu_count}")
        print(f"✅ Memory: {memory_gb:.1f} GB")

        # Test GPU detection
        try:
            import torch

            gpu_available = torch.cuda.is_available()
            print(f"✅ GPU available: {gpu_available}")
            if gpu_available:
                gpu_name = torch.cuda.get_device_name(0)
                print(f"✅ GPU name: {gpu_name}")
        except ImportError:
            print("⚠️  PyTorch not available for GPU detection")

        return True

    except Exception as e:
        print(f"❌ System analysis failed: {e}")
        return False


def test_model_selection():
    """Test model selection logic"""
    print("\n🧪 Testing model selection...")

    try:
        # Import the efficient runner
        from mcli.workflow.model_service.ollama_efficient_runner import (
            EFFICIENT_MODELS,
            get_system_info,
            recommend_model,
        )

        # Test model dictionary
        print(f"✅ Found {len(EFFICIENT_MODELS)} efficient models:")
        for key, info in EFFICIENT_MODELS.items():
            print(f"  - {key}: {info['name']} ({info['parameters']})")

        # Test system info
        system_info = get_system_info()
        print(f"✅ System info collected")

        # Test model recommendation
        recommended = recommend_model(system_info)
        print(f"✅ Recommended model: {recommended}")

        return True

    except Exception as e:
        print(f"❌ Model selection test failed: {e}")
        return False


def test_ollama_check():
    """Test Ollama installation check"""
    print("\n🧪 Testing Ollama check...")

    try:
        from mcli.workflow.model_service.ollama_efficient_runner import check_ollama_installed

        # This will check if ollama is installed
        installed = check_ollama_installed()

        if installed:
            print("✅ Ollama is installed")
        else:
            print("⚠️  Ollama not installed (this is expected if not installed)")

        return True

    except Exception as e:
        print(f"❌ Ollama check failed: {e}")
        return False


def test_mcli_service():
    """Test MCLI model service functionality"""
    print("\n🧪 Testing MCLI model service...")

    try:
        from mcli.workflow.model_service.model_service import ModelService

        # Create service instance
        service = ModelService()
        print("✅ ModelService created")

        # Check status
        status = service.status()
        print(f"✅ Service status: {status['running']}")

        # Test database
        models = service.model_manager.db.get_all_models()
        print(f"✅ Database accessible, {len(models)} models found")

        return True

    except Exception as e:
        print(f"❌ MCLI service test failed: {e}")
        return False


def test_api_endpoints():
    """Test API endpoint definitions"""
    print("\n🧪 Testing API endpoints...")

    try:
        from mcli.workflow.model_service.model_service import ModelService

        service = ModelService()

        # Check for required endpoints
        routes = [route.path for route in service.app.routes]
        required_routes = ["/models", "/models/summary", "/models/from-url"]

        for route in required_routes:
            if route in routes:
                print(f"✅ Route {route} found")
            else:
                print(f"❌ Route {route} not found")
                return False

        return True

    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Efficient Model Runner")
    print("=" * 50)

    tests = [
        ("Imports", test_imports),
        ("System Analysis", test_system_analysis),
        ("Model Selection", test_model_selection),
        ("Ollama Check", test_ollama_check),
        ("MCLI Service", test_mcli_service),
        ("API Endpoints", test_api_endpoints),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} test passed")
        else:
            print(f"❌ {test_name} test failed")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The efficient model runner is ready to use.")
        print("\n📝 Next steps:")
        print("1. Install Ollama: https://ollama.com/download")
        print("2. Run: python ollama_efficient_runner.py")
        print("3. Follow the prompts to download and test models")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
