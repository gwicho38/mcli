"""
Input validation for scheduler job commands.

Provides validation and sanitization for job configurations
to prevent accidental mistakes and improve security posture.
"""

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


# Dangerous command patterns that warrant warnings
DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\s+-rf\s+[/~]"), "Recursive delete on root or home directory"),
    (re.compile(r"\brm\s+-rf\s+/\s*$"), "Recursive delete of root filesystem"),
    (re.compile(r"\bdd\s+.*of=/dev/"), "Direct disk write operation"),
    (re.compile(r"\bmkfs\b"), "Filesystem formatting command"),
    (re.compile(r">\s*/dev/sd[a-z]"), "Direct write to block device"),
    (re.compile(r"\bchmod\s+-R\s+777\b"), "Overly permissive chmod -R 777"),
    (re.compile(r"\bchown\s+-R\s+.*\s+/\s*$"), "Recursive chown on root"),
    (re.compile(r":\(\)\{.*\}"), "Potential fork bomb pattern"),
    (re.compile(r"\beval\s+"), "Use of eval (potential code injection)"),
    (re.compile(r"\$\(.*\).*\|.*sh\b"), "Command substitution piped to shell"),
    (re.compile(r"`.*`.*\|.*sh\b"), "Backtick expansion piped to shell"),
]

# Environment variable patterns
ENV_VAR_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Maximum command length (prevent memory issues with huge commands)
MAX_COMMAND_LENGTH = 100000

# Maximum environment variable value length
MAX_ENV_VALUE_LENGTH = 32768


def validate_job_command(
    command: str,
    job_type: str = "command",
    strict: bool = False,
) -> ValidationResult:
    """
    Validate a job command for potential issues.

    Args:
        command: The command string to validate
        job_type: Type of job (command, python, etc.)
        strict: If True, warnings become errors

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(valid=True)

    # Check for empty command
    if not command or not command.strip():
        result.add_error("Command cannot be empty")
        return result

    # Check command length
    if len(command) > MAX_COMMAND_LENGTH:
        result.add_error(f"Command exceeds maximum length of {MAX_COMMAND_LENGTH} characters")
        return result

    # Check for null bytes (potential injection)
    if "\x00" in command:
        result.add_error("Command contains null bytes")
        return result

    # Check for dangerous patterns
    for pattern, description in DANGEROUS_PATTERNS:
        if pattern.search(command):
            message = f"Dangerous pattern detected: {description}"
            if strict:
                result.add_error(message)
            else:
                result.add_warning(message)

    # Job type specific validation
    if job_type == "python":
        result.merge(_validate_python_code(command))
    elif job_type == "api_call":
        result.merge(_validate_api_call_config(command))

    return result


def _validate_python_code(code: str) -> ValidationResult:
    """Validate Python code for obvious issues."""
    result = ValidationResult(valid=True)

    # Check for common dangerous patterns in Python
    dangerous_python_patterns = [
        (re.compile(r"\bos\.system\s*\("), "os.system() usage - prefer subprocess"),
        (re.compile(r"\beval\s*\("), "eval() usage - potential code injection"),
        (re.compile(r"\bexec\s*\("), "exec() usage - potential code injection"),
        (re.compile(r"\b__import__\s*\("), "__import__() usage - dynamic import"),
        (
            re.compile(r"\bopen\s*\([^)]*,\s*['\"]w['\"]"),
            "Writing to files without path validation",
        ),
    ]

    for pattern, description in dangerous_python_patterns:
        if pattern.search(code):
            result.add_warning(f"Python code warning: {description}")

    return result


def _validate_api_call_config(config_str: str) -> ValidationResult:
    """Validate API call configuration."""
    result = ValidationResult(valid=True)

    import json

    try:
        config = json.loads(config_str)
        if not isinstance(config, dict):
            result.add_error("API call config must be a JSON object")
            return result

        # Check for required fields
        if "url" not in config:
            result.add_error("API call config missing 'url' field")

        # Validate URL format
        url = config.get("url", "")
        if url and not url.startswith(("http://", "https://")):
            result.add_warning("API URL should use http:// or https:// scheme")

    except json.JSONDecodeError as e:
        result.add_error(f"API call config is not valid JSON: {e}")

    return result


def validate_working_directory(working_dir: Optional[str]) -> ValidationResult:
    """
    Validate a working directory path.

    Args:
        working_dir: The working directory path to validate

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(valid=True)

    if working_dir is None:
        return result

    # Check for empty string
    if not working_dir.strip():
        result.add_error("Working directory cannot be an empty string")
        return result

    # Expand user and resolve path
    try:
        path = Path(working_dir).expanduser().resolve()
    except Exception as e:
        result.add_error(f"Invalid path format: {e}")
        return result

    # Check if path exists
    if not path.exists():
        result.add_warning(f"Working directory does not exist: {path}")
    elif not path.is_dir():
        result.add_error(f"Working directory is not a directory: {path}")

    # Check for write permissions (if it exists)
    if path.exists() and not os.access(path, os.W_OK):
        result.add_warning(f"No write permission for working directory: {path}")

    return result


