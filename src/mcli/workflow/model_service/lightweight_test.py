#!/usr/bin/env python3
"""
Test script for the lightweight model server.
"""

import os
import sys
import time
from pathlib import Path

import requests

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def test_lightweight_models():
    """Test the lightweight models configuration"""
    print("🧪 Testing lightweight models configuration...")

    try:
        from mcli.workflow.model_service.lightweight_model_server import LIGHTWEIGHT_MODELS

        print(f"✅ Found {len(LIGHTWEIGHT_MODELS)} lightweight models:")

        total_size = 0
        for key, info in LIGHTWEIGHT_MODELS.items():
            print(f"  - {key}: {info['name']} ({info['parameters']}) - {info['size_mb']} MB")
            total_size += info["size_mb"]

        print(f"\n📊 Total size if all downloaded: {total_size:.1f} MB")
        print(
            f"🎯 Smallest model: {min(LIGHTWEIGHT_MODELS.items(), key=lambda x: x[1]['size_mb'])[1]['name']}"
        )
        print(
            f"⚡ Most efficient: {max(LIGHTWEIGHT_MODELS.items(), key=lambda x: x[1]['efficiency_score'])[1]['name']}"
        )

        return True

    except Exception as e:
        print(f"❌ Lightweight models test failed: {e}")
        return False


def test_downloader():
    """Test the downloader functionality"""
    print("\n🧪 Testing downloader functionality...")

    try:
        from mcli.workflow.model_service.lightweight_model_server import LightweightModelDownloader

        # Create downloader
        downloader = LightweightModelDownloader("./test_models")
        print("✅ Downloader created")

        # Test session
        if downloader.session:
            print("✅ HTTP session configured")
        else:
            print("❌ HTTP session not configured")
            return False

        # Test models directory
        if downloader.models_dir.exists():
            print("✅ Models directory exists")
        else:
            print("❌ Models directory not created")
            return False

        return True

    except Exception as e:
        print(f"❌ Downloader test failed: {e}")
        return False


def test_server():
    """Test the server functionality"""
    print("\n🧪 Testing server functionality...")

    try:
        from mcli.workflow.model_service.lightweight_model_server import LightweightModelServer

        # Create server
        server = LightweightModelServer(port=8081)  # Use different port for testing
        print("✅ Server created")

        # Test system info
        system_info = server.get_system_info()
        print(f"✅ System info collected:")
        print(f"  - CPU cores: {system_info['cpu_count']}")
        print(f"  - Memory: {system_info['memory_gb']:.1f} GB")
        print(f"  - Free disk: {system_info['disk_free_gb']:.1f} GB")

        # Test model recommendation
        recommended = server.recommend_model()
        print(f"✅ Recommended model: {recommended}")

        return True

    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False


def test_http_server():
    """Test the HTTP server functionality"""
    print("\n🧪 Testing HTTP server...")

    try:
        import threading
        import time

        from mcli.workflow.model_service.lightweight_model_server import LightweightModelServer

        # Create server
        server = LightweightModelServer(port=8082)

        # Start server in background
        server.start_server()
        time.sleep(2)  # Wait for server to start

        # Test server endpoints
        try:
            # Health check
            response = requests.get("http://localhost:8082/health", timeout=5)
            if response.status_code == 200:
                print("✅ Health endpoint working")
            else:
                print("❌ Health endpoint failed")
                return False

            # Models endpoint
            response = requests.get("http://localhost:8082/models", timeout=5)
            if response.status_code == 200:
                print("✅ Models endpoint working")
            else:
                print("❌ Models endpoint failed")
                return False

            # Root endpoint
            response = requests.get("http://localhost:8082/", timeout=5)
            if response.status_code == 200:
                print("✅ Root endpoint working")
            else:
                print("❌ Root endpoint failed")
                return False

            return True

        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to test server")
            return False
        except Exception as e:
            print(f"❌ HTTP server test failed: {e}")
            return False

    except Exception as e:
        print(f"❌ HTTP server test failed: {e}")
        return False


def test_model_download():
    """Test model download functionality"""
    print("\n🧪 Testing model download...")

    try:
        from mcli.workflow.model_service.lightweight_model_server import (
            LIGHTWEIGHT_MODELS,
            LightweightModelDownloader,
        )

        # Create downloader
        downloader = LightweightModelDownloader("./test_download")

        # Test with smallest model
        smallest_model = min(LIGHTWEIGHT_MODELS.items(), key=lambda x: x[1]["size_mb"])[0]
        print(f"📥 Testing download of smallest model: {smallest_model}")

        # This would actually download the model, so we'll just test the method exists
        if hasattr(downloader, "download_model"):
            print("✅ Download method exists")
        else:
            print("❌ Download method not found")
            return False

        if hasattr(downloader, "download_file"):
            print("✅ File download method exists")
        else:
            print("❌ File download method not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Model download test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Lightweight Model Server")
    print("=" * 50)

    tests = [
        ("Lightweight Models", test_lightweight_models),
        ("Downloader", test_downloader),
        ("Server", test_server),
        ("HTTP Server", test_http_server),
        ("Model Download", test_model_download),
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
        print("🎉 All tests passed! The lightweight model server is ready to use.")
        print("\n📝 Next steps:")
        print("1. Run: python lightweight_model_server.py")
        print("2. Choose a model to download")
        print("3. Test with: python lightweight_client.py")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
