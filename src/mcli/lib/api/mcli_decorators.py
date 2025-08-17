"""
MCLI Decorators - Complete Click Superset with Built-in API and Background Processing

This module provides decorators that completely subsume Click functionality,
adding API endpoints and background processing capabilities while maintaining
the familiar Click interface. Users only need to import mcli and get everything.
"""

import functools
import inspect
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

from .api import api_endpoint as _api_endpoint
from .api import get_api_app, start_api_server, stop_api_server
from .daemon_decorator import daemon_command as _daemon_command
from .daemon_decorator import is_daemon_available

logger = get_logger(__name__)

# =============================================================================
# Complete Click Superset Decorators
# =============================================================================


def command(
    name: Optional[str] = None,
    cls: Optional[type] = None,
    help: Optional[str] = None,
    epilog: Optional[str] = None,
    short_help: Optional[str] = None,
    options_metavar: Optional[str] = None,
    add_help_option: bool = True,
    no_args_is_help: bool = False,
    hidden: bool = False,
    deprecated: bool = False,
    # MCLI extensions
    api_endpoint: Optional[str] = None,
    api_method: str = "POST",
    api_description: Optional[str] = None,
    api_tags: Optional[List[str]] = None,
    background: bool = False,
    background_timeout: Optional[int] = None,
    **kwargs,
):
    """
    Complete Click command decorator with built-in API and background processing.

    This decorator completely subsumes Click's @command decorator. All Click
    parameters work exactly as expected, with additional MCLI capabilities.

    Args:
        # Standard Click parameters (all work exactly as in Click)
        name: Command name
        cls: Command class
        help: Help text
        epilog: Epilog text
        short_help: Short help text
        options_metavar: Options metavar
        add_help_option: Add help option
        no_args_is_help: Show help if no args
        hidden: Hide from help
        deprecated: Mark as deprecated

        # MCLI extensions (optional)
        api_endpoint: API endpoint path (enables API endpoint)
        api_method: HTTP method for API endpoint
        api_description: API documentation description
        api_tags: OpenAPI tags for API endpoint
        background: Enable background processing
        background_timeout: Background processing timeout

    Example:
        # Standard Click command (works exactly as before)
        @mcli.command()
        def greet(name: str):
            return f"Hello, {name}!"

        # Click command with API endpoint
        @mcli.command(api_endpoint="/greet", api_method="POST")
        def greet(name: str):
            return {"message": f"Hello, {name}!"}

        # Click command with background processing
        @mcli.command(background=True, background_timeout=60)
        def process_file(file_path: str):
            return {"processed": file_path}

        # Click command with both API and background
        @mcli.command(
            api_endpoint="/process",
            api_method="POST",
            background=True,
            background_timeout=300
        )
        def process_file(file_path: str):
            return {"processed": file_path}
    """

    def decorator(func: Callable) -> Callable:
        # Import Click here to avoid circular imports
        import click

        # Filter out MCLI-specific parameters for Click
        click_kwargs = {
            "name": name,
            "cls": cls,
            "help": help,
            "epilog": epilog,
            "short_help": short_help,
            "options_metavar": options_metavar,
            "add_help_option": add_help_option,
            "no_args_is_help": no_args_is_help,
            "hidden": hidden,
            "deprecated": deprecated,
        }

        # Add any other Click parameters
        click_kwargs.update(kwargs)

        # Create the Click command with all standard parameters
        click_command = click.command(**click_kwargs)(func)

        # Apply API endpoint if specified
        if api_endpoint:
            click_command = _api_endpoint(
                endpoint_path=api_endpoint,
                http_method=api_method,
                description=api_description or help or f"API endpoint for {func.__name__}",
                tags=api_tags or ["mcli"],
            )(click_command)

        # Apply background processing if enabled
        if background:
            click_command = _daemon_command(
                command_name=name or func.__name__,
                auto_route=True,
                fallback_to_local=True,
                timeout=background_timeout,
            )(click_command)

        return click_command

    return decorator


