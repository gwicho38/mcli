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


if __name__ == "__main__":
    test_group()
