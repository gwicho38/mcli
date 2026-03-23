"""
Python source sync for MCLI commands.

Provides opt-in bidirectional synchronization between Python source files
and JSON command definitions. Uses hash-based change detection and optional
file watching.

Commands:
    mcli link <command> --source <path>   Link a command to a source file
    mcli unlink <command>                 Remove source link
    mcli watch                            Start file watcher daemon
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console, error, info, success, warning

logger = get_logger(__name__)

SYNC_STATE_FILE = ".sync_state.json"


def _file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_sync_state_path(workflows_dir: Path) -> Path:
    """Get the sync state file path."""
    return workflows_dir / SYNC_STATE_FILE


def _load_sync_state(workflows_dir: Path) -> dict:
    """Load the sync state from disk."""
    state_path = _get_sync_state_path(workflows_dir)
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {"links": {}}


def _save_sync_state(workflows_dir: Path, state: dict):
    """Save the sync state to disk."""
    state_path = _get_sync_state_path(workflows_dir)
    state_path.write_text(json.dumps(state, indent=2))


def _resolve_workflows_dir(global_mode: bool) -> Path:
    """Resolve the workflows directory."""
    from mcli.lib.paths import get_mcli_home

    if global_mode:
        return get_mcli_home() / "workflows"
    return Path.cwd() / ".mcli" / "workflows"


def sync_source_to_command(source_path: Path, command_name: str, workflows_dir: Path) -> bool:
    """Sync a Python source file to a JSON command definition.

    Reads the source file, extracts metadata, and writes/updates
    the corresponding JSON command file.

    Returns True if sync was performed, False if no changes.
    """
    if not source_path.exists():
        error(f"Source file not found: {source_path}")
        return False

    state = _load_sync_state(workflows_dir)
    link = state.get("links", {}).get(command_name, {})
    current_hash = _file_hash(source_path)

    if link.get("source_hash") == current_hash:
        return False  # No changes

    # Read source and build JSON command
    code = source_path.read_text()

    # Extract metadata from comments
    metadata = {"description": "", "version": "1.0.0", "tags": []}
    for line in code.splitlines():
        line = line.strip()
        if line.startswith("# @description:"):
            metadata["description"] = line.split(":", 1)[1].strip()
        elif line.startswith("# @version:"):
            metadata["version"] = line.split(":", 1)[1].strip()
        elif line.startswith("# @tags:"):
            metadata["tags"] = [t.strip() for t in line.split(":", 1)[1].split(",")]

    # Write JSON command file
    from datetime import datetime

    json_path = workflows_dir / f"{command_name}.json"
    command_data = {
        "name": command_name,
        "description": metadata["description"],
        "code": code,
        "language": "python",
        "group": "workflow",
        "version": metadata["version"],
        "tags": metadata["tags"],
        "source_file": str(source_path.resolve()),
        "updated_at": datetime.now().isoformat(),
    }

    if json_path.exists():
        existing = json.loads(json_path.read_text())
        command_data["created_at"] = existing.get("created_at", command_data["updated_at"])
    else:
        command_data["created_at"] = command_data["updated_at"]

    json_path.write_text(json.dumps(command_data, indent=2))

    # Update sync state
    state.setdefault("links", {})[command_name] = {
        "source": str(source_path.resolve()),
        "source_hash": current_hash,
        "json_hash": _file_hash(json_path),
        "synced_at": datetime.now().isoformat(),
    }
    _save_sync_state(workflows_dir, state)

    return True


@click.group("source")
def source_group():
    """Manage Python source file sync for commands."""
    pass


@source_group.command("link")
@click.argument("command_name")
@click.option("--source", "-s", "source_path", required=True, help="Path to Python source file")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Use global workflows")
def link_cmd(command_name: str, source_path: str, global_mode: bool):
    """Link a command to a Python source file.

    Creates a bidirectional link between a .py source file and its
    JSON command definition. Changes to the source are synced on next run.

    Examples:
        mcli source link backup --source ./backup.py
        mcli source link -g deploy --source ~/scripts/deploy.py
    """
    src = Path(source_path).resolve()
    if not src.exists():
        error(f"Source file not found: {src}")
        return

    if not src.suffix == ".py":
        error("Only Python (.py) source files are supported")
        return

    workflows_dir = _resolve_workflows_dir(global_mode)
    if not workflows_dir.exists():
        workflows_dir.mkdir(parents=True, exist_ok=True)

    synced = sync_source_to_command(src, command_name, workflows_dir)
    if synced:
        success(f"Linked '{command_name}' to {src}")
    else:
        info(f"'{command_name}' already linked and up to date")


@source_group.command("unlink")
@click.argument("command_name")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Use global workflows")
def unlink_cmd(command_name: str, global_mode: bool):
    """Remove the source link for a command.

    The JSON command definition is preserved; only the sync link is removed.

    Examples:
        mcli source unlink backup
    """
    workflows_dir = _resolve_workflows_dir(global_mode)
    state = _load_sync_state(workflows_dir)

    if command_name not in state.get("links", {}):
        warning(f"No source link found for '{command_name}'")
        return

    del state["links"][command_name]
    _save_sync_state(workflows_dir, state)
    success(f"Unlinked '{command_name}' from source file")


@source_group.command("status")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Use global workflows")
def status_cmd(global_mode: bool):
    """Show sync status for all linked commands.

    Examples:
        mcli source status
        mcli source status -g
    """
    workflows_dir = _resolve_workflows_dir(global_mode)
    state = _load_sync_state(workflows_dir)
    links = state.get("links", {})

    if not links:
        info("No source links configured. Use 'mcli source link' to create one.")
        return

    table = Table(title="Source Sync Status")
    table.add_column("Command", style="cyan")
    table.add_column("Source", style="dim")
    table.add_column("Status", style="green")

    for name, link_data in sorted(links.items()):
        src = Path(link_data["source"])
        if not src.exists():
            status = "[red]Source missing[/red]"
        else:
            current_hash = _file_hash(src)
            if current_hash == link_data.get("source_hash"):
                status = "[green]In sync[/green]"
            else:
                status = "[yellow]Source changed[/yellow]"

        table.add_row(name, str(src), status)

    console.print(table)


@source_group.command("sync")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Use global workflows")
def sync_cmd(global_mode: bool):
    """Sync all linked source files to their commands.

    Examples:
        mcli source sync
        mcli source sync -g
    """
    workflows_dir = _resolve_workflows_dir(global_mode)
    state = _load_sync_state(workflows_dir)
    links = state.get("links", {})

    if not links:
        info("No source links to sync.")
        return

    synced = 0
    for name, link_data in links.items():
        src = Path(link_data["source"])
        if not src.exists():
            warning(f"Skipping '{name}': source file missing ({src})")
            continue

        if sync_source_to_command(src, name, workflows_dir):
            console.print(f"[green]\u2713[/green] Synced '{name}'")
            synced += 1

    if synced:
        success(f"Synced {synced} command(s)")
    else:
        info("All linked commands are up to date")


@source_group.command("watch")
@click.option("--global", "-g", "global_mode", is_flag=True, help="Use global workflows")
def watch_cmd(global_mode: bool):
    """Watch linked source files and auto-sync on changes.

    Runs in the foreground. Press Ctrl+C to stop.

    Examples:
        mcli source watch
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        error("watchdog is required for file watching: pip install watchdog")
        return

    workflows_dir = _resolve_workflows_dir(global_mode)
    state = _load_sync_state(workflows_dir)
    links = state.get("links", {})

    if not links:
        info("No source links to watch.")
        return

    # Build reverse map: source_path -> command_name
    watch_map: dict[str, str] = {}
    watch_dirs: set[str] = set()

    for name, link_data in links.items():
        src = Path(link_data["source"])
        if src.exists():
            watch_map[str(src)] = name
            watch_dirs.add(str(src.parent))

    if not watch_dirs:
        warning("No valid source files to watch")
        return

    class SyncHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            src_path = str(Path(event.src_path).resolve())
            cmd_name = watch_map.get(src_path)
            if cmd_name:
                if sync_source_to_command(Path(src_path), cmd_name, workflows_dir):
                    console.print(
                        f"[green]\u2713[/green] Auto-synced '{cmd_name}' from {event.src_path}"
                    )

    observer = Observer()
    handler = SyncHandler()

    for dir_path in watch_dirs:
        observer.schedule(handler, dir_path, recursive=False)

    observer.start()
    info(f"Watching {len(watch_map)} source file(s). Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[dim]Watcher stopped.[/dim]")

    observer.join()
