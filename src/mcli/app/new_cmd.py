"""
Top-level new command for MCLI.

This module provides the `mcli new` command for creating new portable
workflow commands as native script files in ~/.mcli/workflows/.

Example:
    mcli new my_command -l python
    mcli new --file ./existing_script.py -g
"""

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.prompt import Prompt

from mcli.lib.constants import (
    ScriptCommentPrefixes,
    ScriptExtensions,
    ScriptLanguages,
    ScriptMetadataDefaults,
    ScriptMetadataKeys,
    ShellTypes,
)
from mcli.lib.errors import (
    InvalidCommandNameError,
    InvalidGroupNameError,
    UnsupportedFileTypeError,
    UnsupportedLanguageError,
)
from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir, get_git_root, is_git_repository
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.types import CommandMetadata, ScriptTemplate
from mcli.lib.ui.styling import console

logger = get_logger(__name__)

# Regex pattern for valid command/group names
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1


# =============================================================================
# Validation Functions
# =============================================================================


def validate_command_name(name: str) -> str:
    """
    Validate and normalize a command name.

    Args:
        name: The command name to validate

    Returns:
        Normalized command name (lowercase, underscores)

    Raises:
        InvalidCommandNameError: If the name is invalid
    """
    normalized = name.lower().replace("-", "_")
    if not NAME_PATTERN.match(normalized):
        raise InvalidCommandNameError(normalized)
    return normalized


def validate_group_name(name: str) -> str:
    """
    Validate and normalize a group name.

    Args:
        name: The group name to validate

    Returns:
        Normalized group name (lowercase, underscores)

    Raises:
        InvalidGroupNameError: If the name is invalid
    """
    normalized = name.lower().replace("-", "_")
    if not NAME_PATTERN.match(normalized):
        raise InvalidGroupNameError(normalized)
    return normalized


# =============================================================================
# Language Detection Functions
# =============================================================================


def detect_language_from_file(file_path: Path) -> str:
    """
    Detect the script language from a file's extension.

    Args:
        file_path: Path to the file

    Returns:
        Language identifier (e.g., "python", "shell")

    Raises:
        UnsupportedFileTypeError: If the file extension is not supported
    """
    extension = file_path.suffix.lower()
    language = ScriptExtensions.TO_LANGUAGE.get(extension)

    if language is None:
        raise UnsupportedFileTypeError(extension, ScriptExtensions.ALL)

    return language


# =============================================================================
# Metadata Functions
# =============================================================================


def has_mcli_metadata(content: str, language: str) -> bool:
    """
    Check if the file content already contains mcli metadata.

    Args:
        content: File content as string
        language: Script language identifier

    Returns:
        True if metadata comments/section exists, False otherwise
    """
    if language == ScriptLanguages.IPYNB:
        try:
            notebook = json.loads(content)
            return "mcli" in notebook.get("metadata", {})
        except json.JSONDecodeError:
            return False

    prefix = ScriptCommentPrefixes.BY_LANGUAGE.get(language, ScriptCommentPrefixes.HASH)
    pattern = rf"^{re.escape(prefix)}\s*@({ScriptMetadataKeys.DESCRIPTION}|{ScriptMetadataKeys.VERSION}|{ScriptMetadataKeys.GROUP}):"
    return bool(re.search(pattern, content, re.MULTILINE))


def add_metadata_to_script(
    content: str,
    language: str,
    name: str,
    description: str,
    group: str,
    version: str = ScriptMetadataDefaults.VERSION,
) -> str:
    """
    Add mcli metadata comments to an existing script.

    Metadata is inserted after the shebang line (if present) with proper
    spacing. For notebooks, metadata is added to the JSON structure.

    Args:
        content: Original file content
        language: Script language identifier
        name: Command name (unused but kept for API consistency)
        description: Command description
        group: Command group
        version: Command version

    Returns:
        Modified content with metadata added
    """
    if language == ScriptLanguages.IPYNB:
        return _add_metadata_to_notebook(content, description, group, version)

    prefix = ScriptCommentPrefixes.BY_LANGUAGE.get(language, ScriptCommentPrefixes.HASH)
    lines = content.split("\n")

    # Generate metadata block
    metadata_lines = [
        f"{prefix} @{ScriptMetadataKeys.DESCRIPTION}: {description}",
        f"{prefix} @{ScriptMetadataKeys.VERSION}: {version}",
        f"{prefix} @{ScriptMetadataKeys.GROUP}: {group}",
    ]

    # Find where to insert metadata (after shebang)
    insert_index = 0
    if lines and lines[0].startswith("#!"):
        insert_index = 1
        # Skip blank line after shebang
        if len(lines) > 1 and lines[1].strip() == "":
            insert_index = 2

    # Add spacing around metadata
    if insert_index > 0 and lines[insert_index - 1].startswith("#!"):
        metadata_lines.insert(0, "")
    metadata_lines.append("")

    # Rebuild content
    result_lines = lines[:insert_index] + metadata_lines + lines[insert_index:]
    return "\n".join(result_lines)


