"""
Notebook command loader for dynamically creating CLI commands from notebook cells.

This module extracts Click command decorators from notebook cells and creates
a Click group with all the commands as subcommands.
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from mcli.lib.logger.logger import get_logger
from mcli.workflow.notebook.converter import WorkflowConverter
from mcli.workflow.notebook.schema import CellType, WorkflowNotebook

logger = get_logger(__name__)


class NotebookCommandLoader:
    """Load Click commands from notebook cells."""

    def __init__(self, notebook: WorkflowNotebook):
        """
        Initialize the command loader.

        Args:
            notebook: WorkflowNotebook instance
        """
        self.notebook = notebook
        self.globals_dict: Dict[str, Any] = {}

    def _is_command_cell(self, source: str) -> bool:
        """
        Check if a cell contains a Click command decorator.

        Args:
            source: Cell source code

        Returns:
            True if cell contains @click.command or @command decorator
        """
        # Look for @click.command(), @command(), or similar decorators
        patterns = [
            r"@click\.command\(",
            r"@click\.group\(",
            r"@command\(",
            r"@group\(",
        ]

        for pattern in patterns:
            if re.search(pattern, source):
                return True

        return False

    def _extract_function_name(self, source: str) -> Optional[str]:
        """
        Extract the function name from a cell with a command decorator.

        Args:
            source: Cell source code

        Returns:
            Function name or None if not found
        """
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has decorators
                    for decorator in node.decorator_list:
                        decorator_name = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                        if "command" in decorator_name or "group" in decorator_name:
                            return node.name
        except SyntaxError:
            logger.warning(f"Failed to parse cell for function name")

        return None

    def _execute_setup_cells(self) -> None:
        """
        Execute all cells before command definitions to set up imports and context.

        This ensures that when we execute command cells, all necessary imports
        and helper functions are available.
        """
        for cell in self.notebook.cells:
            if cell.cell_type != CellType.CODE:
                continue

            source = cell.source_text

            # Skip command definition cells
            if self._is_command_cell(source):
                continue

            # Execute setup code
            try:
                exec(source, self.globals_dict)
                logger.debug(f"Executed setup cell")
            except Exception as e:
                logger.warning(f"Failed to execute setup cell: {e}")

    def _load_command_from_cell(self, source: str) -> Optional[click.Command]:
        """
        Load a Click command from a cell's source code.

        Args:
            source: Cell source code

        Returns:
            Click Command object or None if failed
        """
        try:
            # Ensure click is imported
            if "click" not in self.globals_dict:
                self.globals_dict["click"] = click

            # Execute the cell to define the command
            exec(source, self.globals_dict)

            # Extract function name
            func_name = self._extract_function_name(source)
            if not func_name:
                logger.warning("Could not extract function name from command cell")
                return None

            # Get the command object
            cmd = self.globals_dict.get(func_name)
            if not cmd:
                logger.warning(f"Function {func_name} not found in globals after execution")
                return None

            # Verify it's a Click command
            if not isinstance(cmd, (click.Command, click.Group)):
                logger.warning(f"Function {func_name} is not a Click command")
                return None

            logger.info(f"Loaded command: {func_name}")
            return cmd

        except Exception as e:
            logger.error(f"Failed to load command from cell: {e}")
            return None

    def extract_commands(self) -> List[Tuple[str, click.Command]]:
        """
        Extract all Click commands from the notebook.

        Returns:
            List of (command_name, command) tuples
        """
        commands = []

        # First, execute setup cells (imports, helper functions, etc.)
        self._execute_setup_cells()

        # Then load command cells
        for cell in self.notebook.cells:
            if cell.cell_type != CellType.CODE:
                continue

            source = cell.source_text

            # Check if this is a command cell
            if not self._is_command_cell(source):
                continue

            # Load the command
            cmd = self._load_command_from_cell(source)
            if cmd:
                func_name = self._extract_function_name(source)
                if func_name:
                    commands.append((func_name, cmd))

        return commands

    def create_group(self, group_name: Optional[str] = None) -> Optional[click.Group]:
        """
        Create a Click group containing all commands from the notebook.

        Args:
            group_name: Name for the group (defaults to notebook name)

        Returns:
            Click Group with all notebook commands
        """
        if group_name is None:
            group_name = self.notebook.metadata.mcli.name

        # Extract commands
        commands = self.extract_commands()

        if not commands:
            logger.warning(f"No commands found in notebook {group_name}")
            return None

        # Create a Click group
        @click.group(name=group_name)
        def notebook_group():
            """Commands from notebook."""
            pass

        # Add description from notebook metadata
        if self.notebook.metadata.mcli.description:
            notebook_group.__doc__ = self.notebook.metadata.mcli.description

        # Add all commands to the group
        for cmd_name, cmd in commands:
            notebook_group.add_command(cmd, name=cmd_name)
            logger.debug(f"Added command {cmd_name} to group {group_name}")

        logger.info(f"Created group {group_name} with {len(commands)} command(s)")
        return notebook_group

    @classmethod
    def from_file(cls, notebook_path: Path) -> "NotebookCommandLoader":
        """
        Create a command loader from a notebook file.

        Args:
            notebook_path: Path to the notebook JSON file

        Returns:
            NotebookCommandLoader instance
        """
        notebook = WorkflowConverter.load_notebook_json(notebook_path)
        return cls(notebook)

    @classmethod
    def load_group_from_file(
        cls, notebook_path: Path, group_name: Optional[str] = None
    ) -> Optional[click.Group]:
        """
        Load a Click group directly from a notebook file.

        Args:
            notebook_path: Path to the notebook JSON file
            group_name: Optional group name (defaults to notebook name)

        Returns:
            Click Group with all notebook commands
        """
        loader = cls.from_file(notebook_path)
        return loader.create_group(group_name)
