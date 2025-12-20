"""IPFS sync commands for mcli.

Provides immutable cloud synchronization of workflow state via IPFS.
Push your command lockfile to IPFS and share the CID with anyone.
"""

from pathlib import Path
from typing import Optional

import click

from mcli.lib.constants import SyncMessages
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.ui.styling import console, error, info, success


@click.group(name="sync")
def sync_group():
    """Sync workflow state to IPFS (immutable cloud storage).

    Push your command lockfile to IPFS and get a CID that anyone can use
    to retrieve the exact same workflow state.

    Commands:
        push     Upload workflow state to IPFS
        pull     Download workflow state from IPFS
        history  Show your sync history
        verify   Check if a CID is accessible
    """
    pass


@sync_group.command(name="push")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Push global commands")
@click.option("--description", "-d", help="Description for this sync")
def sync_push_command(global_mode: bool, description: str):
    """Push workflow state to IPFS.

    Uploads your current command lockfile to IPFS and returns an immutable
    CID (Content Identifier) that anyone can use to retrieve the exact same
    workflow state.

    Examples:
        mcli sync push
        mcli sync push -d "Production v1.0"
        mcli sync push --global
    """
    from mcli.lib.ipfs_sync import IPFSSync

    workflows_dir = get_custom_commands_dir(global_mode=global_mode)
    lockfile_path = workflows_dir / "commands.lock.json"

    if not lockfile_path.exists():
        error(SyncMessages.LOCKFILE_NOT_FOUND.format(path=lockfile_path))
        info(SyncMessages.RUN_UPDATE_LOCKFILE)
        return

    ipfs = IPFSSync()

    # Check if IPFS is available
    if not ipfs._check_local_ipfs():
        error(SyncMessages.NO_LOCAL_IPFS_DAEMON)
        console.print()
        console.print(SyncMessages.IPFS_SETUP_HEADER)
        console.print(SyncMessages.IPFS_SETUP_STEP_1)
        console.print(SyncMessages.IPFS_SETUP_STEP_1_ALT)
        console.print(SyncMessages.IPFS_SETUP_STEP_2)
        console.print(SyncMessages.IPFS_SETUP_STEP_3)
        console.print(SyncMessages.IPFS_SETUP_STEP_4)
        return

    info(SyncMessages.UPLOADING_TO_IPFS)

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
    """Pull workflow state from IPFS by CID.

    Retrieves a command lockfile from IPFS using its Content Identifier (CID).
    The CID guarantees you get the exact same content that was uploaded.

    Examples:
        mcli sync pull QmXyZ123...
        mcli sync pull QmXyZ123... -o my-commands.json
        mcli sync pull QmXyZ123... --no-verify
    """
    import json

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
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        success(SyncMessages.SAVED_TO.format(path=output_path))

        # Show summary
        command_count = len(data.get("commands", {}))
        console.print(SyncMessages.COMMANDS_COUNT.format(count=command_count))

        if "version" in data:
            console.print(SyncMessages.VERSION_LABEL.format(version=data["version"]))

    else:
        error(SyncMessages.FAILED_RETRIEVE_IPFS)
        info(SyncMessages.CID_INVALID_OR_NOT_PROPAGATED)


@sync_group.command(name="history")
@click.option("--limit", "-n", default=10, help="Number of entries to show")
def sync_history_command(limit: int):
    """Show IPFS sync history.

    Displays your local history of IPFS syncs, including CIDs,
    timestamps, and descriptions.

    Examples:
        mcli sync history
        mcli sync history -n 20
    """
    from mcli.lib.ipfs_sync import IPFSSync

    ipfs = IPFSSync()
    history = ipfs.get_history(limit=limit)

    if not history:
        info(SyncMessages.NO_SYNC_HISTORY)
        console.print(SyncMessages.RUN_PUSH_FIRST)
        return

    console.print(f"IPFS Sync History (last {len(history)} entries)\n")

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
    """Verify that a CID is accessible on IPFS.

    Checks if the given CID can be retrieved from IPFS gateways.

    Examples:
        mcli sync verify QmXyZ123...
    """
    from mcli.lib.ipfs_sync import IPFSSync

    info(SyncMessages.VERIFYING_CID.format(cid=cid))

    ipfs = IPFSSync()

    if ipfs.verify_cid(cid):
        success(SyncMessages.CID_ACCESSIBLE)
    else:
        error(SyncMessages.CID_NOT_ACCESSIBLE)
        info(SyncMessages.PROPAGATION_DELAY_NOTE)
