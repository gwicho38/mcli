import asyncio
import json
import os
import signal
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiosqlite
import psutil
import redis.asyncio as redis

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class ProcessStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    EXITED = "exited"
    KILLED = "killed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ProcessInfo:
    """Information about a managed process"""

    id: str
    name: str
    command: str
    args: List[str]
    status: ProcessStatus
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    working_dir: Optional[str] = None
    environment: Optional[Dict[str, str]] = None
    stdout_lines: List[str] = None
    stderr_lines: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.stdout_lines is None:
            self.stdout_lines = []
        if self.stderr_lines is None:
            self.stderr_lines = []


class AsyncProcessContainer:
    """Manages a single async process with enhanced monitoring"""

    def __init__(self, process_info: ProcessInfo, redis_client: Optional[redis.Redis] = None):
        self.info = process_info
        self.process: Optional[asyncio.subprocess.Process] = None
        self.container_dir: Optional[Path] = None
        self.stdout_task: Optional[asyncio.Task] = None
        self.stderr_task: Optional[asyncio.Task] = None
        self.redis_client = redis_client
        self._setup_container_environment()

    def _setup_container_environment(self):
        """Setup isolated environment for the process"""
        base_dir = Path.home() / ".local" / "mcli" / "containers"
        self.container_dir = base_dir / self.info.id
        self.container_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata file
        metadata_file = self.container_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(asdict(self.info), f, indent=2, default=str)

    async def start(self, timeout: Optional[float] = None) -> bool:
        """Start the async process with optional timeout"""
        try:
            if self.process and self.process.returncode is None:
                logger.warning(f"Process {self.info.id} is already running")
                return False

            # Create the subprocess
            self.process = await asyncio.create_subprocess_exec(
                self.info.command,
                *self.info.args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.info.working_dir or str(self.container_dir),
                env=self.info.environment or os.environ.copy(),
            )

            self.info.pid = self.process.pid
            self.info.status = ProcessStatus.RUNNING
            self.info.started_at = datetime.now()

            # Start output monitoring tasks
            self.stdout_task = asyncio.create_task(self._monitor_stdout())
            self.stderr_task = asyncio.create_task(self._monitor_stderr())

            # Cache process info in Redis if available
            if self.redis_client:
                await self._cache_process_info()

            logger.info(f"Started async process {self.info.id} with PID {self.process.pid}")

            # Handle timeout if specified
            if timeout:
                asyncio.create_task(self._timeout_handler(timeout))

            return True

        except Exception as e:
            logger.error(f"Failed to start process {self.info.id}: {e}")
            self.info.status = ProcessStatus.FAILED
            return False

    async def stop(self, timeout: float = 10.0) -> bool:
        """Stop the process gracefully with timeout"""
        if not self.process or self.process.returncode is not None:
            return True

        try:
            # Send SIGTERM
            self.process.terminate()

            # Wait for graceful shutdown with timeout
            try:
                await asyncio.wait_for(self.process.wait(), timeout=timeout)
                self.info.status = ProcessStatus.EXITED
            except asyncio.TimeoutError:
                # Force kill if timeout
                self.process.kill()
                await self.process.wait()
                self.info.status = ProcessStatus.KILLED

            self.info.exit_code = self.process.returncode
            self.info.finished_at = datetime.now()

            # Cancel monitoring tasks
            if self.stdout_task:
                self.stdout_task.cancel()
            if self.stderr_task:
                self.stderr_task.cancel()

            # Update cache
            if self.redis_client:
                await self._cache_process_info()

            logger.info(f"Stopped process {self.info.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop process {self.info.id}: {e}")
            return False

    async def kill(self) -> bool:
        """Force kill the process"""
        if not self.process or self.process.returncode is not None:
            return True

        try:
            self.process.kill()
            await self.process.wait()

            self.info.status = ProcessStatus.KILLED
            self.info.exit_code = self.process.returncode
            self.info.finished_at = datetime.now()

            # Cancel monitoring tasks
            if self.stdout_task:
                self.stdout_task.cancel()
            if self.stderr_task:
                self.stderr_task.cancel()

            # Update cache
            if self.redis_client:
                await self._cache_process_info()

            logger.info(f"Killed process {self.info.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to kill process {self.info.id}: {e}")
            return False

    async def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for process to complete with optional timeout"""
        if not self.process:
            raise RuntimeError("Process not started")

        if timeout:
            try:
                await asyncio.wait_for(self.process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                self.info.status = ProcessStatus.TIMEOUT
                self.info.finished_at = datetime.now()
                raise
        else:
            await self.process.wait()

        self.info.exit_code = self.process.returncode
        self.info.status = (
            ProcessStatus.EXITED if self.process.returncode == 0 else ProcessStatus.FAILED
        )
        self.info.finished_at = datetime.now()

        # Update cache
        if self.redis_client:
            await self._cache_process_info()

        return self.process.returncode

    async def _monitor_stdout(self):
        """Monitor stdout and collect lines"""
        if not self.process or not self.process.stdout:
            return

        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break

                line_str = line.decode("utf-8", errors="replace").strip()
                self.info.stdout_lines.append(line_str)

                # Limit memory usage - keep only last 1000 lines
                if len(self.info.stdout_lines) > 1000:
                    self.info.stdout_lines = self.info.stdout_lines[-1000:]

                # Stream to Redis if available
                if self.redis_client:
                    await self.redis_client.lpush(f"process:{self.info.id}:stdout", line_str)
                    await self.redis_client.ltrim(f"process:{self.info.id}:stdout", 0, 999)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error monitoring stdout for {self.info.id}: {e}")

    async def _monitor_stderr(self):
        """Monitor stderr and collect lines"""
        if not self.process or not self.process.stderr:
            return

        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break

                line_str = line.decode("utf-8", errors="replace").strip()
                self.info.stderr_lines.append(line_str)

                # Limit memory usage - keep only last 1000 lines
                if len(self.info.stderr_lines) > 1000:
                    self.info.stderr_lines = self.info.stderr_lines[-1000:]

                # Stream to Redis if available
                if self.redis_client:
                    await self.redis_client.lpush(f"process:{self.info.id}:stderr", line_str)
                    await self.redis_client.ltrim(f"process:{self.info.id}:stderr", 0, 999)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error monitoring stderr for {self.info.id}: {e}")

    async def _timeout_handler(self, timeout: float):
        """Handle process timeout"""
        await asyncio.sleep(timeout)

        if self.process and self.process.returncode is None:
            logger.warning(f"Process {self.info.id} timed out after {timeout}s")
            await self.kill()

    async def _cache_process_info(self):
        """Cache process info in Redis"""
        if not self.redis_client:
            return

        try:
            process_data = {
                "id": self.info.id,
                "name": self.info.name,
                "status": self.info.status.value,
                "pid": self.info.pid,
                "exit_code": self.info.exit_code,
                "created_at": self.info.created_at.isoformat() if self.info.created_at else None,
                "started_at": self.info.started_at.isoformat() if self.info.started_at else None,
                "finished_at": self.info.finished_at.isoformat() if self.info.finished_at else None,
            }

            await self.redis_client.hset(f"process:{self.info.id}:info", mapping=process_data)
            await self.redis_client.expire(f"process:{self.info.id}:info", 3600)  # 1 hour TTL

        except Exception as e:
            logger.error(f"Failed to cache process info for {self.info.id}: {e}")


class AsyncProcessManager:
    """High-performance async process manager with SQLite and Redis"""

    def __init__(self, db_path: Optional[str] = None, redis_url: Optional[str] = None):
        if db_path is None:
            db_path = Path.home() / ".local" / "mcli" / "daemon" / "processes.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.processes: Dict[str, AsyncProcessContainer] = {}
        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client: Optional[redis.Redis] = None

        # Connection pool for SQLite
        self._db_pool_size = 10
        self._db_pool: List[aiosqlite.Connection] = []
        self._db_pool_lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the process manager"""
        await self._init_database()
        await self._init_redis()
        await self._init_db_pool()

    async def _init_database(self):
        """Initialize SQLite database with optimizations"""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA cache_size=10000")
            await db.execute("PRAGMA temp_store=memory")

            # Create processes table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS processes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    command TEXT NOT NULL,
                    args TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pid INTEGER,
                    exit_code INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    working_dir TEXT,
                    environment TEXT,
                    stdout_lines TEXT,
                    stderr_lines TEXT
                )
            """
            )

            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_processes_status ON processes(status)")
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_processes_created_at ON processes(created_at)"
            )

            await db.commit()

    async def _init_redis(self):
        """Initialize Redis connection for caching"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis for caching")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.redis_client = None

    async def _init_db_pool(self):
        """Initialize connection pool for SQLite"""
        async with self._db_pool_lock:
            for _ in range(self._db_pool_size):
                conn = await aiosqlite.connect(self.db_path)
                await conn.execute("PRAGMA journal_mode=WAL")
                self._db_pool.append(conn)

    @asynccontextmanager
    async def _get_db_connection(self):
        """Get a database connection from the pool"""
        async with self._db_pool_lock:
            if self._db_pool:
                conn = self._db_pool.pop()
            else:
                conn = await aiosqlite.connect(self.db_path)
                await conn.execute("PRAGMA journal_mode=WAL")

        try:
            yield conn
        finally:
            async with self._db_pool_lock:
                if len(self._db_pool) < self._db_pool_size:
                    self._db_pool.append(conn)
                else:
                    await conn.close()

    async def start_process(
        self,
        name: str,
        command: str,
        args: List[str],
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Start a new async process"""
        process_info = ProcessInfo(
            id=str(uuid.uuid4()),
            name=name,
            command=command,
            args=args,
            status=ProcessStatus.CREATED,
            working_dir=working_dir,
            environment=environment,
        )

        container = AsyncProcessContainer(process_info, self.redis_client)
        self.processes[process_info.id] = container

        # Save to database
        await self._save_process_info(process_info)

        # Start the process
        success = await container.start(timeout)
        if success:
            await self._save_process_info(process_info)
            return process_info.id
        else:
            del self.processes[process_info.id]
            raise RuntimeError(f"Failed to start process: {name}")

    async def stop_process(self, process_id: str, timeout: float = 10.0) -> bool:
        """Stop a process gracefully"""
        if process_id not in self.processes:
            raise KeyError(f"Process not found: {process_id}")

        container = self.processes[process_id]
        success = await container.stop(timeout)

        if success:
            await self._save_process_info(container.info)

        return success

    async def kill_process(self, process_id: str) -> bool:
        """Force kill a process"""
        if process_id not in self.processes:
            raise KeyError(f"Process not found: {process_id}")

        container = self.processes[process_id]
        success = await container.kill()

        if success:
            await self._save_process_info(container.info)

        return success

    async def get_process_info(self, process_id: str) -> ProcessInfo:
        """Get process information"""
        if process_id in self.processes:
            return self.processes[process_id].info

        # Try to load from database
        async with self._get_db_connection() as db:
            async with db.execute("SELECT * FROM processes WHERE id = ?", (process_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_process_info(row)

        raise KeyError(f"Process not found: {process_id}")

    async def list_processes(self, status_filter: Optional[str] = None) -> List[ProcessInfo]:
        """List all processes with optional status filter"""
        processes = []

        # Add active processes
        for container in self.processes.values():
            if not status_filter or container.info.status.value == status_filter:
                processes.append(container.info)

        # Add historical processes from database
        query = "SELECT * FROM processes"
        params = []

        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)

        query += " ORDER BY created_at DESC"

        async with self._get_db_connection() as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    process_info = self._row_to_process_info(row)
                    # Avoid duplicates
                    if process_info.id not in self.processes:
                        processes.append(process_info)

        return processes

    async def cleanup_finished(self) -> List[str]:
        """Remove finished processes from memory"""
        finished_ids = []

        for process_id, container in list(self.processes.items()):
            if container.info.status in [
                ProcessStatus.EXITED,
                ProcessStatus.FAILED,
                ProcessStatus.KILLED,
                ProcessStatus.TIMEOUT,
            ]:
                finished_ids.append(process_id)
                del self.processes[process_id]

        return finished_ids

    async def _save_process_info(self, process_info: ProcessInfo):
        """Save process info to database"""
        async with self._get_db_connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO processes 
                (id, name, command, args, status, pid, exit_code, created_at, 
                 started_at, finished_at, working_dir, environment, stdout_lines, stderr_lines)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    process_info.id,
                    process_info.name,
                    process_info.command,
                    json.dumps(process_info.args),
                    process_info.status.value,
                    process_info.pid,
                    process_info.exit_code,
                    process_info.created_at.isoformat() if process_info.created_at else None,
                    process_info.started_at.isoformat() if process_info.started_at else None,
                    process_info.finished_at.isoformat() if process_info.finished_at else None,
                    process_info.working_dir,
                    json.dumps(process_info.environment) if process_info.environment else None,
                    json.dumps(process_info.stdout_lines),
                    json.dumps(process_info.stderr_lines),
                ),
            )
            await db.commit()

    def _row_to_process_info(self, row) -> ProcessInfo:
        """Convert database row to ProcessInfo"""
        return ProcessInfo(
            id=row[0],
            name=row[1],
            command=row[2],
            args=json.loads(row[3]),
            status=ProcessStatus(row[4]),
            pid=row[5],
            exit_code=row[6],
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
            started_at=datetime.fromisoformat(row[8]) if row[8] else None,
            finished_at=datetime.fromisoformat(row[9]) if row[9] else None,
            working_dir=row[10],
            environment=json.loads(row[11]) if row[11] else None,
            stdout_lines=json.loads(row[12]) if row[12] else [],
            stderr_lines=json.loads(row[13]) if row[13] else [],
        )

    async def close(self):
        """Clean up resources"""
        # Close all active processes
        for container in self.processes.values():
            await container.stop()

        # Close database connections
        async with self._db_pool_lock:
            for conn in self._db_pool:
                await conn.close()
            self._db_pool.clear()

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
