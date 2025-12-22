import importlib
import os
from pathlib import Path
from typing import List, Optional

import click
import tomli

from mcli.lib.api.api import register_command_as_api
from mcli.lib.logger.logger import disable_runtime_tracing, enable_runtime_tracing, get_logger

# Defer performance optimizations until needed
_optimization_results = None

# Defer API imports until needed

# Get logger
logger = get_logger(__name__)

# Enable runtime tracing if environment variable is set
trace_level = os.environ.get("MCLI_TRACE_LEVEL")
if trace_level:
    try:
        # Convert to integer (1=function calls, 2=line by line, 3=verbose)
        level = int(trace_level)
        enable_runtime_tracing(level=level)
        logger.info(f"Runtime tracing enabled with level {level}")
    except ValueError:
        logger.warning(f"Invalid MCLI_TRACE_LEVEL value: {trace_level}. Using default level 1.")
        enable_runtime_tracing(level=1)

# Defer self management commands import

logger.debug("main")


def discover_modules(base_path: Path, config_path: Optional[Path] = None) -> list[str]:
    """
    Discovers Python modules in specified paths.
    Paths must omit trailing backslash.
    """
    modules = []

    # Try different config file locations
    if config_path is None:
        # Try local config.toml first
        config_paths = [
            Path("config.toml"),  # Current directory
            base_path / "config.toml",  # mcli directory
            base_path.parent.parent / "config.toml",  # Repository root
        ]
        logger.info(f"Config paths: {config_paths}")

        for path in config_paths:
            if path.exists():
                config_path = path
                break
        else:
            # No config file found, use default
            logger.warning("No config file found, using default configuration")
            config_path = None

    # Read the TOML configuration file or use default
    logger.info(f"Config path: {config_path.exists() if config_path else 'None'}")
    if config_path and config_path.exists():
        try:
            with open(config_path, "rb") as f:
                config = tomli.load(f)
                logger.debug(f"Config loaded: {config}")
            logger.debug(f"Using config from {config_path}")
        except Exception as e:
            logger.warning(f"Error reading config file {config_path}: {e}")
            config = {"paths": {"included_dirs": ["app", "self", "workflow", "public"]}}
    else:
        logger.warning("Config file not found, using default configuration")
        config = {"paths": {"included_dirs": ["app", "self", "workflow", "public"]}}
    excluded_files = {"setup.py", "__init__.py"}
    excluded_dirs = {"resources", "models", "scripts", "private", "venv", ".venv", "__pycache__"}

    included_dirs = config.get("paths", {}).get("included_dirs", [])

    logger.debug(f"Included directories: {included_dirs}")
    for directory in included_dirs:
        # Handle nested paths like "app/foo"
        if "/" in directory:
            parts = directory.split("/")
            parent_dir = parts[0]
            sub_dir = "/".join(parts[1:])
            search_path = base_path / parent_dir / sub_dir
            logger.debug(f"Searching in nested path: {search_path}")

            if search_path.exists():
                for file_path in search_path.rglob("*.py"):
                    if file_path.name not in excluded_files and not any(
                        excluded_dir in file_path.parts for excluded_dir in excluded_dirs
                    ):
                        # Convert file path to module name with mcli prefix
                        relative_path = file_path.relative_to(base_path.parent)
                        module_name = str(relative_path).replace("/", ".").replace(".py", "")

                        # Skip individual workflow submodules to avoid duplicate commands
                        if (
                            module_name.startswith("mcli.workflow.")
                            and module_name != "mcli.workflow.workflow"
                        ):
                            # Skip individual workflow submodules (e.g., mcli.workflow.daemon.daemon)
                            # Only include the main workflow module
                            continue

                        modules.append(module_name)
                        logger.debug(f"Found nested module: {module_name}")
        else:
            search_path = base_path / directory
            logger.debug(f"Searching in path: {search_path}")

            if search_path.exists():
                for file_path in search_path.rglob("*.py"):
                    if file_path.name not in excluded_files and not any(
                        excluded_dir in file_path.parts for excluded_dir in excluded_dirs
                    ):
                        # Convert file path to module name with mcli prefix
                        relative_path = file_path.relative_to(base_path.parent)
                        module_name = str(relative_path).replace("/", ".").replace(".py", "")

                        # Skip individual workflow submodules to avoid duplicate commands
                        if (
                            module_name.startswith("mcli.workflow.")
                            and module_name != "mcli.workflow.workflow"
                        ):
                            # Skip individual workflow submodules (e.g., mcli.workflow.daemon.daemon)
                            # Only include the main workflow module
                            continue

                        modules.append(module_name)
                        logger.debug(f"Found module: {module_name}")

    logger.info(f"Discovered {len(modules)} modules")
    return modules


