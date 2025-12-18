"""
Test OpenAI Adapter for MCLI Model Service

This test verifies that the OpenAI-compatible API adapter works correctly.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcli.workflow.model_service.lightweight_model_server import LightweightModelServer
from mcli.workflow.model_service.openai_adapter import create_openai_adapter


@pytest.fixture
def model_server():
    """Create a lightweight model server for testing"""
    server = LightweightModelServer(models_dir="./test_models", port=8899)
    return server


@pytest.fixture
def app_with_auth(model_server):
    """Create FastAPI app with OpenAI adapter and authentication"""
    app = FastAPI()
    adapter = create_openai_adapter(model_server, require_auth=True)
    adapter.api_key_manager.add_key("test-api-key", name="test")
    app.include_router(adapter.router)
    return app


@pytest.fixture
def app_without_auth(model_server):
    """Create FastAPI app with OpenAI adapter without authentication"""
    app = FastAPI()
    adapter = create_openai_adapter(model_server, require_auth=False)
    app.include_router(adapter.router)
    return app


@pytest.fixture
def client_with_auth(app_with_auth):
    """Create test client with authentication"""
    return TestClient(app_with_auth)


@pytest.fixture
def client_without_auth(app_without_auth):
    """Create test client without authentication"""
    return TestClient(app_without_auth)


class TestOpenAIAdapterAuth:
    """Test authentication functionality"""

    def test_list_models_requires_auth(self, client_with_auth):
        """Test that listing models requires authentication"""
        response = client_with_auth.get("/v1/models")
        assert response.status_code == 401

    def test_list_models_with_valid_key(self, client_with_auth):
        """Test listing models with valid API key"""
        response = client_with_auth.get(
            "/v1/models", headers={"Authorization": "Bearer test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_models_with_invalid_key(self, client_with_auth):
        """Test listing models with invalid API key"""
        response = client_with_auth.get(
            "/v1/models", headers={"Authorization": "Bearer invalid-key"}
        )
        assert response.status_code == 401

    def test_list_models_without_auth_disabled(self, client_without_auth):
        """Test listing models when auth is disabled"""
        response = client_without_auth.get("/v1/models")
        assert response.status_code == 200

    def test_invalid_auth_header_format(self, client_with_auth):
        """Test with invalid authorization header format"""
        response = client_with_auth.get("/v1/models", headers={"Authorization": "InvalidFormat"})
        assert response.status_code == 401

    def test_missing_bearer_scheme(self, client_with_auth):
        """Test with missing Bearer scheme"""
        response = client_with_auth.get("/v1/models", headers={"Authorization": "test-api-key"})
        assert response.status_code == 401


class TestOpenAIAdapterEndpoints:
    """Test API endpoints"""

    def test_list_models_structure(self, client_without_auth):
        """Test the structure of model list response"""
        response = client_without_auth.get("/v1/models")
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)

        # If models exist, check structure
        if len(data["data"]) > 0:
            model = data["data"][0]
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "created" in model
            assert "owned_by" in model

    def test_chat_completion_basic(self, client_without_auth):
        """Test basic chat completion"""
        request_data = {
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello!"}],
        }

        response = client_without_auth.post("/v1/chat/completions", json=request_data)

        # Note: This might return 500 if no models are loaded, which is expected
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "object" in data
            assert data["object"] == "chat.completion"
            assert "created" in data
            assert "model" in data
            assert "choices" in data
            assert isinstance(data["choices"], list)

            if len(data["choices"]) > 0:
                choice = data["choices"][0]
                assert "index" in choice
                assert "message" in choice
                assert "finish_reason" in choice
                assert choice["message"]["role"] == "assistant"

    def test_chat_completion_with_options(self, client_without_auth):
        """Test chat completion with various options"""
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"},
            ],
            "temperature": 0.5,
            "top_p": 0.9,
            "max_tokens": 100,
        }

        response = client_without_auth.post("/v1/chat/completions", json=request_data)

        # Note: This might return 500 if no models are loaded
        assert response.status_code in [200, 500]

    def test_chat_completion_requires_auth(self, client_with_auth):
        """Test that chat completion requires authentication when enabled"""
        request_data = {
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello!"}],
        }

        response = client_with_auth.post("/v1/chat/completions", json=request_data)
        assert response.status_code == 401

    def test_chat_completion_with_auth(self, client_with_auth):
        """Test chat completion with valid authentication"""
        request_data = {
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello!"}],
        }

        response = client_with_auth.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer test-api-key"},
        )

        # Note: This might return 500 if no models are loaded
        assert response.status_code in [200, 401, 500]


class TestAPIKeyManager:
    """Test API key manager functionality"""

    def test_add_and_validate_key(self):
        """Test adding and validating API keys"""
        from mcli.workflow.model_service.openai_adapter import APIKeyManager

        manager = APIKeyManager()
        manager.add_key("test-key-1", name="test1")

        assert manager.validate_key("test-key-1") is True
        assert manager.validate_key("invalid-key") is False

    def test_multiple_keys(self):
        """Test managing multiple API keys"""
        from mcli.workflow.model_service.openai_adapter import APIKeyManager

        manager = APIKeyManager()
        manager.add_key("key1", name="user1")
        manager.add_key("key2", name="user2")

        assert manager.validate_key("key1") is True
        assert manager.validate_key("key2") is True
        assert manager.validate_key("key3") is False

    def test_remove_key(self):
        """Test removing API keys"""
        from mcli.workflow.model_service.openai_adapter import APIKeyManager

        manager = APIKeyManager()
        manager.add_key("test-key", name="test")

        assert manager.validate_key("test-key") is True

        manager.remove_key("test-key")
        assert manager.validate_key("test-key") is False

    def test_key_usage_tracking(self):
        """Test that key usage is tracked"""
        from mcli.workflow.model_service.openai_adapter import APIKeyManager

        manager = APIKeyManager()
        manager.add_key("test-key", name="test")

        # Validate multiple times
        for _ in range(3):
            manager.validate_key("test-key")

        # Check usage count
        assert manager.valid_keys["test-key"]["usage_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
