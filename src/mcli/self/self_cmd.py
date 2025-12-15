"""
Self-management commands for mcli.
Provides utilities for maintaining and extending the CLI itself.
"""

import hashlib
import importlib
import inspect
import json
import os
import platform
import sys
import time
from datetime import datetime
from functools import lru_cache
from importlib.metadata import metadata, version
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import tomli
from rich.console import Console
from rich.table import Table

try:
    import warnings

    # Suppress the warning about python-Levenshtein
    warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher")
    from fuzzywuzzy import process
except ImportError:
    process = None

from mcli.lib.constants import ErrorMessages
from mcli.lib.logger.logger import get_logger

logger = get_logger()


# Create a Click command group instead of Typer
@click.group(name="self", help="Manage and extend the mcli application")
def self_app():
    """
    Self-management commands for mcli.
    """


console = Console()

LOCKFILE_PATH = Path.home() / ".local" / "mcli" / "command_lock.json"


# Version info utility
@lru_cache
def get_version_info(verbose: bool = False) -> str:
    """Get version info, cached to prevent multiple calls."""
    try:
        # Try mcli-framework first (PyPI package name), then mcli (local dev)
        mcli_version = None
        meta = None

        for pkg_name in ["mcli-framework", "mcli"]:
            try:
                mcli_version = version(pkg_name)
                meta = metadata(pkg_name)
                break
            except Exception:
                continue

        if mcli_version is None:
            return "Could not determine version: Package metadata not found"

        info = [f"mcli version {mcli_version}"]

        if verbose:
            info.extend(
                [
                    f"\nPython: {sys.version.split()[0]}",
                    f"Platform: {platform.platform()}",
                    f"Description: {meta.get('Summary', 'Not available') if meta else 'Not available'}",
                    f"Author: {meta.get('Author', 'Not available') if meta else 'Not available'}",
                ]
            )
        return "\n".join(info)
    except Exception as e:
        return f"Error getting version info: {e}"


# Utility functions for command state lockfile


def get_current_command_state():
    """Collect all command metadata (names, groups, etc.)."""
    # This should use your actual command collection logic
    # For now, use the collect_commands() function
    return collect_commands()


def hash_command_state(commands):
    """Hash the command state for fast comparison."""
    # Sort for deterministic hash
    commands_sorted = sorted(commands, key=lambda c: (c.get("group") or "", c["name"]))
    state_json = json.dumps(commands_sorted, sort_keys=True)
    return hashlib.sha256(state_json.encode("utf-8")).hexdigest()


def load_lockfile():
    if LOCKFILE_PATH.exists():
        with open(LOCKFILE_PATH) as f:
            return json.load(f)
    return []


def save_lockfile(states):
    with open(LOCKFILE_PATH, "w") as f:
        json.dump(states, f, indent=2, default=str)


def append_lockfile(new_state):
    states = load_lockfile()
    states.append(new_state)
    save_lockfile(states)


def find_state_by_hash(hash_value):
    states = load_lockfile()
    for state in states:
        if state["hash"] == hash_value:
            return state
    return None


def restore_command_state(hash_value):
    state = find_state_by_hash(hash_value)
    if not state:
        return False
    # Here you would implement logic to restore the command registry to this state
    # For now, just print the commands
    print(json.dumps(state["commands"], indent=2))
    return True


# On CLI startup, check and update lockfile if needed
# NOTE: The commands group has been moved to mcli.app.commands_cmd for better organization


def check_and_update_command_lockfile():
    current_commands = get_current_command_state()
    current_hash = hash_command_state(current_commands)
    states = load_lockfile()
    if states and states[-1]["hash"] == current_hash:
        # No change
        return
    # New state, append
    new_state = {
        "hash": current_hash,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "commands": current_commands,
    }
    append_lockfile(new_state)
    logger.info(f"Appended new command state {current_hash[:8]} to lockfile.")


# Call this at the top of your CLI entrypoint (main.py or similar)
# check_and_update_command_lockfile()


