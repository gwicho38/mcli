"""
Shared test fixtures for mcli-framework

This package contains reusable fixtures organized by category:

- model_fixtures: Model server and related fixtures
- chat_fixtures: Chat clients and conversation fixtures
- cli_fixtures: CLI runners and configuration fixtures
- data_fixtures: Test data generation and file fixtures
- db_fixtures: Database connection and data fixtures

Import fixtures in tests using:
    from tests.fixtures.model_fixtures import mock_model_server

Or configure in conftest.py to make them globally available.
"""

from .chat_fixtures import *  # noqa: F403
from .cli_fixtures import *  # noqa: F403
from .data_fixtures import *  # noqa: F403
from .db_fixtures import *  # noqa: F403

# Import all fixtures for easy access
from .model_fixtures import *  # noqa: F403

__all__ = [  # noqa: F405
    # Model fixtures
    "mock_model_server",
    "mock_pypi_response",
    "sample_model_list",
    "temp_models_dir",
    # Chat fixtures
    "mock_openai_client",
    "mock_anthropic_client",
    "mock_ollama_client",
    "sample_chat_history",
    "mock_chat_config",
    # CLI fixtures
    "cli_runner",
    "isolated_cli_runner",
    "temp_workspace",
    "mock_config_file",
    "mock_env_vars",
    "sample_cli_output",
    # Data fixtures
    "sample_json_data",
    "sample_csv_data",
    "temp_json_file",
    "temp_csv_file",
    "sample_log_entries",
    "temp_log_file",
    "sample_ml_dataset",
    "sample_time_series",
    # DB fixtures
    "mock_db_connection",
    "temp_sqlite_db",
    "mock_supabase_client",
    "sample_db_records",
]
