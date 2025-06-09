try:
    import rich
    logger.info(f"Rich module found at: {rich.__file__}")
    logger.info(f"Rich version: {rich.__version__}")
except ImportError as e:
    logger.info(f"Failed to import rich: {e}")
    import sys
    logger.info(f"Python path: {sys.path}")