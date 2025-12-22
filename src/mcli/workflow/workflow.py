"""
Workflows command group for mcli.

Workflow scripts are loaded from:
- Native script files (.py, .sh, .js, .ts, .ipynb) in ~/.mcli/workflows/ or .mcli/workflows/
- Legacy JSON files (deprecated, use `mcli workflow migrate` to convert)

This provides a clean, maintainable way to manage workflow commands.
"""

import click


class ScopedWorkflowsGroup(click.Group):
    """
    Custom Click Group that loads workflows from either local or global scope
    based on the -g/--global flag, or from a specific workspace via -f/--workspace.

    Supports:
    - Native script files (.py, .sh, .js, .ts, .ipynb) via ScriptLoader
    - Legacy JSON files via CustomCommandManager (deprecated)
    - Auto-detected project workflows (Makefile, package.json)
    - Custom workspace paths via -f/--workspace
    """

    def _get_workflows_dir(self, ctx):
        """Get the workflows directory based on context parameters."""
        from mcli.lib.paths import get_custom_commands_dir, resolve_workspace

        # Check for workspace flag first (takes precedence)
        workspace = ctx.params.get("workspace")
        if workspace:
            resolved = resolve_workspace(workspace)
            if resolved:
                return resolved
            # If workspace specified but not found, return None to indicate error
            return None

        # Fall back to global/local scope
        is_global = ctx.params.get("is_global", False)
        return get_custom_commands_dir(global_mode=is_global)

    def list_commands(self, ctx):
        """List available commands based on scope."""
        from pathlib import Path

        from mcli.lib.logger.logger import get_logger
        from mcli.lib.script_loader import ScriptLoader

        logger = get_logger()

        # Get scope from context
        is_global = ctx.params.get("is_global", False)
        workspace = ctx.params.get("workspace")

        # Get workflows directory
        workflows_dir = self._get_workflows_dir(ctx)

        if workflows_dir is None:
            logger.warning(f"Workspace not found: {workspace}")
            return []

        # Load native script commands
        script_commands = []
        if workflows_dir.exists():
            loader = ScriptLoader(workflows_dir)
            scripts = loader.discover_scripts()

            for script_path in scripts:
                name = script_path.stem
                # Validate the command can be loaded
                try:
                    command = loader.load_command(script_path)
                    if command:
                        script_commands.append(name)
                    else:
                        logger.debug(f"Script '{name}' could not be loaded as a command")
                except Exception as e:
                    logger.debug(f"Failed to load script '{name}': {e}")

        # Load legacy JSON commands (for backward compatibility)
        legacy_commands = []
        try:
            from mcli.lib.custom_commands import get_command_manager

            manager = get_command_manager(global_mode=is_global)
            json_commands = manager.load_all_commands()

            for cmd_data in json_commands:
                # Accept both "workflow" and "workflows" for backward compatibility
                if cmd_data.get("group") not in ["workflow", "workflows"]:
                    continue

                cmd_name = cmd_data.get("name")
                # Skip if already loaded as native script
                if cmd_name in script_commands:
                    continue

                # Validate the command can be loaded
                temp_group = click.Group()
                language = cmd_data.get("language", "python")

                try:
                    if language == "shell":
                        success = manager.register_shell_command_with_click(cmd_data, temp_group)
                    else:
                        success = manager.register_command_with_click(cmd_data, temp_group)

                    if success and temp_group.commands.get(cmd_name):
                        legacy_commands.append(cmd_name)
                except Exception as e:
                    logger.debug(f"Failed to load legacy workflow '{cmd_name}': {e}")
        except Exception as e:
            logger.debug(f"Could not load legacy JSON commands: {e}")

        # Also include built-in subcommands
        builtin_commands = list(super().list_commands(ctx))

        # Auto-detect project-level workflows (Makefile, package.json)
        auto_detected_commands = []

        # Only auto-detect for local (non-global) workflows
        if not is_global:
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

        return sorted(
            set(script_commands + legacy_commands + builtin_commands + auto_detected_commands)
        )

    def get_command(self, ctx, cmd_name):
        """Get a command by name, loading from appropriate scope."""
        from pathlib import Path

        from mcli.lib.logger.logger import get_logger
        from mcli.lib.script_loader import ScriptLoader

        logger = get_logger()

        # First check if it's a built-in command
        builtin_cmd = super().get_command(ctx, cmd_name)
        if builtin_cmd:
            return builtin_cmd

        # Get scope from context
        is_global = ctx.params.get("is_global", False)
        workspace = ctx.params.get("workspace")

        # Check for auto-detected project workflows (only for local mode without workspace)
        if not is_global and not workspace:
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

        # Get workflows directory
        workflows_dir = self._get_workflows_dir(ctx)

        if workflows_dir is None:
            logger.warning(f"Workspace not found: {workspace}")
            return None

        # Try to load as native script first
        if workflows_dir.exists():
            loader = ScriptLoader(workflows_dir)
            scripts = loader.discover_scripts()

            # Find matching script
            for script_path in scripts:
                if script_path.stem == cmd_name:
                    try:
                        command = loader.load_command(script_path)
                        if command:
                            logger.debug(f"Loaded native script command: {cmd_name}")
                            return command
                    except Exception as e:
                        logger.debug(f"Failed to load script '{cmd_name}': {e}")
                    break

        # Fall back to legacy JSON commands
        try:
            from mcli.lib.custom_commands import get_command_manager

            manager = get_command_manager(global_mode=is_global)
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

                    cmd = temp_group.commands.get(cmd_name)
                    if cmd:
                        logger.debug(f"Loaded legacy JSON command: {cmd_name}")
                        return cmd
        except Exception as e:
            logger.debug(f"Could not load legacy command '{cmd_name}': {e}")

        return None


