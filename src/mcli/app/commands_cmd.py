import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.prompt import Prompt

from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.custom_commands import get_command_manager
from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


@click.group()
def commands():
    """Manage and execute available commands."""
    pass


@commands.command("list")
@click.option("--include-groups", is_flag=True, help="Include command groups in listing")
@click.option("--daemon-only", is_flag=True, help="Show only daemon database commands")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_commands(include_groups: bool, daemon_only: bool, as_json: bool):
    """List all available commands"""
    try:
        if daemon_only:
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


@commands.command("search")
@click.argument("query")
@click.option("--daemon-only", is_flag=True, help="Search only daemon database commands")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search_commands(query: str, daemon_only: bool, as_json: bool):
    """Search commands by name, description, or tags"""
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


@commands.command("execute")
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


@commands.command("info")
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


@commands.command("add")
@click.argument("command_name", required=True)
@click.option("--group", "-g", help="Command group (defaults to 'workflow')", default="workflow")
@click.option("--description", "-d", help="Description for the command", default="Custom command")
@click.option(
    "--template",
    "-t",
    is_flag=True,
    help="Use template mode (skip editor and use predefined template)",
)
def add_command(command_name, group, description, template):
    """
    Generate a new portable custom command saved to ~/.mcli/commands/.

    This command will open your default editor to allow you to write the Python logic
    for your command. The editor will be opened with a template that you can modify.

    Commands are automatically nested under the 'workflow' group by default,
    making them portable and persistent across updates.

    Example:
        mcli commands add my_command
        mcli commands add analytics --group data
        mcli commands add quick_cmd --template  # Use template without editor
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
    if template:
        # Use template mode - generate and save directly
        code = get_command_template(command_name, command_group)
        click.echo(f"Using template for command: {command_name}")
    else:
        # Editor mode - open editor for user to write code
        click.echo(f"Opening editor for command: {command_name}")
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
    )

    logger.info(f"Created portable custom command: {command_name}")
    console.print(f"[green]Created portable custom command: {command_name}[/green]")
    console.print(f"[dim]Saved to: {saved_path}[/dim]")
    console.print("[dim]Command will be automatically loaded on next mcli startup[/dim]")
    console.print(
        f"[dim]You can share this command by copying {saved_path} to another machine's ~/.mcli/commands/ directory[/dim]"
    )

    return 0


@commands.command("list-custom")
def list_custom_commands():
    """
    List all custom commands stored in ~/.mcli/commands/.
    """
    from rich.table import Table

    manager = get_command_manager()
    cmds = manager.load_all_commands()

    if not cmds:
        console.print("No custom commands found.")
        console.print("Create one with: mcli commands add <name>")
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
    console.print(f"\n[dim]Commands directory: {manager.commands_dir}[/dim]")
    console.print(f"[dim]Lockfile: {manager.lockfile_path}[/dim]")

    return 0


@commands.command("remove")
@click.argument("command_name", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def remove_command(command_name, yes):
    """
    Remove a custom command from ~/.mcli/commands/.
    """
    manager = get_command_manager()
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


@commands.command("export")
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
        console.print(f"[green]Exported custom commands to: {export_path}[/green]")
        console.print(
            f"[dim]Import on another machine with: mcli commands import {export_path}[/dim]"
        )
        return 0
    else:
        console.print("[red]Failed to export commands.[/red]")
        return 1


@commands.command("import")
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


@commands.command("verify")
def verify_commands():
    """
    Verify that custom commands match the lockfile.
    """
    manager = get_command_manager()

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


@commands.command("update-lockfile")
def update_lockfile():
    """
    Update the commands lockfile with current state.
    """
    manager = get_command_manager()

    if manager.update_lockfile():
        console.print(f"[green]Updated lockfile: {manager.lockfile_path}[/green]")
        return 0
    else:
        console.print("[red]Failed to update lockfile.[/red]")
        return 1


@commands.command("edit")
@click.argument("command_name")
@click.option("--editor", "-e", help="Editor to use (defaults to $EDITOR)")
def edit_command(command_name, editor):
    """
    Edit a command interactively using $EDITOR.

    Opens the command's Python code in your preferred editor,
    allows you to make changes, and saves the updated version.

    Examples:
        mcli commands edit my-command
        mcli commands edit my-command --editor code
    """
    import subprocess

    manager = get_command_manager()

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


@commands.command("import-script")
@click.argument("script_path", type=click.Path(exists=True))
@click.option("--name", "-n", help="Command name (defaults to script filename)")
@click.option("--group", "-g", default="workflow", help="Command group")
@click.option("--description", "-d", help="Command description")
@click.option("--interactive", "-i", is_flag=True, help="Open in $EDITOR for review/editing")
def import_script(script_path, name, group, description, interactive):
    """
    Import a Python script as a portable JSON command.

    Converts a Python script into a JSON command that can be loaded
    by mcli. The script should define Click commands.

    Examples:
        mcli commands import-script my_script.py
        mcli commands import-script my_script.py --name custom-cmd --interactive
    """
    import subprocess

    script_file = Path(script_path).resolve()

    if not script_file.exists():
        console.print(f"[red]Script not found: {script_file}[/red]")
        return 1

    # Read the script content
    try:
        with open(script_file, "r") as f:
            code = f.read()
    except Exception as e:
        console.print(f"[red]Failed to read script: {e}[/red]")
        return 1

    # Determine command name
    if not name:
        name = script_file.stem.lower().replace("-", "_")

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
            description = ast.get_docstring(tree) or f"Imported from {script_file.name}"
        except:
            description = f"Imported from {script_file.name}"

    # Save as JSON command
    manager = get_command_manager()

    saved_path = manager.save_command(
        name=name,
        code=code,
        description=description,
        group=group,
        metadata={
            "source": "import-script",
            "original_file": str(script_file),
            "imported_at": datetime.now().isoformat(),
        },
    )

    console.print(f"[green]Imported script as command: {name}[/green]")
    console.print(f"[dim]Saved to: {saved_path}[/dim]")
    console.print(f"[dim]Use with: mcli {group} {name}[/dim]")
    console.print("[dim]Command will be available after restart or reload[/dim]")

    return 0


@commands.command("export-script")
@click.argument("command_name")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option(
    "--standalone",
    "-s",
    is_flag=True,
    help="Make script standalone (add if __name__ == '__main__')",
)
def export_script(command_name, output, standalone):
    """
    Export a JSON command to a Python script.

    Converts a portable JSON command back to a standalone Python script
    that can be edited and run independently.

    Examples:
        mcli commands export-script my-command
        mcli commands export-script my-command --output my_script.py --standalone
    """
    manager = get_command_manager()

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

    console.print(f"[dim]Edit and re-import with: mcli commands import-script {output_file}[/dim]")

    return 0
