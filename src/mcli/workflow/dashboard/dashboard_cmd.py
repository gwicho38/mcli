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


@dashboard.command()
@click.option("--port", "-p", default=8501, help="Port to run dashboard on")
@click.option("--host", "-h", default="localhost", help="Host to bind to")
@click.option("--debug", is_flag=True, help="Run in debug mode")
@click.option(
    "--variant",
    "-v",
    type=click.Choice(["integrated", "supabase", "training"]),
    default="supabase",
    help="Dashboard variant to launch (default: supabase)",
)
def launch(port, host, debug, variant):
    """Launch the ML monitoring dashboard.

    Variants:
      - supabase: Politician trading dashboard with Supabase integration (default)
      - integrated: Full ML dashboard with local database
      - training: ML training dashboard
    """

    click.echo(f"🚀 Starting {variant.title()} Dashboard on http://{host}:{port}")

    # Get the dashboard app path based on variant
    dashboard_dir = Path(__file__).parent.parent.parent / "ml" / "dashboard"

    if variant == "supabase":
        dashboard_path = dashboard_dir / "app_supabase.py"
    elif variant == "integrated":
        dashboard_path = dashboard_dir / "app_integrated.py"
    elif variant == "training":
        dashboard_path = dashboard_dir / "app_training.py"
    else:
        dashboard_path = dashboard_dir / "app.py"

    if not dashboard_path.exists():
        click.echo(f"❌ Dashboard app not found at {dashboard_path}!")
        logger.error(f"Dashboard app not found at {dashboard_path}")
        sys.exit(1)

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

    click.echo(f"📊 Dashboard is starting from {dashboard_path.name}...")
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
        import plotly
        import streamlit

        click.echo("✅ Dashboard dependencies installed")
        click.echo(f"   Streamlit version: {streamlit.__version__}")
        click.echo(f"   Plotly version: {plotly.__version__}")
    except ImportError as e:
        click.echo(f"❌ Missing dependencies: {e}")
        click.echo("   Run: uv pip install streamlit plotly")

    # Check Supabase configuration
    import os

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    click.echo("\n🔌 Supabase Configuration:")
    if supabase_url:
        click.echo(f"   URL: {supabase_url}")
    else:
        click.echo("   ❌ SUPABASE_URL not set")

    if supabase_key:
        click.echo(f"   Key: {'*' * 20}...{supabase_key[-8:]}")
    else:
        click.echo("   ❌ SUPABASE_KEY not set")

    if not supabase_url or not supabase_key:
        click.echo("\n⚠️  To configure Supabase, set environment variables:")
        click.echo("   export SUPABASE_URL=https://your-project.supabase.co")
        click.echo("   export SUPABASE_KEY=your-anon-key")

    click.echo("\n💡 Quick start:")
    click.echo("   mcli workflow dashboard launch                    # Launch Supabase dashboard")
    click.echo("   mcli workflow dashboard launch --variant training # Launch training dashboard")
    click.echo("   mcli workflow dashboard launch --port 8502        # Custom port")
    click.echo("   mcli workflow dashboard launch --host 0.0.0.0     # Expose to network")


@dashboard.command()
def test():
    """Test Supabase connection."""
    import os

    from mcli.ml.dashboard.common import get_supabase_client

    click.echo("🔍 Testing Supabase connection...")
    click.echo("━" * 40)

    # Check environment variables
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url:
        click.echo("❌ SUPABASE_URL not set")
        sys.exit(1)

    if not key:
        click.echo("❌ SUPABASE_KEY or SUPABASE_ANON_KEY not set")
        sys.exit(1)

    click.echo(f"✅ URL configured: {url}")
    click.echo(f"✅ Key configured: {'*' * 20}...{key[-8:]}")

    # Try to connect
    client = get_supabase_client()

    if not client:
        click.echo("❌ Failed to create Supabase client")
        sys.exit(1)

    click.echo("✅ Supabase client created")

    # Try to query a table
    try:
        response = client.table("politicians").select("id").limit(1).execute()
        click.echo(f"✅ Successfully queried 'politicians' table ({len(response.data)} records)")
    except Exception as e:
        click.echo(f"⚠️  Could not query 'politicians' table: {e}")
        click.echo("   (Table might not exist yet)")

    click.echo("\n✅ Connection test passed!")
