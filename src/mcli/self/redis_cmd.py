"""
Redis service management commands
"""

import asyncio

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.services.redis_service import get_redis_service

logger = get_logger(__name__)


@click.group(name="redis")
def redis_group():
    """Manage Redis cache service"""
    pass


@redis_group.command(name="start")
def start_redis():
    """Start Redis server"""

    async def _start():
        service = await get_redis_service()

        if await service.is_running():
            click.echo("✅ Redis is already running")
            status = await service.get_status()
            click.echo(f"   Host: {status['host']}")
            click.echo(f"   Port: {status['port']}")
            click.echo(f"   Uptime: {status.get('uptime', 0)} seconds")
            return

        click.echo("🚀 Starting Redis server...")
        success = await service.start()

        if success:
            click.echo("✅ Redis server started successfully")
            status = await service.get_status()
            click.echo(f"   Connection URL: {await service.get_connection_url()}")
            click.echo(f"   Data directory: {status['data_dir']}")
            click.echo(f"   Process ID: {status['process_id']}")
        else:
            click.echo("❌ Failed to start Redis server")
            click.echo("   Make sure Redis is installed: brew install redis")

    asyncio.run(_start())


@redis_group.command(name="stop")
def stop_redis():
    """Stop Redis server"""

    async def _stop():
        service = await get_redis_service()

        if not await service.is_running():
            click.echo("ℹ️  Redis is not running")
            return

        click.echo("🛑 Stopping Redis server...")
        success = await service.stop()

        if success:
            click.echo("✅ Redis server stopped successfully")
        else:
            click.echo("❌ Failed to stop Redis server")

    asyncio.run(_stop())


@redis_group.command(name="restart")
def restart_redis():
    """Restart Redis server"""

    async def _restart():
        service = await get_redis_service()

        click.echo("🔄 Restarting Redis server...")
        success = await service.restart()

        if success:
            click.echo("✅ Redis server restarted successfully")
            status = await service.get_status()
            click.echo(f"   Connection URL: {await service.get_connection_url()}")
        else:
            click.echo("❌ Failed to restart Redis server")

    asyncio.run(_restart())


@redis_group.command(name="status")
def redis_status():
    """Show Redis server status"""

    async def _status():
        service = await get_redis_service()
        status = await service.get_status()

        if status["running"]:
            click.echo("✅ Redis Status: RUNNING")
            click.echo(f"   Host: {status['host']}")
            click.echo(f"   Port: {status['port']}")
            click.echo(f"   Connection URL: {await service.get_connection_url()}")
            click.echo(f"   Version: {status.get('version', 'unknown')}")
            click.echo(f"   Memory Usage: {status.get('memory_usage', 'unknown')}")
            click.echo(f"   Connected Clients: {status.get('connected_clients', 0)}")
            click.echo(f"   Uptime: {status.get('uptime', 0)} seconds")
            click.echo(f"   Total Commands: {status.get('total_commands', 0):,}")
            click.echo(f"   Cache Hits: {status.get('keyspace_hits', 0):,}")
            click.echo(f"   Cache Misses: {status.get('keyspace_misses', 0):,}")

            if status.get("keyspace_hits", 0) + status.get("keyspace_misses", 0) > 0:
                hit_rate = (
                    status.get("keyspace_hits", 0)
                    / (status.get("keyspace_hits", 0) + status.get("keyspace_misses", 0))
                    * 100
                )
                click.echo(f"   Hit Rate: {hit_rate:.1f}%")

            click.echo(f"   Data Directory: {status['data_dir']}")
            click.echo(f"   Process ID: {status.get('process_id', 'unknown')}")
        else:
            click.echo("❌ Redis Status: NOT RUNNING")
            click.echo(f"   Expected Host: {status['host']}")
            click.echo(f"   Expected Port: {status['port']}")
            click.echo(f"   Data Directory: {status['data_dir']}")

    asyncio.run(_status())


