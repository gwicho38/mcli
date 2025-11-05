"""
Top-level lock management commands for MCLI.
Manages workflow lockfile and verification.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import click
from rich.table import Table

from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)

# Command state lockfile configuration
LOCKFILE_PATH = Path.home() / ".local" / "mcli" / "command_lock.json"


def load_lockfile():
    """Load the command state lockfile."""
    if LOCKFILE_PATH.exists():
        with open(LOCKFILE_PATH, "r") as f:
            data = json.load(f)
            # Handle both old format (array) and new format (object with "states" key)
            if isinstance(data, dict) and "states" in data:
                return data["states"]
            return data if isinstance(data, list) else []
    return []


def save_lockfile(states):
    """Save states to the command state lockfile."""
    LOCKFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCKFILE_PATH, "w") as f:
        json.dump(states, f, indent=2, default=str)


def append_lockfile(new_state):
    """Append a new state to the lockfile."""
    states = load_lockfile()
    states.append(new_state)
    save_lockfile(states)


def find_state_by_hash(hash_value):
    """Find a state by its hash value (supports partial hash matching)."""
    states = load_lockfile()
    matches = []
    for state in states:
        # Support both full hash and partial hash (prefix) matching
        if state["hash"] == hash_value or state["hash"].startswith(hash_value):
            matches.append(state)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Ambiguous - multiple matches
        return None
    return None


def restore_command_state(hash_value):
    """Restore to a previous command state."""
    state = find_state_by_hash(hash_value)
    if not state:
        return False
    # Here you would implement logic to restore the command registry to this state
    # For now, just print the commands
    print(json.dumps(state["commands"], indent=2))
    return True


def get_current_command_state():
    """Collect all command metadata (names, groups, etc.)."""
    # Import here to avoid circular imports
    import importlib
    import inspect
    import os
    from pathlib import Path

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
                module_name = str(relative_path.with_suffix("")).replace(os.sep, ".")

                try:
                    # Try to import the module
                    module = importlib.import_module(module_name)

                    # Suppress Streamlit logging noise during command collection
                    if "streamlit" in module_name or "dashboard" in module_name:
                        # Suppress streamlit logger to avoid noise
                        import logging

                        streamlit_logger = logging.getLogger("streamlit")
                        original_level = streamlit_logger.level
                        streamlit_logger.setLevel(logging.CRITICAL)

                        try:
                            # Import and extract commands
                            pass
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


def hash_command_state(commands):
    """Hash the command state for fast comparison."""
    # Sort for deterministic hash
    commands_sorted = sorted(commands, key=lambda c: (c.get("group") or "", c["name"]))
    state_json = json.dumps(commands_sorted, sort_keys=True)
    return hashlib.sha256(state_json.encode("utf-8")).hexdigest()


@click.group(name="lock")
def lock():
    """Manage workflow lockfile and verification."""


@lock.command("list")
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


@lock.command("restore")
@click.argument("hash_value")
def restore_state(hash_value):
    """Restore to a previous command state by hash."""
    if restore_command_state(hash_value):
        click.echo(f"Restored to state {hash_value[:8]}")
    else:
        click.echo(f"State {hash_value[:8]} not found.", err=True)


@lock.command("write")
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


@lock.command("verify")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Verify global commands instead of local"
)
@click.option("--code", "-c", is_flag=True, help="Also validate that workflow code is executable")
def verify_commands(is_global, code):
    """
    Verify that custom commands match the lockfile and optionally validate code.

    By default verifies local commands (if in git repo), use --global/-g for global commands.
    Use --code/-c to also validate that workflow code is valid and executable.
    """
    manager = get_command_manager(global_mode=is_global)

    # First, ensure lockfile is up to date
    manager.update_lockfile()

    verification = manager.verify_lockfile()

    has_issues = False

    if not verification["valid"]:
        has_issues = True
        console.print("[yellow]Commands are out of sync with the lockfile:[/yellow]\n")

        if verification["missing"]:
            console.print("Missing commands (in lockfile but not found):")
            for name in verification["missing"]:
                console.print(f"  - {name}")

        if verification["extra"]:
            console.print("\nExtra commands (not in lockfile):")
            for name in verification["extra"]:
                console.print(f"  - {name}")

        if verification["modified"]:
            console.print("\nModified commands:")
            for name in verification["modified"]:
                console.print(f"  - {name}")

        console.print("\n[dim]Run 'mcli lock update' to sync the lockfile[/dim]\n")

    # Validate workflow code if requested
    if code:
        console.print("[cyan]Validating workflow code...[/cyan]\n")

        commands = manager.load_all_commands()
        invalid_workflows = []

        for cmd_data in commands:
            if cmd_data.get("group") != "workflow":
                continue

            cmd_name = cmd_data.get("name")
            temp_group = click.Group()
            language = cmd_data.get("language", "python")

            try:
                if language == "shell":
                    success = manager.register_shell_command_with_click(cmd_data, temp_group)
                else:
                    success = manager.register_command_with_click(cmd_data, temp_group)

                if not success or not temp_group.commands.get(cmd_name):
                    invalid_workflows.append(
                        {"name": cmd_name, "reason": "Code does not define a valid Click command"}
                    )
            except SyntaxError as e:
                invalid_workflows.append({"name": cmd_name, "reason": f"Syntax error: {e}"})
            except Exception as e:
                invalid_workflows.append({"name": cmd_name, "reason": f"Failed to load: {e}"})

        if invalid_workflows:
            has_issues = True
            console.print("[red]Invalid workflows found:[/red]\n")

            for item in invalid_workflows:
                console.print(f"  [red]✗[/red] {item['name']}")
                console.print(f"    [dim]{item['reason']}[/dim]")

            console.print("\n[yellow]Fix with:[/yellow] mcli workflow edit <workflow-name>")
            console.print(
                "[dim]Tip: Workflow code must define a Click command decorated with @click.command()[/dim]\n"
            )
        else:
            console.print("[green]✓ All workflow code is valid[/green]\n")

    if not has_issues:
        console.print("[green]✓ All custom commands are verified[/green]")
        return 0

    return 1


@lock.command("update")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Update global lockfile instead of local"
)
def update_lockfile(is_global):
    """
    Update the commands lockfile with current state.

    By default updates local lockfile (if in git repo), use --global/-g for global lockfile.
    """
    manager = get_command_manager(global_mode=is_global)

    if manager.update_lockfile():
        console.print(f"[green]Updated lockfile: {manager.lockfile_path}[/green]")
        return 0
    else:
        console.print("[red]Failed to update lockfile.[/red]")
        return 1
