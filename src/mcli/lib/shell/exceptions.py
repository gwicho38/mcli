"""Custom exceptions for shell command execution.

This module provides a hierarchy of specific exceptions for command execution,
replacing generic RuntimeError/ValueError with typed, informative exceptions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class CommandResult:
    """Structured result from command execution.

    Attributes:
        returncode: Process exit code (0 = success)
        stdout: Standard output (decoded string)
        stderr: Standard error (decoded string)
        command: The command that was executed
        timed_out: Whether the command timed out
        duration_ms: Execution duration in milliseconds (if tracked)
    """

    returncode: int
    stdout: str
    stderr: str
    command: Union[str, List[str]]
    timed_out: bool = False
    duration_ms: Optional[float] = None

    @property
    def success(self) -> bool:
        """Check if command succeeded (returncode == 0)."""
        return self.returncode == 0

    @property
    def output(self) -> str:
        """Get combined stdout and stderr."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "command": self.command if isinstance(self.command, str) else " ".join(self.command),
            "timed_out": self.timed_out,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


class CommandError(Exception):
    """Base exception for command execution errors.

    All command-related exceptions inherit from this, allowing callers
    to catch all command errors with a single except clause.

    Attributes:
        message: Human-readable error message
        command: The command that failed
        result: Optional CommandResult with full execution details
    """

    def __init__(
        self,
        message: str,
        command: Optional[Union[str, List[str]]] = None,
        result: Optional[CommandResult] = None,
    ):
        self.message = message
        self.command = command
        self.result = result
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the full error message with context."""
        parts = [self.message]

        if self.command:
            cmd_str = self.command if isinstance(self.command, str) else " ".join(self.command)
            # Truncate very long commands
            if len(cmd_str) > 200:
                cmd_str = cmd_str[:197] + "..."
            parts.append(f"Command: {cmd_str}")

        if self.result:
            parts.append(f"Exit code: {self.result.returncode}")
            if self.result.stderr:
                stderr_preview = self.result.stderr[:500]
                if len(self.result.stderr) > 500:
                    stderr_preview += "..."
                parts.append(f"Stderr: {stderr_preview}")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for structured logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "command": self.command,
            "result": self.result.to_dict() if self.result else None,
        }


class CommandNotFoundError(CommandError):
    """Raised when the command executable is not found."""

    def __init__(self, executable: str, search_path: Optional[str] = None):
        self.executable = executable
        self.search_path = search_path
        message = f"Command not found: {executable}"
        if search_path:
            message += f" (searched in: {search_path})"
        super().__init__(message, command=executable)


class CommandTimeoutError(CommandError):
    """Raised when command execution times out."""

    def __init__(
        self,
        timeout_seconds: float,
        command: Union[str, List[str]],
        result: Optional[CommandResult] = None,
    ):
        self.timeout_seconds = timeout_seconds
        message = f"Command timed out after {timeout_seconds} seconds"
        # Create result if not provided
        if result is None:
            result = CommandResult(
                returncode=-1,
                stdout="",
                stderr="",
                command=command,
                timed_out=True,
            )
        super().__init__(message, command=command, result=result)


class CommandFailedError(CommandError):
    """Raised when command exits with non-zero status."""

    def __init__(
        self,
        result: CommandResult,
        expected_returncode: int = 0,
    ):
        self.expected_returncode = expected_returncode
        message = f"Command failed with exit code {result.returncode}"
        if result.stderr:
            # Include first line of stderr in message
            first_line = result.stderr.split("\n")[0]
            if len(first_line) > 100:
                first_line = first_line[:97] + "..."
            message += f": {first_line}"
        super().__init__(message, command=result.command, result=result)


class CommandValidationError(CommandError):
    """Raised when command validation fails before execution."""

    def __init__(self, message: str, command: Optional[Union[str, List[str]]] = None):
        super().__init__(message, command=command)


class CommandSecurityError(CommandValidationError):
    """Raised when command contains potentially dangerous patterns."""

    def __init__(
        self,
        message: str,
        command: Union[str, List[str]],
        dangerous_pattern: Optional[str] = None,
    ):
        self.dangerous_pattern = dangerous_pattern
        if dangerous_pattern:
            message = f"{message} (pattern: {dangerous_pattern})"
        super().__init__(message, command=command)


class CommandInterruptedError(CommandError):
    """Raised when command is interrupted by a signal."""

    def __init__(
        self,
        signal_num: int,
        command: Union[str, List[str]],
        result: Optional[CommandResult] = None,
    ):
        self.signal_num = signal_num
        # Map common signals to names
        signal_names = {
            2: "SIGINT",
            9: "SIGKILL",
            15: "SIGTERM",
        }
        signal_name = signal_names.get(signal_num, f"signal {signal_num}")
        message = f"Command interrupted by {signal_name}"
        super().__init__(message, command=command, result=result)


class CommandResourceError(CommandError):
    """Raised when command fails due to resource constraints."""

    def __init__(
        self,
        resource_type: str,
        details: str,
        command: Optional[Union[str, List[str]]] = None,
    ):
        self.resource_type = resource_type
        message = f"Resource error ({resource_type}): {details}"
        super().__init__(message, command=command)
