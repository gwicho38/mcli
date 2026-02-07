"""Service lifecycle management commands for mcli.

Provides `mcli services <subcommand>` for managing long-running processes
as named services with start/stop/restart, health checks, and log tailing.
"""

import sys
import time

import click
from rich.console import Console
from rich.table import Table

from mcli.lib.constants import ServiceDefaults, ServiceMessages
from mcli.lib.services.config import ServiceConfig
from mcli.lib.services.manager import ServiceManager
from mcli.lib.services.state import list_states, load_state, remove_state

console = Console()
manager = ServiceManager()


def _get_config_from_state(name: str) -> ServiceConfig:
    """Build a ServiceConfig from persisted state."""
    state = load_state(name)
    if not state or not state.config:
        return ServiceConfig(name=name)
    cfg = state.config
    return ServiceConfig(
        name=name,
        command=cfg.get("command"),
        service_type=cfg.get("service_type", "daemon"),
        restart_policy=cfg.get("restart_policy", "never"),
        port=cfg.get("port"),
        host=cfg.get("host", ServiceDefaults.DEFAULT_HOST),
        health_check=cfg.get("health_check"),
    )


@click.group(
    "services",
    help="\U0001f6e0\ufe0f Manage long-running services (start/stop/restart, health, logs).",
)
def services():
    """Service lifecycle management."""
    pass


@services.command("list")
def list_services():
    """List all known services and their status."""
    svc_list = manager.list_services()
    if not svc_list:
        console.print(ServiceMessages.NO_SERVICES)
        return

    table = Table(title="Services")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("PID", style="yellow")
    table.add_column("Port", style="blue")
    table.add_column("Type", style="green")
    table.add_column("Restarts", style="dim")

    for svc in svc_list:
        status = svc.get("status", "unknown")
        if status == "running":
            status_display = "[green]running[/green]"
        elif status == "stopped":
            status_display = "[dim]stopped[/dim]"
        elif status == "failed":
            status_display = "[red]failed[/red]"
        else:
            status_display = f"[dim]{status}[/dim]"

        config = svc.get("config", {})
        table.add_row(
            svc["name"],
            status_display,
            str(svc.get("pid") or "-"),
            str(config.get("port") or "-"),
            config.get("service_type", "-"),
            str(svc.get("restart_count", 0)),
        )

    console.print(table)


@services.command("start")
@click.argument("name")
@click.option("--command", "-c", help="Shell command to run as a service.")
@click.option("--port", "-p", type=int, help="Port for the service.")
@click.option("--host", "-h", "host", default=None, help="Host to bind to.")
@click.option(
    "--type",
    "service_type",
    type=click.Choice(["http", "worker", "daemon"]),
    default="daemon",
    help="Service type.",
)
@click.option(
    "--restart",
    "restart_policy",
    type=click.Choice(["never", "on-failure", "always"]),
    default="never",
    help="Restart policy.",
)
@click.option("--health-check", help="Health check path (for http) or callable.")
def start_service(name, command, port, host, service_type, restart_policy, health_check):
    """Start a service as a background daemon."""
    # Check if already running
    existing_state = load_state(name)
    if existing_state and existing_state.status == "running" and existing_state.pid:
        from mcli.lib.services.health import check_pid_alive

        if check_pid_alive(existing_state.pid):
            console.print(
                ServiceMessages.SERVICE_ALREADY_RUNNING.format(name=name, pid=existing_state.pid)
            )
            return

    # Build config from args or existing state
    if command:
        config = ServiceConfig(
            name=name,
            command=command,
            port=port,
            host=host or ServiceDefaults.DEFAULT_HOST,
            service_type=service_type,
            restart_policy=restart_policy,
            health_check=health_check,
        )
    elif existing_state and existing_state.config and existing_state.config.get("command"):
        config = _get_config_from_state(name)
        # Override with any provided options
        if port is not None:
            config.port = port
        if host is not None:
            config.host = host
        if restart_policy != "never":
            config.restart_policy = restart_policy
        if health_check:
            config.health_check = health_check
    else:
        console.print(
            "[red]No command specified. Use --command/-c to provide the command to run.[/red]"
        )
        sys.exit(1)

    pid = manager.start_service(config)
    if pid:
        console.print(ServiceMessages.SERVICE_STARTED.format(name=name, pid=pid))

        # Start supervisor if restart policy is set
        if config.restart_policy != "never":
            from mcli.lib.services.supervisor import ServiceSupervisor

            supervisor = ServiceSupervisor(manager)
            supervisor.start_supervisor(config)
            console.print(
                ServiceMessages.SUPERVISOR_STARTED.format(name=name, policy=config.restart_policy)
            )
    else:
        console.print(ServiceMessages.SERVICE_FAILED_START.format(name=name, error="see logs"))
        sys.exit(1)


@services.command("stop")
@click.argument("name")
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=ServiceDefaults.GRACEFUL_TIMEOUT,
    help="Seconds to wait before force-killing.",
)
def stop_service(name, timeout):
    """Stop a running service."""
    state = load_state(name)
    if not state:
        console.print(ServiceMessages.SERVICE_NOT_FOUND.format(name=name))
        sys.exit(1)

    if state.status != "running":
        console.print(ServiceMessages.SERVICE_NOT_RUNNING.format(name=name))
        return

    if manager.stop_service(name, timeout=timeout):
        console.print(ServiceMessages.SERVICE_STOPPED.format(name=name))
    else:
        console.print(ServiceMessages.SERVICE_FAILED_STOP.format(name=name, error="see logs"))
        sys.exit(1)


