import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.lib.logger.logger import get_logger, register_subprocess

logger = get_logger(__name__)


def shell_exec(script_path: str, function_name: str, *args) -> Dict[str, Any]:
    """Execute a shell script function with security checks and better error handling"""
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


def execute_os_command(command, fail_on_error=True, stdin=None):
    logger.debug("Executing command '%s'", command)
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    # Register the process for system monitoring
    register_subprocess(process)

    if stdin is not None:
        stdin = stdin.encode()
    stdout, stderr = [stream.decode().strip() for stream in process.communicate(input=stdin)]

    logger.debug("rc    > %s", process.returncode)
    if stdout:
        logger.debug("stdout> %s", stdout)
    if stderr:
        logger.debug("stderr> %s", stderr)

    if process.returncode:
        msg = f'Failed to execute command "{command}", error:\n{stdout}{stderr}'
        if fail_on_error:
            fatal_error(msg)
        else:
            raise RuntimeError(msg)

    return stdout


def cli_exec():
    pass