def validate_environment(environment: Optional[dict]) -> ValidationResult:
    """
    Validate environment variables dictionary.

    Args:
        environment: Dictionary of environment variables

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(valid=True)

    if environment is None:
        return result

    if not isinstance(environment, dict):
        result.add_error("Environment must be a dictionary")
        return result

    for key, value in environment.items():
        # Validate key format
        if not isinstance(key, str):
            result.add_error(f"Environment variable name must be a string: {key}")
            continue

        if not ENV_VAR_NAME_PATTERN.match(key):
            result.add_error(
                f"Invalid environment variable name '{key}': "
                "must start with letter or underscore, contain only alphanumeric and underscores"
            )

        # Validate value
        if not isinstance(value, (str, int, float, bool)):
            result.add_warning(
                f"Environment variable '{key}' has non-string value, will be converted"
            )

        # Check value length
        str_value = str(value)
        if len(str_value) > MAX_ENV_VALUE_LENGTH:
            result.add_error(
                f"Environment variable '{key}' value exceeds maximum length of {MAX_ENV_VALUE_LENGTH}"
            )

        # Check for null bytes
        if "\x00" in str_value:
            result.add_error(f"Environment variable '{key}' contains null bytes")

    return result


def validate_cron_expression(cron_expr: str) -> ValidationResult:
    """
    Validate a cron expression format.

    Args:
        cron_expr: The cron expression to validate

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(valid=True)

    if not cron_expr or not cron_expr.strip():
        result.add_error("Cron expression cannot be empty")
        return result

    cron_expr = cron_expr.strip()

    # Handle special expressions
    special_expressions = {
        "@reboot",
        "@yearly",
        "@annually",
        "@monthly",
        "@weekly",
        "@daily",
        "@hourly",
    }
    if cron_expr.lower() in special_expressions:
        return result

    # Standard cron has 5 fields, extended has 6 (with seconds)
    parts = cron_expr.split()
    if len(parts) < 5:
        result.add_error(f"Cron expression has too few fields: expected 5, got {len(parts)}")
    elif len(parts) > 6:
        result.add_error(f"Cron expression has too many fields: expected 5-6, got {len(parts)}")

    # Basic field validation
    cron_field_pattern = re.compile(r"^[\d\*\-,/]+$")
    for i, part in enumerate(parts[:5] if len(parts) >= 5 else parts):
        if not cron_field_pattern.match(part):
            result.add_warning(f"Cron field {i + 1} has unusual characters: {part}")

    return result


def validate_job_name(name: str) -> ValidationResult:
    """
    Validate a job name.

    Args:
        name: The job name to validate

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(valid=True)

    if not name or not name.strip():
        result.add_error("Job name cannot be empty")
        return result

    # Check length
    if len(name) > 255:
        result.add_error("Job name exceeds maximum length of 255 characters")

    # Check for problematic characters
    if "\x00" in name:
        result.add_error("Job name contains null bytes")

    # Warn about names that might cause issues
    if name.startswith("."):
        result.add_warning("Job name starts with dot, may be treated as hidden")

    if any(c in name for c in "/\\:"):
        result.add_warning("Job name contains path separators, may cause filesystem issues")

    return result


def validate_job_config(
    name: str,
    cron_expression: str,
    command: str,
    job_type: str = "command",
    working_directory: Optional[str] = None,
    environment: Optional[dict] = None,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate a complete job configuration.

    Args:
        name: Job name
        cron_expression: Cron schedule
        command: Command to execute
        job_type: Type of job
        working_directory: Optional working directory
        environment: Optional environment variables
        strict: If True, warnings become errors

    Returns:
        ValidationResult with all errors and warnings
    """
    result = ValidationResult(valid=True)

    # Validate each component
    result.merge(validate_job_name(name))
    result.merge(validate_cron_expression(cron_expression))
    result.merge(validate_job_command(command, job_type, strict))
    result.merge(validate_working_directory(working_directory))
    result.merge(validate_environment(environment))

    return result


def sanitize_command_for_logging(command: str, max_length: int = 200) -> str:
    """
    Sanitize a command string for safe logging.

    Truncates long commands and masks potential secrets.

    Args:
        command: The command to sanitize
        max_length: Maximum length before truncation

    Returns:
        Sanitized command string
    """
    if not command:
        return "<empty>"

    # Mask potential secrets (simple pattern matching)
    secret_patterns = [
        (re.compile(r"(password|passwd|pwd|secret|token|key|api_key)\s*=\s*\S+", re.I), r"\1=****"),
        (re.compile(r"(Bearer|Basic)\s+\S+", re.I), r"\1 ****"),
    ]

    sanitized = command
    for pattern, replacement in secret_patterns:
        sanitized = pattern.sub(replacement, sanitized)

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[: max_length - 3] + "..."

    return sanitized
