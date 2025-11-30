"""
Notebook command loader for dynamically creating CLI commands from notebook cells.

This module extracts Click command decorators from notebook cells and creates
a Click group with all the commands as subcommands.
"""

import ast
import io
import logging
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import click

from mcli.lib.constants import EnvVars
from mcli.lib.logger.logger import get_logger
from mcli.workflow.notebook.converter import WorkflowConverter
from mcli.workflow.notebook.schema import CellType, WorkflowNotebook

logger = get_logger(__name__)


def _is_completion_mode() -> bool:
    """Check if we're running in shell completion mode."""
    return os.environ.get(EnvVars.COMPLETE) is not None


def _is_command_execution_mode() -> bool:
    """Check if we're in command execution mode (not just listing/loading)."""
    return os.environ.get(EnvVars.MCLI_NOTEBOOK_EXECUTE, "") == "1"


@contextmanager
def _suppress_output_during_loading() -> Generator[None, None, None]:
    """
    Context manager to suppress stdout and logging during notebook loading.

    When loading notebooks to discover commands, any stdout or logging output
    from executed setup cells is unwanted noise. This suppresses:
    - stdout (print statements)
    - stderr (error output)
    - logging at INFO level and below

    Output is only suppressed when NOT in execution mode (i.e., during command
    listing/loading). When actually running a command, output is preserved.
    """
    # If we're in command execution mode, don't suppress output
    if _is_command_execution_mode():
        yield
        return

    # Suppress stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    # Suppress logging at INFO and below by temporarily raising the root logger level
    root_logger = logging.getLogger()
    old_level = root_logger.level
    # Also suppress any handlers that might output to console
    old_handler_levels = {}
    for handler in root_logger.handlers:
        old_handler_levels[handler] = handler.level
        if handler.level < logging.WARNING:
            handler.level = logging.WARNING

    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        root_logger.level = old_level
        for handler, level in old_handler_levels.items():
            handler.level = level


@contextmanager
def _suppress_stdout_if_completing() -> Generator[None, None, None]:
    """
    Context manager to suppress stdout during shell completion.

    When tab completion is running, any stdout output from executed cells
    (like print statements) corrupts the completion response. This suppresses
    stdout only during completion mode.

    Note: This is kept for backwards compatibility. New code should use
    _suppress_output_during_loading() instead.
    """
    if _is_completion_mode():
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            yield
        finally:
            sys.stdout = old_stdout
    else:
        yield


def _find_project_venv(notebook_path: Path) -> Optional[Path]:
    """
    Find the project's virtual environment for a notebook.

    Searches upward from the notebook's directory for common venv locations.

    Args:
        notebook_path: Path to the notebook file

    Returns:
        Path to the venv's site-packages, or None if not found
    """
    search_dir = notebook_path.parent.resolve()

    # Search upward to find the project root
    for _ in range(10):  # Limit search depth
        # Check common venv locations
        venv_candidates = [
            search_dir / ".venv",
            search_dir / "venv",
            search_dir / ".env",
            search_dir / "env",
        ]

        for venv_path in venv_candidates:
            if venv_path.is_dir():
                # Find site-packages
                # macOS/Linux: lib/pythonX.Y/site-packages
                # Windows: Lib/site-packages
                for lib_dir in venv_path.glob("lib/python*/site-packages"):
                    if lib_dir.is_dir():
                        return lib_dir
                # Windows fallback
                win_site = venv_path / "Lib" / "site-packages"
                if win_site.is_dir():
                    return win_site

        # Move up one directory
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent

    return None


