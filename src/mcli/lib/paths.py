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


def is_git_repository(path: Optional[Path] = None) -> bool:
    """
    Check if the current directory (or specified path) is inside a git repository.

    Args:
        path: Path to check (defaults to current working directory)

    Returns:
        True if inside a git repository, False otherwise
    """
    check_path = path or Path.cwd()

    # Walk up the directory tree looking for .git
    current = check_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return True
        current = current.parent

    return False


def get_git_root(path: Optional[Path] = None) -> Optional[Path]:
    """
    Get the root directory of the git repository.

    Args:
        path: Path to check (defaults to current working directory)

    Returns:
        Path to git root, or None if not in a git repository
    """
    check_path = path or Path.cwd()

    # Walk up the directory tree looking for .git
    current = check_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    return None


def get_local_mcli_dir() -> Optional[Path]:
    """
    Get the local .mcli directory for the current git repository.

    Returns:
        Path to .mcli directory in git root, or None if not in a git repository
    """
    git_root = get_git_root()
    if git_root:
        local_mcli = git_root / ".mcli"
        return local_mcli
    return None


def get_local_commands_dir() -> Optional[Path]:
    """
    Get the local workflows directory for the current git repository.

    Note: This function name is kept for backward compatibility but now returns
    the workflows directory. Checks workflows first, then commands for migration.

    Returns:
        Path to .mcli/workflows (or .mcli/commands for migration) in git root,
        or None if not in a git repository
    """
    local_mcli = get_local_mcli_dir()
    if local_mcli:
        # Check for new workflows directory first
        workflows_dir = local_mcli / "workflows"
        if workflows_dir.exists():
            return workflows_dir

        # Fall back to old commands directory for migration support
        commands_dir = local_mcli / "commands"
        return commands_dir
    return None


def get_custom_commands_dir(global_mode: bool = False) -> Path:
    """
    Get the custom workflows directory for mcli.

    Note: This function name is kept for backward compatibility but now returns
    the workflows directory. Checks workflows first, then commands for migration.

    Args:
        global_mode: If True, always use global directory. If False, use local if in git repo.

    Returns:
        Path to custom workflows directory, created if it doesn't exist
    """
    # If not in global mode and we're in a git repository, use local directory
    if not global_mode:
        local_dir = get_local_commands_dir()
        if local_dir:
            local_dir.mkdir(parents=True, exist_ok=True)
            return local_dir

    # Otherwise, use global directory
    # Check for new workflows directory first
    workflows_dir = get_mcli_home() / "workflows"
    if workflows_dir.exists():
        return workflows_dir

    # Check for old commands directory (for migration support)
    commands_dir = get_mcli_home() / "commands"
    if commands_dir.exists():
        # Return commands directory if it exists (user hasn't migrated yet)
        return commands_dir

    # If neither exists, create the new workflows directory
    workflows_dir.mkdir(parents=True, exist_ok=True)
    return workflows_dir


def get_lockfile_path(global_mode: bool = False) -> Path:
    """
    Get the lockfile path for workflow management.

    Note: Lockfile remains named commands.lock.json for compatibility.

    Args:
        global_mode: If True, use global lockfile. If False, use local if in git repo.

    Returns:
        Path to the lockfile
    """
    workflows_dir = get_custom_commands_dir(global_mode=global_mode)
    # Keep the old lockfile name for compatibility
    return workflows_dir / "commands.lock.json"
