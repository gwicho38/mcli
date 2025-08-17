import functools
import inspect
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

from .daemon_client import APIDaemonClient, get_daemon_client

logger = get_logger(__name__)


def daemon_command(
    command_name: Optional[str] = None,
    auto_route: bool = True,
    fallback_to_local: bool = True,
    timeout: Optional[int] = None,
):
    """
    Decorator to route Click commands to the API daemon when enabled.

    Args:
        command_name: Name of the command (defaults to function name)
        auto_route: Whether to automatically route to daemon if enabled
        fallback_to_local: Whether to fallback to local execution if daemon fails
        timeout: Command timeout in seconds
    """

    def decorator(func: Callable) -> Callable:
        # Get command name
        cmd_name = command_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if daemon routing is enabled
            if not auto_route or not _is_daemon_routing_enabled():
                return func(*args, **kwargs)

            try:
                # Try to execute via daemon
                client = get_daemon_client()

                # Convert args and kwargs to command arguments
                cmd_args = _convert_to_command_args(args, kwargs, func)

                # Execute via daemon
                result = client.execute_command(
                    command_name=cmd_name, args=cmd_args, timeout=timeout
                )

                if result.get("success"):
                    logger.info(f"Command '{cmd_name}' executed successfully via daemon")
                    return result.get("result")
                else:
                    logger.warning(
                        f"Daemon execution failed for '{cmd_name}': {result.get('error')}"
                    )
                    if fallback_to_local:
                        logger.info(f"Falling back to local execution for '{cmd_name}'")
                        return func(*args, **kwargs)
                    else:
                        raise Exception(f"Daemon execution failed: {result.get('error')}")

            except Exception as e:
                logger.warning(f"Failed to execute '{cmd_name}' via daemon: {e}")
                if fallback_to_local:
                    logger.info(f"Falling back to local execution for '{cmd_name}'")
                    return func(*args, **kwargs)
                else:
                    raise

        return wrapper

    return decorator


def _is_daemon_routing_enabled() -> bool:
    """Check if daemon routing is enabled in configuration"""
    # Check environment variable
    if os.environ.get("MCLI_DAEMON_ROUTING", "false").lower() in ("true", "1", "yes"):
        return True

    # Check config files
    config_paths = [
        Path("config.toml"),  # Current directory
        Path.home() / ".config" / "mcli" / "config.toml",  # User config
        Path(__file__).parent.parent.parent.parent.parent / "config.toml",  # Project root
    ]

    for path in config_paths:
        if path.exists():
            try:
                daemon_config = read_from_toml(str(path), "api_daemon")
                if daemon_config and daemon_config.get("enabled", False):
                    return True
            except Exception as e:
                logger.debug(f"Could not read daemon config from {path}: {e}")

    return False


def _convert_to_command_args(args: tuple, kwargs: dict, func: Callable) -> List[str]:
    """Convert function arguments to command line arguments"""
    cmd_args = []

    # Get function signature
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    # Convert to command line arguments
    for param_name, param_value in bound_args.arguments.items():
        param = sig.parameters[param_name]

        # Skip self parameter for methods
        if param_name == "self":
            continue

        # Handle different parameter types
        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            # Positional argument
            if param_value is not None:
                cmd_args.append(str(param_value))
        elif param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            # Can be positional or keyword
            if param_value is not None:
                if param.default == inspect.Parameter.empty:
                    # Required argument
                    cmd_args.append(str(param_value))
                else:
                    # Optional argument with value
                    cmd_args.extend([f"--{param_name}", str(param_value)])
        elif param.kind == inspect.Parameter.KEYWORD_ONLY:
            # Keyword-only argument
            if param_value is not None and param_value != param.default:
                cmd_args.extend([f"--{param_name}", str(param_value)])
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            # *args
            if isinstance(param_value, (list, tuple)):
                cmd_args.extend([str(arg) for arg in param_value])
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            # **kwargs
            if isinstance(param_value, dict):
                for key, value in param_value.items():
                    cmd_args.extend([f"--{key}", str(value)])

    return cmd_args


def daemon_group(
    group_name: Optional[str] = None, auto_route: bool = True, fallback_to_local: bool = True
):
    """
    Decorator to route Click groups to the API daemon when enabled.

    Args:
        group_name: Name of the group (defaults to function name)
        auto_route: Whether to automatically route to daemon if enabled
        fallback_to_local: Whether to fallback to local execution if daemon fails
    """

    def decorator(func: Callable) -> Callable:
        # Get group name
        grp_name = group_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if daemon routing is enabled
            if not auto_route or not _is_daemon_routing_enabled():
                return func(*args, **kwargs)

            try:
                # Try to execute via daemon
                client = get_daemon_client()

                # For groups, we'll just check if the daemon is available
                # and then fall back to local execution
                if client.is_running():
                    logger.info(
                        f"Daemon is running, but group '{grp_name}' will be executed locally"
                    )

                return func(*args, **kwargs)

            except Exception as e:
                logger.warning(f"Failed to check daemon for group '{grp_name}': {e}")
                if fallback_to_local:
                    logger.info(f"Falling back to local execution for group '{grp_name}'")
                    return func(*args, **kwargs)
                else:
                    raise

        return wrapper

    return decorator


# Convenience function to check if daemon is available
def is_daemon_available() -> bool:
    """Check if the API daemon is available and running"""
    try:
        client = get_daemon_client()
        return client.is_running()
    except Exception:
        return False


# Convenience function to get daemon status
def get_daemon_status() -> Optional[Dict[str, Any]]:
    """Get daemon status if available"""
    try:
        client = get_daemon_client()
        return client.status()
    except Exception:
        return None
