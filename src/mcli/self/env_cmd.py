"""Python environment information command for mcli self.

This module provides the `mcli self env` command for displaying
Python environment information for workflows.
"""

import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir, get_git_root, is_git_repository
from mcli.lib.pyenv import PyEnvManager

logger = get_logger(__name__)
console = Console()


def get_python_version(python_exe: Path) -> str:
    """Get the Python version from an executable."""
    try:
        result = subprocess.run(
            [str(python_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        logger.debug(f"Error getting Python version: {e}")
    return "Unknown"


def get_installed_packages(python_exe: Path, limit: int = 20) -> list[tuple[str, str]]:
    """Get list of installed packages from a Python environment."""
    # Try uv pip list first (for uv-managed environments)
    try:
        result = subprocess.run(
            ["uv", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            packages = []
            for line in result.stdout.strip().split("\n"):
                if "==" in line:
                    name, version = line.split("==", 1)
                    packages.append((name, version))
            if packages:
                return packages[:limit]
    except Exception as e:
        logger.debug(f"Error getting packages via uv: {e}")

    # Fall back to pip
    try:
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            packages = []
            for line in result.stdout.strip().split("\n"):
                if "==" in line:
                    name, version = line.split("==", 1)
                    packages.append((name, version))
            return packages[:limit]
    except Exception as e:
        logger.debug(f"Error getting installed packages via pip: {e}")
    return []


def get_env_vars() -> dict[str, str]:
    """Get relevant Python environment variables."""
    import os

    relevant_vars = [
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "MCLI_VENV_PATH",
        "MCLI_USE_SYSTEM_PYTHON",
        "MCLI_AUTO_INSTALL_DEPS",
    ]
    return {k: v for k, v in os.environ.items() if k in relevant_vars}


@click.command("env")
@click.argument("workflow", required=False)
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Workspace directory to check environment for",
)
@click.option(
    "--packages",
    "-p",
    is_flag=True,
    help="Show installed packages",
)
@click.option(
    "--limit",
    "-l",
    default=20,
    help="Limit number of packages shown (default: 20)",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON",
)
def env_command(
    workflow: Optional[str],
    workspace: Optional[str],
    packages: bool,
    limit: int,
    as_json: bool,
):
    """🐍 Show Python environment information for workflows.

    Display detailed information about the Python environment used
    for running workflows, including virtual environment detection,
    Python version, and installed packages.

    \b
    Examples:
        mcli self env                    # Show env for current workspace
        mcli self env -w ~/repos/myapp/  # Show env for specific workspace
        mcli self env -p                 # Include installed packages
        mcli self env --json             # Output as JSON
    """
    import json as json_lib

    # Determine workspace directory
    if workspace:
        workspace_dir = Path(workspace)
    elif is_git_repository():
        workspace_dir = get_git_root()
    else:
        workspace_dir = Path.cwd()

    # Initialize PyEnvManager for the workspace
    manager = PyEnvManager(workspace_dir=workspace_dir)
    venv_path, source = manager.resolve_environment()
    python_exe = manager.get_python_executable()

    # Gather environment information
    env_info = {
        "workspace": str(workspace_dir),
        "workspace_name": workspace_dir.name,
        "source": source,
        "python_executable": str(python_exe),
        "python_version": get_python_version(python_exe),
        "platform": platform.platform(),
        "system_python": sys.executable,
    }

    if venv_path:
        env_info["venv_path"] = str(venv_path)
        env_info["venv_exists"] = venv_path.exists()

    # Get workflows directory for this workspace
    _workflows_dir = get_custom_commands_dir(global_mode=False)  # noqa: F841
    if workspace_dir and is_git_repository():
        from mcli.lib.constants.paths import DirNames

        # Check both new mcli/ and legacy .mcli/ local dir
        local_workflows = None
        for dir_name in [DirNames.LOCAL_MCLI, DirNames.LEGACY_LOCAL_MCLI]:
            candidate = workspace_dir / dir_name / "workflows"
            if candidate.exists():
                local_workflows = candidate
                break

        if local_workflows is not None:
            env_info["workflows_dir"] = str(local_workflows)
            # Count workflow scripts
            script_count = sum(
                1 for f in local_workflows.iterdir() if f.suffix in [".py", ".sh", ".js", ".ts"]
            )
            env_info["workflow_count"] = script_count

    # Get environment variables
    env_vars = get_env_vars()
    if env_vars:
        env_info["env_vars"] = env_vars

    # Get installed packages if requested
    if packages:
        pkg_list = get_installed_packages(python_exe, limit=limit)
        env_info["packages"] = [{"name": n, "version": v} for n, v in pkg_list]
        env_info["package_count"] = len(pkg_list)

    # Output
    if as_json:
        click.echo(json_lib.dumps(env_info, indent=2, default=str))
        return

    # Rich formatted output
    console.print()
    console.print("[bold cyan]🐍 Python Environment Info[/bold cyan]")
    console.print("=" * 50)

    # Basic info table
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Label", style="dim")
    info_table.add_column("Value", style="bold")

    info_table.add_row("Workspace", f"[cyan]{env_info['workspace_name']}[/cyan]")
    info_table.add_row("Path", str(workspace_dir))
    info_table.add_row("Environment Source", f"[green]{source}[/green]")
    info_table.add_row("Python Version", env_info["python_version"])
    info_table.add_row("Python Executable", str(python_exe))

    if venv_path:
        venv_status = "[green]exists[/green]" if venv_path.exists() else "[red]missing[/red]"
        info_table.add_row("Virtual Environment", f"{venv_path} ({venv_status})")

    if "workflows_dir" in env_info:
        info_table.add_row(
            "Workflows",
            f"{env_info.get('workflow_count', 0)} scripts in {env_info['workflows_dir']}",
        )

    console.print(Panel(info_table, title="Environment", border_style="blue"))

    # Environment variables
    if env_vars:
        var_table = Table(show_header=True, header_style="bold")
        var_table.add_column("Variable", style="cyan")
        var_table.add_column("Value")

        for var, value in env_vars.items():
            # Truncate long values
            display_value = value if len(value) <= 60 else value[:57] + "..."
            var_table.add_row(var, display_value)

        console.print(Panel(var_table, title="Environment Variables", border_style="yellow"))

    # Installed packages
    if packages:
        pkg_list = env_info.get("packages", [])
        if pkg_list:
            pkg_table = Table(show_header=True, header_style="bold")
            pkg_table.add_column("Package", style="green")
            pkg_table.add_column("Version", style="dim")

            for pkg in pkg_list:
                pkg_table.add_row(pkg["name"], pkg["version"])

            title = f"Installed Packages (showing {len(pkg_list)})"
            console.print(Panel(pkg_table, title=title, border_style="green"))

            if len(pkg_list) == limit:
                console.print("[dim]Use --limit to show more packages[/dim]")
        else:
            console.print("[yellow]Could not retrieve installed packages[/yellow]")

    console.print()


# Export for registration
env = env_command
