"""
Script synchronization commands for mcli.

Commands to manage the script → JSON synchronization system.
"""

from pathlib import Path

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_sync import ScriptSyncManager
from mcli.lib.ui.styling import console, error, info, success, warning

logger = get_logger(__name__)


@click.group(name="sync")
def sync_group():
    """Manage script-to-JSON synchronization."""
    pass


@sync_group.command(name="all")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Sync global commands")
@click.option("--force", "-f", is_flag=True, help="Force regeneration of all JSONs")
def sync_all_command(global_mode: bool, force: bool):
    """
    Sync all scripts to JSON workflow files.

    Scans the commands directory for script files (.py, .sh, .js, etc.) and
    generates/updates their JSON workflow representations.

    Examples:
        mcli workflows sync all           # Sync local commands
        mcli workflows sync all --global  # Sync global commands
        mcli workflows sync all --force   # Force regeneration
    """
    commands_dir = get_custom_commands_dir(global_mode=global_mode)

    if not commands_dir.exists():
        error(f"Commands directory does not exist: {commands_dir}")
        return

    info(f"Syncing scripts in {commands_dir}...")

    sync_manager = ScriptSyncManager(commands_dir)
    synced = sync_manager.sync_all(force=force)

    if synced:
        success(f"✓ Synced {len(synced)} script(s) to JSON")
        for json_path in synced:
            console.print(f"  • {json_path.relative_to(commands_dir)}")
    else:
        info("No scripts needed syncing")


@sync_group.command(name="one")
@click.argument("script_path", type=click.Path(exists=True, path_type=Path))
@click.option("--global", "-g", "global_mode", is_flag=True, help="Use global commands dir")
@click.option("--force", "-f", is_flag=True, help="Force regeneration")
def sync_one_command(script_path: Path, global_mode: bool, force: bool):
    """
    Sync a single script to JSON.

    SCRIPT_PATH: Path to the script file to sync

    Examples:
        mcli workflows sync one ~/.mcli/commands/utils/backup.sh
        mcli workflows sync one ./my_script.py --force
    """
    commands_dir = get_custom_commands_dir(global_mode=global_mode)
    sync_manager = ScriptSyncManager(commands_dir)

    info(f"Syncing {script_path}...")

    json_path = sync_manager.generate_json(script_path, force=force)

    if json_path:
        success(f"✓ Generated JSON: {json_path}")
    else:
        error(f"✗ Failed to generate JSON for {script_path}")


@sync_group.command(name="status")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Check global commands")
def sync_status_command(global_mode: bool):
    """
    Show synchronization status of scripts.

    Displays which scripts are in sync with their JSON files and which need updating.
    """
    commands_dir = get_custom_commands_dir(global_mode=global_mode)

    if not commands_dir.exists():
        error(f"Commands directory does not exist: {commands_dir}")
        return

    sync_manager = ScriptSyncManager(commands_dir)

    in_sync = []
    needs_sync = []
    no_json = []

    from mcli.lib.script_sync import LANGUAGE_MAP

    for script_path in commands_dir.rglob("*"):
        if script_path.is_dir():
            continue

        if script_path.suffix not in LANGUAGE_MAP:
            continue

        if script_path.suffix == ".json":
            continue

        if any(part.startswith(".") for part in script_path.parts):
            continue

        json_path = script_path.with_suffix(".json")

        if not json_path.exists():
            no_json.append(script_path)
        elif sync_manager.needs_sync(script_path, json_path):
            needs_sync.append(script_path)
        else:
            in_sync.append(script_path)

    # Display results
    console.print(f"\n[bold]Script Synchronization Status[/bold]")
    console.print(f"Location: {commands_dir}\n")

    if in_sync:
        success(f"✓ In sync: {len(in_sync)} script(s)")
        for path in in_sync:
            console.print(f"  • {path.relative_to(commands_dir)}")
        console.print()

    if needs_sync:
        warning(f"⚠ Needs sync: {len(needs_sync)} script(s)")
        for path in needs_sync:
            console.print(f"  • {path.relative_to(commands_dir)}")
        console.print()

    if no_json:
        info(f"○ No JSON: {len(no_json)} script(s)")
        for path in no_json:
            console.print(f"  • {path.relative_to(commands_dir)}")
        console.print()

    total = len(in_sync) + len(needs_sync) + len(no_json)
    console.print(f"Total scripts: {total}")

    if needs_sync or no_json:
        console.print(f"\nRun [bold]mcli workflows sync all[/bold] to sync all scripts")


@sync_group.command(name="cleanup")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Clean global commands")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def sync_cleanup_command(global_mode: bool, yes: bool):
    """
    Remove orphaned JSON files.

    Finds and removes JSON files that no longer have corresponding script files.
    Only removes auto-generated JSON files (not manually created ones).
    """
    commands_dir = get_custom_commands_dir(global_mode=global_mode)

    if not commands_dir.exists():
        error(f"Commands directory does not exist: {commands_dir}")
        return

    sync_manager = ScriptSyncManager(commands_dir)

    # Find orphaned JSONs (dry run)
    info("Scanning for orphaned JSON files...")

    orphaned = []
    for json_path in commands_dir.rglob("*.json"):
        if json_path == sync_manager.sync_cache_path:
            continue

        if json_path.name == "commands.lock.json":
            continue

        try:
            import json

            with open(json_path, "r") as f:
                json_data = json.load(f)
                if not json_data.get("metadata", {}).get("auto_generated"):
                    continue
        except Exception:
            continue

        # Check if source exists
        from mcli.lib.script_sync import LANGUAGE_MAP

        script_exists = False
        for ext in LANGUAGE_MAP.keys():
            script_path = json_path.with_suffix(ext)
            if script_path.exists():
                script_exists = True
                break

        if not script_exists:
            orphaned.append(json_path)

    if not orphaned:
        success("✓ No orphaned JSON files found")
        return

    warning(f"Found {len(orphaned)} orphaned JSON file(s):")
    for path in orphaned:
        console.print(f"  • {path.relative_to(commands_dir)}")

    if not yes:
        if not click.confirm("\nRemove these files?"):
            info("Cancelled")
            return

    # Remove orphaned files
    removed = sync_manager.cleanup_orphaned_json()

    if removed:
        success(f"✓ Removed {len(removed)} orphaned JSON file(s)")
    else:
        info("No files were removed")


@sync_group.command(name="watch")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Watch global commands")
def sync_watch_command(global_mode: bool):
    """
    Watch for script changes and auto-sync (development mode).

    Starts a file watcher that monitors the commands directory for changes
    and automatically syncs scripts to JSON in real-time.

    Press Ctrl+C to stop watching.
    """
    commands_dir = get_custom_commands_dir(global_mode=global_mode)

    if not commands_dir.exists():
        error(f"Commands directory does not exist: {commands_dir}")
        return

    from mcli.lib.script_sync import ScriptSyncManager
    from mcli.lib.script_watcher import start_watcher, stop_watcher

    info(f"Starting file watcher for {commands_dir}")
    console.print("Press Ctrl+C to stop\n")

    sync_manager = ScriptSyncManager(commands_dir)
    observer = start_watcher(commands_dir, sync_manager)

    if not observer:
        error("Failed to start file watcher")
        return

    try:
        success("✓ Watching for changes...")
        # Keep running until interrupted
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n")
        info("Stopping watcher...")
        stop_watcher(observer)
        success("✓ Stopped")