def register_command_as_api_endpoint(command_func, module_name: str, command_name: str):
    """
    Register a Click command as an API endpoint.

    Args:
        command_func: The Click command function
        module_name: The module name for grouping
        command_name: The command name
    """
    try:
        # Create endpoint path based on module and command
        endpoint_path = f"/{module_name.replace('.', '/')}/{command_name}"

        logger.info(f"Registering API endpoint: {endpoint_path} for command {command_name}")
        logger.info(f"Command function: {command_func.__name__}")

        # Register the command as an API endpoint
        register_command_as_api(
            command_func=command_func,
            endpoint_path=endpoint_path,
            http_method="POST",
            description=f"API endpoint for {command_name} command from {module_name}",
            tags=[module_name.split(".")[-1]],  # Use last part of module name as tag
        )

        logger.debug(f"Registered API endpoint: {endpoint_path} for command {command_name}")

    except Exception as e:
        logger.warning(f"Failed to register API endpoint for {command_name}: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")


def process_click_commands(obj, module_name: str, parent_name: str = ""):
    """
    Recursively process Click commands and groups to register them as API endpoints.

    Args:
        obj: Click command or group object
        module_name: The module name
        parent_name: Parent command name for nesting
    """
    logger.info(
        f"Processing Click object: {type(obj).__name__} with name: {getattr(obj, 'name', 'Unknown')}"
    )

    if hasattr(obj, "commands"):
        # This is a Click group
        logger.info(f"This is a Click group with {len(obj.commands)} commands")
        for name, command in obj.commands.items():
            full_name = f"{parent_name}/{name}" if parent_name else name
            logger.info(f"Processing command: {name} -> {full_name}")

            # Register the command as an API endpoint
            register_command_as_api_endpoint(command.callback, module_name, full_name)

            # Recursively process nested commands
            if hasattr(command, "commands"):
                logger.info(f"Recursively processing nested commands for {name}")
                process_click_commands(command, module_name, full_name)
    else:
        # This is a single command
        logger.info(f"This is a single command: {getattr(obj, 'name', 'Unknown')}")
        if hasattr(obj, "callback") and obj.callback:
            full_name = parent_name if parent_name else obj.name
            logger.info(f"Registering single command: {full_name}")
            register_command_as_api_endpoint(obj.callback, module_name, full_name)


class LazyCommand(click.Command):
    """A Click command that loads its implementation lazily."""

    def __init__(self, name, import_path, *args, **kwargs):
        self.import_path = import_path
        self._loaded_command = None
        super().__init__(name, *args, **kwargs)

    def _load_command(self):
        """Load the actual command on first use."""
        if self._loaded_command is None:
            try:
                module_path, attr_name = self.import_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                self._loaded_command = getattr(module, attr_name)
                logger.debug(f"Lazily loaded command: {self.name}")
            except Exception as e:
                logger.error(f"Failed to load command {self.name}: {e}")

                # Return a dummy command that shows an error
                def error_callback():
                    click.echo(f"Error: Command {self.name} is not available")

                self._loaded_command = click.Command(self.name, callback=error_callback)
        return self._loaded_command

    def invoke(self, ctx):
        """Invoke the lazily loaded command."""
        cmd = self._load_command()
        return cmd.invoke(ctx)

    def get_params(self, ctx):
        """Get parameters from the lazily loaded command."""
        cmd = self._load_command()
        return cmd.get_params(ctx)

    def shell_complete(self, ctx, param, incomplete):
        """Provide shell completion for the lazily loaded command."""
        cmd = self._load_command()
        # Delegate to the loaded command's completion
        if hasattr(cmd, "shell_complete"):
            return cmd.shell_complete(ctx, param, incomplete)
        # Fallback to default Click completion
        return (
            super().shell_complete(ctx, param, incomplete)
            if hasattr(super(), "shell_complete")
            else []
        )


