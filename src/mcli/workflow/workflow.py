"""
Workflows command group for mcli.

All workflow commands are now loaded from portable JSON files in ~/.mcli/workflows/
This provides a clean, maintainable way to manage workflow commands.
"""

import click


class ScopedWorkflowsGroup(click.Group):
    """
    Custom Click Group that loads workflows from either local or global scope
    based on the -g/--global flag.
    """

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

        # Filter to only workflow group commands AND validate they can be loaded
        workflow_commands = []
        for cmd_data in commands:
            if cmd_data.get("group") != "workflow":
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

        return sorted(set(workflow_commands + builtin_commands))

    def get_command(self, ctx, cmd_name):
        """Get a command by name, loading from appropriate scope."""
        # First check if it's a built-in command
        builtin_cmd = super().get_command(ctx, cmd_name)
        if builtin_cmd:
            return builtin_cmd

        # Get scope from context
        is_global = ctx.params.get("is_global", False)

        # Load the workflow command from appropriate directory
        from mcli.lib.custom_commands import get_command_manager

        manager = get_command_manager(global_mode=is_global)
        commands = manager.load_all_commands()

        # Find the workflow command
        for command_data in commands:
            if command_data.get("name") == cmd_name and command_data.get("group") == "workflow":
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
