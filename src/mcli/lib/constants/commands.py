"""Command metadata and configuration constants for mcli.

This module defines all constants related to command metadata, configuration keys,
and command management throughout the mcli application.
"""

from typing import Set


class CommandKeys:
    """Keys used in command metadata dictionaries."""

    NAME = "name"
    CODE = "code"
    DESCRIPTION = "description"
    GROUP = "group"
    LANGUAGE = "language"
    SHELL = "shell"
    VERSION = "version"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    METADATA = "metadata"
    HELP = "help"
    PATH = "path"
    MODULE = "module"
    TAGS = "tags"
    IS_ACTIVE = "is_active"
    IS_GROUP = "is_group"
    ARGS = "args"
    KWARGS = "kwargs"
    DEPENDENCIES = "dependencies"
    AUTHOR = "author"


class CommandGroups:
    """Standard command group names.

    Note: WORKFLOW vs WORKFLOWS:
    - WORKFLOW: Management commands for workflows (add, edit, remove, etc.)
      Used by: mcli workflow (formerly mcli commands)
    - WORKFLOWS: Runnable workflow executions (secrets, pdf, clean, etc.)
      Used by: mcli workflows (formerly mcli workflow)
    """

    APP = "app"
    WORKFLOW = "workflow"  # Management of workflows
    WORKFLOWS = "workflows"  # Running workflows
    SELF = "self"
    PUBLIC = "public"
    CUSTOM = "custom"
    ML = "ml"
    TRADING = "trading"
    CHAT = "chat"
    VIDEO = "video"
    COMPLETION = "completion"
    MODEL = "model"


class ConfigKeys:
    """Configuration file keys."""

    PATHS = "paths"
    INCLUDED_DIRS = "included_dirs"
    EXCLUDED_DIRS = "excluded_dirs"
    EXCLUDED_FILES = "excluded_files"
    PLUGINS = "plugins"
    ENABLED = "enabled"
    SETTINGS = "settings"
    ENVIRONMENT = "environment"
    LOGGING = "logging"
    LEVEL = "level"
    FORMAT = "format"
    COMMANDS = "commands"
    ALIASES = "aliases"


class DefaultIncludedDirs:
    """Default directories to scan for commands."""

    DIRS: Set[str] = {"app", "self", "workflow", "public"}


class DefaultExcludedDirs:
    """Default directories to exclude from command scanning."""

    DIRS: Set[str] = {
        "resources",
        "models",
        "scripts",
        "private",
        "venv",
        ".venv",
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "build",
        "dist",
        "*.egg-info",
    }


class DefaultExcludedFiles:
    """Default files to exclude from command scanning."""

    FILES: Set[str] = {
        "setup.py",
        "__init__.py",
        "conftest.py",
        "test_*.py",
        "*_test.py",
    }


class CompletionKeys:
    """Shell completion related constants."""

    COMPLETE_VAR = "_MCLI_COMPLETE"
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    BASH_COMPLETE = "source_bash"
    ZSH_COMPLETE = "source_zsh"
    FISH_COMPLETE = "source_fish"


__all__ = [
    "CommandKeys",
    "CommandGroups",
    "ConfigKeys",
    "DefaultIncludedDirs",
    "DefaultExcludedDirs",
    "DefaultExcludedFiles",
    "CompletionKeys",
]
