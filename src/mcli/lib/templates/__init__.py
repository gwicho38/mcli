"""Templates module for mcli.

This module provides code templates for command generation.
Templates use standard Python format strings with named placeholders.

Usage:
    from mcli.lib.templates import CommandTemplates

    template = CommandTemplates.PYTHON_GROUP.format(name="my_command")
    shell_template = CommandTemplates.SHELL.format(name="backup", shell="bash", description="Backup files")
"""

from .command_templates import CommandTemplates, EditorTemplates

__all__ = ["CommandTemplates", "EditorTemplates"]
