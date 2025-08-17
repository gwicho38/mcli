"""
Enhanced async daemon with Rust extensions and performance optimizations
"""

import asyncio
import json
import os
import signal
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
import redis.asyncio as redis

from mcli.lib.logger.logger import get_logger
from mcli.lib.performance.rust_bridge import (
    get_command_matcher,
    get_file_watcher,
    get_process_manager,
    get_tfidf_vectorizer,
)
from mcli.lib.search.cached_vectorizer import CachedTfIdfVectorizer, SmartVectorizerManager
from mcli.workflow.daemon.async_command_database import (
    AsyncCommandDatabase,
    Command,
    ExecutionRecord,
)
from mcli.workflow.daemon.async_process_manager import AsyncProcessManager

logger = get_logger(__name__)


class EnhancedDaemon:
    """High-performance async daemon with Rust extensions"""

    def __init__(
        self, db_path: Optional[str] = None, redis_url: Optional[str] = None, use_rust: bool = True
    ):

        self.use_rust = use_rust
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Core components
        self.command_db: Optional[AsyncCommandDatabase] = None
        self.process_manager: Optional[AsyncProcessManager] = None
        self.vectorizer_manager: Optional[SmartVectorizerManager] = None
        self.file_watcher = None
        self.command_matcher = None

        # Configuration
        self.db_path = db_path or Path.home() / ".local" / "mcli" / "daemon" / "enhanced.db"
        self.redis_url = redis_url or "redis://localhost:6379"

        # Performance metrics
        self.metrics = {
            "commands_executed": 0,
            "search_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "start_time": None,
        }

    async def initialize(self):
        """Initialize all daemon components"""
        logger.info("Initializing Enhanced Daemon...")

        try:
            # Initialize database
            self.command_db = AsyncCommandDatabase(
                db_path=str(self.db_path), redis_url=self.redis_url
            )
            await self.command_db.initialize()

            # Initialize process manager
            self.process_manager = AsyncProcessManager(
                db_path=str(self.db_path.parent / "processes.db"), redis_url=self.redis_url
            )
            await self.process_manager.initialize()

            # Initialize vectorizer manager
            self.vectorizer_manager = SmartVectorizerManager(redis_url=self.redis_url)

            # Initialize Rust components if available
            await self._initialize_rust_components()

            # Set up signal handlers
            self._setup_signal_handlers()

            logger.info("Enhanced Daemon initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Daemon: {e}")
            raise

    async def _initialize_rust_components(self):
        """Initialize Rust-based components"""
        try:
            # File watcher
            self.file_watcher = get_file_watcher(use_rust=self.use_rust)
            if self.file_watcher:
                # Start watching command directories
                watch_dirs = [
                    str(Path.home() / ".local" / "mcli" / "commands"),
                    str(Path.cwd() / "commands"),
                ]

                existing_dirs = [d for d in watch_dirs if Path(d).exists()]
                if existing_dirs:
                    self.file_watcher.start_watching(existing_dirs)
                    logger.info(f"File watcher monitoring: {existing_dirs}")

            # Command matcher
            self.command_matcher = get_command_matcher(use_rust=self.use_rust)
            if self.command_matcher:
                # Load existing commands into matcher
                commands = await self.command_db.get_all_commands()
                if commands:
                    command_dicts = [
                        {
                            "id": cmd.id,
                            "name": cmd.name,
                            "description": cmd.description,
                            "tags": cmd.tags,
                            "execution_count": cmd.execution_count,
                        }
                        for cmd in commands
                    ]

                    if hasattr(self.command_matcher, "add_commands"):
                        self.command_matcher.add_commands(command_dicts)

                    logger.info(f"Command matcher loaded {len(commands)} commands")

        except Exception as e:
            logger.warning(f"Failed to initialize some Rust components: {e}")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""

        def signal_handler():
            logger.info("Received shutdown signal")
            asyncio.create_task(self.shutdown())

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda s, f: asyncio.create_task(self.shutdown()))

    async def start(self):
        """Start the daemon"""
        if self.running:
            logger.warning("Daemon is already running")
            return

        logger.info("Starting Enhanced Daemon...")
        self.running = True
        self.metrics["start_time"] = datetime.now()

        # Start background tasks
        tasks = [
            asyncio.create_task(self._file_watcher_loop()),
            asyncio.create_task(self._maintenance_loop()),
            asyncio.create_task(self._metrics_loop()),
        ]

        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()

        finally:
            # Cancel background tasks
            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info("Enhanced Daemon stopped")

    async def shutdown(self):
        """Graceful shutdown"""
        if not self.running:
            return

        logger.info("Shutting down Enhanced Daemon...")
        self.running = False
        self.shutdown_event.set()

        # Stop file watcher
        if self.file_watcher and hasattr(self.file_watcher, "stop_watching"):
            try:
                self.file_watcher.stop_watching()
            except Exception as e:
                logger.warning(f"Error stopping file watcher: {e}")

        # Close components
        if self.command_db:
            await self.command_db.close()

        if self.process_manager:
            await self.process_manager.close()

        if self.vectorizer_manager:
            await self.vectorizer_manager.close_all()

    async def _file_watcher_loop(self):
        """Background loop for processing file system events"""
        if not self.file_watcher:
            return

        while self.running:
            try:
                if hasattr(self.file_watcher, "get_events"):
                    events = self.file_watcher.get_events()

                    for event in events:
                        await self._handle_file_event(event)

                await asyncio.sleep(1)  # Check for events every second

            except Exception as e:
                logger.error(f"Error in file watcher loop: {e}")
                await asyncio.sleep(5)  # Back off on error

    async def _handle_file_event(self, event):
        """Handle a file system event"""
        try:
            event_type = event.get("event_type") or event.get("type", "unknown")
            path = event.get("path", "")

            if not path.endswith(".json"):
                return  # Only process JSON command files

            if event_type in ["created", "modified"]:
                await self._reload_command_file(path)
            elif event_type == "deleted":
                await self._remove_command_file(path)

        except Exception as e:
            logger.error(f"Error handling file event {event}: {e}")

    async def _reload_command_file(self, file_path: str):
        """Reload a command from a JSON file"""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            command = Command(
                id=data.get("id") or str(uuid.uuid4()),
                name=data["name"],
                description=data.get("description", ""),
                code=data["code"],
                language=data["language"],
                group=data.get("group"),
                tags=data.get("tags", []),
                version=data.get("version", "1.0"),
                author=data.get("author"),
                dependencies=data.get("dependencies", []),
            )

            # Add/update in database
            existing = await self.command_db.get_command(command.id)
            if existing:
                await self.command_db.update_command(command)
            else:
                await self.command_db.add_command(command)

            # Update command matcher
            if self.command_matcher and hasattr(self.command_matcher, "add_command"):
                command_dict = {
                    "id": command.id,
                    "name": command.name,
                    "description": command.description,
                    "tags": command.tags,
                    "execution_count": command.execution_count,
                }
                self.command_matcher.add_command(command_dict)

            logger.info(f"Reloaded command: {command.name}")

        except Exception as e:
            logger.error(f"Failed to reload command file {file_path}: {e}")

    async def _remove_command_file(self, file_path: str):
        """Remove a command when its file is deleted"""
        try:
            # Extract command ID from filename
            command_id = Path(file_path).stem

            # Soft delete from database
            await self.command_db.delete_command(command_id)

            logger.info(f"Removed command: {command_id}")

        except Exception as e:
            logger.error(f"Failed to remove command file {file_path}: {e}")

    async def _maintenance_loop(self):
        """Background maintenance tasks"""
        while self.running:
            try:
                # Clean up finished processes
                if self.process_manager:
                    cleaned = await self.process_manager.cleanup_finished()
                    if cleaned:
                        logger.debug(f"Cleaned up {len(cleaned)} finished processes")

                # Update search indexes
                await self._update_search_indexes()

                # Wait 5 minutes before next maintenance
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(60)

    async def _metrics_loop(self):
        """Background metrics collection"""
        while self.running:
            try:
                # Log performance metrics every 10 minutes
                uptime = datetime.now() - self.metrics["start_time"]

                logger.info(
                    f"Daemon metrics - Uptime: {uptime}, "
                    f"Commands executed: {self.metrics['commands_executed']}, "
                    f"Search queries: {self.metrics['search_queries']}"
                )

                await asyncio.sleep(600)  # 10 minutes

            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(60)

    async def _update_search_indexes(self):
        """Update search indexes for better performance"""
        try:
            # Get all commands
            commands = await self.command_db.get_all_commands()

            if not commands:
                return

            # Prepare documents for vectorization
            documents = []
            for cmd in commands:
                text_parts = [cmd.name, cmd.description or ""]
                text_parts.extend(cmd.tags or [])
                documents.append(" ".join(text_parts))

            # Update vectorizer cache
            vectorizer = await self.vectorizer_manager.get_vectorizer("commands")
            await vectorizer.fit_transform(documents)

            logger.debug(f"Updated search indexes for {len(commands)} commands")

        except Exception as e:
            logger.error(f"Failed to update search indexes: {e}")

    # Public API methods

    async def add_command(self, command_data: Dict[str, Any]) -> str:
        """Add a new command"""
        command = Command(
            id=command_data.get("id") or str(uuid.uuid4()),
            name=command_data["name"],
            description=command_data.get("description", ""),
            code=command_data["code"],
            language=command_data["language"],
            group=command_data.get("group"),
            tags=command_data.get("tags", []),
            version=command_data.get("version", "1.0"),
            author=command_data.get("author"),
            dependencies=command_data.get("dependencies", []),
        )

        command_id = await self.command_db.add_command(command)

        # Update command matcher
        if self.command_matcher and hasattr(self.command_matcher, "add_command"):
            command_dict = {
                "id": command.id,
                "name": command.name,
                "description": command.description,
                "tags": command.tags,
                "execution_count": command.execution_count,
            }
            self.command_matcher.add_command(command_dict)

        return command_id

    async def search_commands(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for commands"""
        self.metrics["search_queries"] += 1

        # Try Rust command matcher first
        if self.command_matcher and hasattr(self.command_matcher, "search"):
            try:
                results = self.command_matcher.search(query, limit)
                return [
                    {
                        "command": result.get("command", {}),
                        "score": result.get("score", 0.0),
                        "match_type": result.get("match_type", "rust"),
                        "matched_fields": result.get("matched_fields", []),
                    }
                    for result in results
                ]
            except Exception as e:
                logger.warning(f"Rust command matcher failed: {e}")

        # Fallback to database search
        commands = await self.command_db.search_commands(query, limit)

        # Use vectorizer for similarity scoring
        if commands and self.vectorizer_manager:
            try:
                command_dicts = [
                    {
                        "id": cmd.id,
                        "name": cmd.name,
                        "description": cmd.description,
                        "tags": cmd.tags,
                    }
                    for cmd in commands
                ]

                results = await self.vectorizer_manager.search_commands(query, command_dicts, limit)

                return [
                    {
                        "command": cmd_dict,
                        "score": score,
                        "match_type": "vectorized",
                        "matched_fields": ["name", "description", "tags"],
                    }
                    for cmd_dict, score in results
                ]

            except Exception as e:
                logger.warning(f"Vectorized search failed: {e}")

        # Basic fallback
        return [
            {
                "command": {
                    "id": cmd.id,
                    "name": cmd.name,
                    "description": cmd.description,
                    "tags": cmd.tags,
                },
                "score": 1.0,
                "match_type": "database",
                "matched_fields": ["name"],
            }
            for cmd in commands
        ]

    async def execute_command(
        self, command_id: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Execute a command"""
        self.metrics["commands_executed"] += 1

        # Get command
        command = await self.command_db.get_command(command_id)
        if not command:
            raise ValueError(f"Command not found: {command_id}")

        # Start process
        process_id = await self.process_manager.start_process(
            name=f"{command.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            command=self._get_command_executor(command.language),
            args=self._prepare_command_args(command),
            working_dir=context.get("working_dir") if context else None,
            environment=context.get("environment") if context else None,
            timeout=context.get("timeout") if context else None,
        )

        # Record execution
        execution = ExecutionRecord(
            id=str(uuid.uuid4()),
            command_id=command_id,
            executed_at=datetime.now(),
            status="started",
            user=context.get("user") if context else None,
            context=context,
        )

        await self.command_db.record_execution(execution)

        return process_id

    def _get_command_executor(self, language: str) -> str:
        """Get the appropriate executor for a language"""
        executors = {
            "python": "python",
            "node": "node",
            "shell": "bash",
            "lua": "lua",
            "rust": "cargo",
        }
        return executors.get(language, "bash")

    def _prepare_command_args(self, command: Command) -> List[str]:
        """Prepare command arguments based on language"""
        if command.language == "python":
            return ["-c", command.code]
        elif command.language == "node":
            return ["-e", command.code]
        elif command.language == "shell":
            return ["-c", command.code]
        elif command.language == "lua":
            return ["-e", command.code]
        else:
            return [command.code]

    async def get_status(self) -> Dict[str, Any]:
        """Get daemon status"""
        return {
            "running": self.running,
            "uptime": (
                (datetime.now() - self.metrics["start_time"]).total_seconds()
                if self.metrics["start_time"]
                else 0
            ),
            "metrics": self.metrics.copy(),
            "components": {
                "command_db": self.command_db is not None,
                "process_manager": self.process_manager is not None,
                "vectorizer_manager": self.vectorizer_manager is not None,
                "file_watcher": self.file_watcher is not None,
                "command_matcher": self.command_matcher is not None,
            },
        }


# Daemon instance management
_daemon_instance: Optional[EnhancedDaemon] = None


async def get_daemon() -> EnhancedDaemon:
    """Get the global daemon instance"""
    global _daemon_instance

    if _daemon_instance is None:
        _daemon_instance = EnhancedDaemon()
        await _daemon_instance.initialize()

    return _daemon_instance


async def start_daemon():
    """Start the global daemon"""
    daemon = await get_daemon()
    await daemon.start()


async def stop_daemon():
    """Stop the global daemon"""
    global _daemon_instance

    if _daemon_instance:
        await _daemon_instance.shutdown()
        _daemon_instance = None
