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
        """List available commands based on scope.

        When multiple scripts share a stem (e.g. backup.py and backup.sh),
        emits suffixed names like backup:py and backup:sh so that tab completion
        offers distinct entries for each language variant.
        """

        from collections import Counter

        from mcli.lib.logger.logger import get_logger
        from mcli.lib.script_loader import LANGUAGE_TO_SUFFIX, ScriptLoader

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
        script_stems = set()
        if workflows_dir.exists():
            loader = ScriptLoader(workflows_dir)
            scripts = loader.discover_scripts()

            # Count how many scripts share each stem
            stem_counts = Counter(sp.stem for sp in scripts)

            for script_path in scripts:
                name = script_path.stem
                try:
                    command = loader.load_command(script_path)
                    if command:
                        if stem_counts[name] > 1:
                            lang = loader.detect_language(script_path)
                            suffix = LANGUAGE_TO_SUFFIX.get(lang, script_path.suffix.lstrip("."))
                            script_commands.append(f"{name}:{suffix}")
                        else:
                            script_commands.append(name)
                        script_stems.add(name)
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
                if cmd_name in script_stems:
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

        # Only return user-defined workflows (scripts + legacy JSON)
        return sorted(set(script_commands + legacy_commands))

    def get_command(self, ctx, cmd_name):
        """Get a command by name, loading from appropriate scope.

        Supports language suffix disambiguation: 'backup:py' loads the Python
        version, 'backup:sh' loads the shell version. Bare names work when
        unambiguous; when ambiguous, a warning is shown and the first match runs.
        """
        from mcli.lib.constants.messages import WarningMessages
        from mcli.lib.logger.logger import get_logger
        from mcli.lib.script_loader import LANGUAGE_TO_SUFFIX, ScriptLoader, parse_command_name

        logger = get_logger()

        # Get scope from context
        is_global = ctx.params.get("is_global", False)
        workspace = ctx.params.get("workspace")

        # Get workflows directory
        workflows_dir = self._get_workflows_dir(ctx)

        if workflows_dir is None:
            logger.warning(f"Workspace not found: {workspace}")
            return None

        # Parse language suffix (e.g. "backup:py" → base="backup", lang="python")
        base_name, lang_filter = parse_command_name(cmd_name)

        # Try to load as native script first
        if workflows_dir.exists():
            loader = ScriptLoader(workflows_dir)
            matches = loader.find_scripts_by_stem(base_name)

            if lang_filter:
                # Filter to requested language
                matches = [p for p in matches if loader.detect_language(p) == lang_filter]

            if len(matches) == 1:
                try:
                    command = loader.load_command(matches[0])
                    if command:
                        logger.debug(f"Loaded native script command: {cmd_name}")
                        return command
                except Exception as e:
                    logger.debug(f"Failed to load script '{cmd_name}': {e}")
            elif len(matches) > 1 and not lang_filter:
                # Ambiguous — show hint, pick first
                from mcli.lib.ui.styling import warning

                suffixes = [LANGUAGE_TO_SUFFIX.get(loader.detect_language(p), "?") for p in matches]
                options = ", ".join(f"{base_name}:{s}" for s in suffixes)
                warning(WarningMessages.AMBIGUOUS_COMMAND.format(name=base_name, options=options))
                try:
                    command = loader.load_command(matches[0])
                    if command:
                        logger.debug(f"Loaded first match for ambiguous command: {base_name}")
                        return command
                except Exception as e:
                    logger.debug(f"Failed to load script '{base_name}': {e}")

        # Fall back to legacy JSON commands (use base_name for lookup)
        lookup_name = base_name if lang_filter else cmd_name
        try:
            from mcli.lib.custom_commands import get_command_manager

            manager = get_command_manager(global_mode=is_global)
            commands = manager.load_all_commands()

            # Find the workflow command
            for command_data in commands:
                # Accept both "workflow" and "workflows" for backward compatibility
                if command_data.get("name") == lookup_name and command_data.get("group") in [
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

                    cmd = temp_group.commands.get(lookup_name)
                    if cmd:
                        logger.debug(f"Loaded legacy JSON command: {lookup_name}")
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
    """▶️ Run workflows for automation, video processing, and daemon management

    Examples:
        mcli run my-workflow              # Execute local workflow (if in git repo)
        mcli run -g my-workflow           # Execute global workflow
        mcli run -f ~/projects/myapp my-workflow  # Execute from specific workspace
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


# For backward compatibility, keep workflow as an alias
workflow = workflows

# Add 'run' as a convenient alias for workflows
run = workflows

if __name__ == "__main__":
    workflows()
