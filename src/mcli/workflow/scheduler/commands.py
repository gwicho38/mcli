"""
CLI commands for the MCLI scheduler system
"""

import json
from datetime import datetime
from typing import Optional

import click

from mcli.lib.logger.logger import get_logger

from .cron_parser import CronExpression, get_next_run_times, validate_cron_expression
from .job import JobStatus, JobType, ScheduledJob
from .scheduler import (
    JobScheduler,
    create_desktop_cleanup_job,
    create_system_backup_job,
    create_temp_cleanup_job,
)

logger = get_logger(__name__)

# Global scheduler instance
_scheduler: Optional[JobScheduler] = None


def get_scheduler() -> JobScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler


@click.group()
def scheduler():
    """Robust cron-like job scheduling system"""
    pass


@scheduler.command()
@click.option("--start", is_flag=True, help="Start the scheduler")
@click.option("--stop", is_flag=True, help="Stop the scheduler")
@click.option("--restart", is_flag=True, help="Restart the scheduler")
@click.option("--status", is_flag=True, help="Show scheduler status")
def control(start: bool, stop: bool, restart: bool, status: bool):
    """Control the scheduler daemon"""
    sched = get_scheduler()

    if restart:
        click.echo("Restarting scheduler...")
        sched.stop()
        sched.start()
        click.echo("Scheduler restarted")
    elif start:
        click.echo("Starting scheduler...")
        sched.start()
        click.echo("Scheduler started")
    elif stop:
        click.echo("Stopping scheduler...")
        sched.stop()
        click.echo("Scheduler stopped")
    elif status:
        stats = sched.get_scheduler_stats()
        click.echo(f"Scheduler running: {stats['running']}")
        click.echo(f"Total jobs: {stats['total_jobs']}")
        click.echo(f"Enabled jobs: {stats['enabled_jobs']}")
        click.echo(f"Running jobs: {stats['running_jobs']}")
    else:
        click.echo("Use --start, --stop, --restart, or --status")


