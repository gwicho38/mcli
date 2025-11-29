"""
Script synchronization commands for mcli.

Commands to manage the script → JSON synchronization system.
"""

from pathlib import Path
from typing import Optional

import click

from mcli.lib.constants import SyncMessages
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
        error(SyncMessages.DIR_NOT_EXIST.format(path=commands_dir))
        return

    info(SyncMessages.SYNCING_SCRIPTS.format(path=commands_dir))

    sync_manager = ScriptSyncManager(commands_dir)
    synced = sync_manager.sync_all(force=force)

    if synced:
        success(SyncMessages.SYNCED_SCRIPTS.format(count=len(synced)))
        for json_path in synced:
            console.print(f"  • {json_path.relative_to(commands_dir)}")
    else:
        info(SyncMessages.NO_SCRIPTS_NEEDED_SYNCING)


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

    info(SyncMessages.SYNCING_SCRIPT.format(path=script_path))

    json_path = sync_manager.generate_json(script_path, force=force)

    if json_path:
        success(SyncMessages.GENERATED_JSON.format(path=json_path))
    else:
        error(SyncMessages.FAILED_TO_GENERATE_JSON.format(path=script_path))


@sync_group.command(name="status")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Check global commands")
def sync_status_command(global_mode: bool):
    """
    Show synchronization status of scripts.

    Displays which scripts are in sync with their JSON files and which need updating.
    """
    commands_dir = get_custom_commands_dir(global_mode=global_mode)

    if not commands_dir.exists():
        error(SyncMessages.DIR_NOT_EXIST.format(path=commands_dir))
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
    console.print(SyncMessages.SCRIPT_SYNC_STATUS_HEADER)
    console.print(SyncMessages.LOCATION.format(path=commands_dir))

    if in_sync:
        success(SyncMessages.IN_SYNC_COUNT.format(count=len(in_sync)))
        for path in in_sync:
            console.print(f"  • {path.relative_to(commands_dir)}")
        console.print()

    if needs_sync:
        warning(SyncMessages.NEEDS_SYNC_COUNT.format(count=len(needs_sync)))
        for path in needs_sync:
            console.print(f"  • {path.relative_to(commands_dir)}")
        console.print()

    if no_json:
        info(SyncMessages.NO_JSON_COUNT.format(count=len(no_json)))
        for path in no_json:
            console.print(f"  • {path.relative_to(commands_dir)}")
        console.print()

    total = len(in_sync) + len(needs_sync) + len(no_json)
    console.print(SyncMessages.TOTAL_SCRIPTS.format(count=total))

    if needs_sync or no_json:
        console.print(SyncMessages.RUN_SYNC_ALL_HINT)


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
        error(SyncMessages.DIR_NOT_EXIST.format(path=commands_dir))
        return

    sync_manager = ScriptSyncManager(commands_dir)

    # Find orphaned JSONs (dry run)
    info(SyncMessages.SCANNING_ORPHANED)

    orphaned = []
    for json_path in commands_dir.rglob("*.json"):
        if json_path == sync_manager.sync_cache_path:
            continue

        if json_path.name == "commands.lock.json":
            continue

        try:
            import json

            with open(json_path) as f:
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
        success(SyncMessages.NO_ORPHANED_FOUND)
        return

    warning(SyncMessages.FOUND_ORPHANED.format(count=len(orphaned)))
    for path in orphaned:
        console.print(f"  • {path.relative_to(commands_dir)}")

    if not yes:
        if not click.confirm(SyncMessages.REMOVE_FILES_PROMPT):
            info(SyncMessages.CANCELLED)
            return

    # Remove orphaned files
    removed = sync_manager.cleanup_orphaned_json()

    if removed:
        success(SyncMessages.REMOVED_ORPHANED.format(count=len(removed)))
    else:
        info(SyncMessages.NO_FILES_REMOVED)


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
        error(SyncMessages.DIR_NOT_EXIST.format(path=commands_dir))
        return

    from mcli.lib.script_sync import ScriptSyncManager
    from mcli.lib.script_watcher import start_watcher, stop_watcher

    info(SyncMessages.STARTING_WATCHER.format(path=commands_dir))
    console.print(SyncMessages.PRESS_CTRL_C)

    sync_manager = ScriptSyncManager(commands_dir)
    observer = start_watcher(commands_dir, sync_manager)

    if not observer:
        error(SyncMessages.FAILED_START_WATCHER)
        return

    try:
        success(SyncMessages.WATCHING_FOR_CHANGES)
        # Keep running until interrupted
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n")
        info(SyncMessages.STOPPING_WATCHER)
        stop_watcher(observer)
        success(SyncMessages.STOPPED)


