"""
Top-level lock management commands for MCLI.
Manages workflow lockfile and verification.

The lockfile (workflows.lock.json) tracks:
- Script file names and languages
- Content hash (SHA256) for change detection
- Version from @version metadata
- Other metadata (description, author, tags, etc.)
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import click
from rich.table import Table

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console

logger = get_logger(__name__)

# Legacy command state lockfile (for historical snapshots)
LEGACY_LOCKFILE_PATH = Path.home() / ".local" / "mcli" / "command_lock.json"


def load_legacy_lockfile():
    """Load the legacy command state lockfile."""
    if LEGACY_LOCKFILE_PATH.exists():
        with open(LEGACY_LOCKFILE_PATH, "r") as f:
            data = json.load(f)
            if isinstance(data, dict) and "states" in data:
                return data["states"]
            return data if isinstance(data, list) else []
    return []


def save_legacy_lockfile(states):
    """Save states to the legacy command state lockfile."""
    LEGACY_LOCKFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEGACY_LOCKFILE_PATH, "w") as f:
        json.dump(states, f, indent=2, default=str)


def append_legacy_lockfile(new_state):
    """Append a new state to the legacy lockfile."""
    states = load_legacy_lockfile()
    states.append(new_state)
    save_legacy_lockfile(states)


def find_state_by_hash(hash_value):
    """Find a state by its hash value (supports partial hash matching)."""
    states = load_legacy_lockfile()
    matches = []
    for state in states:
        if state["hash"] == hash_value or state["hash"].startswith(hash_value):
            matches.append(state)

    if len(matches) == 1:
        return matches[0]
    return None


def hash_command_state(commands):
    """Hash the command state for fast comparison."""
    commands_sorted = sorted(commands, key=lambda c: (c.get("group") or "", c.get("name", "")))
    state_json = json.dumps(commands_sorted, sort_keys=True)
    return hashlib.sha256(state_json.encode("utf-8")).hexdigest()


@click.group(name="lock")
def lock():
    """Manage workflow lockfile and verification.

    The lockfile (workflows.lock.json) tracks script metadata including:
    - Content hash (SHA256) for change detection
    - Version from @version metadata
    - Language, description, author, tags, etc.

    Use 'mcli lock update' to regenerate the lockfile from current scripts.
    Use 'mcli lock verify' to check if scripts match the lockfile.
    """


@lock.command("list")
@click.option("--global", "-g", "is_global", is_flag=True, help="List global workflow scripts")
def list_scripts(is_global):
    """List all workflow scripts and their lockfile status."""
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    scripts = loader.discover_scripts()
    if not scripts:
        scope = "global" if is_global else "local"
        click.echo(f"No {scope} workflow scripts found.")
        return

    lockfile = loader.load_lockfile()
    locked_commands = lockfile.get("commands", {}) if lockfile else {}

    table = Table(title=f"Workflow Scripts ({'global' if is_global else 'local'})")
    table.add_column("Name", style="cyan")
    table.add_column("Language", style="blue")
    table.add_column("Version", style="green")
    table.add_column("Hash", style="dim")
    table.add_column("Status", style="yellow")

    for script_path in scripts:
        name = script_path.stem
        info = loader.get_script_info(script_path)

        # Check status against lockfile
        if name in locked_commands:
            locked = locked_commands[name]
            current_hash = info.get("content_hash", "")
            locked_hash = locked.get("content_hash", "")

            if current_hash == locked_hash:
                status = "[green]synced[/green]"
            else:
                status = "[yellow]modified[/yellow]"
        else:
            status = "[red]unlocked[/red]"

        table.add_row(
            name,
            info.get("language", "unknown"),
            info.get("version", "1.0.0"),
            info.get("content_hash", "")[:16] + "..." if info.get("content_hash") else "-",
            status,
        )

    console.print(table)

    # Show lockfile info
    if lockfile:
        console.print(f"\n[dim]Lockfile: {loader.lockfile_path}[/dim]")
        console.print(f"[dim]Generated: {lockfile.get('generated_at', 'unknown')}[/dim]")
        console.print(f"[dim]Schema version: {lockfile.get('version', '1.0')}[/dim]")


@lock.command("history")
def list_history():
    """List historical command state snapshots."""
    states = load_legacy_lockfile()
    if not states:
        click.echo("No command state history found.")
        return

    table = Table(title="Command State History")
    table.add_column("Hash", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("# Commands", style="yellow")

    for state in states:
        table.add_row(state["hash"][:8], state["timestamp"], str(len(state.get("commands", []))))

    console.print(table)


@lock.command("restore")
@click.argument("hash_value")
def restore_state(hash_value):
    """Restore to a previous command state by hash (from history)."""
    state = find_state_by_hash(hash_value)
    if not state:
        click.echo(f"State {hash_value[:8]} not found.", err=True)
        return 1

    console.print(f"[yellow]State {hash_value[:8]} contents:[/yellow]\n")
    console.print(json.dumps(state["commands"], indent=2))
    console.print("\n[dim]Note: Automatic restore is not yet implemented.[/dim]")
    console.print("[dim]Copy the command definitions manually to restore.[/dim]")
    return 0


@lock.command("verify")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Verify global workflows instead of local"
)
@click.option("--code", "-c", is_flag=True, help="Also validate that workflow code is executable")
def verify_scripts(is_global, code):
    """
    Verify that workflow scripts match the lockfile.

    Checks:
    - Missing scripts (in lockfile but not on disk)
    - Extra scripts (on disk but not in lockfile)
    - Hash mismatches (script content changed)
    - Version mismatches (informational)

    Use --code/-c to also validate that scripts can be loaded as Click commands.
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    lockfile = loader.load_lockfile()
    if not lockfile:
        console.print("[yellow]No lockfile found. Run 'mcli lock update' to create one.[/yellow]")
        return 1

    verification = loader.verify_lockfile()
    has_issues = False

    # Check for issues
    if not verification["valid"]:
        has_issues = True
        console.print("[yellow]Workflows are out of sync with the lockfile:[/yellow]\n")

        if verification["missing"]:
            console.print("[red]Missing scripts[/red] (in lockfile but not found):")
            for name in verification["missing"]:
                console.print(f"  - {name}")

        if verification["extra"]:
            console.print("\n[yellow]Extra scripts[/yellow] (not in lockfile):")
            for name in verification["extra"]:
                console.print(f"  - {name}")

        if verification["hash_mismatch"]:
            console.print("\n[yellow]Modified scripts[/yellow] (content hash changed):")
            for name in verification["hash_mismatch"]:
                console.print(f"  - {name}")

        console.print("\n[dim]Run 'mcli lock update' to sync the lockfile[/dim]\n")

    # Report version mismatches (informational)
    if verification.get("version_mismatch"):
        console.print("[cyan]Version changes detected:[/cyan]")
        for name in verification["version_mismatch"]:
            console.print(f"  - {name}")
        console.print("")

    # Validate code if requested
    if code:
        console.print("[cyan]Validating workflow code...[/cyan]\n")

        scripts = loader.discover_scripts()
        invalid_scripts = []

        for script_path in scripts:
            name = script_path.stem
            try:
                command = loader.load_command(script_path)
                if command is None:
                    invalid_scripts.append(
                        {"name": name, "reason": "Could not load as Click command"}
                    )
            except SyntaxError as e:
                invalid_scripts.append({"name": name, "reason": f"Syntax error: {e}"})
            except Exception as e:
                invalid_scripts.append({"name": name, "reason": f"Failed to load: {e}"})

        if invalid_scripts:
            has_issues = True
            console.print("[red]Invalid scripts found:[/red]\n")

            for item in invalid_scripts:
                console.print(f"  [red]x[/red] {item['name']}")
                console.print(f"    [dim]{item['reason']}[/dim]")

            console.print("\n[yellow]Fix the script code and try again.[/yellow]")
        else:
            console.print("[green]All workflow code is valid[/green]\n")

    if not has_issues:
        console.print("[green]All workflows are verified and in sync[/green]")
        return 0

    return 1


