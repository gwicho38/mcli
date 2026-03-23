"""Centralized configuration management with Pydantic validation.

Provides a single validated settings object that loads from:
1. Environment variables (highest priority)
2. .env file
3. config.toml
4. Defaults (lowest priority)

Usage:
    from mcli.lib.config.settings import get_settings

    settings = get_settings()
    print(settings.mcli_env)
    print(settings.openai_api_key)
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCLISettings(BaseSettings):
    """Validated MCLI configuration.

    Loads from environment variables (MCLI_*, OPENAI_*, etc.) and .env files.
    All fields have sensible defaults for zero-config startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- MCLI Core ---
    mcli_env: str = Field(default="development", alias="MCLI_ENV")
    mcli_home: Optional[str] = Field(default=None, alias="MCLI_HOME")
    mcli_debug: bool = Field(default=False, alias="MCLI_DEBUG")
    mcli_trace_level: int = Field(default=0, alias="MCLI_TRACE_LEVEL")
    mcli_auto_optimize: bool = Field(default=False, alias="MCLI_AUTO_OPTIMIZE")
    mcli_plugin_path: Optional[str] = Field(default=None, alias="MCLI_PLUGIN_PATH")
    mcli_include_test_commands: bool = Field(
        default=False, alias="MCLI_INCLUDE_TEST_COMMANDS"
    )
    mcli_show_performance_summary: bool = Field(
        default=False, alias="MCLI_SHOW_PERFORMANCE_SUMMARY"
    )
    mcli_notebook_execute: bool = Field(default=False, alias="MCLI_NOTEBOOK_EXECUTE")

    # --- Python Environment ---
    mcli_auto_install_deps: bool = Field(
        default=False, alias="MCLI_AUTO_INSTALL_DEPS"
    )
    mcli_use_system_python: bool = Field(
        default=False, alias="MCLI_USE_SYSTEM_PYTHON"
    )
    mcli_venv_path: Optional[str] = Field(default=None, alias="MCLI_VENV_PATH")

    # --- API Keys ---
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_org_id: Optional[str] = Field(default=None, alias="OPENAI_ORG_ID")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # --- System ---
    debug: bool = Field(default=False, alias="DEBUG")
    editor: str = Field(default="vim", alias="EDITOR")
    shell: str = Field(default="/bin/bash", alias="SHELL")

    # --- Paths (derived) ---
    included_dirs: List[str] = Field(
        default=["app", "self", "workflow", "public"],
    )

    @field_validator("mcli_trace_level", mode="before")
    @classmethod
    def validate_trace_level(cls, v):
        """Coerce trace level to int and clamp to 0-3."""
        try:
            level = int(v) if v else 0
        except (ValueError, TypeError):
            return 0
        return max(0, min(3, level))

    @field_validator("mcli_env", mode="before")
    @classmethod
    def validate_env(cls, v):
        """Validate environment name."""
        valid = {"development", "staging", "production", "test"}
        if v and str(v).lower() in valid:
            return str(v).lower()
        return "development"

    @property
    def home_path(self) -> Path:
        """Resolved MCLI home directory."""
        if self.mcli_home:
            return Path(self.mcli_home)
        xdg = os.getenv("XDG_DATA_HOME")
        if xdg:
            return Path(xdg) / "mcli"
        return Path.home() / ".mcli"

    @property
    def workflows_dir(self) -> Path:
        """Global workflows directory."""
        return self.home_path / "workflows"

    @property
    def config_dir(self) -> Path:
        """User config directory (~/.config/mcli)."""
        return Path.home() / ".config" / "mcli"

    @property
    def is_debug(self) -> bool:
        """Whether debug mode is active (either flag)."""
        return self.debug or self.mcli_debug

    @property
    def is_ci(self) -> bool:
        """Whether running in CI environment."""
        return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))

    def has_api_key(self, provider: str) -> bool:
        """Check if an API key is configured for a provider."""
        key_map = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
        }
        return bool(key_map.get(provider))

    def to_env_dict(self) -> dict:
        """Export current settings as environment variable dict (for .env writing)."""
        result = {}
        if self.mcli_env != "development":
            result["MCLI_ENV"] = self.mcli_env
        if self.mcli_debug:
            result["MCLI_DEBUG"] = "1"
        if self.mcli_trace_level > 0:
            result["MCLI_TRACE_LEVEL"] = str(self.mcli_trace_level)
        if self.openai_api_key:
            result["OPENAI_API_KEY"] = self.openai_api_key
        if self.anthropic_api_key:
            result["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        if self.editor != "vim":
            result["EDITOR"] = self.editor
        return result


def load_toml_config(config_path: Optional[Path] = None) -> dict:
    """Load config.toml and return as dict.

    Searches in order: current dir, ~/.mcli/, repo root.
    """
    import tomli

    if config_path and config_path.exists():
        with open(config_path, "rb") as f:
            return tomli.load(f)

    search_paths = [
        Path("config.toml"),
        Path.home() / ".mcli" / "config.toml",
    ]

    for path in search_paths:
        if path.exists():
            with open(path, "rb") as f:
                return tomli.load(f)

    return {}


@lru_cache
def get_settings() -> MCLISettings:
    """Get the cached singleton settings instance.

    Call this from anywhere in the app to get validated configuration.
    The result is cached — settings are loaded once per process.
    """
    toml_config = load_toml_config()

    # Merge toml paths config into settings init
    init_kwargs = {}
    included = toml_config.get("paths", {}).get("included_dirs")
    if included:
        init_kwargs["included_dirs"] = included

    return MCLISettings(**init_kwargs)


def reset_settings():
    """Clear the cached settings (useful for testing)."""
    get_settings.cache_clear()