@sync_group.command(name="push")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Push global commands")
@click.option("--description", "-d", help="Description for this sync")
def sync_push_command(global_mode: bool, description: str):
    """
    Push command state to IPFS (immutable cloud storage).

    Uploads your current command lockfile to IPFS and returns an immutable
    CID (Content Identifier) that anyone can use to retrieve the exact same
    command state.

    Features:
    - Zero configuration (no accounts or API keys)
    - Immutable (CID proves authenticity)
    - Decentralized (no single point of failure)
    - Free forever

    Examples:
        mcli workflows sync push
        mcli workflows sync push -d "Production commands v1.0"
        mcli workflows sync push --global
    """
    from mcli.lib.ipfs_sync import IPFSSync
    from mcli.lib.paths import get_workflows_dir

    workflows_dir = get_workflows_dir(global_mode=global_mode)
    lockfile_path = workflows_dir / "commands.lock.json"

    if not lockfile_path.exists():
        error(SyncMessages.LOCKFILE_NOT_FOUND.format(path=lockfile_path))
        info(SyncMessages.RUN_UPDATE_LOCKFILE)
        return

    info(SyncMessages.UPLOADING_TO_IPFS)

    ipfs = IPFSSync()
    cid = ipfs.push(lockfile_path, description=description or "")

    if cid:
        success(SyncMessages.PUSHED_TO_IPFS)
        console.print(SyncMessages.CID_LABEL.format(cid=cid))
        console.print(SyncMessages.RETRIEVE_HINT)
        console.print(SyncMessages.RETRIEVE_COMMAND.format(cid=cid))
        console.print(SyncMessages.VIEW_BROWSER_HINT)
        console.print(SyncMessages.IPFS_GATEWAY_URL.format(cid=cid))
    else:
        error(SyncMessages.FAILED_PUSH_IPFS)


@sync_group.command(name="pull")
@click.argument("cid")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file path")
@click.option("--no-verify", is_flag=True, help="Skip hash verification")
def sync_pull_command(cid: str, output: Optional[Path], no_verify: bool):
    """
    Pull command state from IPFS by CID.

    Retrieves a command lockfile from IPFS using its Content Identifier (CID).
    The CID guarantees you get the exact same content that was uploaded.

    CID: The IPFS content identifier (e.g., QmXyZ123...)

    Examples:
        mcli workflows sync pull QmXyZ123...
        mcli workflows sync pull QmXyZ123... -o my-commands.json
        mcli workflows sync pull QmXyZ123... --no-verify
    """
    from mcli.lib.ipfs_sync import IPFSSync

    info(SyncMessages.RETRIEVING_FROM_IPFS.format(cid=cid))

    ipfs = IPFSSync()
    data = ipfs.pull(cid, verify=not no_verify)

    if data:
        success(SyncMessages.RETRIEVED_FROM_IPFS)

        # Determine output path
        if output:
            output_path = output
        else:
            output_path = Path(f"commands_{cid[:8]}.json")

        # Write to file
        import json

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        success(SyncMessages.SAVED_TO.format(path=output_path))

        # Show summary
        command_count = len(data.get("commands", {}))
        console.print(SyncMessages.COMMANDS_COUNT.format(count=command_count))

        if "version" in data:
            console.print(SyncMessages.VERSION_LABEL.format(version=data["version"]))

        if "synced_at" in data:
            console.print(SyncMessages.SYNCED_AT_LABEL.format(timestamp=data["synced_at"]))

        if "description" in data and data["description"]:
            console.print(SyncMessages.DESCRIPTION_LABEL.format(description=data["description"]))

    else:
        error(SyncMessages.FAILED_RETRIEVE_IPFS)
        info(SyncMessages.CID_INVALID_OR_NOT_PROPAGATED)


@sync_group.command(name="history")
@click.option("--limit", "-n", default=10, help="Number of entries to show")
def sync_history_command(limit: int):
    """
    Show IPFS sync history.

    Displays your local history of IPFS syncs, including CIDs,
    timestamps, and descriptions.

    Examples:
        mcli workflows sync history
        mcli workflows sync history --limit 20
    """
    from mcli.lib.ipfs_sync import IPFSSync

    ipfs = IPFSSync()
    history = ipfs.get_history(limit=limit)

    if not history:
        info(SyncMessages.NO_SYNC_HISTORY)
        console.print(SyncMessages.RUN_PUSH_FIRST)
        return

    console.print(SyncMessages.IPFS_SYNC_HISTORY_HEADER.format(count=len(history)))

    for entry in reversed(history):
        console.print(f"[bold cyan]{entry['cid']}[/bold cyan]")
        console.print(f"  Time: {entry['timestamp']}")
        console.print(f"  Commands: {entry.get('command_count', 0)}")

        if entry.get("description"):
            console.print(f"  Description: {entry['description']}")

        console.print()


@sync_group.command(name="verify")
@click.argument("cid")
def sync_verify_command(cid: str):
    """
    Verify that a CID is accessible on IPFS.

    Checks if the given CID can be retrieved from IPFS gateways.

    CID: The IPFS content identifier to verify

    Examples:
        mcli workflows sync verify QmXyZ123...
    """
    from mcli.lib.ipfs_sync import IPFSSync

    info(SyncMessages.VERIFYING_CID.format(cid=cid))

    ipfs = IPFSSync()

    if ipfs.verify_cid(cid):
        success(SyncMessages.CID_ACCESSIBLE)
    else:
        error(SyncMessages.CID_NOT_ACCESSIBLE)
        info(SyncMessages.PROPAGATION_DELAY_NOTE)
