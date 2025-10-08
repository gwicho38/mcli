import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import psutil
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    HAS_WATCHDOG = True
except ImportError:
    # Watchdog not available, file watching will be disabled
    HAS_WATCHDOG = False
    FileSystemEventHandler = object  # Stub for inheritance
    Observer = None

# Import existing utilities
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

logger = get_logger(__name__)


# Stub CommandDatabase for backward compatibility
# Commands are now managed via JSON files in ~/.mcli/commands/
class CommandDatabase:
    """Stub database for backward compatibility.
    Commands are now stored as JSON files and loaded via the custom commands system.
    """
    def __init__(self, db_path: Optional[str] = None):
        logger.debug("CommandDatabase stub initialized - commands now managed via JSON files")
        pass


@dataclass
class Command:
    """Represents a stored command"""

    id: str
    name: str
    description: str
    code: str
    language: str  # 'python', 'node', 'lua', 'shell'
    group: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    execution_count: int = 0
    last_executed: Optional[datetime] = None
    is_active: bool = True


class CommandFileWatcher(FileSystemEventHandler):
    """Watches a directory for command file changes and updates the registry."""

    def __init__(self, db, watch_dir: str):
        self.db = db
        self.watch_dir = Path(watch_dir)
        self.observer = Observer()
        self.observer.schedule(self, str(self.watch_dir), recursive=False)
        self.observer.start()

    def on_modified(self, event):
        if event.is_directory:
            return
        self._reload_command_file(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self._reload_command_file(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        # Remove command from DB if file deleted
        cmd_id = Path(event.src_path).stem
        self.db.delete_command(cmd_id)

    def _reload_command_file(self, file_path):
        # Example: expects each file to be a JSON with command fields
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            cmd = Command(
                id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                code=data["code"],
                language=data["language"],
                group=data.get("group"),
                tags=data.get("tags", []),
                created_at=(
                    datetime.fromisoformat(data["created_at"])
                    if data.get("created_at")
                    else datetime.now()
                ),
                updated_at=(
                    datetime.fromisoformat(data["updated_at"])
                    if data.get("updated_at")
                    else datetime.now()
                ),
                execution_count=data.get("execution_count", 0),
                last_executed=(
                    datetime.fromisoformat(data["last_executed"])
                    if data.get("last_executed")
                    else None
                ),
                is_active=data.get("is_active", True),
            )
            # Upsert: try update, else add
            if not self.db.update_command(cmd):
                self.db.add_command(cmd)
        except Exception as e:
            logger.error(f"Failed to reload command file {file_path}: {e}")


def start_command_file_watcher(db, watch_dir: str = None):
    """Start a file watcher for command files (JSON) in a directory."""
    if watch_dir is None:
        watch_dir = str(Path.home() / ".local" / "mcli" / "daemon" / "commands")
    Path(watch_dir).mkdir(parents=True, exist_ok=True)
    watcher = CommandFileWatcher(db, watch_dir)
    logger.info(f"Started command file watcher on {watch_dir}")
    return watcher
    """Manages command storage and retrieval"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path.home() / ".local" / "mcli" / "daemon" / "commands.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

        # Initialize vectorizer for similarity search
        self.vectorizer = TfidfVectorizer(
            max_features=1000, stop_words="english", ngram_range=(1, 2)
        )
        self._update_embeddings()

    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Commands table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                code TEXT NOT NULL,
                language TEXT NOT NULL,
                group_name TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                last_executed TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """
        )

        # Groups table for hierarchical organization
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                parent_group_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_group_id) REFERENCES groups (id)
            )
        """
        )

        # Execution history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                command_id TEXT NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                output TEXT,
                error TEXT,
                execution_time_ms INTEGER,
                FOREIGN KEY (command_id) REFERENCES commands (id)
            )
        """
        )

        conn.commit()
        conn.close()

    def _update_embeddings(self):
        """Update TF-IDF embeddings for similarity search"""
        commands = self.get_all_commands()
        if not commands:
            return

        # Combine name, description, and tags for embedding
        texts = []
        for cmd in commands:
            text_parts = [cmd.name, cmd.description or ""]
            text_parts.extend(cmd.tags or [])
            texts.append(" ".join(text_parts))

        if texts:
            self.vectorizer.fit(texts)

    def add_command(self, command: Command) -> str:
        """Add a new command to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO commands 
                (id, name, description, code, language, group_name, tags, 
                 created_at, updated_at, execution_count, last_executed, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    command.id,
                    command.name,
                    command.description,
                    command.code,
                    command.language,
                    command.group,
                    json.dumps(command.tags),
                    command.created_at.isoformat(),
                    command.updated_at.isoformat(),
                    command.execution_count,
                    command.last_executed.isoformat() if command.last_executed else None,
                    command.is_active,
                ),
            )

            conn.commit()
            self._update_embeddings()
            return command.id

        except Exception as e:
            logger.error(f"Error adding command: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_command(self, command_id: str) -> Optional[Command]:
        """Get a command by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, name, description, code, language, group_name, tags,
                       created_at, updated_at, execution_count, last_executed, is_active
                FROM commands WHERE id = ?
            """,
                (command_id,),
            )

            row = cursor.fetchone()
            if row:
                return self._row_to_command(row)
            return None

        finally:
            conn.close()

    def get_all_commands(self, include_inactive: bool = False) -> List[Command]:
        """Get all commands, optionally including inactive ones"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            if include_inactive:
                cursor.execute(
                    """
                    SELECT id, name, description, code, language, group_name, tags,
                           created_at, updated_at, execution_count, last_executed, is_active
                    FROM commands
                    ORDER BY name
                """
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name, description, code, language, group_name, tags,
                           created_at, updated_at, execution_count, last_executed, is_active
                    FROM commands WHERE is_active = 1
                    ORDER BY name
                """
                )
            return [self._row_to_command(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def search_commands(self, query: str, limit: int = 10) -> List[Command]:
        """Search commands by name, description, or tags"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Simple text search
            search_term = f"%{query}%"
            cursor.execute(
                """
                SELECT id, name, description, code, language, group_name, tags,
                       created_at, updated_at, execution_count, last_executed, is_active
                FROM commands 
                WHERE is_active = 1 
                AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)
                ORDER BY name
                LIMIT ?
            """,
                (search_term, search_term, search_term, limit),
            )

            return [self._row_to_command(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    def find_similar_commands(self, query: str, limit: int = 5) -> List[tuple]:
        """Find similar commands using cosine similarity"""
        commands = self.get_all_commands()
        if not commands:
            return []

        # Prepare query text
        query_text = query.lower()

        # Get command texts for comparison
        command_texts = []
        for cmd in commands:
            text_parts = [cmd.name, cmd.description or ""]
            text_parts.extend(cmd.tags or [])
            command_texts.append(" ".join(text_parts).lower())

        if not command_texts:
            return []

        # Calculate similarities
        try:
            # Transform query and commands
            query_vector = self.vectorizer.transform([query_text])
            command_vectors = self.vectorizer.transform(command_texts)

            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, command_vectors).flatten()

            # Sort by similarity
            command_similarities = list(zip(commands, similarities))
            command_similarities.sort(key=lambda x: x[1], reverse=True)

            return command_similarities[:limit]

        except Exception as e:
            logger.error(f"Error calculating similarities: {e}")
            return []

    def update_command(self, command: Command) -> bool:
        """Update an existing command"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE commands 
                SET name = ?, description = ?, code = ?, language = ?, 
                    group_name = ?, tags = ?, updated_at = ?, is_active = ?
                WHERE id = ?
            """,
                (
                    command.name,
                    command.description,
                    command.code,
                    command.language,
                    command.group,
                    json.dumps(command.tags),
                    datetime.now().isoformat(),
                    command.is_active,
                    command.id,
                ),
            )

            conn.commit()
            self._update_embeddings()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating command: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_command(self, command_id: str) -> bool:
        """Delete a command (soft delete)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE commands SET is_active = 0 WHERE id = ?
            """,
                (command_id,),
            )

            conn.commit()
            self._update_embeddings()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting command: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def record_execution(
        self,
        command_id: str,
        status: str,
        output: str = None,
        error: str = None,
        execution_time_ms: int = None,
    ):
        """Record command execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Record execution
            execution_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO executions 
                (id, command_id, executed_at, status, output, error, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    execution_id,
                    command_id,
                    datetime.now().isoformat(),
                    status,
                    output,
                    error,
                    execution_time_ms,
                ),
            )

            # Update command stats
            cursor.execute(
                """
                UPDATE commands 
                SET execution_count = execution_count + 1, 
                    last_executed = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), command_id),
            )

            conn.commit()

        except Exception as e:
            logger.error(f"Error recording execution: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _row_to_command(self, row) -> Command:
        """Convert database row to Command object"""
        return Command(
            id=row[0],
            name=row[1],
            description=row[2],
            code=row[3],
            language=row[4],
            group=row[5],
            tags=json.loads(row[6]) if row[6] else [],
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
            execution_count=row[9],
            last_executed=datetime.fromisoformat(row[10]) if row[10] else None,
            is_active=bool(row[11]),
        )


class CommandExecutor:
    """Handles safe execution of commands in different languages"""

    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "mcli_daemon"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Language-specific execution environments
        self.language_handlers = {
            "python": self._execute_python,
            "node": self._execute_node,
            "lua": self._execute_lua,
            "shell": self._execute_shell,
        }

    def execute_command(self, command: Command, args: List[str] = None) -> Dict[str, Any]:
        """Execute a command safely"""
        start_time = time.time()

        try:
            # Get the appropriate handler
            handler = self.language_handlers.get(command.language)
            if not handler:
                raise ValueError(f"Unsupported language: {command.language}")

            # Execute the command
            result = handler(command, args or [])

            execution_time = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "execution_time_ms": execution_time,
                "status": "completed",
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "execution_time_ms": execution_time,
                "status": "failed",
            }

    def _execute_python(self, command: Command, args: List[str]) -> Dict[str, str]:
        """Execute Python code safely"""
        # Create temporary file
        script_file = self.temp_dir / f"{command.id}_{int(time.time())}.py"

        try:
            # Write code to file
            with open(script_file, "w") as f:
                f.write(command.code)

            # Execute with subprocess
            result = subprocess.run(
                [sys.executable, str(script_file)] + args,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=self.temp_dir,
            )

            return {"output": result.stdout, "error": result.stderr}

        finally:
            # Clean up
            if script_file.exists():
                script_file.unlink()

    def _execute_node(self, command: Command, args: List[str]) -> Dict[str, str]:
        """Execute Node.js code safely"""
        script_file = self.temp_dir / f"{command.id}_{int(time.time())}.js"

        try:
            with open(script_file, "w") as f:
                f.write(command.code)

            result = subprocess.run(
                ["node", str(script_file)] + args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.temp_dir,
            )

            return {"output": result.stdout, "error": result.stderr}

        finally:
            if script_file.exists():
                script_file.unlink()

    def _execute_lua(self, command: Command, args: List[str]) -> Dict[str, str]:
        """Execute Lua code safely"""
        script_file = self.temp_dir / f"{command.id}_{int(time.time())}.lua"

        try:
            with open(script_file, "w") as f:
                f.write(command.code)

            result = subprocess.run(
                ["lua", str(script_file)] + args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.temp_dir,
            )

            return {"output": result.stdout, "error": result.stderr}

        finally:
            if script_file.exists():
                script_file.unlink()

    def _execute_shell(self, command: Command, args: List[str]) -> Dict[str, str]:
        """Execute shell commands safely"""
        script_file = self.temp_dir / f"{command.id}_{int(time.time())}.sh"

        try:
            with open(script_file, "w") as f:
                f.write("#!/bin/bash\n")
                f.write(command.code)

            # Make executable
            script_file.chmod(0o755)

            result = subprocess.run(
                [str(script_file)] + args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.temp_dir,
            )

            return {"output": result.stdout, "error": result.stderr}

        finally:
            if script_file.exists():
                script_file.unlink()