def _add_metadata_to_notebook(
    content: str,
    description: str,
    group: str,
    version: str = ScriptMetadataDefaults.VERSION,
) -> str:
    """
    Add mcli metadata to a Jupyter notebook's metadata section.

    Args:
        content: Notebook JSON content
        description: Command description
        group: Command group
        version: Command version

    Returns:
        Modified notebook JSON string
    """
    try:
        notebook = json.loads(content)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in notebook file")
        return content

    if "metadata" not in notebook:
        notebook["metadata"] = {}

    notebook["metadata"]["mcli"] = {
        ScriptMetadataKeys.DESCRIPTION: description,
        ScriptMetadataKeys.VERSION: version,
        ScriptMetadataKeys.GROUP: group,
    }

    return json.dumps(notebook, indent=2)


def restructure_file_as_command(
    file_path: Path,
    name: str,
    description: str,
    group: str,
    version: str,
    language: str,
) -> str:
    """
    Read a file and add mcli metadata if not already present.

    Args:
        file_path: Path to the source file
        name: Command name
        description: Command description
        group: Command group
        version: Command version
        language: Detected language

    Returns:
        File content with metadata (original or modified)

    Raises:
        click.ClickException: If file cannot be read
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise click.ClickException(f"Failed to read file: {e}")

    if has_mcli_metadata(content, language):
        logger.info(f"File already has mcli metadata: {file_path}")
        return content

    return add_metadata_to_script(content, language, name, description, group, version)


# =============================================================================
# Template Generation Functions
# =============================================================================


def get_template(template: ScriptTemplate) -> str:
    """
    Generate template code for a new script.

    Args:
        template: ScriptTemplate with name, description, group, version, language

    Returns:
        Template code string

    Raises:
        UnsupportedLanguageError: If language is not supported
    """
    generators = {
        ScriptLanguages.PYTHON: _get_python_template,
        ScriptLanguages.SHELL: _get_shell_template,
        ScriptLanguages.JAVASCRIPT: _get_javascript_template,
        ScriptLanguages.TYPESCRIPT: _get_typescript_template,
        ScriptLanguages.IPYNB: _get_ipynb_template,
    }

    generator = generators.get(template.language)
    if generator is None:
        raise UnsupportedLanguageError(template.language, ScriptLanguages.ALL)

    return generator(template)


def _get_python_template(t: ScriptTemplate) -> str:
    """Generate Python command template."""
    return f'''#!/usr/bin/env python3
# @{ScriptMetadataKeys.DESCRIPTION}: {t.description}
# @{ScriptMetadataKeys.VERSION}: {t.version}
# @{ScriptMetadataKeys.GROUP}: {t.group}

"""
{t.name} command for mcli.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()


@click.command(name="{t.name}")
@click.argument("name", default="World")
def {t.name}_command(name: str):
    """
    {t.description}
    """
    logger.info(f"Hello, {{name}}! This is the {t.name} command.")
    click.echo(f"Hello, {{name}}! This is the {t.name} command.")
