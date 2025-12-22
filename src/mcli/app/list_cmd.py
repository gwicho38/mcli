"""
Top-level list command for MCLI.

This module provides the `mcli list` command for listing available workflows.
"""

import json

import click

from mcli.lib.custom_commands import get_command_manager
from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


@click.command("list")
@click.option("--include-groups", is_flag=True, help="Include command groups in listing")
@click.option(
    "--custom-only", is_flag=True, help="Show only custom commands from command directory"
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Use global commands (~/.mcli/workflows/) instead of local",
)
def list_cmd(include_groups: bool, custom_only: bool, as_json: bool, is_global: bool):
    """
    List all available workflow commands.

    By default, shows all discovered commands. Use flags to filter:
    - --custom-only: Show only custom commands
    - --global/-g: Use global commands directory instead of local

    Examples:
        mcli list                  # Show all commands
        mcli list --custom-only    # Show only custom commands
        mcli list --global         # Show global commands
        mcli list --json           # Output as JSON
    """
    from rich.table import Table

    try:
        if custom_only:
            # Show only custom commands
            manager = get_command_manager(global_mode=is_global)
            cmds = manager.load_all_commands()

            if not cmds:
                console.print("No custom commands found.")
                console.print("Create one with: mcli new <name>")
                return 0

            if as_json:
                click.echo(json.dumps({"commands": cmds, "total": len(cmds)}, indent=2))
                return 0

            table = Table(title="Custom Commands")
            table.add_column("Name", style="green")
            table.add_column("Group", style="blue")
            table.add_column("Description", style="yellow")
            table.add_column("Version", style="cyan")
            table.add_column("Updated", style="dim")

            for cmd in cmds:
                table.add_row(
                    cmd["name"],
                    cmd.get("group", "-"),
                    cmd.get("description", ""),
                    cmd.get("version", "1.0"),
                    cmd.get("updated_at", "")[:10] if cmd.get("updated_at") else "-",
                )

            console.print(table)

            # Show context information
            scope = "global" if is_global or not manager.is_local else "local"
            scope_color = "yellow" if scope == "local" else "cyan"
            console.print(f"\n[dim]Scope: [{scope_color}]{scope}[/{scope_color}][/dim]")
            if manager.is_local and manager.git_root:
                console.print(f"[dim]Git repository: {manager.git_root}[/dim]")
            console.print(f"[dim]Commands directory: {manager.commands_dir}[/dim]")
            console.print(f"[dim]Lockfile: {manager.lockfile_path}[/dim]")

            return 0

        else:
            # Show all discovered Click commands
            discovery = get_command_discovery()
            commands_data = discovery.get_commands(include_groups=include_groups)

        if as_json:
            click.echo(
                json.dumps({"commands": commands_data, "total": len(commands_data)}, indent=2)
            )
            return

        if not commands_data:
            console.print("No commands found")
            return

        console.print(f"[bold]Available Commands ({len(commands_data)}):[/bold]")
        for cmd in commands_data:
            group_indicator = "[blue][GROUP][/blue] " if cmd.get("is_group") else ""
            console.print(f"{group_indicator}[green]{cmd['full_name']}[/green]")

            if cmd.get("description"):
                console.print(f"  {cmd['description']}")
            if cmd.get("module"):
                console.print(f"  Module: {cmd['module']}")
            if cmd.get("tags"):
                console.print(f"  Tags: {', '.join(cmd['tags'])}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# Alias for backward compatibility
ls = list_cmd
