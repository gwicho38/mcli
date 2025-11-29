"""Command code templates for mcli.

This module contains all code templates used for generating new commands.
Templates use Python's str.format() with named placeholders.

Template placeholders:
    - {name}: Command name
    - {name_cap}: Capitalized command name (for docstrings)
    - {group}: Command group name
    - {shell}: Shell interpreter (bash, zsh, etc.)
    - {description}: Command description
    - {template_code}: Pre-extracted template code (for editor templates)
"""


class CommandTemplates:
    """Code templates for new command generation."""

    # Python command template for group commands (with Click decorators)
    PYTHON_GROUP = '''"""
{name} command for mcli.{group}.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

# Create a Click command group
@click.group(name="{name}")
def app():
    """Description for {name} command group."""
    pass

@app.command("hello")
@click.argument("name", default="World")
def hello(name: str):
    """Example subcommand."""
    logger.info(f"Hello, {{name}}! This is the {name} command.")
    click.echo(f"Hello, {{name}}! This is the {name} command.")
'''

    # Python command template for standalone commands
    PYTHON_STANDALONE = '''"""
{name} command for mcli.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

def {name}_command(name: str = "World"):
    """
    {name_cap} command.
    """
    logger.info(f"Hello, {{name}}! This is the {name} command.")
    click.echo(f"Hello, {{name}}! This is the {name} command.")
'''

    # Shell command template
    SHELL = """#!/usr/bin/env {shell}
# {name} - {description}
#
# This is a shell-based MCLI workflow command.
# Arguments are passed as positional parameters: $1, $2, $3, etc.
# The command name is available in: $MCLI_COMMAND

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Command logic
echo "Hello from {name} shell command!"
echo "Command: $MCLI_COMMAND"

# Example: Access arguments
if [ $# -gt 0 ]; then
    echo "Arguments: $@"
    for arg in "$@"; do
        echo "  - $arg"
    done
else
    echo "No arguments provided"
fi

# Exit successfully
exit 0
"""


class EditorTemplates:
    """Templates for the interactive editor experience."""

    # Enhanced template with instructions shown in editor
    EDITOR_PYTHON = '''"""
{name} command for mcli.{group}.

Description: {description}

Instructions:
1. Write your Python command logic below
2. Use Click decorators for command definition
3. Save and close the editor to create the command
4. The command will be automatically converted to JSON format

Example Click command structure:
@click.command()
@click.argument('name', default='World')
def my_command(name):
    # My custom command.
    click.echo(f"Hello, {{name}}!")
"""
# Write your command logic below.
# Delete the example code and replace with your implementation.

{template_code}
'''


__all__ = ["CommandTemplates", "EditorTemplates"]