def get_command_template(name: str, group: Optional[str] = None) -> str:
    """Generate template code for a new command."""

    if group:
        # Template for a command in a group using Click
        # Use 'app' as the variable name so it's found first
        template = f'''"""
{name} command for mcli.{group}.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

# Create a Click command group
@click.group(name="{name}")
def app():
    """Description for {name} command group."""
    pass

@app.command("hello")
@click.argument("name", default="World")
def hello(name: str):
    """Example subcommand."""
    logger.info(f"Hello, {{name}}! This is the {name} command.")
    click.echo(f"Hello, {{name}}! This is the {name} command.")
'''
    else:
        # Template for a command directly under self using Click
        template = f'''"""
{name} command for mcli.self.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

def {name}_command(name: str = "World"):
    """
    {name.capitalize()} command.
    """
    logger.info(f"Hello, {{name}}! This is the {name} command.")
    click.echo(f"Hello, {{name}}! This is the {name} command.")
'''

    return template


# NOTE: search command has been moved to mcli.app.commands_cmd for better organization


def collect_commands() -> list[dict[str, Any]]:
    """Collect all commands from the mcli application."""
    commands = []

    # Look for command modules in the mcli package
    mcli_path = Path(__file__).parent.parent

    # This finds command groups as directories under mcli
    for item in mcli_path.iterdir():
        if item.is_dir() and not item.name.startswith("__") and not item.name.startswith("."):
            group_name = item.name

            # Recursively find all Python files that might define commands
            for py_file in item.glob("**/*.py"):
                if py_file.name.startswith("__"):
                    continue

                # Convert file path to module path
                relative_path = py_file.relative_to(mcli_path.parent)
                module_name = ".".join(relative_path.with_suffix("").parts)

                try:
                    # Suppress Streamlit warnings and logging during module import
                    import logging
                    import warnings
                    from contextlib import redirect_stderr
                    from io import StringIO

                    # Suppress Python warnings
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
                        warnings.filterwarnings("ignore", message=".*No runtime found.*")
                        warnings.filterwarnings(
                            "ignore", message=".*Session state does not function.*"
                        )
                        warnings.filterwarnings("ignore", message=".*to view this Streamlit app.*")

                        # Suppress Streamlit logger warnings
                        streamlit_logger = logging.getLogger("streamlit")
                        original_level = streamlit_logger.level
                        streamlit_logger.setLevel(logging.CRITICAL)

                        # Also suppress specific Streamlit sub-loggers
                        logging.getLogger(
                            "streamlit.runtime.scriptrunner_utils.script_run_context"
                        ).setLevel(logging.CRITICAL)
                        logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(
                            logging.CRITICAL
                        )

                        # Redirect stderr to suppress Streamlit warnings
                        with redirect_stderr(StringIO()):
                            try:
                                # Try to import the module
                                module = importlib.import_module(module_name)
                            finally:
                                # Restore original logging level
                                streamlit_logger.setLevel(original_level)

                    # Extract command and group objects
                    for _name, obj in inspect.getmembers(module):
                        # Handle Click commands and groups
                        if isinstance(obj, click.Command):
                            if isinstance(obj, click.Group):
                                # Found a Click group
                                app_info = {
                                    "name": obj.name,
                                    "group": group_name,
                                    "path": module_name,
                                    "help": obj.help,
                                }
                                commands.append(app_info)

                                # Add subcommands if any
                                for cmd_name, cmd in obj.commands.items():
                                    commands.append(
                                        {
                                            "name": cmd_name,
                                            "group": f"{group_name}.{app_info['name']}",
                                            "path": f"{module_name}.{cmd_name}",
                                            "help": cmd.help,
                                        }
                                    )
                            else:
                                # Found a standalone Click command
                                commands.append(
                                    {
                                        "name": obj.name,
                                        "group": group_name,
                                        "path": f"{module_name}.{obj.name}",
                                        "help": obj.help,
                                    }
                                )
                except (ImportError, AttributeError) as e:
                    logger.debug(f"Skipping {module_name}: {e}")

    return commands