@services.command("restart")
@click.argument("name")
def restart_service(name):
    """Restart a service (stop then start)."""
    state = load_state(name)
    if not state:
        console.print(ServiceMessages.SERVICE_NOT_FOUND.format(name=name))
        sys.exit(1)

    config = _get_config_from_state(name)
    if not config.command:
        console.print("[red]Cannot restart: no command in service state.[/red]")
        sys.exit(1)

    pid = manager.restart_service(config)
    if pid:
        console.print(ServiceMessages.SERVICE_RESTARTED.format(name=name, pid=pid))
    else:
        console.print(ServiceMessages.SERVICE_FAILED_START.format(name=name, error="see logs"))
        sys.exit(1)


@services.command("run")
@click.argument("name")
@click.option("--command", "-c", help="Shell command to run.")
@click.option("--port", "-p", type=int, help="Port for the service.")
def run_foreground(name, command, port):
    """Run a service in the foreground (Ctrl+C to stop)."""
    if command:
        config = ServiceConfig(name=name, command=command, port=port)
    else:
        config = _get_config_from_state(name)
        if not config.command:
            console.print("[red]No command specified. Use --command/-c.[/red]")
            sys.exit(1)

    console.print(ServiceMessages.RUNNING_FOREGROUND.format(name=name))
    exit_code = manager.run_foreground(config)
    console.print(ServiceMessages.FOREGROUND_STOPPED.format(name=name))
    sys.exit(exit_code)


@services.command("status")
@click.argument("name")
def service_status(name):
    """Show detailed status of a single service."""
    status = manager.get_service_status(name)
    if status["status"] == "unknown":
        console.print(ServiceMessages.SERVICE_NOT_FOUND.format(name=name))
        sys.exit(1)

    table = Table(title=f"Service: {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", status["name"])

    status_val = status["status"]
    if status_val == "running":
        status_display = "[green]running[/green]"
    elif status_val == "failed":
        status_display = "[red]failed[/red]"
    else:
        status_display = f"[dim]{status_val}[/dim]"
    table.add_row("Status", status_display)

    table.add_row("PID", str(status.get("pid") or "-"))
    table.add_row("Started", status.get("started_at") or "-")
    table.add_row("Stopped", status.get("stopped_at") or "-")
    table.add_row("Restarts", str(status.get("restart_count", 0)))

    health = status.get("health_status")
    if health == "healthy":
        table.add_row("Health", ServiceMessages.HEALTH_HEALTHY)
    elif health == "unhealthy":
        table.add_row("Health", ServiceMessages.HEALTH_UNHEALTHY)
    elif health:
        table.add_row("Health", ServiceMessages.HEALTH_UNKNOWN)

    config = status.get("config", {})
    if config.get("port"):
        table.add_row("Port", str(config["port"]))
    if config.get("service_type"):
        table.add_row("Type", config["service_type"])
    if config.get("restart_policy"):
        table.add_row("Restart Policy", config["restart_policy"])
    if config.get("command"):
        table.add_row("Command", config["command"])

    console.print(table)


@services.command("logs")
@click.argument("name")
@click.option(
    "--lines", "-n", type=int, default=ServiceDefaults.LOG_TAIL_LINES, help="Lines to show."
)
@click.option("--follow", "-f", is_flag=True, help="Follow log output.")
@click.option("--stderr", is_flag=True, help="Show stderr instead of stdout.")
def service_logs(name, lines, follow, stderr):
    """Tail log output for a service."""
    state = load_state(name)
    if not state:
        console.print(ServiceMessages.SERVICE_NOT_FOUND.format(name=name))
        sys.exit(1)

    if not follow:
        logs = manager.get_logs(name, lines=lines)
        stream = "stderr" if stderr else "stdout"
        output = logs.get(stream, "")
        if output:
            console.print(output)
        else:
            console.print(ServiceMessages.LOG_FILE_NOT_FOUND.format(name=name))
        return

    # Follow mode
    console.print(ServiceMessages.FOLLOWING_LOGS.format(name=name))
    log_path = manager._stderr_log(name) if stderr else manager._stdout_log(name)

    if not log_path.exists():
        console.print(ServiceMessages.LOG_FILE_NOT_FOUND.format(name=name))
        return

    try:
        with open(log_path) as f:
            # Seek to end minus N lines
            f.seek(0, 2)
            file_size = f.tell()
            f.seek(max(0, file_size - lines * 200))
            # Discard partial first line
            if f.tell() > 0:
                f.readline()
            # Print remaining
            for line in f:
                console.print(line, end="")

            # Follow new output
            while True:
                line = f.readline()
                if line:
                    console.print(line, end="")
                else:
                    time.sleep(0.5)
    except KeyboardInterrupt:
        pass


@services.command("cleanup")
def cleanup_services():
    """Remove stale PID files and update state for dead services."""
    count = manager.cleanup_stale()
    if count > 0:
        console.print(ServiceMessages.CLEANUP_COMPLETE.format(count=count))
    else:
        console.print(ServiceMessages.CLEANUP_NONE)


@services.command("info")
@click.argument("name")
def service_info(name):
    """Show full config, state, and process stats for a service."""
    info = manager.get_service_info(name)
    if not info:
        console.print(ServiceMessages.SERVICE_NOT_FOUND.format(name=name))
        sys.exit(1)

    table = Table(title=f"Service Info: {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    for key, value in info.items():
        if key == "config" and isinstance(value, dict):
            for ck, cv in value.items():
                table.add_row(f"config.{ck}", str(cv) if cv is not None else "-")
        else:
            display_val = str(value) if value is not None else "-"
            table.add_row(key, display_val)

    console.print(table)
