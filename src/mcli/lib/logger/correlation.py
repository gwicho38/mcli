"""Correlation ID support for structured logging.

This module provides correlation ID generation and context management
for tracing requests and operations across multiple components.

Usage:
    from mcli.lib.logger.correlation import (
        get_correlation_id,
        set_correlation_id,
        correlation_context,
        CorrelationFilter,
    )

    # Manual context management
    set_correlation_id("my-custom-id")
    logger.info("This log will include the correlation ID")

    # Context manager (recommended)
    with correlation_context() as correlation_id:
        logger.info("This log will include an auto-generated correlation ID")

    # In a function decorator
    @with_correlation_id
    def my_function():
        logger.info("This log has a correlation ID")
"""

import contextvars
import functools
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional, TypeVar

# Context variable for correlation ID - thread-safe and async-safe
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns a shortened UUID4 for readability while maintaining uniqueness.
    Format: 8 hex characters (provides ~4 billion unique IDs)

    Returns:
        A unique correlation ID string.
    """
    return uuid.uuid4().hex[:8]


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID for this context.

    Returns:
        The current correlation ID, or None if not set.
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: Optional[str]) -> contextvars.Token[Optional[str]]:
    """Set the correlation ID for the current context.

    Args:
        correlation_id: The correlation ID to set, or None to clear.

    Returns:
        A token that can be used to reset the correlation ID to its previous value.
    """
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: contextvars.Token[Optional[str]]) -> None:
    """Reset the correlation ID to its previous value.

    Args:
        token: The token returned from set_correlation_id.
    """
    _correlation_id.reset(token)


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id.set(None)


@contextmanager
def correlation_context(
    correlation_id: Optional[str] = None,
) -> "Generator[str, None, None]":
    """Context manager for correlation ID scoping.

    If no correlation_id is provided, a new one is generated.

    Args:
        correlation_id: Optional correlation ID to use. If None, a new one is generated.

    Yields:
        The correlation ID being used.

    Example:
        with correlation_context() as cid:
            logger.info("Processing request")  # Includes cid in log
            do_work()
            logger.info("Request complete")  # Same cid
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    token = set_correlation_id(correlation_id)
    try:
        yield correlation_id
    finally:
        reset_correlation_id(token)


def with_correlation_id(func: F) -> F:
    """Decorator that ensures a function has a correlation ID context.

    If a correlation ID is already set in the current context, it will be reused.
    Otherwise, a new one will be generated for the duration of the function call.

    Args:
        func: The function to wrap.

    Returns:
        The wrapped function.

    Example:
        @with_correlation_id
        def process_request(data):
            logger.info("Processing")  # Has correlation ID
            return result
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Reuse existing correlation ID if present
        existing_id = get_correlation_id()
        if existing_id is not None:
            return func(*args, **kwargs)

        # Otherwise create a new context
        with correlation_context():
            return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


class CorrelationIdMixin:
    """Mixin class that adds correlation ID support to any class.

    Usage:
        class MyService(CorrelationIdMixin):
            def process(self):
                with self.correlation_scope():
                    self.logger.info("Processing...")
    """

    def get_correlation_id(self) -> Optional[str]:
        """Get the current correlation ID."""
        return get_correlation_id()

    def set_correlation_id(self, correlation_id: str) -> contextvars.Token[Optional[str]]:
        """Set a correlation ID for the current context."""
        return set_correlation_id(correlation_id)

    @contextmanager
    def correlation_scope(self, correlation_id: Optional[str] = None) -> Generator[str, None, None]:
        """Create a correlation ID scope."""
        with correlation_context(correlation_id) as cid:
            yield cid
