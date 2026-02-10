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
    IpfsDefaults,
    Languages,
    LogLevels,
    ServiceDefaults,
    Shells,
    Timeouts,
    URLs,
)
from .env import EnvVars
from .messages import (
    ChatMessages,
    CommandMessages,
    EditMessages,
    ErrorMessages,
    InfoMessages,
    IpfsMessages,
    ModelServiceMessages,
    MoveMessages,
    PromptMessages,
    ServiceMessages,
    SuccessMessages,
    SyncMessages,
    SystemIntegrationMessages,
    VenvMessages,
    WarningMessages,
)
from .paths import DirNames, FileNames, GitIgnorePatterns, PathPatterns, VenvPaths
from .scripts import (
    CommandTypes,
    ScriptCommentPrefixes,
    ScriptExtensions,
    ScriptLanguages,
    ScriptMetadataDefaults,
    ScriptMetadataKeys,
    ShellTypes,
)
from .storage import (
    StorachaBridgeCapabilities,
    StorachaHTTPHeaders,
    StorageContentTypes,
    StorageDefaults,
    StorageEnvVars,
    StorageMessages,
    StoragePaths,
)

__version__ = "1.0.0"

__all__ = [
    # Environment variables
    "EnvVars",
    # Paths
    "DirNames",
    "FileNames",
    "PathPatterns",
    "GitIgnorePatterns",
    "VenvPaths",
    # Messages
    "ErrorMessages",
    "SuccessMessages",
    "WarningMessages",
    "InfoMessages",
    "PromptMessages",
    "ChatMessages",
    "CommandMessages",
    "EditMessages",
    "MoveMessages",
    "ModelServiceMessages",
    "SystemIntegrationMessages",
    "SyncMessages",
    "ServiceMessages",
    "IpfsMessages",
    "VenvMessages",
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
    "ServiceDefaults",
    "IpfsDefaults",
    # Commands
    "CommandKeys",
    "CommandGroups",
    "ConfigKeys",
    "DefaultIncludedDirs",
    "DefaultExcludedDirs",
    "DefaultExcludedFiles",
    "CompletionKeys",
    # Storage
    "StorageEnvVars",
    "StoragePaths",
    "StorageDefaults",
    "StorageMessages",
    "StorageContentTypes",
    "StorachaBridgeCapabilities",
    "StorachaHTTPHeaders",
    # Scripts
    "ScriptLanguages",
    "ScriptExtensions",
    "ScriptCommentPrefixes",
    "ScriptMetadataKeys",
    "ScriptMetadataDefaults",
    "ShellTypes",
    "CommandTypes",
]