class DaemonService:
    """Background daemon service for command management"""

    def __init__(self, config_path: Optional[str] = None):
        # Load configuration from TOML
        if config_path is None:
            # Try to find config.toml in common locations
            config_paths = [
                Path("config.toml"),  # Current directory
                Path.home() / ".config" / "mcli" / "config.toml",  # User config
                Path(__file__).parent.parent.parent.parent.parent / "config.toml",  # Project root
            ]

            for path in config_paths:
                if path.exists():
                    config_path = str(path)
                    break

        self.config = {}
        if config_path:
            try:
                # Load paths configuration
                paths_config = read_from_toml(config_path, "paths")
                if paths_config:
                    self.config["paths"] = paths_config
                logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                logger.warning(f"Could not load config from {config_path}: {e}")

        self.db = CommandDatabase()
        self.executor = CommandExecutor()
        self.running = False
        self.pid_file = Path.home() / ".local" / "mcli" / "daemon" / "daemon.pid"
        self.socket_file = Path.home() / ".local" / "mcli" / "daemon" / "daemon.sock"

        # Ensure daemon directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def start(self):
        """Start the daemon service"""
        if self.running:
            logger.info("Daemon is already running")
            return

        # Check if already running
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    logger.info(f"Daemon already running with PID {pid}")
                    return
            except Exception:
                pass

        # Start daemon
        self.running = True

        # Write PID file
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        logger.info(f"Daemon started with PID {os.getpid()}")

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Start main loop
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Daemon interrupted")
        finally:
            self.stop()

    def stop(self):
        """Stop the daemon service"""
        if not self.running:
            return

        self.running = False

        # Remove PID file
        if self.pid_file.exists():
            self.pid_file.unlink()

        logger.info("Daemon stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def _main_loop(self):
        """Main daemon loop"""
        logger.info("Daemon main loop started")

        while self.running:
            try:
                # Check for commands to execute
                # This is a simple implementation - in a real system you'd use
                # a message queue or socket communication
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)

    def status(self) -> Dict[str, Any]:
        """Get daemon status"""
        is_running = False
        pid = None

        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                is_running = psutil.pid_exists(pid)
            except Exception:
                pass

        return {
            "running": is_running,
            "pid": pid,
            "pid_file": str(self.pid_file),
            "socket_file": str(self.socket_file),
        }


