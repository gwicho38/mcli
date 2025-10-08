"""
Self-management commands for mcli.
Provides utilities for maintaining and extending the CLI itself.
"""

import hashlib
import importlib
import inspect
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import tomli
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

try:
    import warnings

    # Suppress the warning about python-Levenshtein
    warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher")
    from fuzzywuzzy import process
except ImportError:
    process = None

from mcli.lib.logger.logger import get_logger
from mcli.lib.custom_commands import get_command_manager

logger = get_logger()


# Create a Click command group instead of Typer
@click.group(name="self", help="Manage and extend the mcli application")
def self_app():
    """
    Self-management commands for mcli.
    """
    pass


console = Console()

LOCKFILE_PATH = Path.home() / ".local" / "mcli" / "command_lock.json"

# Utility functions for command state lockfile


def get_current_command_state():
    """Collect all command metadata (names, groups, etc.)"""
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
        with open(LOCKFILE_PATH, "r") as f:
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


# Create a Click group for all command management
@self_app.group("commands")
def commands_group():
    """Manage CLI commands and command state."""
    pass


# Move the command-state group under commands_group
@commands_group.group("state")
def command_state():
    """Manage command state lockfile and history."""
    pass


@command_state.command("list")
def list_states():
    """List all saved command states (hash, timestamp, #commands)."""
    states = load_lockfile()
    if not states:
        click.echo("No command states found.")
        return
    table = Table(title="Command States")
    table.add_column("Hash", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("# Commands", style="yellow")
    for state in states:
        table.add_row(state["hash"][:8], state["timestamp"], str(len(state["commands"])))
    console.print(table)


@command_state.command("restore")
@click.argument("hash_value")
def restore_state(hash_value):
    """Restore to a previous command state by hash."""
    if restore_command_state(hash_value):
        click.echo(f"Restored to state {hash_value[:8]}")
    else:
        click.echo(f"State {hash_value[:8]} not found.", err=True)


@command_state.command("write")
@click.argument("json_file", required=False, type=click.Path(exists=False))
def write_state(json_file):
    """Write a new command state to the lockfile from a JSON file or the current app state."""
    import traceback

    print("[DEBUG] write_state called")
    print(f"[DEBUG] LOCKFILE_PATH: {LOCKFILE_PATH}")
    try:
        if json_file:
            print(f"[DEBUG] Loading command state from file: {json_file}")
            with open(json_file, "r") as f:
                commands = json.load(f)
            click.echo(f"Loaded command state from {json_file}.")
        else:
            print("[DEBUG] Snapshotting current command state.")
            commands = get_current_command_state()
        state_hash = hash_command_state(commands)
        new_state = {
            "hash": state_hash,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "commands": commands,
        }
        append_lockfile(new_state)
        print(f"[DEBUG] Wrote new command state {state_hash[:8]} to lockfile at {LOCKFILE_PATH}")
        click.echo(f"Wrote new command state {state_hash[:8]} to lockfile.")
    except Exception as e:
        print(f"[ERROR] Exception in write_state: {e}")
        print(traceback.format_exc())
        click.echo(f"[ERROR] Failed to write command state: {e}", err=True)


# On CLI startup, check and update lockfile if needed


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


@self_app.command("search")
@click.argument("query", required=False)
@click.option("--full", "-f", is_flag=True, help="Show full command paths and descriptions")
def search(query, full):
    """
    Search for available commands using fuzzy matching.

    Similar to telescope in neovim, this allows quick fuzzy searching
    through all available commands in mcli.

    If no query is provided, lists all commands.
    """
    # Collect all commands from the application
    commands = collect_commands()

    # Display the commands in a table
    table = Table(title="mcli Commands")
    table.add_column("Command", style="green")
    table.add_column("Group", style="blue")
    if full:
        table.add_column("Path", style="dim")
        table.add_column("Description", style="yellow")

    if query:
        filtered_commands = []

        # Try to use fuzzywuzzy for better matching if available
        if process:
            # Extract command names for matching
            command_names = [
                f"{cmd['group']}.{cmd['name']}" if cmd["group"] else cmd["name"] for cmd in commands
            ]
            matches = process.extract(query, command_names, limit=10)

            # Filter to matched commands
            match_indices = [command_names.index(match[0]) for match in matches if match[1] > 50]
            filtered_commands = [commands[i] for i in match_indices]
        else:
            # Fallback to simple substring matching
            filtered_commands = [
                cmd
                for cmd in commands
                if query.lower() in cmd["name"].lower()
                or (cmd["group"] and query.lower() in cmd["group"].lower())
            ]

        commands = filtered_commands

    # Sort commands by group then name
    commands.sort(key=lambda c: (c["group"] if c["group"] else "", c["name"]))

    # Add rows to the table
    for cmd in commands:
        if full:
            table.add_row(
                cmd["name"],
                cmd["group"] if cmd["group"] else "-",
                cmd["path"],
                cmd["help"] if cmd["help"] else "",
            )
        else:
            table.add_row(cmd["name"], cmd["group"] if cmd["group"] else "-")

    console.print(table)

    if not commands:
        logger.info("No commands found matching the search query")
        click.echo("No commands found matching the search query")

    return 0


def collect_commands() -> List[Dict[str, Any]]:
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
                    # Try to import the module
                    module = importlib.import_module(module_name)

                    # Extract command and group objects
                    for name, obj in inspect.getmembers(module):
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


@self_app.command("add-command")
@click.argument("command_name", required=True)
@click.option("--group", "-g", help="Command group (defaults to 'workflow')", default="workflow")
@click.option(
    "--description", "-d", help="Description for the command", default="Custom command"
)
def add_command(command_name, group, description):
    """
    Generate a new portable custom command saved to ~/.mcli/commands/.

    Commands are automatically nested under the 'workflow' group by default,
    making them portable and persistent across updates.

    Example:
        mcli self add-command my_command
        mcli self add-command analytics --group data
    """
    command_name = command_name.lower().replace("-", "_")

    # Validate command name
    if not re.match(r"^[a-z][a-z0-9_]*$", command_name):
        logger.error(
            f"Invalid command name: {command_name}. Use lowercase letters, numbers, and underscores (starting with a letter)."
        )
        click.echo(
            f"Invalid command name: {command_name}. Use lowercase letters, numbers, and underscores (starting with a letter).",
            err=True,
        )
        return 1

    # Validate group name if provided
    if group:
        command_group = group.lower().replace("-", "_")
        if not re.match(r"^[a-z][a-z0-9_]*$", command_group):
            logger.error(
                f"Invalid group name: {command_group}. Use lowercase letters, numbers, and underscores (starting with a letter)."
            )
            click.echo(
                f"Invalid group name: {command_group}. Use lowercase letters, numbers, and underscores (starting with a letter).",
                err=True,
            )
            return 1
    else:
        command_group = "workflow"  # Default to workflow group

    # Get the command manager
    manager = get_command_manager()

    # Check if command already exists
    command_file = manager.commands_dir / f"{command_name}.json"
    if command_file.exists():
        logger.warning(f"Custom command already exists: {command_name}")
        should_override = Prompt.ask(
            "Command already exists. Override?", choices=["y", "n"], default="n"
        )
        if should_override.lower() != "y":
            logger.info("Command creation aborted.")
            click.echo("Command creation aborted.")
            return 1

    # Generate command code
    code = get_command_template(command_name, command_group)

    # Save the command
    saved_path = manager.save_command(
        name=command_name,
        code=code,
        description=description,
        group=command_group,
    )

    logger.info(f"Created portable custom command: {command_name}")
    click.echo(f"✅ Created portable custom command: {command_name}")
    click.echo(f"📁 Saved to: {saved_path}")
    click.echo(f"🔄 Command will be automatically loaded on next mcli startup")
    click.echo(
        f"💡 You can share this command by copying {saved_path} to another machine's ~/.mcli/commands/ directory"
    )

    return 0


@self_app.command("list-commands")
def list_commands():
    """
    List all custom commands stored in ~/.mcli/commands/.
    """
    manager = get_command_manager()
    commands = manager.load_all_commands()

    if not commands:
        click.echo("No custom commands found.")
        click.echo(
            f"Create one with: mcli self add-command <name>"
        )
        return 0

    table = Table(title="Custom Commands")
    table.add_column("Name", style="green")
    table.add_column("Group", style="blue")
    table.add_column("Description", style="yellow")
    table.add_column("Version", style="cyan")
    table.add_column("Updated", style="dim")

    for cmd in commands:
        table.add_row(
            cmd["name"],
            cmd.get("group", "-"),
            cmd.get("description", ""),
            cmd.get("version", "1.0"),
            cmd.get("updated_at", "")[:10] if cmd.get("updated_at") else "-",
        )

    console.print(table)
    click.echo(f"\n📁 Commands directory: {manager.commands_dir}")
    click.echo(f"🔒 Lockfile: {manager.lockfile_path}")

    return 0


@self_app.command("remove-command")
@click.argument("command_name", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def remove_command(command_name, yes):
    """
    Remove a custom command from ~/.mcli/commands/.
    """
    manager = get_command_manager()
    command_file = manager.commands_dir / f"{command_name}.json"

    if not command_file.exists():
        click.echo(f"❌ Command '{command_name}' not found.", err=True)
        return 1

    if not yes:
        should_delete = Prompt.ask(
            f"Delete command '{command_name}'?", choices=["y", "n"], default="n"
        )
        if should_delete.lower() != "y":
            click.echo("Deletion cancelled.")
            return 0

    if manager.delete_command(command_name):
        click.echo(f"✅ Deleted custom command: {command_name}")
        return 0
    else:
        click.echo(f"❌ Failed to delete command: {command_name}", err=True)
        return 1


@self_app.command("export-commands")
@click.argument("export_file", type=click.Path(), required=False)
def export_commands(export_file):
    """
    Export all custom commands to a JSON file.

    If no file is specified, exports to commands-export.json in current directory.
    """
    manager = get_command_manager()

    if not export_file:
        export_file = "commands-export.json"

    export_path = Path(export_file)

    if manager.export_commands(export_path):
        click.echo(f"✅ Exported custom commands to: {export_path}")
        click.echo(
            f"💡 Import on another machine with: mcli self import-commands {export_path}"
        )
        return 0
    else:
        click.echo("❌ Failed to export commands.", err=True)
        return 1


@self_app.command("import-commands")
@click.argument("import_file", type=click.Path(exists=True), required=True)
@click.option("--overwrite", is_flag=True, help="Overwrite existing commands")
def import_commands(import_file, overwrite):
    """
    Import custom commands from a JSON file.
    """
    manager = get_command_manager()
    import_path = Path(import_file)

    results = manager.import_commands(import_path, overwrite=overwrite)

    success_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - success_count

    if success_count > 0:
        click.echo(f"✅ Imported {success_count} command(s)")

    if failed_count > 0:
        click.echo(
            f"⚠️  Skipped {failed_count} command(s) (already exist, use --overwrite to replace)"
        )
        click.echo("Skipped commands:")
        for name, success in results.items():
            if not success:
                click.echo(f"  - {name}")

    return 0


@self_app.command("verify-commands")
def verify_commands():
    """
    Verify that custom commands match the lockfile.
    """
    manager = get_command_manager()

    # First, ensure lockfile is up to date
    manager.update_lockfile()

    verification = manager.verify_lockfile()

    if verification["valid"]:
        click.echo("✅ All custom commands are in sync with the lockfile.")
        return 0

    click.echo("⚠️  Commands are out of sync with the lockfile:\n")

    if verification["missing"]:
        click.echo(f"Missing commands (in lockfile but not found):")
        for name in verification["missing"]:
            click.echo(f"  - {name}")

    if verification["extra"]:
        click.echo(f"\nExtra commands (not in lockfile):")
        for name in verification["extra"]:
            click.echo(f"  - {name}")

    if verification["modified"]:
        click.echo(f"\nModified commands:")
        for name in verification["modified"]:
            click.echo(f"  - {name}")

    click.echo(f"\n💡 Run 'mcli self update-lockfile' to sync the lockfile")

    return 1


@self_app.command("update-lockfile")
def update_lockfile():
    """
    Update the commands lockfile with current state.
    """
    manager = get_command_manager()

    if manager.update_lockfile():
        click.echo(f"✅ Updated lockfile: {manager.lockfile_path}")
        return 0
    else:
        click.echo("❌ Failed to update lockfile.", err=True)
        return 1


@self_app.command("extract-workflow-commands")
@click.option(
    "--output", "-o", type=click.Path(), help="Output file (default: workflow-commands.json)"
)
def extract_workflow_commands(output):
    """
    Extract workflow commands from Python modules to JSON format.

    This command helps migrate existing workflow commands to portable JSON format.
    """
    import inspect
    from pathlib import Path

    output_file = Path(output) if output else Path("workflow-commands.json")

    workflow_commands = []

    # Try to get workflow from the main app
    try:
        from mcli.app.main import create_app

        app = create_app()

        # Check if workflow group exists
        if "workflow" in app.commands:
            workflow_group = app.commands["workflow"]

            # Force load lazy group if needed
            if hasattr(workflow_group, "_load_group"):
                workflow_group = workflow_group._load_group()

            if hasattr(workflow_group, "commands"):
                for cmd_name, cmd_obj in workflow_group.commands.items():
                    # Extract command information
                    command_info = {
                        "name": cmd_name,
                        "group": "workflow",
                        "description": cmd_obj.help or "Workflow command",
                        "version": "1.0",
                        "metadata": {"source": "workflow", "migrated": True},
                    }

                    # Create a template based on command type
                    # Replace hyphens with underscores for valid Python function names
                    safe_name = cmd_name.replace("-", "_")

                    if isinstance(cmd_obj, click.Group):
                        # For groups, create a template
                        command_info["code"] = f'''"""
{cmd_name} workflow command.
"""
import click

@click.group(name="{cmd_name}")
def app():
    """{cmd_obj.help or 'Workflow command group'}"""
    pass

# Add your subcommands here
'''
                    else:
                        # For regular commands, create a template
                        command_info["code"] = f'''"""
{cmd_name} workflow command.
"""
import click

@click.command(name="{cmd_name}")
def app():
    """{cmd_obj.help or 'Workflow command'}"""
    click.echo("Workflow command: {cmd_name}")
    # Add your implementation here
'''

                    workflow_commands.append(command_info)

        if workflow_commands:
            import json

            with open(output_file, "w") as f:
                json.dump(workflow_commands, f, indent=2)

            click.echo(f"✅ Extracted {len(workflow_commands)} workflow commands")
            click.echo(f"📁 Saved to: {output_file}")
            click.echo(
                f"\n💡 These are templates. Import with: mcli self import-commands {output_file}"
            )
            click.echo(
                "   Then customize the code in ~/.mcli/commands/<command>.json"
            )
            return 0
        else:
            click.echo("⚠️  No workflow commands found to extract")
            return 1

    except Exception as e:
        logger.error(f"Failed to extract workflow commands: {e}")
        click.echo(f"❌ Failed to extract workflow commands: {e}", err=True)
        import traceback

        click.echo(traceback.format_exc(), err=True)
        return 1


@click.group("plugin")
def plugin():
    """
    Manage plugins for mcli.

    Use one of the subcommands: add, remove, update.
    """
    logger.info("Plugin management commands loaded")
    pass


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
        click.echo(
            "Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root.",
            err=True,
        )
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
        click.echo(
            "Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root.",
            err=True,
        )
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
        click.echo(
            "Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root.",
            err=True,
        )
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


@self_app.command("hello")
@click.argument("name", default="World")
def hello(name: str):
    """A simple hello command for testing."""
    message = f"Hello, {name}! This is the MCLI hello command."
    logger.info(message)
    console.print(f"[green]{message}[/green]")


@self_app.command("logs")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["main", "system", "trace", "all"]),
    default="main",
    help="Type of logs to display",
)
@click.option("--lines", "-n", default=50, help="Number of lines to show (default: 50)")
@click.option("--follow", "-f", is_flag=True, help="Follow log output in real-time")
@click.option("--date", "-d", help="Show logs for specific date (YYYYMMDD format)")
@click.option("--grep", "-g", help="Filter logs by pattern")
@click.option(
    "--level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Filter logs by minimum level",
)
def logs(type: str, lines: int, follow: bool, date: str, grep: str, level: str):
    """
    Display runtime logs of the mcli application.

    Shows the most recent log entries from the application's logging system.
    Supports filtering by log type, date, content, and log level.

    Log files are named as mcli_YYYYMMDD.log, mcli_system_YYYYMMDD.log, mcli_trace_YYYYMMDD.log.
    """
    import re
    import subprocess
    from datetime import datetime
    from pathlib import Path

    # Import get_logs_dir to get the correct logs directory
    from mcli.lib.paths import get_logs_dir

    # Get the logs directory (creates it if it doesn't exist)
    logs_dir = get_logs_dir()

    if not logs_dir.exists():
        click.echo("❌ Logs directory not found", err=True)
        click.echo(f"Expected location: {logs_dir}", err=True)
        return

    # Determine which log files to read
    log_files = []

    if type == "all":
        # Get all log files for the specified date or latest
        if date:
            # Look for files like mcli_20250709.log, mcli_system_20250709.log, mcli_trace_20250709.log
            patterns = [f"mcli_{date}.log", f"mcli_system_{date}.log", f"mcli_trace_{date}.log"]
        else:
            # Get the most recent log files
            patterns = ["mcli_*.log"]

        log_files = []
        for pattern in patterns:
            files = list(logs_dir.glob(pattern))
            if files:
                # Sort by modification time (newest first)
                files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                log_files.extend(files)

        # Remove duplicates and take only the most recent files of each type
        seen_types = set()
        filtered_files = []
        for log_file in log_files:
            # Extract log type from filename
            # mcli_20250709 -> main
            # mcli_system_20250709 -> system
            # mcli_trace_20250709 -> trace
            if log_file.name.startswith("mcli_system_"):
                log_type = "system"
            elif log_file.name.startswith("mcli_trace_"):
                log_type = "trace"
            else:
                log_type = "main"

            if log_type not in seen_types:
                seen_types.add(log_type)
                filtered_files.append(log_file)

        log_files = filtered_files
    else:
        # Get specific log type
        if date:
            if type == "main":
                filename = f"mcli_{date}.log"
            else:
                filename = f"mcli_{type}_{date}.log"
        else:
            # Find the most recent file for this type
            if type == "main":
                pattern = "mcli_*.log"
                # Exclude system and trace files
                exclude_patterns = ["mcli_system_*.log", "mcli_trace_*.log"]
            else:
                pattern = f"mcli_{type}_*.log"
                exclude_patterns = []

            files = list(logs_dir.glob(pattern))

            # Filter out excluded patterns
            if exclude_patterns:
                filtered_files = []
                for file in files:
                    excluded = False
                    for exclude_pattern in exclude_patterns:
                        if file.match(exclude_pattern):
                            excluded = True
                            break
                    if not excluded:
                        filtered_files.append(file)
                files = filtered_files

            if files:
                # Sort by modification time and take the most recent
                files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                filename = files[0].name
            else:
                click.echo(f"❌ No {type} log files found", err=True)
                return

        log_file = logs_dir / filename
        if log_file.exists():
            log_files = [log_file]
        else:
            click.echo(f"❌ Log file not found: {filename}", err=True)
            return

    if not log_files:
        click.echo("❌ No log files found", err=True)
        return

    # Display log file information
    click.echo(f"📋 Showing logs from {len(log_files)} file(s):")
    for log_file in log_files:
        size_mb = log_file.stat().st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(log_file.stat().st_mtime)
        click.echo(
            f"   📄 {log_file.name} ({size_mb:.1f}MB, modified {modified.strftime('%Y-%m-%d %H:%M:%S')})"
        )
    click.echo()

    # Process each log file
    for log_file in log_files:
        click.echo(f"🔍 Reading: {log_file.name}")
        click.echo("─" * 80)

        try:
            # Read the file content
            with open(log_file, "r") as f:
                content = f.readlines()

            # Apply filters
            filtered_lines = []
            for line in content:
                # Apply grep filter
                if grep and grep.lower() not in line.lower():
                    continue

                # Apply level filter
                if level:
                    level_pattern = rf"\b{level}\b"
                    if not re.search(level_pattern, line, re.IGNORECASE):
                        # Check if line has a lower level than requested
                        level_order = {
                            "DEBUG": 0,
                            "INFO": 1,
                            "WARNING": 2,
                            "ERROR": 3,
                            "CRITICAL": 4,
                        }
                        requested_level = level_order.get(level.upper(), 0)

                        # Check if line contains any log level
                        found_level = None
                        for log_level in level_order:
                            if log_level in line.upper():
                                found_level = level_order[log_level]
                                break

                        if found_level is None or found_level < requested_level:
                            continue

                filtered_lines.append(line)

            # Show the last N lines
            if lines > 0:
                filtered_lines = filtered_lines[-lines:]

            # Display the lines
            for line in filtered_lines:
                # Colorize log levels
                colored_line = line
                if "ERROR" in line or "CRITICAL" in line:
                    colored_line = click.style(line, fg="red")
                elif "WARNING" in line:
                    colored_line = click.style(line, fg="yellow")
                elif "INFO" in line:
                    colored_line = click.style(line, fg="green")
                elif "DEBUG" in line:
                    colored_line = click.style(line, fg="blue")

                click.echo(colored_line.rstrip())

            if not filtered_lines:
                click.echo("(No matching log entries found)")

        except Exception as e:
            click.echo(f"❌ Error reading log file {log_file.name}: {e}", err=True)

        click.echo()

    if follow:
        click.echo("🔄 Following log output... (Press Ctrl+C to stop)")
        try:
            # Use tail -f for real-time following
            for log_file in log_files:
                click.echo(f"📡 Following: {log_file.name}")
                process = subprocess.Popen(
                    ["tail", "-f", str(log_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                try:
                    if process.stdout:
                        for line in process.stdout:
                            # Apply filters to real-time output
                            if grep and grep.lower() not in line.lower():
                                continue

                            if level:
                                level_pattern = rf"\b{level}\b"
                                if not re.search(level_pattern, line, re.IGNORECASE):
                                    continue

                            # Colorize and display
                            colored_line = line
                            if "ERROR" in line or "CRITICAL" in line:
                                colored_line = click.style(line, fg="red")
                            elif "WARNING" in line:
                                colored_line = click.style(line, fg="yellow")
                            elif "INFO" in line:
                                colored_line = click.style(line, fg="green")
                            elif "DEBUG" in line:
                                colored_line = click.style(line, fg="blue")

                            click.echo(colored_line.rstrip())

                except KeyboardInterrupt:
                    process.terminate()
                    break

        except KeyboardInterrupt:
            click.echo("\n🛑 Stopped following logs")
        except Exception as e:
            click.echo(f"❌ Error following logs: {e}", err=True)


@self_app.command("performance")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed performance information")
@click.option("--benchmark", "-b", is_flag=True, help="Run performance benchmarks")
def performance(detailed: bool, benchmark: bool):
    """🚀 Show performance optimization status and benchmarks"""
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
                    for i in range(20):
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
                        console.print(f"\n💻 System Info:")
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
    """📊 Launch live system dashboard"""
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
    """🔄 Check for and install mcli updates from PyPI"""
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
            except:
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
            console.print(f"[red]❌ Update failed:[/red]")
            console.print(result.stderr)

    except Exception as e:
        console.print(f"[red]❌ Error during update: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")


# Register the plugin group with self_app
self_app.add_command(plugin)

# This part is important to make the command available to the CLI
if __name__ == "__main__":
    self_app()
