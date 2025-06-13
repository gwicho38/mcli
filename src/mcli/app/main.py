import sys
import platform
import inspect
import importlib
from pathlib import Path
from typing import Optional, List
import typer
from typer import Typer, Option
from importlib.metadata import version, metadata
from functools import lru_cache
import click
import functools
import tomli
import os
from mcli.lib.logger.logger import get_logger, enable_runtime_tracing, disable_runtime_tracing

# Get logger
logger = get_logger()

# Enable runtime tracing if environment variable is set
trace_level = os.environ.get('MCLI_TRACE_LEVEL')
if trace_level:
    try:
        # Convert to integer (1=function calls, 2=line by line, 3=verbose)
        level = int(trace_level)
        enable_runtime_tracing(level=level)
        logger.info(f"Runtime tracing enabled with level {level}")
    except ValueError:
        logger.warning(f"Invalid MCLI_TRACE_LEVEL value: {trace_level}. Using default level 1.")
        enable_runtime_tracing(level=1)
        
logger.debug("About to import readiness module")

# Import self management commands
try:
    from mcli.self.self_cmd import self_app
    logger.debug("Successfully imported self management module")
except ImportError as e:
    logger.error(f"Error importing self management module: {e}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")

logger.debug("main")

def discover_modules(
    base_path: Path, config_path: Path = None
) -> List[str]:
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
            base_path.parent.parent / "config.toml"  # Repository root
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
        logger.warning(f"Config file not found, using default configuration")
        config = {"paths": {"included_dirs": ["app", "self", "workflow", "public"]}}
    excluded_files = {"setup.py", "__init__.py"}
    excluded_dirs = {"resources", "models", "scripts", "private"}

    included_dirs = config.get("paths", {}).get("included_dirs", [])

    logger.debug(f"Included directories: {included_dirs}")
    for directory in included_dirs:
        # Handle nested paths like "app/readiness"
        if "/" in directory:
            parts = directory.split("/")
            parent_dir = parts[0]
            sub_dir = "/".join(parts[1:])
            search_path = base_path / parent_dir / sub_dir
            logger.debug(f"Searching in nested path: {search_path}")
            
            if search_path.exists():
                # Find the main module file (same name as the last directory part)
                last_dir = parts[-1]
                main_file = search_path / f"{last_dir}.py"
                
                if main_file.exists():
                    try:
                        # Create module path like mcli.app.readiness.readiness
                        module_parts = [base_path.name] + parts + [last_dir]
                        module_name = ".".join(module_parts)
                        logger.debug(f"Adding nested module: {module_name}")
                        modules.append(module_name)
                    except Exception as e:
                        logger.error(f"Error adding nested module {main_file}: {e}")
            continue
            
        # Original code for non-nested paths
        search_path = base_path / directory
        logger.debug(f"Searching in path: {search_path}")
        if search_path.exists():
            for package in search_path.rglob("*.py"):
                if (
                    package.name in excluded_files
                    or package.stem.startswith("test_")
                    or package.stem != search_path.stem
                ):
                    continue

                if any(part in excluded_dirs for part in package.parts):
                    continue

                try:
                    relative_path = package.relative_to(base_path.parent)
                    module_name = ".".join(relative_path.with_suffix("").parts)
                    modules.append(module_name)
                except Exception as e:
                    logger.error(f"Error converting {package} to module: {e}")

    return modules


