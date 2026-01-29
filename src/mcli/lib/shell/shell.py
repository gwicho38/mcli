"""Shell command execution utilities with robust error handling.

This module provides functions for executing shell commands with:
- Typed exceptions for different error conditions
- Structured result objects
- Security validation
- Resource cleanup
- Timeout handling
"""

import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcli.lib.logger.logger import get_logger, register_subprocess
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

logger = get_logger(__name__)


# Maximum command length to prevent memory issues
MAX_COMMAND_LENGTH = 100000


def shell_exec(script_path: str, function_name: str, *args) -> Optional[Dict[str, Any]]:
    """Execute a shell script function with security checks and better error handling.

    Args:
        script_path: Path to the shell script
        function_name: Name of the function to execute
        *args: Arguments to pass to the function

    Returns:
        Dictionary with execution result or None on failure

    Raises:
        CommandNotFoundError: If script doesn't exist
        CommandFailedError: If script execution fails
    """
    # Validate script path
    script_path_obj = Path(script_path).resolve()
    if not script_path_obj.exists():
        raise CommandNotFoundError(str(script_path_obj))

    # Prepare the full command with the shell script, function name, and arguments
    command = [str(script_path_obj), function_name] + list(args)
    logger.info(f"Running command: {command}")

    start_time = time.monotonic()

    try:
        # Run the shell script with the function name and arguments
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Register the process for system monitoring
        register_subprocess(proc)

        # Wait for the process to complete and get output
        stdout, stderr = proc.communicate()

        duration_ms = (time.monotonic() - start_time) * 1000

        result = CommandResult(
            returncode=proc.returncode,
            stdout=stdout.strip() if stdout else "",
            stderr=stderr.strip() if stderr else "",
            command=command,
            duration_ms=duration_ms,
        )

        # Check return code
        if proc.returncode != 0:
            raise CommandFailedError(result)

        # Output from the shell script
        if result.stdout:
            logger.info(f"Script output stdout:\n{result.stdout}")

        if result.stderr:
            logger.info(f"Script output stderr:\n{result.stderr}")

        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}

    except CommandError:
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e}")
        logger.error(f"Standard Output: {e.stdout}")
        logger.error(f"Error Output: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON: {e}")
        return None
    except OSError as e:
        # Handle OS-level errors (file not found, permission denied, etc.)
        raise CommandResourceError("os", str(e), command)


def get_shell_script_path(command: str, command_path: str) -> str:
    """Get the path to a shell script.

    Args:
        command: Name of the command/script
        command_path: Base path for the command module

    Returns:
        Full path to the shell script
    """
    # Get the path to the shell script
    base_dir = os.path.dirname(os.path.realpath(command_path))
    scripts_path = f"{base_dir}/scripts/{command}.sh"
    return scripts_path


def shell_recurse(root_path: str) -> None:
    """Recursively apply shell_exec to all files in a directory tree.

    Args:
        root_path: The root directory to start from
    """
    # Check if the current root_path is a directory
    if os.path.isdir(root_path):
        # List all entries in the directory
        for entry in os.listdir(root_path):
            # Construct the full path
            full_path = os.path.join(root_path, entry)
            # Recursively apply the function if it's a directory
            shell_recurse(full_path)
    else:
        # If it's a file, apply the function
        shell_exec(root_path, "")


def is_executable_available(executable: str) -> bool:
    """Check if an executable is available in PATH.

    Args:
        executable: Name of the executable to find

    Returns:
        True if executable is found, False otherwise
    """
    return shutil.which(executable) is not None


def fatal_error(msg: str) -> None:
    """Log a critical error and exit the application.

    Args:
        msg: Error message to log
    """
    logger.critical(msg + " Unable to recover from the error, exiting.")
    if not logger.isEnabledFor(logging.DEBUG):
        logger.error(
            "Debug output may help you to fix this issue or will be useful for maintainers of this tool."
            " Please try to rerun tool with `-d` flag to enable debug output"
        )
    sys.exit(1)


