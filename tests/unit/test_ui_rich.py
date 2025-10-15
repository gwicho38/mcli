import logging

logger = logging.getLogger(__name__)


def test_rich_import():
    """Test that rich can be imported"""
    try:
        import rich

        logger.info(f"Rich module found at: {rich.__file__}")
        try:
            logger.info(f"Rich version: {rich.__version__}")
        except AttributeError:
            logger.info("Rich version not available")
        assert True
    except ImportError as e:
        logger.info(f"Failed to import rich: {e}")
        import sys

        logger.info(f"Python path: {sys.path}")
        assert False, f"Rich import failed: {e}"
