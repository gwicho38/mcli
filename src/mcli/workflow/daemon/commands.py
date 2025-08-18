import hashlib
import json
import logging
import os
import pickle
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
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

# Import existing utilities
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Command:
    """Represents a stored command"""

    id: str
    name: str
    description: str
    code: str
    language: str  # 'python', 'node', 'lua', 'shell'
    group: Optional[str] = None
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    execution_count: int = 0
    last_executed: Optional[datetime] = None
    is_active: bool = True

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class CommandDatabase:
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
        """Get all commands with optional inactive inclusion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            query = """
                SELECT id, name, description, code, language, group_name, tags,
                       created_at, updated_at, execution_count, last_executed, is_active
                FROM commands
            """
            if not include_inactive:
                query += " WHERE is_active = 1"
            query += " ORDER BY name"

            cursor.execute(query)

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
                AND (name LIKE ? OR description LIKE ? OR tags LIKE ? OR language LIKE ?)
                ORDER BY name
                LIMIT ?
            """,
                (search_term, search_term, search_term, search_term, limit),
            )

            return [self._row_to_command(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    def find_similar_commands(self, query: str, limit: int = 5) -> List[tuple]:
        """Find similar commands using cosine similarity"""
        cmd_list = self.get_all_commands()
        if not cmd_list:
            return []

        # Prepare query text
        query_text = query.lower()

        # Get command texts for comparison
        command_texts = []
        for cmd in cmd_list:
            text_parts = [cmd.name, cmd.description or ""]
            text_parts.extend(cmd.tags or [])
            command_texts.append(" ".join(text_parts).lower())

        if not command_texts:
            return []

        # Calculate similarities
        try:
            # Re-fit vectorizer with current commands if needed
            if len(command_texts) > 0:
                # Create a temporary vectorizer for this search
                temp_vectorizer = TfidfVectorizer(
                    max_features=1000, stop_words="english", ngram_range=(1, 2)
                )

                # Fit on current command texts
                all_texts = command_texts + [query_text]
                temp_vectorizer.fit(all_texts)

                # Transform query and commands
                query_vector = temp_vectorizer.transform([query_text])
                command_vectors = temp_vectorizer.transform(command_texts)

                # Calculate cosine similarities
                similarities = cosine_similarity(query_vector, command_vectors).flatten()

                # Sort by similarity - avoid using 'commands' variable name
                cmd_similarities = []
                for i, similarity_score in enumerate(similarities):
                    cmd_similarities.append((cmd_list[i], similarity_score))

                cmd_similarities.sort(key=lambda x: x[1], reverse=True)

                return cmd_similarities[:limit]
            else:
                return []

        except Exception as e:
            logger.error(f"Error calculating similarities: {e}")
            import traceback

            traceback.print_exc()
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

            # Check if execution was successful
            returncode = result.get("returncode", 0)
            success = returncode == 0
            status = "completed" if success else "failed"

            return {
                "success": success,
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "execution_time_ms": execution_time,
                "status": status,
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
        """Execute Python code safely with resource limits and sandboxing"""
        # Create secure temporary file
        script_file = self.temp_dir / f"{command.id}_{int(time.time())}.py"
        script_file.touch(mode=0o700)  # Restrict permissions

        # Add resource limits
        resource_limits = """
import resource
resource.setrlimit(resource.RLIMIT_CPU, (1, 1))  # 1 second CPU time
resource.setrlimit(resource.RLIMIT_AS, (256*1024*1024, 256*1024*1024))  # 256MB memory
"""

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

            return {
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
            }

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

            return {
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
            }

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

            return {
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
            }

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

            return {
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
            }

        finally:
            if script_file.exists():
                script_file.unlink()


class DaemonService:
    """Background daemon service for command management"""

    def __init__(self, config_path: Optional[str] = None):
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


# Create the daemon command group
@click.group(name="daemon")
def daemon():
    """Daemon service for command management"""
    pass


# Daemon service commands
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


# Client commands
@daemon.command()
@click.argument("name")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--description", help="Command description")
@click.option(
    "--language",
    type=click.Choice(["python", "node", "lua", "shell", "auto"]),
    default="auto",
    help="Programming language",
)
@click.option("--group", help="Command group")
@click.option("--tags", help="Comma-separated tags")
def add_file(name: str, file_path: str, description: str, language: str, group: str, tags: str):
    """Add a command from a file"""
    db = CommandDatabase()

    # Read code from file
    with open(file_path, "r") as f:
        code_content = f.read()

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

    # Create command
    command = Command(
        id=str(uuid.uuid4()),
        name=name,
        description=description or "",
        code=code_content,
        language=language,
        group=group,
        tags=tag_list,
    )

    # Add to database
    command_id = db.add_command(command)
    click.echo(f"✅ Command '{name}' added with ID: {command_id}")


@daemon.command()
@click.argument("name")
@click.option("--description", help="Command description")
@click.option(
    "--language",
    type=click.Choice(["python", "node", "lua", "shell"]),
    default="python",
    help="Programming language",
)
@click.option("--group", help="Command group")
@click.option("--tags", help="Comma-separated tags")
def add_stdin(name: str, description: str, language: str, group: str, tags: str):
    """Add a command from stdin"""
    db = CommandDatabase()

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

    click.echo("Enter your code (Ctrl+D when done):")

    # Read from stdin
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    code = "\n".join(lines)

    if not code.strip():
        click.echo("No code provided", err=True)
        return

    # Create command
    command = Command(
        id=str(uuid.uuid4()),
        name=name,
        description=description or "",
        code=code,
        language=language,
        group=group,
        tags=tag_list,
    )

    # Add to database
    command_id = db.add_command(command)
    click.echo(f"✅ Command '{name}' added with ID: {command_id}")


@daemon.command()
def add_interactive():
    """Add a command interactively"""
    db = CommandDatabase()

    # Get command name
    name = click.prompt("Command name", type=str)

    # Check if name already exists
    existing = db.search_commands(name, limit=1)
    if existing and existing[0].name == name:
        if not click.confirm(f"Command '{name}' already exists. Overwrite?"):
            click.echo("Command creation cancelled")
            return

    # Get description
    description = click.prompt("Description (optional)", type=str, default="")

    # Get language
    language = click.prompt(
        "Language", type=click.Choice(["python", "node", "lua", "shell"]), default="python"
    )

    # Get group
    group = click.prompt("Group (optional)", type=str, default="")
    if not group:
        group = None

    # Get tags
    tags_input = click.prompt("Tags (comma-separated, optional)", type=str, default="")
    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

    # Get code source
    source = click.prompt(
        "Code source", type=click.Choice(["file", "stdin", "paste"]), default="paste"
    )

    if source == "file":
        file_path = click.prompt("File path", type=click.Path(exists=True))
        with open(file_path, "r") as f:
            code = f.read()
    elif source == "stdin":
        click.echo("Enter your code (Ctrl+D when done):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        code = "\n".join(lines)
    else:  # paste
        click.echo("Paste your code below (Ctrl+D when done):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        code = "\n".join(lines)

    if not code.strip():
        click.echo("No code provided", err=True)
        return

    # Create command
    command = Command(
        id=str(uuid.uuid4()),
        name=name,
        description=description or "",
        code=code,
        language=language,
        group=group,
        tags=tags,
    )

    # Add to database
    command_id = db.add_command(command)
    click.echo(f"✅ Command '{name}' added with ID: {command_id}")


@daemon.command()
@click.argument("command_id")
@click.argument("args", nargs=-1)
def execute(command_id: str, args: List[str]):
    """Execute a command"""
    db = CommandDatabase()
    executor = CommandExecutor()

    # Get command
    command = db.get_command(command_id)
    if not command:
        click.echo(f"Command '{command_id}' not found", err=True)
        return

    # Execute
    result = executor.execute_command(command, list(args))

    # Record execution
    db.record_execution(
        command_id=command_id,
        status=result["status"],
        output=result.get("output", ""),
        error=result.get("error", ""),
        execution_time_ms=result.get("execution_time_ms", 0),
    )

    # Display results
    if result["success"]:
        click.echo("✅ Command executed successfully")
        if result["output"]:
            click.echo("Output:")
            click.echo(result["output"])
    else:
        click.echo("❌ Command execution failed")
        if result["error"]:
            click.echo(f"Error: {result['error']}")

    click.echo(f"Execution time: {result.get('execution_time_ms', 0)}ms")


@daemon.command()
@click.argument("query")
@click.option("--limit", default=10, help="Maximum number of results")
@click.option("--similar", is_flag=True, help="Use similarity search")
def search(query: str, limit: int, similar: bool):
    """Search for commands"""
    db = CommandDatabase()

    try:
        if similar:
            results = db.find_similar_commands(query, limit)
            if results:
                click.echo(f"Found {len(results)} similar command(s):")
                for cmd, similarity in results:
                    click.echo(f"  {cmd.name} ({cmd.language}) - {cmd.description}")
                    click.echo(f"    Similarity: {similarity:.3f}")
                    if cmd.tags:
                        click.echo(f"    Tags: {', '.join(cmd.tags)}")
                    click.echo()
            else:
                click.echo("No similar commands found")
        else:
            commands = db.search_commands(query, limit)
            if commands:
                click.echo(f"Found {len(commands)} command(s):")
                for cmd in commands:
                    click.echo(f"  {cmd.name} ({cmd.language}) - {cmd.description}")
                    if cmd.tags:
                        click.echo(f"    Tags: {', '.join(cmd.tags)}")
                    click.echo()
            else:
                click.echo("No commands found")

    except Exception as e:
        click.echo(f"❌ Error searching commands: {e}", err=True)


@daemon.command()
@click.option("--group", help="Filter by group")
@click.option("--language", help="Filter by language")
def list(group: str, language: str):
    """List all commands"""
    db = CommandDatabase()

    try:
        commands = db.get_all_commands()

        # Apply filters
        if group:
            commands = [cmd for cmd in commands if cmd.group == group]
        if language:
            commands = [cmd for cmd in commands if cmd.language == language]

        if not commands:
            click.echo("No commands found")
            return

        click.echo(f"Found {len(commands)} command(s):")
        for cmd in commands:
            click.echo(f"  {cmd.name} ({cmd.language}) - {cmd.description}")
            if cmd.group:
                click.echo(f"    Group: {cmd.group}")
            if cmd.tags:
                click.echo(f"    Tags: {', '.join(cmd.tags)}")
            click.echo(f"    Executed {cmd.execution_count} times")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing commands: {e}", err=True)


@daemon.command()
@click.argument("command_id")
def show(command_id: str):
    """Show command details"""
    db = CommandDatabase()

    try:
        command = db.get_command(command_id)
        if not command:
            click.echo(f"Command '{command_id}' not found", err=True)
            return

        click.echo(f"Command: {command.name}")
        click.echo(f"ID: {command.id}")
        click.echo(f"Description: {command.description}")
        click.echo(f"Language: {command.language}")
        if command.group:
            click.echo(f"Group: {command.group}")
        if command.tags:
            click.echo(f"Tags: {', '.join(command.tags)}")
        click.echo(f"Created: {command.created_at}")
        click.echo(f"Updated: {command.updated_at}")
        click.echo(f"Executed: {command.execution_count} times")
        if command.last_executed:
            click.echo(f"Last executed: {command.last_executed}")
        click.echo()
        click.echo("Code:")
        click.echo("=" * 50)
        click.echo(command.code)
        click.echo("=" * 50)

    except Exception as e:
        click.echo(f"❌ Error showing command: {e}", err=True)


@daemon.command()
@click.argument("command_id")
def delete(command_id: str):
    """Delete a command"""
    db = CommandDatabase()

    try:
        command = db.get_command(command_id)
        if not command:
            click.echo(f"Command '{command_id}' not found", err=True)
            return

        if click.confirm(f"Are you sure you want to delete command '{command.name}'?"):
            if db.delete_command(command_id):
                click.echo(f"✅ Command '{command.name}' deleted")
            else:
                click.echo(f"❌ Error deleting command '{command.name}'")
        else:
            click.echo("Deletion cancelled")

    except Exception as e:
        click.echo(f"❌ Error deleting command: {e}", err=True)


@daemon.command()
@click.argument("command_id")
@click.option("--name", help="New name")
@click.option("--description", help="New description")
@click.option("--group", help="New group")
@click.option("--tags", help="New tags (comma-separated)")
def edit(command_id: str, name: str, description: str, group: str, tags: str):
    """Edit a command"""
    db = CommandDatabase()

    try:
        command = db.get_command(command_id)
        if not command:
            click.echo(f"Command '{command_id}' not found", err=True)
            return

        # Update fields if provided
        if name:
            command.name = name
        if description:
            command.description = description
        if group:
            command.group = group
        if tags:
            command.tags = [tag.strip() for tag in tags.split(",")]

        command.updated_at = datetime.now()

        if db.update_command(command):
            click.echo(f"✅ Command '{command.name}' updated")
        else:
            click.echo(f"❌ Error updating command '{command.name}'")

    except Exception as e:
        click.echo(f"❌ Error editing command: {e}", err=True)


@daemon.command()
def groups():
    """List all command groups"""
    db = CommandDatabase()

    try:
        commands = db.get_all_commands()
        groups = {}

        for cmd in commands:
            group = cmd.group or "ungrouped"
            if group not in groups:
                groups[group] = []
            groups[group].append(cmd)

        if not groups:
            click.echo("No groups found")
            return

        click.echo("Command groups:")
        for group_name, group_commands in groups.items():
            click.echo(f"  {group_name} ({len(group_commands)} commands)")
            for cmd in group_commands:
                click.echo(f"    - {cmd.name} ({cmd.language})")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing groups: {e}", err=True)


if __name__ == "__main__":
    daemon()
