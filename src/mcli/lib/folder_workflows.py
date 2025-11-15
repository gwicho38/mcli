"""
Folder-based workflow system for mcli.

This module provides support for organizing workflows in folder hierarchies where:
- Folders become command groups
- Scripts inside folders become subcommands
- Language auto-detected from shebang/extension

Example structure:
    .mcli/workflows/
    ├── cheese/
    │   ├── cheddar.py    # mcli run cheese cheddar
    │   └── gouda.sh      # mcli run cheese gouda
    └── bread/
        └── sourdough.sh  # mcli run bread sourdough
"""

import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


def detect_script_language(script_path: Path) -> Tuple[str, Optional[str]]:
    """
    Detect the language of a script file.

    Detection priority:
    1. Shebang line (highest priority)
    2. File extension
    3. Default to Python

    Args:
        script_path: Path to the script file

    Returns:
        Tuple of (language, shell_type)
        - language: "python" or "shell"
        - shell_type: "bash", "zsh", "fish", "sh", or None for Python
    """
    # Check shebang first
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

            if first_line.startswith("#!"):
                shebang = first_line[2:].strip()

                # Check for Python
                if "python" in shebang.lower():
                    return ("python", None)

                # Check for various shells
                if "bash" in shebang.lower():
                    return ("shell", "bash")
                if "zsh" in shebang.lower():
                    return ("shell", "zsh")
                if "fish" in shebang.lower():
                    return ("shell", "fish")
                if shebang.endswith("/sh") or "sh" in shebang:
                    return ("shell", "sh")
    except (OSError, UnicodeDecodeError) as e:
        logger.debug(f"Could not read shebang from {script_path}: {e}")

    # Fallback to extension
    ext = script_path.suffix.lower()

    if ext == ".py":
        return ("python", None)
    if ext in [".sh", ".bash"]:
        return ("shell", "bash")
    if ext == ".zsh":
        return ("shell", "zsh")
    if ext == ".fish":
        return ("shell", "fish")

    # Default to Python if unknown
    logger.debug(f"No shebang or recognized extension for {script_path}, defaulting to Python")
    return ("python", None)


def extract_help_text(script_path: Path, language: str) -> str:
    """
    Extract help text from a script.

    For Python: Extracts module-level docstring
    For Shell: Extracts comments at top of file (after shebang)

    Args:
        script_path: Path to the script file
        language: "python" or "shell"

    Returns:
        Help text string, or generic message if none found
    """
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if language == "python":
            # Look for module-level docstring
            in_docstring = False
            docstring_lines = []
            quote_char = None

            for line in lines:
                stripped = line.strip()

                # Skip shebang and comments
                if stripped.startswith("#"):
                    continue

                # Found start of docstring
                if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
                    quote_char = '"""' if stripped.startswith('"""') else "'''"
                    in_docstring = True

                    # Check if it's a one-line docstring
                    if stripped.endswith(quote_char) and len(stripped) > 6:
                        return stripped[3:-3].strip()

                    # Multi-line docstring
                    docstring_lines.append(stripped[3:])
                    continue

                # Inside docstring
                if in_docstring:
                    if stripped.endswith(quote_char):
                        # End of docstring
                        docstring_lines.append(stripped[:-3])
                        return "\n".join(docstring_lines).strip()
                    else:
                        docstring_lines.append(line.rstrip())

                # If we hit code before finding docstring, stop
                if not in_docstring and stripped and not stripped.startswith("#"):
                    break

        else:  # shell
            # Extract comments from top of file (after shebang)
            comment_lines = []
            started = False

            for line in lines:
                stripped = line.strip()

                # Skip shebang
                if stripped.startswith("#!"):
                    continue

                # Found comment
                if stripped.startswith("#"):
                    started = True
                    # Remove leading # and whitespace
                    comment_text = stripped[1:].strip()
                    if comment_text:  # Skip empty comment lines
                        comment_lines.append(comment_text)

                # Stop at first non-comment, non-empty line after comments started
                elif started and stripped:
                    break

            if comment_lines:
                return "\n".join(comment_lines)

    except (OSError, UnicodeDecodeError) as e:
        logger.debug(f"Could not extract help text from {script_path}: {e}")

    # Default help text
    return f"Execute {script_path.stem} script"


