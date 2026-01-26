"""Shared fixtures for chat testing"""

from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_openai_client():
    """Provide a mock OpenAI client for testing"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = Mock(
        return_value=Mock(
            choices=[
                Mock(
                    message=Mock(content="Test response from OpenAI", role="assistant"),
                    finish_reason="stop",
                )
            ],
            usage=Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
    )
    return client


@pytest.fixture
def mock_anthropic_client():
    """Provide a mock Anthropic client for testing"""
    client = Mock()
    client.messages = Mock()
    client.messages.create = Mock(
        return_value=Mock(
            content=[Mock(text="Test response from Anthropic", type="text")],
            stop_reason="end_turn",
            usage=Mock(input_tokens=10, output_tokens=20),
        )
    )
    return client


@pytest.fixture
def mock_ollama_client():
    """Provide a mock Ollama client for testing"""
    client = Mock()
    client.chat = Mock(
        return_value=Mock(
            message=Mock(content="Test response from Ollama", role="assistant"),
            done=True,
        )
    )
    client.list = Mock(return_value=Mock(models=[]))
    return client


@pytest.fixture
def sample_chat_history():
    """Provide sample chat history for testing"""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
        {"role": "user", "content": "What is Python?"},
        {
            "role": "assistant",
            "content": "Python is a high-level programming language known for its simplicity and readability.",
        },
    ]


@pytest.fixture
def mock_chat_config():
    """Provide mock chat configuration"""
    return {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
        "stream": False,
        "system_prompt": "You are a helpful assistant.",
    }