@lock.command("update")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Update global lockfile instead of local"
)
def update_lockfile(is_global):
    """
    Update the workflows lockfile with current script state.

    This regenerates workflows.lock.json from the current script files,
    capturing their content hash, version, and other metadata.
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    scripts = loader.discover_scripts()
    if not scripts:
        scope = "global" if is_global else "local"
        console.print(f"[yellow]No {scope} workflow scripts found.[/yellow]")
        return 0

    if loader.save_lockfile():
        console.print(f"[green]Updated lockfile: {loader.lockfile_path}[/green]")
        console.print(f"[dim]Tracked {len(scripts)} workflow script(s)[/dim]")
        return 0
    else:
        console.print("[red]Failed to update lockfile.[/red]")
        return 1


@lock.command("show")
@click.argument("name", required=False)
@click.option("--global", "-g", "is_global", is_flag=True, help="Show global lockfile")
def show_lockfile(name, is_global):
    """
    Show lockfile contents or details for a specific script.

    If NAME is provided, shows detailed info for that script.
    Otherwise shows the full lockfile.
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    lockfile = loader.load_lockfile()
    if not lockfile:
        console.print("[yellow]No lockfile found. Run 'mcli lock update' to create one.[/yellow]")
        return 1

    if name:
        commands = lockfile.get("commands", {})
        if name not in commands:
            console.print(f"[red]Script '{name}' not found in lockfile.[/red]")
            return 1

        info = commands[name]
        console.print(f"[cyan]Script: {name}[/cyan]\n")
        console.print(json.dumps(info, indent=2))
    else:
        console.print(f"[cyan]Lockfile: {loader.lockfile_path}[/cyan]\n")
        console.print(json.dumps(lockfile, indent=2))

    return 0


