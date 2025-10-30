import hashlib
import importlib
import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import tomli
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.custom_commands import get_command_manager
from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console, error, info, success, warning

logger = get_logger(__name__)

# Command state lockfile configuration
LOCKFILE_PATH = Path.home() / ".local" / "mcli" / "command_lock.json"

# Command store configuration
DEFAULT_STORE_PATH = Path.home() / "repos" / "mcli-commands"
COMMANDS_PATH = Path.home() / ".mcli" / "commands"


# Helper functions for command state management


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


def get_current_command_state():
    """Collect all command metadata (names, groups, etc.)"""
    return collect_commands()


def hash_command_state(commands):
    """Hash the command state for fast comparison."""
    # Sort for deterministic hash
    commands_sorted = sorted(commands, key=lambda c: (c.get("group") or "", c["name"]))
    state_json = json.dumps(commands_sorted, sort_keys=True)
    return hashlib.sha256(state_json.encode("utf-8")).hexdigest()


def load_lockfile():
    """Load the command state lockfile."""
    if LOCKFILE_PATH.exists():
        with open(LOCKFILE_PATH, "r") as f:
            return json.load(f)
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
    """Find a state by its hash value."""
    states = load_lockfile()
    for state in states:
        if state["hash"] == hash_value:
            return state
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


@click.group(name="workflow")
def workflow():
    """Manage workflows - create, edit, import, export workflow commands."""
    pass


# For backward compatibility, keep commands as an alias
commands = workflow


@workflow.command("init")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Initialize global workflows directory instead of local"
)
@click.option(
    "--git", is_flag=True, help="Initialize git repository in workflows directory"
)
@click.option(
    "--force", "-f", is_flag=True, help="Force initialization even if directory exists"
)
def init_workflows(is_global, git, force):
    """
    Initialize workflows directory structure.

    Creates the necessary directories and configuration files for managing
    custom workflows. By default, creates a local .mcli/workflows/ directory
    if in a git repository, otherwise uses ~/.mcli/workflows/.

    Examples:
        mcli workflow init              # Initialize local workflows (if in git repo)
        mcli workflow init --global     # Initialize global workflows
        mcli workflow init --git        # Also initialize git repository
    """
    from mcli.lib.paths import (
        get_custom_commands_dir,
        get_lockfile_path,
        get_git_root,
        is_git_repository,
    )

    # Determine if we're in a git repository
    in_git_repo = is_git_repository() and not is_global
    git_root = get_git_root() if in_git_repo else None

    # Get the workflows directory
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    lockfile_path = get_lockfile_path(global_mode=is_global)

    # Check if already initialized
    if workflows_dir.exists() and not force:
        if lockfile_path.exists():
            console.print(f"[yellow]Workflows directory already initialized at:[/yellow] {workflows_dir}")
            console.print(f"[dim]Use --force to reinitialize[/dim]")

            should_continue = Prompt.ask(
                "Continue anyway?", choices=["y", "n"], default="n"
            )
            if should_continue.lower() != "y":
                return 0

    # Create workflows directory
    workflows_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Created workflows directory: {workflows_dir}")

    # Create README.md
    readme_path = workflows_dir / "README.md"
    if not readme_path.exists() or force:
        scope = "local" if in_git_repo else "global"
        scope_desc = f"for repository: {git_root.name}" if in_git_repo else "globally"

        readme_content = f"""# MCLI Custom Workflows

This directory contains custom workflow commands {scope_desc}.

## Quick Start

### Create a New Workflow

```bash
# Python workflow
mcli workflow add my-workflow

# Shell workflow
mcli workflow add my-script --language shell
```

### List Workflows

```bash
mcli workflow list --custom-only
```

### Execute a Workflow

```bash
mcli workflows my-workflow
```

### Edit a Workflow

```bash
mcli workflow edit my-workflow
```

### Export/Import Workflows

```bash
# Export all workflows
mcli workflow export workflows-backup.json

# Import workflows
mcli workflow import workflows-backup.json
```

## Directory Structure

```
{workflows_dir.name}/
├── README.md              # This file
├── commands.lock.json     # Lockfile for workflow state
└── *.json                 # Individual workflow definitions
```

## Workflow Format

Workflows are stored as JSON files with the following structure:

```json
{{
  "name": "workflow-name",
  "description": "Workflow description",
  "code": "Python or shell code",
  "language": "python",
  "group": "workflow",
  "version": "1.0",
  "created_at": "2025-10-30T...",
  "updated_at": "2025-10-30T..."
}}
```

## Scope

- **Scope**: {'Local (repository-specific)' if in_git_repo else 'Global (user-wide)'}
- **Location**: `{workflows_dir}`
{f"- **Git Repository**: `{git_root}`" if git_root else ""}

## Documentation

- [MCLI Documentation](https://github.com/gwicho38/mcli)
- [Workflow Guide](https://github.com/gwicho38/mcli/blob/main/docs/features/LOCAL_VS_GLOBAL_COMMANDS.md)

---

*Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        readme_path.write_text(readme_content)
        console.print(f"[green]✓[/green] Created README: {readme_path.name}")

    # Initialize lockfile
    if not lockfile_path.exists() or force:
        lockfile_data = {
            "version": "1.0",
            "initialized_at": datetime.now().isoformat(),
            "scope": "local" if in_git_repo else "global",
            "commands": {}
        }

        with open(lockfile_path, "w") as f:
            json.dump(lockfile_data, f, indent=2)

        console.print(f"[green]✓[/green] Initialized lockfile: {lockfile_path.name}")

    # Create .gitignore if in workflows directory
    gitignore_path = workflows_dir / ".gitignore"
    if not gitignore_path.exists() or force:
        gitignore_content = """# Backup files
*.backup
*.bak

# Temporary files
*.tmp
*.temp

# OS files
.DS_Store
Thumbs.db

