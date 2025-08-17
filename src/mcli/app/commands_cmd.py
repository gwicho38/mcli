import json
from typing import Optional

import click

from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.ui.styling import console


@click.group()
def commands():
    """Manage and execute available commands."""
    pass


@commands.command("list")
@click.option("--include-groups", is_flag=True, help="Include command groups in listing")
@click.option("--daemon-only", is_flag=True, help="Show only daemon database commands")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_commands(include_groups: bool, daemon_only: bool, as_json: bool):
    """List all available commands"""
    try:
        if daemon_only:
            # Show only daemon database commands
            client = get_daemon_client()
            result = client.list_commands(all=True)

            if isinstance(result, dict):
                commands_data = result.get("commands", [])
            elif isinstance(result, list):
                commands_data = result
            else:
                commands_data = []
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
            # Handle different command sources
            if daemon_only:
                status = "[red][INACTIVE][/red] " if not cmd.get("is_active", True) else ""
                console.print(
                    f"{status}• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})"
                )
            else:
                group_indicator = "[blue][GROUP][/blue] " if cmd.get("is_group") else ""
                console.print(f"{group_indicator}• [green]{cmd['full_name']}[/green]")

            if cmd.get("description"):
                console.print(f"  {cmd['description']}")
            if cmd.get("module"):
                console.print(f"  Module: {cmd['module']}")
            if cmd.get("tags"):
                console.print(f"  Tags: {', '.join(cmd['tags'])}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@commands.command("search")
@click.argument("query")
@click.option("--daemon-only", is_flag=True, help="Search only daemon database commands")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search_commands(query: str, daemon_only: bool, as_json: bool):
    """Search commands by name, description, or tags"""
    try:
        if daemon_only:
            # Search only daemon database commands
            client = get_daemon_client()
            result = client.list_commands(all=True)

            if isinstance(result, dict):
                all_commands = result.get("commands", [])
            elif isinstance(result, list):
                all_commands = result
            else:
                all_commands = []

            # Filter commands that match the query
            matching_commands = [
                cmd
                for cmd in all_commands
                if (
                    query.lower() in cmd["name"].lower()
                    or query.lower() in (cmd["description"] or "").lower()
                    or any(query.lower() in tag.lower() for tag in cmd.get("tags", []))
                )
            ]
        else:
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
            if daemon_only:
                status = "[red][INACTIVE][/red] " if not cmd.get("is_active", True) else ""
                console.print(
                    f"{status}• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})"
                )
            else:
                group_indicator = "[blue][GROUP][/blue] " if cmd.get("is_group") else ""
                console.print(f"{group_indicator}• [green]{cmd['full_name']}[/green]")

            console.print(f"  [italic]{cmd['description']}[/italic]")
            if cmd.get("module"):
                console.print(f"  Module: {cmd['module']}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@commands.command("execute")
@click.argument("command_name")
@click.argument("args", nargs=-1)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
def execute_command(command_name: str, args: tuple, as_json: bool, timeout: Optional[int]):
    """Execute a command by name"""
    try:
        client = get_daemon_client()
        result = client.execute_command(command_name=command_name, args=list(args), timeout=timeout)

        if as_json:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success"):
            if result.get("output"):
                console.print(f"[green]Output:[/green]\n{result['output']}")
            else:
                console.print("[green]Command executed successfully[/green]")

            if result.get("execution_time_ms"):
                console.print(f"[dim]Execution time: {result['execution_time_ms']}ms[/dim]")
        else:
            console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@commands.command("info")
@click.argument("command_name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def command_info(command_name: str, as_json: bool):
    """Show detailed information about a command"""
    try:
        client = get_daemon_client()
        result = client.list_commands(all=True)

        if isinstance(result, dict):
            all_commands = result.get("commands", [])
        elif isinstance(result, list):
            all_commands = result
        else:
            all_commands = []

        # Find the command
        command = None
        for cmd in all_commands:
            if cmd["name"].lower() == command_name.lower():
                command = cmd
                break

        if not command:
            console.print(f"[red]Command '{command_name}' not found[/red]")
            return

        if as_json:
            click.echo(json.dumps(command, indent=2))
            return

        console.print(f"[bold]Command: {command['name']}[/bold]")
        console.print(f"Language: {command['language']}")
        console.print(f"Description: {command.get('description', 'No description')}")
        console.print(f"Group: {command.get('group', 'None')}")
        console.print(f"Tags: {', '.join(command.get('tags', []))}")
        console.print(f"Active: {'Yes' if command.get('is_active', True) else 'No'}")
        console.print(f"Execution Count: {command.get('execution_count', 0)}")

        if command.get("created_at"):
            console.print(f"Created: {command['created_at']}")
        if command.get("last_executed"):
            console.print(f"Last Executed: {command['last_executed']}")

        if command.get("code"):
            console.print(f"\n[bold]Code:[/bold]")
            console.print(f"```{command['language']}")
            console.print(command["code"])
            console.print("```")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
