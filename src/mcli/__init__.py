# logger.info("I am in mcli.__init__.py")
import sys

try:
    from mcli.app import main

    # from mcli.public import *
    # from mcli.private import *
    # Import the complete Click superset decorators
    from mcli.lib.api.mcli_decorators import BOOL  # mcli.BOOL - Click BOOL type
    from mcli.lib.api.mcli_decorators import FLOAT  # mcli.FLOAT - Click FLOAT type
    from mcli.lib.api.mcli_decorators import INT  # mcli.INT - Click INT type
    from mcli.lib.api.mcli_decorators import STRING  # mcli.STRING - Click STRING type
    from mcli.lib.api.mcli_decorators import UNPROCESSED  # mcli.UNPROCESSED - Click UNPROCESSED
    from mcli.lib.api.mcli_decorators import UUID  # mcli.UUID - Click UUID type
    from mcli.lib.api.mcli_decorators import Abort  # mcli.Abort - Click Abort
    from mcli.lib.api.mcli_decorators import BadParameter  # mcli.BadParameter - Click BadParameter
    from mcli.lib.api.mcli_decorators import Choice  # mcli.Choice - Click Choice type
    from mcli.lib.api.mcli_decorators import File  # mcli.File - Click File type
    from mcli.lib.api.mcli_decorators import FloatRange  # mcli.FloatRange - Click FloatRange type
    from mcli.lib.api.mcli_decorators import IntRange  # mcli.IntRange - Click IntRange type
    from mcli.lib.api.mcli_decorators import ParamType  # mcli.ParamType - Click ParamType
    from mcli.lib.api.mcli_decorators import Path  # mcli.Path - Click Path type
    from mcli.lib.api.mcli_decorators import UsageError  # mcli.UsageError - Click UsageError
    from mcli.lib.api.mcli_decorators import api  # @mcli.api - Legacy API decorator
    from mcli.lib.api.mcli_decorators import (
        api_command,  # @mcli.api_command - Convenience for API endpoints
    )
    from mcli.lib.api.mcli_decorators import argument  # @mcli.argument - Click argument decorator
    from mcli.lib.api.mcli_decorators import (
        background,  # @mcli.background - Legacy background decorator
    )
    from mcli.lib.api.mcli_decorators import (
        background_command,  # @mcli.background_command - Convenience for background
    )
    from mcli.lib.api.mcli_decorators import clear  # mcli.clear - Click clear
    from mcli.lib.api.mcli_decorators import (
        cli_with_api,  # @mcli.cli_with_api - Legacy combined decorator
    )
    from mcli.lib.api.mcli_decorators import (
        command,  # @mcli.command - Complete Click command with API/background
    )
    from mcli.lib.api.mcli_decorators import confirm  # mcli.confirm - Click confirmation
    from mcli.lib.api.mcli_decorators import echo  # mcli.echo - Click echo function
    from mcli.lib.api.mcli_decorators import edit  # mcli.edit - Click editor
    from mcli.lib.api.mcli_decorators import (
        format_filename,  # mcli.format_filename - Click filename
    )
    from mcli.lib.api.mcli_decorators import get_app  # mcli.get_app - Click app
    from mcli.lib.api.mcli_decorators import get_app_dir  # mcli.get_app_dir - Click app directory
    from mcli.lib.api.mcli_decorators import (
        get_binary_stream,  # mcli.get_binary_stream - Click binary stream
    )
    from mcli.lib.api.mcli_decorators import (
        get_current_context,  # mcli.get_current_context - Click context
    )
    from mcli.lib.api.mcli_decorators import (
        get_network_credentials,  # mcli.get_network_credentials - Click network
    )
    from mcli.lib.api.mcli_decorators import get_os_args  # mcli.get_os_args - Click OS args
    from mcli.lib.api.mcli_decorators import (
        get_terminal_size,  # mcli.get_terminal_size - Click terminal size
    )
    from mcli.lib.api.mcli_decorators import (
        get_text_stream,  # mcli.get_text_stream - Click text stream
    )
    from mcli.lib.api.mcli_decorators import getchar  # mcli.getchar - Click character input
    from mcli.lib.api.mcli_decorators import (
        group,  # @mcli.group - Complete Click group with API support
    )
    from mcli.lib.api.mcli_decorators import launch  # mcli.launch - Click launch
    from mcli.lib.api.mcli_decorators import open_file  # mcli.open_file - Click file operations
    from mcli.lib.api.mcli_decorators import option  # @mcli.option - Click option decorator
    from mcli.lib.api.mcli_decorators import pause  # mcli.pause - Click pause
    from mcli.lib.api.mcli_decorators import progressbar  # mcli.progressbar - Click progress bar
    from mcli.lib.api.mcli_decorators import prompt  # mcli.prompt - Click prompt
    from mcli.lib.api.mcli_decorators import secho  # mcli.secho - Click styled echo
    from mcli.lib.api.mcli_decorators import style  # mcli.style - Click styling
    from mcli.lib.api.mcli_decorators import unstyle  # mcli.unstyle - Click unstyle
    from mcli.lib.api.mcli_decorators import (  # Core decorators (complete Click superset); Click re-exports (complete subsume); Click types (complete subsume); Convenience decorators; Legacy decorators (for backward compatibility); Server management; Configuration; Convenience functions
        disable_api_server,
        enable_api_server,
        get_api_config,
        health_check,
        is_background_available,
        is_server_running,
        start_server,
        status_check,
        stop_server,
    )

    # Make everything available at the top level (complete Click subsume)
    __all__ = [
        "main",
        # Core decorators (complete Click superset)
        "command",
        "group",
        # Click re-exports (complete subsume)
        "option",
        "argument",
        "echo",
        "get_current_context",
        "get_app",
        "launch",
        "open_file",
        "get_os_args",
        "get_binary_stream",
        "get_text_stream",
        "format_filename",
        "getchar",
        "pause",
        "clear",
        "style",
        "unstyle",
        "secho",
        "edit",
        "confirm",
        "prompt",
        "progressbar",
        "get_terminal_size",
        "get_app_dir",
        "get_network_credentials",
        # Click types (complete subsume)
        "Path",
        "Choice",
        "IntRange",
        "FloatRange",
        "UNPROCESSED",
        "STRING",
        "INT",
        "FLOAT",
        "BOOL",
        "UUID",
        "File",
        "ParamType",
        "BadParameter",
        "UsageError",
        "Abort",
        # Convenience decorators
        "api_command",
        "background_command",
        # Legacy decorators (for backward compatibility)
        "api",
        "background",
        "cli_with_api",
        # Server management
        "start_server",
        "stop_server",
        "is_server_running",
        "is_background_available",
        "get_api_config",
        "enable_api_server",
        "disable_api_server",
        "health_check",
        "status_check",
    ]

except ImportError:
    # from .app import main
    sys.exit(1)