@lock.command("diff")
@click.option("--global", "-g", "is_global", is_flag=True, help="Diff global workflows")
def diff_lockfile(is_global):
    """
    Show differences between current scripts and lockfile.

    Compares current script state against the lockfile and shows
    what has changed (added, removed, modified).
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    loader = ScriptLoader(workflows_dir)

    lockfile = loader.load_lockfile()
    if not lockfile:
        console.print("[yellow]No lockfile found. Run 'mcli lock update' to create one.[/yellow]")
        return 1

    verification = loader.verify_lockfile()
    locked_commands = lockfile.get("commands", {})

    has_changes = False

    # Added scripts
    if verification["extra"]:
        has_changes = True
        console.print("[green]Added scripts:[/green]")
        for name in verification["extra"]:
            console.print(f"  + {name}")
        console.print("")

    # Removed scripts
    if verification["missing"]:
        has_changes = True
        console.print("[red]Removed scripts:[/red]")
        for name in verification["missing"]:
            console.print(f"  - {name}")
        console.print("")

    # Modified scripts
    if verification["hash_mismatch"]:
        has_changes = True
        console.print("[yellow]Modified scripts:[/yellow]")
        for name in verification["hash_mismatch"]:
            if name in locked_commands:
                old_version = locked_commands[name].get("version", "?")
                # Get current version
                scripts = {p.stem: p for p in loader.discover_scripts()}
                if name in scripts:
                    info = loader.get_script_info(scripts[name])
                    new_version = info.get("version", "?")
                    console.print(f"  ~ {name} (v{old_version} -> v{new_version})")
                else:
                    console.print(f"  ~ {name}")
        console.print("")

    # Version-only changes (no hash change)
    version_only = [
        n
        for n in verification.get("version_mismatch", [])
        if n not in verification["hash_mismatch"]
    ]
    if version_only:
        console.print("[cyan]Version bumped (metadata only):[/cyan]")
        for name in version_only:
            console.print(f"  * {name}")
        console.print("")

    if not has_changes:
        console.print("[green]No changes detected. Lockfile is in sync.[/green]")

    return 0
