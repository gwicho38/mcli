"""
Top-level search command for MCLI.

This module provides the `mcli search` command for searching workflow commands.
"""

import json

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console
from mcli.lib.workspace_registry import auto_register_current, get_all_workflows

logger = get_logger(__name__)


def _search_workflows(query: str, workflows: list) -> list:
    """Search workflows by name, description, or tags."""
    query_lower = query.lower()
    matching = []

    for wf in workflows:
        name = wf.get("name", "").lower()
        description = wf.get("description", "").lower()
        tags = [t.lower() for t in wf.get("tags", [])]
        language = wf.get("language", "").lower()

        if (
            query_lower in name
            or query_lower in description
            or any(query_lower in tag for tag in tags)
            or query_lower in language
        ):
            matching.append(wf)

    return matching


@click.command("search")
@click.argument("query")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--all", "-a", "search_all", is_flag=True, help="Search all registered workspaces"
)
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Search global workflows only"
)
@click.option(
    "--builtin", "-b", is_flag=True, help="Also search built-in CLI commands"
)
def search(query: str, as_json: bool, search_all: bool, is_global: bool, builtin: bool):
    """🔍 Search workflows by name, description, or tags.

    By default searches workflows in the current workspace (local if in git repo,
    or global otherwise).

    Examples:
        mcli search backup          # Search current workspace workflows
        mcli search deploy --all    # Search all registered workspaces
        mcli search test --global   # Search global workflows only
        mcli search model --builtin # Also search built-in commands
        mcli search test --json     # Output results as JSON
    """
    try:
        # Auto-register current workspace
        auto_register_current()

        all_results = []

        # Search user workflows
        if search_all:
            # Search all registered workspaces
            all_workflows_by_workspace = get_all_workflows()
            for workspace_name, workflows in all_workflows_by_workspace.items():
                matching = _search_workflows(query, workflows)
                for wf in matching:
                    wf["workspace"] = workspace_name
                    wf["source"] = "workflow"
                all_results.extend(matching)
        else:
            # Search specific scope
            workflows_dir = get_custom_commands_dir(global_mode=is_global)
            if workflows_dir.exists():
                loader = ScriptLoader(workflows_dir)
                scripts = loader.discover_scripts()

                workflows = []
                for script_path in scripts:
                    try:
                        info = loader.get_script_info(script_path)
                        info["name"] = script_path.stem
                        info["path"] = str(script_path)
                        workflows.append(info)
                    except Exception as e:
                        logger.debug(f"Failed to get info for {script_path}: {e}")

                matching = _search_workflows(query, workflows)
                for wf in matching:
                    wf["source"] = "workflow"
                    wf["workspace"] = "global" if is_global else "local"
                all_results.extend(matching)

        # Optionally search built-in commands
        if builtin:
            from mcli.lib.discovery.command_discovery import get_command_discovery

            discovery = get_command_discovery()
            builtin_commands = discovery.search_commands(query)
            for cmd in builtin_commands:
                cmd["source"] = "builtin"
            all_results.extend(builtin_commands)

        # Output results
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "results": all_results,
                        "total": len(all_results),
                        "query": query,
                    },
                    indent=2,
                )
            )
            return

        if not all_results:
            console.print(f"No workflows found matching '[yellow]{query}[/yellow]'")
            if not search_all:
                console.print("\n[dim]Try --all/-a to search all registered workspaces[/dim]")
            if not builtin:
                console.print("[dim]Try --builtin/-b to also search built-in commands[/dim]")
            return

        console.print(f"[bold]Results for '{query}' ({len(all_results)}):[/bold]\n")

        # Group results by source
        workflows = [r for r in all_results if r.get("source") == "workflow"]
        builtins = [r for r in all_results if r.get("source") == "builtin"]

        if workflows:
            console.print("[bold cyan]Workflows:[/bold cyan]")
            for wf in workflows:
                workspace = wf.get("workspace", "")
                workspace_indicator = f"[dim]({workspace})[/dim] " if workspace else ""
                console.print(f"  {workspace_indicator}[green]{wf['name']}[/green]")
                if wf.get("description"):
                    desc = wf["description"]
                    if len(desc) > 60:
                        desc = desc[:57] + "..."
                    console.print(f"    [italic]{desc}[/italic]")
                lang = wf.get("language", "")
                version = wf.get("version", "")
                if lang or version:
                    console.print(f"    [dim]{lang} v{version}[/dim]")
            console.print()

        if builtins:
            console.print("[bold blue]Built-in Commands:[/bold blue]")
            for cmd in builtins:
                group_indicator = "[GROUP] " if cmd.get("is_group") else ""
                console.print(f"  {group_indicator}[green]{cmd['full_name']}[/green]")
                if cmd.get("description"):
                    desc = cmd["description"]
                    if len(desc) > 60:
                        desc = desc[:57] + "..."
                    console.print(f"    [italic]{desc}[/italic]")
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
