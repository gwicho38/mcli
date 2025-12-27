"""Top-level edit command for MCLI.

This module provides the `mcli edit` command for editing existing custom commands.
Supports both native script files (.py, .sh, .js, .ts, .ipynb) and legacy JSON files.
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import click
from rich.prompt import Prompt

from mcli.lib.constants import EditMessages, Editors
from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.ui.styling import console

logger = get_logger(__name__)
EM = EditMessages  # Short alias for cleaner code

# Supported native script extensions
NATIVE_SCRIPT_EXTENSIONS = [".py", ".sh", ".bash", ".js", ".ts", ".ipynb"]


def find_native_script(workflows_dir: Path, command_name: str) -> Path | None:
    """Find a native script file by command name."""
    for ext in NATIVE_SCRIPT_EXTENSIONS:
        script_path = workflows_dir / f"{command_name}{ext}"
        if script_path.exists():
            return script_path
    return None


@click.command("edit")
@click.argument("command_name")
@click.option("--editor", "-e", help="Editor to use (defaults to $EDITOR)")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Edit global command instead of local"
)
def edit(command_name, editor, is_global):
    """Edit a command interactively using $EDITOR.

    Opens the command's script file in your preferred editor.
    Supports both native scripts (.py, .sh, .js, .ts, .ipynb) and legacy JSON commands.

    Examples:
        mcli edit my-command            # Edit local command (if in git repo)
        mcli edit my-command --global   # Edit global command
        mcli edit my-command --editor code
    """
    # Determine editor
    if not editor:
        editor = os.environ.get("EDITOR", Editors.DEFAULT)

    # Get workflows directory
    workflows_dir = get_custom_commands_dir(global_mode=is_global)

    # First, try to find a native script file
    script_file = find_native_script(workflows_dir, command_name)

    if script_file:
        # Native script found - edit directly
        console.print(EM.OPENING_IN_EDITOR.format(editor=editor))
        logger.debug(EM.EDITING_NATIVE_SCRIPT.format(path=script_file))

        result = subprocess.run([editor, str(script_file)])  # nosec B603

        if result.returncode != 0:
            console.print(EM.EDITOR_EXIT_CODE.format(code=result.returncode))
        else:
            console.print(EM.EDITED_FILE.format(filename=script_file.name))

        return result.returncode

    # Fall back to legacy JSON command
    manager = get_command_manager(global_mode=is_global)
    command_file = manager.commands_dir / f"{command_name}.json"

    if not command_file.exists():
        console.print(EM.COMMAND_NOT_FOUND.format(name=command_name))
        console.print(EM.SEARCHED_IN.format(path=workflows_dir))
        console.print(EM.LOOKING_FOR_EXTENSIONS)
        return 1

    # Legacy JSON handling
    try:
        with open(command_file) as f:
            command_data = json.load(f)
    except Exception as e:
        console.print(EM.FAILED_TO_LOAD.format(error=e))
        return 1

    code = command_data.get("code", "")

    if not code:
        console.print(EM.NO_CODE.format(name=command_name))
        return 1

    console.print(EM.OPENING_IN_EDITOR.format(editor=editor))
    console.print(EM.LEGACY_JSON_NOTE)

    # Create temp file with the code
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix=f"{command_name}_"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # Open in editor
        result = subprocess.run([editor, tmp_path])  # nosec B603

        if result.returncode != 0:
            console.print(EM.EDITOR_EXIT_CODE.format(code=result.returncode))

        # Read edited content
        with open(tmp_path) as f:
            new_code = f.read()

        # Check if code changed
        if new_code.strip() == code.strip():
            console.print(EM.NO_CHANGES)
            return 0

        # Validate syntax
        try:
            compile(new_code, "<string>", "exec")
        except SyntaxError as e:
            console.print(EM.SYNTAX_ERROR.format(error=e))
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

        console.print(EM.UPDATED_COMMAND.format(name=command_name))
        console.print(EM.SAVED_TO.format(path=command_file))
        console.print(EM.RELOAD_HINT)

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return 0
