"""Custom exceptions for mcli.

This module defines a hierarchy of exceptions used throughout the mcli application.
Using specific exception types instead of generic errors or return codes makes
error handling more explicit and easier to test.

Exception Hierarchy:
    McliError (base)
    ├── CommandError (command-related errors)
    │   ├── InvalidCommandNameError
    │   ├── CommandNotFoundError
    │   ├── CommandAlreadyExistsError
    │   └── CommandExecutionError
    ├── ScriptError (script processing errors)
    │   ├── UnsupportedLanguageError
    │   ├── InvalidScriptError
    │   ├── ScriptParseError
    │   └── MetadataExtractionError
    ├── ValidationError (input validation errors)
    │   ├── InvalidGroupNameError
    │   └── InvalidFilePathError
    └── ConfigurationError (configuration errors)
        └── MissingConfigurationError

Example:
    from mcli.lib.errors import UnsupportedLanguageError, InvalidCommandNameError

    def process_script(path: Path, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            raise UnsupportedLanguageError(language, SUPPORTED_LANGUAGES)

        # ... process script
"""

from pathlib import Path
from typing import List, Optional, Union


class McliError(Exception):
    """Base exception for all mcli errors.

    All mcli-specific exceptions should inherit from this class.
    This allows catching all mcli errors with a single except clause.

    Attributes:
        message: Human-readable error message
        details: Optional additional details about the error
    """

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the error message with optional details."""
        if self.details:
            return f"{self.message}\n  Details: {self.details}"
        return self.message


# =============================================================================
# Command Errors
# =============================================================================


class CommandError(McliError):
    """Base exception for command-related errors."""

    pass


class InvalidCommandNameError(CommandError):
    """Raised when a command name is invalid.

    Command names must:
    - Start with a lowercase letter
    - Contain only lowercase letters, numbers, and underscores
    """

    def __init__(self, name: str, reason: Optional[str] = None) -> None:
        self.name = name
        message = f"Invalid command name: '{name}'"
        details = reason or (
            "Command names must start with a lowercase letter and contain only "
            "lowercase letters, numbers, and underscores."
        )
        super().__init__(message, details)


class CommandNotFoundError(CommandError):
    """Raised when a command cannot be found."""

    def __init__(self, name: str, searched_locations: Optional[List[str]] = None) -> None:
        self.name = name
        self.searched_locations = searched_locations or []
        message = f"Command not found: '{name}'"
        details = None
        if searched_locations:
            details = f"Searched in: {', '.join(searched_locations)}"
        super().__init__(message, details)


class CommandAlreadyExistsError(CommandError):
    """Raised when attempting to create a command that already exists."""

    def __init__(self, name: str, existing_path: Optional[Union[str, Path]] = None) -> None:
        self.name = name
        self.existing_path = existing_path
        message = f"Command already exists: '{name}'"
        details = f"Existing location: {existing_path}" if existing_path else None
        super().__init__(message, details)


class CommandExecutionError(CommandError):
    """Raised when a command fails to execute."""

    def __init__(
        self,
        name: str,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
    ) -> None:
        self.name = name
        self.exit_code = exit_code
        self.stderr = stderr
        message = f"Command execution failed: '{name}'"
        details_parts = []
        if exit_code is not None:
            details_parts.append(f"Exit code: {exit_code}")
        if stderr:
            details_parts.append(f"Error output: {stderr[:200]}")
        details = "; ".join(details_parts) if details_parts else None
        super().__init__(message, details)


# =============================================================================
# Script Errors
# =============================================================================


class ScriptError(McliError):
    """Base exception for script processing errors."""

    pass


class UnsupportedLanguageError(ScriptError):
    """Raised when a script language is not supported.

    Includes the list of supported languages in the error message
    for better user guidance.
    """

    def __init__(self, language: str, supported: Optional[List[str]] = None) -> None:
        self.language = language
        self.supported = supported or []
        message = f"Unsupported language: '{language}'"
        details = f"Supported languages: {', '.join(self.supported)}" if self.supported else None
        super().__init__(message, details)


class UnsupportedFileTypeError(ScriptError):
    """Raised when a file extension is not supported.

    Includes the list of supported extensions in the error message.
    """

    def __init__(self, extension: str, supported: Optional[List[str]] = None) -> None:
        self.extension = extension
        self.supported = supported or []
        message = f"Unsupported file type: '{extension}'"
        details = f"Supported extensions: {', '.join(self.supported)}" if self.supported else None
        super().__init__(message, details)


class InvalidScriptError(ScriptError):
    """Raised when a script file is invalid or malformed."""

    def __init__(self, path: Union[str, Path], reason: str) -> None:
        self.path = Path(path)
        self.reason = reason
        message = f"Invalid script: {self.path.name}"
        super().__init__(message, reason)


class ScriptParseError(ScriptError):
    """Raised when a script cannot be parsed."""

    def __init__(
        self,
        path: Union[str, Path],
        line_number: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> None:
        self.path = Path(path)
        self.line_number = line_number
        self.reason = reason
        message = f"Failed to parse script: {self.path.name}"
        details_parts = []
        if line_number:
            details_parts.append(f"Line {line_number}")
        if reason:
            details_parts.append(reason)
        details = ": ".join(details_parts) if details_parts else None
        super().__init__(message, details)


class MetadataExtractionError(ScriptError):
    """Raised when metadata cannot be extracted from a script."""

    def __init__(self, path: Union[str, Path], reason: str) -> None:
        self.path = Path(path)
        self.reason = reason
        message = f"Failed to extract metadata from: {self.path.name}"
        super().__init__(message, reason)


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(McliError):
    """Base exception for validation errors."""

    pass


class InvalidGroupNameError(ValidationError):
    """Raised when a group name is invalid."""

    def __init__(self, name: str, reason: Optional[str] = None) -> None:
        self.name = name
        message = f"Invalid group name: '{name}'"
        details = reason or (
            "Group names must start with a lowercase letter and contain only "
            "lowercase letters, numbers, and underscores."
        )
        super().__init__(message, details)


class InvalidFilePathError(ValidationError):
    """Raised when a file path is invalid or doesn't exist."""

    def __init__(self, path: Union[str, Path], reason: str) -> None:
        self.path = Path(path)
        message = f"Invalid file path: {self.path}"
        super().__init__(message, reason)


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(McliError):
    """Base exception for configuration errors."""

    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    def __init__(self, key: str, config_file: Optional[str] = None) -> None:
        self.key = key
        self.config_file = config_file
        message = f"Missing required configuration: '{key}'"
        details = f"Check configuration file: {config_file}" if config_file else None
        super().__init__(message, details)


__all__ = [
    # Base
    "McliError",
    # Command errors
    "CommandError",
    "InvalidCommandNameError",
    "CommandNotFoundError",
    "CommandAlreadyExistsError",
    "CommandExecutionError",
    # Script errors
    "ScriptError",
    "UnsupportedLanguageError",
    "UnsupportedFileTypeError",
    "InvalidScriptError",
    "ScriptParseError",
    "MetadataExtractionError",
    # Validation errors
    "ValidationError",
    "InvalidGroupNameError",
    "InvalidFilePathError",
    # Configuration errors
    "ConfigurationError",
    "MissingConfigurationError",
]