@scheduler.command()
@click.argument("name")
@click.argument("cron_expression")
@click.argument("command")
@click.option(
    "--type",
    "job_type",
    type=click.Choice([t.value for t in JobType]),
    default="command",
    help="Job type",
)
@click.option("--description", default="", help="Job description")
@click.option("--enabled/--disabled", default=True, help="Enable/disable job")
@click.option("--max-runtime", default=3600, help="Maximum runtime in seconds")
@click.option("--retry-count", default=0, help="Number of retries on failure")
@click.option("--retry-delay", default=60, help="Delay between retries in seconds")
@click.option("--working-dir", help="Working directory for job execution")
@click.option("--env", multiple=True, help="Environment variables (KEY=VALUE)")
def add(
    name: str,
    cron_expression: str,
    command: str,
    job_type: str,
    description: str,
    enabled: bool,
    max_runtime: int,
    retry_count: int,
    retry_delay: int,
    working_dir: Optional[str],
    env: tuple,
):
    """Add a new scheduled job"""

    # Validate cron expression
    if not validate_cron_expression(cron_expression):
        click.echo(f"Error: Invalid cron expression: {cron_expression}", err=True)
        return

    # Parse environment variables
    environment = {}
    for env_var in env:
        if "=" in env_var:
            key, value = env_var.split("=", 1)
            environment[key] = value
        else:
            click.echo(f"Warning: Invalid environment variable format: {env_var}")

    # Create job
    job = ScheduledJob(
        name=name,
        cron_expression=cron_expression,
        job_type=JobType(job_type),
        command=command,
        description=description,
        enabled=enabled,
        max_runtime=max_runtime,
        retry_count=retry_count,
        retry_delay=retry_delay,
        working_directory=working_dir,
        environment=environment,
    )

    # Add to scheduler
    sched = get_scheduler()
    if sched.add_job(job):
        click.echo(f"Added job: {name} ({job.id})")

        # Show next run times
        try:
            cron = CronExpression(cron_expression)
            if not cron.is_reboot:
                next_times = get_next_run_times(cron_expression, 3)
                if next_times:
                    click.echo("Next run times:")
                    for i, time in enumerate(next_times, 1):
                        click.echo(f"  {i}. {time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            logger.warning(f"Could not calculate next run times: {e}")
    else:
        click.echo("Failed to add job", err=True)


@scheduler.command()
@click.argument("job_id")
def remove(job_id: str):
    """Remove a scheduled job"""
    sched = get_scheduler()

    # Find job by ID or name
    job = sched.get_job(job_id)
    if not job:
        # Try to find by name
        for j in sched.get_all_jobs():
            if j.name == job_id:
                job = j
                break

    if not job:
        click.echo(f"Job not found: {job_id}", err=True)
        return

    if sched.remove_job(job.id):
        click.echo(f"Removed job: {job.name}")
    else:
        click.echo("Failed to remove job", err=True)


@scheduler.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.option("--status", "filter_status", help="Filter by job status")
@click.option("--enabled-only", is_flag=True, help="Show only enabled jobs")
def list(output_format: str, filter_status: Optional[str], enabled_only: bool):
    """List all scheduled jobs"""
    sched = get_scheduler()
    jobs = sched.get_all_jobs()

    # Apply filters
    if filter_status:
        try:
            status = JobStatus(filter_status)
            jobs = [job for job in jobs if job.status == status]
        except ValueError:
            click.echo(f"Invalid status: {filter_status}", err=True)
            return

    if enabled_only:
        jobs = [job for job in jobs if job.enabled]

    if not jobs:
        click.echo("No jobs found")
        return

    if output_format == "json":
        job_data = [job.to_dict() for job in jobs]
        click.echo(json.dumps(job_data, indent=2))
    else:
        # Table format
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        table.add_column("Name", style="cyan")
        table.add_column("Schedule", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="red")
        table.add_column("Enabled", style="blue")
        table.add_column("Last Run", style="dim")
        table.add_column("Next Run", style="dim")

        for job in jobs:
            enabled_str = "✓" if job.enabled else "✗"
            last_run = job.last_run.strftime("%m-%d %H:%M") if job.last_run else "Never"
            next_run = job.next_run.strftime("%m-%d %H:%M") if job.next_run else "Unknown"

            table.add_row(
                job.name[:20],
                job.cron_expression[:15],
                job.job_type.value,
                job.status.value,
                enabled_str,
                last_run,
                next_run,
            )

        console.print(table)


@scheduler.command()
@click.argument("job_id")
@click.option("--history", is_flag=True, help="Show execution history")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def show(job_id: str, history: bool, verbose: bool):
    """Show detailed information about a job"""
    sched = get_scheduler()

    # Find job by ID or name
    job = sched.get_job(job_id)
    if not job:
        for j in sched.get_all_jobs():
            if j.name == job_id:
                job = j
                break

    if not job:
        click.echo(f"Job not found: {job_id}", err=True)
        return

    # Show basic info
    click.echo(f"Job: {job.name}")
    click.echo(f"ID: {job.id}")
    click.echo(f"Type: {job.job_type.value}")
    click.echo(f"Schedule: {job.cron_expression}")
    click.echo(f"Description: {job.description}")
    click.echo(f"Status: {job.status.value}")
    click.echo(f"Enabled: {'Yes' if job.enabled else 'No'}")
    click.echo(f"Created: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if job.last_run:
        click.echo(f"Last Run: {job.last_run.strftime('%Y-%m-%d %H:%M:%S')}")
    if job.next_run:
        click.echo(f"Next Run: {job.next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    click.echo(f"Run Count: {job.run_count}")
    click.echo(f"Success Count: {job.success_count}")
    click.echo(f"Failure Count: {job.failure_count}")

    if verbose:
        click.echo(f"\nCommand: {job.command}")
        click.echo(f"Max Runtime: {job.max_runtime}s")
        click.echo(f"Retry Count: {job.retry_count}")
        click.echo(f"Retry Delay: {job.retry_delay}s")

        if job.working_directory:
            click.echo(f"Working Directory: {job.working_directory}")

        if job.environment:
            click.echo("Environment Variables:")
            for key, value in job.environment.items():
                click.echo(f"  {key}={value}")

        if job.last_output:
            click.echo(f"\nLast Output:\n{job.last_output}")

        if job.last_error:
            click.echo(f"\nLast Error:\n{job.last_error}")

    if history:
        click.echo(f"\nExecution History:")
        job_history = sched.storage.get_job_history(job.id, limit=10)

        if not job_history:
            click.echo("  No execution history")
        else:
            for record in job_history:
                executed_at = record.get("executed_at", "Unknown")
                status = record.get("status", "unknown")
                runtime = record.get("runtime_seconds", 0)
                click.echo(f"  {executed_at}: {status} ({runtime}s)")


@scheduler.command()
@click.argument("job_id")
@click.option("--enabled/--disabled", help="Enable or disable the job")
@click.option("--cron", help="Update cron expression")
@click.option("--command", help="Update command")
@click.option("--description", help="Update description")
@click.option("--max-runtime", type=int, help="Update max runtime")
def update(
    job_id: str,
    enabled: Optional[bool],
    cron: Optional[str],
    command: Optional[str],
    description: Optional[str],
    max_runtime: Optional[int],
):
    """Update a scheduled job"""
    sched = get_scheduler()

    # Find job
    job = sched.get_job(job_id)
    if not job:
        for j in sched.get_all_jobs():
            if j.name == job_id:
                job = j
                break

    if not job:
        click.echo(f"Job not found: {job_id}", err=True)
        return

    # Update fields
    updated = False
    if enabled is not None:
        job.enabled = enabled
        updated = True

    if cron:
        if not validate_cron_expression(cron):
            click.echo(f"Error: Invalid cron expression: {cron}", err=True)
            return
        job.cron_expression = cron
        updated = True

    if command:
        job.command = command
        updated = True

    if description is not None:
        job.description = description
        updated = True

    if max_runtime:
        job.max_runtime = max_runtime
        updated = True

    if updated:
        sched.storage.save_job(job)
        click.echo(f"Updated job: {job.name}")
    else:
        click.echo("No changes made")


@scheduler.command()
@click.argument("cron_expression")
@click.option("--count", default=5, help="Number of future run times to show")
def test_cron(cron_expression: str, count: int):
    """Test a cron expression and show next run times"""
    if not validate_cron_expression(cron_expression):
        click.echo(f"Error: Invalid cron expression: {cron_expression}", err=True)
        return

    try:
        cron = CronExpression(cron_expression)
        click.echo(f"Cron Expression: {cron_expression}")
        click.echo(f"Description: {cron.get_description()}")

        if cron.is_reboot:
            click.echo("This is a @reboot job (runs only at scheduler startup)")
        else:
            next_times = get_next_run_times(cron_expression, count)
            if next_times:
                click.echo(f"\nNext {len(next_times)} run times:")
                for i, time in enumerate(next_times, 1):
                    click.echo(f"  {i}. {time.strftime('%Y-%m-%d %H:%M:%S %A')}")
            else:
                click.echo("Could not calculate next run times")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@scheduler.command()
@click.option("--json", "output_json", is_flag=True, help="Output JSON for frontend")
def status(output_json: bool):
    """Show scheduler status and statistics"""
    sched = get_scheduler()
    stats = sched.get_scheduler_stats()

    if output_json:
        response = sched.create_json_response()
        click.echo(json.dumps(response, indent=2))
    else:
        click.echo(f"Scheduler Status: {'Running' if stats['running'] else 'Stopped'}")
        click.echo(f"Total Jobs: {stats['total_jobs']}")
        click.echo(f"Enabled Jobs: {stats['enabled_jobs']}")
        click.echo(f"Currently Running: {stats['running_jobs']}")

        monitor_stats = stats.get("monitor_stats", {})
        if monitor_stats.get("running_job_ids"):
            click.echo(f"Running Job IDs: {', '.join(monitor_stats['running_job_ids'])}")

        storage_info = stats.get("storage_info", {})
        if storage_info:
            click.echo(f"Storage Directory: {storage_info.get('storage_dir', 'Unknown')}")
            click.echo(f"Jobs in Storage: {storage_info.get('jobs_count', 0)}")
            click.echo(f"History Records: {storage_info.get('history_count', 0)}")


@scheduler.group()
def presets():
    """Pre-configured job templates"""
    pass


@presets.command()
@click.option("--cron", default="0 9 * * 1", help="Cron expression (default: Monday 9 AM)")
@click.option("--enabled/--disabled", default=True, help="Enable job")
def desktop_cleanup(cron: str, enabled: bool):
    """Add desktop file organization job"""
    job = create_desktop_cleanup_job("Desktop Organization", cron, enabled)

    sched = get_scheduler()
    if sched.add_job(job):
        click.echo(f"Added desktop cleanup job: {job.name}")
    else:
        click.echo("Failed to add desktop cleanup job", err=True)


@presets.command()
@click.option("--path", default="/tmp", help="Path to clean up")
@click.option("--days", default=7, help="Delete files older than this many days")
@click.option("--cron", default="0 2 * * *", help="Cron expression (default: daily 2 AM)")
@click.option("--enabled/--disabled", default=True, help="Enable job")
def temp_cleanup(path: str, days: int, cron: str, enabled: bool):
    """Add temporary file cleanup job"""
    job = create_temp_cleanup_job("Temp File Cleanup", cron, path, days, enabled)

    sched = get_scheduler()
    if sched.add_job(job):
        click.echo(f"Added temp cleanup job: {job.name}")
    else:
        click.echo("Failed to add temp cleanup job", err=True)


@presets.command()
@click.argument("backup_command")
@click.option("--cron", default="0 1 * * 0", help="Cron expression (default: Sunday 1 AM)")
@click.option("--enabled/--disabled", default=True, help="Enable job")
def system_backup(backup_command: str, cron: str, enabled: bool):
    """Add system backup job"""
    job = create_system_backup_job("System Backup", cron, backup_command, enabled)

    sched = get_scheduler()
    if sched.add_job(job):
        click.echo(f"Added system backup job: {job.name}")
    else:
        click.echo("Failed to add system backup job", err=True)


# Add the scheduler commands to the main CLI
def register_scheduler_commands(cli_group):
    """Register scheduler commands with the main CLI"""
    cli_group.add_command(scheduler)
