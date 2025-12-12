"""
Top-level new command for MCLI.

This module provides the `mcli new` command for creating new portable
workflow commands as native script files in ~/.mcli/workflows/.
"""

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click
from rich.prompt import Prompt

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir, get_git_root, is_git_repository
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console

logger = get_logger(__name__)

# File extensions for each language
LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "shell": ".sh",
    "javascript": ".js",
    "typescript": ".ts",
    "ipynb": ".ipynb",
}


def get_python_template(name: str, description: str, group: str, version: str = "1.0.0") -> str:
    """Generate template code for a Python command."""
    return f'''#!/usr/bin/env python3
# @description: {description}
# @version: {version}
# @group: {group}

"""
{name} command for mcli.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()


@click.command(name="{name}")
@click.argument("name", default="World")
def {name}_command(name: str):
    """
    {description}
    """
    logger.info(f"Hello, {{name}}! This is the {name} command.")
    click.echo(f"Hello, {{name}}! This is the {name} command.")
'''


def get_shell_template(
    name: str, description: str, group: str, shell: str = "bash", version: str = "1.0.0"
) -> str:
    """Generate template shell script for a new command."""
    return f"""#!/usr/bin/env {shell}
# @description: {description}
# @version: {version}
# @group: {group}
# @shell: {shell}

# {name} - {description}
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


def get_javascript_template(name: str, description: str, group: str, version: str = "1.0.0") -> str:
    """Generate template JavaScript code for a new command."""
    return f"""#!/usr/bin/env bun
// @description: {description}
// @version: {version}
// @group: {group}

/**
 * {name} - {description}
 *
 * This is a JavaScript MCLI workflow command executed with Bun.
 * Arguments are available in Bun.argv (first two are bun and script path).
 * The command name is available in process.env.MCLI_COMMAND
 */

const args = Bun.argv.slice(2);

console.log(`Hello from {name} JavaScript command!`);
console.log(`Command: ${{process.env.MCLI_COMMAND}}`);

if (args.length > 0) {{
    console.log(`Arguments: ${{args.join(', ')}}`);
    args.forEach((arg, i) => console.log(`  ${{i + 1}}. ${{arg}}`));
}} else {{
    console.log('No arguments provided');
}}
"""


def get_typescript_template(name: str, description: str, group: str, version: str = "1.0.0") -> str:
    """Generate template TypeScript code for a new command."""
    return f"""#!/usr/bin/env bun
// @description: {description}
// @version: {version}
// @group: {group}

/**
 * {name} - {description}
 *
 * This is a TypeScript MCLI workflow command executed with Bun.
 * Arguments are available in Bun.argv (first two are bun and script path).
 * The command name is available in process.env.MCLI_COMMAND
 */

const args: string[] = Bun.argv.slice(2);
const commandName: string = process.env.MCLI_COMMAND || '{name}';

console.log(`Hello from {name} TypeScript command!`);
console.log(`Command: ${{commandName}}`);

