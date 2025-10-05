"""CLI interface for ML dashboard"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def launch(
    port: int = typer.Option(8501, "--port", "-p", help="Port to run dashboard on"),
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind to"),
    debug: bool = typer.Option(False, "--debug", help="Run in debug mode"),
):
    """Launch the ML monitoring dashboard"""

    # Get the dashboard app path
    dashboard_path = Path(__file__).parent / "app.py"

    if not dashboard_path.exists():
        console.print("[red]Dashboard app not found![/red]")
        raise typer.Exit(1)

    # Build streamlit command
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.port",
        str(port),
        "--server.address",
        host,
        "--browser.gatherUsageStats",
        "false",
    ]

    if debug:
        cmd.extend(["--logger.level", "debug"])

    console.print(f"[green]Starting ML Dashboard on http://{host}:{port}[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start dashboard: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