class LazyGroup(click.Group):
    """A Click group that loads its implementation lazily."""

    def __init__(self, name, import_path, *args, **kwargs):
        self.import_path = import_path
        self._loaded_group = None
        super().__init__(name, *args, **kwargs)

    def _load_group(self):
        """Load the actual group on first use."""
        if self._loaded_group is None:
            try:
                module_path, attr_name = self.import_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                self._loaded_group = getattr(module, attr_name)
                logger.debug(f"Lazily loaded group: {self.name}")
            except Exception as e:
                logger.error(f"Failed to load group {self.name}: {e}")

                # Return a dummy group that shows an error
                def error_callback():
                    click.echo(f"Error: Command group {self.name} is not available")

                self._loaded_group = click.Group(self.name, callback=error_callback)
        return self._loaded_group

    def invoke(self, ctx):
        """Invoke the lazily loaded group."""
        group = self._load_group()
        return group.invoke(ctx)

    def get_command(self, ctx, cmd_name):
        """Get a command from the lazily loaded group."""
        group = self._load_group()
        return group.get_command(ctx, cmd_name)

    def list_commands(self, ctx):
        """List commands from the lazily loaded group."""
        group = self._load_group()
        return group.list_commands(ctx)

    def get_params(self, ctx):
        """Get parameters from the lazily loaded group."""
        group = self._load_group()
        return group.get_params(ctx)

    def shell_complete(self, ctx, param, incomplete):
        """Provide shell completion for the lazily loaded group."""
        group = self._load_group()
        # Delegate to the loaded group's completion
        if hasattr(group, "shell_complete"):
            return group.shell_complete(ctx, param, incomplete)
        # Fallback to default Click completion
        return (
            super().shell_complete(ctx, param, incomplete)
            if hasattr(super(), "shell_complete")
            else []
        )


