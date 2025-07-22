import sys
import platform
import inspect
import importlib
from pathlib import Path
from typing import Optional, List
from importlib.metadata import version, metadata
from functools import lru_cache
import click
import functools
from mcli.lib.ui.styling import info, success
import tomli
import os
from mcli.lib.logger.logger import get_logger, enable_runtime_tracing, disable_runtime_tracing

# Import API decorator
from mcli.lib.api.api import api_endpoint, start_api_server, register_command_as_api, get_api_config

# Get logger
logger = get_logger(__name__)

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
    base_path: Path, config_path: Optional[Path] = None
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
    excluded_dirs = {"resources", "models", "scripts", "private", "venv", ".venv", "__pycache__"}

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
                for file_path in search_path.rglob("*.py"):
                    if file_path.name not in excluded_files and not any(
                        excluded_dir in file_path.parts for excluded_dir in excluded_dirs
                    ):
                        # Convert file path to module name with mcli prefix
                        relative_path = file_path.relative_to(base_path.parent)
                        module_name = str(relative_path).replace("/", ".").replace(".py", "")
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
        
        # Register the command as an API endpoint
        register_command_as_api(
            command_func=command_func,
            endpoint_path=endpoint_path,
            http_method="POST",
            description=f"API endpoint for {command_name} command from {module_name}",
            tags=[module_name.split('.')[-1]]  # Use last part of module name as tag
        )
        
        logger.debug(f"Registered API endpoint: {endpoint_path} for command {command_name}")
        
    except Exception as e:
        logger.warning(f"Failed to register API endpoint for {command_name}: {e}")


def process_click_commands(obj, module_name: str, parent_name: str = ""):
    """
    Recursively process Click commands and groups to register them as API endpoints.
    
    Args:
        obj: Click command or group object
        module_name: The module name
        parent_name: Parent command name for nesting
    """
    if hasattr(obj, 'commands'):
        # This is a Click group
        for name, command in obj.commands.items():
            full_name = f"{parent_name}/{name}" if parent_name else name
            
            # Register the command as an API endpoint
            register_command_as_api_endpoint(command.callback, module_name, full_name)
            
            # Recursively process nested commands
            if hasattr(command, 'commands'):
                process_click_commands(command, module_name, full_name)
    else:
        # This is a single command
        if hasattr(obj, 'callback') and obj.callback:
            full_name = parent_name if parent_name else obj.name
            register_command_as_api_endpoint(obj.callback, module_name, full_name)


def create_app() -> click.Group:
    """Create and configure the Click application with dynamically loaded commands."""
    
    logger.debug("create_app")
    
    app = click.Group(name="mcli")

    @app.command()
    def hello():
        """Test command to verify CLI is working"""
        message = "Hello from mcli!"
        logger.info(message)
        success(message)

    @app.command()
    @click.option("--verbose", "-v", is_flag=True, help="Show additional system information")
    def version(verbose: bool):
        """Show mcli version and system information"""
        message = get_version_info(verbose)
        logger.info(message)
        info(message)

    # Get the base path (mcli root)
    base_path = Path(__file__).parent.parent  # Updated to point to src/mcli instead of src/mcli/app

    # # Discover modules
    module_names = discover_modules(base_path)
    logger.debug(f"Discovered modules: {module_names}")

    # Add self commands explicitly
    try:
        if 'self_app' in globals():
            app.add_command(self_app, name="self")
            logger.info("Added self management commands to mcli")
            
            # Register self commands as API endpoints
            process_click_commands(self_app, "mcli.self", "self")
    except Exception as e:
        logger.error(f"Error adding self management commands: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
    # First import all modules and collect Click groups
    groups = {}
    for module_name in module_names:
        try:
            logger.debug(f"Processing module: {module_name}")
            module = importlib.import_module(module_name)

            for name, obj in inspect.getmembers(module):
                if isinstance(obj, click.Group):
                    logger.info(f"Discovered group {obj.name} in {module_name}")
                    groups[module_name] = obj
                    
                    # Register all commands in this group as API endpoints
                    process_click_commands(obj, module_name, obj.name)
                    
                elif isinstance(obj, click.Command):
                    logger.info(f"Discovered command {obj.name} in {module_name}")
                    
                    # Register single command as API endpoint
                    register_command_as_api_endpoint(obj.callback, module_name, obj.name)
                    
        except ImportError as e:
            logger.warning(f"Could not import module {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error processing module {module_name}: {e}")

    logger.info(f"Total groups found: {len(groups)}")
    logger.info(f"Group modules: {list(groups.keys())}")

    def find_parent(module_name: str) -> Optional[str]:
        """Return the parent module path if a parent group exists."""
        parts = module_name.split(".")
        if len(parts) >= 4 and parts[-1] == parts[-2]:
            candidate = ".".join(parts[:-2] + [parts[-3]])
            if candidate in groups:
                return candidate
        return None

    # Register groups with proper nesting
    for module_name, group in groups.items():
        parent = find_parent(module_name)
        if parent:
            logger.info(f"Nesting group {group.name} under {groups[parent].name}")
            groups[parent].add_command(group, name=group.name)
        else:
            logger.info(f"Adding top-level group {group.name}")
            app.add_command(group, name=group.name)
    
    # Start API server if enabled in configuration
    api_config = get_api_config()
    if api_config["enabled"]:
        api_url = start_api_server()
        if api_url:
            logger.info(f"✅ API server started at {api_url}")
            logger.info(f"📋 Available endpoints:")
            logger.info(f"   GET  {api_url}/health")
            logger.info(f"   GET  {api_url}/")
            logger.info(f"   GET  {api_url}/docs")
            logger.info(f"   GET  {api_url}/redoc")
        else:
            logger.warning("❌ Failed to start API server")
    else:
        logger.debug("API server is disabled in configuration")
    
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