def open_editor_for_command(
    command_name: str, command_group: str, description: str
) -> Optional[str]:
    """
    Open the user's default editor to allow them to write command logic.

    Args:
        command_name: Name of the command
        command_group: Group for the command
        description: Description of the command

    Returns:
        The Python code written by the user, or None if cancelled
    """
    import os
    import subprocess
    import sys
    import tempfile

    # Get the user's default editor
    editor = os.environ.get("EDITOR")
    if not editor:
        # Try common editors in order of preference
        for common_editor in ["vim", "nano", "code", "subl", "atom", "emacs"]:
            if subprocess.run(["which", common_editor], capture_output=True).returncode == 0:
                editor = common_editor
                break

    if not editor:
        click.echo(f"❌ {ErrorMessages.EDITOR_NOT_FOUND}")
        return None

    # Create a temporary file with the template
    template = get_command_template(command_name, command_group)

    # Add helpful comments to the template
    enhanced_template = f'''"""
{command_name} command for mcli.{command_group}.

Description: {description}

Instructions:
1. Write your Python command logic below
2. Use Click decorators for command definition
3. Save and close the editor to create the command
4. The command will be automatically converted to JSON format

Example Click command structure:
@click.command()
@click.argument('name', default='World')
def my_command(name):
    \"\"\"My custom command.\"\"\"
    click.echo(f"Hello, {{name}}!")
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

# Write your command logic here:
# Replace this template with your actual command implementation

{template.split('"""')[2].split('"""')[0] if '"""' in template else ''}

# Your command implementation goes here:
# Example:
# @click.command()
# @click.argument('name', default='World')
# def {command_name}_command(name):
#     \"\"\"{description}\"\"\"
#     logger.info(f"Executing {command_name} command with name: {{name}}")
#     click.echo(f"Hello, {{name}}! This is the {command_name} command.")
'''

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_file.write(enhanced_template)
        temp_file_path = temp_file.name

    try:
        # Check if we're in an interactive environment
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            click.echo(
                "❌ Editor requires an interactive terminal. Use --template flag for non-interactive mode."
            )
            return None

        # Open editor
        click.echo(f"📝 Opening {editor} to edit command logic...")
        click.echo("💡 Write your Python command logic and save the file to continue.")
        click.echo("💡 Press Ctrl+C to cancel command creation.")

        # Run the editor
        result = subprocess.run([editor, temp_file_path], check=False)

        if result.returncode != 0:
            click.echo("❌ Editor exited with error. Command creation cancelled.")
            return None

        # Read the edited content
        with open(temp_file_path) as f:
            edited_code = f.read()

        # Check if the file was actually edited (not just the template)
        if edited_code.strip() == enhanced_template.strip():
            click.echo("⚠️  No changes detected. Command creation cancelled.")
            return None

        # Extract the actual command code (remove the instructions)
        lines = edited_code.split("\n")
        code_lines = []
        in_code_section = False

        for line in lines:
            if line.strip().startswith("# Your command implementation goes here:"):
                in_code_section = True
                continue
            if in_code_section:
                code_lines.append(line)

        if not code_lines or not any(line.strip() for line in code_lines):
            # Fallback: use the entire file content
            code_lines = lines

        final_code = "\n".join(code_lines).strip()

        if not final_code:
            click.echo("❌ No command code found. Command creation cancelled.")
            return None

        click.echo("✅ Command code captured successfully!")
        return final_code

    except KeyboardInterrupt:
        click.echo("\n❌ Command creation cancelled by user.")
        return None
    except Exception as e:
        click.echo(f"❌ Error opening editor: {e}")
        return None
    finally:
        # Clean up temporary file
        try:  # noqa: SIM105
            os.unlink(temp_file_path)
        except OSError:
            pass


# NOTE: extract-workflow-commands has been moved to mcli.app.commands_cmd for better organization


@click.group("plugin")
def plugin():
    """
    Manage plugins for mcli.

    Use one of the subcommands: add, remove, update.
    """
    logger.info("Plugin management commands loaded")


