"""Shared fixtures for chat testing"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = Mock()

    # Mock response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Test response from OpenAI"
    mock_response.choices[0].finish_reason = "stop"

    client.chat.completions.create.return_value = mock_response

    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    client = Mock()
    client.messages = Mock()
    client.messages.create = Mock()

    # Mock response
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test response from Claude"
    mock_response.stop_reason = "end_turn"

    client.messages.create.return_value = mock_response

    return client


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing"""
    client = Mock()
    client.chat = Mock()

    # Mock response
    mock_response = {
        "message": {
            "role": "assistant",
            "content": "Test response from Ollama"
        },
        "done": True
    }

    client.chat.return_value = mock_response

    return client


@pytest.fixture
def sample_chat_history():
    """Provide sample chat history for testing"""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you?"},
        {"role": "user", "content": "What's the weather?"},
        {"role": "assistant", "content": "I don't have access to real-time weather data."}
    ]


@pytest.fixture
def mock_chat_config():
    """Mock chat configuration"""
    return {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
        "stream": False
    }