# CLI Commands
@click.group(name="daemon")
def daemon():
    """Daemon service for command management"""
    pass


@daemon.command()
@click.option("--config", help="Path to configuration file")
def start(config: Optional[str]):
    """Start the daemon service"""
    service = DaemonService(config)
    service.start()


@daemon.command()
def stop():
    """Stop the daemon service"""
    pid_file = Path.home() / ".local" / "mcli" / "daemon" / "daemon.pid"

    if not pid_file.exists():
        click.echo("Daemon is not running")
        return

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        # Send SIGTERM
        os.kill(pid, signal.SIGTERM)
        click.echo(f"Sent stop signal to daemon (PID {pid})")

        # Wait a bit and check if it stopped
        time.sleep(2)
        if not psutil.pid_exists(pid):
            click.echo("Daemon stopped successfully")
        else:
            click.echo("Daemon may still be running")

    except Exception as e:
        click.echo(f"Error stopping daemon: {e}")


@daemon.command()
def status():
    """Show daemon status"""
    service = DaemonService()
    status_info = service.status()
    if status_info["running"]:
        click.echo(f"✅ Daemon is running (PID: {status_info['pid']})")
    else:
        click.echo("❌ Daemon is not running")
    click.echo(f"PID file: {status_info['pid_file']}")
    click.echo(f"Socket file: {status_info['socket_file']}")