def _add_lazy_commands(app: click.Group):
    """Add command groups with lazy loading."""
    # ============================================================
    # Core top-level commands (simplified CLI structure v8.0.0)
    # ============================================================

    # mcli run - The killer app: run workflow commands
    # (registered below with workflows group)

    # mcli list - List available commands
    try:
        from mcli.app.list_cmd import list_cmd

        app.add_command(list_cmd, name="list")
        logger.debug("Added list command")
    except ImportError as e:
        logger.debug(f"Could not load list command: {e}")

    # mcli search - Search for commands
    try:
        from mcli.app.search_cmd import search

        app.add_command(search, name="search")
        logger.debug("Added search command")
    except ImportError as e:
        logger.debug(f"Could not load search command: {e}")

    # mcli new - Create new workflow command
    try:
        from mcli.app.new_cmd import new

        app.add_command(new, name="new")
        logger.debug("Added new command")
    except ImportError as e:
        logger.debug(f"Could not load new command: {e}")

    # mcli edit - Edit a command
    try:
        from mcli.app.edit_cmd import edit

        app.add_command(edit, name="edit")
        logger.debug("Added edit command")
    except ImportError as e:
        logger.debug(f"Could not load edit command: {e}")

    # mcli delete - Delete a command (aliases: rm, remove)
    try:
        from mcli.app.delete_cmd import delete, rm

        app.add_command(delete, name="delete")
        app.add_command(rm, name="rm")
        logger.debug("Added delete/rm commands")
    except ImportError as e:
        logger.debug(f"Could not load delete command: {e}")

    # mcli sync - IPFS sync + lockfile management
    try:
        from mcli.app.sync_cmd import sync_group

        app.add_command(sync_group, name="sync")
        logger.debug("Added sync group")
    except ImportError as e:
        logger.debug(f"Could not load sync group: {e}")

    # mcli config - Configuration management
    try:
        from mcli.app.config_cmd import config

        app.add_command(config, name="config")
        logger.debug("Added config group")
    except ImportError as e:
        logger.debug(f"Could not load config group: {e}")

    # mcli init - Top-level shortcut to initialize workflows directory
    try:
        from mcli.app.config_cmd import config_init

        app.add_command(config_init, name="init")
        logger.debug("Added init command")
    except ImportError as e:
        logger.debug(f"Could not load init command: {e}")

    # mcli self - Self management (version, update, health, plugin, completion)
    try:
        from mcli.self.self_cmd import self_app

        app.add_command(self_app, name="self")
        logger.debug("Added self management commands")
    except Exception as e:
        logger.debug(f"Could not load self commands: {e}")

    # ============================================================
    # mcli run - The killer app: run workflow commands
    # ============================================================
    # Add workflows group directly (not lazy-loaded) to preserve -g/--global option
    try:
        from mcli.workflow.workflow import workflows as workflows_group

        # Primary command: mcli run
        app.add_command(workflows_group, name="run")
        logger.debug("Added 'run' command")

        # Keep 'workflows' as alias for backward compatibility
        app.add_command(workflows_group, name="workflows")
        logger.debug("Added 'workflows' alias for backward compatibility")
    except ImportError as e:
        logger.error(f"Could not load run/workflows group: {e}")
        # Fallback to lazy loading if import fails
        try:
            from mcli.app.completion_helpers import create_completion_aware_lazy_group

            workflows_group = create_completion_aware_lazy_group(
                "run",
                "mcli.workflow.workflow.workflows",
                "Run workflow commands",
            )
            app.add_command(workflows_group, name="run")
            app.add_command(workflows_group, name="workflows")  # Backward compat alias
            logger.debug("Added completion-aware run group with 'workflows' alias (fallback)")
        except ImportError:
            workflows_group = LazyGroup(
                "run",
                "mcli.workflow.workflow.workflows",
                help="Run workflow commands",
            )
            app.add_command(workflows_group, name="run")
            app.add_command(workflows_group, name="workflows")  # Backward compat alias
            logger.debug("Added lazy run group with 'workflows' alias (fallback)")

    # Lazy load other heavy commands that are used less frequently
    # NOTE: chat and model commands have been removed
    # - chat: removed from core commands
    # - model: moved to ~/.mcli/commands workflow
    # - test: removed from core commands
    lazy_commands = {}

    for cmd_name, cmd_info in lazy_commands.items():
        # Skip workflows since we already added it with completion support
        if cmd_name == "workflows":
            continue

        if cmd_name in ["model"]:
            # Use completion-aware LazyGroup for commands that have subcommands
            try:
                from mcli.app.completion_helpers import create_completion_aware_lazy_group

                lazy_cmd = create_completion_aware_lazy_group(
                    cmd_name, cmd_info["import_path"], cmd_info["help"]
                )
            except ImportError:
                # Fallback to standard LazyGroup
                lazy_cmd = LazyGroup(
                    name=cmd_name,
                    import_path=cmd_info["import_path"],
                    help=cmd_info["help"],
                )
        else:
            # Use LazyCommand for simple commands
            lazy_cmd = LazyCommand(
                name=cmd_name,
                import_path=cmd_info["import_path"],
                callback=lambda: None,  # Placeholder
                help=cmd_info["help"],
            )
        app.add_command(lazy_cmd)
        logger.debug(f"Added lazy command: {cmd_name}")

    # Note: Native script workflows are now loaded directly by ScopedWorkflowsGroup
    # in workflow.py using ScriptLoader. No sync step needed.

    # Load legacy JSON commands (for non-workflow group commands only)
    # Workflow-group JSON commands are handled by ScopedWorkflowsGroup
    try:
        from mcli.lib.custom_commands import load_custom_commands

        loaded_count = load_custom_commands(app)
        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} legacy JSON command(s)")
    except Exception as e:
        logger.debug(f"Could not load legacy JSON commands: {e}")


def create_app() -> click.Group:
    """Create and configure the Click application with clean top-level commands."""

    logger.debug("create_app")

    app = click.Group(name="mcli")

    # Version command moved to self group (mcli self version)
    # Add lazy-loaded command groups
    _add_lazy_commands(app)

    return app


# get_version_info moved to self_cmd.py


def main():
    """Main entry point for the application."""
    logger.debug("Entering main function")
    try:
        app = create_app()
        logger.debug("Created app, now calling app()")
        app()
        logger.debug("App executed")
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        # Make sure tracing is disabled on exit
        if os.environ.get("MCLI_TRACE_LEVEL"):
            logger.debug("Disabling runtime tracing on exit")
            disable_runtime_tracing()


if __name__ == "__main__":
    logger.debug("Script is being run directly")
    main()