def is_valid_script_file(path: Path) -> bool:
    """
    Check if a path is a valid script file.

    Valid scripts:
    - Must be a file (not directory)
    - Must not start with . (hidden files)
    - Must not be __pycache__ or other special files
    - Must have reasonable size (< 10MB)

    Args:
        path: Path to check

    Returns:
        True if valid script file
    """
    if not path.is_file():
        return False

    if path.name.startswith("."):
        return False

    if path.name in ["__pycache__", "__init__.py", "README.md", "LICENSE"]:
        return False

    # Check file size (skip very large files)
    try:
        if path.stat().st_size > 10 * 1024 * 1024:  # 10MB
            logger.warning(f"Skipping {path}: file too large (> 10MB)")
            return False
    except OSError:
        return False

    return True


def make_script_executable(script_path: Path) -> bool:
    """
    Make a script executable by adding execute permission.

    Args:
        script_path: Path to the script

    Returns:
        True if successful or already executable
    """
    try:
        current_permissions = script_path.stat().st_mode
        # Add execute permission for owner
        new_permissions = current_permissions | stat.S_IXUSR
        if current_permissions != new_permissions:
            script_path.chmod(new_permissions)
            logger.debug(f"Made {script_path} executable")
        return True
    except OSError as e:
        logger.warning(f"Could not make {script_path} executable: {e}")
        return False


def create_python_script_command(cmd_name: str, script_path: Path, help_text: str) -> click.Command:
    """
    Create a Click command that executes a Python script.

    Uses subprocess for isolation and safety.

    Args:
        cmd_name: Name of the command
        script_path: Path to the Python script
        help_text: Help text for the command

    Returns:
        Click Command object
    """

    @click.command(name=cmd_name, help=help_text, context_settings={"ignore_unknown_options": True})
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def script_cmd(ctx, args):
        """Execute Python script as subprocess."""
        try:
            # Build command
            cmd = [sys.executable, str(script_path)] + list(args)

            logger.debug(f"Executing Python script: {' '.join(cmd)}")

            # Execute script
            result = subprocess.run(
                cmd,
                capture_output=False,  # Stream output directly
                text=True,
                cwd=script_path.parent,  # Run in script's directory
            )

            # Exit with script's return code (only if non-zero)
            if result.returncode != 0:
                ctx.exit(result.returncode)

        except Exception as e:
            click.echo(f"Error executing {script_path}: {e}", err=True)
            logger.error(f"Failed to execute {script_path}: {e}")
            ctx.exit(1)

    return script_cmd


def create_shell_script_command(
    cmd_name: str, script_path: Path, shell_type: str, help_text: str
) -> click.Command:
    """
    Create a Click command that executes a shell script.

    Uses subprocess for execution.

    Args:
        cmd_name: Name of the command
        script_path: Path to the shell script
        shell_type: Type of shell (bash, zsh, fish, sh)
        help_text: Help text for the command

    Returns:
        Click Command object
    """

    @click.command(name=cmd_name, help=help_text, context_settings={"ignore_unknown_options": True})
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def script_cmd(ctx, args):
        """Execute shell script as subprocess."""
        try:
            # Make script executable
            make_script_executable(script_path)

            # Build command
            cmd = [str(script_path)] + list(args)

            logger.debug(f"Executing shell script: {' '.join(cmd)}")

            # Set environment variable for script name
            env = os.environ.copy()
            env["MCLI_COMMAND"] = cmd_name
            env["MCLI_SCRIPT_PATH"] = str(script_path)

            # Execute script
            result = subprocess.run(
                cmd,
                capture_output=False,  # Stream output directly
                text=True,
                cwd=script_path.parent,  # Run in script's directory
                env=env,
                shell=False,  # Don't use shell, execute directly
            )

            # Exit with script's return code (only if non-zero)
            if result.returncode != 0:
                ctx.exit(result.returncode)

        except Exception as e:
            click.echo(f"Error executing {script_path}: {e}", err=True)
            logger.error(f"Failed to execute {script_path}: {e}")
            ctx.exit(1)

    return script_cmd


