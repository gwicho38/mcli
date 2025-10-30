"""
Workflows command group for mcli.

All workflow commands are now loaded from portable JSON files in ~/.mcli/commands/
This provides a clean, maintainable way to manage workflow commands.
"""

import click


@click.group(name="workflows")
def workflows():
    """Runnable workflows for automation, video processing, and daemon management"""
    pass


# Add secrets workflow
try:
    from mcli.workflow.secrets.secrets_cmd import secrets

    workflows.add_command(secrets)
except ImportError as e:
    # Secrets workflow not available
    import sys
    from mcli.lib.logger.logger import get_logger

    logger = get_logger()
    logger.debug(f"Secrets workflow not available: {e}")

# Add notebook subcommand
try:
    from mcli.workflow.notebook.notebook_cmd import notebook

    workflows.add_command(notebook)
except ImportError as e:
    # Notebook commands not available
    import sys
    from mcli.lib.logger.logger import get_logger

    logger = get_logger()
    logger.debug(f"Notebook commands not available: {e}")


# For backward compatibility, keep workflow as an alias
workflow = workflows

if __name__ == "__main__":
    workflows()