def execute_os_command(
    command: Union[str, List[str]],
    fail_on_error: bool = True,
    stdin: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Execute an OS command and return stdout.

    SECURITY WARNING: This function uses shell=True when command is a string,
    which can be vulnerable to shell injection if the command contains
    unsanitized user input. Prefer using execute_command_safe() or pass
    command as a list of arguments.

    Args:
        command: Command to execute (string or list of args)
        fail_on_error: If True, call fatal_error on failure; else raise exception
        stdin: Optional string to pass to stdin
        timeout: Optional timeout in seconds

    Returns:
        stdout from the command

    Raises:
        CommandValidationError: If command is empty or invalid
        CommandSecurityError: If command contains dangerous patterns
        CommandTimeoutError: If command times out
        CommandFailedError: If command fails and fail_on_error is False
    """
    # Input validation
    if not command:
        raise CommandValidationError("Command cannot be empty")

    # Check for dangerous patterns in string commands
    use_shell = isinstance(command, str)

    if use_shell:
        # Validate command length
        if len(command) > MAX_COMMAND_LENGTH:
            raise CommandValidationError(
                f"Command exceeds maximum length of {MAX_COMMAND_LENGTH}",
                command=command,
            )

        # Check for null bytes (potential injection)
        if "\x00" in command:
            raise CommandSecurityError(
                "Command contains null bytes",
                command=command,
                dangerous_pattern="\\x00",
            )

        # Log warning for shell=True usage
        logger.debug("Executing shell command (shell=True): %s", _sanitize_for_log(command))
    else:
        logger.debug("Executing command: %s", command)

    start_time = time.monotonic()

    process = subprocess.Popen(
        command,
        shell=use_shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    # Register the process for system monitoring
    register_subprocess(process)

    stdin_bytes = stdin.encode() if stdin is not None else None

    try:
        stdout_bytes, stderr_bytes = process.communicate(input=stdin_bytes, timeout=timeout)
        stdout = stdout_bytes.decode().strip()
        stderr = stderr_bytes.decode().strip()
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()  # Clean up
        error = CommandTimeoutError(timeout or 0, command)
        if fail_on_error:
            fatal_error(str(error))
        else:
            raise error

    duration_ms = (time.monotonic() - start_time) * 1000

    logger.debug("rc    > %s", process.returncode)
    if stdout:
        logger.debug("stdout> %s", stdout[:500] if len(stdout) > 500 else stdout)
    if stderr:
        logger.debug("stderr> %s", stderr[:500] if len(stderr) > 500 else stderr)

    if process.returncode:
        # Check if process was killed by signal
        if process.returncode < 0:
            signal_num = -process.returncode
            error = CommandInterruptedError(signal_num, command)
            if fail_on_error:
                fatal_error(str(error))
            else:
                raise error

        result = CommandResult(
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            command=command,
            duration_ms=duration_ms,
        )
        error = CommandFailedError(result)
        if fail_on_error:
            fatal_error(str(error))
        else:
            raise error

    return stdout


def execute_command_safe(
    args: List[str],
    fail_on_error: bool = True,
    stdin: Optional[str] = None,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    check_executable: bool = True,
) -> str:
    """Execute a command safely without shell interpolation.

    This is the preferred way to execute commands as it avoids shell injection
    vulnerabilities by not using shell=True.

    Args:
        args: List of command arguments (first element is the executable)
        fail_on_error: If True, call fatal_error on failure; else raise exception
        stdin: Optional string to pass to stdin
        timeout: Optional timeout in seconds
        cwd: Optional working directory
        env: Optional environment variables (merged with current env)
        check_executable: If True, verify executable exists before running

    Returns:
        stdout from the command

    Raises:
        CommandValidationError: If args is empty
        CommandNotFoundError: If executable is not found
        CommandTimeoutError: If command times out
        CommandFailedError: If command fails and fail_on_error is False
    """
    if not args:
        raise CommandValidationError("Command arguments cannot be empty")

    executable = args[0]

    # Optionally check if executable exists
    if check_executable and not shutil.which(executable):
        raise CommandNotFoundError(executable)

    logger.debug("Executing command safely: %s", args)

    # Merge environment if provided
    cmd_env = None
    if env:
        cmd_env = os.environ.copy()
        cmd_env.update(env)

    start_time = time.monotonic()

    try:
        process = subprocess.Popen(
            args,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            cwd=cwd,
            env=cmd_env,
        )
    except FileNotFoundError:
        raise CommandNotFoundError(executable)
    except PermissionError:
        raise CommandResourceError("permission", f"Permission denied: {executable}", args)
    except OSError as e:
        raise CommandResourceError("os", str(e), args)

    # Register the process for system monitoring
    register_subprocess(process)

    stdin_bytes = stdin.encode() if stdin is not None else None

    try:
        stdout_bytes, stderr_bytes = process.communicate(input=stdin_bytes, timeout=timeout)
        stdout = stdout_bytes.decode().strip()
        stderr = stderr_bytes.decode().strip()
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()  # Clean up
        error = CommandTimeoutError(timeout or 0, args)
        if fail_on_error:
            fatal_error(str(error))
        else:
            raise error

    duration_ms = (time.monotonic() - start_time) * 1000

    logger.debug("rc    > %s", process.returncode)
    if stdout:
        logger.debug("stdout> %s", stdout[:500] if len(stdout) > 500 else stdout)
    if stderr:
        logger.debug("stderr> %s", stderr[:500] if len(stderr) > 500 else stderr)

    if process.returncode:
        # Check if process was killed by signal
        if process.returncode < 0:
            signal_num = -process.returncode
            error = CommandInterruptedError(signal_num, args)
            if fail_on_error:
                fatal_error(str(error))
            else:
                raise error

        result = CommandResult(
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            command=args,
            duration_ms=duration_ms,
        )
        error = CommandFailedError(result)
        if fail_on_error:
            fatal_error(str(error))
        else:
            raise error

    return stdout


def execute_command_with_result(
    args: List[str],
    stdin: Optional[str] = None,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> CommandResult:
    """Execute a command and return structured result (never raises on non-zero exit).

    Use this when you need to inspect the result regardless of success/failure,
    rather than having exceptions raised.

    Args:
        args: List of command arguments (first element is the executable)
        stdin: Optional string to pass to stdin
        timeout: Optional timeout in seconds
        cwd: Optional working directory
        env: Optional environment variables (merged with current env)

    Returns:
        CommandResult with full execution details

    Raises:
        CommandValidationError: If args is empty
        CommandTimeoutError: If command times out
    """
    if not args:
        raise CommandValidationError("Command arguments cannot be empty")

    logger.debug("Executing command with result: %s", args)

    # Merge environment if provided
    cmd_env = None
    if env:
        cmd_env = os.environ.copy()
        cmd_env.update(env)

    start_time = time.monotonic()

    try:
        process = subprocess.Popen(
            args,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            cwd=cwd,
            env=cmd_env,
        )
    except FileNotFoundError:
        return CommandResult(
            returncode=127,  # Standard "command not found" exit code
            stdout="",
            stderr=f"Command not found: {args[0]}",
            command=args,
        )
    except OSError as e:
        return CommandResult(
            returncode=126,  # Standard "command not executable" exit code
            stdout="",
            stderr=str(e),
            command=args,
        )

    # Register the process for system monitoring
    register_subprocess(process)

    stdin_bytes = stdin.encode() if stdin is not None else None

    try:
        stdout_bytes, stderr_bytes = process.communicate(input=stdin_bytes, timeout=timeout)
        stdout = stdout_bytes.decode().strip()
        stderr = stderr_bytes.decode().strip()
        timed_out = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_bytes, stderr_bytes = process.communicate()  # Clean up
        stdout = stdout_bytes.decode().strip() if stdout_bytes else ""
        stderr = stderr_bytes.decode().strip() if stderr_bytes else ""
        timed_out = True

    duration_ms = (time.monotonic() - start_time) * 1000

    return CommandResult(
        returncode=process.returncode if not timed_out else -1,
        stdout=stdout,
        stderr=stderr,
        command=args,
        timed_out=timed_out,
        duration_ms=duration_ms,
    )


def _sanitize_for_log(command: str, max_length: int = 200) -> str:
    """Sanitize command string for safe logging, masking potential secrets.

    Args:
        command: The command string to sanitize
        max_length: Maximum length of output

    Returns:
        Sanitized command string safe for logging
    """
    import re

    if not command:
        return "<empty>"

    # Mask potential secrets
    patterns = [
        (re.compile(r"(password|passwd|pwd|secret|token|key|api_key)\s*=\s*\S+", re.I), r"\1=****"),
        (re.compile(r"(Bearer|Basic)\s+\S+", re.I), r"\1 ****"),
    ]

    sanitized = command
    for pattern, replacement in patterns:
        sanitized = pattern.sub(replacement, sanitized)

    if len(sanitized) > max_length:
        sanitized = sanitized[: max_length - 3] + "..."

    return sanitized


def cli_exec() -> None:
    """CLI execution entry point (placeholder)."""
    pass