# Editor files
*.swp
*.swo
*~
.vscode/
.idea/
"""
        gitignore_path.write_text(gitignore_content)
        console.print(f"[green]✓[/green] Created .gitignore")

    # Initialize git if requested
    if git and not (workflows_dir / ".git").exists():
        try:
            subprocess.run(
                ["git", "init"],
                cwd=workflows_dir,
                check=True,
                capture_output=True
            )
            console.print(f"[green]✓[/green] Initialized git repository in workflows directory")

            # Create initial commit
            subprocess.run(
                ["git", "add", "."],
                cwd=workflows_dir,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit: Initialize workflows directory"],
                cwd=workflows_dir,
                check=True,
                capture_output=True
            )
            console.print(f"[green]✓[/green] Created initial commit")

        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]⚠[/yellow] Git initialization failed: {e}")
        except FileNotFoundError:
            console.print(f"[yellow]⚠[/yellow] Git not found. Skipping git initialization.")

    # Summary
    console.print()
    console.print("[bold green]Workflows directory initialized successfully![/bold green]")
    console.print()

    # Display summary table
    table = Table(title="Initialization Summary", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Scope", "Local (repository-specific)" if in_git_repo else "Global (user-wide)")
    table.add_row("Location", str(workflows_dir))
    if git_root:
        table.add_row("Git Repository", str(git_root))
    table.add_row("Lockfile", str(lockfile_path))
    table.add_row("Git Initialized", "Yes" if git and (workflows_dir / ".git").exists() else "No")

    console.print(table)
    console.print()

    # Next steps
    console.print("[bold]Next Steps:[/bold]")
    console.print("  1. Create a workflow:  [cyan]mcli workflow add my-workflow[/cyan]")
    console.print("  2. List workflows:     [cyan]mcli workflow list --custom-only[/cyan]")
    console.print("  3. Execute workflow:   [cyan]mcli workflows my-workflow[/cyan]")
    console.print("  4. View README:        [cyan]cat {}/README.md[/cyan]".format(workflows_dir))
    console.print()

    if in_git_repo:
        console.print(f"[dim]Tip: Workflows are local to this repository. Use --global for user-wide workflows.[/dim]")
    else:
        console.print(f"[dim]Tip: Use workflows in any git repository, or create local ones with 'mcli workflow init' inside repos.[/dim]")

    return 0


@workflow.command("list")
@click.option("--include-groups", is_flag=True, help="Include command groups in listing")
@click.option("--daemon-only", is_flag=True, help="Show only daemon database commands")
@click.option(
    "--custom-only", is_flag=True, help="Show only custom commands from command directory"
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Use global commands (~/.mcli/commands/) instead of local (.mcli/commands/)"
)
def list_commands(include_groups: bool, daemon_only: bool, custom_only: bool, as_json: bool, is_global: bool):
    """
    List all available commands.

    By default, shows all discovered Click commands. Use flags to filter:
    - --custom-only: Show only custom commands
    - --daemon-only: Show only daemon database commands
    - --global/-g: Use global commands directory instead of local

    Examples:
        mcli commands list                  # Show all commands (local if in git repo)
        mcli commands list --custom-only    # Show only custom commands (local if in git repo)
        mcli commands list --global         # Show all global commands
        mcli commands list --custom-only -g # Show only global custom commands
        mcli commands list --json           # Output as JSON
    """
    from rich.table import Table

    try:
        if custom_only:
            # Show only custom commands
            manager = get_command_manager(global_mode=is_global)
            cmds = manager.load_all_commands()

            if not cmds:
                console.print("No custom commands found.")
                console.print("Create one with: mcli commands add <name>")
                return 0

            if as_json:
                click.echo(json.dumps({"commands": cmds, "total": len(cmds)}, indent=2))
                return 0

            table = Table(title="Custom Commands")
            table.add_column("Name", style="green")
            table.add_column("Group", style="blue")
            table.add_column("Description", style="yellow")
            table.add_column("Version", style="cyan")
            table.add_column("Updated", style="dim")

            for cmd in cmds:
                table.add_row(
                    cmd["name"],
                    cmd.get("group", "-"),
                    cmd.get("description", ""),
                    cmd.get("version", "1.0"),
                    cmd.get("updated_at", "")[:10] if cmd.get("updated_at") else "-",
                )

            console.print(table)

            # Show context information
            scope = "global" if is_global or not manager.is_local else "local"
            scope_color = "yellow" if scope == "local" else "cyan"
            console.print(f"\n[dim]Scope: [{scope_color}]{scope}[/{scope_color}][/dim]")
            if manager.is_local and manager.git_root:
                console.print(f"[dim]Git repository: {manager.git_root}[/dim]")
            console.print(f"[dim]Commands directory: {manager.commands_dir}[/dim]")
            console.print(f"[dim]Lockfile: {manager.lockfile_path}[/dim]")

            return 0

        elif daemon_only:
            # Show only daemon database commands
            client = get_daemon_client()
            result = client.list_commands(all=True)

            if isinstance(result, dict):
                commands_data = result.get("commands", [])
            elif isinstance(result, list):
                commands_data = result
            else:
                commands_data = []
        else:
            # Show all discovered Click commands
            discovery = get_command_discovery()
            commands_data = discovery.get_commands(include_groups=include_groups)

        if as_json:
            click.echo(
                json.dumps({"commands": commands_data, "total": len(commands_data)}, indent=2)
            )
            return

        if not commands_data:
            console.print("No commands found")
            return

        console.print(f"[bold]Available Commands ({len(commands_data)}):[/bold]")
        for cmd in commands_data:
            # Handle different command sources
            if daemon_only:
                status = "[red][INACTIVE][/red] " if not cmd.get("is_active", True) else ""
                console.print(
                    f"{status}• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})"
                )
            else:
                group_indicator = "[blue][GROUP][/blue] " if cmd.get("is_group") else ""
                console.print(f"{group_indicator}• [green]{cmd['full_name']}[/green]")

            if cmd.get("description"):
                console.print(f"  {cmd['description']}")
            if cmd.get("module"):
                console.print(f"  Module: {cmd['module']}")
            if cmd.get("tags"):
                console.print(f"  Tags: {', '.join(cmd['tags'])}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@workflow.command("search")
@click.argument("query")
@click.option("--daemon-only", is_flag=True, help="Search only daemon database commands")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Search global commands instead of local"
)
def search_commands(query: str, daemon_only: bool, as_json: bool, is_global: bool):
    """
    Search commands by name, description, or tags.

    By default searches local commands (if in git repo), use --global/-g for global commands.
    """
    try:
        if daemon_only:
            # Search only daemon database commands
            client = get_daemon_client()
            result = client.list_commands(all=True)

            if isinstance(result, dict):
                all_commands = result.get("commands", [])
            elif isinstance(result, list):
                all_commands = result
            else:
                all_commands = []

            # Filter commands that match the query
            matching_commands = [
                cmd
                for cmd in all_commands
                if (
                    query.lower() in cmd["name"].lower()
                    or query.lower() in (cmd["description"] or "").lower()
                    or any(query.lower() in tag.lower() for tag in cmd.get("tags", []))
                )
            ]
        else:
            # Search all discovered Click commands
            discovery = get_command_discovery()
            matching_commands = discovery.search_commands(query)

        if as_json:
            click.echo(
                json.dumps(
                    {
                        "commands": matching_commands,
                        "total": len(matching_commands),
                        "query": query,
                    },
                    indent=2,
                )
            )
            return

        if not matching_commands:
            console.print(f"No commands found matching '[yellow]{query}[/yellow]'")
            return

        console.print(f"[bold]Commands matching '{query}' ({len(matching_commands)}):[/bold]")
        for cmd in matching_commands:
            if daemon_only:
                status = "[red][INACTIVE][/red] " if not cmd.get("is_active", True) else ""
                console.print(
                    f"{status}• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})"
                )
            else:
                group_indicator = "[blue][GROUP][/blue] " if cmd.get("is_group") else ""
                console.print(f"{group_indicator}• [green]{cmd['full_name']}[/green]")

            console.print(f"  [italic]{cmd['description']}[/italic]")
            if cmd.get("module"):
                console.print(f"  Module: {cmd['module']}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@workflow.command("execute")
@click.argument("command_name")
@click.argument("args", nargs=-1)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
def execute_command(command_name: str, args: tuple, as_json: bool, timeout: Optional[int]):
    """Execute a command by name"""
    try:
        client = get_daemon_client()
        result = client.execute_command(command_name=command_name, args=list(args), timeout=timeout)

        if as_json:
            click.echo(json.dumps(result, indent=2))
            return

        if result.get("success"):
            if result.get("output"):
                console.print(f"[green]Output:[/green]\n{result['output']}")
            else:
                console.print("[green]Command executed successfully[/green]")

            if result.get("execution_time_ms"):
                console.print(f"[dim]Execution time: {result['execution_time_ms']}ms[/dim]")
        else:
            console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@workflow.command("info")
@click.argument("command_name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def command_info(command_name: str, as_json: bool):
    """Show detailed information about a command"""
    try:
        client = get_daemon_client()
        result = client.list_commands(all=True)

        if isinstance(result, dict):
            all_commands = result.get("commands", [])
        elif isinstance(result, list):
            all_commands = result
        else:
            all_commands = []

        # Find the command
        command = None
        for cmd in all_commands:
            if cmd["name"].lower() == command_name.lower():
                command = cmd
                break

        if not command:
            console.print(f"[red]Command '{command_name}' not found[/red]")
            return

        if as_json:
            click.echo(json.dumps(command, indent=2))
            return

        console.print(f"[bold]Command: {command['name']}[/bold]")
        console.print(f"Language: {command['language']}")
        console.print(f"Description: {command.get('description', 'No description')}")
        console.print(f"Group: {command.get('group', 'None')}")
        console.print(f"Tags: {', '.join(command.get('tags', []))}")
        console.print(f"Active: {'Yes' if command.get('is_active', True) else 'No'}")
        console.print(f"Execution Count: {command.get('execution_count', 0)}")

        if command.get("created_at"):
            console.print(f"Created: {command['created_at']}")
        if command.get("last_executed"):
            console.print(f"Last Executed: {command['last_executed']}")

        if command.get("code"):
            console.print(f"\n[bold]Code:[/bold]")
            console.print(f"```{command['language']}")
            console.print(command["code"])
            console.print("```")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# Custom command management functions
# Moved from mcli.self.self_cmd for better organization


def get_command_template(name: str, group: Optional[str] = None) -> str:
    """Generate template code for a new command."""
    if group:
        # Template for a command in a group using Click
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
        # Template for a command directly under workflow using Click
        template = f'''"""
{name} command for mcli.
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


