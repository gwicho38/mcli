"""
Workflow command group for mcli.

All workflow commands are now loaded from portable JSON files in ~/.mcli/commands/
This provides a clean, maintainable way to manage workflow commands.
"""

import click


@click.group(name="workflow")
def workflow():
    """Workflow commands for automation, video processing, and daemon management"""
    pass


if __name__ == "__main__":
    workflow()
