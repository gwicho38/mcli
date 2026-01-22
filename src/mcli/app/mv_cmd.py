"""Top-level mv command for MCLI.

This module provides the `mcli mv` command for moving/renaming workflow commands.
Supports moving between local and global locations.
"""

import shutil
from pathlib import Path

import click
from rich.prompt import Prompt

from mcli.lib.constants import MoveMessages
from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.ui.styling import console

logger = get_logger(__name__)
MM = MoveMessages  # Short alias for cleaner code

# Supported native script extensions
NATIVE_SCRIPT_EXTENSIONS = [".py", ".sh", ".bash", ".js", ".ts", ".ipynb"]


def find_command_file(workflows_dir: Path, command_name: str) -> Path | None:
    """Find a command file by name (native script or JSON)."""
    # Check native scripts first
    for ext in NATIVE_SCRIPT_EXTENSIONS:
        script_path = workflows_dir / f"{command_name}{ext}"
        if script_path.exists():
            return script_path

    # Check JSON file
    json_path = workflows_dir / f"{command_name}.json"
    if json_path.exists():
        return json_path

    return None


@click.command("mv")
@click.argument("from_name", required=True)
@click.argument("to_name", required=True)
@click.option(
    "--global",
    "-g",
    "from_global",
    is_flag=True,
    help="Source is a global command",
)
@click.option(
    "--to-global",
    "-G",
    "to_global",
    is_flag=True,
    help="Move destination to global commands",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def mv(from_name: str, to_name: str, from_global: bool, to_global: bool, yes: bool):
    """📦 Move or rename a workflow command.

    Move a command from one location to another, or rename it within the same scope.

    \b
    Examples:
        mcli mv old-name new-name           # Rename local command
        mcli mv my-cmd --to-global          # Move local to global (keep same name)
        mcli mv my-cmd -g new-name          # Move global to local with new name
        mcli mv my-cmd -g -G new-name       # Rename global command
    """
    # Get source and destination directories
    source_dir = get_custom_commands_dir(global_mode=from_global)
    dest_dir = get_custom_commands_dir(global_mode=to_global)

    # Find the source file
    source_file = find_command_file(source_dir, from_name)

    if not source_file:
        console.print(MM.COMMAND_NOT_FOUND.format(name=from_name))
        console.print(MM.SEARCHED_IN.format(path=source_dir))
        return 1

    # Determine destination path (preserve extension)
    dest_file = dest_dir / f"{to_name}{source_file.suffix}"

    # Check if destination already exists
    if dest_file.exists():
        console.print(MM.ALREADY_EXISTS.format(name=to_name))
        console.print(MM.PATH_DISPLAY.format(path=dest_file))
        return 1

    # Describe the operation
    if from_global == to_global:
        # Same scope - just renaming
        if from_name == to_name:
            console.print(MM.NO_CHANGE_NEEDED)
            return 0
        operation = MM.RENAME_OP.format(from_name=from_name, to_name=to_name)
        scope = "global" if from_global else "local"
        console.print(MM.RENAMING_COMMAND.format(scope=scope))
    else:
        # Moving between scopes
        from_scope = "global" if from_global else "local"
        to_scope = "global" if to_global else "local"
        operation = MM.MOVE_OP.format(from_name=from_name, from_scope=from_scope, to_scope=to_scope)
        if from_name != to_name:
            operation += MM.MOVE_AS_OP.format(to_name=to_name)
        console.print(MM.MOVING_COMMAND)

    console.print(MM.FROM_PATH.format(path=source_file))
    console.print(MM.TO_PATH.format(path=dest_file))

    # Confirm
    if not yes:
        should_move = Prompt.ask(MM.PROCEED_PROMPT, choices=["y", "n"], default="n")
        if should_move.lower() != "y":
            console.print(MM.CANCELLED)
            return 0

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Perform the move
    try:
        shutil.move(str(source_file), str(dest_file))

        # Update lockfiles for both source and destination managers
        source_manager = get_command_manager(global_mode=from_global)
        source_manager.update_lockfile()

        if from_global != to_global:
            dest_manager = get_command_manager(global_mode=to_global)
            dest_manager.update_lockfile()

        console.print(MM.MOVE_SUCCESS.format(operation=operation))
        console.print(MM.NEW_LOCATION.format(path=dest_file))
        return 0

    except Exception as e:
        console.print(MM.MOVE_FAILED.format(error=e))
        logger.exception("Failed to move command")
        return 1
