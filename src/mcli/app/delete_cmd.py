"""
Top-level delete command for MCLI.

This module provides the `mcli delete` command for removing workflow commands.
Aliases: rm, remove
"""

import click
from rich.prompt import Prompt

from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


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
def delete(command_name: str, yes: bool, is_global: bool):
    """
    Delete a workflow command.

    By default removes from local commands (if in git repo), use --global/-g for global commands.

    Examples:
        mcli delete my-command          # Delete local command
        mcli delete my-command --global # Delete global command
        mcli delete my-command -y       # Skip confirmation

    Aliases: rm, remove
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
        console.print(f"[green]Deleted workflow command: {command_name}[/green]")
        return 0
    else:
        console.print(f"[red]Failed to delete command: {command_name}[/red]")
        return 1


# Aliases for backward compatibility
rm = delete
remove = delete