def _setup_project_imports(notebook_path: Path) -> list[str]:
    """
    Set up sys.path to include the project's virtual environment.

    This allows notebooks to import packages installed in the project's venv.

    Args:
        notebook_path: Path to the notebook file

    Returns:
        List of paths added to sys.path (for cleanup later)
    """
    added_paths = []

    # Find and add project venv
    venv_site_packages = _find_project_venv(notebook_path)
    if venv_site_packages:
        site_str = str(venv_site_packages)
        if site_str not in sys.path:
            sys.path.insert(0, site_str)
            added_paths.append(site_str)
            logger.info(f"Added project venv to import path: {venv_site_packages}")

    # Also add the project root (for local package imports like 'politician_trading')
    project_root = notebook_path.parent.resolve()
    for _ in range(10):
        # Look for common project markers
        markers = ["pyproject.toml", "setup.py", "setup.cfg", ".git"]
        if any((project_root / m).exists() for m in markers):
            root_str = str(project_root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
                added_paths.append(root_str)
                logger.info(f"Added project root to import path: {project_root}")

            # Also add src/ if it exists (common pattern)
            src_dir = project_root / "src"
            if src_dir.is_dir():
                src_str = str(src_dir)
                if src_str not in sys.path:
                    sys.path.insert(0, src_str)
                    added_paths.append(src_str)
            break

        parent = project_root.parent
        if parent == project_root:
            break
        project_root = parent

    return added_paths


class NotebookCommandLoader:
    """Load Click commands from notebook cells."""

    def __init__(self, notebook: WorkflowNotebook, notebook_path: Optional[Path] = None):
        """
        Initialize the command loader.

        Args:
            notebook: WorkflowNotebook instance
            notebook_path: Optional path to the notebook file (for resolving project imports)
        """
        self.notebook = notebook
        self.notebook_path = notebook_path
        self.globals_dict: dict[str, Any] = {}
        self._added_paths: list[str] = []

        # Set up project imports if we have a path
        if notebook_path:
            self._added_paths = _setup_project_imports(notebook_path)

    def _is_command_cell(self, source: str) -> bool:
        """
        Check if a cell contains a Click command decorator.

        Args:
            source: Cell source code

        Returns:
            True if cell contains @click.command, @group.command, or similar decorator
        """
        # Look for @click.command(), @command(), @<group>.command(), or similar decorators
        patterns = [
            r"@click\.command\(",
            r"@click\.group\(",
            r"@command\(",
            r"@group\(",
            r"@\w+\.command\(",  # Matches @ingest.command(), @mygroup.command(), etc.
            r"@\w+\.group\(",  # Matches @parent.group(), etc.
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

        Note: If a cell fails (e.g., missing module), we try to execute it
        line-by-line to salvage what we can. This handles cases where imports
        and definitions are mixed in the same cell.
        """
        for cell in self.notebook.cells:
            if cell.cell_type != CellType.CODE:
                continue

            source = cell.source_text

            # Skip command definition cells
            if self._is_command_cell(source):
                continue

            # Execute setup code (suppress stdout during completion to avoid corrupting output)
            try:
                with _suppress_output_during_loading():
                    exec(source, self.globals_dict)
                logger.debug("Executed setup cell successfully")
            except Exception as e:
                logger.warning(f"Failed to execute setup cell: {e}")
                # Try line-by-line execution to salvage what we can
                self._execute_cell_line_by_line(source)

    def _execute_cell_line_by_line(self, source: str) -> None:
        """
        Execute a cell line-by-line to handle partial failures.

        This is a fallback when a cell fails - we try to execute each
        statement individually to salvage imports and definitions that work.

        Args:
            source: Cell source code
        """
        import ast

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return

        for node in tree.body:
            try:
                # Compile and execute each statement individually
                code = compile(ast.Module(body=[node], type_ignores=[]), "<string>", "exec")
                with _suppress_output_during_loading():
                    exec(code, self.globals_dict)
            except Exception as stmt_e:
                # Log but continue - we want to execute as much as possible
                stmt_source = ast.get_source_segment(source, node) or "<unknown>"
                if len(stmt_source) > 100:
                    stmt_source = stmt_source[:100] + "..."
                logger.debug(f"Skipped statement due to error: {stmt_e}")

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

            # Execute the cell to define the command (suppress stdout during completion)
            with _suppress_output_during_loading():
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

    def extract_commands(self) -> list[tuple[str, click.Command]]:
        """
        Extract all Click commands from the notebook.

        This handles two patterns:
        1. Standalone @click.command() decorators
        2. Group subcommands like @group.command() where commands are registered to a group

        Returns:
            List of (command_name, command) tuples
        """
        commands = []
        found_groups = {}  # Track groups defined in the notebook

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
                    # Track groups for later extraction of subcommands
                    if isinstance(cmd, click.Group):
                        found_groups[func_name] = cmd
                    commands.append((func_name, cmd))

        # If we found groups, extract their subcommands
        # This handles @group.command() pattern where commands are registered during execution
        for group_name, group in found_groups.items():
            if hasattr(group, "commands") and group.commands:
                for cmd_name, cmd in group.commands.items():
                    # Add subcommands if not already in the list
                    if not any(name == cmd_name for name, _ in commands):
                        commands.append((cmd_name, cmd))
                        logger.debug(f"Extracted subcommand {cmd_name} from group {group_name}")

        return commands

    def create_group(self, group_name: Optional[str] = None) -> Optional[click.Group]:
        """
        Create a Click group containing all commands from the notebook.

        If the notebook defines its own group (via @click.group), that group
        is returned directly with all its subcommands already attached.
        Otherwise, a new group is created to wrap standalone commands.

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

        # Check if the notebook defines its own group that matches the expected name
        # If so, return that group directly (it already has subcommands attached)
        for cmd_name, cmd in commands:
            if isinstance(cmd, click.Group):
                # If notebook defines a group, use it directly
                # The subcommands are already attached via @group.command()
                if cmd.commands:
                    logger.info(
                        f"Using notebook-defined group '{cmd_name}' with "
                        f"{len(cmd.commands)} subcommand(s)"
                    )
                    return cmd

        # No user-defined group found, create a wrapper group
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

        This also sets up the import path to include the project's virtual
        environment, so notebooks can import project-specific packages.

        Args:
            notebook_path: Path to the notebook JSON file

        Returns:
            NotebookCommandLoader instance
        """
        notebook = WorkflowConverter.load_notebook_json(notebook_path)
        return cls(notebook, notebook_path=notebook_path.resolve())

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
        # Wrap the entire loading process in output suppression
        # This catches imports that happen during notebook cell execution
        with _suppress_output_during_loading():
            loader = cls.from_file(notebook_path)
            return loader.create_group(group_name)
