import asyncio
import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
import redis.asyncio as redis

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Command:
    """Represents a stored command with enhanced metadata"""

    id: str
    name: str
    description: str
    code: str
    language: str  # 'python', 'node', 'lua', 'shell', 'rust'
    group: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    execution_count: int = 0
    last_executed: Optional[datetime] = None
    is_active: bool = True
    version: str = "1.0"
    author: Optional[str] = None
    dependencies: Optional[List[str]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ExecutionRecord:
    """Represents a command execution record"""

    id: str
    command_id: str
    executed_at: datetime
    status: str  # 'success', 'failed', 'timeout'
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    user: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AsyncCommandDatabase:
    """High-performance async command database with connection pooling and caching"""

    def __init__(
        self, db_path: Optional[str] = None, redis_url: Optional[str] = None, pool_size: int = 10
    ):
        if db_path is None:
            db_path = Path.home() / ".local" / "mcli" / "daemon" / "commands.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client: Optional[redis.Redis] = None

        # Connection pool
        self.pool_size = pool_size
        self._connection_pool: List[aiosqlite.Connection] = []
        self._pool_lock = asyncio.Lock()
        self._initialized = False

        # Cache settings
        self.cache_ttl = 3600  # 1 hour
        self.enable_caching = True

    async def initialize(self):
        """Initialize database and connection pool"""
        if self._initialized:
            return

        await self._init_database()
        await self._init_redis()
        await self._init_connection_pool()

        self._initialized = True
        logger.info("AsyncCommandDatabase initialized successfully")

    async def _init_database(self):
        """Initialize SQLite database with optimizations"""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable performance optimizations
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA cache_size=10000")
            await db.execute("PRAGMA temp_store=memory")
            await db.execute("PRAGMA mmap_size=268435456")  # 256MB

            # Create tables
            await db.execute(
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
                    is_active BOOLEAN DEFAULT 1,
                    version TEXT DEFAULT '1.0',
                    author TEXT,
                    dependencies TEXT
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    parent_group_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (parent_group_id) REFERENCES groups (id)
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY,
                    command_id TEXT NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    output TEXT,
                    error TEXT,
                    execution_time_ms INTEGER,
                    user TEXT,
                    context TEXT,
                    FOREIGN KEY (command_id) REFERENCES commands (id)
                )
            """
            )

            # Create performance indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_commands_name ON commands(name)")
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_commands_language ON commands(language)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_commands_group ON commands(group_name)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_commands_active ON commands(is_active)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_commands_execution_count ON commands(execution_count)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_command_id ON executions(command_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_executed_at ON executions(executed_at)"
            )

            # Create full-text search for commands
            await db.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS commands_fts USING fts5(
                    id UNINDEXED,
                    name,
                    description,
                    tags,
                    content='commands',
                    content_rowid='rowid'
                )
            """
            )

            # Create FTS triggers
            await db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS commands_fts_insert AFTER INSERT ON commands BEGIN
                    INSERT INTO commands_fts(id, name, description, tags)
                    VALUES (new.id, new.name, new.description, new.tags);
                END
            """
            )

            await db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS commands_fts_update AFTER UPDATE ON commands BEGIN
                    UPDATE commands_fts SET name=new.name, description=new.description, tags=new.tags
                    WHERE id=new.id;
                END
            """
            )

            await db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS commands_fts_delete AFTER DELETE ON commands BEGIN
                    DELETE FROM commands_fts WHERE id=old.id;
                END
            """
            )

            await db.commit()

    async def _init_redis(self):
        """Initialize Redis connection for caching"""
        if not self.enable_caching:
            return

        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis for command caching")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.redis_client = None
            self.enable_caching = False

    async def _init_connection_pool(self):
        """Initialize connection pool"""
        async with self._pool_lock:
            for _ in range(self.pool_size):
                conn = await aiosqlite.connect(self.db_path)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                self._connection_pool.append(conn)

    @asynccontextmanager
    async def _get_connection(self):
        """Get a database connection from the pool"""
        async with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
            else:
                conn = await aiosqlite.connect(self.db_path)
                await conn.execute("PRAGMA journal_mode=WAL")

        try:
            yield conn
        finally:
            async with self._pool_lock:
                if len(self._connection_pool) < self.pool_size:
                    self._connection_pool.append(conn)
                else:
                    await conn.close()

    async def add_command(self, command: Command) -> str:
        """Add a new command to the database"""
        if not command.id:
            command.id = str(uuid.uuid4())

        command.updated_at = datetime.now()

        async with self._get_connection() as db:
            try:
                await db.execute(
                    """
                    INSERT INTO commands 
                    (id, name, description, code, language, group_name, tags, 
                     created_at, updated_at, execution_count, last_executed, is_active,
                     version, author, dependencies)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        command.version,
                        command.author,
                        json.dumps(command.dependencies),
                    ),
                )

                await db.commit()

                # Cache the command
                if self.enable_caching and self.redis_client:
                    await self._cache_command(command)

                logger.info(f"Added command: {command.name} ({command.id})")
                return command.id

            except Exception as e:
                logger.error(f"Error adding command: {e}")
                await db.rollback()
                raise

    async def get_command(self, command_id: str) -> Optional[Command]:
        """Get a command by ID with caching"""
        # Try cache first
        if self.enable_caching and self.redis_client:
            cached = await self._get_cached_command(command_id)
            if cached:
                return cached

        async with self._get_connection() as db:
            async with db.execute(
                "SELECT * FROM commands WHERE id = ? AND is_active = 1", (command_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    command = self._row_to_command(row)

                    # Cache the result
                    if self.enable_caching and self.redis_client:
                        await self._cache_command(command)

                    return command

        return None

    async def update_command(self, command: Command) -> bool:
        """Update an existing command"""
        command.updated_at = datetime.now()

        async with self._get_connection() as db:
            try:
                result = await db.execute(
                    """
                    UPDATE commands SET 
                    name=?, description=?, code=?, language=?, group_name=?, tags=?,
                    updated_at=?, execution_count=?, last_executed=?, is_active=?,
                    version=?, author=?, dependencies=?
                    WHERE id=?
                """,
                    (
                        command.name,
                        command.description,
                        command.code,
                        command.language,
                        command.group,
                        json.dumps(command.tags),
                        command.updated_at.isoformat(),
                        command.execution_count,
                        command.last_executed.isoformat() if command.last_executed else None,
                        command.is_active,
                        command.version,
                        command.author,
                        json.dumps(command.dependencies),
                        command.id,
                    ),
                )

                await db.commit()

                if result.rowcount > 0:
                    # Update cache
                    if self.enable_caching and self.redis_client:
                        await self._cache_command(command)

                    logger.info(f"Updated command: {command.name} ({command.id})")
                    return True

                return False

            except Exception as e:
                logger.error(f"Error updating command: {e}")
                await db.rollback()
                raise

    async def delete_command(self, command_id: str) -> bool:
        """Delete a command (soft delete)"""
        async with self._get_connection() as db:
            try:
                result = await db.execute(
                    "UPDATE commands SET is_active = 0, updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), command_id),
                )

                await db.commit()

                if result.rowcount > 0:
                    # Remove from cache
                    if self.enable_caching and self.redis_client:
                        await self.redis_client.delete(f"command:{command_id}")

                    logger.info(f"Deleted command: {command_id}")
                    return True

                return False

            except Exception as e:
                logger.error(f"Error deleting command: {e}")
                await db.rollback()
                raise

    async def search_commands(self, query: str, limit: int = 50) -> List[Command]:
        """Full-text search for commands"""
        if not query.strip():
            return await self.get_all_commands(limit=limit)

        # Use FTS for efficient search
        async with self._get_connection() as db:
            # Prepare FTS query
            fts_query = " ".join(f'"{word}"*' for word in query.split() if word.strip())

            async with db.execute(
                """
                SELECT c.* FROM commands c
                JOIN commands_fts fts ON c.id = fts.id
                WHERE commands_fts MATCH ? AND c.is_active = 1
                ORDER BY rank, c.execution_count DESC, c.updated_at DESC
                LIMIT ?
            """,
                (fts_query, limit),
            ) as cursor:
                commands = []
                async for row in cursor:
                    commands.append(self._row_to_command(row))
                return commands

    async def get_all_commands(
        self,
        group: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Command]:
        """Get all commands with optional filtering"""
        where_clauses = ["is_active = 1"]
        params = []

        if group:
            where_clauses.append("group_name = ?")
            params.append(group)

        if language:
            where_clauses.append("language = ?")
            params.append(language)

        params.extend([limit, offset])

        query = f"""
            SELECT * FROM commands 
            WHERE {" AND ".join(where_clauses)}
            ORDER BY execution_count DESC, updated_at DESC
            LIMIT ? OFFSET ?
        """

        async with self._get_connection() as db:
            async with db.execute(query, params) as cursor:
                commands = []
                async for row in cursor:
                    commands.append(self._row_to_command(row))
                return commands

    async def get_popular_commands(self, limit: int = 10) -> List[Command]:
        """Get most popular commands by execution count"""
        async with self._get_connection() as db:
            async with db.execute(
                """
                SELECT * FROM commands 
                WHERE is_active = 1 AND execution_count > 0
                ORDER BY execution_count DESC, updated_at DESC
                LIMIT ?
            """,
                (limit,),
            ) as cursor:
                commands = []
                async for row in cursor:
                    commands.append(self._row_to_command(row))
                return commands

    async def record_execution(self, execution: ExecutionRecord):
        """Record a command execution"""
        async with self._get_connection() as db:
            try:
                await db.execute(
                    """
                    INSERT INTO executions 
                    (id, command_id, executed_at, status, output, error, execution_time_ms, user, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        execution.id,
                        execution.command_id,
                        execution.executed_at.isoformat(),
                        execution.status,
                        execution.output,
                        execution.error,
                        execution.execution_time_ms,
                        execution.user,
                        json.dumps(execution.context) if execution.context else None,
                    ),
                )

                # Update command execution count
                await db.execute(
                    """
                    UPDATE commands SET 
                    execution_count = execution_count + 1,
                    last_executed = ?
                    WHERE id = ?
                """,
                    (execution.executed_at.isoformat(), execution.command_id),
                )

                await db.commit()

                # Invalidate cache for the command
                if self.enable_caching and self.redis_client:
                    await self.redis_client.delete(f"command:{execution.command_id}")

            except Exception as e:
                logger.error(f"Error recording execution: {e}")
                await db.rollback()
                raise

    async def get_execution_history(
        self, command_id: Optional[str] = None, limit: int = 100
    ) -> List[ExecutionRecord]:
        """Get execution history"""
        query = "SELECT * FROM executions"
        params = []

        if command_id:
            query += " WHERE command_id = ?"
            params.append(command_id)

        query += " ORDER BY executed_at DESC LIMIT ?"
        params.append(limit)

        async with self._get_connection() as db:
            async with db.execute(query, params) as cursor:
                executions = []
                async for row in cursor:
                    executions.append(
                        ExecutionRecord(
                            id=row[0],
                            command_id=row[1],
                            executed_at=datetime.fromisoformat(row[2]),
                            status=row[3],
                            output=row[4],
                            error=row[5],
                            execution_time_ms=row[6],
                            user=row[7],
                            context=json.loads(row[8]) if row[8] else None,
                        )
                    )
                return executions

    async def _cache_command(self, command: Command):
        """Cache a command in Redis"""
        if not self.redis_client:
            return

        try:
            command_data = {
                "id": command.id,
                "name": command.name,
                "description": command.description,
                "code": command.code,
                "language": command.language,
                "group": command.group,
                "tags": json.dumps(command.tags),
                "execution_count": command.execution_count,
                "is_active": command.is_active,
                "version": command.version,
                "author": command.author,
                "dependencies": json.dumps(command.dependencies),
                "created_at": command.created_at.isoformat() if command.created_at else None,
                "updated_at": command.updated_at.isoformat() if command.updated_at else None,
                "last_executed": (
                    command.last_executed.isoformat() if command.last_executed else None
                ),
            }

            await self.redis_client.hset(f"command:{command.id}", mapping=command_data)
            await self.redis_client.expire(f"command:{command.id}", self.cache_ttl)

        except Exception as e:
            logger.warning(f"Failed to cache command {command.id}: {e}")

    async def _get_cached_command(self, command_id: str) -> Optional[Command]:
        """Get a command from Redis cache"""
        if not self.redis_client:
            return None

        try:
            data = await self.redis_client.hgetall(f"command:{command_id}")
            if not data:
                return None

            return Command(
                id=data["id"],
                name=data["name"],
                description=data.get("description"),
                code=data["code"],
                language=data["language"],
                group=data.get("group"),
                tags=json.loads(data.get("tags", "[]")),
                execution_count=int(data.get("execution_count", 0)),
                is_active=bool(int(data.get("is_active", 1))),
                version=data.get("version", "1.0"),
                author=data.get("author"),
                dependencies=json.loads(data.get("dependencies", "[]")),
                created_at=(
                    datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                ),
                updated_at=(
                    datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
                ),
                last_executed=(
                    datetime.fromisoformat(data["last_executed"])
                    if data.get("last_executed")
                    else None
                ),
            )

        except Exception as e:
            logger.warning(f"Failed to get cached command {command_id}: {e}")
            return None

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
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
            updated_at=datetime.fromisoformat(row[8]) if row[8] else None,
            execution_count=row[9] or 0,
            last_executed=datetime.fromisoformat(row[10]) if row[10] else None,
            is_active=bool(row[11]),
            version=row[12] if len(row) > 12 else "1.0",
            author=row[13] if len(row) > 13 else None,
            dependencies=json.loads(row[14]) if len(row) > 14 and row[14] else [],
        )

    async def close(self):
        """Clean up resources"""
        async with self._pool_lock:
            for conn in self._connection_pool:
                await conn.close()
            self._connection_pool.clear()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("AsyncCommandDatabase closed")
