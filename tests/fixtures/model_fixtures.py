"""Shared fixtures for model testing"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_model_server():
    """Provide a mock LightweightModelServer for testing"""
    from mcli.workflow.model_service.lightweight_model_server import LightweightModelServer

    server = Mock(spec=LightweightModelServer)
    server.running = False
    server.loaded_models = {}
    server.models_dir = Path("/tmp/test_models")
    server.port = 8080

    # Mock methods
    server.start_server = Mock(return_value=True)
    server.stop_server = Mock(return_value=True)
    server.download_and_load_model = Mock(return_value=True)
    server.delete_model = Mock(return_value=True)
    server.get_model_info = Mock(return_value={})

    return server


@pytest.fixture
def mock_pypi_response():
    """Mock PyPI API response for version checking"""
    return {
        "info": {
            "version": "7.0.6",
            "project_urls": {"Changelog": "https://github.com/gwicho38/mcli/releases"},
        },
        "releases": {"7.0.5": [], "7.0.6": []},
    }


@pytest.fixture
def sample_model_list():
    """Provide sample model list for testing"""
    return {
        "distilbert-base-uncased": {
            "name": "DistilBERT Base Uncased",
            "size": "250MB",
            "description": "Lightweight BERT model",
            "downloaded": False,
        },
        "t5-small": {
            "name": "T5 Small",
            "size": "200MB",
            "description": "Text-to-text transfer model",
            "downloaded": False,
        },
    }


@pytest.fixture
def temp_models_dir(tmp_path):
    """Create a temporary models directory"""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    return models_dir
