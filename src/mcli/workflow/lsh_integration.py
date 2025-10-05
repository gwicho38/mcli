"""
LSH Integration Commands for mcli
Provides CLI interface for managing LSH daemon integration and data pipeline
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

from mcli.lib.api import mcli_decorators as mcli
from mcli.lib.logger.logger import get_logger
from mcli.lib.services.data_pipeline import DataPipelineConfig, LSHDataPipeline
from mcli.lib.services.lsh_client import LSHClient, LSHEventProcessor

logger = get_logger(__name__)


@mcli.command(name="lsh-status", help="Check LSH daemon connection and status")
@mcli.option(
    "--url", default=None, help="LSH API URL (default: $LSH_API_URL or http://localhost:3030)"
)
@mcli.option("--api-key", default=None, help="LSH API key (default: $LSH_API_KEY)")
async def lsh_status(url: Optional[str], api_key: Optional[str]):
    """Check LSH daemon connection and status"""
    try:
        async with LSHClient(base_url=url, api_key=api_key) as client:
            # Test connection
            is_healthy = await client.health_check()
            if not is_healthy:
                mcli.echo(mcli.style("❌ LSH daemon is not healthy", fg="red"))
                sys.exit(1)

            # Get status
            status = await client.get_status()

            mcli.echo(mcli.style("✅ LSH Daemon Status", fg="green", bold=True))
            mcli.echo(f"URL: {client.base_url}")
            mcli.echo(f"PID: {status.get('pid', 'unknown')}")
            mcli.echo(f"Uptime: {status.get('uptime', 0) // 60} minutes")
            mcli.echo(
                f"Memory: {status.get('memoryUsage', {}).get('heapUsed', 0) // 1024 // 1024} MB"
            )

            # Get jobs summary
            jobs = await client.list_jobs()
            running_jobs = [j for j in jobs if j.get("status") == "running"]

            mcli.echo(f"Total Jobs: {len(jobs)}")
            mcli.echo(f"Running Jobs: {len(running_jobs)}")

    except Exception as e:
        mcli.echo(mcli.style(f"❌ Error connecting to LSH daemon: {e}", fg="red"))
        sys.exit(1)


@mcli.command(name="lsh-jobs", help="List and manage LSH jobs")
@mcli.option("--status", help="Filter by job status")
@mcli.option("--format", type=mcli.Choice(["table", "json"]), default="table", help="Output format")
@mcli.option("--url", default=None, help="LSH API URL")
@mcli.option("--api-key", default=None, help="LSH API key")
async def lsh_jobs(status: Optional[str], format: str, url: Optional[str], api_key: Optional[str]):
    """List LSH jobs"""
    try:
        async with LSHClient(base_url=url, api_key=api_key) as client:
            filter_params = {}
            if status:
                filter_params["status"] = status

            jobs = await client.list_jobs(filter_params)

            if format == "json":
                mcli.echo(json.dumps(jobs, indent=2))
            else:
                # Table format
                mcli.echo(mcli.style("\n📋 LSH Jobs", fg="blue", bold=True))
                mcli.echo("-" * 80)
                mcli.echo(f"{'ID':<20} {'Name':<25} {'Status':<10} {'Type':<15}")
                mcli.echo("-" * 80)

                for job in jobs:
                    job_id = job.get("id", "unknown")[:18]
                    name = job.get("name", "unknown")[:23]
                    job_status = job.get("status", "unknown")
                    job_type = job.get("type", "unknown")[:13]

                    status_color = {
                        "running": "green",
                        "completed": "blue",
                        "failed": "red",
                        "pending": "yellow",
                    }.get(job_status, "white")

                    mcli.echo(
                        f"{job_id:<20} {name:<25} {mcli.style(job_status, fg=status_color):<20} {job_type:<15}"
                    )

    except Exception as e:
        mcli.echo(mcli.style(f"❌ Error listing jobs: {e}", fg="red"))
        sys.exit(1)


@mcli.command(name="lsh-create-job", help="Create a new LSH job")
@mcli.option("--name", required=True, help="Job name")
@mcli.option("--command", required=True, help="Command to execute")
@mcli.option("--schedule", help="Cron schedule (e.g., '0 */6 * * *')")
@mcli.option("--type", default="shell", help="Job type")
@mcli.option("--description", help="Job description")
@mcli.option("--tags", help="Comma-separated tags")
@mcli.option("--database-sync", is_flag=True, help="Enable database synchronization")
@mcli.option("--url", default=None, help="LSH API URL")
@mcli.option("--api-key", default=None, help="LSH API key")
async def lsh_create_job(
    name: str,
    command: str,
    schedule: Optional[str],
    type: str,
    description: Optional[str],
    tags: Optional[str],
    database_sync: bool,
    url: Optional[str],
    api_key: Optional[str],
):
    """Create a new LSH job"""
    try:
        async with LSHClient(base_url=url, api_key=api_key) as client:
            job_spec = {
                "name": name,
                "command": command,
                "type": type,
                "databaseSync": database_sync,
            }

            if schedule:
                job_spec["schedule"] = {"cron": schedule}

            if description:
                job_spec["description"] = description

            if tags:
                job_spec["tags"] = [tag.strip() for tag in tags.split(",")]

            job = await client.create_job(job_spec)

            mcli.echo(mcli.style("✅ Job created successfully", fg="green"))
            mcli.echo(f"Job ID: {job.get('id')}")
            mcli.echo(f"Name: {job.get('name')}")
            mcli.echo(f"Status: {job.get('status')}")

    except Exception as e:
        mcli.echo(mcli.style(f"❌ Error creating job: {e}", fg="red"))
        sys.exit(1)


@mcli.command(name="lsh-pipeline", help="Start LSH data pipeline listener")
@mcli.option("--batch-size", default=100, help="Batch size for processing")
@mcli.option("--batch-timeout", default=30, help="Batch timeout in seconds")
@mcli.option("--output-dir", default="./data/processed", help="Output directory for processed data")
@mcli.option("--disable-validation", is_flag=True, help="Disable data validation")
@mcli.option("--disable-enrichment", is_flag=True, help="Disable data enrichment")
@mcli.option("--url", default=None, help="LSH API URL")
@mcli.option("--api-key", default=None, help="LSH API key")
async def lsh_pipeline(
    batch_size: int,
    batch_timeout: int,
    output_dir: str,
    disable_validation: bool,
    disable_enrichment: bool,
    url: Optional[str],
    api_key: Optional[str],
):
    """Start LSH data pipeline listener"""
    try:
        # Configure pipeline
        config = DataPipelineConfig()
        config.batch_size = batch_size
        config.batch_timeout = batch_timeout
        config.output_dir = Path(output_dir)
        config.enable_validation = not disable_validation
        config.enable_enrichment = not disable_enrichment

        mcli.echo(mcli.style("🚀 Starting LSH Data Pipeline", fg="green", bold=True))
        mcli.echo(f"LSH API: {url or os.getenv('LSH_API_URL', 'http://localhost:3030')}")
        mcli.echo(f"Batch Size: {batch_size}")
        mcli.echo(f"Batch Timeout: {batch_timeout}s")
        mcli.echo(f"Output Directory: {output_dir}")
        mcli.echo(f"Validation: {'enabled' if config.enable_validation else 'disabled'}")
        mcli.echo(f"Enrichment: {'enabled' if config.enable_enrichment else 'disabled'}")

        # Initialize client and pipeline
        lsh_client = LSHClient(base_url=url, api_key=api_key)
        pipeline = LSHDataPipeline(lsh_client, config)

        # Setup graceful shutdown
        def signal_handler(signum, frame):
            mcli.echo(mcli.style("\n🛑 Stopping pipeline...", fg="yellow"))
            asyncio.create_task(pipeline.stop())
            sys.exit(0)

        import signal

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start pipeline
        await pipeline.start()

    except KeyboardInterrupt:
        mcli.echo(mcli.style("\n🛑 Pipeline stopped by user", fg="yellow"))
    except Exception as e:
        mcli.echo(mcli.style(f"❌ Pipeline error: {e}", fg="red"))
        sys.exit(1)


@mcli.command(name="lsh-listen", help="Listen to LSH events (for debugging)")
@mcli.option("--url", default=None, help="LSH API URL")
@mcli.option("--api-key", default=None, help="LSH API key")
@mcli.option("--filter", help="Event type filter (e.g., 'job:completed')")
async def lsh_listen(url: Optional[str], api_key: Optional[str], filter: Optional[str]):
    """Listen to LSH events for debugging"""
    try:
        mcli.echo(mcli.style("👂 Listening to LSH events...", fg="blue", bold=True))
        mcli.echo("Press Ctrl+C to stop")

        lsh_client = LSHClient(base_url=url, api_key=api_key)

        def print_event(event_data: Dict[str, Any]):
            event_type = event_data.get("type", "unknown")
            timestamp = event_data.get("timestamp", "")

            if filter and filter not in event_type:
                return

            mcli.echo(f"\n🔔 Event: {mcli.style(event_type, fg='cyan', bold=True)}")
            mcli.echo(f"Time: {timestamp}")
            mcli.echo(f"Data: {json.dumps(event_data.get('data', {}), indent=2)}")

        lsh_client.on("*", print_event)

        await lsh_client.connect()
        await lsh_client.stream_events()

    except KeyboardInterrupt:
        mcli.echo(mcli.style("\n👋 Stopped listening", fg="yellow"))
    except Exception as e:
        mcli.echo(mcli.style(f"❌ Error listening to events: {e}", fg="red"))
        sys.exit(1)


@mcli.command(name="lsh-webhook", help="Manage LSH webhooks")
@mcli.option("--action", type=mcli.Choice(["list", "add"]), required=True, help="Action to perform")
@mcli.option("--endpoint", help="Webhook endpoint URL (for add action)")
@mcli.option("--url", default=None, help="LSH API URL")
@mcli.option("--api-key", default=None, help="LSH API key")
async def lsh_webhook(
    action: str, endpoint: Optional[str], url: Optional[str], api_key: Optional[str]
):
    """Manage LSH webhooks"""
    try:
        async with LSHClient(base_url=url, api_key=api_key) as client:
            if action == "list":
                webhooks = await client.list_webhooks()
                mcli.echo(mcli.style("📮 LSH Webhooks", fg="blue", bold=True))
                mcli.echo(f"Enabled: {webhooks.get('enabled', False)}")
                mcli.echo("Endpoints:")
                for endpoint in webhooks.get("endpoints", []):
                    mcli.echo(f"  • {endpoint}")

            elif action == "add":
                if not endpoint:
                    mcli.echo(mcli.style("❌ Endpoint URL required for add action", fg="red"))
                    sys.exit(1)

                result = await client.add_webhook(endpoint)
                mcli.echo(mcli.style("✅ Webhook added successfully", fg="green"))
                mcli.echo(f"Endpoints: {result.get('endpoints', [])}")

    except Exception as e:
        mcli.echo(mcli.style(f"❌ Error managing webhooks: {e}", fg="red"))
        sys.exit(1)


@mcli.command(name="lsh-config", help="Configure LSH integration settings")
@mcli.option("--set-url", help="Set LSH API URL")
@mcli.option("--set-api-key", help="Set LSH API key")
@mcli.option("--show", is_flag=True, help="Show current configuration")
def lsh_config(set_url: Optional[str], set_api_key: Optional[str], show: bool):
    """Configure LSH integration settings"""
    env_file = Path.home() / ".mcli" / "lsh.env"
    env_file.parent.mkdir(exist_ok=True)

    if show:
        mcli.echo(mcli.style("⚙️  LSH Configuration", fg="blue", bold=True))
        mcli.echo(f"API URL: {os.getenv('LSH_API_URL', 'not set')}")
        mcli.echo(f"API Key: {'set' if os.getenv('LSH_API_KEY') else 'not set'}")
        mcli.echo(f"Config file: {env_file}")
        return

    if set_url:
        # Update env file
        config = {}
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        config[key] = value

        config["LSH_API_URL"] = set_url

        with open(env_file, "w") as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")

        mcli.echo(mcli.style(f"✅ LSH API URL set to: {set_url}", fg="green"))

    if set_api_key:
        # Update env file
        config = {}
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        config[key] = value

        config["LSH_API_KEY"] = set_api_key

        with open(env_file, "w") as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")

        mcli.echo(mcli.style("✅ LSH API key updated", fg="green"))


# Register all commands with mcli
def register_lsh_commands():
    """Register LSH integration commands with mcli"""
    pass  # Commands are automatically registered via decorators