# --- New CLI: list-commands ---
@daemon.command("list-commands")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--all", "show_all", is_flag=True, help="Show all commands, including inactive")
def list_commands(as_json, show_all):
    """List all available commands (optionally including inactive)"""
    import sys

    service = DaemonService()
    commands = service.db.get_all_commands(include_inactive=show_all)
    result = []
    for cmd in commands:
        result.append(
            {
                "id": cmd.id,
                "name": cmd.name,
                "description": cmd.description,
                "language": cmd.language,
                "group": cmd.group,
                "tags": cmd.tags,
                "created_at": cmd.created_at.isoformat() if cmd.created_at else None,
                "updated_at": cmd.updated_at.isoformat() if cmd.updated_at else None,
                "execution_count": cmd.execution_count,
                "last_executed": cmd.last_executed.isoformat() if cmd.last_executed else None,
                "is_active": cmd.is_active,
            }
        )
    if as_json:
        import json

        print(json.dumps({"commands": result}, indent=2))
    else:
        for cmd in result:
            status = "[INACTIVE] " if not cmd["is_active"] else ""
            click.echo(f"{status}- {cmd['name']} ({cmd['language']}) : {cmd['description']}")


# --- New CLI: execute ---
@daemon.command("execute")
@click.argument("command_name")
@click.argument("args", nargs=-1)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def execute_command(command_name, args, as_json):
    """Execute a command by name with optional arguments"""
    import sys

    service = DaemonService()
    # Find command by name
    commands = service.db.get_all_commands()
    cmd = next((c for c in commands if c.name == command_name), None)
    if not cmd:
        msg = f"Command '{command_name}' not found."
        if as_json:
            import json

            print(json.dumps({"success": False, "error": msg}))
        else:
            click.echo(msg)
        return
    result = service.executor.execute_command(cmd, list(args))
    if as_json:
        import json

        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            click.echo(result.get("output", ""))
        else:
            click.echo(f"Error: {result.get('error', '')}")


# Client commands - these will be moved to the client module
# but we'll keep the core daemon service commands here

if __name__ == "__main__":
    # Start file watcher for hot-reloading file-based commands
    db = CommandDatabase()
    start_command_file_watcher(db)
    daemon()
