"""Sync and lockfile management commands for mcli.

Provides:
- IPFS synchronization of workflow state (push/pull)
- Lockfile management (status/update/diff)
- IPFS daemon initialization
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from mcli.lib.constants import IpfsMessages, SyncMessages
from mcli.lib.ipfs_utils import ipfs_daemon_running as _ipfs_daemon_running
from mcli.lib.ipfs_utils import ipfs_initialized as _ipfs_initialized
from mcli.lib.ipfs_utils import ipfs_installed as _ipfs_installed
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console, error, info, success, warning


@click.group(name="sync")
def sync_group():
    """🔄 Sync workflow state and manage lockfile.

    Setup:
        init       Initialize and start IPFS daemon
        info       Show mcli configuration and paths
        teardown   Remove workflows directory

    Lockfile Management:
        status   Show workflow scripts and their lockfile status
        update   Update lockfile with current script state
        diff     Show differences between scripts and lockfile
        show     Show lockfile contents

    IPFS Sync:
        push     Upload workflow state to IPFS
        pull     Download workflow state from IPFS
        verify   Verify lockfile or IPFS CID accessibility
        now      Update lockfile and push to IPFS in one command
    """
    pass


@sync_group.command(name="init")
@click.option("--install", "-i", is_flag=True, help="Install IPFS if not present (requires brew)")
@click.option("--foreground", "-f", is_flag=True, help="Run daemon in foreground (blocking)")
def sync_init(install: bool, foreground: bool):
    """🚀 Initialize and start the IPFS daemon.

    This command sets up IPFS for workflow synchronization:
    1. Checks if IPFS is installed (optionally installs with --install)
    2. Initializes IPFS if not already initialized
    3. Starts the IPFS daemon in the background

    Examples:
        mcli sync init              # Initialize and start daemon
        mcli sync init --install    # Install IPFS first (via brew)
        mcli sync init --foreground # Run daemon in foreground
    """
    # Step 1: Check/Install IPFS
    if not _ipfs_installed():
        if install:
            if sys.platform != "darwin":
                error("Auto-install only supported on macOS. Please install IPFS manually:")
                console.print("  https://docs.ipfs.tech/install/command-line/")
                return 1

            info("Installing IPFS via Homebrew...")
            result = subprocess.run(
                ["brew", "install", "ipfs"],
                capture_output=False,
            )
            if result.returncode != 0:
                error("Failed to install IPFS via brew.")
                console.print("[dim]Try: brew install ipfs[/dim]")
                return 1
            success("IPFS installed successfully!")
        else:
            error("IPFS is not installed.")
            console.print()
            console.print("[yellow]To install IPFS:[/yellow]")
            console.print("  [dim]macOS:[/dim]   brew install ipfs")
            console.print("  [dim]Linux:[/dim]   See https://docs.ipfs.tech/install/command-line/")
            console.print("  [dim]Windows:[/dim] See https://docs.ipfs.tech/install/command-line/")
            console.print()
            console.print("[dim]Or run: mcli sync init --install[/dim]")
            console.print()
            console.print(IpfsMessages.SETUP_HINT)
            return 1

    success("IPFS is installed")

    # Step 2: Initialize IPFS
    if not _ipfs_initialized():
        info("Initializing IPFS...")
        result = subprocess.run(
            ["ipfs", "init"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            error("Failed to initialize IPFS.")
            console.print(f"[dim]{result.stderr}[/dim]")
            return 1
        success("IPFS initialized!")
    else:
        info("IPFS already initialized")

    # Step 3: Check if daemon is already running
    if _ipfs_daemon_running():
        success("IPFS daemon is already running!")
        console.print()
        console.print("[green]✓ IPFS is ready for workflow sync[/green]")
        console.print("[dim]Try: mcli sync push[/dim]")
        return 0

    # Step 4: Start daemon
    if foreground:
        info("Starting IPFS daemon in foreground (Ctrl+C to stop)...")
        console.print()
        try:
            subprocess.run(["ipfs", "daemon"])
        except KeyboardInterrupt:
            console.print("\n[dim]Daemon stopped.[/dim]")
        return 0
    else:
        info("Starting IPFS daemon in background...")

        # Start daemon in background
        process = subprocess.Popen(
            ["ipfs", "daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Save PID for tracking
        pid_file = Path.home() / ".mcli" / "data" / "ipfs-daemon.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(process.pid))

        # Wait for daemon to start with health check
        import time

        import requests as _requests

        for _ in range(10):
            try:
                response = _requests.get("http://127.0.0.1:5001/api/v0/id", timeout=2)
                if response.ok:
                    break
            except Exception:
                time.sleep(1)

        if _ipfs_daemon_running():
            success("IPFS daemon started!")
            console.print()
            console.print("[green]✓ IPFS is ready for workflow sync[/green]")
            console.print(f"[dim]Daemon PID: {process.pid}[/dim]")
            console.print("[dim]Try: mcli sync push[/dim]")
            console.print("[dim]Stop with: pkill -f 'ipfs daemon'[/dim]")
            return 0
        else:
            warning("Daemon started but may still be initializing...")
            console.print("[dim]Check status with: mcli sync init[/dim]")
            return 0


# ============================================================
# Lockfile Management Commands
# ============================================================


@sync_group.command(name="status")
@click.option("--global", "-g", "is_global", is_flag=True, help="Show global workflow scripts")
def sync_status(is_global: bool):
    """📊 Show workflow scripts and their lockfile status.

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
    """🔒 Update the workflows lockfile with current script state.

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
    """📝 Show differences between current scripts and lockfile.

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
    """👁️ Show lockfile contents or details for a specific script.

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
    """⬆️ Push workflow state to IPFS.

    Uploads your current command lockfile to IPFS and returns an immutable
    CID (Content Identifier) that anyone can use to retrieve the exact same
    workflow state. If MCLI_SYNC_KEY is set, also publishes to IPNS for
    automatic resolution by teammates.

    Examples:
        mcli sync push
        mcli sync push -d "Production v1.0"
        mcli sync push --global
    """
    from mcli.lib.ipfs_sync import IPFSSync
    from mcli.lib.ipfs_utils import ensure_daemon_running
    from mcli.lib.ipns_manager import get_sync_key

    workflows_dir = get_custom_commands_dir(global_mode=global_mode)
    lockfile_path = workflows_dir / "commands.lock.json"

    if not lockfile_path.exists():
        error(SyncMessages.LOCKFILE_NOT_FOUND.format(path=lockfile_path))
        info(SyncMessages.RUN_UPDATE_LOCKFILE)
        return

    # Auto-ensure daemon is running
    if not ensure_daemon_running():
        error(SyncMessages.DAEMON_START_FAILED)
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

        # Show IPNS info if published
        if get_sync_key():
            console.print()
            info("Teammates can pull latest with: mcli sync pull")
    else:
        error(SyncMessages.FAILED_PUSH_IPFS)


@sync_group.command(name="pull")
@click.argument("cid", required=False)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file path")
@click.option("--no-verify", is_flag=True, help="Skip hash verification")
@click.option("--repo", "-r", help="Override repo name for IPNS resolution (cross-repo pull)")
def sync_pull_command(
    cid: Optional[str], output: Optional[Path], no_verify: bool, repo: Optional[str]
):
    """⬇️ Pull workflow state from IPFS.

    If CID is provided, retrieves that exact version. If CID is omitted and
    MCLI_SYNC_KEY is set, automatically resolves the latest via IPNS.

    Examples:
        mcli sync pull                           # Auto-resolve via IPNS
        mcli sync pull QmXyZ123...               # Pull specific CID
        mcli sync pull --repo other-project      # Pull from different repo
        mcli sync pull QmXyZ123... -o my-cmds.json
    """
    import json

    from mcli.lib.ipfs_sync import IPFSSync
    from mcli.lib.ipfs_utils import ensure_daemon_running

    ipfs = IPFSSync()

    if cid:
        # Explicit CID — just retrieve it
        info(SyncMessages.RETRIEVING_FROM_IPFS.format(cid=cid))
        data = ipfs.pull(cid, verify=not no_verify)
    else:
        # No CID — resolve via IPNS
        if not ensure_daemon_running():
            error(SyncMessages.DAEMON_START_FAILED)
            return

        info(SyncMessages.IPNS_RESOLVING)
        data = ipfs.pull_latest(scope="global", repo_name=repo)

        if data is None:
            from mcli.lib.ipns_manager import get_sync_key

            if not get_sync_key():
                error(SyncMessages.IPNS_NO_SYNC_KEY)
                console.print(SyncMessages.IPNS_SYNC_KEY_HINT)
                console.print(SyncMessages.IPNS_PULL_HINT)
            else:
                error(SyncMessages.IPNS_RESOLVE_FAILED)
                console.print(SyncMessages.IPNS_PULL_HINT)
            return

    if data:
        success(SyncMessages.RETRIEVED_FROM_IPFS)

        # Determine output path
        if output:
            output_path = output
        else:
            output_path = Path(f"commands_{(cid or 'latest')[:8]}.json")

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
    """📜 Show IPFS sync history.

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
    """✅ Verify that a CID is accessible on IPFS.

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


@sync_group.command(name="now")
@click.option("--global", "-g", "is_global", is_flag=True, help="Sync global workflows")
@click.option("--description", "-d", help="Description for IPFS sync")
def sync_now(is_global: bool, description: str):
    """⚡ Update lockfile and push to IPFS in one command.

    Combines 'update' and 'push' into a single operation:
    1. Updates the lockfile with current script state
    2. Pushes to IPFS for distributed backup

    Examples:
        mcli sync now                    # Sync local workflows
        mcli sync now --global           # Sync global workflows
        mcli sync now -d "v1.0 release"  # Sync with description
    """
    scope = "global" if is_global else "local"
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    # Step 1: Check for scripts
    scripts = loader.discover_scripts()
    if not scripts:
        warning(f"No {scope} workflow scripts found.")
        return 1

    # Step 2: Update lockfile
    info(f"🔒 Updating {scope} lockfile...")
    if not loader.save_lockfile():
        error("Failed to update lockfile.")
        return 1
    success(f"Updated lockfile with {len(scripts)} script(s)")

    # Step 3: Push to IPFS
    info("⬆️ Pushing to IPFS...")
    from mcli.lib.ipfs_utils import ensure_daemon_running

    if not ensure_daemon_running():
        warning("IPFS daemon not available. Lockfile updated but not pushed to IPFS.")
        return 0

    from mcli.lib.ipfs_sync import IPFSSync
    from mcli.lib.ipns_manager import get_sync_key

    ipfs = IPFSSync()

    lockfile_path = loader.lockfile_path
    cid = ipfs.push(lockfile_path, description=description or "")

    if cid:
        success("✅ Sync complete!")
        console.print(f"\n[bold cyan]CID:[/bold cyan] {cid}")
        console.print(f"[dim]Retrieve with: mcli sync pull {cid}[/dim]")
        if get_sync_key():
            console.print("[dim]Teammates can pull latest with: mcli sync pull[/dim]")
    else:
        error("Failed to push to IPFS.")
        return 1

    return 0


# ============================================================
# Configuration Commands (moved from config_cmd)
# ============================================================


@sync_group.command(name="teardown")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Teardown global workflows directory",
)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def sync_teardown(is_global: bool, force: bool):
    """🗑️ Remove workflows directory and configuration.

    This will delete all custom workflows and configuration.
    Use with caution - this cannot be undone!

    Examples:
        mcli sync teardown           # Remove local workflows
        mcli sync teardown --global  # Remove global workflows
        mcli sync teardown --force   # Skip confirmation
    """
    from rich.prompt import Prompt

    from mcli.lib.paths import get_local_mcli_dir, get_mcli_home, is_git_repository

    # Determine directory to remove
    in_git_repo = is_git_repository() and not is_global

    if not is_global and in_git_repo:
        local_mcli = get_local_mcli_dir()
        if local_mcli is not None:
            workflows_dir = local_mcli / "workflows"
        else:
            workflows_dir = get_mcli_home() / "workflows"
    else:
        workflows_dir = get_mcli_home() / "workflows"

    if not workflows_dir.exists():
        info(f"Workflows directory does not exist: {workflows_dir}")
        return 0

    # Count items
    items = list(workflows_dir.glob("*"))
    workflow_count = len([f for f in items if f.suffix in [".py", ".sh", ".js", ".ts", ".ipynb"]])

    if not force:
        warning(f"This will delete {workflow_count} workflow(s) from: {workflows_dir}")
        should_delete = Prompt.ask("Are you sure?", choices=["y", "n"], default="n")
        if should_delete.lower() != "y":
            info("Teardown cancelled")
            return 0

    try:
        shutil.rmtree(workflows_dir)
        success(f"Removed workflows directory: {workflows_dir}")
    except Exception as e:
        error(f"Failed to remove directory: {e}")
        return 1

    return 0


@sync_group.command(name="info")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Show global configuration",
)
def sync_info(is_global: bool):
    """ℹ️ Show mcli configuration and paths.

    Displays the current configuration including paths, settings,
    and environment variables.

    Examples:
        mcli sync info           # Show local configuration
        mcli sync info --global  # Show global configuration
    """
    from mcli.lib.paths import (
        get_custom_commands_dir,
        get_git_root,
        get_local_mcli_dir,
        get_mcli_home,
        is_git_repository,
    )

    console.print("[bold]MCLI Configuration[/bold]")
    console.print()

    # Environment
    in_git_repo = is_git_repository()
    git_root = get_git_root() if in_git_repo else None

    console.print("[bold cyan]Environment:[/bold cyan]")
    console.print(f"  In git repository: {'Yes' if in_git_repo else 'No'}")
    if git_root:
        console.print(f"  Git root: {git_root}")
    console.print()

    # Paths
    console.print("[bold cyan]Paths:[/bold cyan]")
    console.print(f"  MCLI home: {get_mcli_home()}")

    local_mcli = get_local_mcli_dir()
    if local_mcli:
        console.print(f"  Local .mcli: {local_mcli}")

    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    console.print(f"  Workflows directory: {workflows_dir}")

    lockfile = workflows_dir / "commands.lock.json"
    console.print(f"  Lockfile: {lockfile} ({'exists' if lockfile.exists() else 'missing'})")
    console.print()

    # Stats
    if workflows_dir.exists():
        console.print("[bold cyan]Workflows:[/bold cyan]")
        py_count = len(list(workflows_dir.glob("*.py")))
        sh_count = len(list(workflows_dir.glob("*.sh")))
        js_count = len(list(workflows_dir.glob("*.js")))
        ts_count = len(list(workflows_dir.glob("*.ts")))
        nb_count = len(list(workflows_dir.glob("*.ipynb")))
        total = py_count + sh_count + js_count + ts_count + nb_count

        console.print(f"  Total: {total}")
        if py_count:
            console.print(f"  Python: {py_count}")
        if sh_count:
            console.print(f"  Shell: {sh_count}")
        if js_count:
            console.print(f"  JavaScript: {js_count}")
        if ts_count:
            console.print(f"  TypeScript: {ts_count}")
        if nb_count:
            console.print(f"  Notebooks: {nb_count}")

    # IPFS status
    console.print()
    console.print("[bold cyan]IPFS Status:[/bold cyan]")
    if _ipfs_installed():
        console.print("  Installed: Yes")
        console.print(f"  Initialized: {'Yes' if _ipfs_initialized() else 'No'}")
        console.print(f"  Daemon running: {'Yes' if _ipfs_daemon_running() else 'No'}")
    else:
        console.print("  Installed: No")
        console.print("  [dim]Install with: brew install ipfs[/dim]")
