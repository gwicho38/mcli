"""Shell command execution utilities.

This package provides robust command execution with:
- Custom exception hierarchy for different error types
- Structured result objects with full execution context
- Security validation and sanitization
- Timeout and resource cleanup
"""

from mcli.lib.shell.exceptions import (
    CommandError,
    CommandFailedError,
    CommandInterruptedError,
    CommandNotFoundError,
    CommandResourceError,
    CommandResult,
    CommandSecurityError,
    CommandTimeoutError,
    CommandValidationError,
)
from mcli.lib.shell.shell import (
    execute_command_safe,
    execute_command_with_result,
    execute_os_command,
    fatal_error,
    get_shell_script_path,
    is_executable_available,
    shell_exec,
)

__all__ = [
    # Exceptions
    "CommandError",
    "CommandFailedError",
    "CommandInterruptedError",
    "CommandNotFoundError",
    "CommandResourceError",
    "CommandSecurityError",
    "CommandTimeoutError",
    "CommandValidationError",
    # Result
    "CommandResult",
    # Functions
    "execute_command_safe",
    "execute_command_with_result",
    "execute_os_command",
    "fatal_error",
    "get_shell_script_path",
    "is_executable_available",
    "shell_exec",
]
