"""Warning suppression utilities for Streamlit components used outside runtime context"""

import warnings
import logging
from contextlib import contextmanager


@contextmanager
def suppress_streamlit_warnings():
    """Context manager to suppress Streamlit warnings when used outside runtime context"""
    # Suppress specific Streamlit warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
        warnings.filterwarnings("ignore", message=".*No runtime found.*")
        warnings.filterwarnings("ignore", message=".*Session state does not function.*")
        warnings.filterwarnings("ignore", message=".*to view this Streamlit app.*")
        
        # Also suppress logging warnings from Streamlit
        streamlit_logger = logging.getLogger("streamlit")
        original_level = streamlit_logger.level
        streamlit_logger.setLevel(logging.ERROR)
        
        try:
            yield
        finally:
            streamlit_logger.setLevel(original_level)


def suppress_streamlit_warnings_decorator(func):
    """Decorator to suppress Streamlit warnings for a function"""
    def wrapper(*args, **kwargs):
        with suppress_streamlit_warnings():
            return func(*args, **kwargs)
    return wrapper