@plugin.command("add")
@click.argument("plugin_name")
@click.argument("repo_url", required=False)
def plugin_add(plugin_name, repo_url=None):
    """Add a new plugin."""
    # First, check for config path in environment variable
    logger.info(f"Adding plugin: {plugin_name} with repo URL: {repo_url}")
    config_env = os.environ.get("MCLI_CONFIG")
    config_path = None

    if config_env and Path(config_env).expanduser().exists():
        config_path = Path(config_env).expanduser()
    else:
        # Default to $HOME/.config/mcli/config.toml
        home_config = Path.home() / ".config" / "mcli" / "config.toml"
        if home_config.exists():
            config_path = home_config
        else:
            # Fallback to top-level config.toml
            top_level_config = Path(__file__).parent.parent.parent / "config.toml"
            if top_level_config.exists():
                config_path = top_level_config

    if not config_path or not config_path.exists():
        click.echo(ErrorMessages.CONFIG_NOT_FOUND, err=True)
        return 1

    with open(config_path, "rb") as f:
        config = tomli.load(f)

    # Example: plugins are listed under [plugins]
    plugins = config.get("plugins", {})
    if plugin_name in plugins:
        click.echo(f"Plugin '{plugin_name}' already exists in config.toml.")
        return 1

    # Determine plugin install path
    plugin_path = None
    # 1. Check config file for plugin location
    plugin_location = config.get("plugin_location")
    if plugin_location:
        plugin_path = Path(plugin_location).expanduser()
    else:
        # 2. Check env variable
        env_plugin_path = os.environ.get("MCLI_PLUGIN_PATH")
        if env_plugin_path:
            plugin_path = Path(env_plugin_path).expanduser()
        else:
            # 3. Default location
            plugin_path = Path.home() / ".config" / "mcli" / "plugins"

    plugin_path.mkdir(parents=True, exist_ok=True)

    # Download the repo if a URL is provided
    if repo_url:
        import subprocess

        dest = plugin_path / plugin_name
        if dest.exists():
            click.echo(f"Plugin directory already exists at {dest}. Aborting download.", err=True)
            return 1
        try:
            click.echo(f"Cloning {repo_url} into {dest} ...")
            subprocess.run(["git", "clone", repo_url, str(dest)], check=True)
            click.echo(f"Plugin '{plugin_name}' cloned to {dest}")
        except Exception as e:
            click.echo(f"Failed to clone repository: {e}", err=True)
            return 1
    else:
        click.echo("No repo URL provided, plugin will not be downloaded.")

    # TODO: Optionally update config.toml to register the new plugin

    return 0


@plugin.command("remove")
@click.argument("plugin_name")
def plugin_remove(plugin_name):
    """Remove an existing plugin."""
    # Determine plugin install path as in plugin_add
    logger.info(f"Removing plugin: {plugin_name}")
    config_env = os.environ.get("MCLI_CONFIG")
    config_path = None

    if config_env and Path(config_env).expanduser().exists():
        config_path = Path(config_env).expanduser()
    else:
        home_config = Path.home() / ".config" / "mcli" / "config.toml"
        if home_config.exists():
            config_path = home_config
        else:
            top_level_config = Path(__file__).parent.parent.parent / "config.toml"
            if top_level_config.exists():
                config_path = top_level_config

    if not config_path or not config_path.exists():
        click.echo(ErrorMessages.CONFIG_NOT_FOUND, err=True)
        return 1

    with open(config_path, "rb") as f:
        config = tomli.load(f)

    plugin_location = config.get("plugin_location")
    if plugin_location:
        plugin_path = Path(plugin_location).expanduser()
    else:
        env_plugin_path = os.environ.get("MCLI_PLUGIN_PATH")
        if env_plugin_path:
            plugin_path = Path(env_plugin_path).expanduser()
        else:
            plugin_path = Path.home() / ".config" / "mcli" / "plugins"

    dest = plugin_path / plugin_name
    if not dest.exists():
        click.echo(f"Plugin directory does not exist at {dest}. Nothing to remove.", err=True)
        return 1

    import shutil

    try:
        shutil.rmtree(dest)
        click.echo(f"Plugin '{plugin_name}' removed from {dest}")
    except Exception as e:
        click.echo(f"Failed to remove plugin: {e}", err=True)
        return 1

    # TODO: Optionally update config.toml to unregister the plugin

    return 0


