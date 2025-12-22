"""Sync and lockfile management commands for mcli.

Provides:
- IPFS synchronization of workflow state (push/pull)
- Lockfile management (status/update/diff)
"""

import json
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from mcli.lib.constants import SyncMessages
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console, error, info, success, warning


@click.group(name="sync")
def sync_group():
    """Sync workflow state and manage lockfile.

    Lockfile Management:
        status   Show workflow scripts and their lockfile status
        update   Update lockfile with current script state
        diff     Show differences between scripts and lockfile
        show     Show lockfile contents

    IPFS Sync:
        push     Upload workflow state to IPFS
        pull     Download workflow state from IPFS
        verify   Verify lockfile or IPFS CID accessibility
    """
    pass


# ============================================================
# Lockfile Management Commands
# ============================================================


@sync_group.command(name="status")
@click.option("--global", "-g", "is_global", is_flag=True, help="Show global workflow scripts")
def sync_status(is_global: bool):
    """Show workflow scripts and their lockfile status.

    Lists all workflow scripts and shows whether they are:
    - synced: matches lockfile
    - modified: content changed since last lock
    - unlocked: not yet in lockfile

    Examples:
        mcli sync status           # Show local workflows status
        mcli sync status --global  # Show global workflows status
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    scripts = loader.discover_scripts()
    if not scripts:
        scope = "global" if is_global else "local"
        info(f"No {scope} workflow scripts found.")
        return

    lockfile = loader.load_lockfile()
    locked_commands = lockfile.get("commands", {}) if lockfile else {}

    table = Table(title=f"Workflow Scripts ({'global' if is_global else 'local'})")
    table.add_column("Name", style="cyan")
    table.add_column("Language", style="blue")
    table.add_column("Version", style="green")
    table.add_column("Hash", style="dim")
    table.add_column("Status", style="yellow")

    for script_path in scripts:
        name = script_path.stem
        script_info = loader.get_script_info(script_path)

        # Check status against lockfile
        if name in locked_commands:
            locked = locked_commands[name]
            current_hash = script_info.get("content_hash", "")
            locked_hash = locked.get("content_hash", "")

            if current_hash == locked_hash:
                status = "[green]synced[/green]"
            else:
                status = "[yellow]modified[/yellow]"
        else:
            status = "[red]unlocked[/red]"

        table.add_row(
            name,
            script_info.get("language", "unknown"),
            script_info.get("version", "1.0.0"),
            (
                script_info.get("content_hash", "")[:16] + "..."
                if script_info.get("content_hash")
                else "-"
            ),
            status,
        )

    console.print(table)

    # Show lockfile info
    if lockfile:
        console.print(f"\n[dim]Lockfile: {loader.lockfile_path}[/dim]")
        console.print(f"[dim]Generated: {lockfile.get('generated_at', 'unknown')}[/dim]")
        console.print(f"[dim]Schema version: {lockfile.get('version', '1.0')}[/dim]")


@sync_group.command(name="update")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Update global lockfile instead of local"
)
def sync_update(is_global: bool):
    """Update the workflows lockfile with current script state.

    Regenerates workflows.lock.json from the current script files,
    capturing their content hash, version, and other metadata.

    Examples:
        mcli sync update           # Update local lockfile
        mcli sync update --global  # Update global lockfile
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    scripts = loader.discover_scripts()
    if not scripts:
        scope = "global" if is_global else "local"
        warning(f"No {scope} workflow scripts found.")
        return 0

    if loader.save_lockfile():
        success(f"Updated lockfile: {loader.lockfile_path}")
        info(f"Tracked {len(scripts)} workflow script(s)")
        return 0
    else:
        error("Failed to update lockfile.")
        return 1


@sync_group.command(name="diff")
@click.option("--global", "-g", "is_global", is_flag=True, help="Diff global workflows")
def sync_diff(is_global: bool):
    """Show differences between current scripts and lockfile.

    Compares current script state against the lockfile and shows
    what has changed (added, removed, modified).

    Examples:
        mcli sync diff           # Show local changes
        mcli sync diff --global  # Show global changes
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    lockfile = loader.load_lockfile()
    if not lockfile:
        warning("No lockfile found. Run 'mcli sync update' to create one.")
        return 1

    verification = loader.verify_lockfile()
    locked_commands = lockfile.get("commands", {})

    has_changes = False

    # Added scripts
    if verification["extra"]:
        has_changes = True
        console.print("[green]Added scripts:[/green]")
        for name in verification["extra"]:
            console.print(f"  + {name}")
        console.print("")

    # Removed scripts
    if verification["missing"]:
        has_changes = True
        console.print("[red]Removed scripts:[/red]")
        for name in verification["missing"]:
            console.print(f"  - {name}")
        console.print("")

    # Modified scripts
    if verification["hash_mismatch"]:
        has_changes = True
        console.print("[yellow]Modified scripts:[/yellow]")
        for name in verification["hash_mismatch"]:
            if name in locked_commands:
                old_version = locked_commands[name].get("version", "?")
                # Get current version
                scripts = {p.stem: p for p in loader.discover_scripts()}
                if name in scripts:
                    script_info = loader.get_script_info(scripts[name])
                    new_version = script_info.get("version", "?")
                    console.print(f"  ~ {name} (v{old_version} -> v{new_version})")
                else:
                    console.print(f"  ~ {name}")
        console.print("")

    # Version-only changes (no hash change)
    version_only = [
        n
        for n in verification.get("version_mismatch", [])
        if n not in verification["hash_mismatch"]
    ]
    if version_only:
        console.print("[cyan]Version bumped (metadata only):[/cyan]")
        for name in version_only:
            console.print(f"  * {name}")
        console.print("")

    if not has_changes:
        success("No changes detected. Lockfile is in sync.")

    return 0


@sync_group.command(name="show")
@click.argument("name", required=False)
@click.option("--global", "-g", "is_global", is_flag=True, help="Show global lockfile")
def sync_show(name: Optional[str], is_global: bool):
    """Show lockfile contents or details for a specific script.

    If NAME is provided, shows detailed info for that script.
    Otherwise shows the full lockfile.

    Examples:
        mcli sync show                 # Show full lockfile
        mcli sync show my-workflow     # Show details for 'my-workflow'
        mcli sync show --global        # Show global lockfile
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    lockfile = loader.load_lockfile()
    if not lockfile:
        warning("No lockfile found. Run 'mcli sync update' to create one.")
        return 1

    if name:
        commands = lockfile.get("commands", {})
        if name not in commands:
            error(f"Script '{name}' not found in lockfile.")
            return 1

        script_info = commands[name]
        console.print(f"[cyan]Script: {name}[/cyan]\n")
        console.print(json.dumps(script_info, indent=2))
    else:
        console.print(f"[cyan]Lockfile: {loader.lockfile_path}[/cyan]\n")
        console.print(json.dumps(lockfile, indent=2))

    return 0


# ============================================================
# IPFS Sync Commands
# ============================================================


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
