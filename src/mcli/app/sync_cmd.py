"""
Top-level sync command for MCLI.

This module provides the `mcli sync` command for quickly syncing workflows
from local or global context.
"""

import click

from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_sync import ScriptSyncManager
from mcli.lib.ui.styling import console, error, info, success

logger = get_logger(__name__)


@click.command("sync")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Sync global workflows (~/.mcli/commands/) instead of local (.mcli/workflows/)",
)
@click.option("--force", "-f", is_flag=True, help="Force regeneration of all JSONs")
def sync(is_global, force):
    """
    Sync workflows from local or global context.

    Scans the workflows directory for new or modified script files (.py, .sh, .js, etc.)
    and generates/updates their JSON workflow representations. Also reloads the command
    manager to pick up any changes.

    By default, syncs local workflows (if in git repo). Use --global/-g for global workflows.

    Examples:
        mcli sync              # Sync local workflows (if in git repo)
        mcli sync --global     # Sync global workflows
        mcli sync -g --force   # Force regeneration of all global workflows
    """
    # Determine the scope
    scope = "global" if is_global else "local"
    commands_dir = get_custom_commands_dir(global_mode=is_global)

    if not commands_dir.exists():
        error(f"Workflows directory does not exist: {commands_dir}")
        info(
            f"Run 'mcli init' to create {scope} workflows directory"
            if not is_global
            else "Global workflows directory will be created automatically when needed"
        )
        return 1

    info(f"Syncing {scope} workflows from {commands_dir}...")

    # Step 1: Sync scripts to JSON
    sync_manager = ScriptSyncManager(commands_dir)
    synced = sync_manager.sync_all(force=force)

    if synced:
        success(f"✓ Synced {len(synced)} script(s) to JSON")
        for json_path in synced:
            relative_path = json_path.relative_to(commands_dir)
            console.print(f"  • {relative_path}")
    else:
        info("All scripts are already in sync")

    # Step 2: Reload command manager to pick up changes
    info("Reloading command manager...")
    manager = get_command_manager(global_mode=is_global)
    commands = manager.load_all_commands()

    # Count workflow commands
    workflow_count = sum(1 for cmd in commands if cmd.get("group") in ["workflow", "workflows"])

    success(f"✓ Loaded {workflow_count} workflow command(s)")
    console.print(f"\n[dim]Scope: {scope}[/dim]")
    console.print(f"[dim]Location: {commands_dir}[/dim]")

    if not is_global and manager.git_root:
        console.print(f"[dim]Git repository: {manager.git_root}[/dim]")

    console.print("\n[dim]Commands are now available for use[/dim]")

    return 0