@plugin.command("update")
@click.argument("plugin_name")
def plugin_update(plugin_name):
    """Update an existing plugin (git pull on default branch)."""
    """Update an existing plugin by pulling the latest changes from its repository."""
    # Determine plugin install path as in plugin_add
    config_env = os.environ.get("MCLI_CONFIG")
    config_path = None

    # Determine plugin install path as in plugin_add
    config_env = os.environ.get("MCLI_CONFIG")
    config_path = None

    if config_env and Path(config_env).expanduser().exists():
        config_path = Path(config_env).expanduser()
    else:
        home_config = Path.home() / ".config" / "mcli" / "config.toml"
        if home_config.exists():
            config_path = home_config
        else:
            top_level_config = Path(__file__).parent.parent.parent / "config.toml"
            if top_level_config.exists():
                config_path = top_level_config

    if not config_path or not config_path.exists():
        click.echo(ErrorMessages.CONFIG_NOT_FOUND, err=True)
        return 1

    with open(config_path, "rb") as f:
        config = tomli.load(f)

    plugin_location = config.get("plugin_location")
    if plugin_location:
        plugin_path = Path(plugin_location).expanduser()
    else:
        env_plugin_path = os.environ.get("MCLI_PLUGIN_PATH")
        if env_plugin_path:
            plugin_path = Path(env_plugin_path).expanduser()
        else:
            plugin_path = Path.home() / ".config" / "mcli" / "plugins"

    dest = plugin_path / plugin_name
    if not dest.exists():
        click.echo(f"Plugin directory does not exist at {dest}. Cannot update.", err=True)
        return 1

    import subprocess

    try:
        click.echo(f"Updating plugin '{plugin_name}' in {dest} ...")
        subprocess.run(["git", "-C", str(dest), "pull"], check=True)
        click.echo(f"Plugin '{plugin_name}' updated (git pull).")
    except Exception as e:
        click.echo(f"Failed to update plugin: {e}", err=True)
        return 1

    return 0


@self_app.command("version")
@click.option("--verbose", "-v", is_flag=True, help="Show additional system information")
def version_cmd(verbose: bool):
    """Show mcli version and system information."""
    from mcli.lib.ui.styling import info

    message = get_version_info(verbose)
    logger.info(message)
    info(message)


@self_app.command("hello")
@click.argument("name", default="World")
def hello(name: str):
    """A simple hello command for testing."""
    message = f"Hello, {name}! This is the MCLI hello command."
    logger.info(message)
    console.print(f"[green]{message}[/green]")


@self_app.command("logs")
def logs():
    """
    [DEPRECATED] Display runtime logs - Use 'mcli logs' instead.

    This command has been moved to 'mcli logs' with enhanced features.
    """
    console.print("\n[yellow]⚠️  DEPRECATED:[/yellow] This command has been moved.")
    console.print("\n[cyan]New usage:[/cyan]")
    console.print("  mcli logs [bold]stream[/bold]    - Stream logs in real-time")
    console.print("  mcli logs [bold]list[/bold]      - List available log files")
    console.print("  mcli logs [bold]tail[/bold]      - Tail recent log entries")
    console.print("  mcli logs [bold]grep[/bold]      - Search in log files")
    console.print("  mcli logs [bold]location[/bold]  - Show logs directory")
    console.print("  mcli logs [bold]clear[/bold]     - Clear old log files")
    console.print("\n[dim]Run 'mcli logs --help' for more information[/dim]\n")


