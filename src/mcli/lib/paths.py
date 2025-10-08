"""
Path resolution utilities for mcli

Provides consistent path resolution for logs, config, and data directories
that work both when running from source and when installed as a package.
"""

import os
from pathlib import Path
from typing import Optional


def get_mcli_home() -> Path:
    """
    Get the mcli home directory for storing logs, config, and data.

    Returns:
        Path to ~/.mcli directory, created if it doesn't exist
    """
    # Check for MCLI_HOME environment variable first
    mcli_home = os.getenv("MCLI_HOME")
    if mcli_home:
        path = Path(mcli_home)
    else:
        # Use XDG_DATA_HOME if set, otherwise default to ~/.mcli
        xdg_data_home = os.getenv("XDG_DATA_HOME")
        if xdg_data_home:
            path = Path(xdg_data_home) / "mcli"
        else:
            path = Path.home() / ".mcli"

    # Create directory if it doesn't exist
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    """
    Get the logs directory for mcli.

    Returns:
        Path to logs directory (e.g., ~/.mcli/logs), created if it doesn't exist
    """
    logs_dir = get_mcli_home() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_config_dir() -> Path:
    """
    Get the config directory for mcli.

    Returns:
        Path to config directory (e.g., ~/.mcli/config), created if it doesn't exist
    """
    config_dir = get_mcli_home() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """
    Get the data directory for mcli.

    Returns:
        Path to data directory (e.g., ~/.mcli/data), created if it doesn't exist
    """
    data_dir = get_mcli_home() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    """
    Get the cache directory for mcli.

    Returns:
        Path to cache directory (e.g., ~/.mcli/cache), created if it doesn't exist
    """
    cache_dir = get_mcli_home() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_custom_commands_dir() -> Path:
    """
    Get the custom commands directory for mcli.

    Returns:
        Path to custom commands directory (e.g., ~/.mcli/commands), created if it doesn't exist
    """
    commands_dir = get_mcli_home() / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    return commands_dir
