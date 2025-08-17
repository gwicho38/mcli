import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DiscoveredCommand:
    """Represents a discovered Click command"""

    name: str
    full_name: str  # e.g., "workflow.file.oxps_to_pdf"
    module_name: str
    group_name: Optional[str]
    description: str
    callback: callable
    is_group: bool = False
    subcommands: List[str] = None


class ClickCommandDiscovery:
    """Discovers all Click commands in the MCLI application"""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self.discovered_commands: Dict[str, DiscoveredCommand] = {}

    def discover_all_commands(self) -> List[DiscoveredCommand]:
        """Discover all Click commands in the application"""
        self.discovered_commands.clear()

        # Get the included directories from config
        from mcli.lib.toml.toml import read_from_toml

        config_paths = [Path("config.toml"), self.base_path.parent.parent / "config.toml"]

        included_dirs = ["workflow", "app", "self"]  # Default

        for config_path in config_paths:
            if config_path.exists():
                try:
                    config = read_from_toml(str(config_path), "paths")
                    if config and config.get("included_dirs"):
                        included_dirs = config["included_dirs"]
                        break
                except Exception as e:
                    logger.debug(f"Could not load config from {config_path}: {e}")

        logger.info(f"Discovering commands in directories: {included_dirs}")

        # Discover commands in each included directory
        for directory in included_dirs:
            self._discover_in_directory(directory)

        return list(self.discovered_commands.values())

    def _discover_in_directory(self, directory: str):
        """Discover commands in a specific directory"""
        if "/" in directory:
            # Handle nested paths like "workflow/daemon"
            parts = directory.split("/")
            search_path = self.base_path
            for part in parts:
                search_path = search_path / part
        else:
            search_path = self.base_path / directory

        if not search_path.exists():
            logger.debug(f"Directory {search_path} does not exist")
            return

        logger.debug(f"Searching for commands in: {search_path}")

        # Find all Python files
        for py_file in search_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                self._discover_in_file(py_file, directory)
            except Exception as e:
                logger.debug(f"Error discovering commands in {py_file}: {e}")

    def _discover_in_file(self, py_file: Path, base_directory: str):
        """Discover commands in a specific Python file"""
        # Convert file path to module name
        relative_path = py_file.relative_to(self.base_path.parent)
        module_name = str(relative_path).replace("/", ".").replace(".py", "")

        # Skip certain modules
        if any(skip in module_name for skip in ["test_", "__pycache__", ".pyc"]):
            return

        try:
            # Import the module
            if module_name not in sys.modules:
                module = importlib.import_module(module_name)
            else:
                module = sys.modules[module_name]

            # Find Click objects
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, click.Group):
                    self._register_group(obj, module_name, base_directory)
                elif isinstance(obj, click.Command):
                    self._register_command(obj, module_name, base_directory)

        except Exception as e:
            logger.debug(f"Could not import or inspect module {module_name}: {e}")

    def _register_group(self, group: click.Group, module_name: str, base_directory: str):
        """Register a Click group and its commands"""
        group_full_name = f"{base_directory}.{group.name}" if group.name else base_directory

        # Register the group itself
        group_cmd = DiscoveredCommand(
            name=group.name or "unnamed",
            full_name=group_full_name,
            module_name=module_name,
            group_name=None,
            description=group.help or "No description",
            callback=group.callback,
            is_group=True,
            subcommands=[],
        )

        self.discovered_commands[group_full_name] = group_cmd

        # Register all commands in the group
        for cmd_name, cmd in group.commands.items():
            cmd_full_name = f"{group_full_name}.{cmd_name}"

            command = DiscoveredCommand(
                name=cmd_name,
                full_name=cmd_full_name,
                module_name=module_name,
                group_name=group.name,
                description=cmd.help or "No description",
                callback=cmd.callback,
                is_group=isinstance(cmd, click.Group),
            )

            self.discovered_commands[cmd_full_name] = command
            group_cmd.subcommands.append(cmd_name)

            # If this command is also a group, recursively register its commands
            if isinstance(cmd, click.Group):
                self._register_group_recursive(cmd, cmd_full_name, module_name)

    def _register_command(self, command: click.Command, module_name: str, base_directory: str):
        """Register a standalone Click command"""
        cmd_full_name = f"{base_directory}.{command.name}" if command.name else base_directory

        cmd = DiscoveredCommand(
            name=command.name or "unnamed",
            full_name=cmd_full_name,
            module_name=module_name,
            group_name=None,
            description=command.help or "No description",
            callback=command.callback,
            is_group=False,
        )

        self.discovered_commands[cmd_full_name] = cmd

    def _register_group_recursive(self, group: click.Group, parent_name: str, module_name: str):
        """Recursively register nested group commands"""
        for cmd_name, cmd in group.commands.items():
            cmd_full_name = f"{parent_name}.{cmd_name}"

            command = DiscoveredCommand(
                name=cmd_name,
                full_name=cmd_full_name,
                module_name=module_name,
                group_name=group.name,
                description=cmd.help or "No description",
                callback=cmd.callback,
                is_group=isinstance(cmd, click.Group),
            )

            self.discovered_commands[cmd_full_name] = command

            if isinstance(cmd, click.Group):
                self._register_group_recursive(cmd, cmd_full_name, module_name)

    def get_commands(self, include_groups: bool = True) -> List[Dict[str, Any]]:
        """Get all discovered commands as dictionaries"""
        commands = []

        for cmd in self.discovered_commands.values():
            if not include_groups and cmd.is_group:
                continue

            command_dict = {
                "id": cmd.full_name,
                "name": cmd.name,
                "full_name": cmd.full_name,
                "description": cmd.description,
                "module": cmd.module_name,
                "group": cmd.group_name,
                "is_group": cmd.is_group,
                "language": "python",
                "tags": [cmd.group_name] if cmd.group_name else [],
                "is_active": True,
                "execution_count": 0,
                "created_at": None,
                "updated_at": None,
                "last_executed": None,
            }

            if cmd.subcommands:
                command_dict["subcommands"] = cmd.subcommands

            commands.append(command_dict)

        return sorted(commands, key=lambda x: x["full_name"])

    def search_commands(self, query: str) -> List[Dict[str, Any]]:
        """Search commands by name, description, or module"""
        query = query.lower()
        all_commands = self.get_commands()

        matching_commands = []
        for cmd in all_commands:
            if (
                query in cmd["name"].lower()
                or query in cmd["description"].lower()
                or query in cmd["module"].lower()
                or query in (cmd["group"] or "").lower()
            ):
                matching_commands.append(cmd)

        return matching_commands

    def get_command_by_name(self, name: str) -> Optional[DiscoveredCommand]:
        """Get a command by its name or full name"""
        # First try exact match by full name
        if name in self.discovered_commands:
            return self.discovered_commands[name]

        # Then try by short name
        for cmd in self.discovered_commands.values():
            if cmd.name == name:
                return cmd

        return None


# Global instance for caching
_discovery_instance = None


def get_command_discovery() -> ClickCommandDiscovery:
    """Get a cached command discovery instance"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = ClickCommandDiscovery()
        _discovery_instance.discover_all_commands()
    return _discovery_instance


def refresh_command_discovery():
    """Refresh the command discovery cache"""
    global _discovery_instance
    _discovery_instance = None
    return get_command_discovery()
