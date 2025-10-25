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


# Add notebook subcommand
try:
    from mcli.workflow.notebook.notebook_cmd import notebook

    workflow.add_command(notebook)
except ImportError as e:
    # Notebook commands not available
    import sys
    from mcli.lib.logger.logger import get_logger

    logger = get_logger()
    logger.debug(f"Notebook commands not available: {e}")


if __name__ == "__main__":
    workflow()
