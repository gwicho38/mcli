"""Logger module for mcli.

This module provides logging utilities including:
- Basic file logging (get_logger)
- Structured JSON logging with correlation IDs (get_structured_logger)
- Correlation ID context management

Usage:
    # Basic logging (existing behavior)
    from mcli.lib.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Hello world")

    # Structured logging with correlation IDs
    from mcli.lib.logger import (
        get_structured_logger,
        correlation_context,
        with_correlation_id,
    )

    logger = get_structured_logger(__name__)
    with correlation_context() as cid:
        logger.info("Processing request", user_id="123")

    # Output (JSON):
    # {"timestamp": "...", "correlation_id": "abc12345",
    #  "level": "INFO", "message": "Processing request",
    #  "extra": {"user_id": "123"}}
"""

from .correlation import (
    CorrelationIdMixin,
    clear_correlation_id,
    correlation_context,
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
    with_correlation_id,
)
from .logger import (
    disable_runtime_tracing,
    disable_system_tracing,
    enable_runtime_tracing,
    enable_system_tracing,
    get_logger,
    get_system_trace_logger,
    register_process,
    register_subprocess,
    unregister_process,
)
from .structured import (
    CorrelationFilter,
    StructuredFormatter,
    StructuredLogger,
    configure_structured_logging,
    get_structured_logger,
)

__all__ = [
    # Basic logger
    "get_logger",
    # Trace loggers
    "get_system_trace_logger",
    "enable_runtime_tracing",
    "disable_runtime_tracing",
    "enable_system_tracing",
    "disable_system_tracing",
    "register_process",
    "register_subprocess",
    "unregister_process",
    # Correlation IDs
    "generate_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
    "reset_correlation_id",
    "clear_correlation_id",
    "correlation_context",
    "with_correlation_id",
    "CorrelationIdMixin",
    # Structured logging
    "StructuredFormatter",
    "StructuredLogger",
    "CorrelationFilter",
    "get_structured_logger",
    "configure_structured_logging",
]
