# src/mcli/app/__init__.py

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

logger.info("Initializing mcli.app package")

# Import main function
try:
    from .main import main

    logger.info("Successfully imported main from .main")
except ImportError as e:
    logger.error(f"Failed to import main: {e}")
    import traceback

    logger.error(f"Traceback: {traceback.format_exc()}")
    raise

__all__ = ["main"]
