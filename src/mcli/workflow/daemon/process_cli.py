import json
from typing import Optional

import click
import requests

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

# Default API URL - should match the daemon configuration
API_BASE_URL = "http://localhost:8000"


@click.group(name="process")
def process_cli():
    """Docker-like process management commands"""
    pass


@process_cli.command("ps")
@click.option("--all", "-a", is_flag=True, help="Show all processes including exited ones")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_processes(all: bool, as_json: bool):
    """List processes (like 'docker ps')"""
    try:
        params = {"all": "true"} if all else {}
        response = requests.get(f"{API_BASE_URL}/processes", params=params)

        if response.status_code == 200:
            data = response.json()
            processes = data.get("processes", [])

            if as_json:
                click.echo(json.dumps(data, indent=2))
                return

            if not processes:
                click.echo("No processes found")
                return

            # Print header
            click.echo(
                f"{'CONTAINER ID':<13} {'NAME':<15} {'COMMAND':<25} {'STATUS':<10} {'UPTIME':<10} {'CPU':<8} {'MEMORY'}"
            )
            click.echo("-" * 90)

            # Print process rows
            for proc in processes:
                click.echo(
                    f"{proc['id']:<13} {proc['name']:<15} {proc['command'][:24]:<25} {proc['status']:<10} {proc['uptime']:<10} {proc['cpu']:<8} {proc['memory']}"
                )
        else:
            click.echo(f"Error: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


@process_cli.command("run")
@click.argument("command")
@click.argument("args", nargs=-1)
@click.option("--name", help="Name for the process container")
@click.option("--detach", "-d", is_flag=True, default=True, help="Run in detached mode")
@click.option("--working-dir", help="Working directory inside container")
def run_process(
    command: str, args: tuple, name: Optional[str], detach: bool, working_dir: Optional[str]
):
    """Create and start a process (like 'docker run')"""
    try:
        data = {
            "name": name or f"proc-{command}",
            "command": command,
            "args": list(args),
            "detach": detach,
        }

        if working_dir:
            data["working_dir"] = working_dir

        response = requests.post(f"{API_BASE_URL}/processes/run", json=data)

        if response.status_code == 200:
            result = response.json()
            click.echo(f"Started process with ID: {result['id']}")
            if detach:
                click.echo("Use 'mcli workflow daemon process logs <id>' to view output")
        else:
            click.echo(f"Error: HTTP {response.status_code}")
            if response.text:
                click.echo(response.text)

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


@process_cli.command("logs")
@click.argument("process_id")
@click.option("--lines", "-n", type=int, help="Number of lines to show from end of logs")
def show_logs(process_id: str, lines: Optional[int]):
    """Show logs for a process (like 'docker logs')"""
    try:
        params = {}
        if lines:
            params["lines"] = lines

        response = requests.get(f"{API_BASE_URL}/processes/{process_id}/logs", params=params)

        if response.status_code == 200:
            logs = response.json()

            if logs.get("stdout"):
                click.echo(logs["stdout"], nl=False)
            if logs.get("stderr"):
                click.echo(logs["stderr"], nl=False)
            if not logs.get("stdout") and not logs.get("stderr"):
                click.echo("No logs available")
        elif response.status_code == 404:
            click.echo(f"Process {process_id} not found")
        else:
            click.echo(f"Error: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


@process_cli.command("inspect")
@click.argument("process_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def inspect_process(process_id: str, as_json: bool):
    """Show detailed information about a process (like 'docker inspect')"""
    try:
        response = requests.get(f"{API_BASE_URL}/processes/{process_id}")

        if response.status_code == 200:
            info = response.json()

            if as_json:
                click.echo(json.dumps(info, indent=2))
                return

            click.echo(f"Process ID: {info['id']}")
            click.echo(f"Name: {info['name']}")
            click.echo(f"Status: {info['status']}")
            click.echo(f"PID: {info.get('pid', 'N/A')}")
            click.echo(f"Command: {info['command']} {' '.join(info.get('args', []))}")
            click.echo(f"Working Dir: {info.get('working_dir', 'N/A')}")
            click.echo(f"Created: {info.get('created_at', 'N/A')}")
            click.echo(f"Started: {info.get('started_at', 'N/A')}")

            if info.get("stats"):
                stats = info["stats"]
                click.echo(f"\nResource Usage:")
                click.echo(f"  CPU: {stats.get('cpu_percent', 0):.1f}%")
                click.echo(f"  Memory: {stats.get('memory_mb', 0):.1f} MB")
                click.echo(f"  Uptime: {stats.get('uptime_seconds', 0)} seconds")

        elif response.status_code == 404:
            click.echo(f"Process {process_id} not found")
        else:
            click.echo(f"Error: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


@process_cli.command("stop")
@click.argument("process_id")
@click.option("--timeout", "-t", type=int, default=10, help="Timeout in seconds")
def stop_process(process_id: str, timeout: int):
    """Stop a process (like 'docker stop')"""
    try:
        data = {"timeout": timeout}
        response = requests.post(f"{API_BASE_URL}/processes/{process_id}/stop", json=data)

        if response.status_code == 200:
            click.echo(f"Process {process_id} stopped")
        elif response.status_code == 404:
            click.echo(f"Process {process_id} not found")
        else:
            click.echo(f"Error: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


@process_cli.command("start")
@click.argument("process_id")
def start_process(process_id: str):
    """Start a stopped process (like 'docker start')"""
    try:
        response = requests.post(f"{API_BASE_URL}/processes/{process_id}/start")

        if response.status_code == 200:
            click.echo(f"Process {process_id} started")
        elif response.status_code == 404:
            click.echo(f"Process {process_id} not found")
        else:
            click.echo(f"Error: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


@process_cli.command("kill")
@click.argument("process_id")
def kill_process(process_id: str):
    """Kill a process (like 'docker kill')"""
    try:
        response = requests.post(f"{API_BASE_URL}/processes/{process_id}/kill")

        if response.status_code == 200:
            click.echo(f"Process {process_id} killed")
        elif response.status_code == 404:
            click.echo(f"Process {process_id} not found")
        else:
            click.echo(f"Error: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


@process_cli.command("rm")
@click.argument("process_id")
@click.option("--force", "-f", is_flag=True, help="Force remove running process")
def remove_process(process_id: str, force: bool):
    """Remove a process (like 'docker rm')"""
    try:
        params = {"force": "true"} if force else {}
        response = requests.delete(f"{API_BASE_URL}/processes/{process_id}", params=params)

        if response.status_code == 200:
            click.echo(f"Process {process_id} removed")
        elif response.status_code == 404:
            click.echo(f"Process {process_id} not found")
        else:
            click.echo(f"Error: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error connecting to daemon: {e}")


if __name__ == "__main__":
    process_cli()
