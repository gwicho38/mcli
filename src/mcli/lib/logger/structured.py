"""Structured logging support for mcli.

This module provides JSON-formatted structured logging that includes
correlation IDs, timestamps, and rich metadata for better observability.

Usage:
    from mcli.lib.logger.structured import (
        StructuredFormatter,
        StructuredLogger,
        get_structured_logger,
    )

    # Get a structured logger
    logger = get_structured_logger(__name__)
    logger.info("Processing request", user_id="123", action="login")

    # Output (JSON):
    # {"timestamp": "2026-01-29T10:00:00.000Z", "level": "INFO",
    #  "correlation_id": "abc12345", "logger": "mymodule",
    #  "message": "Processing request", "user_id": "123", "action": "login"}
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, MutableMapping, Optional, Tuple

from .correlation import get_correlation_id

# Log format strings - kept here since they contain specialized format specifiers
# that don't fit well in a constants module
LOG_FORMAT_TRADITIONAL = "%(asctime)s [%(levelname)s] [%(correlation_id)s] [%(name)s] %(message)s"
LOG_FORMAT_CONSOLE = "[%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s"


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Produces log records as JSON objects with:
    - timestamp (ISO 8601 format)
    - level (log level name)
    - correlation_id (from context)
    - logger (logger name)
    - message (formatted message)
    - Any additional fields passed via extra

    Args:
        include_stack_info: Whether to include stack traces for errors.
        include_process_info: Whether to include process/thread IDs.
    """

    def __init__(
        self,
        include_stack_info: bool = True,
        include_process_info: bool = False,
    ) -> None:
        """Initialize the structured formatter.

        Args:
            include_stack_info: Whether to include stack traces for errors.
            include_process_info: Whether to include process/thread IDs.
        """
        super().__init__()
        self.include_stack_info = include_stack_info
        self.include_process_info = include_process_info

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Build the base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add process/thread info if requested
        if self.include_process_info:
            log_entry["process_id"] = record.process
            log_entry["thread_id"] = record.thread
            log_entry["thread_name"] = record.threadName

        # Add file location info
        log_entry["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info and self.include_stack_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (
                    traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
                ),
            }

        # Add any extra fields (excluding standard LogRecord attributes)
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "message",
            "taskName",
        }

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in standard_attrs and not key.startswith("_")
        }

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class CorrelationFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records.

    This filter automatically adds the current correlation ID to all log records,
    making it available in traditional formatters as %(correlation_id)s.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the record and allow it to pass."""
        record.correlation_id = get_correlation_id() or "-"  # type: ignore[attr-defined]
        return True


class StructuredLogger(logging.LoggerAdapter):
    """Logger adapter that adds structured context to log messages.

    This adapter allows passing additional context fields as keyword arguments:

        logger.info("User logged in", user_id="123", ip="192.168.1.1")

    The extra fields will be included in the structured log output.
    """

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the structured logger adapter.

        Args:
            logger: The underlying logger instance.
            extra: Optional default extra fields for all log messages.
        """
        super().__init__(logger, extra or {})

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> Tuple[str, MutableMapping[str, Any]]:
        """Process the log message and keyword arguments.

        Merges extra context from the adapter with kwargs passed to the log call.
        """
        extra = kwargs.get("extra", {})

        # Add adapter-level context
        if self.extra:
            extra.update(self.extra)

        # Extract non-standard kwargs as extra context
        # Standard logging kwargs: exc_info, stack_info, stacklevel
        standard_kwargs = {"exc_info", "stack_info", "stacklevel"}
        custom_fields = {
            key: value for key, value in kwargs.items() if key not in standard_kwargs | {"extra"}
        }

        if custom_fields:
            extra.update(custom_fields)
            # Remove custom fields from kwargs to avoid TypeError
            for key in custom_fields:
                kwargs.pop(key, None)

        kwargs["extra"] = extra
        return msg, kwargs

    def with_context(self, **context: Any) -> "StructuredLogger":
        """Create a new logger with additional context.

        Args:
            **context: Key-value pairs to add to all log messages.

        Returns:
            A new StructuredLogger with the merged context.

        Example:
            request_logger = logger.with_context(request_id="abc", user_id="123")
            request_logger.info("Processing")  # Includes request_id and user_id
        """
        merged_extra = dict(self.extra or {})
        merged_extra.update(context)
        return StructuredLogger(self.logger, merged_extra)


def get_structured_logger(
    name: str,
    level: int = logging.DEBUG,
    structured_output: bool = True,
    log_to_file: bool = True,
    log_to_console: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> StructuredLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (default: DEBUG).
        structured_output: If True, use JSON format. If False, use traditional format.
        log_to_file: Whether to log to file.
        log_to_console: Whether to also log to console (stderr).
        extra: Default extra fields to include in all log messages.

    Returns:
        A configured StructuredLogger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Don't add handlers if they already exist for this logger
    if logger.handlers:
        return StructuredLogger(logger, extra)

    # Add correlation ID filter
    correlation_filter = CorrelationFilter()
    logger.addFilter(correlation_filter)

    # Set up file handler
    if log_to_file:
        try:
            from mcli.lib.paths import get_logs_dir

            log_dir = get_logs_dir()
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = log_dir / f"mcli_structured_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)

            if structured_output:
                file_handler.setFormatter(StructuredFormatter())
            else:
                # Traditional format with correlation ID
                file_handler.setFormatter(logging.Formatter(LOG_FORMAT_TRADITIONAL))

            logger.addHandler(file_handler)

        except Exception:
            # Fall back to console if file logging fails
            log_to_console = True

    # Set up console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)

        if structured_output:
            console_handler.setFormatter(StructuredFormatter(include_process_info=False))
        else:
            console_handler.setFormatter(logging.Formatter(LOG_FORMAT_CONSOLE))

        logger.addHandler(console_handler)

    return StructuredLogger(logger, extra)


def configure_structured_logging(
    root_level: int = logging.INFO,
    structured_output: bool = True,
    include_process_info: bool = False,
) -> None:
    """Configure the root logger for structured output.

    This affects all loggers that don't have their own configuration.

    Args:
        root_level: Root logger level.
        structured_output: Whether to use JSON format.
        include_process_info: Whether to include process/thread info.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add correlation filter
    root_logger.addFilter(CorrelationFilter())

    # Add structured handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(root_level)

    if structured_output:
        handler.setFormatter(StructuredFormatter(include_process_info=include_process_info))
    else:
        handler.setFormatter(logging.Formatter(LOG_FORMAT_TRADITIONAL))

    root_logger.addHandler(handler)
