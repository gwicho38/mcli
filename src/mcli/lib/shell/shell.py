import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcli.lib.logger.logger import get_logger, register_subprocess

logger = get_logger(__name__)


# Maximum command length to prevent memory issues
MAX_COMMAND_LENGTH = 100000


def shell_exec(script_path: str, function_name: str, *args) -> Dict[str, Any]:
    """Execute a shell script function with security checks and better error handling."""
    # Validate script path
    script_path = Path(script_path).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    # Prepare the full command with the shell script, function name, and arguments
    command = [str(script_path), function_name]
    result = {"success": False, "stdout": "", "stderr": ""}
    logger.info(f"Running command: {command}")
    try:
        # Run the shell script with the function name and arguments
        proc = subprocess.Popen(
            command + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Register the process for system monitoring
        register_subprocess(proc)

        # Wait for the process to complete and get output
        stdout, stderr = proc.communicate()

        # Check return code
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, command, stdout, stderr)

        # Store the result for later reference
        result = subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)

        # Output from the shell script
        if result.stdout:
            logger.info(f"Script output stdout:\n{result.stdout}")

        if result.stderr:
            logger.info(f"Script output stderr:\n{result.stderr}")
        # return output  # Should contain the "result" key with the list of files
    except subprocess.CalledProcessError as e:
        logger.info(f"Command failed with error: {e}")
        logger.info(f"Standard Output: {e.stdout}")
        logger.info(f"Error Output: {e.stderr}")
    except json.JSONDecodeError as e:
        logger.info(f"Failed to decode JSON: {e}")
        logger.info(f"Raw Output: {result.stdout.strip() if result else 'No output'}")
    return None


def get_shell_script_path(command: str, command_path: str):
    # Get the path to the shell script
    base_dir = os.path.dirname(os.path.realpath(command_path))
    scripts_path = f"{base_dir}/scripts/{command}.sh"
    return scripts_path


def shell_recurse(root_path):
    """
    Recursively applies a given function to all files in the directory tree starting from root_path.

    :param func: function, a function that takes a file path as its argument and executes on the file
    :param root_path: str, the root directory from which to start applying the function
    """
    # Check if the current root_path is a directory
    if os.path.isdir(root_path):
        # List all entries in the directory
        for entry in os.listdir(root_path):
            # Construct the full path
            full_path = os.path.join(root_path, entry)
            # Recursively apply the function if it's a directory
            shell_recurse(full_path, shell_exec)
    else:
        # If it's a file, apply the function
        shell_exec(root_path)


def is_executable_available(executable):
    return shutil.which(executable) is not None


def fatal_error(msg):
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
    """
    Execute an OS command and return stdout.

    SECURITY WARNING: This function uses shell=True when command is a string,
    which can be vulnerable to shell injection if the command contains
    unsanitized user input. Prefer using execute_command_safe() or pass
    command as a list of arguments.

    Args:
        command: Command to execute (string or list of args)
        fail_on_error: If True, call fatal_error on failure; else raise RuntimeError
        stdin: Optional string to pass to stdin
        timeout: Optional timeout in seconds

    Returns:
        stdout from the command

    Raises:
        RuntimeError: If command fails and fail_on_error is False
        ValueError: If command is empty or too long
    """
    # Input validation
    if not command:
        raise ValueError("Command cannot be empty")

    # Check for dangerous patterns in string commands
    use_shell = isinstance(command, str)

    if use_shell:
        # Validate command length
        if len(command) > MAX_COMMAND_LENGTH:
            raise ValueError(f"Command exceeds maximum length of {MAX_COMMAND_LENGTH}")

        # Check for null bytes (potential injection)
        if "\x00" in command:
            raise ValueError("Command contains null bytes")

        # Log warning for shell=True usage
        logger.debug("Executing shell command (shell=True): %s", _sanitize_for_log(command))
    else:
        logger.debug("Executing command: %s", command)

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
        msg = f"Command timed out after {timeout} seconds"
        if fail_on_error:
            fatal_error(msg)
        else:
            raise RuntimeError(msg)

    logger.debug("rc    > %s", process.returncode)
    if stdout:
        logger.debug("stdout> %s", stdout[:500] if len(stdout) > 500 else stdout)
    if stderr:
        logger.debug("stderr> %s", stderr[:500] if len(stderr) > 500 else stderr)

    if process.returncode:
        msg = f"Failed to execute command, error:\n{stdout}{stderr}"
        if fail_on_error:
            fatal_error(msg)
        else:
            raise RuntimeError(msg)

    return stdout


def execute_command_safe(
    args: List[str],
    fail_on_error: bool = True,
    stdin: Optional[str] = None,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> str:
    """
    Execute a command safely without shell interpolation.

    This is the preferred way to execute commands as it avoids shell injection
    vulnerabilities by not using shell=True.

    Args:
        args: List of command arguments (first element is the executable)
        fail_on_error: If True, call fatal_error on failure; else raise RuntimeError
        stdin: Optional string to pass to stdin
        timeout: Optional timeout in seconds
        cwd: Optional working directory
        env: Optional environment variables (merged with current env)

    Returns:
        stdout from the command

    Raises:
        RuntimeError: If command fails and fail_on_error is False
        ValueError: If args is empty
    """
    if not args:
        raise ValueError("Command arguments cannot be empty")

    logger.debug("Executing command safely: %s", args)

    # Merge environment if provided
    cmd_env = None
    if env:
        cmd_env = os.environ.copy()
        cmd_env.update(env)

    process = subprocess.Popen(
        args,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        cwd=cwd,
        env=cmd_env,
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
        msg = f"Command timed out after {timeout} seconds"
        if fail_on_error:
            fatal_error(msg)
        else:
            raise RuntimeError(msg)

    logger.debug("rc    > %s", process.returncode)
    if stdout:
        logger.debug("stdout> %s", stdout[:500] if len(stdout) > 500 else stdout)
    if stderr:
        logger.debug("stderr> %s", stderr[:500] if len(stderr) > 500 else stderr)

    if process.returncode:
        msg = f"Failed to execute command {args[0]}, error:\n{stdout}{stderr}"
        if fail_on_error:
            fatal_error(msg)
        else:
            raise RuntimeError(msg)

    return stdout


def _sanitize_for_log(command: str, max_length: int = 200) -> str:
    """Sanitize command string for safe logging, masking potential secrets."""
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


def cli_exec():
    pass
