"""UI message constants for mcli.

This module defines all user-facing messages used throughout the mcli application.
Using these constants ensures consistency in user communication and makes
internationalization easier in the future.
"""


class ErrorMessages:
    """Error message constants."""

    EDITOR_NOT_FOUND = (
        "No editor found. Please set the EDITOR environment variable or install vim/nano."
    )
    CONFIG_NOT_FOUND = (
        "Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root."
    )
    COMMAND_NOT_FOUND = "Command '{name}' not found"
    COMMAND_NOT_AVAILABLE = "Command {name} is not available"
    GIT_COMMAND_FAILED = "Git command failed: {error}"
    FILE_NOT_FOUND = "File not found: {path}"
    DIRECTORY_NOT_FOUND = "Directory not found: {path}"
    INVALID_COMMAND_FORMAT = "Invalid command format"
    PERMISSION_DENIED = "Permission denied: {path}"
    NETWORK_ERROR = "Network error: {error}"
    API_ERROR = "API error: {error}"
    DATABASE_ERROR = "Database error: {error}"
    IMPORT_ERROR = "Failed to import: {module}"
    INVALID_CONFIG = "Invalid configuration: {error}"
    MISSING_REQUIRED_FIELD = "Missing required field: {field}"


class SuccessMessages:
    """Success message constants."""

    INITIALIZED_GIT_REPO = "Initialized git repository at {path}"
    COMMAND_STORE_INITIALIZED = "Command store initialized at {path}"
    CREATED_COMMAND = "Created portable custom command: {name}"
    SAVED_TO = "Saved to: {path}"
    UPDATED_SUCCESSFULLY = "Successfully updated {item}"
    DELETED_SUCCESSFULLY = "Successfully deleted {item}"
    COPIED_SUCCESSFULLY = "Successfully copied {source} to {dest}"
    INSTALLED_SUCCESSFULLY = "Successfully installed {item}"
    UNINSTALLED_SUCCESSFULLY = "Successfully uninstalled {item}"
    COMMAND_COMPLETED = "Command completed successfully"
    FILE_CREATED = "Created file: {path}"
    DIRECTORY_CREATED = "Created directory: {path}"


class WarningMessages:
    """Warning message constants."""

    NO_CHANGES = "No changes to commit"
    NO_REMOTE = "No remote configured or push failed. Commands committed locally."
    ALREADY_EXISTS = "{item} already exists"
    DEPRECATED_FEATURE = "{feature} is deprecated and will be removed in {version}"
    SKIPPED = "Skipped: {reason}"
    PARTIAL_SUCCESS = "Partially successful: {details}"
    RATE_LIMIT_WARNING = "Approaching rate limit for {service}"
    LARGE_FILE_WARNING = "Large file detected: {path} ({size})"


class InfoMessages:
    """Informational message constants."""

    COPYING_COMMANDS = "Copying commands from {source} to {dest}..."
    NO_CHANGES_TO_COMMIT = "No changes to commit"
    LOADING = "Loading {item}..."
    PROCESSING = "Processing {item}..."
    CONNECTING = "Connecting to {service}..."
    FETCHING = "Fetching {item}..."
    BUILDING = "Building {item}..."
    TESTING = "Testing {item}..."
    DEPLOYING = "Deploying {item}..."
    CLEANING = "Cleaning {item}..."
    ANALYZING = "Analyzing {item}..."
    VALIDATING = "Validating {item}..."


class PromptMessages:
    """User prompt constants."""

    CONFIRM_DELETE = "Are you sure you want to delete {item}?"
    CONFIRM_OVERWRITE = "File {path} already exists. Overwrite?"
    ENTER_VALUE = "Enter {field}:"
    SELECT_OPTION = "Select an option:"
    CONTINUE = "Continue?"


__all__ = [
    "ErrorMessages",
    "SuccessMessages",
    "WarningMessages",
    "InfoMessages",
    "PromptMessages",
]