@click.group(name="workflows", cls=ScopedWorkflowsGroup, invoke_without_command=True)
@click.option(
    "-g",
    "--global",
    "is_global",
    is_flag=True,
    help="Execute workflows from global directory (~/.mcli/workflows/) instead of local (.mcli/workflows/)",
)
@click.option(
    "-f",
    "--workspace",
    "workspace",
    type=str,
    help="Execute workflows from a specific workspace (directory or config file path)",
)
@click.pass_context
def workflows(ctx, is_global, workspace):
    """Runnable workflows for automation, video processing, and daemon management

    Examples:
        mcli run my-workflow              # Execute local workflow (if in git repo)
        mcli run -g my-workflow           # Execute global workflow
        mcli run -f ~/projects/myapp my-workflow  # Execute from specific workspace

    Alias: You can also use 'mcli workflows' as an alias for 'mcli run'
    """
    from mcli.lib.paths import resolve_workspace
    from mcli.lib.ui.styling import error

    # Validate that -g and -f are mutually exclusive
    if is_global and workspace:
        error("Cannot use both --global and --workspace flags together")
        ctx.exit(1)

    # Validate workspace exists if specified
    if workspace:
        resolved = resolve_workspace(workspace)
        if resolved is None:
            error(f"Workspace not found: {workspace}")
            ctx.exit(1)

    # Store flags in the context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj["is_global"] = is_global
    ctx.obj["workspace"] = workspace

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

# Note: sync is now a top-level command (mcli sync)

# Add storage subcommand (Storacha/IPFS)
try:
    from mcli.workflow.storage.storage_cmd import storage

    workflows.add_command(storage)
except ImportError as e:
    from mcli.lib.logger.logger import get_logger

    logger = get_logger()
    logger.debug(f"Storage commands not available: {e}")


# For backward compatibility, keep workflow as an alias
workflow = workflows

# Add 'run' as a convenient alias for workflows
run = workflows

if __name__ == "__main__":
    workflows()
