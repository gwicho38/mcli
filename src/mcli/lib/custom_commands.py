"""
Custom command storage and loading for mcli (Legacy JSON Format).

DEPRECATION NOTICE:
This module handles legacy JSON-based commands. New commands should be created
as native script files (.py, .sh, .js, .ts, .ipynb) using `mcli new -l <language>`.

The new native script system is in `mcli.lib.script_loader.ScriptLoader`.

Migration:
- Use `mcli workflow migrate` to convert JSON files to native scripts
- JSON files will continue to work but are deprecated

This module provides functionality to store user-created commands in a portable
format in ~/.mcli/commands/ and automatically load them at startup.
"""

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import click

from mcli.lib.logger.logger import get_logger, register_subprocess
from mcli.lib.paths import (
    get_custom_commands_dir,
    get_git_root,
    get_lockfile_path,
    is_git_repository,
)

logger = get_logger()


class CustomCommandManager:
    """Manages custom user commands stored in JSON format."""

    def __init__(self, global_mode: bool = False):
        """
        Initialize the custom command manager.

        Args:
            global_mode: If True, use global commands directory (~/.mcli/commands/).
                        If False, use local directory (.mcli/commands/) when in a git repository.
        """
        self.global_mode = global_mode
        self.commands_dir = get_custom_commands_dir(global_mode=global_mode)
        self.loaded_commands: dict[str, Any] = {}
        self.lockfile_path = get_lockfile_path(global_mode=global_mode)

        # Store context information for display
        self.is_local = not global_mode and is_git_repository()
        self.git_root = get_git_root() if self.is_local else None

    def save_command(
        self,
        name: str,
        code: str,
        description: str = "",
        group: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        language: str = "python",
        shell: Optional[str] = None,
    ) -> Path:
        """
        Save a custom command to the commands directory.

        Args:
            name: Command name
            code: Python code or shell script for the command
            description: Command description
            group: Optional command group
            metadata: Additional metadata
            language: Command language ("python" or "shell")
            shell: Shell type for shell commands (bash, zsh, fish, sh)

        Returns:
            Path to the saved command file
        """
        command_data = {
            "name": name,
            "code": code,
            "description": description,
            "group": group,
            "language": language,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "metadata": metadata or {},
        }

        # Add shell type for shell commands
        if language == "shell":
            command_data["shell"] = shell or os.environ.get("SHELL", "bash").split("/")[-1]

        # Save as JSON file
        command_file = self.commands_dir / f"{name}.json"
        with open(command_file, "w") as f:
            json.dump(command_data, f, indent=2)

        logger.info(f"Saved custom command: {name} to {command_file}")

        # Update lockfile
        self.update_lockfile()

        return command_file

    def load_command(self, command_file: Path) -> Optional[dict[str, Any]]:
        """
        Load a command from a JSON or notebook file.

        Args:
            command_file: Path to the command JSON file or .ipynb notebook

        Returns:
            Command data dictionary or None if loading failed
        """
        try:
            with open(command_file) as f:
                command_data = json.load(f)

            # If it's a notebook file (.ipynb), convert it to command metadata
            if command_file.suffix == ".ipynb":
                # Get file modification time for timestamps
                from datetime import datetime

                stat = command_file.stat()
                updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
                created_at = datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z"

                # Notebooks are handled specially - create minimal metadata
                return {
                    "name": command_file.stem,
                    "description": f"Jupyter notebook: {command_file.stem}",
                    "type": "notebook",
                    "file": str(command_file),
                    "group": "workflow",
                    "version": "1.0",
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "metadata": {
                        "notebook_format": True,
                        "source_file": str(command_file),
                    },
                }

            return dict(command_data)  # Cast json.load result to dict
        except Exception as e:
            logger.error(f"Failed to load command from {command_file}: {e}")
            return None

    def load_all_commands(self) -> list[dict[str, Any]]:
        """
        Load all custom commands from the commands directory.

        Automatically filters out test commands (starting with 'test_' or 'test-')
        unless MCLI_INCLUDE_TEST_COMMANDS=true is set.

        Scans for both .json workflow definitions and .ipynb notebook files.

        Returns:
            List of command data dictionaries
        """
        commands = []
        include_test = os.environ.get("MCLI_INCLUDE_TEST_COMMANDS", "false").lower() == "true"

        # Load .json workflow files
        for command_file in self.commands_dir.glob("*.json"):
            # Skip the lockfile
            if command_file.name == "commands.lock.json":
                continue

            # Skip test commands unless explicitly included
            if not include_test and command_file.stem.startswith(("test_", "test-")):
                logger.debug(f"Skipping test command: {command_file.name}")
                continue

            command_data = self.load_command(command_file)
            if command_data:
                commands.append(command_data)

        # Load .ipynb notebook files
        for notebook_file in self.commands_dir.glob("*.ipynb"):
            # Skip test notebooks unless explicitly included
            if not include_test and notebook_file.stem.startswith(("test_", "test-")):
                logger.debug(f"Skipping test notebook: {notebook_file.name}")
                continue

            # Load notebook as a command
            command_data = self.load_command(notebook_file)
            if command_data:
                commands.append(command_data)

        return commands

    def delete_command(self, name: str) -> bool:
        """
        Delete a custom command.

        Args:
            name: Command name

        Returns:
            True if deleted successfully, False otherwise
        """
        command_file = self.commands_dir / f"{name}.json"
        if command_file.exists():
            command_file.unlink()
            logger.info(f"Deleted custom command: {name}")
            self.update_lockfile()  # Update lockfile after deletion
            return True
        return False

    def generate_lockfile(self) -> dict[str, Any]:
        """
        Generate a lockfile containing metadata about all custom commands.

        Returns:
            Dictionary containing lockfile data
        """
        commands = self.load_all_commands()

        commands_dict: dict[str, Any] = {}
        lockfile_data: dict[str, Any] = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "commands": commands_dict,
        }

        for command_data in commands:
            name = command_data["name"]
            commands_dict[name] = {
                "name": name,
                "description": command_data.get("description", ""),
                "group": command_data.get("group"),
                "version": command_data.get("version", "1.0"),
                "created_at": command_data.get("created_at", ""),
                "updated_at": command_data.get("updated_at", ""),
            }

        return lockfile_data

    def update_lockfile(self) -> bool:
        """
        Update the lockfile with current command state.

        Returns:
            True if successful, False otherwise
        """
        try:
            lockfile_data = self.generate_lockfile()
            with open(self.lockfile_path, "w") as f:
                json.dump(lockfile_data, f, indent=2)
            logger.debug(f"Updated lockfile: {self.lockfile_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to update lockfile: {e}")
            return False

    def load_lockfile(self) -> Optional[dict[str, Any]]:
        """
        Load the lockfile.

        Returns:
            Lockfile data dictionary or None if not found
        """
        if not self.lockfile_path.exists():
            return None

        try:
            with open(self.lockfile_path) as f:
                return dict(json.load(f))  # Cast json.load result to dict
        except Exception as e:
            logger.error(f"Failed to load lockfile: {e}")
            return None

    def verify_lockfile(self) -> dict[str, Any]:
        """
        Verify that the current command state matches the lockfile.

        Returns:
            Dictionary with verification results:
            - 'valid': bool indicating if lockfile is valid
            - 'missing': list of commands in lockfile but not in filesystem
            - 'extra': list of commands in filesystem but not in lockfile
            - 'modified': list of commands with different metadata
        """
        missing: list[str] = []
        extra: list[str] = []
        modified: list[str] = []
        result: dict[str, Any] = {
            "valid": True,
            "missing": missing,
            "extra": extra,
            "modified": modified,
        }

        lockfile_data = self.load_lockfile()
        if not lockfile_data:
            result["valid"] = False
            return result

        current_commands = {cmd["name"]: cmd for cmd in self.load_all_commands()}
        lockfile_commands = lockfile_data.get("commands", {})

        # Check for missing commands (in lockfile but not in filesystem)
        for name in lockfile_commands:
            if name not in current_commands:
                missing.append(name)
                result["valid"] = False

        # Check for extra commands (in filesystem but not in lockfile)
        for name in current_commands:
            if name not in lockfile_commands:
                extra.append(name)
                result["valid"] = False

        # Check for modified commands (different metadata)
        for name in set(current_commands.keys()) & set(lockfile_commands.keys()):
            current = current_commands[name]
            locked = lockfile_commands[name]

            if current.get("updated_at") != locked.get("updated_at"):
                modified.append(name)
                result["valid"] = False

        return result

    def register_command_with_click(
        self, command_data: dict[str, Any], target_group: click.Group
    ) -> bool:
        """
        Dynamically register a custom command with a Click group.

        Args:
            command_data: Command data dictionary
            target_group: Click group to register the command with

        Returns:
            True if successful, False otherwise
        """
        try:
            name = command_data["name"]
            code = command_data["code"]

            # Create a temporary module to execute the command code
            module_name = f"mcli_custom_{name}"

            # Create a temporary file to store the code
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            try:
                # Load the module from the temporary file
                spec = importlib.util.spec_from_file_location(module_name, temp_file_path)
                if not spec or not spec.loader:
                    logger.warning(f"Could not load spec for custom command: {name}")
                    return False

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Look for a command or command group in the module
                # Prioritize Groups over Commands to handle commands with subcommands correctly
                command_obj: Optional[Union[click.Command, click.Group]] = None
                found_commands: list[click.Command] = []

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, click.Group):
                        # Found a group - this takes priority
                        command_obj = attr
                        break
                    elif isinstance(attr, click.Command):
                        # Store command for fallback
                        found_commands.append(attr)

                # If no group found, use the first command
                if not command_obj and found_commands:
                    command_obj = found_commands[0]

                if command_obj:
                    # Register with the target group
                    target_group.add_command(command_obj, name=name)
                    self.loaded_commands[name] = command_obj
                    logger.info(f"Registered custom command: {name}")
                    return True
                else:
                    logger.warning(f"No Click command found in custom command: {name}")
                    return False
            finally:
                # Clean up temporary file
                Path(temp_file_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Failed to register custom command {name}: {e}")
            return False

    def register_shell_command_with_click(
        self, command_data: dict[str, Any], target_group: click.Group
    ) -> bool:
        """
        Dynamically register a shell command with a Click group.

        Args:
            command_data: Command data dictionary
            target_group: Click group to register the command with

        Returns:
            True if successful, False otherwise
        """
        try:
            name = command_data["name"]
            code = command_data["code"]
            shell_type = command_data.get("shell", "bash")
            description = command_data.get("description", "Shell command")

            # Create a Click command wrapper for the shell script
            def create_shell_command(script_code: str, shell: str, cmd_name: str):
                """Factory function to create shell command wrapper."""

                @click.command(name=cmd_name, help=description)
                @click.argument("args", nargs=-1)
                @click.pass_context
                def shell_command(ctx, args):
                    """Execute shell script command."""
                    # Create temporary script file
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".sh", delete=False, prefix=f"mcli_{cmd_name}_"
                    ) as temp_file:
                        # Add shebang if not present
                        if not script_code.strip().startswith("#!"):
                            temp_file.write(f"#!/usr/bin/env {shell}\n")
                        temp_file.write(script_code)
                        temp_file_path = temp_file.name

                    try:
                        # Make script executable
                        os.chmod(temp_file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

                        # Execute the shell script
                        logger.info(f"Executing shell command: {cmd_name}")
                        process = subprocess.Popen(
                            [temp_file_path] + list(args),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            env={**os.environ, "MCLI_COMMAND": cmd_name},
                        )

                        # Register for monitoring
                        register_subprocess(process)

                        # Wait and capture output
                        stdout, stderr = process.communicate()

                        # Print output
                        if stdout:
                            click.echo(stdout, nl=False)
                        if stderr:
                            click.echo(stderr, nl=False, err=True)

                        # Exit with same code as script
                        if process.returncode != 0:
                            logger.warning(
                                f"Shell command {cmd_name} exited with code {process.returncode}"
                            )
                            ctx.exit(process.returncode)

                    except Exception as e:
                        logger.error(f"Failed to execute shell command {cmd_name}: {e}")
                        click.echo(f"Error executing shell command: {e}", err=True)
                        ctx.exit(1)
                    finally:
                        # Clean up temporary file
                        try:  # noqa: SIM105
                            Path(temp_file_path).unlink(missing_ok=True)
                        except Exception:
                            pass

                return shell_command

            # Create the command
            command_obj = create_shell_command(code, shell_type, name)

            # Register with the target group
            target_group.add_command(command_obj, name=name)
            self.loaded_commands[name] = command_obj
            logger.info(f"Registered shell command: {name} (shell: {shell_type})")
            return True

        except Exception as e:
            logger.error(f"Failed to register shell command {name}: {e}")
            return False

    def register_notebook_command_with_click(
        self, notebook_file: Path, target_group: click.Group
    ) -> bool:
        """
        Dynamically register a notebook file as a Click group with subcommands.

        This loads a Jupyter notebook (.ipynb) file and extracts all Click commands
        defined in its cells, creating a command group.

        Args:
            notebook_file: Path to the notebook file
            target_group: Click group to register the notebook commands with

        Returns:
            True if successful, False otherwise
        """
        try:
            from mcli.workflow.notebook.command_loader import NotebookCommandLoader

            # Get group name from notebook file stem (filename without extension)
            group_name = notebook_file.stem

            logger.info(f"Loading notebook commands from {notebook_file}")

            # Load the notebook and create a command group
            notebook_group = NotebookCommandLoader.load_group_from_file(
                notebook_file, group_name=group_name
            )

            if not notebook_group:
                logger.warning(f"No commands found in notebook: {notebook_file}")
                return False

            # Register the group with the target
            target_group.add_command(notebook_group, name=group_name)
            self.loaded_commands[group_name] = notebook_group
            logger.info(f"Registered notebook command group: {group_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register notebook {notebook_file.name}: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return False

    def export_commands(self, export_path: Path) -> bool:
        """
        Export all custom commands to a single JSON file.

        Args:
            export_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            commands = self.load_all_commands()
            with open(export_path, "w") as f:
                json.dump(commands, f, indent=2)
            logger.info(f"Exported {len(commands)} commands to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export commands: {e}")
            return False

    def import_commands(self, import_path: Path, overwrite: bool = False) -> dict[str, bool]:
        """
        Import commands from a JSON file.

        Args:
            import_path: Path to import file
            overwrite: Whether to overwrite existing commands

        Returns:
            Dictionary mapping command names to success status
        """
        results = {}
        try:
            with open(import_path) as f:
                commands = json.load(f)

            for command_data in commands:
                name = command_data["name"]
                command_file = self.commands_dir / f"{name}.json"

                if command_file.exists() and not overwrite:
                    logger.warning(f"Command {name} already exists, skipping")
                    results[name] = False
                    continue

                # Update timestamp
                command_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

                with open(command_file, "w") as f:
                    json.dump(command_data, f, indent=2)

                results[name] = True
                logger.info(f"Imported command: {name}")

            return results
        except Exception as e:
            logger.error(f"Failed to import commands: {e}")
            return results


# Global and local instances
_global_command_manager: Optional[CustomCommandManager] = None
_local_command_manager: Optional[CustomCommandManager] = None


def get_command_manager(global_mode: bool = False) -> CustomCommandManager:
    """
    Get the custom command manager instance.

    Args:
        global_mode: If True, return global manager. If False, return local
            manager (if in git repo).

    Returns:
        CustomCommandManager instance for the appropriate scope
    """
    global _global_command_manager, _local_command_manager

    if global_mode:
        if _global_command_manager is None:
            _global_command_manager = CustomCommandManager(global_mode=True)
        return _global_command_manager
    else:
        # Use local manager if in git repository
        if is_git_repository():
            # Recreate local manager if git root changed (e.g., changed directory)
            if _local_command_manager is None or _local_command_manager.git_root != get_git_root():
                _local_command_manager = CustomCommandManager(global_mode=False)
            return _local_command_manager
        else:
            # Fallback to global manager when not in a git repository
            if _global_command_manager is None:
                _global_command_manager = CustomCommandManager(global_mode=True)
            return _global_command_manager


def has_legacy_json_commands(global_mode: bool = False) -> bool:
    """
    Check if there are legacy JSON command files that need migration.

    Args:
        global_mode: If True, check global directory. If False, check local.

    Returns:
        True if there are JSON command files, False otherwise
    """
    commands_dir = get_custom_commands_dir(global_mode=global_mode)
    if not commands_dir.exists():
        return False

    for json_file in commands_dir.glob("*.json"):
        # Skip lockfiles
        if json_file.name in ("commands.lock.json", "workflows.lock.json", ".sync_cache.json"):
            continue
        return True
    return False


def load_custom_commands(target_group: click.Group) -> int:
    """
    Load all custom commands and register them with the target Click group.

    DEPRECATED: This function loads legacy JSON commands. New code should use
    ScriptLoader.register_all_commands() for native script files.

    Args:
        target_group: Click group to register commands with

    Returns:
        Number of commands successfully loaded
    """
    manager = get_command_manager()
    commands = manager.load_all_commands()

    if not commands:
        return 0

    # Log deprecation warning if JSON commands are found
    logger.debug(
        "Loading legacy JSON commands. Consider migrating to native scripts "
        "with 'mcli workflow migrate'"
    )

    loaded_count = 0
    for command_data in commands:
        # Check if command should be nested under a group
        group_name = command_data.get("group")
        language = command_data.get("language", "python")

        if group_name:
            # Find or create the group
            group_cmd = target_group.commands.get(group_name)

            # Handle LazyGroup - force loading
            if group_cmd and hasattr(group_cmd, "_load_group"):
                logger.debug(f"Loading lazy group: {group_name}")
                group_cmd = group_cmd._load_group()
                # Update the command in the parent group
                target_group.commands[group_name] = group_cmd

            if not group_cmd:
                # Create the group if it doesn't exist
                group_cmd = click.Group(name=group_name, help=f"{group_name.capitalize()} commands")
                target_group.add_command(group_cmd)
                logger.info(f"Created command group: {group_name}")

            # Register the command under the group based on type/language
            if isinstance(group_cmd, click.Group):
                command_type = command_data.get("type", "")
                if command_type == "notebook":
                    # Handle notebook commands
                    notebook_file = Path(command_data["file"])
                    success = manager.register_notebook_command_with_click(notebook_file, group_cmd)
                elif language == "shell":
                    success = manager.register_shell_command_with_click(command_data, group_cmd)
                else:
                    success = manager.register_command_with_click(command_data, group_cmd)

                if success:
                    loaded_count += 1
        else:
            # Register at top level based on type/language
            command_type = command_data.get("type", "")
            if command_type == "notebook":
                # Handle notebook commands
                notebook_file = Path(command_data["file"])
                success = manager.register_notebook_command_with_click(notebook_file, target_group)
            elif language == "shell":
                success = manager.register_shell_command_with_click(command_data, target_group)
            else:
                success = manager.register_command_with_click(command_data, target_group)

            if success:
                loaded_count += 1

    if loaded_count > 0:
        logger.info(f"Loaded {loaded_count} legacy JSON commands")

    return loaded_count
