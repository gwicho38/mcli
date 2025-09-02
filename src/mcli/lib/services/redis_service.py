"""
Redis Service Manager - Manages Redis as a background process
"""

import asyncio
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
import redis.asyncio as redis

from mcli.lib.logger.logger import get_logger
from mcli.workflow.daemon.async_process_manager import AsyncProcessManager, ProcessStatus

logger = get_logger(__name__)


class RedisService:
    """
    Manages Redis server as a background process integrated with MCLI's job system
    """

    def __init__(
        self,
        port: int = 6379,
        host: str = "127.0.0.1",
        data_dir: Optional[Path] = None,
        process_manager: Optional[AsyncProcessManager] = None,
    ):
        self.port = port
        self.host = host
        self.data_dir = data_dir or Path.home() / ".mcli" / "redis-data"
        self.config_file = None
        self.process_manager = process_manager or AsyncProcessManager()
        self.process_id = None
        self.redis_client = None

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> bool:
        """Start Redis server as a managed background process"""
        try:
            # Check if Redis is already running on this port
            if await self.is_running():
                logger.info(f"Redis already running on {self.host}:{self.port}")
                return True

            # Find Redis server executable
            redis_server_path = self._find_redis_server()
            if not redis_server_path:
                logger.error("Redis server not found. Install with: brew install redis")
                return False

            # Generate Redis configuration
            config_file = await self._generate_config()

            # Start Redis process through the process manager
            command_args = [str(redis_server_path), str(config_file)]

            logger.info(f"Starting Redis server: {' '.join(command_args)}")

            self.process_id = await self.process_manager.start_process(
                name="redis-server",
                command=str(redis_server_path),
                args=command_args[1:],  # Skip the executable name
                working_dir=str(self.data_dir),
                environment={"REDIS_PORT": str(self.port)},
            )

            # Wait a moment for startup
            await asyncio.sleep(1)

            # Verify Redis is running
            if await self.is_running():
                logger.info(f"✅ Redis server started successfully on {self.host}:{self.port}")
                logger.info(f"   Process ID: {self.process_id}")
                logger.info(f"   Data directory: {self.data_dir}")
                return True
            else:
                logger.error("Failed to start Redis server")
                return False

        except Exception as e:
            logger.error(f"Error starting Redis server: {e}")
            return False

    async def stop(self) -> bool:
        """Stop Redis server"""
        try:
            if self.process_id:
                # Use process manager to stop cleanly
                success = await self.process_manager.stop_process(self.process_id)
                if success:
                    logger.info("✅ Redis server stopped successfully")
                    self.process_id = None
                    return True
                else:
                    logger.warning("Process manager couldn't stop Redis, trying direct approach")

            # Fallback: find and stop Redis process directly
            return await self._stop_redis_direct()

        except Exception as e:
            logger.error(f"Error stopping Redis server: {e}")
            return False

    async def restart(self) -> bool:
        """Restart Redis server"""
        logger.info("Restarting Redis server...")
        await self.stop()
        await asyncio.sleep(1)
        return await self.start()

    async def is_running(self) -> bool:
        """Check if Redis server is running and accepting connections"""
        try:
            if not self.redis_client:
                self.redis_client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )

            await self.redis_client.ping()
            return True
        except (redis.ConnectionError, redis.TimeoutError, asyncio.TimeoutError):
            return False
        except Exception as e:
            logger.debug(f"Redis connection check failed: {e}")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """Get detailed Redis server status"""
        status = {
            "running": False,
            "host": self.host,
            "port": self.port,
            "data_dir": str(self.data_dir),
            "process_id": self.process_id,
            "process_status": None,
            "memory_usage": None,
            "connected_clients": None,
            "uptime": None,
        }

        # Check if running
        status["running"] = await self.is_running()

        if not status["running"]:
            return status

        try:
            # Get process information from process manager
            if self.process_id:
                process_info = await self.process_manager.get_process_info(self.process_id)
                if process_info:
                    status["process_status"] = process_info.status.value

            # Get Redis server info
            if self.redis_client:
                info = await self.redis_client.info()
                status.update(
                    {
                        "memory_usage": info.get("used_memory_human", "unknown"),
                        "connected_clients": info.get("connected_clients", 0),
                        "uptime": info.get("uptime_in_seconds", 0),
                        "version": info.get("redis_version", "unknown"),
                        "total_commands": info.get("total_commands_processed", 0),
                        "keyspace_hits": info.get("keyspace_hits", 0),
                        "keyspace_misses": info.get("keyspace_misses", 0),
                    }
                )

        except Exception as e:
            logger.debug(f"Failed to get Redis status details: {e}")

        return status

    async def get_connection_url(self) -> str:
        """Get Redis connection URL"""
        return f"redis://{self.host}:{self.port}"

    async def test_connection(self) -> Dict[str, Any]:
        """Test Redis connection and performance"""
        if not await self.is_running():
            return {"status": "failed", "error": "Redis not running"}

        try:
            start_time = time.perf_counter()

            # Test basic operations
            test_key = "mcli:test:connection"
            await self.redis_client.set(test_key, "test_value", ex=10)
            value = await self.redis_client.get(test_key)
            await self.redis_client.delete(test_key)

            latency = (time.perf_counter() - start_time) * 1000  # ms

            return {
                "status": "success",
                "latency_ms": round(latency, 2),
                "connection_url": await self.get_connection_url(),
                "test_result": value == "test_value",
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "connection_url": await self.get_connection_url(),
            }

    def _find_redis_server(self) -> Optional[Path]:
        """Find Redis server executable"""
        possible_paths = [
            "/opt/homebrew/bin/redis-server",  # Homebrew on Apple Silicon
            "/usr/local/bin/redis-server",  # Homebrew on Intel
            "/usr/bin/redis-server",  # System install
            Path.home() / ".local/bin/redis-server",  # Local install
        ]

        # Check PATH first
        try:
            result = subprocess.run(
                ["which", "redis-server"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                path = Path(result.stdout.strip())
                if path.exists():
                    return path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check known locations
        for path in possible_paths:
            if isinstance(path, str):
                path = Path(path)
            if path.exists():
                return path

        return None

    async def _generate_config(self) -> Path:
        """Generate Redis configuration file"""
        config_content = f"""
# MCLI Redis Configuration
port {self.port}
bind {self.host}
dir {self.data_dir}

# Performance settings
save 60 1000
stop-writes-on-bgsave-error no
rdbcompression yes
rdbchecksum yes
dbfilename mcli-redis.rdb

# Memory settings  
maxmemory-policy allkeys-lru
maxmemory 256mb

# Logging
loglevel notice
logfile {self.data_dir}/redis.log

# Security (basic)
protected-mode yes

# Disable potentially dangerous commands in production
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Client settings
timeout 300
tcp-keepalive 300

# Persistence
appendonly yes
appendfilename "mcli-redis.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
"""

        config_file = self.data_dir / "redis.conf"
        config_file.write_text(config_content.strip())
        self.config_file = config_file

        logger.info(f"Generated Redis config: {config_file}")
        return config_file

    async def _stop_redis_direct(self) -> bool:
        """Stop Redis by finding process directly"""
        try:
            # Find Redis processes
            redis_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] == "redis-server":
                        # Check if it's our instance by port
                        cmdline = proc.info.get("cmdline", [])
                        if any(str(self.port) in arg for arg in cmdline):
                            redis_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not redis_processes:
                logger.info("No Redis processes found to stop")
                return True

            # Stop processes gracefully
            for proc in redis_processes:
                try:
                    logger.info(f"Stopping Redis process {proc.pid}")
                    proc.send_signal(signal.SIGTERM)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.debug(f"Could not stop process {proc.pid}: {e}")

            # Wait for graceful shutdown
            await asyncio.sleep(2)

            # Force kill if still running
            for proc in redis_processes:
                try:
                    if proc.is_running():
                        logger.warning(f"Force killing Redis process {proc.pid}")
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return True

        except Exception as e:
            logger.error(f"Failed to stop Redis directly: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        await self.stop()


# Global Redis service instance
_redis_service = None


async def get_redis_service() -> RedisService:
    """Get or create global Redis service instance"""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service


async def ensure_redis_running() -> bool:
    """Ensure Redis is running, start if needed"""
    service = await get_redis_service()

    if await service.is_running():
        logger.info("Redis already running")
        return True

    logger.info("Starting Redis service...")
    return await service.start()


async def get_redis_connection() -> Optional[redis.Redis]:
    """Get Redis connection, starting service if needed"""
    service = await get_redis_service()

    if not await service.is_running():
        success = await service.start()
        if not success:
            return None

    return redis.Redis(host=service.host, port=service.port, decode_responses=True)