@self_app.command("performance")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed performance information")
@click.option("--benchmark", "-b", is_flag=True, help="Run performance benchmarks")
def performance(detailed: bool, benchmark: bool):
    """🚀 Show performance optimization status and benchmarks."""
    try:
        from mcli.lib.performance.optimizer import get_global_optimizer
        from mcli.lib.performance.rust_bridge import print_performance_summary

        # Always show the performance summary
        print_performance_summary()

        if detailed:
            console.print("\n📊 Detailed Performance Information:")
            console.print("─" * 60)

            optimizer = get_global_optimizer()
            summary = optimizer.get_optimization_summary()

            table = Table(
                title="Detailed Optimization Results", show_header=True, header_style="bold magenta"
            )
            table.add_column("Optimization", style="cyan", width=20)
            table.add_column("Status", justify="center", width=10)
            table.add_column("Details", style="white", width=40)

            for name, details in summary["details"].items():
                status = "✅" if details.get("success") else "❌"
                detail_text = details.get("performance_gain", "N/A")
                if details.get("optimizations"):
                    opts = details["optimizations"]
                    detail_text += f"\n{len(opts)} optimizations applied"

                table.add_row(name.replace("_", " ").title(), status, detail_text)

            console.print(table)

            console.print(
                f"\n🎯 Estimated Performance Gain: {summary['estimated_performance_gain']}"
            )

        if benchmark:
            console.print("\n🏁 Running Performance Benchmarks...")
            console.print("─" * 60)

            try:
                from mcli.lib.ui.visual_effects import MCLIProgressBar

                progress = MCLIProgressBar.create_fancy_progress()
                with progress:
                    # Benchmark task
                    task = progress.add_task("🔥 Running TF-IDF benchmark...", total=100)

                    optimizer = get_global_optimizer()

                    # Update progress
                    for _i in range(20):
                        progress.update(task, advance=5)
                        time.sleep(0.05)

                    # Run actual benchmark
                    benchmark_results = optimizer.benchmark_performance("medium")

                    progress.update(task, advance=100)

                # Display results
                if benchmark_results:
                    console.print("\n📈 Benchmark Results:")

                    tfidf_results = benchmark_results.get("tfidf_benchmark", {})
                    if tfidf_results.get("rust") and tfidf_results.get("python"):
                        speedup = tfidf_results["python"] / tfidf_results["rust"]
                        console.print(f"   🦀 Rust TF-IDF: {tfidf_results['rust']:.3f}s")
                        console.print(f"   🐍 Python TF-IDF: {tfidf_results['python']:.3f}s")
                        console.print(f"   ⚡ Speedup: {speedup:.1f}x faster with Rust!")

                    system_info = benchmark_results.get("system_info", {})
                    if system_info:
                        console.print("\n💻 System Info:")
                        console.print(f"   Platform: {system_info.get('platform', 'Unknown')}")
                        console.print(f"   CPUs: {system_info.get('cpu_count', 'Unknown')}")
                        console.print(
                            f"   Memory: {system_info.get('memory_total', 0) // (1024**3):.1f}GB"
                        )

            except ImportError:
                click.echo("📊 Benchmark functionality requires additional dependencies")
                click.echo("💡 Install with: pip install rich")

    except ImportError as e:
        click.echo(f"❌ Performance monitoring not available: {e}")
        click.echo("💡 Try installing dependencies: pip install rich psutil")
    except Exception as e:
        click.echo(f"❌ Error showing performance status: {e}")


@self_app.command()
@click.option("--refresh", "-r", default=2.0, help="Refresh interval in seconds")
@click.option("--once", is_flag=True, help="Show dashboard once and exit")
def dashboard(refresh: float, once: bool):
    """📊 Launch live system dashboard."""
    try:
        from mcli.lib.ui.visual_effects import LiveDashboard

        dashboard = LiveDashboard()

        if once:
            # Show dashboard once
            console.clear()
            layout = dashboard.create_full_dashboard()
            console.print(layout)
        else:
            # Start live updating dashboard
            dashboard.start_live_dashboard(refresh_interval=refresh)

    except ImportError as e:
        console.print("[red]Dashboard module not available[/red]")
        console.print(f"Error: {e}")
    except Exception as e:
        console.print(f"[red]Error launching dashboard: {e}[/red]")