def get_shell_command_template(name: str, shell: str = "bash", description: str = "") -> str:
    """Generate template shell script for a new command."""
    template = f"""#!/usr/bin/env {shell}
# {name} - {description or "Shell workflow command"}
#
# This is a shell-based MCLI workflow command.
# Arguments are passed as positional parameters: $1, $2, $3, etc.
# The command name is available in: $MCLI_COMMAND

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Command logic
echo "Hello from {name} shell command!"
echo "Command: $MCLI_COMMAND"

# Example: Access arguments
if [ $# -gt 0 ]; then
    echo "Arguments: $@"
    for arg in "$@"; do
        echo "  - $arg"
    done
else
    echo "No arguments provided"
fi

# Exit successfully
exit 0
"""
    return template


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
    import subprocess
    import sys

    # Get the user's default editor
    editor = os.environ.get("EDITOR")
    if not editor:
        # Try common editors in order of preference
        for common_editor in ["vim", "nano", "code", "subl", "atom", "emacs"]:
            if subprocess.run(["which", common_editor], capture_output=True).returncode == 0:
                editor = common_editor
                break

    if not editor:
        click.echo(
            "No editor found. Please set the EDITOR environment variable or install vim/nano."
        )
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
    """My custom command."""
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
                "Editor requires an interactive terminal. Use --template flag for non-interactive mode."
            )
            return None

        # Open editor
        click.echo(f"Opening {editor} to edit command logic...")
        click.echo("Write your Python command logic and save the file to continue.")
        click.echo("Press Ctrl+C to cancel command creation.")

        # Run the editor
        result = subprocess.run([editor, temp_file_path], check=False)

        if result.returncode != 0:
            click.echo("Editor exited with error. Command creation cancelled.")
            return None

        # Read the edited content
        with open(temp_file_path, "r") as f:
            edited_code = f.read()

        # Check if the file was actually edited (not just the template)
        if edited_code.strip() == enhanced_template.strip():
            click.echo("No changes detected. Command creation cancelled.")
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
            click.echo("No command code found. Command creation cancelled.")
            return None

        click.echo("Command code captured successfully!")
        return final_code

    except KeyboardInterrupt:
        click.echo("\nCommand creation cancelled by user.")
        return None
    except Exception as e:
        click.echo(f"Error opening editor: {e}")
        return None
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass


@workflow.command("add")
@click.argument("command_name", required=True)
@click.option("--group", help="Command group (defaults to 'workflow')", default="workflow")
@click.option("--description", "-d", help="Description for the command", default="Custom command")
@click.option(
    "--template",
    "-t",
    is_flag=True,
    help="Use template mode (skip editor and use predefined template)",
)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["python", "shell"], case_sensitive=False),
    default="python",
    help="Command language (python or shell)",
)
@click.option(
    "--shell",
    "-s",
    type=click.Choice(["bash", "zsh", "fish", "sh"], case_sensitive=False),
    help="Shell type for shell commands (defaults to $SHELL)",
)
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Add to global commands (~/.mcli/commands/) instead of local (.mcli/commands/)"
)
def add_command(command_name, group, description, template, language, shell, is_global):
    """
    Generate a new portable custom command saved to ~/.mcli/commands/.

    This command will open your default editor to allow you to write Python or shell
    logic for your command. The editor will be opened with a template that you can modify.

    Commands are automatically nested under the 'workflow' group by default,
    making them portable and persistent across updates.

    Examples:
        # Python command (default)
        mcli commands add my_command
        mcli commands add analytics --group data
        mcli commands add quick_cmd --template

        # Shell command
        mcli commands add backup-db --language shell
        mcli commands add deploy --language shell --shell bash
        mcli commands add quick-sh -l shell -t  # Template mode
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
    manager = get_command_manager(global_mode=is_global)

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

    # Normalize language
    language = language.lower()

    # Determine shell type for shell commands
    if language == "shell":
        if not shell:
            # Default to $SHELL environment variable or bash
            shell_env = os.environ.get("SHELL", "/bin/bash")
            shell = shell_env.split("/")[-1]
            click.echo(f"Using shell: {shell} (from $SHELL environment variable)")

    # Generate command code
    if template:
        # Use template mode - generate and save directly
        if language == "shell":
            code = get_shell_command_template(command_name, shell, description)
            click.echo(f"Using shell template for command: {command_name}")
        else:
            code = get_command_template(command_name, command_group)
            click.echo(f"Using Python template for command: {command_name}")
    else:
        # Editor mode - open editor for user to write code
        click.echo(f"Opening editor for command: {command_name}")

        if language == "shell":
            # For shell commands, open editor with shell template
            shell_template = get_shell_command_template(command_name, shell, description)

            # Create temp file with shell template
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tmp:
                tmp.write(shell_template)
                tmp_path = tmp.name

            try:
                editor = os.environ.get("EDITOR", "vim")
                result = subprocess.run([editor, tmp_path])

                if result.returncode != 0:
                    click.echo("Editor exited with error. Command creation cancelled.")
                    return 1

                with open(tmp_path, "r") as f:
                    code = f.read()

                if not code.strip():
                    click.echo("No code provided. Command creation cancelled.")
                    return 1
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            # Python command - use existing editor function
            code = open_editor_for_command(command_name, command_group, description)
            if code is None:
                click.echo("Command creation cancelled.")
                return 1

    # Save the command
    saved_path = manager.save_command(
        name=command_name,
        code=code,
        description=description,
        group=command_group,
        language=language,
        shell=shell if language == "shell" else None,
    )

    lang_display = f"{language}" if language == "python" else f"{language} ({shell})"
    scope = "global" if is_global or not manager.is_local else "local"
    scope_display = f"[cyan]{scope}[/cyan]" if scope == "global" else f"[yellow]{scope}[/yellow]"

    logger.info(f"Created portable custom command: {command_name} ({lang_display}) [{scope}]")
    console.print(
        f"[green]Created portable custom command: {command_name}[/green] [dim]({lang_display}) [Scope: {scope_display}][/dim]"
    )
    console.print(f"[dim]Saved to: {saved_path}[/dim]")
    if manager.is_local and manager.git_root:
        console.print(f"[dim]Git repository: {manager.git_root}[/dim]")
    console.print(f"[dim]Group: {command_group}[/dim]")
    console.print(f"[dim]Execute with: mcli {command_group} {command_name}[/dim]")
    console.print("[dim]Command will be automatically loaded on next mcli startup[/dim]")

    if scope == "global":
        console.print(
            f"[dim]You can share this command by copying {saved_path} to another machine's ~/.mcli/commands/ directory[/dim]"
        )
    else:
        console.print(
            f"[dim]This command is local to this git repository. Use --global/-g to create global commands.[/dim]"
        )

    return 0


@workflow.command("remove")
@click.argument("command_name", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Remove from global commands instead of local"
)
def remove_command(command_name, yes, is_global):
    """
    Remove a custom command.

    By default removes from local commands (if in git repo), use --global/-g for global commands.
    """
    manager = get_command_manager(global_mode=is_global)
    command_file = manager.commands_dir / f"{command_name}.json"

    if not command_file.exists():
        console.print(f"[red]Command '{command_name}' not found.[/red]")
        return 1

    if not yes:
        should_delete = Prompt.ask(
            f"Delete command '{command_name}'?", choices=["y", "n"], default="n"
        )
        if should_delete.lower() != "y":
            console.print("Deletion cancelled.")
            return 0

    if manager.delete_command(command_name):
        console.print(f"[green]Deleted custom command: {command_name}[/green]")
        return 0
    else:
        console.print(f"[red]Failed to delete command: {command_name}[/red]")
        return 1


@workflow.command("export")
@click.argument("target", type=click.Path(), required=False)
@click.option(
    "--script", "-s", is_flag=True, help="Export as Python script (requires command name)"
)
@click.option(
    "--standalone", is_flag=True, help="Make script standalone (add if __name__ == '__main__')"
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Export from global commands instead of local"
)
def export_commands(target, script, standalone, output, is_global):
    """
    Export custom commands to JSON file or export a single command to Python script.

    Default behavior (no flags): Export all commands to JSON
    With --script/-s: Export a single command to Python script

    Examples:
        mcli commands export                    # Export all local commands
        mcli commands export --global           # Export all global commands
        mcli commands export my-export.json     # Export all to specified file
        mcli commands export my-cmd -s          # Export command to my-cmd.py
        mcli commands export my-cmd -s -o out.py --standalone
    """
    manager = get_command_manager(global_mode=is_global)

    if script:
        # Export single command to Python script
        if not target:
            console.print("[red]Command name required when using --script/-s flag[/red]")
            return 1

        command_name = target

        # Load the command
        command_file = manager.commands_dir / f"{command_name}.json"
        if not command_file.exists():
            console.print(f"[red]Command not found: {command_name}[/red]")
            return 1

        try:
            with open(command_file, "r") as f:
                command_data = json.load(f)
        except Exception as e:
            console.print(f"[red]Failed to load command: {e}[/red]")
            return 1

        # Get the code
        code = command_data.get("code", "")

        if not code:
            console.print(f"[red]Command has no code: {command_name}[/red]")
            return 1

        # Add standalone wrapper if requested
        if standalone:
            # Check if already has if __name__ == '__main__'
            if "if __name__" not in code:
                code += "\n\nif __name__ == '__main__':\n    app()\n"

        # Determine output path
        if not output:
            output = f"{command_name}.py"

        output_file = Path(output)

        # Write the script
        try:
            with open(output_file, "w") as f:
                f.write(code)
        except Exception as e:
            console.print(f"[red]Failed to write script: {e}[/red]")
            return 1

        console.print(f"[green]Exported command to script: {output_file}[/green]")
        console.print(f"[dim]Source command: {command_name}[/dim]")

        if standalone:
            console.print(f"[dim]Run standalone with: python {output_file}[/dim]")

        console.print(f"[dim]Edit and re-import with: mcli commands import {output_file} -s[/dim]")

        return 0
    else:
        # Export all commands to JSON
        export_file = target if target else "commands-export.json"
        export_path = Path(export_file)

        if manager.export_commands(export_path):
            console.print(f"[green]Exported custom commands to: {export_path}[/green]")
            console.print(
                f"[dim]Import on another machine with: mcli commands import {export_path}[/dim]"
            )
            return 0
        else:
            console.print("[red]Failed to export commands.[/red]")
            return 1


@workflow.command("import")
@click.argument("source", type=click.Path(exists=True), required=True)
@click.option("--script", "-s", is_flag=True, help="Import from Python script")
@click.option("--overwrite", is_flag=True, help="Overwrite existing commands")
@click.option("--name", "-n", help="Command name (for script import, defaults to script filename)")
@click.option("--group", default="workflow", help="Command group (for script import)")
@click.option("--description", "-d", help="Command description (for script import)")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Open in $EDITOR for review/editing (for script import)",
)
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Import to global commands instead of local"
)
def import_commands(source, script, overwrite, name, group, description, interactive, is_global):
    """
    Import custom commands from JSON file or import a Python script as a command.

    Default behavior (no flags): Import from JSON file
    With --script/-s: Import a Python script as a command

    Examples:
        mcli commands import commands-export.json        # Import to local (if in git repo)
        mcli commands import commands-export.json --global  # Import to global
        mcli commands import my_script.py -s
        mcli commands import my_script.py -s --name custom-cmd --interactive
    """
    import subprocess

    manager = get_command_manager(global_mode=is_global)
    source_path = Path(source)

    if script:
        # Import script as command (Python or Shell)
        if not source_path.exists():
            console.print(f"[red]Script not found: {source_path}[/red]")
            return 1

        # Read the script content
        try:
            with open(source_path, "r") as f:
                code = f.read()
        except Exception as e:
            console.print(f"[red]Failed to read script: {e}[/red]")
            return 1

        # Auto-detect language from shebang or file extension
        detected_language = "python"
        detected_shell = None

        if code.strip().startswith("#!"):
            # Parse shebang
            shebang = code.strip().split("\n")[0]
            if "bash" in shebang:
                detected_language = "shell"
                detected_shell = "bash"
            elif "zsh" in shebang:
                detected_language = "shell"
                detected_shell = "zsh"
            elif "fish" in shebang:
                detected_language = "shell"
                detected_shell = "fish"
            elif "/bin/sh" in shebang or "/sh" in shebang:
                detected_language = "shell"
                detected_shell = "sh"
            elif "python" in shebang:
                detected_language = "python"

        # Also check file extension
        if source_path.suffix in [".sh", ".bash", ".zsh"]:
            detected_language = "shell"
            if not detected_shell:
                if source_path.suffix == ".bash":
                    detected_shell = "bash"
                elif source_path.suffix == ".zsh":
                    detected_shell = "zsh"
                else:
                    detected_shell = "bash"  # Default for .sh

        console.print(f"[dim]Detected language: {detected_language}[/dim]")
        if detected_language == "shell":
            console.print(f"[dim]Detected shell: {detected_shell}[/dim]")

        # Determine command name
        if not name:
            name = source_path.stem.lower().replace("-", "_")

        # Validate command name
        if not re.match(r"^[a-z][a-z0-9_]*$", name):
            console.print(f"[red]Invalid command name: {name}[/red]")
            return 1

        # Interactive editing
        if interactive:
            editor = os.environ.get("EDITOR", "vim")
            console.print(f"Opening in {editor} for review...")

            # Create temp file with the code
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            try:
                subprocess.run([editor, tmp_path], check=True)

                # Read edited content
                with open(tmp_path, "r") as f:
                    code = f.read()
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        # Get description
        if not description:
            # Try to extract from docstring
            import ast

            try:
                tree = ast.parse(code)
                description = ast.get_docstring(tree) or f"Imported from {source_path.name}"
            except:
                description = f"Imported from {source_path.name}"

        # Save as JSON command
        saved_path = manager.save_command(
            name=name,
            code=code,
            description=description,
            group=group,
            language=detected_language,
            shell=detected_shell if detected_language == "shell" else None,
            metadata={
                "source": "import-script",
                "original_file": str(source_path),
                "imported_at": datetime.now().isoformat(),
            },
        )

        lang_display = (
            f"{detected_language}"
            if detected_language == "python"
            else f"{detected_language} ({detected_shell})"
        )
        console.print(
            f"[green]Imported script as command: {name}[/green] [dim]({lang_display})[/dim]"
        )
        console.print(f"[dim]Saved to: {saved_path}[/dim]")
        console.print(f"[dim]Use with: mcli {group} {name}[/dim]")
        console.print("[dim]Command will be available after restart or reload[/dim]")

        return 0
    else:
        # Import from JSON file
        results = manager.import_commands(source_path, overwrite=overwrite)

        success_count = sum(1 for v in results.values() if v)
        failed_count = len(results) - success_count

        if success_count > 0:
            console.print(f"[green]Imported {success_count} command(s)[/green]")

        if failed_count > 0:
            console.print(
                f"[yellow]Skipped {failed_count} command(s) (already exist, use --overwrite to replace)[/yellow]"
            )
            console.print("Skipped commands:")
            for name, success in results.items():
                if not success:
                    console.print(f"  - {name}")

        return 0


@workflow.command("verify")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Verify global commands instead of local"
)
def verify_commands(is_global):
    """
    Verify that custom commands match the lockfile.

    By default verifies local commands (if in git repo), use --global/-g for global commands.
    """
    manager = get_command_manager(global_mode=is_global)

    # First, ensure lockfile is up to date
    manager.update_lockfile()

    verification = manager.verify_lockfile()

    if verification["valid"]:
        console.print("[green]All custom commands are in sync with the lockfile.[/green]")
        return 0

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

    console.print("\n[dim]Run 'mcli commands update-lockfile' to sync the lockfile[/dim]")

    return 1


@workflow.command("update-lockfile")
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


@workflow.command("edit")
@click.argument("command_name")
@click.option("--editor", "-e", help="Editor to use (defaults to $EDITOR)")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Edit global command instead of local"
)
def edit_command(command_name, editor, is_global):
    """
    Edit a command interactively using $EDITOR.

    Opens the command's Python code in your preferred editor,
    allows you to make changes, and saves the updated version.

    Examples:
        mcli commands edit my-command            # Edit local command (if in git repo)
        mcli commands edit my-command --global   # Edit global command
        mcli commands edit my-command --editor code
    """
    import subprocess

    manager = get_command_manager(global_mode=is_global)

    # Load the command
    command_file = manager.commands_dir / f"{command_name}.json"
    if not command_file.exists():
        console.print(f"[red]Command not found: {command_name}[/red]")
        return 1

    try:
        with open(command_file, "r") as f:
            command_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Failed to load command: {e}[/red]")
        return 1

    code = command_data.get("code", "")

    if not code:
        console.print(f"[red]Command has no code: {command_name}[/red]")
        return 1

    # Determine editor
    if not editor:
        editor = os.environ.get("EDITOR", "vim")

    console.print(f"Opening command in {editor}...")

    # Create temp file with the code
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix=f"{command_name}_"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # Open in editor
        result = subprocess.run([editor, tmp_path])

        if result.returncode != 0:
            console.print(f"[yellow]Editor exited with code {result.returncode}[/yellow]")

        # Read edited content
        with open(tmp_path, "r") as f:
            new_code = f.read()

        # Check if code changed
        if new_code.strip() == code.strip():
            console.print("No changes made")
            return 0

        # Validate syntax
        try:
            compile(new_code, "<string>", "exec")
        except SyntaxError as e:
            console.print(f"[red]Syntax error in edited code: {e}[/red]")
            should_save = Prompt.ask("Save anyway?", choices=["y", "n"], default="n")
            if should_save.lower() != "y":
                return 1

        # Update the command
        command_data["code"] = new_code
        command_data["updated_at"] = datetime.now().isoformat()

        with open(command_file, "w") as f:
            json.dump(command_data, f, indent=2)

        # Update lockfile
        manager.update_lockfile()

        console.print(f"[green]Updated command: {command_name}[/green]")
        console.print(f"[dim]Saved to: {command_file}[/dim]")
        console.print("[dim]Reload with: mcli self reload or restart mcli[/dim]")

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return 0


# State management subgroup
# Moved from mcli.self for better organization


@workflow.group("state")
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


# Store management subgroup
# Moved from mcli.self for better organization


def _get_store_path() -> Path:
    """Get store path from config or default"""
    config_file = Path.home() / ".mcli" / "store.conf"

    if config_file.exists():
        store_path = Path(config_file.read_text().strip())
        if store_path.exists():
            return store_path

    # Use default
    return DEFAULT_STORE_PATH


@workflow.group("store")
def store():
    """Manage command store - sync ~/.mcli/commands/ to git"""
    pass


@store.command(name="init")
@click.option("--path", "-p", type=click.Path(), help=f"Store path (default: {DEFAULT_STORE_PATH})")
@click.option("--remote", "-r", help="Git remote URL (optional)")
def init_store(path, remote):
    """Initialize command store with git"""
    store_path = Path(path) if path else DEFAULT_STORE_PATH

    try:
        # Create store directory
        store_path.mkdir(parents=True, exist_ok=True)

        # Initialize git if not already initialized
        git_dir = store_path / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=store_path, check=True, capture_output=True)
            success(f"Initialized git repository at {store_path}")

            # Create .gitignore
            gitignore = store_path / ".gitignore"
            gitignore.write_text("*.backup\n.DS_Store\n")

            # Create README
            readme = store_path / "README.md"
            readme.write_text(
                f"""# MCLI Commands Store