def group(
    name: Optional[str] = None,
    commands: Optional[Union[Dict[str, Callable], List[Callable]]] = None,
    order: Optional[List[str]] = None,
    help: Optional[str] = None,
    epilog: Optional[str] = None,
    short_help: Optional[str] = None,
    options_metavar: Optional[str] = None,
    add_help_option: bool = True,
    no_args_is_help: bool = False,
    hidden: bool = False,
    deprecated: bool = False,
    # MCLI extensions
    api_base_path: Optional[str] = None,
    api_description: Optional[str] = None,
    api_tags: Optional[List[str]] = None,
    **kwargs,
):
    """
    Complete Click group decorator with built-in API capabilities.

    This decorator completely subsumes Click's @group decorator. All Click
    parameters work exactly as expected, with additional MCLI capabilities.

    Args:
        # Standard Click parameters (all work exactly as in Click)
        name: Group name
        commands: Commands dictionary or list
        order: Command order
        help: Help text
        epilog: Epilog text
        short_help: Short help text
        options_metavar: Options metavar
        add_help_option: Add help option
        no_args_is_help: Show help if no args
        hidden: Hide from help
        deprecated: Mark as deprecated

        # MCLI extensions (optional)
        api_base_path: Base path for API endpoints in this group
        api_description: API documentation description
        api_tags: OpenAPI tags for API endpoints

    Example:
        # Standard Click group (works exactly as before)
        @mcli.group()
        def mycli():
            pass

        # Click group with API base path
        @mcli.group(api_base_path="/api/v1")
        def mycli():
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Import Click here to avoid circular imports
        import click

        # Filter out MCLI-specific parameters for Click
        click_kwargs = {
            "name": name,
            "help": help,
            "epilog": epilog,
            "short_help": short_help,
            "options_metavar": options_metavar,
            "add_help_option": add_help_option,
            "no_args_is_help": no_args_is_help,
            "hidden": hidden,
            "deprecated": deprecated,
        }

        # Add commands if provided
        if commands is not None:
            click_kwargs["commands"] = commands

        # Add order if provided
        if order is not None:
            click_kwargs["order"] = order

        # Add any other Click parameters
        click_kwargs.update(kwargs)

        # Create the Click group with all standard parameters
        click_group = click.group(**click_kwargs)(func)

        # Store API configuration for child commands
        if api_base_path:
            click_group.api_base_path = api_base_path
            click_group.api_description = api_description
            click_group.api_tags = api_tags

        return click_group

    return decorator


# =============================================================================
# Re-export Click functionality for complete subsume
# =============================================================================


def option(*param_decls, **attrs):
    """
    Re-export Click's option decorator.

    This allows users to use @mcli.option instead of @click.option.
    """
    import click

    return click.option(*param_decls, **attrs)


def argument(*param_decls, **attrs):
    """
    Re-export Click's argument decorator.

    This allows users to use @mcli.argument instead of @click.argument.
    """
    import click

    return click.argument(*param_decls, **attrs)


def echo(message=None, file=None, nl=True, err=False, color=None):
    """
    Re-export Click's echo function.

    This allows users to use mcli.echo instead of click.echo.
    """
    import click

    return click.echo(message, file, nl, err, color)


def get_current_context():
    """
    Re-export Click's get_current_context function.

    This allows users to use mcli.get_current_context instead of click.get_current_context.
    """
    import click

    return click.get_current_context()


def get_app():
    """
    Re-export Click's get_app function.

    This allows users to use mcli.get_app instead of click.get_app.
    """
    import click

    return click.get_app


def launch(url, wait=False, locate=False):
    """
    Re-export Click's launch function.

    This allows users to use mcli.launch instead of click.launch.
    """
    import click

    return click.launch(url, wait, locate)


def open_file(filename, mode="r", encoding=None, errors="strict", lazy=False, atomic=False):
    """
    Re-export Click's open_file function.

    This allows users to use mcli.open_file instead of click.open_file.
    """
    import click

    return click.open_file(filename, mode, encoding, errors, lazy, atomic)


def get_os_args():
    """
    Re-export Click's get_os_args object.

    This allows users to use mcli.get_os_args instead of click.get_os_args.
    """
    import click

    return click.get_os_args


def get_binary_stream(name):
    """
    Re-export Click's get_binary_stream function.

    This allows users to use mcli.get_binary_stream instead of click.get_binary_stream.
    """
    import click

    return click.get_binary_stream(name)


def get_text_stream(name, encoding=None, errors="strict"):
    """
    Re-export Click's get_text_stream function.

    This allows users to use mcli.get_text_stream instead of click.get_text_stream.
    """
    import click

    return click.get_text_stream(name, encoding, errors)


def format_filename(filename):
    """
    Re-export Click's format_filename function.

    This allows users to use mcli.format_filename instead of click.format_filename.
    """
    import click

    return click.format_filename(filename)


def getchar(echo=False):
    """
    Re-export Click's getchar function.

    This allows users to use mcli.getchar instead of click.getchar.
    """
    import click

    return click.getchar(echo)


def pause(info="Press any key to continue ...", err=False):
    """
    Re-export Click's pause function.

    This allows users to use mcli.pause instead of click.pause.
    """
    import click

    return click.pause(info, err)


def clear():
    """
    Re-export Click's clear function.

    This allows users to use mcli.clear instead of click.clear.
    """
    import click

    return click.clear()


def style(
    text,
    fg=None,
    bg=None,
    bold=None,
    dim=None,
    underline=None,
    overline=None,
    italic=None,
    blink=None,
    reverse=None,
    strikethrough=None,
    reset=True,
):
    """
    Re-export Click's style function.

    This allows users to use mcli.style instead of click.style.
    """
    import click

    return click.style(
        text, fg, bg, bold, dim, underline, overline, italic, blink, reverse, strikethrough, reset
    )


def unstyle(text):
    """
    Re-export Click's unstyle function.

    This allows users to use mcli.unstyle instead of click.unstyle.
    """
    import click

    return click.unstyle(text)


def secho(message=None, file=None, nl=True, err=False, color=None, **styles):
    """
    Re-export Click's secho function.

    This allows users to use mcli.secho instead of click.secho.
    """
    import click

    return click.secho(message, file, nl, err, color, **styles)


def edit(
    filename=None, editor=None, env=None, require_save=True, extension=".txt", filename_pattern=None
):
    """
    Re-export Click's edit function.

    This allows users to use mcli.edit instead of click.edit.
    """
    import click

    return click.edit(filename, editor, env, require_save, extension, filename_pattern)


def confirm(text, default=False, abort=False, prompt_suffix=": ", show_default=True, err=False):
    """
    Re-export Click's confirm function.

    This allows users to use mcli.confirm instead of click.confirm.
    """
    import click

    return click.confirm(text, default, abort, prompt_suffix, show_default, err)


def prompt(
    text,
    default=None,
    hide_input=False,
    confirmation_prompt=False,
    type=None,
    value_proc=None,
    prompt_suffix=": ",
    show_default=True,
    err=False,
    show_choices=True,
):
    """
    Re-export Click's prompt function.

    This allows users to use mcli.prompt instead of click.prompt.
    """
    import click

    return click.prompt(
        text,
        default,
        hide_input,
        confirmation_prompt,
        type,
        value_proc,
        prompt_suffix,
        show_default,
        err,
        show_choices,
    )


def progressbar(
    iterable=None,
    length=None,
    label=None,
    show_eta=True,
    show_percent=True,
    show_pos=False,
    item_show_func=None,
    fill_char="#",
    empty_char="-",
    bar_template="%(label)s  [%(bar)s]  %(info)s",
    info_sep="  ",
    width=36,
    file=None,
    color=None,
):
    """
    Re-export Click's progressbar function.

    This allows users to use mcli.progressbar instead of click.progressbar.
    """
    import click

    # Ensure show_eta is always a bool (default True if None)
    show_eta_bool = True if show_eta is None else bool(show_eta)
    return click.progressbar(
        iterable=iterable,
        length=length,
        label=label,
        show_eta=show_eta_bool,
        show_percent=show_percent,
        show_pos=show_pos,
        item_show_func=item_show_func,
        fill_char=fill_char,
        empty_char=empty_char,
        bar_template=bar_template,
        info_sep=info_sep,
        width=width,
        file=file,
        color=color,
    )


def get_terminal_size():
    """
    Re-export Click's get_terminal_size function.

    This allows users to use mcli.get_terminal_size instead of click.get_terminal_size.
    """
    import click

    return click.get_terminal_size


def get_app_dir(app_name, roaming=True, force_posix=False):
    """
    Re-export Click's get_app_dir function.

    This allows users to use mcli.get_app_dir instead of click.get_app_dir.
    """
    import click

    return click.get_app_dir(app_name, roaming, force_posix)


def get_network_credentials():
    """
    Re-export Click's get_network_credentials function.

    This allows users to use mcli.get_network_credentials instead of click.get_network_credentials.
    """
    import click

    return click.get_network_credentials


# Re-export Click types and classes
def _get_click_types():
    """Get Click types for re-export"""
    import click

    return {
        "Path": click.Path,
        "Choice": click.Choice,
        "IntRange": click.IntRange,
        "FloatRange": click.FloatRange,
        "UNPROCESSED": click.UNPROCESSED,
        "STRING": click.STRING,
        "INT": click.INT,
        "FLOAT": click.FLOAT,
        "BOOL": click.BOOL,
        "UUID": click.UUID,
        "File": click.File,
        "ParamType": click.ParamType,
        "BadParameter": click.BadParameter,
        "UsageError": click.UsageError,
        "Abort": click.Abort,
    }


# Add Click types to the module namespace
_click_types = _get_click_types()
globals().update(_click_types)

# =============================================================================
# Convenience Decorators for Common Patterns
# =============================================================================


def api_command(
    endpoint_path: str,
    http_method: str = "POST",
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    background: bool = True,
    background_timeout: Optional[int] = None,
    **click_kwargs,
):
    """
    Convenience decorator for Click commands that should be API endpoints.

    This is equivalent to @mcli.command() with api_endpoint and background=True.

    Args:
        endpoint_path: API endpoint path
        http_method: HTTP method
        description: API description
        tags: OpenAPI tags
        background: Enable background processing
        background_timeout: Background timeout
        **click_kwargs: All standard Click command parameters

    Example:
        @mcli.api_command("/greet", "POST", description="Greet someone")
        def greet(name: str):
            return {"message": f"Hello, {name}!"}
    """
    return command(
        api_endpoint=endpoint_path,
        api_method=http_method,
        api_description=description,
        api_tags=tags,
        background=background,
        background_timeout=background_timeout,
        **click_kwargs,
    )


def background_command(timeout: Optional[int] = None, **click_kwargs):
    """
    Convenience decorator for Click commands that should use background processing.

    This is equivalent to @mcli.command() with background=True.

    Args:
        timeout: Background processing timeout
        **click_kwargs: All standard Click command parameters

    Example:
        @mcli.background_command(timeout=300)
        def process_large_file(file_path: str):
            return {"processed": file_path}
    """
    return command(background=True, background_timeout=timeout, **click_kwargs)


# =============================================================================
# Legacy Support - Keep old names for backward compatibility
# =============================================================================


def api(
    endpoint_path: Optional[str] = None,
    http_method: str = "POST",
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enable_background: bool = True,
    background_timeout: Optional[int] = None,
):
    """
    Legacy decorator - use @mcli.command() with api_endpoint parameter instead.

    Example:
        # Old way
        @mcli.api("/greet", "POST")
        def greet(name: str):
            return {"message": f"Hello, {name}!"}

        # New way (recommended)
        @mcli.command(api_endpoint="/greet", api_method="POST")
        def greet(name: str):
            return {"message": f"Hello, {name}!"}
    """

    def decorator(func: Callable) -> Callable:
        return command(
            api_endpoint=endpoint_path or f"/{func.__name__}",
            api_method=http_method,
            api_description=description,
            api_tags=tags,
            background=enable_background,
            background_timeout=background_timeout,
        )(func)

    return decorator


def background(
    command_name: Optional[str] = None,
    auto_route: bool = True,
    fallback_to_local: bool = True,
    timeout: Optional[int] = None,
):
    """
    Legacy decorator - use @mcli.command() with background=True instead.

    Example:
        # Old way
        @mcli.background(timeout=300)
        def process_file(file_path: str):
            return {"processed": file_path}

        # New way (recommended)
        @mcli.command(background=True, background_timeout=300)
        def process_file(file_path: str):
            return {"processed": file_path}
    """

    def decorator(func: Callable) -> Callable:
        return command(name=command_name, background=True, background_timeout=timeout)(func)

    return decorator


def cli_with_api(
    endpoint_path: Optional[str] = None,
    http_method: str = "POST",
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enable_background: bool = True,
    background_timeout: Optional[int] = None,
):
    """
    Legacy decorator - use @mcli.command() with api_endpoint and background=True instead.

    Example:
        # Old way
        @mcli.cli_with_api("/process", "POST")
        def process_file(file_path: str):
            return {"processed": file_path}

        # New way (recommended)
        @mcli.command(api_endpoint="/process", api_method="POST", background=True)
        def process_file(file_path: str):
            return {"processed": file_path}
    """
    return command(
        api_endpoint=endpoint_path,
        api_method=http_method,
        api_description=description,
        api_tags=tags,
        background=enable_background,
        background_timeout=background_timeout,
    )


# =============================================================================
# Server Management Functions
# =============================================================================


def start_server(
    host: str = "0.0.0.0", port: Optional[int] = None, debug: bool = False
) -> Optional[str]:
    """
    Start the API server for your CLI.

    Args:
        host: Server host address
        port: Server port (uses random port if None)
        debug: Enable debug mode

    Returns:
        Server URL if started successfully, None otherwise

    Example:
        if __name__ == "__main__":
            mcli.start_server(port=8000)
            my_cli()
    """
    try:
        if port is not None:
            server_url = start_api_server(host=host, port=port, debug=debug)
        else:
            server_url = start_api_server(host=host, debug=debug)
        logger.info(f"API server started at: {server_url}")
        return server_url
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        return None


def stop_server():
    """
    Stop the API server.

    Example:
        import atexit
        atexit.register(mcli.stop_server)
    """
    try:
        stop_api_server()
        logger.info("API server stopped")
    except Exception as e:
        logger.error(f"Failed to stop API server: {e}")


def is_server_running() -> bool:
    """
    Check if the API server is running.

    Returns:
        True if server is running, False otherwise
    """
    try:
        app = get_api_app()
        return app is not None
    except Exception:
        return False


def is_background_available() -> bool:
    """
    Check if background processing service is available.

    Returns:
        True if background service is available, False otherwise
    """
    return is_daemon_available()


# =============================================================================
# Configuration Helpers
# =============================================================================


def get_api_config() -> Dict[str, Any]:
    """
    Get the current API configuration.

    Returns:
        Dictionary with API configuration settings
    """
    config = {
        "enabled": False,
        "host": "0.0.0.0",
        "port": None,
        "use_random_port": True,
        "debug": False,
    }

    # Check environment variables
    if os.environ.get("MCLI_API_SERVER", "false").lower() in ("true", "1", "yes"):
        config["enabled"] = True

    if os.environ.get("MCLI_API_HOST"):
        config["host"] = os.environ.get("MCLI_API_HOST")

    port_env = os.environ.get("MCLI_API_PORT")
    if port_env is not None:
        config["port"] = int(port_env)
        config["use_random_port"] = False

    if os.environ.get("MCLI_API_DEBUG", "false").lower() in ("true", "1", "yes"):
        config["debug"] = True

    return config


def enable_api_server():
    """
    Enable the API server via environment variable.

    Example:
        mcli.enable_api_server()
        # Now your CLI will start the API server
    """
    os.environ["MCLI_API_SERVER"] = "true"


def disable_api_server():
    """
    Disable the API server via environment variable.
    """
    os.environ["MCLI_API_SERVER"] = "false"


# =============================================================================
# Convenience Functions for Common Patterns
# =============================================================================


def health_check():
    """
    Create a health check endpoint.

    Example:
        @mcli.command(api_endpoint="/health", api_method="GET")
        def health():
            return {"status": "healthy", "timestamp": time.time()}
    """
    import time

    return {"status": "healthy", "timestamp": time.time()}


def status_check():
    """
    Create a status check endpoint that includes server and background service status.

    Example:
        @mcli.command(api_endpoint="/status", api_method="GET")
        def status():
            return mcli.status_check()
    """
    return {
        "api_server": "running" if is_server_running() else "not_running",
        "background_service": "available" if is_background_available() else "not_available",
        "timestamp": time.time(),
    }


# =============================================================================
# Chat Interface
# =============================================================================


class ChatCommandGroup(click.Group):
    """Special command group that provides chat-based interaction"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_client = None

    def get_help(self, ctx):
        """Start interactive chat session instead of showing normal help"""
        from mcli.chat.chat import ChatClient

        self.chat_client = ChatClient()
        self.chat_client.start_interactive_session()
        return ""


