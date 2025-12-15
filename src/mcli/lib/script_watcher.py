"""
File watcher for script → JSON synchronization.

This module provides real-time file watching to automatically sync script files
to their JSON workflow representations when changes are detected.

Features:
- Watches for script file creation, modification, and deletion
- Automatically generates JSON on script creation
- Updates JSON when scripts are modified
- Removes JSON when scripts are deleted
- Debouncing to avoid multiple syncs from rapid changes

Example:
    >>> from mcli.lib.script_watcher import start_watcher
    >>> from mcli.lib.script_sync import ScriptSyncManager
    >>>
    >>> sync_manager = ScriptSyncManager(Path("~/.mcli/commands"))
    >>> observer = start_watcher(Path("~/.mcli/commands"), sync_manager)
    >>> # Watcher runs in background
    >>> observer.stop()
"""

from pathlib import Path
from threading import Timer
from typing import Dict, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

# Supported script extensions
SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".zsh", ".fish", ".js", ".ts", ".rb", ".pl", ".lua"}


class DebouncedScriptHandler(FileSystemEventHandler):
    """
    File system event handler with debouncing for script files.

    Debouncing prevents multiple syncs when editors save files multiple times
    in quick succession (e.g., vim swap files, editor auto-save).
    """

    def __init__(self, sync_manager, debounce_seconds: float = 0.5):
        """
        Initialize the debounced handler.

        Args:
            sync_manager: ScriptSyncManager instance
            debounce_seconds: Time to wait before processing events
        """
        super().__init__()
        self.sync_manager = sync_manager
        self.debounce_seconds = debounce_seconds
        self.pending_timers: dict[str, Timer] = {}

    def _is_script_file(self, path: Path) -> bool:
        """Check if path is a script file we should watch."""
        # Must be a file (not directory)
        if not path.is_file():
            return False

        # Must have supported extension
        if path.suffix not in SCRIPT_EXTENSIONS:
            return False

        # Skip hidden files
        if path.name.startswith("."):
            return False

        # Skip JSON files
        if path.suffix == ".json":
            return False

        return True

    def _debounced_sync(self, path: Path, action: str):
        """
        Debounce sync operations to avoid rapid repeated syncs.

        Args:
            path: Path to the script file
            action: Type of action ("create", "modify", "delete")
        """
        path_key = str(path)

        # Cancel pending timer for this path
        if path_key in self.pending_timers:
            self.pending_timers[path_key].cancel()

        # Create new timer
        def do_sync():
            try:
                if action == "delete":
                    self._handle_deletion(path)
                else:
                    self._handle_creation_or_modification(path)
            finally:
                # Remove from pending
                self.pending_timers.pop(path_key, None)

        timer = Timer(self.debounce_seconds, do_sync)
        self.pending_timers[path_key] = timer
        timer.start()

    def _handle_creation_or_modification(self, path: Path):
        """Handle script file creation or modification."""
        logger.info(f"Script changed: {path}")

        try:
            json_path = self.sync_manager.generate_json(path)
            if json_path:
                logger.info(f"Synced: {path} → {json_path}")
            else:
                logger.warning(f"Failed to sync: {path}")
        except Exception as e:
            logger.error(f"Error syncing {path}: {e}")

    def _handle_deletion(self, path: Path):
        """Handle script file deletion."""
        logger.info(f"Script deleted: {path}")

        try:
            # Remove corresponding JSON
            json_path = path.with_suffix(".json")
            if json_path.exists():
                # Only delete if auto-generated
                import json

                try:
                    with open(json_path) as f:
                        json_data = json.load(f)
                        if json_data.get("metadata", {}).get("auto_generated"):
                            json_path.unlink()
                            logger.info(f"Removed JSON: {json_path}")
                        else:
                            logger.info(f"Keeping manual JSON: {json_path}")
                except Exception as e:
                    logger.warning(f"Could not check if JSON is auto-generated: {e}")
        except Exception as e:
            logger.error(f"Error handling deletion of {path}: {e}")

    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        if self._is_script_file(path):
            logger.debug(f"File created: {path}")
            self._debounced_sync(path, "create")

    def on_modified(self, event):
        """Handle file modification event."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        if self._is_script_file(path):
            logger.debug(f"File modified: {path}")
            self._debounced_sync(path, "modify")

    def on_deleted(self, event):
        """Handle file deletion event."""
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Check if it was a script file (by extension)
        if path.suffix in SCRIPT_EXTENSIONS and not path.name.startswith("."):
            logger.debug(f"File deleted: {path}")
            self._debounced_sync(path, "delete")

    def on_moved(self, event):
        """Handle file move/rename event."""
        if event.is_directory:
            return

        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)

        # Treat move as delete + create
        if src_path.suffix in SCRIPT_EXTENSIONS:
            self._debounced_sync(src_path, "delete")

        if self._is_script_file(dest_path):
            self._debounced_sync(dest_path, "create")


def start_watcher(
    commands_dir: Path, sync_manager, debounce_seconds: float = 0.5
) -> Optional[Observer]:
    """
    Start file watcher for commands directory.

    The watcher runs in a background thread and monitors the commands directory
    for script file changes, automatically syncing to JSON as needed.

    Args:
        commands_dir: Directory to watch
        sync_manager: ScriptSyncManager instance
        debounce_seconds: Debounce delay for file events

    Returns:
        Observer instance if started successfully, None otherwise

    Example::

        # Create a sync manager first
        manager = ScriptSyncManager(commands_dir)
        observer = start_watcher(Path("~/.mcli/commands"), manager)
        # Do other work...
        observer.stop()
        observer.join()
    """
    if not commands_dir.exists():
        logger.warning(f"Commands directory does not exist: {commands_dir}")
        return None

    try:
        event_handler = DebouncedScriptHandler(sync_manager, debounce_seconds)
        observer = Observer()
        observer.schedule(event_handler, str(commands_dir), recursive=True)
        observer.start()

        logger.info(f"Started file watcher for {commands_dir}")
        return observer

    except Exception as e:
        logger.error(f"Failed to start file watcher: {e}")
        return None


def stop_watcher(observer: Observer, timeout: float = 5.0):
    """
    Stop file watcher gracefully.

    Args:
        observer: Observer instance to stop
        timeout: Maximum time to wait for observer to stop (seconds)
    """
    if observer is None:
        return

    try:
        logger.info("Stopping file watcher...")
        observer.stop()
        observer.join(timeout=timeout)

        if observer.is_alive():
            logger.warning("File watcher did not stop cleanly")
        else:
            logger.info("File watcher stopped")

    except Exception as e:
        logger.error(f"Error stopping file watcher: {e}")
