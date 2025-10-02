"""Shared fixtures for CLI testing"""
import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def isolated_cli_runner():
    """Provide a CLI runner with isolated filesystem"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory for testing"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create common subdirectories
    (workspace / "logs").mkdir()
    (workspace / "config").mkdir()
    (workspace / "data").mkdir()

    yield workspace

    # Cleanup
    if workspace.exists():
        shutil.rmtree(workspace)


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a mock configuration file"""
    config_dir = tmp_path / ".mcli"
    config_dir.mkdir()

    config_file = config_dir / "config.toml"
    config_file.write_text("""
[general]
log_level = "INFO"
theme = "default"

[chat]
provider = "openai"
model = "gpt-4"
temperature = 0.7

[paths]
logs_dir = "~/.mcli/logs"
cache_dir = "~/.mcli/cache"
""")

    return config_file


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables"""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "MCLI_HOME": "/tmp/test_mcli",
        "MCLI_LOG_LEVEL": "DEBUG"
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
def sample_cli_output():
    """Provide sample CLI output for parsing tests"""
    return {
        "success": "✅ Operation completed successfully\n",
        "error": "❌ Error: Something went wrong\n",
        "warning": "⚠️  Warning: This is a test warning\n",
        "info": "ℹ️  Info: Additional information\n",
        "progress": "📦 Processing... [####------] 40%\n"
    }