from typing import Any, Callable


def chat(**kwargs) -> Callable[[Callable[..., Any]], click.Group]:
    """Create a chat command group that provides an interactive LLM-powered interface"""
    kwargs.setdefault("invoke_without_command", True)
    kwargs.setdefault("no_args_is_help", False)
    return click.group(cls=ChatCommandGroup, **kwargs)


# =============================================================================
# Export everything for complete Click subsume
# =============================================================================

# Main decorators (complete Click superset)
__all__ = [
    # Core decorators
    "command",  # @mcli.command - Complete Click command with API/background
    "group",  # @mcli.group - Complete Click group with API support
    "chat",  # @mcli.chat - Interactive command chat interface
    # Click re-exports (complete subsume)
    "option",  # @mcli.option - Click option decorator
    "argument",  # @mcli.argument - Click argument decorator
    "echo",  # mcli.echo - Click echo function
    "get_current_context",  # mcli.get_current_context - Click context
    "get_app",  # mcli.get_app - Click app
    "launch",  # mcli.launch - Click launch
    "open_file",  # mcli.open_file - Click file operations
    "get_os_args",  # mcli.get_os_args - Click OS args
    "get_binary_stream",  # mcli.get_binary_stream - Click binary stream
    "get_text_stream",  # mcli.get_text_stream - Click text stream
    "format_filename",  # mcli.format_filename - Click filename
    "getchar",  # mcli.getchar - Click character input
    "pause",  # mcli.pause - Click pause
    "clear",  # mcli.clear - Click clear
    "style",  # mcli.style - Click styling
    "unstyle",  # mcli.unstyle - Click unstyle
    "secho",  # mcli.secho - Click styled echo
    "edit",  # mcli.edit - Click editor
    "confirm",  # mcli.confirm - Click confirmation
    "prompt",  # mcli.prompt - Click prompt
    "progressbar",  # mcli.progressbar - Click progress bar
    "get_terminal_size",  # mcli.get_terminal_size - Click terminal size
    "get_app_dir",  # mcli.get_app_dir - Click app directory
    "get_network_credentials",  # mcli.get_network_credentials - Click network
    # Convenience decorators
    "api_command",  # @mcli.api_command - Convenience for API endpoints
    "background_command",  # @mcli.background_command - Convenience for background
    # Legacy decorators (for backward compatibility)
    "api",  # @mcli.api - Legacy API decorator
    "background",  # @mcli.background - Legacy background decorator
    "cli_with_api",  # @mcli.cli_with_api - Legacy combined decorator
    # Server management
    "start_server",
    "stop_server",
    "is_server_running",
    "is_background_available",
    # Configuration
    "get_api_config",
    "enable_api_server",
    "disable_api_server",
    # Convenience functions
    "health_check",
    "status_check",
]
