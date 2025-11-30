"""
Top-level create command for MCLI.

This module provides the `mcli create` command for generating new portable
custom commands saved to ~/.mcli/commands/.
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import click
from rich.prompt import Prompt

from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


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
        with open(temp_file_path) as f:
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
        try:  # noqa: SIM105
            os.unlink(temp_file_path)
        except OSError:
            pass


@click.command("create")
@click.argument("command_name", required=True)
@click.option("--group", help="Command group (defaults to 'workflows')", default="workflows")
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
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Add to global commands (~/.mcli/commands/) instead of local (.mcli/commands/)",
)
def create(command_name, group, description, template, language, shell, is_global):
    """
    Generate a new portable custom command saved to ~/.mcli/commands/.

    This command will open your default editor to allow you to write Python or shell
    logic for your command. The editor will be opened with a template that you can modify.

    Commands are automatically nested under the 'workflows' group by default,
    making them portable and persistent across updates.

    Examples:
        # Python command (default)
        mcli create my_command
        mcli create analytics --group data
        mcli create quick_cmd --template

        # Shell command
        mcli create backup-db --language shell
        mcli create deploy --language shell --shell bash
        mcli create quick-sh -l shell -t  # Template mode
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
        command_group = "workflows"  # Default to workflows group

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
    if language == "shell":  # noqa: SIM102
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

                with open(tmp_path) as f:
                    code = f.read()

                if not code.strip():
                    click.echo("No code provided. Command creation cancelled.")
                    return 1
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            # Python command - use existing editor function
            editor_result = open_editor_for_command(command_name, command_group, description)
            if editor_result is None:
                click.echo("Command creation cancelled.")
                return 1
            code = editor_result

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
            "[dim]This command is local to this git repository. Use --global/-g to create global commands.[/dim]"
        )

    return 0
