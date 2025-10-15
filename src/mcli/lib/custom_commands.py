"""
Custom command storage and loading for mcli.

This module provides functionality to store user-created commands in a portable
format in ~/.mcli/commands/ and automatically load them at startup.
"""

import importlib.util
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir

logger = get_logger()


class CustomCommandManager:
    """Manages custom user commands stored in JSON format."""

    def __init__(self):
        self.commands_dir = get_custom_commands_dir()
        self.loaded_commands: Dict[str, Any] = {}
        self.lockfile_path = self.commands_dir / "commands.lock.json"

    def save_command(
        self,
        name: str,
        code: str,
        description: str = "",
        group: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Save a custom command to the commands directory.

        Args:
            name: Command name
            code: Python code for the command
            description: Command description
            group: Optional command group
            metadata: Additional metadata

        Returns:
            Path to the saved command file
        """
        command_data = {
            "name": name,
            "code": code,
            "description": description,
            "group": group,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "metadata": metadata or {},
        }

        # Save as JSON file
        command_file = self.commands_dir / f"{name}.json"
        with open(command_file, "w") as f:
            json.dump(command_data, f, indent=2)

        logger.info(f"Saved custom command: {name} to {command_file}")

        # Update lockfile
        self.update_lockfile()

        return command_file

    def load_command(self, command_file: Path) -> Optional[Dict[str, Any]]:
        """
        Load a command from a JSON file.

        Args:
            command_file: Path to the command JSON file

        Returns:
            Command data dictionary or None if loading failed
        """
        try:
            with open(command_file, "r") as f:
                command_data = json.load(f)
            return command_data
        except Exception as e:
            logger.error(f"Failed to load command from {command_file}: {e}")
            return None

    def load_all_commands(self) -> List[Dict[str, Any]]:
        """
        Load all custom commands from the commands directory.

        Returns:
            List of command data dictionaries
        """
        commands = []
        for command_file in self.commands_dir.glob("*.json"):
            # Skip the lockfile
            if command_file.name == "commands.lock.json":
                continue

            command_data = self.load_command(command_file)
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

    def generate_lockfile(self) -> Dict[str, Any]:
        """
        Generate a lockfile containing metadata about all custom commands.

        Returns:
            Dictionary containing lockfile data
        """
        commands = self.load_all_commands()

        lockfile_data = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "commands": {},
        }

        for command_data in commands:
            name = command_data["name"]
            lockfile_data["commands"][name] = {
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

    def load_lockfile(self) -> Optional[Dict[str, Any]]:
        """
        Load the lockfile.

        Returns:
            Lockfile data dictionary or None if not found
        """
        if not self.lockfile_path.exists():
            return None

        try:
            with open(self.lockfile_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load lockfile: {e}")
            return None

    def verify_lockfile(self) -> Dict[str, Any]:
        """
        Verify that the current command state matches the lockfile.

        Returns:
            Dictionary with verification results:
            - 'valid': bool indicating if lockfile is valid
            - 'missing': list of commands in lockfile but not in filesystem
            - 'extra': list of commands in filesystem but not in lockfile
            - 'modified': list of commands with different metadata
        """
        result = {
            "valid": True,
            "missing": [],
            "extra": [],
            "modified": [],
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
                result["missing"].append(name)
                result["valid"] = False

        # Check for extra commands (in filesystem but not in lockfile)
        for name in current_commands:
            if name not in lockfile_commands:
                result["extra"].append(name)
                result["valid"] = False

        # Check for modified commands (different metadata)
        for name in set(current_commands.keys()) & set(lockfile_commands.keys()):
            current = current_commands[name]
            locked = lockfile_commands[name]

            if current.get("updated_at") != locked.get("updated_at"):
                result["modified"].append(name)
                result["valid"] = False

        return result

    def register_command_with_click(
        self, command_data: Dict[str, Any], target_group: click.Group
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
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Look for a command or command group in the module
                    # Prioritize Groups over Commands to handle commands with subcommands correctly
                    command_obj = None
                    found_commands = []

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

    def import_commands(self, import_path: Path, overwrite: bool = False) -> Dict[str, bool]:
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
            with open(import_path, "r") as f:
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


# Global instance
_command_manager: Optional[CustomCommandManager] = None


def get_command_manager() -> CustomCommandManager:
    """Get the global custom command manager instance."""
    global _command_manager
    if _command_manager is None:
        _command_manager = CustomCommandManager()
    return _command_manager


def load_custom_commands(target_group: click.Group) -> int:
    """
    Load all custom commands and register them with the target Click group.

    Args:
        target_group: Click group to register commands with

    Returns:
        Number of commands successfully loaded
    """
    manager = get_command_manager()
    commands = manager.load_all_commands()

    loaded_count = 0
    for command_data in commands:
        # Check if command should be nested under a group
        group_name = command_data.get("group")

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

            # Register the command under the group
            if isinstance(group_cmd, click.Group):
                if manager.register_command_with_click(command_data, group_cmd):
                    loaded_count += 1
        else:
            # Register at top level
            if manager.register_command_with_click(command_data, target_group):
                loaded_count += 1

    if loaded_count > 0:
        logger.info(f"Loaded {loaded_count} custom commands")

    return loaded_count
