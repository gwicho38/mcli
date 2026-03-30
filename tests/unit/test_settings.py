"""Tests for the Pydantic settings module."""

import os
from unittest.mock import patch

import pytest

# Env vars to clear during tests so real shell env doesn't leak in
_ISOLATED_ENV = {
    "MCLI_ENV": None,
    "MCLI_DEBUG": None,
    "MCLI_TRACE_LEVEL": None,
    "MCLI_HOME": None,
    "DEBUG": None,
    "EDITOR": None,
    "OPENAI_API_KEY": None,
    "ANTHROPIC_API_KEY": None,
}


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch):
    """Clear settings cache and isolate from real env vars."""
    from mcli.lib.config.settings import reset_settings

    for var in _ISOLATED_ENV:
        monkeypatch.delenv(var, raising=False)
    reset_settings()
    yield
    reset_settings()


class TestMCLISettings:
    """Test the MCLISettings Pydantic model."""

    def test_default_settings(self):
        """Settings load with sensible defaults."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(_env_file=None)
        assert settings.mcli_env == "development"
        assert settings.mcli_debug is False
        assert settings.mcli_trace_level == 0
        assert settings.included_dirs == ["app", "self", "workflow", "public"]

    def test_trace_level_clamped(self):
        """Trace level is clamped to 0-3."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(MCLI_TRACE_LEVEL="5")
        assert settings.mcli_trace_level == 3

        settings2 = MCLISettings(MCLI_TRACE_LEVEL="-1")
        assert settings2.mcli_trace_level == 0

    def test_trace_level_invalid_string(self):
        """Invalid trace level string defaults to 0."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(MCLI_TRACE_LEVEL="abc")
        assert settings.mcli_trace_level == 0

    def test_env_validation(self):
        """Invalid env falls back to development."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(MCLI_ENV="invalid")
        assert settings.mcli_env == "development"

        settings2 = MCLISettings(MCLI_ENV="production")
        assert settings2.mcli_env == "production"

    def test_home_path_default(self):
        """home_path uses ~/.mcli by default."""
        from pathlib import Path

        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings()
        assert settings.home_path == Path.home() / ".mcli"

    def test_home_path_override(self):
        """home_path uses MCLI_HOME when set."""
        from pathlib import Path

        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(MCLI_HOME="/tmp/test-mcli")
        assert settings.home_path == Path("/tmp/test-mcli")

    def test_workflows_dir(self):
        """workflows_dir is under home_path."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings()
        assert settings.workflows_dir == settings.home_path / "workflows"

    def test_has_api_key(self):
        """has_api_key checks for provider keys."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(OPENAI_API_KEY="sk-test")
        assert settings.has_api_key("openai") is True
        assert settings.has_api_key("anthropic") is False

    def test_is_debug(self):
        """is_debug checks both debug flags."""
        from mcli.lib.config.settings import MCLISettings

        assert MCLISettings(_env_file=None).is_debug is False
        assert MCLISettings(_env_file=None, DEBUG="1").is_debug is True
        assert MCLISettings(_env_file=None, MCLI_DEBUG="1").is_debug is True

    def test_to_env_dict(self):
        """to_env_dict exports only non-default values."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(MCLI_ENV="production", OPENAI_API_KEY="sk-test")
        env = settings.to_env_dict()
        assert env["MCLI_ENV"] == "production"
        assert env["OPENAI_API_KEY"] == "sk-test"
        assert "MCLI_DEBUG" not in env  # default value, not exported

    def test_get_settings_cached(self):
        """get_settings returns the same instance (cached)."""
        from mcli.lib.config.settings import get_settings

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset_settings(self):
        """reset_settings clears the cache."""
        from mcli.lib.config.settings import get_settings, reset_settings

        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2

    def test_included_dirs_from_init(self):
        """included_dirs can be overridden via init kwargs."""
        from mcli.lib.config.settings import MCLISettings

        settings = MCLISettings(included_dirs=["app", "custom"])
        assert settings.included_dirs == ["app", "custom"]