def check_ci_status(version: str) -> tuple[bool, Optional[str]]:
    """
    Check GitHub Actions CI status for the main branch.
    Returns (passing, url) tuple.
    """
    try:
        import requests

        response = requests.get(
            "https://api.github.com/repos/gwicho38/mcli/actions/runs",
            params={"per_page": 5},
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "mcli-cli"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            runs = data.get("workflow_runs", [])

            # Find the most recent completed run for main branch
            main_runs = [
                run
                for run in runs
                if run.get("head_branch") == "main" and run.get("status") == "completed"
            ]

            if main_runs:
                latest_run = main_runs[0]
                passing = latest_run.get("conclusion") == "success"
                url = latest_run.get("html_url")
                return (passing, url)

        # If we can't check CI, don't block the update
        return (True, None)
    except Exception:
        # On error, don't block the update
        return (True, None)


@self_app.command()
@click.option("--check", is_flag=True, help="Only check for updates, don't install")
@click.option("--pre", is_flag=True, help="Include pre-release versions")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--skip-ci-check", is_flag=True, help="Skip CI status check and install anyway")
def update(check: bool, pre: bool, yes: bool, skip_ci_check: bool):
    """🔄 Check for and install mcli updates from PyPI."""
    import subprocess
    import sys
    from importlib.metadata import version as get_version

    try:
        import requests
    except ImportError:
        console.print("[red]❌ Error: 'requests' module not found[/red]")
        console.print("[yellow]Install it with: pip install requests[/yellow]")
        return

    try:
        # Get current version
        try:
            current_version = get_version("mcli-framework")
        except Exception:
            console.print("[yellow]⚠️  Could not determine current version[/yellow]")
            current_version = "unknown"

        console.print(f"[cyan]Current version:[/cyan] {current_version}")
        console.print("[cyan]Checking PyPI for updates...[/cyan]")

        # Check PyPI for latest version
        try:
            response = requests.get("https://pypi.org/pypi/mcli-framework/json", timeout=10)
            response.raise_for_status()
            pypi_data = response.json()
        except requests.RequestException as e:
            console.print(f"[red]❌ Error fetching version info from PyPI: {e}[/red]")
            return

        # Get latest version
        if pre:
            # Include pre-releases
            all_versions = list(pypi_data["releases"].keys())
            latest_version = max(
                all_versions,
                key=lambda v: [int(x) for x in v.split(".")] if v[0].isdigit() else [0],
            )
        else:
            # Only stable releases
            latest_version = pypi_data["info"]["version"]

        console.print(f"[cyan]Latest version:[/cyan] {latest_version}")

        # Compare versions
        if current_version == latest_version:
            console.print("[green]✅ You're already on the latest version![/green]")
            return

        # Parse versions for comparison
        def parse_version(v):
            try:
                return tuple(int(x) for x in v.split(".") if x.isdigit())
            except Exception:
                return (0, 0, 0)

        current_parsed = parse_version(current_version)
        latest_parsed = parse_version(latest_version)

        if current_parsed >= latest_parsed:
            console.print(
                f"[green]✅ Your version ({current_version}) is up to date or newer[/green]"
            )
            return

        console.print(f"[yellow]⬆️  Update available: {current_version} → {latest_version}[/yellow]")

        # Show release notes if available
        if "urls" in pypi_data["info"] and pypi_data["info"].get("project_urls"):
            project_urls = pypi_data["info"]["project_urls"]
            if "Changelog" in project_urls:
                console.print(f"[dim]📝 Changelog: {project_urls['Changelog']}[/dim]")

        if check:
            console.print("[cyan]ℹ️  Run 'mcli self update' to install the update[/cyan]")
            return

        # Ask for confirmation unless --yes flag is used
        if not yes:
            from rich.prompt import Confirm

            if not Confirm.ask(f"[yellow]Install mcli {latest_version}?[/yellow]"):
                console.print("[yellow]Update cancelled[/yellow]")
                return

        # Check CI status before installing (unless skipped)
        if not skip_ci_check:
            console.print("[cyan]🔍 Checking CI status...[/cyan]")
            ci_passing, ci_url = check_ci_status(latest_version)

            if not ci_passing:
                console.print("[red]✗ CI build is failing for the latest version[/red]")
                if ci_url:
                    console.print(f"[yellow]  View CI status: {ci_url}[/yellow]")
                console.print(
                    "[yellow]⚠️  Update blocked to prevent installing a broken version[/yellow]"
                )
                console.print(
                    "[dim]  Use --skip-ci-check to install anyway (not recommended)[/dim]"
                )
                return
            else:
                console.print("[green]✓ CI build is passing[/green]")

        # Install update
        console.print(f"[cyan]📦 Installing mcli {latest_version}...[/cyan]")

        # Detect if we're running from a uv tool installation
        # uv tool installations are typically in ~/.local/share/uv/tools/ or similar
        executable_path = str(sys.executable).replace("\\", "/")  # Normalize path separators

        is_uv_tool = (
            "/uv/tools/" in executable_path
            or "/.local/share/uv/tools/" in executable_path
            or "\\AppData\\Local\\uv\\tools\\" in str(sys.executable)
        )

        if is_uv_tool:
            # Use uv tool install for uv tool environments (uv doesn't include pip)
            console.print("[dim]Detected uv tool installation, using 'uv tool install'[/dim]")
            cmd = ["uv", "tool", "install", "--force", "mcli-framework"]
            if pre:
                # For pre-releases, we'd need to specify the version explicitly
                # For now, --pre is not supported with uv tool install in this context
                console.print(
                    "[yellow]⚠️  Pre-release flag not supported with uv tool install[/yellow]"
                )
        else:
            # Use pip to upgrade for regular installations (requires pip in environment)
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "mcli-framework"]
            if pre:
                cmd.append("--pre")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print(f"[green]✅ Successfully updated to mcli {latest_version}![/green]")
            if is_uv_tool:
                console.print(
                    "[yellow]ℹ️  Run 'hash -r' to refresh your shell's command cache[/yellow]"
                )
            else:
                console.print(
                    "[yellow]ℹ️  Restart your terminal or run 'hash -r' to use the new version[/yellow]"
                )
        else:
            console.print("[red]❌ Update failed:[/red]")
            console.print(result.stderr)

    except Exception as e:
        console.print(f"[red]❌ Error during update: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")


