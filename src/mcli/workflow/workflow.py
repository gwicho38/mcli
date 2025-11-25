"""
Workflows command group for mcli.

All workflow commands are now loaded from portable JSON files in ~/.mcli/workflows/
This provides a clean, maintainable way to manage workflow commands.
"""

from pathlib import Path

import click
from click.shell_completion import CompletionItem


class ScopedWorkflowsGroup(click.Group):
    """
    Custom Click Group that loads workflows from either local or global scope
    based on the -g/--global flag.
    """

    def shell_complete(self, ctx, incomplete):
        """
        Provide shell completion for workflow commands and file paths.

        Supports:
        - Workflow command names (from JSON/notebook files)
        - File paths (when incomplete starts with ./ or /)
        - Built-in subcommands
        """
        from mcli.lib.logger.logger import get_logger

        logger = get_logger()

        # If incomplete looks like a file path, provide file completions
        if incomplete.startswith("./") or incomplete.startswith("/") or incomplete.startswith("~"):
            logger.debug(f"Providing file path completions for: {incomplete}")
            completions = []

            try:
                # Expand user home directory
                incomplete_path = incomplete
                if incomplete_path.startswith("~"):
                    incomplete_path = str(Path(incomplete_path).expanduser())

                # Get the directory and partial filename
                # Special case: if incomplete ends with "/", we're listing directory contents
                if incomplete_path.endswith("/"):
                    dir_path = Path(incomplete_path)
                    partial_name = ""
                elif "/" in incomplete_path:
                    # Contains a path separator - split into directory and partial filename
                    # Split on the last slash to get directory and partial filename
                    last_slash = incomplete_path.rfind("/")
                    dir_str = incomplete_path[: last_slash + 1] if last_slash >= 0 else "./"
                    partial_name = (
                        incomplete_path[last_slash + 1 :] if last_slash >= 0 else incomplete_path
                    )
                    dir_path = Path(dir_str)
                else:
                    # No slash - shouldn't happen for file path completion but handle it
                    dir_path = Path.cwd()
                    partial_name = incomplete_path

                # Resolve the directory path
                if not dir_path.is_absolute():
                    dir_path = Path.cwd() / dir_path

                # If directory doesn't exist yet, try parent
                if not dir_path.exists():
                    partial_name = dir_path.name
                    dir_path = dir_path.parent

                # List files/directories that match
                if dir_path.exists() and dir_path.is_dir():
                    for item in sorted(dir_path.iterdir()):
                        # Skip hidden files unless explicitly requested
                        if item.name.startswith(".") and not partial_name.startswith("."):
                            continue

                        # Check if item matches partial name
                        if not partial_name or item.name.startswith(partial_name):
                            # Use relative path if original was relative
                            if incomplete.startswith("./"):
                                try:
                                    rel_path = item.relative_to(Path.cwd())
                                    completion_path = f"./{rel_path}"
                                except ValueError:
                                    # If item is not relative to cwd, use absolute path
                                    completion_path = str(item)
                            else:
                                completion_path = str(item)

                            # Add trailing slash for directories
                            if item.is_dir():
                                completion_path += "/"

                            completions.append(CompletionItem(completion_path))
                            logger.debug(f"Added file completion: {completion_path}")

            except Exception as e:
                logger.debug(f"Error providing file completions: {e}")
                import traceback

                logger.debug(traceback.format_exc())

            return completions

        # Otherwise, provide workflow command completions
        commands = self.list_commands(ctx)
        return [CompletionItem(name) for name in commands if name.startswith(incomplete)]

    def list_commands(self, ctx):
        """List available commands based on scope."""
        # Get scope from context
        is_global = ctx.params.get("is_global", False)

        # Load commands from appropriate directory
        from mcli.lib.custom_commands import get_command_manager
        from mcli.lib.logger.logger import get_logger

        logger = get_logger()
        manager = get_command_manager(global_mode=is_global)
        commands = manager.load_all_commands()

        # Filter to only workflow/workflows group commands AND validate they can be loaded
        workflow_commands = []
        for cmd_data in commands:
            # Accept both "workflow" and "workflows" for backward compatibility
            if cmd_data.get("group") not in ["workflow", "workflows"]:
                continue

            cmd_name = cmd_data.get("name")
            # Validate the command can be loaded
            temp_group = click.Group()
            language = cmd_data.get("language", "python")

            try:
                if language == "shell":
                    success = manager.register_shell_command_with_click(cmd_data, temp_group)
                else:
                    success = manager.register_command_with_click(cmd_data, temp_group)

                if success and temp_group.commands.get(cmd_name):
                    workflow_commands.append(cmd_name)
                else:
                    # Log the issue but don't show to user during list (too noisy)
                    logger.debug(
                        f"Workflow '{cmd_name}' has invalid code and will not be loaded. "
                        f"Edit with: mcli workflow edit {cmd_name}"
                    )
            except Exception as e:
                # Log the issue but don't show to user during list (too noisy)
                logger.debug(
                    f"Failed to load workflow '{cmd_name}': {e}. "
                    f"Edit with: mcli workflow edit {cmd_name}"
                )

        # Also include built-in subcommands
        builtin_commands = list(super().list_commands(ctx))

        # Auto-detect project-level workflows (Makefile, package.json)
        auto_detected_commands = []

        # Only auto-detect for local (non-global) workflows
        if not is_global:
            from pathlib import Path

            from mcli.lib.makefile_workflows import find_makefile
            from mcli.lib.packagejson_workflows import find_package_json

            # Check for Makefile
            if find_makefile(Path.cwd()):
                auto_detected_commands.append("make")
                logger.debug("Auto-detected Makefile in current directory")

            # Check for package.json
            if find_package_json(Path.cwd()):
                auto_detected_commands.append("npm")
                logger.debug("Auto-detected package.json in current directory")

        # Discover notebook files (.ipynb) and add as command groups
        notebook_commands = []
        commands_dir = manager.commands_dir
        if commands_dir.exists():
            for notebook_file in commands_dir.rglob("*.ipynb"):
                # Skip hidden files/directories (but not parent directories like .mcli)
                relative_parts = notebook_file.relative_to(commands_dir).parts
                if any(part.startswith(".") for part in relative_parts):
                    continue

                # Get command name from file stem
                cmd_name = notebook_file.stem
                notebook_commands.append(cmd_name)
                logger.debug(f"Discovered notebook: {cmd_name} from {notebook_file}")

        return sorted(
            set(workflow_commands + builtin_commands + auto_detected_commands + notebook_commands)
        )

    def _create_file_command(self, file_path, ctx):
        """
        Create a Click command to execute a file directly.

        Supports:
        - Python scripts (.py)
        - Shell scripts (.sh, .bash, .zsh)
        - Jupyter notebooks (.ipynb)
        - Any executable file

        Args:
            file_path: Path to the file to execute
            ctx: Click context

        Returns:
            Click Command or Group
        """
        from pathlib import Path

        from mcli.lib.logger.logger import get_logger

        logger = get_logger()
        file_path = Path(file_path).resolve()
        extension = file_path.suffix.lower()

        logger.debug(f"Creating command for file: {file_path}")

        # Handle Jupyter notebooks
        if extension == ".ipynb":
            from mcli.lib.custom_commands import get_command_manager

            is_global = ctx.params.get("is_global", False)
            manager = get_command_manager(global_mode=is_global)

            logger.info(f"Loading notebook from file: {file_path}")
            temp_group = click.Group()
            if manager.register_notebook_command_with_click(file_path, temp_group):
                # Return the notebook group
                return temp_group.commands.get(file_path.stem)

            logger.warning(f"Failed to load notebook: {file_path}")
            return None

        # Handle Python scripts
        if extension == ".py":

            @click.command(name=file_path.stem)
            @click.argument("args", nargs=-1, type=click.UNPROCESSED)
            def python_command(args):
                """Execute Python script"""
                import subprocess

                cmd = ["python", str(file_path)] + list(args)
                logger.info(f"Executing: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=False)
                if result.returncode != 0:
                    raise SystemExit(result.returncode)

            return python_command

        # Handle shell scripts
        if extension in [".sh", ".bash", ".zsh", ""]:
            # Check if file is executable
            if not file_path.stat().st_mode & 0o111:
                logger.warning(f"File is not executable: {file_path}")
                # Make it executable
                file_path.chmod(file_path.stat().st_mode | 0o111)

            @click.command(name=file_path.stem)
            @click.argument("args", nargs=-1, type=click.UNPROCESSED)
            def shell_command(args):
                """Execute shell script"""
                import subprocess

                cmd = [str(file_path)] + list(args)
                logger.info(f"Executing: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=False)
                if result.returncode != 0:
                    raise SystemExit(result.returncode)

            return shell_command

        # Generic executable fallback
        if file_path.stat().st_mode & 0o111:

            @click.command(name=file_path.stem)
            @click.argument("args", nargs=-1, type=click.UNPROCESSED)
            def generic_command(args):
                """Execute file"""
                import subprocess

                cmd = [str(file_path)] + list(args)
                logger.info(f"Executing: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=False)
                if result.returncode != 0:
                    raise SystemExit(result.returncode)

            return generic_command

        # Unsupported file type
        logger.error(f"Unsupported file type: {extension}")
        return None

    def get_command(self, ctx, cmd_name):
        """Get a command by name, loading from appropriate scope."""
        # First check if it's a built-in command
        builtin_cmd = super().get_command(ctx, cmd_name)
        if builtin_cmd:
            return builtin_cmd

        # Check if cmd_name is a file path that exists
        from pathlib import Path

        potential_file = Path(cmd_name)
        if potential_file.exists() and potential_file.is_file():
            # File exists - execute it directly
            return self._create_file_command(potential_file, ctx)

        # Get scope from context
        is_global = ctx.params.get("is_global", False)

        # Check for auto-detected project workflows (only for local mode)
        if not is_global:
            from pathlib import Path

            # Check for Makefile workflows
            if cmd_name == "make":
                from mcli.lib.makefile_workflows import load_makefile_workflow

                make_group = load_makefile_workflow(Path.cwd())
                if make_group:
                    return make_group

            # Check for package.json workflows
            if cmd_name == "npm":
                from mcli.lib.packagejson_workflows import load_package_json_workflow

                npm_group = load_package_json_workflow(Path.cwd())
                if npm_group:
                    return npm_group

        # Load the workflow command from appropriate directory
        from mcli.lib.custom_commands import get_command_manager
        from mcli.lib.logger.logger import get_logger

        logger = get_logger()
        manager = get_command_manager(global_mode=is_global)

        # First, check if there's a notebook file with this name
        commands_dir = manager.commands_dir
        if commands_dir.exists():
            for notebook_file in commands_dir.rglob("*.ipynb"):
                # Skip hidden files/directories (but not parent directories like .mcli)
                relative_parts = notebook_file.relative_to(commands_dir).parts
                if any(part.startswith(".") for part in relative_parts):
                    continue

                if notebook_file.stem == cmd_name:
                    # Found matching notebook - load it as a command group
                    logger.debug(f"Loading notebook commands from {notebook_file}")
                    temp_group = click.Group()
                    if manager.register_notebook_command_with_click(notebook_file, temp_group):
                        return temp_group.commands.get(cmd_name)

        # Then check regular JSON workflow commands
        commands = manager.load_all_commands()

        # Find the workflow command
        for command_data in commands:
            # Accept both "workflow" and "workflows" for backward compatibility
            if command_data.get("name") == cmd_name and command_data.get("group") in [
                "workflow",
                "workflows",
            ]:
                # Create a temporary group to register the command
                temp_group = click.Group()
                language = command_data.get("language", "python")

                if language == "shell":
                    manager.register_shell_command_with_click(command_data, temp_group)
                else:
                    manager.register_command_with_click(command_data, temp_group)

                return temp_group.commands.get(cmd_name)

        return None


@click.group(name="workflows", cls=ScopedWorkflowsGroup, invoke_without_command=True)
@click.option(
    "-g",
    "--global",
    "is_global",
    is_flag=True,
    help="Execute workflows from global directory (~/.mcli/workflows/) instead of local (.mcli/workflows/)",
)
@click.pass_context
def workflows(ctx, is_global):
    """Runnable workflows for automation, video processing, and daemon management

    Examples:
        mcli workflows my-workflow              # Execute local workflow (if in git repo)
        mcli workflows -g my-workflow           # Execute global workflow
        mcli workflows --global another-workflow # Execute global workflow

    Alias: You can also use 'mcli run' as a shorthand for 'mcli workflows'
    """
    # Store the is_global flag in the context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj["is_global"] = is_global

    # If a subcommand was invoked, the subcommand will handle execution
    if ctx.invoked_subcommand:
        return

    # If no subcommand, show help
    click.echo(ctx.get_help())


# Add secrets workflow
try:
    from mcli.workflow.secrets.secrets_cmd import secrets

    workflows.add_command(secrets)
except ImportError as e:
    # Secrets workflow not available
    import sys

    from mcli.lib.logger.logger import get_logger

    logger = get_logger()
    logger.debug(f"Secrets workflow not available: {e}")

# Add notebook subcommand
try:
    from mcli.workflow.notebook.notebook_cmd import notebook

    workflows.add_command(notebook)
except ImportError as e:
    # Notebook commands not available
    import sys

    from mcli.lib.logger.logger import get_logger

    logger = get_logger()
    logger.debug(f"Notebook commands not available: {e}")

# Add sync subcommand
try:
    from mcli.workflow.sync_cmd import sync_group

    workflows.add_command(sync_group)
except ImportError as e:
    # Sync commands not available

    from mcli.lib.logger.logger import get_logger

    logger = get_logger()
    logger.debug(f"Sync commands not available: {e}")


# For backward compatibility, keep workflow as an alias
workflow = workflows

# Add 'run' as a convenient alias for workflows
run = workflows

if __name__ == "__main__":
    workflows()
