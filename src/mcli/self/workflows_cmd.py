"""
Workflows command for mcli self.

Provides a comprehensive view of all workflows tracked by mcli,
including a dashboard summary and detailed listings.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir, get_git_root, get_mcli_home, is_git_repository
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.workspace_registry import (
    auto_register_current,
    get_all_workflows,
    get_registry_path,
    list_registered_workspaces,
    load_registry,
)

logger = get_logger(__name__)
console = Console()


def _get_workflow_stats() -> Dict[str, Any]:
    """
    Gather comprehensive workflow statistics.

    Returns:
        Dictionary with stats about workspaces, workflows, and health
    """
    registry = load_registry()
    workspaces = list_registered_workspaces()
    all_workflows = get_all_workflows()

    # Count totals
    total_workflows = sum(len(wfs) for wfs in all_workflows.values())
    active_workspaces = sum(1 for ws in workspaces if ws["exists"])
    missing_workspaces = len(workspaces) - active_workspaces

    # Count by language
    language_counts: Dict[str, int] = {}
    for workflows in all_workflows.values():
        for wf in workflows:
            lang = wf.get("language", "unknown")
            language_counts[lang] = language_counts.get(lang, 0) + 1

    # Global workflows
    global_dir = get_mcli_home() / "workflows"
    global_count = len(all_workflows.get("global (~/.mcli/workflows)", []))

    # Local workflows (current workspace)
    local_count = 0
    current_workspace = None
    if is_git_repository():
        git_root = get_git_root()
        if git_root:
            current_workspace = git_root.name
            for ws_name, wfs in all_workflows.items():
                if str(git_root) in ws_name:
                    local_count = len(wfs)
                    break

    # Registry metadata
    registry_updated = registry.get("updated_at", "Never")

    return {
        "total_workflows": total_workflows,
        "total_workspaces": len(workspaces),
        "active_workspaces": active_workspaces,
        "missing_workspaces": missing_workspaces,
        "global_workflows": global_count,
        "local_workflows": local_count,
        "current_workspace": current_workspace,
        "language_counts": language_counts,
        "registry_updated": registry_updated,
        "all_workflows": all_workflows,
        "workspaces": workspaces,
    }


def _render_dashboard(stats: Dict[str, Any]) -> None:
    """Render the workflow dashboard to console."""
    # Header
    console.print()
    console.print("[bold cyan]MCLI Workflow Tracker[/bold cyan]")
    console.print("=" * 50)

    # Summary stats
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Label", style="dim")
    summary_table.add_column("Value", style="bold")

    summary_table.add_row("Total Workflows", f"[green]{stats['total_workflows']}[/green]")
    summary_table.add_row("Global Workflows", str(stats["global_workflows"]))
    summary_table.add_row("Local Workflows", str(stats["local_workflows"]))
    summary_table.add_row(
        "Active Workspaces",
        f"[green]{stats['active_workspaces']}[/green]/{stats['total_workspaces']}",
    )

    if stats["missing_workspaces"] > 0:
        summary_table.add_row(
            "Missing Workspaces", f"[yellow]{stats['missing_workspaces']}[/yellow]"
        )

    if stats["current_workspace"]:
        summary_table.add_row("Current Workspace", f"[cyan]{stats['current_workspace']}[/cyan]")

    console.print(Panel(summary_table, title="Summary", border_style="blue"))

    # Language breakdown
    if stats["language_counts"]:
        lang_table = Table(show_header=True, header_style="bold")
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Count", justify="right")

        for lang, count in sorted(
            stats["language_counts"].items(), key=lambda x: x[1], reverse=True
        ):
            lang_table.add_row(lang.title(), str(count))

        console.print(Panel(lang_table, title="By Language", border_style="green"))

    # Workspace overview
    if stats["workspaces"]:
        ws_table = Table(show_header=True, header_style="bold")
        ws_table.add_column("Workspace", style="cyan")
        ws_table.add_column("Workflows", justify="right")
        ws_table.add_column("Status")

        # Add global first
        global_count = stats["global_workflows"]
        if global_count > 0:
            ws_table.add_row("global", str(global_count), "[green]Active[/green]")

        for ws in stats["workspaces"]:
            # Find workflow count for this workspace
            ws_workflows = 0
            for ws_name, wfs in stats["all_workflows"].items():
                if ws["path"] in ws_name:
                    ws_workflows = len(wfs)
                    break

            status = "[green]Active[/green]" if ws["exists"] else "[yellow]Missing[/yellow]"
            ws_table.add_row(ws["name"], str(ws_workflows), status)

        console.print(Panel(ws_table, title="Workspaces", border_style="magenta"))

    # Registry info
    console.print()
    console.print(f"[dim]Registry: {get_registry_path()}[/dim]")
    console.print(f"[dim]Last updated: {stats['registry_updated']}[/dim]")
    console.print()


def _render_workflow_list(
    all_workflows: Dict[str, List[Dict[str, Any]]], is_global: bool = False
) -> None:
    """Render detailed workflow listing."""
    if not all_workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        console.print("\n[dim]Create a workflow with:[/dim]")
        console.print("  mcli new <name>")
        return

    total = 0

    for workspace_name, workflows in all_workflows.items():
        if not workflows:
            continue

        # Filter for global only if requested
        if is_global and "global" not in workspace_name.lower():
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
            Panel(
                table,
                title=f"[bold]{workspace_name}[/bold]",
                subtitle=f"{len(workflows)} workflow(s)",
            )
        )
        total += len(workflows)

    console.print(f"\n[bold]Total: {total} workflow(s)[/bold]")


@click.command("workflows")
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show detailed list of all workflows",
)
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Show only global workflows (~/.mcli/workflows/)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--dashboard",
    "-d",
    is_flag=True,
    help="Show dashboard view (default when no flags)",
)
def workflows_cmd(show_all: bool, is_global: bool, as_json: bool, dashboard: bool):
    """📊 View all workflows tracked by mcli.

    Shows a dashboard summary of all registered workspaces and their workflows.
    Use flags to get different views:

    \b
    Default (no flags):  Dashboard with summary stats
    --all/-a:            Detailed list of all workflows
    --global/-g:         Show only global workflows
    --json:              Output as JSON for scripting
    --dashboard/-d:      Force dashboard view

    \b
    Examples:
        mcli self workflows              # Dashboard summary
        mcli self workflows --all        # List all workflows
        mcli self workflows --global     # Global workflows only
        mcli self workflows --json       # JSON output
    """
    try:
        # Auto-register current workspace if applicable
        auto_register_current()

        # Gather stats
        stats = _get_workflow_stats()

        # JSON output
        if as_json:
            output = {
                "summary": {
                    "total_workflows": stats["total_workflows"],
                    "total_workspaces": stats["total_workspaces"],
                    "active_workspaces": stats["active_workspaces"],
                    "missing_workspaces": stats["missing_workspaces"],
                    "global_workflows": stats["global_workflows"],
                    "local_workflows": stats["local_workflows"],
                    "current_workspace": stats["current_workspace"],
                    "registry_updated": stats["registry_updated"],
                },
                "language_counts": stats["language_counts"],
                "workspaces": stats["workspaces"],
            }

            # Add full workflow details if --all
            if show_all:
                flat_workflows = []
                for workspace_name, workflows in stats["all_workflows"].items():
                    for wf in workflows:
                        wf["workspace"] = workspace_name
                        flat_workflows.append(wf)
                output["workflows"] = flat_workflows

            click.echo(json.dumps(output, indent=2, default=str))
            return 0

        # Detailed list mode
        if show_all or is_global:
            _render_workflow_list(stats["all_workflows"], is_global)
            return 0

        # Default: dashboard view
        _render_dashboard(stats)
        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to display workflows")
        return 1