Personal workflow commands for mcli framework.

## Usage

Push commands:
```bash
mcli commands store push
```

Pull commands:
```bash
mcli commands store pull
```

Sync (bidirectional):
```bash
mcli commands store sync
```

## Structure

All JSON command files from `~/.mcli/commands/` are stored here and version controlled.

Last updated: {datetime.now().isoformat()}
"""
            )

            # Add remote if provided
            if remote:
                subprocess.run(
                    ["git", "remote", "add", "origin", remote], cwd=store_path, check=True
                )
                success(f"Added remote: {remote}")
        else:
            info(f"Git repository already exists at {store_path}")

        # Save store path to config
        config_file = Path.home() / ".mcli" / "store.conf"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(str(store_path))

        success(f"Command store initialized at {store_path}")
        info(f"Store path saved to {config_file}")

    except subprocess.CalledProcessError as e:
        error(f"Git command failed: {e}")
        logger.error(f"Git init failed: {e}")
    except Exception as e:
        error(f"Failed to initialize store: {e}")
        logger.exception(e)


@store.command(name="push")
@click.option("--message", "-m", help="Commit message")
@click.option("--all", "-a", is_flag=True, help="Push all files (including backups)")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Push global commands instead of local"
)
def push_commands(message, all, is_global):
    """
    Push commands to git store.

    By default pushes local commands (if in git repo), use --global/-g for global commands.
    """
    try:
        store_path = _get_store_path()
        from mcli.lib.paths import get_custom_commands_dir
        COMMANDS_PATH = get_custom_commands_dir(global_mode=is_global)

        # Copy commands to store
        info(f"Copying commands from {COMMANDS_PATH} to {store_path}...")

        copied_count = 0
        for item in COMMANDS_PATH.glob("*"):
            # Skip backups unless --all specified
            if not all and item.name.endswith(".backup"):
                continue

            dest = store_path / item.name
            if item.is_file():
                shutil.copy2(item, dest)
                copied_count += 1
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
                copied_count += 1

        success(f"Copied {copied_count} items to store")

        # Git add, commit, push
        subprocess.run(["git", "add", "."], cwd=store_path, check=True)

        # Check if there are changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=store_path, capture_output=True, text=True
        )

        if not result.stdout.strip():
            info("No changes to commit")
            return

        # Commit with message
        commit_msg = message or f"Update commands {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=store_path, check=True)
        success(f"Committed changes: {commit_msg}")

        # Push to remote if configured
        try:
            subprocess.run(["git", "push"], cwd=store_path, check=True, capture_output=True)
            success("Pushed to remote")
        except subprocess.CalledProcessError:
            warning("No remote configured or push failed. Commands committed locally.")

    except Exception as e:
        error(f"Failed to push commands: {e}")
        logger.exception(e)


@store.command(name="pull")
@click.option("--force", "-f", is_flag=True, help="Overwrite local commands without backup")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Pull to global commands instead of local"
)
def pull_commands(force, is_global):
    """
    Pull commands from git store.

    By default pulls to local commands (if in git repo), use --global/-g for global commands.
    """
    try:
        store_path = _get_store_path()
        from mcli.lib.paths import get_custom_commands_dir
        COMMANDS_PATH = get_custom_commands_dir(global_mode=is_global)

        # Pull from remote
        try:
            subprocess.run(["git", "pull"], cwd=store_path, check=True)
            success("Pulled latest changes from remote")
        except subprocess.CalledProcessError:
            warning("No remote configured or pull failed. Using local store.")

        # Backup existing commands if not force
        if not force and COMMANDS_PATH.exists():
            backup_dir = (
                COMMANDS_PATH.parent / f"commands_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.copytree(COMMANDS_PATH, backup_dir)
            info(f"Backed up existing commands to {backup_dir}")

        # Copy from store to commands directory
        info(f"Copying commands from {store_path} to {COMMANDS_PATH}...")

        COMMANDS_PATH.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        for item in store_path.glob("*"):
            # Skip git directory and README
            if item.name in [".git", "README.md", ".gitignore"]:
                continue

            dest = COMMANDS_PATH / item.name
            if item.is_file():
                shutil.copy2(item, dest)
                copied_count += 1
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
                copied_count += 1

        success(f"Pulled {copied_count} items from store")

    except Exception as e:
        error(f"Failed to pull commands: {e}")
        logger.exception(e)


@store.command(name="sync")
@click.option("--message", "-m", help="Commit message if pushing")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Sync global commands instead of local"
)
def sync_commands(message, is_global):
    """
    Sync commands bidirectionally (pull then push if changes).

    By default syncs local commands (if in git repo), use --global/-g for global commands.
    """
    try:
        store_path = _get_store_path()
        from mcli.lib.paths import get_custom_commands_dir
        COMMANDS_PATH = get_custom_commands_dir(global_mode=is_global)

        # First pull
        info("Pulling latest changes...")
        try:
            subprocess.run(["git", "pull"], cwd=store_path, check=True, capture_output=True)
            success("Pulled from remote")
        except subprocess.CalledProcessError:
            warning("No remote or pull failed")

        # Then push local changes
        info("Pushing local changes...")

        # Copy commands
        for item in COMMANDS_PATH.glob("*"):
            if item.name.endswith(".backup"):
                continue
            dest = store_path / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)

        # Check for changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=store_path, capture_output=True, text=True
        )

        if not result.stdout.strip():
            success("Everything in sync!")
            return

        # Commit and push
        subprocess.run(["git", "add", "."], cwd=store_path, check=True)
        commit_msg = message or f"Sync commands {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=store_path, check=True)

        try:
            subprocess.run(["git", "push"], cwd=store_path, check=True, capture_output=True)
            success("Synced and pushed to remote")
        except subprocess.CalledProcessError:
            success("Synced locally (no remote configured)")

    except Exception as e:
        error(f"Sync failed: {e}")
        logger.exception(e)


@store.command(name="status")
def store_status():
    """Show git status of command store"""
    try:
        store_path = _get_store_path()

        click.echo(f"\n📦 Store: {store_path}\n")

        # Git status
        result = subprocess.run(
            ["git", "status", "--short", "--branch"], cwd=store_path, capture_output=True, text=True
        )

        if result.stdout:
            click.echo(result.stdout)

        # Show remote
        result = subprocess.run(
            ["git", "remote", "-v"], cwd=store_path, capture_output=True, text=True
        )

        if result.stdout:
            click.echo("\n🌐 Remotes:")
            click.echo(result.stdout)
        else:
            info("\nNo remote configured")

        click.echo()

    except Exception as e:
        error(f"Failed to get status: {e}")
        logger.exception(e)


@store.command(name="config")
@click.option("--remote", "-r", help="Set git remote URL")
@click.option("--path", "-p", type=click.Path(), help="Change store path")
def configure_store(remote, path):
    """Configure store settings"""
    try:
        store_path = _get_store_path()

        if path:
            new_path = Path(path).expanduser().resolve()
            config_file = Path.home() / ".mcli" / "store.conf"
            config_file.write_text(str(new_path))
            success(f"Store path updated to: {new_path}")
            return

        if remote:
            # Check if remote exists
            result = subprocess.run(
                ["git", "remote"], cwd=store_path, capture_output=True, text=True
            )

            if "origin" in result.stdout:
                subprocess.run(
                    ["git", "remote", "set-url", "origin", remote], cwd=store_path, check=True
                )
                success(f"Updated remote URL: {remote}")
            else:
                subprocess.run(
                    ["git", "remote", "add", "origin", remote], cwd=store_path, check=True
                )
                success(f"Added remote URL: {remote}")

    except Exception as e:
        error(f"Configuration failed: {e}")
        logger.exception(e)


@store.command(name="list")
@click.option("--store", "-s", is_flag=True, help="List store instead of local")
def list_commands(store):
    """List all commands"""
    try:
        if store:
            store_path = _get_store_path()
            path = store_path
            title = f"Commands in store ({store_path})"
        else:
            path = COMMANDS_PATH
            title = f"Local commands ({COMMANDS_PATH})"

        click.echo(f"\n{title}:\n")

        if not path.exists():
            warning(f"Directory does not exist: {path}")
            return

        items = sorted(path.glob("*"))
        if not items:
            info("No commands found")
            return

        for item in items:
            if item.name in [".git", ".gitignore", "README.md"]:
                continue

            if item.is_file():
                size = item.stat().st_size / 1024
                modified = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                click.echo(f"  📄 {item.name:<40} {size:>8.1f} KB  {modified}")
            elif item.is_dir():
                count = len(list(item.glob("*")))
                click.echo(f"  📁 {item.name:<40} {count:>3} files")

        click.echo()

    except Exception as e:
        error(f"Failed to list commands: {e}")
        logger.exception(e)


@store.command(name="show")
@click.argument("command_name")
@click.option("--store", "-s", is_flag=True, help="Show from store instead of local")
def show_command(command_name, store):
    """Show command file contents"""
    try:
        if store:
            store_path = _get_store_path()
            path = store_path / command_name
        else:
            path = COMMANDS_PATH / command_name

        if not path.exists():
            error(f"Command not found: {command_name}")
            return

        if path.is_file():
            click.echo(f"\n📄 {path}:\n")
            click.echo(path.read_text())
        else:
            info(f"{command_name} is a directory")
            for item in sorted(path.glob("*")):
                click.echo(f"  {item.name}")

        click.echo()

    except Exception as e:
        error(f"Failed to show command: {e}")
        logger.exception(e)


# Extract workflow commands command
# Moved from mcli.self for better organization


@workflow.command("extract-workflow-commands")
@click.option(
    "--output", "-o", type=click.Path(), help="Output file (default: workflow-commands.json)"
)
def extract_workflow_commands(output):
    """
    Extract workflow commands from Python modules to JSON format.

    This command helps migrate existing workflow commands to portable JSON format.
    """
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
                        command_info[
                            "code"
                        ] = f'''"""
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
                        command_info[
                            "code"
                        ] = f'''"""
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
            with open(output_file, "w") as f:
                json.dump(workflow_commands, f, indent=2)

            click.echo(f"✅ Extracted {len(workflow_commands)} workflow commands")
            click.echo(f"📁 Saved to: {output_file}")
            click.echo(f"\n💡 These are templates. Import with: mcli commands import {output_file}")
            click.echo("   Then customize the code in ~/.mcli/commands/<command>.json")
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
