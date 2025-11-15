"""Constants module for mcli.

This module provides centralized constants for the entire mcli application,
including environment variables, file paths, messages, defaults, and command metadata.

Usage:
    from mcli.lib.constants import EnvVars, DirNames, ErrorMessages

    api_key = os.getenv(EnvVars.OPENAI_API_KEY)
    config_path = Path.home() / DirNames.CONFIG / FileNames.CONFIG_TOML
    click.echo(ErrorMessages.COMMAND_NOT_FOUND.format(name="foo"))
"""

from .commands import (
    CommandGroups,
    CommandKeys,
    CompletionKeys,
    ConfigKeys,
    DefaultExcludedDirs,
    DefaultExcludedFiles,
    DefaultIncludedDirs,
)
from .defaults import (
    DateFormats,
    Editors,
    Encoding,
    HTTPMethods,
    Languages,
    LogLevels,
    Shells,
    Timeouts,
    URLs,
)
from .env import EnvVars
from .messages import ErrorMessages, InfoMessages, PromptMessages, SuccessMessages, WarningMessages
from .paths import DirNames, FileNames, GitIgnorePatterns, PathPatterns

__version__ = "1.0.0"

__all__ = [
    # Environment variables
    "EnvVars",
    # Paths
    "DirNames",
    "FileNames",
    "PathPatterns",
    "GitIgnorePatterns",
    # Messages
    "ErrorMessages",
    "SuccessMessages",
    "WarningMessages",
    "InfoMessages",
    "PromptMessages",
    # Defaults
    "Editors",
    "Shells",
    "URLs",
    "Languages",
    "LogLevels",
    "HTTPMethods",
    "Timeouts",
    "DateFormats",
    "Encoding",
    # Commands
    "CommandKeys",
    "CommandGroups",
    "ConfigKeys",
    "DefaultIncludedDirs",
    "DefaultExcludedDirs",
    "DefaultExcludedFiles",
    "CompletionKeys",
]
