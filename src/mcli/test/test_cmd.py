"""
Test command group for mcli.
Contains testing and validation utilities.
"""

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@click.group(name="test")
def test_group():
    """Testing and validation commands"""
    pass


# Import and register subcommands
try:
    from mcli.test.cron_test_cmd import cron_test

    test_group.add_command(cron_test, name="cron")
    logger.debug("Added cron test command to test group")
except ImportError as e:
    logger.debug(f"Could not load cron test command: {e}")


if __name__ == "__main__":
    test_group()
