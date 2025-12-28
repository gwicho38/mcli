"""
Top-level list command for MCLI.

This module provides the `mcli list` command for listing available workflows
from all registered workspaces.
"""

import json

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir, get_git_root, is_git_repository
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console
from mcli.lib.workspace_registry import (
    auto_register_current,
    get_all_workflows,
    list_registered_workspaces,
)

logger = get_logger(__name__)


@click.command("list")
@click.option(
    "--all", "-a", "show_all", is_flag=True, help="Show workflows from all registered workspaces"
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Show only global workflows (~/.mcli/workflows/)",
)
@click.option(
    "--workspaces",
    "-w",
    is_flag=True,
    help="List registered workspaces instead of workflows",
)
def list_cmd(show_all: bool, as_json: bool, is_global: bool, workspaces: bool):
    """📋 List all available workflow commands.

    By default, shows workflows from the current workspace (local if in git repo,
    or global otherwise). Use flags to see more:

    - --all/-a: Show workflows from ALL registered workspaces
    - --global/-g: Show only global workflows
    - --workspaces/-w: List registered workspaces

    Examples:
        mcli list                  # Show current workspace workflows
        mcli list --all            # Show all workflows from all workspaces
        mcli list --global         # Show global workflows only
        mcli list --workspaces     # List registered workspaces
        mcli list --json           # Output as JSON
    """
    try:
        # List workspaces mode
        if workspaces:
            _list_workspaces(as_json)
            return 0

        # Auto-register current workspace if applicable
        auto_register_current()

        # Show all workspaces
        if show_all:
            _list_all_workflows(as_json)
            return 0

        # Show specific scope (global or local)
        _list_scope_workflows(is_global, as_json)
        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


def _list_workspaces(as_json: bool):
    """List all registered workspaces."""
    from rich.table import Table

    workspaces = list_registered_workspaces()

    if as_json:
        click.echo(json.dumps({"workspaces": workspaces, "total": len(workspaces)}, indent=2))
        return

    if not workspaces:
        console.print("[yellow]No workspaces registered.[/yellow]")
        console.print("\n[dim]Register a workspace with:[/dim]")
        console.print("  mcli self workspace add [PATH]")
        console.print("\n[dim]Or initialize workflows in current directory:[/dim]")
        console.print("  mcli init")
        return

    table = Table(title="Registered Workspaces")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Status", style="green")

    for ws in workspaces:
        status = "✅ Active" if ws["exists"] else "⚠️ Missing"
        table.add_row(ws["name"], ws["path"], status)

    console.print(table)
    console.print(f"\n[dim]Total: {len(workspaces)} workspace(s)[/dim]")


def _list_all_workflows(as_json: bool):
    """List workflows from all registered workspaces."""
    from rich.panel import Panel
    from rich.table import Table

    all_workflows = get_all_workflows()

    if as_json:
        # Flatten for JSON output
        flat_workflows = []
        for workspace_name, workflows in all_workflows.items():
            for wf in workflows:
                wf["workspace"] = workspace_name
                flat_workflows.append(wf)
        click.echo(
            json.dumps({"workflows": flat_workflows, "total": len(flat_workflows)}, indent=2)
        )
        return

    if not all_workflows:
        console.print("[yellow]No workflows found in any registered workspace.[/yellow]")
        console.print("\n[dim]Create a workflow with:[/dim]")
        console.print("  mcli new <name>")
        return

    total = 0

    for workspace_name, workflows in all_workflows.items():
        if not workflows:
            continue

        table = Table(show_header=True, header_style="bold")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Language", style="blue")
        table.add_column("Version", style="green")

        for wf in workflows:
            desc = wf.get("description", "")
            if len(desc) > 50:
                desc = desc[:47] + "..."
            table.add_row(
                wf["name"],
                desc,
                wf.get("language", "?"),
                wf.get("version", "1.0.0"),
            )

        console.print(
            Panel(table, title=f"📁 {workspace_name}", subtitle=f"{len(workflows)} workflow(s)")
        )
        total += len(workflows)

    console.print(
        f"\n[bold]Total: {total} workflow(s) across {len(all_workflows)} workspace(s)[/bold]"
    )


def _list_scope_workflows(is_global: bool, as_json: bool):
    """List workflows from a specific scope (global or local)."""
    from rich.table import Table

    workflows_dir = get_custom_commands_dir(global_mode=is_global)

    if not workflows_dir.exists():
        scope = "global" if is_global else "local"
        console.print(f"[yellow]No {scope} workflows found.[/yellow]")
        console.print("\n[dim]Create a workflow with:[/dim]")
        console.print("  mcli new <name>")
        return

    loader = ScriptLoader(workflows_dir)
    scripts = loader.discover_scripts()

    if not scripts:
        scope = "global" if is_global else "local"
        console.print(f"[yellow]No {scope} workflows found.[/yellow]")
        console.print("\n[dim]Create a workflow with:[/dim]")
        console.print("  mcli new <name>")
        return

    workflows = []
    for script_path in scripts:
        try:
            info = loader.get_script_info(script_path)
            info["name"] = script_path.stem
            info["path"] = str(script_path)
            workflows.append(info)
        except Exception as e:
            logger.debug(f"Failed to get info for {script_path}: {e}")

    if as_json:
        click.echo(json.dumps({"workflows": workflows, "total": len(workflows)}, indent=2))
        return

    # Determine scope name
    if is_global:
        scope_name = "Global (~/.mcli/workflows)"
    elif is_git_repository():
        git_root = get_git_root()
        scope_name = f"Local ({git_root.name if git_root else 'current'})"
    else:
        scope_name = "Local"

    table = Table(title=f"Workflows - {scope_name}")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Language", style="blue")
    table.add_column("Version", style="green")

    for wf in workflows:
        desc = wf.get("description", "")
        if len(desc) > 50:
            desc = desc[:47] + "..."
        table.add_row(
            wf["name"],
            desc,
            wf.get("language", "?"),
            wf.get("version", "1.0.0"),
        )

    console.print(table)

    # Show context information
    console.print(f"\n[dim]Workflows directory: {workflows_dir}[/dim]")
    console.print(f"[dim]Total: {len(workflows)} workflow(s)[/dim]")

    # Hint about --all flag
    if not is_global:
        console.print("\n[dim]Use --all/-a to see workflows from all registered workspaces[/dim]")


# Alias for backward compatibility
ls = list_cmd
