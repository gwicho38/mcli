#!/usr/bin/env python3
# @description: Example Python workflow command
# @version: 1.0.0
# @group: examples
# @author: MCLI Team
# @tags: example, demo, python

"""
Example Python workflow command for mcli.

This demonstrates how to create a Python-based mcli command using Click.
The script will be automatically discovered and available as:
    mcli run example_python

Metadata comments (@-prefixed) are extracted by the script loader and used
for documentation, grouping, and command registration.
"""

import click
from pathlib import Path
from typing import Optional


@click.command(name="example_python")
@click.argument("name", default="World")
@click.option("--greeting", "-g", default="Hello", help="Greeting to use")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def example_python_command(name: str, greeting: str, verbose: bool) -> None:
    """
    An example Python workflow command.

    Demonstrates Click argument and option handling, as well as
    mcli metadata extraction.

    Arguments:
        NAME: Name to greet (default: World)
    """
    if verbose:
        click.echo(f"[DEBUG] name={name}, greeting={greeting}")

    message = f"{greeting}, {name}!"
    click.echo(message)

    if verbose:
        click.echo(f"[DEBUG] Message length: {len(message)}")


# Entry point for direct execution
if __name__ == "__main__":
    example_python_command()
