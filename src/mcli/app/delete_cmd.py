"""
Top-level delete command for MCLI.

This module provides the `mcli delete` command for removing workflow commands.
Aliases: rm, remove
"""

from pathlib import Path
from typing import Optional

import click
from rich.prompt import Prompt

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_loader import SUPPORTED_EXTENSIONS
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


def find_command_file(commands_dir: Path, command_name: str) -> Optional[Path]:
    """
    Find a command file by name in the commands directory.

    Searches for native script files first (.py, .sh, .js, .ts, .ipynb),
    then falls back to legacy .json files.

    Args:
        commands_dir: Directory to search in
        command_name: Name of the command (without extension)

    Returns:
        Path to the command file, or None if not found
    """
    # Check for native script files first (new format)
    for ext in SUPPORTED_EXTENSIONS:
        script_file = commands_dir / f"{command_name}{ext}"
        if script_file.exists():
            return script_file

    # Check for legacy JSON file
    json_file = commands_dir / f"{command_name}.json"
    if json_file.exists():
        return json_file

    # Check in subdirectories (for grouped commands)
    for subdir in commands_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("."):
            for ext in SUPPORTED_EXTENSIONS:
                script_file = subdir / f"{command_name}{ext}"
                if script_file.exists():
                    return script_file
            # Also check for .json in subdirectories
            json_file = subdir / f"{command_name}.json"
            if json_file.exists():
                return json_file

    return None


@click.command("delete")
@click.argument("command_name", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Remove from global commands instead of local",
)
def delete(command_name: str, yes: bool, is_global: bool) -> int:
    """🗑️ Delete a workflow command.

    Removes native script files (.py, .sh, .js, .ts, .ipynb) or legacy JSON commands.
    By default removes from local commands (if in git repo), use --global/-g for global commands.

    Examples:
        mcli delete my-command          # Delete local command
        mcli delete my-command --global # Delete global command
        mcli delete my-command -y       # Skip confirmation

    Aliases: rm, remove
    """
    commands_dir = get_custom_commands_dir(global_mode=is_global)
    command_file = find_command_file(commands_dir, command_name)

    if not command_file:
        console.print(f"[red]Command '{command_name}' not found.[/red]")
        scope = "global" if is_global else "local"
        console.print(f"[dim]Searched in: {commands_dir} ({scope})[/dim]")
        return 1

    # Show file info
    file_type = command_file.suffix.lstrip(".")
    console.print(f"[dim]Found: {command_file.relative_to(commands_dir)} ({file_type})[/dim]")

    if not yes:
        should_delete = Prompt.ask(
            f"Delete command '{command_name}'?", choices=["y", "n"], default="n"
        )
        if should_delete.lower() != "y":
            console.print("Deletion cancelled.")
            return 0

    try:
        command_file.unlink()
        logger.info(f"Deleted command file: {command_file}")
        console.print(f"[green]✓ Deleted command: {command_name}[/green]")
        return 0
    except Exception as e:
        logger.error(f"Failed to delete command file {command_file}: {e}")
        console.print(f"[red]Failed to delete command: {e}[/red]")
        return 1


# Aliases for backward compatibility
rm = delete
remove = delete