def scan_standalone_workflows(workflows_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Scan for standalone workflow scripts at the top level of workflows directory.

    Returns dictionary mapping script names to their metadata:
        {
            "image-convert": {
                "path": Path(...),
                "language": "python",
                "shell": None,
                "help": "..."
            }
        }
    """
    if not workflows_dir.exists() or not workflows_dir.is_dir():
        return {}

    standalone_scripts = {}

    try:
        for item in workflows_dir.iterdir():
            # Only process files (not directories or JSON files)
            if not is_valid_script_file(item):
                continue

            # Skip JSON files (handled by JSON command system)
            if item.suffix.lower() == ".json":
                continue

            # Detect language
            language, shell_type = detect_script_language(item)

            # Extract help text
            help_text = extract_help_text(item, language)

            # Command name is the filename without extension
            cmd_name = item.stem

            # Store command info
            standalone_scripts[cmd_name] = {
                "path": item,
                "language": language,
                "shell": shell_type,
                "help": help_text,
            }

            logger.debug(
                f"Found standalone workflow: {cmd_name} "
                f"({language}{f'/{shell_type}' if shell_type else ''})"
            )

    except OSError as e:
        logger.error(f"Error scanning standalone workflows in {workflows_dir}: {e}")

    return standalone_scripts


def scan_folder_workflows(workflows_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Scan a workflows directory for folder-based workflows.

    Folder structure:
        workflows_dir/
        ├── group1/
        │   ├── script1.py
        │   └── script2.sh
        └── group2/
            └── script3.py

    Returns:
        {
            "group1": {
                "commands": {
                    "script1": {
                        "path": Path(...),
                        "language": "python",
                        "shell": None,
                        "help": "..."
                    },
                    "script2": {
                        "path": Path(...),
                        "language": "shell",
                        "shell": "bash",
                        "help": "..."
                    }
                }
            }
        }
    """
    if not workflows_dir.exists() or not workflows_dir.is_dir():
        return {}

    folder_groups = {}

    try:
        for item in workflows_dir.iterdir():
            # Only process directories (not JSON files or other files)
            if not item.is_dir():
                continue

            # Skip hidden directories
            if item.name.startswith("."):
                continue

            # Skip special directories
            if item.name in ["__pycache__", ".git"]:
                continue

            # Found a potential command group folder
            group_name = item.name
            group_commands = {}

            # Scan folder for scripts
            for script_file in item.iterdir():
                if not is_valid_script_file(script_file):
                    continue

                # Detect language
                language, shell_type = detect_script_language(script_file)

                # Extract help text
                help_text = extract_help_text(script_file, language)

                # Command name is the filename without extension
                cmd_name = script_file.stem

                # Store command info
                group_commands[cmd_name] = {
                    "path": script_file,
                    "language": language,
                    "shell": shell_type,
                    "help": help_text,
                }

                logger.debug(
                    f"Found folder workflow: {group_name}/{cmd_name} "
                    f"({language}{f'/{shell_type}' if shell_type else ''})"
                )

            # Only add group if it has commands
            if group_commands:
                folder_groups[group_name] = {"commands": group_commands}
                logger.info(
                    f"Loaded folder group '{group_name}' with {len(group_commands)} commands"
                )

    except OSError as e:
        logger.error(f"Error scanning folder workflows in {workflows_dir}: {e}")

    return folder_groups


def create_folder_command_group(group_name: str, commands: Dict[str, Any]) -> click.Group:
    """
    Create a Click command group from a folder of scripts.

    Args:
        group_name: Name of the command group (folder name)
        commands: Dictionary of command info from scan_folder_workflows

    Returns:
        Click Group with registered subcommands
    """
    # Create the group
    group = click.Group(
        name=group_name,
        help=f"Commands from {group_name}/ folder",
    )

    # Register each script as a subcommand
    for cmd_name, cmd_info in commands.items():
        try:
            if cmd_info["language"] == "python":
                cmd = create_python_script_command(
                    cmd_name,
                    cmd_info["path"],
                    cmd_info["help"],
                )
            else:  # shell
                cmd = create_shell_script_command(
                    cmd_name,
                    cmd_info["path"],
                    cmd_info["shell"] or "bash",
                    cmd_info["help"],
                )

            group.add_command(cmd)
            logger.debug(f"Registered {group_name}/{cmd_name} as Click command")

        except Exception as e:
            logger.error(f"Failed to register {group_name}/{cmd_name}: {e}")
            continue

    return group
