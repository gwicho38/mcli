"""ML Dashboard commands for mcli."""

import subprocess
import sys
from pathlib import Path

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@click.group(name="dashboard")
def dashboard():
    """ML monitoring dashboard commands."""
    pass


@dashboard.command()
@click.option("--port", "-p", default=8501, help="Port to run dashboard on")
@click.option("--host", "-h", default="localhost", help="Host to bind to")
@click.option("--debug", is_flag=True, help="Run in debug mode")
def launch(port, host, debug):
    """Launch the ML monitoring dashboard."""

    click.echo(f"🚀 Starting ML Dashboard on http://{host}:{port}")

    # Get the dashboard app path - use Supabase version to avoid joblib issues
    dashboard_path = Path(__file__).parent.parent.parent / "ml" / "dashboard" / "app_supabase.py"

    if not dashboard_path.exists():
        click.echo("❌ Dashboard app not found!")
        logger.error(f"Dashboard app not found at {dashboard_path}")
        sys.exit(1)

    # Build streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port", str(port),
        "--server.address", host,
        "--browser.gatherUsageStats", "false"
    ]

    if debug:
        cmd.extend(["--logger.level", "debug"])

    click.echo("📊 Dashboard is starting...")
    click.echo("Press Ctrl+C to stop")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        click.echo("\n⏹️  Dashboard stopped")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to start dashboard: {e}")
        logger.error(f"Dashboard failed to start: {e}")
        sys.exit(1)


@dashboard.command()
def info():
    """Show dashboard information and status."""

    click.echo("📊 ML Dashboard Information")
    click.echo("━" * 40)

    # Check if dependencies are installed
    try:
        import streamlit
        import plotly

        click.echo("✅ Dashboard dependencies installed")
        click.echo(f"   Streamlit version: {streamlit.__version__}")
        click.echo(f"   Plotly version: {plotly.__version__}")
    except ImportError as e:
        click.echo(f"❌ Missing dependencies: {e}")
        click.echo("   Run: uv sync --extra dashboard")

    # Check database connection
    try:
        from mcli.ml.config import settings
        click.echo(f"\n📁 Database URL: {settings.database.url}")
        click.echo(f"📍 Redis URL: {settings.redis.url}")
    except Exception as e:
        click.echo(f"⚠️  Configuration not available: {e}")

    click.echo("\n💡 Quick start:")
    click.echo("   mcli workflow dashboard launch")
    click.echo("   mcli workflow dashboard launch --port 8502 --host 0.0.0.0")


@dashboard.command()
@click.argument("action", type=click.Choice(["start", "stop", "restart"]))
def service(action):
    """Manage dashboard as a background service."""

    if action == "start":
        click.echo("🚀 Starting dashboard service...")
        # Could implement systemd or pm2 integration here
        click.echo("⚠️  Service mode not yet implemented")
        click.echo("   Use 'mcli workflow dashboard launch' instead")
    elif action == "stop":
        click.echo("⏹️  Stopping dashboard service...")
        click.echo("⚠️  Service mode not yet implemented")
    elif action == "restart":
        click.echo("🔄 Restarting dashboard service...")
        click.echo("⚠️  Service mode not yet implemented")


if __name__ == "__main__":
    dashboard()