@redis_group.command(name="test")
def test_redis():
    """Test Redis connection and performance"""

    async def _test():
        service = await get_redis_service()

        if not await service.is_running():
            click.echo("❌ Redis is not running. Start it with: mcli redis start")
            return

        click.echo("🧪 Testing Redis connection...")
        result = await service.test_connection()

        if result["status"] == "success":
            click.echo("✅ Redis connection test passed")
            click.echo(f"   Latency: {result['latency_ms']}ms")
            click.echo(f"   Connection URL: {result['connection_url']}")
            click.echo(
                f"   Read/Write Test: {'✅ Passed' if result['test_result'] else '❌ Failed'}"
            )
        else:
            click.echo("❌ Redis connection test failed")
            click.echo(f"   Error: {result.get('error', 'unknown')}")
            click.echo(f"   Connection URL: {result.get('connection_url', 'unknown')}")

    asyncio.run(_test())


@redis_group.command(name="info")
def redis_info():
    """Show detailed Redis server information"""

    async def _info():
        service = await get_redis_service()

        if not await service.is_running():
            click.echo("❌ Redis is not running")
            return

        try:
            if not service.redis_client:
                import redis.asyncio as redis

                service.redis_client = redis.Redis(
                    host=service.host, port=service.port, decode_responses=True
                )

            info = await service.redis_client.info()

            click.echo("📊 Redis Server Information")
            click.echo("=" * 40)

            # Server info
            click.echo(f"Redis Version: {info.get('redis_version', 'unknown')}")
            click.echo(f"Redis Mode: {info.get('redis_mode', 'unknown')}")
            click.echo(f"OS: {info.get('os', 'unknown')}")
            click.echo(f"Architecture: {info.get('arch_bits', 'unknown')} bits")
            click.echo(f"Uptime: {info.get('uptime_in_seconds', 0)} seconds")

            click.echo()
            click.echo("Memory:")
            click.echo(f"  Used Memory: {info.get('used_memory_human', 'unknown')}")
            click.echo(f"  Peak Memory: {info.get('used_memory_peak_human', 'unknown')}")
            click.echo(f"  Memory Fragmentation: {info.get('mem_fragmentation_ratio', 'unknown')}")

            click.echo()
            click.echo("Stats:")
            click.echo(f"  Total Connections: {info.get('total_connections_received', 0):,}")
            click.echo(f"  Total Commands: {info.get('total_commands_processed', 0):,}")
            click.echo(f"  Commands/sec: {info.get('instantaneous_ops_per_sec', 0)}")
            click.echo(f"  Keyspace Hits: {info.get('keyspace_hits', 0):,}")
            click.echo(f"  Keyspace Misses: {info.get('keyspace_misses', 0):,}")

            if info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0) > 0:
                hit_rate = (
                    info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                    * 100
                )
                click.echo(f"  Hit Rate: {hit_rate:.2f}%")

            click.echo()
            click.echo("Persistence:")
            click.echo(f"  RDB Last Save: {info.get('rdb_last_save_time', 'unknown')}")
            click.echo(f"  AOF Enabled: {info.get('aof_enabled', 0) == 1}")

            # Show keyspace info if available
            db_info = {k: v for k, v in info.items() if k.startswith("db")}
            if db_info:
                click.echo()
                click.echo("Databases:")
                for db, stats in db_info.items():
                    click.echo(f"  {db}: {stats}")

        except Exception as e:
            click.echo(f"❌ Failed to get Redis info: {e}")

    asyncio.run(_info())


@redis_group.command(name="logs")
@click.option("--lines", "-n", default=20, help="Number of log lines to show")
def redis_logs(lines):
    """Show Redis server logs"""

    async def _logs():
        service = await get_redis_service()
        log_file = service.data_dir / "redis.log"

        if not log_file.exists():
            click.echo(f"❌ Log file not found: {log_file}")
            return

        try:
            # Read last N lines
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            click.echo(f"📋 Redis Logs (last {len(recent_lines)} lines)")
            click.echo("=" * 50)

            for line in recent_lines:
                click.echo(line.rstrip())

        except Exception as e:
            click.echo(f"❌ Failed to read logs: {e}")

    asyncio.run(_logs())


# Register with main CLI
def register_redis_commands(cli):
    """Register Redis commands with the main CLI"""
    cli.add_command(redis_group)