# Register the plugin group with self_app
self_app.add_command(plugin)

# Import and register new commands that have been moved to self
try:
    from mcli.self.completion_cmd import completion

    self_app.add_command(completion, name="completion")
    logger.debug("Added completion command to self group")
except ImportError as e:
    logger.debug(f"Could not load completion command: {e}")

try:
    from mcli.self.logs_cmd import logs_group

    self_app.add_command(logs_group, name="logs")
    logger.debug("Added logs command to self group")
except ImportError as e:
    logger.debug(f"Could not load logs command: {e}")

try:
    from mcli.self.redis_cmd import redis_group

    self_app.add_command(redis_group, name="redis")
    logger.debug("Added redis command to self group")
except ImportError as e:
    logger.debug(f"Could not load redis command: {e}")

try:
    from mcli.self.zsh_cmd import zsh_group

    self_app.add_command(zsh_group, name="zsh")
    logger.debug("Added zsh command to self group")
except ImportError as e:
    logger.debug(f"Could not load zsh command: {e}")

try:
    from mcli.self.visual_cmd import visual

    self_app.add_command(visual, name="visual")
    logger.debug("Added visual command to self group")
except ImportError as e:
    logger.debug(f"Could not load visual command: {e}")

try:
    from mcli.self.migrate_cmd import migrate_command

    self_app.add_command(migrate_command, name="migrate")
    logger.debug("Added migrate command to self group")
except ImportError as e:
    logger.debug(f"Could not load migrate command: {e}")

try:
    from mcli.self.health_cmd import health

    self_app.add_command(health, name="health")
    logger.debug("Added health command to self group")
except ImportError as e:
    logger.debug(f"Could not load health command: {e}")

# NOTE: store command has been moved to mcli.app.commands_cmd for better organization

# This part is important to make the command available to the CLI
if __name__ == "__main__":
    self_app()