'''


def _get_shell_template(t: ScriptTemplate) -> str:
    """Generate shell script template."""
    shell = t.shell or ShellTypes.DEFAULT
    return f"""#!/usr/bin/env {shell}
# @{ScriptMetadataKeys.DESCRIPTION}: {t.description}
# @{ScriptMetadataKeys.VERSION}: {t.version}
# @{ScriptMetadataKeys.GROUP}: {t.group}
# @{ScriptMetadataKeys.SHELL}: {shell}

# {t.name} - {t.description}
#
# This is a shell-based MCLI workflow command.
# Arguments are passed as positional parameters: $1, $2, $3, etc.
# The command name is available in: $MCLI_COMMAND

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Command logic
echo "Hello from {t.name} shell command!"
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


def _get_javascript_template(t: ScriptTemplate) -> str:
    """Generate JavaScript template."""
    return f"""#!/usr/bin/env bun
// @{ScriptMetadataKeys.DESCRIPTION}: {t.description}
// @{ScriptMetadataKeys.VERSION}: {t.version}
// @{ScriptMetadataKeys.GROUP}: {t.group}

/**
 * {t.name} - {t.description}
 *
 * This is a JavaScript MCLI workflow command executed with Bun.
 * Arguments are available in Bun.argv (first two are bun and script path).
 * The command name is available in process.env.MCLI_COMMAND
 */

const args = Bun.argv.slice(2);

console.log(`Hello from {t.name} JavaScript command!`);
console.log(`Command: ${{process.env.MCLI_COMMAND}}`);

if (args.length > 0) {{
    console.log(`Arguments: ${{args.join(', ')}}`);
    args.forEach((arg, i) => console.log(`  ${{i + 1}}. ${{arg}}`));
}} else {{
    console.log('No arguments provided');
}}
"""


def _get_typescript_template(t: ScriptTemplate) -> str:
    """Generate TypeScript template."""
    return f"""#!/usr/bin/env bun
// @{ScriptMetadataKeys.DESCRIPTION}: {t.description}
// @{ScriptMetadataKeys.VERSION}: {t.version}
// @{ScriptMetadataKeys.GROUP}: {t.group}

/**
 * {t.name} - {t.description}
 *
 * This is a TypeScript MCLI workflow command executed with Bun.
 * Arguments are available in Bun.argv (first two are bun and script path).
 * The command name is available in process.env.MCLI_COMMAND
 */

const args: string[] = Bun.argv.slice(2);
const commandName: string = process.env.MCLI_COMMAND || '{t.name}';

console.log(`Hello from {t.name} TypeScript command!`);
console.log(`Command: ${{commandName}}`);

if (args.length > 0) {{
    console.log(`Arguments: ${{args.join(', ')}}`);
    args.forEach((arg: string, i: number) => console.log(`  ${{i + 1}}. ${{arg}}`));
}} else {{
    console.log('No arguments provided');
}}
"""


def _get_ipynb_template(t: ScriptTemplate) -> str:
    """Generate Jupyter notebook template."""
    notebook: Dict[str, Any] = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# {t.name}\n",
                    "\n",
                    f"{t.description}\n",
                    "\n",
                    "This notebook can be executed as an MCLI workflow command using papermill.\n",
                    f"Parameters can be passed via `mcli run {t.name} -p key value`.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {"tags": ["parameters"]},
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
                    f"print(f'Hello from {t.name} notebook!')\n",
                    "print(f'name parameter: {name}')\n",
                    "\n",
                    "if verbose:\n",
                    "    print('Verbose mode enabled')\n",
                ],
            },
        ],
        "metadata": {
            "mcli": {
                ScriptMetadataKeys.DESCRIPTION: t.description,
                ScriptMetadataKeys.VERSION: t.version,
                ScriptMetadataKeys.GROUP: t.group,
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(notebook, indent=2)


# =============================================================================
# Editor Functions
# =============================================================================


def open_editor_for_script(
    script_path: Path,
    template_content: str,
    language: str,
) -> Optional[str]:
    """
    Open the user's default editor to write script code.

    Args:
        script_path: Target path for the script (used for display)
        template_content: Initial template to populate the editor
        language: Script language (determines file extension)

    Returns:
        Edited code content, or None if cancelled/failed
    """
    editor = _find_editor()
    if editor is None:
        click.echo(
            "No editor found. Please set the EDITOR environment variable or install vim/nano."
        )
        return None

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        click.echo(
            "Editor requires an interactive terminal. Use --template flag for non-interactive mode."
        )
        return None

    suffix = ScriptExtensions.BY_LANGUAGE.get(language, ".txt")

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


def _find_editor() -> Optional[str]:
    """Find an available text editor."""
    editor = os.environ.get("EDITOR")
    if editor:
        return editor

    for common_editor in ["vim", "nano", "code", "subl", "atom", "emacs"]:
        result = subprocess.run(["which", common_editor], capture_output=True)
        if result.returncode == 0:
            return common_editor

    return None


# =============================================================================
# File Operations
# =============================================================================


def save_script(
    workflows_dir: Path,
    name: str,
    code: str,
    language: str,
) -> Path:
    """
    Save script code to a file in the workflows directory.

    Args:
        workflows_dir: Directory to save the script
        name: Command name (used as filename)
        code: Script code content
        language: Script language (determines extension)

    Returns:
        Path to the saved script file
    """
    extension = ScriptExtensions.BY_LANGUAGE.get(language, ".txt")
    script_path = workflows_dir / f"{name}{extension}"

    workflows_dir.mkdir(parents=True, exist_ok=True)

    with open(script_path, "w") as f:
        f.write(code)

    # Make executable for shell/python scripts
    if language in (ScriptLanguages.PYTHON, ScriptLanguages.SHELL):
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)

    return script_path


# =============================================================================
# Main Command
# =============================================================================


@click.command("new")
@click.argument("command_name", required=False, default=None)
@click.option(
    "--language",
    "-l",
    type=click.Choice(ScriptLanguages.ALL, case_sensitive=False),
    help="Script language (auto-detected with --file)",
)
@click.option(
    "--group",
    default=ScriptMetadataDefaults.GROUP,
    help=f"Command group (default: '{ScriptMetadataDefaults.GROUP}')",
)
@click.option("--description", "-d", default="", help="Description for the command")
@click.option(
    "--version",
    "-v",
    "cmd_version",
    default=ScriptMetadataDefaults.VERSION,
    help=f"Initial version (default: '{ScriptMetadataDefaults.VERSION}')",
)
@click.option(
    "--template",
    "-t",
    is_flag=True,
    help="Use template mode (skip editor)",
)
@click.option(
    "--shell",
    "-s",
    type=click.Choice(ShellTypes.ALL, case_sensitive=False),
    help=f"Shell type for shell scripts (default: $SHELL or '{ShellTypes.DEFAULT}')",
)
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Add to global workflows (~/.mcli/workflows/)",
)
@click.option(
    "--file",
    "-f",
    "source_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Import an existing script file as an mcli command",
)
def new(
    command_name: Optional[str],
    language: Optional[str],
    group: str,
    description: str,
    cmd_version: str,
    template: bool,
    shell: Optional[str],
    is_global: bool,
    source_file: Optional[str],
) -> int:
    """
    Create a new workflow command as a native script file.

    When using --file, the command name is derived from the filename and the
    language is auto-detected from the file extension.

    Supported languages: python (.py), shell (.sh, .bash), javascript (.js),
    typescript (.ts), and ipynb (.ipynb).

    \b
    Examples:
        mcli new my_command -l python
        mcli new backup_db -l shell
        mcli new --file ./my_script.py
        mcli new --file ./backup.sh --group utils
        mcli new quick_cmd -l python -t
    """
    try:
        return _execute_new_command(
            command_name=command_name,
            language=language,
            group=group,
            description=description,
            cmd_version=cmd_version,
            template=template,
            shell=shell,
            is_global=is_global,
            source_file=source_file,
        )
    except (InvalidCommandNameError, InvalidGroupNameError, UnsupportedFileTypeError) as e:
        click.echo(f"Error: {e.message}", err=True)
        if e.details:
            click.echo(f"  {e.details}", err=True)
        return EXIT_ERROR


def _execute_new_command(
    command_name: Optional[str],
    language: Optional[str],
    group: str,
    description: str,
    cmd_version: str,
    template: bool,
    shell: Optional[str],
    is_global: bool,
    source_file: Optional[str],
) -> int:
    """
    Execute the new command logic.

    This is separated from the click command for easier testing and
    cleaner error handling.

    Returns:
        EXIT_SUCCESS (0) on success, EXIT_ERROR (1) on failure
    """
    # Handle --file mode
    if source_file:
        source_path = Path(source_file)
        detected_language = detect_language_from_file(source_path)

        language = language.lower() if language else detected_language

        if command_name is None:
            command_name = validate_command_name(source_path.stem)
        else:
            command_name = validate_command_name(command_name)

        console.print(f"[dim]Importing file: {source_path}[/dim]")
        console.print(f"[dim]Detected language: {language}[/dim]")
        console.print(f"[dim]Command name: {command_name}[/dim]")
    else:
        # Standard mode: require command_name and language
        if command_name is None:
            click.echo(
                "Error: Missing argument 'COMMAND_NAME'. Use --file to import an existing file.",
                err=True,
            )
            return EXIT_ERROR

        if language is None:
            click.echo(
                "Error: Missing option '--language' / '-l'. Use --file to auto-detect language.",
                err=True,
            )
            return EXIT_ERROR

        command_name = validate_command_name(command_name)
        language = language.lower()

    # Validate group
    command_group = validate_group_name(group)

    # Get workflows directory
    workflows_dir = get_custom_commands_dir(global_mode=is_global)

    # Check if command already exists
    extension = ScriptExtensions.BY_LANGUAGE.get(language, ".txt")
    script_path = workflows_dir / f"{command_name}{extension}"

    if script_path.exists():
        logger.warning(f"Script already exists: {script_path}")
        should_override = Prompt.ask(
            "Script already exists. Override?", choices=["y", "n"], default="n"
        )
        if should_override.lower() != "y":
            logger.info("Command creation aborted.")
            click.echo("Command creation aborted.")
            return EXIT_ERROR

    # Set default description
    if not description:
        description = f"{command_name.replace('_', ' ').title()} command"

    # Generate or restructure code
    if source_file:
        code = restructure_file_as_command(
            file_path=Path(source_file),
            name=command_name,
            description=description,
            group=command_group,
            version=cmd_version,
            language=language,
        )
        console.print("[dim]File restructured with mcli metadata[/dim]")
    else:
        code = _generate_or_edit_code(
            command_name=command_name,
            description=description,
            command_group=command_group,
            cmd_version=cmd_version,
            language=language,
            shell=shell,
            template=template,
            script_path=script_path,
        )
        if code is None:
            return EXIT_ERROR

    # Save the script
    saved_path = save_script(workflows_dir, command_name, code, language)

    # Update lockfile
    try:
        loader = ScriptLoader(workflows_dir)
        loader.save_lockfile()
    except Exception as e:
        logger.warning(f"Failed to update lockfile: {e}")

    # Display success message
    _display_success_message(
        command_name=command_name,
        language=language,
        shell=shell,
        saved_path=saved_path,
        command_group=command_group,
        is_global=is_global,
    )

    return EXIT_SUCCESS


def _generate_or_edit_code(
    command_name: str,
    description: str,
    command_group: str,
    cmd_version: str,
    language: str,
    shell: Optional[str],
    template: bool,
    script_path: Path,
) -> Optional[str]:
    """Generate template code and optionally open editor."""
    # Determine shell type
    if language == ScriptLanguages.SHELL and not shell:
        shell_env = os.environ.get("SHELL", ShellTypes.DEFAULT)
        shell = shell_env.split("/")[-1]
        click.echo(f"Using shell: {shell} (from $SHELL environment variable)")

    # Create template
    script_template = ScriptTemplate(
        name=command_name,
        description=description,
        group=command_group,
        version=cmd_version,
        language=language,
        shell=shell,
    )

    try:
        template_code = get_template(script_template)
    except UnsupportedLanguageError as e:
        click.echo(f"Error: {e.message}", err=True)
        return None

    if template:
        click.echo(f"Using {language} template for command: {command_name}")
        return template_code

    click.echo(f"Opening editor for {language} command: {command_name}")
    code = open_editor_for_script(script_path, template_code, language)
    if code is None:
        click.echo("Command creation cancelled.")
        return None

    return code


def _display_success_message(
    command_name: str,
    language: str,
    shell: Optional[str],
    saved_path: Path,
    command_group: str,
    is_global: bool,
) -> None:
    """Display success message after creating a command."""
    is_local = not is_global and is_git_repository()
    git_root = get_git_root() if is_local else None
    scope = "local" if is_local else "global"
    scope_display = f"[yellow]{scope}[/yellow]" if is_local else f"[cyan]{scope}[/cyan]"

    lang_display = language
    if language == ScriptLanguages.SHELL and shell:
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
