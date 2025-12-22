"""
Top-level search command for MCLI.

This module provides the `mcli search` command for searching workflow commands.
"""

import json

import click

from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


@click.command("search")
@click.argument("query")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Search global commands instead of local"
)
def search(query: str, as_json: bool, is_global: bool):
    """
    Search commands by name, description, or tags.

    By default searches local commands (if in git repo), use --global/-g for global commands.

    Examples:
        mcli search backup          # Search for 'backup' in command names/descriptions
        mcli search deploy --global # Search global commands
        mcli search test --json     # Output results as JSON
    """
    try:
        # Search all discovered Click commands
        discovery = get_command_discovery()
        matching_commands = discovery.search_commands(query)

        if as_json:
            click.echo(
                json.dumps(
                    {
                        "commands": matching_commands,
                        "total": len(matching_commands),
                        "query": query,
                    },
                    indent=2,
                )
            )
            return

        if not matching_commands:
            console.print(f"No commands found matching '[yellow]{query}[/yellow]'")
            return

        console.print(f"[bold]Commands matching '{query}' ({len(matching_commands)}):[/bold]")
        for cmd in matching_commands:
            group_indicator = "[blue][GROUP][/blue] " if cmd.get("is_group") else ""
            console.print(f"{group_indicator}[green]{cmd['full_name']}[/green]")

            if cmd.get("description"):
                console.print(f"  [italic]{cmd['description']}[/italic]")
            if cmd.get("module"):
                console.print(f"  Module: {cmd['module']}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