if (args.length > 0) {{
    console.log(`Arguments: ${{args.join(', ')}}`);
    args.forEach((arg: string, i: number) => console.log(`  ${{i + 1}}. ${{arg}}`));
}} else {{
    console.log('No arguments provided');
}}
"""


def get_ipynb_template(name: str, description: str, group: str, version: str = "1.0.0") -> str:
    """Generate template Jupyter notebook for a new command."""
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# {name}\n",
                    "\n",
                    f"{description}\n",
                    "\n",
                    "This notebook can be executed as an MCLI workflow command using papermill.\n",
                    "Parameters can be passed via `mcli run {name} -p key value`.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {
                    "tags": ["parameters"],
                },
                "outputs": [],
                "source": [
                    "# Parameters cell - values can be overridden at runtime\n",
                    "name = 'World'\n",
                    "verbose = False\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Main logic\n",
                    f"print(f'Hello from {name} notebook!')\n",
                    "print(f'name parameter: {name}')\n",
                    "\n",
                    "if verbose:\n",
                    "    print('Verbose mode enabled')\n",
                ],
            },
        ],
        "metadata": {
            "mcli": {
                "description": description,
                "version": version,
                "group": group,
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(notebook, indent=2)


def open_editor_for_script(
    script_path: Path,
    template_content: str,
    language: str,
) -> Optional[str]:
    """
    Open the user's default editor to allow them to write script code.

    Args:
        script_path: Path where the script will be saved
        template_content: Initial template content
        language: Script language

    Returns:
        The code written by the user, or None if cancelled
    """
    # Get the user's default editor
    editor = os.environ.get("EDITOR")
    if not editor:
        for common_editor in ["vim", "nano", "code", "subl", "atom", "emacs"]:
            if subprocess.run(["which", common_editor], capture_output=True).returncode == 0:
                editor = common_editor
                break

    if not editor:
        click.echo(
            "No editor found. Please set the EDITOR environment variable or install vim/nano."
        )
        return None

    # Check if we're in an interactive environment
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        click.echo(
            "Editor requires an interactive terminal. Use --template flag for non-interactive mode."
        )
        return None

    # Determine file suffix
    suffix = LANGUAGE_EXTENSIONS.get(language, ".txt")

    # Create temporary file with template
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as temp_file:
        temp_file.write(template_content)
        temp_file_path = temp_file.name

    try:
        click.echo(f"Opening {editor} to edit {language} script...")
        click.echo("Write your code and save the file to continue.")
        click.echo("Press Ctrl+C to cancel.")

        result = subprocess.run([editor, temp_file_path], check=False)

        if result.returncode != 0:
            click.echo("Editor exited with error. Command creation cancelled.")
            return None

        with open(temp_file_path, "r") as f:
            edited_code = f.read()

        if not edited_code.strip():
            click.echo("No code provided. Command creation cancelled.")
            return None

        click.echo("Script code captured successfully!")
        return edited_code

    except KeyboardInterrupt:
        click.echo("\nCommand creation cancelled by user.")
        return None
    except Exception as e:
        click.echo(f"Error opening editor: {e}")
        return None
    finally:
        Path(temp_file_path).unlink(missing_ok=True)


def save_script(
    workflows_dir: Path,
    name: str,
    code: str,
    language: str,
) -> Path:
    """
    Save script code to a file.

    Args:
        workflows_dir: Directory to save the script
        name: Command name
        code: Script code content
        language: Script language

    Returns:
        Path to the saved script file
    """
    extension = LANGUAGE_EXTENSIONS.get(language, ".txt")
    script_path = workflows_dir / f"{name}{extension}"

    # Ensure directory exists
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # Write the script
    with open(script_path, "w") as f:
        f.write(code)

    # Make executable for shell/python scripts
    if language in ("python", "shell"):
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)

    return script_path


@click.command("new")
@click.argument("command_name", required=True)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["python", "shell", "javascript", "typescript", "ipynb"], case_sensitive=False),
    required=True,
    help="Script language (required): python, shell, javascript, typescript, or ipynb",
)
@click.option("--group", help="Command group (defaults to 'workflows')", default="workflows")
@click.option("--description", "-d", help="Description for the command", default="")
@click.option("--version", "-v", "cmd_version", help="Initial version", default="1.0.0")
@click.option(
    "--template",
    "-t",
    is_flag=True,
    help="Use template mode (skip editor and use predefined template)",
)
@click.option(
    "--shell",
    "-s",
    type=click.Choice(["bash", "zsh", "fish", "sh"], case_sensitive=False),
    help="Shell type for shell scripts (defaults to $SHELL)",
)
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Add to global workflows (~/.mcli/workflows/) instead of local (.mcli/workflows/)",
)
def new(command_name, language, group, description, cmd_version, template, shell, is_global):
    """
    Create a new workflow command as a native script file.

    LANGUAGE is required: python, shell, javascript, typescript, or ipynb

    This command will open your default editor to allow you to write your
    script. The script will be saved directly as a native file (.py, .sh, .js, .ts, or .ipynb).

    Commands are automatically nested under the 'workflows' group by default.

    Examples:

        mcli new my_command -l python

        mcli new backup_db -l shell

        mcli new data_fetch -l javascript

        mcli new processor -l typescript

        mcli new analysis -l ipynb

        mcli new quick_cmd -l python -t  # Template mode (no editor)
    """
    # Normalize command name
    command_name = command_name.lower().replace("-", "_")

    # Validate command name
    if not re.match(r"^[a-z][a-z0-9_]*$", command_name):
        logger.error(
            f"Invalid command name: {command_name}. "
            "Use lowercase letters, numbers, and underscores (starting with a letter)."
        )
        click.echo(
            f"Invalid command name: {command_name}. "
            "Use lowercase letters, numbers, and underscores (starting with a letter).",
            err=True,
        )
        return 1

    # Validate and normalize group name
    if group:
        command_group = group.lower().replace("-", "_")
        if not re.match(r"^[a-z][a-z0-9_]*$", command_group):
            logger.error(
                f"Invalid group name: {command_group}. "
                "Use lowercase letters, numbers, and underscores (starting with a letter)."
            )
            click.echo(
                f"Invalid group name: {command_group}. "
                "Use lowercase letters, numbers, and underscores (starting with a letter).",
                err=True,
            )
            return 1
    else:
        command_group = "workflows"

    # Normalize language
    language = language.lower()

    # Get workflows directory
    workflows_dir = get_custom_commands_dir(global_mode=is_global)

    # Check if command already exists
    extension = LANGUAGE_EXTENSIONS.get(language, ".txt")
    script_path = workflows_dir / f"{command_name}{extension}"

    if script_path.exists():
        logger.warning(f"Script already exists: {script_path}")
        should_override = Prompt.ask(
            "Script already exists. Override?", choices=["y", "n"], default="n"
        )
        if should_override.lower() != "y":
            logger.info("Command creation aborted.")
            click.echo("Command creation aborted.")
            return 1

    # Set default description if not provided
    if not description:
        description = f"{command_name.replace('_', ' ').title()} command"

    # Determine shell type for shell commands
    if language == "shell" and not shell:
        shell_env = os.environ.get("SHELL", "/bin/bash")
        shell = shell_env.split("/")[-1]
        click.echo(f"Using shell: {shell} (from $SHELL environment variable)")

    # Generate template code based on language
    if language == "python":
        template_code = get_python_template(command_name, description, command_group, cmd_version)
    elif language == "shell":
        template_code = get_shell_template(
            command_name, description, command_group, shell or "bash", cmd_version
        )
    elif language == "javascript":
        template_code = get_javascript_template(command_name, description, command_group, cmd_version)
    elif language == "typescript":
        template_code = get_typescript_template(command_name, description, command_group, cmd_version)
    elif language == "ipynb":
        template_code = get_ipynb_template(command_name, description, command_group, cmd_version)
    else:
        click.echo(f"Unsupported language: {language}", err=True)
        return 1

    # Get final code
    if template:
        # Use template mode - save directly
        code = template_code
        click.echo(f"Using {language} template for command: {command_name}")
    else:
        # Editor mode
        click.echo(f"Opening editor for {language} command: {command_name}")
        code = open_editor_for_script(script_path, template_code, language)
        if code is None:
            click.echo("Command creation cancelled.")
            return 1

    # Save the script
    saved_path = save_script(workflows_dir, command_name, code, language)

    # Update lockfile
    try:
        loader = ScriptLoader(workflows_dir)
        loader.save_lockfile()
    except Exception as e:
        logger.warning(f"Failed to update lockfile: {e}")

    # Display success message
    is_local = not is_global and is_git_repository()
    git_root = get_git_root() if is_local else None
    scope = "local" if is_local else "global"
    scope_display = f"[yellow]{scope}[/yellow]" if is_local else f"[cyan]{scope}[/cyan]"

    lang_display = language
    if language == "shell" and shell:
        lang_display = f"{language} ({shell})"

    logger.info(f"Created workflow script: {command_name} ({lang_display}) [{scope}]")
    console.print(
        f"[green]Created workflow script: {command_name}[/green] "
        f"[dim]({lang_display}) [Scope: {scope_display}][/dim]"
    )
    console.print(f"[dim]Saved to: {saved_path}[/dim]")
    if is_local and git_root:
        console.print(f"[dim]Git repository: {git_root}[/dim]")
    console.print(f"[dim]Group: {command_group}[/dim]")
    console.print(f"[dim]Execute with: mcli run {command_name}[/dim]")
    console.print("[dim]Or with global flag: mcli run -g {command_name}[/dim]")

    if scope == "global":
        console.print(
            f"[dim]You can share this command by copying {saved_path} to another machine's "
            "~/.mcli/workflows/ directory[/dim]"
        )
    else:
        console.print(
            "[dim]This command is local to this git repository. "
            "Use --global/-g to create global commands.[/dim]"
        )

    return 0