def create_app() -> Typer:
    """Creates and configures the Typer application with dynamically loaded commands."""
    
    logger.debug("create_app")
    
    app = Typer(name="mcli", add_completion=True, no_args_is_help=True, rich_markup_mode=None)

    @app.command()
    def hello():
        """Test command to verify CLI is working"""
        logger.info("Hello from mcli!")

    @app.command()
    def version(
        verbose: Optional[bool] = Option(
            False, "--verbose", "-v", help="Show additional system information"
        ),
    ):
        """Show mcli version and system information"""
        logger.info(get_version_info(verbose))

    # Get the base path (mcli root)
    base_path = Path(__file__).parent.parent  # Updated to point to src/mcli instead of src/mcli/app

    # # Discover modules
    module_names = discover_modules(base_path)
    logger.debug(f"Discovered modules: {module_names}")

    # Add self commands explicitly
    try:
        if 'self_app' in globals():
            # Create a Typer app to wrap the Click-based self_app
            self_typer_app = Typer(name="self", help="Manage and extend the mcli application", no_args_is_help=True, rich_markup_mode=None)
            
            # Add each command from the Click group to the Typer app
            for cmd_name, cmd in self_app.commands.items():
                # Create wrapper function for each command
                def create_click_wrapper(click_cmd):
                    @functools.wraps(click_cmd.callback)
                    def wrapper(*args, **kwargs):
                        # Filter out typer context if it was passed
                        if 'ctx' in kwargs and isinstance(kwargs['ctx'], typer.Context):
                            del kwargs['ctx']
                        yield click_cmd.callback(*args, **kwargs)
                    return wrapper
                
                # Register the command
                self_typer_app.command(name=cmd_name)(create_click_wrapper(cmd))
            
            # Add the self commands to the main app
            app.add_typer(self_typer_app)
            logger.info("Added self management commands to mcli")
    except Exception as e:
        logger.error(f"Error adding self management commands: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
    # Add readiness command explicitly
    try:
        if 'readiness' in globals():
            logger.info(f"Found readiness in globals: {readiness}")
            # Create a Typer app for the readiness group
            readiness_app = Typer(name=readiness.name, help=readiness.help or "Readiness commands", no_args_is_help=True, rich_markup_mode=None)
            
            # Add the readiness app to the main app
            app.add_typer(readiness_app, name=readiness.name)
            
            # Create wrapper function for each command in the Click group
            def create_wrapper(callback):
                @functools.wraps(callback)
                def wrapper(*args, **kwargs):
                    return callback(*args, **kwargs)
                
                # Remove the 'ctx' parameter if it exists
                try:
                    sig = inspect.signature(callback)
                    parameters = list(sig.parameters.values())
                    if parameters and parameters[0].name == "ctx":
                        parameters = parameters[1:]
                    new_sig = inspect.Signature(parameters)
                    wrapper.__signature__ = new_sig
                except Exception as e:
                    logger.error(f"Error preserving signature: {e}")
                return wrapper
            
            # Add each command to the readiness app
            for cmd_name, cmd in readiness.commands.items():
                logger.info(f"Adding readiness command: {cmd_name}")
                readiness_app.command(name=cmd_name)(create_wrapper(cmd.callback))
                
            logger.info("Added readiness commands to mcli")
    except Exception as e:
        logger.error(f"Error adding readiness commands: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

    # # Import each module and register its commands properly
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)

            # Look for Click groups first
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, click.Group):
                    # Create a Typer app for each group
                    group_app = Typer(
                        name=obj.name, help=obj.help, no_args_is_help=True, rich_markup_mode=None
                    )

                    def create_wrapper(callback):
                        @functools.wraps(callback)
                        def wrapper(*args, **kwargs):
                            return callback(*args, **kwargs)

                        try:
                            sig = inspect.signature(callback)
                            parameters = list(sig.parameters.values())
                            # Remove the first parameter if it's the context (named "ctx")
                            if parameters and parameters[0].name == "ctx":
                                parameters = parameters[1:]
                            new_sig = inspect.Signature(parameters)
                            wrapper.__signature__ = new_sig
                        except Exception as e:
                            logger.error(f"Error preserving signature: {e}")
                        return wrapper

                    @group_app.callback()
                    def readiness_callback(ctx: typer.Context):
                        if ctx.invoked_subcommand is None:
                            typer.echo(ctx.get_help())

                            # Add the group app to the main app first

                    app.add_typer(group_app, name=obj.name)

                    # Add each command from the Click group to the Typer app
                    for cmd_name, cmd in obj.commands.items():
                        # logger.info(f"Adding command {cmd_name} to group {obj.name}")
                        group_app.command(name=cmd_name)(create_wrapper(cmd.callback))
                        # logger.info(cmd_name)

                elif isinstance(obj, typer.Typer):
                    # It's already a Typer app
                    app.add_typer(obj, name=obj.info.name)
                else:
                    pass
                # elif isinstance(obj, click.Command):
                #     # Add individual Click commands directly to the main app
                #     def create_wrapper(callback):
                #         def wrapper(*args, **kwargs):
                #             return callback(*args, **kwargs)

                #         wrapper.__name__ = callback.__name__
                #         wrapper.__doc__ = callback.__doc__
                #         return wrapper

                #     wrapper = create_wrapper(obj.callback)
                #     app.command(name=obj.name)(wrapper)

        except ImportError as e:
            logger.warning(f"Could not import module {module_name}: {e}")
    
    return app


@lru_cache()
def get_version_info(verbose: bool = False) -> str:
    """Get version info, cached to prevent multiple calls."""
    try:
        mcli_version = version("mcli")
        meta = metadata("mcli")

        info = [f"mcli version {mcli_version}"]

        if verbose:
            info.extend(
                [
                    f"\nPython: {sys.version.split()[0]}",
                    f"Platform: {platform.platform()}",
                    f"Description: {meta.get('Summary', 'Not available')}",
                    f"Author: {meta.get('Author', 'Not available')}",
                ]
            )
        return "\n".join(info)
    except Exception as e:
        return f"Could not determine version: {e}"


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
        if os.environ.get('MCLI_TRACE_LEVEL'):
            logger.debug("Disabling runtime tracing on exit")
            disable_runtime_tracing()


if __name__ == "__main__":
    logger.debug("Script is being run directly")
    main()
