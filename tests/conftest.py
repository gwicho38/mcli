"""
Pytest configuration and fixtures for MCLI tests.

This file provides common fixtures and configuration for all tests.
Shared fixtures from tests/fixtures/ are automatically imported and available globally.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Import shared fixtures to make them globally available
# These fixtures can now be used in any test without explicit imports
pytest_plugins = [
    "fixtures.model_fixtures",
    "fixtures.chat_fixtures",
    "fixtures.cli_fixtures",
    "fixtures.data_fixtures",
    "fixtures.db_fixtures",
]

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set test environment variables
os.environ["MCLI_ENV"] = "test"
os.environ["DEBUG"] = "true"
os.environ["MCLI_TRACE_LEVEL"] = "0"


@pytest.fixture
def mock_env(monkeypatch):
    """Provide a clean environment for tests."""
    test_env = {
        "MCLI_ENV": "test",
        "DEBUG": "true",
        "MCLI_TRACE_LEVEL": "0",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    mock = MagicMock()
    mock.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Test response"))
    ]
    return mock


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client."""
    mock = MagicMock()
    mock.messages.create.return_value.content = [MagicMock(text="Test response")]
    return mock


@pytest.fixture
def mock_ollama():
    """Mock Ollama client."""
    mock = MagicMock()
    mock.generate.return_value = {"response": "Test response"}
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    return mock


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.execute.return_value.data = []
    return mock


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[llm]
provider = "local"
model = "test-model"
temperature = 0.7
"""
    )
    return config_file


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # This ensures test isolation
    yield
    # Cleanup code here if needed


# pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "cli: marks tests as CLI tests")
    config.addinivalue_line(
        "markers", "api: marks tests as API tests (require network/credentials)"
    )
    config.addinivalue_line("markers", "requires_api: marks tests requiring API credentials")
    config.addinivalue_line("markers", "requires_db: marks tests requiring database")


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    # Add markers automatically based on test location/name
    for item in items:
        # Mark slow tests
        if "slow" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)

        # Mark integration tests
        if "integration" in item.nodeid or "end_to_end" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Mark unit tests (default for tests not marked otherwise)
        if not any(mark.name in ["integration", "slow"] for mark in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
