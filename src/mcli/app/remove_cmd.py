"""
Top-level remove/delete command for MCLI.

This module provides the `mcli remove` and `mcli delete` commands for removing custom commands.
"""

import click
from rich.prompt import Prompt

from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


@click.command("remove")
@click.argument("command_name", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Remove from global commands instead of local"
)
def remove(command_name, yes, is_global):
    """
    Remove a custom command.

    By default removes from local commands (if in git repo), use --global/-g for global commands.

    Examples:
        mcli remove my-command          # Remove local command
        mcli remove my-command --global # Remove global command
        mcli remove my-command -y       # Skip confirmation

    Alias: mcli delete
    """
    manager = get_command_manager(global_mode=is_global)
    command_file = manager.commands_dir / f"{command_name}.json"

    if not command_file.exists():
        console.print(f"[red]Command '{command_name}' not found.[/red]")
        return 1

    if not yes:
        should_delete = Prompt.ask(
            f"Delete command '{command_name}'?", choices=["y", "n"], default="n"
        )
        if should_delete.lower() != "y":
            console.print("Deletion cancelled.")
            return 0

    if manager.delete_command(command_name):
        console.print(f"[green]Deleted custom command: {command_name}[/green]")
        return 0
    else:
        console.print(f"[red]Failed to delete command: {command_name}[/red]")
        return 1


# Create an alias for delete
delete = remove
