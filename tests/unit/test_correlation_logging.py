"""Unit tests for mcli.lib.logger.correlation and mcli.lib.logger.structured modules."""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from unittest.mock import patch


class TestCorrelationIdGeneration:
    """Tests for correlation ID generation."""

    def test_generate_correlation_id_returns_string(self):
        """Test that generate_correlation_id returns a string."""
        from mcli.lib.logger.correlation import generate_correlation_id

        cid = generate_correlation_id()
        assert isinstance(cid, str)

    def test_generate_correlation_id_has_correct_length(self):
        """Test that correlation IDs are 8 characters."""
        from mcli.lib.logger.correlation import generate_correlation_id

        cid = generate_correlation_id()
        assert len(cid) == 8

    def test_generate_correlation_id_is_hex(self):
        """Test that correlation IDs are valid hex strings."""
        from mcli.lib.logger.correlation import generate_correlation_id

        cid = generate_correlation_id()
        # Should not raise ValueError
        int(cid, 16)

    def test_generate_correlation_id_uniqueness(self):
        """Test that generated correlation IDs are unique."""
        from mcli.lib.logger.correlation import generate_correlation_id

        ids = {generate_correlation_id() for _ in range(1000)}
        assert len(ids) == 1000  # All unique


class TestCorrelationIdContext:
    """Tests for correlation ID context management."""

    def test_get_correlation_id_default_none(self):
        """Test that correlation ID is None by default."""
        from mcli.lib.logger.correlation import clear_correlation_id, get_correlation_id

        clear_correlation_id()
        assert get_correlation_id() is None

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        from mcli.lib.logger.correlation import (
            clear_correlation_id,
            get_correlation_id,
            set_correlation_id,
        )

        clear_correlation_id()
        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"
        clear_correlation_id()

    def test_reset_correlation_id(self):
        """Test resetting correlation ID to previous value."""
        from mcli.lib.logger.correlation import (
            clear_correlation_id,
            get_correlation_id,
            reset_correlation_id,
            set_correlation_id,
        )

        clear_correlation_id()
        set_correlation_id("original")
        token = set_correlation_id("new")
        assert get_correlation_id() == "new"

        reset_correlation_id(token)
        assert get_correlation_id() == "original"
        clear_correlation_id()

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        from mcli.lib.logger.correlation import (
            clear_correlation_id,
            get_correlation_id,
            set_correlation_id,
        )

        set_correlation_id("test")
        clear_correlation_id()
        assert get_correlation_id() is None


class TestCorrelationContext:
    """Tests for correlation_context context manager."""

    def test_correlation_context_generates_id(self):
        """Test that correlation_context generates an ID if not provided."""
        from mcli.lib.logger.correlation import clear_correlation_id, correlation_context

        clear_correlation_id()
        with correlation_context() as cid:
            assert cid is not None
            assert len(cid) == 8

    def test_correlation_context_uses_provided_id(self):
        """Test that correlation_context uses provided ID."""
        from mcli.lib.logger.correlation import correlation_context, get_correlation_id

        with correlation_context("custom-id") as cid:
            assert cid == "custom-id"
            assert get_correlation_id() == "custom-id"

    def test_correlation_context_cleans_up(self):
        """Test that correlation_context cleans up after exit."""
        from mcli.lib.logger.correlation import (
            clear_correlation_id,
            correlation_context,
            get_correlation_id,
        )

        clear_correlation_id()
        with correlation_context("temp"):
            pass
        assert get_correlation_id() is None

    def test_correlation_context_restores_previous(self):
        """Test that nested contexts restore previous value."""
        from mcli.lib.logger.correlation import correlation_context, get_correlation_id

        with correlation_context("outer"):
            assert get_correlation_id() == "outer"
            with correlation_context("inner"):
                assert get_correlation_id() == "inner"
            assert get_correlation_id() == "outer"

    def test_correlation_context_exception_handling(self):
        """Test that context cleans up even on exception."""
        from contextlib import suppress

        from mcli.lib.logger.correlation import (
            clear_correlation_id,
            correlation_context,
            get_correlation_id,
        )

        clear_correlation_id()
        with suppress(ValueError), correlation_context("test"):
            raise ValueError("test error")

        assert get_correlation_id() is None


class TestWithCorrelationIdDecorator:
    """Tests for the with_correlation_id decorator."""

    def test_decorator_creates_correlation_id(self):
        """Test that decorator creates correlation ID."""
        from mcli.lib.logger.correlation import (
            clear_correlation_id,
            get_correlation_id,
            with_correlation_id,
        )

        clear_correlation_id()

        @with_correlation_id
        def my_function():
            return get_correlation_id()

        result = my_function()
        assert result is not None
        assert len(result) == 8

    def test_decorator_reuses_existing_id(self):
        """Test that decorator reuses existing correlation ID."""
        from mcli.lib.logger.correlation import (
            clear_correlation_id,
            correlation_context,
            get_correlation_id,
            with_correlation_id,
        )

        clear_correlation_id()

        @with_correlation_id
        def my_function():
            return get_correlation_id()

        with correlation_context("existing-id"):
            result = my_function()
            assert result == "existing-id"

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        from mcli.lib.logger.correlation import with_correlation_id

        @with_correlation_id
        def documented_function():
            """This is my docstring."""
            pass

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is my docstring."

    def test_decorator_passes_arguments(self):
        """Test that decorator passes arguments correctly."""
        from mcli.lib.logger.correlation import with_correlation_id

        @with_correlation_id
        def add(a, b, multiplier=1):
            return (a + b) * multiplier

        assert add(2, 3) == 5
        assert add(2, 3, multiplier=2) == 10


class TestCorrelationIdMixin:
    """Tests for CorrelationIdMixin class."""

    def test_mixin_get_correlation_id(self):
        """Test mixin get_correlation_id method."""
        from mcli.lib.logger.correlation import (
            CorrelationIdMixin,
            clear_correlation_id,
            set_correlation_id,
        )

        class MyClass(CorrelationIdMixin):
            pass

        obj = MyClass()
        clear_correlation_id()
        assert obj.get_correlation_id() is None

        set_correlation_id("test-id")
        assert obj.get_correlation_id() == "test-id"
        clear_correlation_id()

    def test_mixin_correlation_scope(self):
        """Test mixin correlation_scope context manager."""
        from mcli.lib.logger.correlation import CorrelationIdMixin, clear_correlation_id

        class MyService(CorrelationIdMixin):
            def process(self):
                with self.correlation_scope("request-123") as cid:
                    return cid

        clear_correlation_id()
        service = MyService()
        result = service.process()
        assert result == "request-123"


class TestCorrelationIdThreadSafety:
    """Tests for thread safety of correlation IDs."""

    def test_correlation_id_thread_isolation(self):
        """Test that correlation IDs are isolated between threads."""
        from mcli.lib.logger.correlation import correlation_context, get_correlation_id

        results = {}

        def thread_func(thread_id):
            with correlation_context(f"thread-{thread_id}"):
                # Sleep a bit to increase chance of race condition
                import time

                time.sleep(0.01)
                results[thread_id] = get_correlation_id()

        threads = [threading.Thread(target=thread_func, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have its own correlation ID
        for i in range(10):
            assert results[i] == f"thread-{i}"

    def test_correlation_id_executor_isolation(self):
        """Test correlation ID isolation in thread pool executor."""
        from mcli.lib.logger.correlation import correlation_context, get_correlation_id

        def worker(worker_id):
            with correlation_context(f"worker-{worker_id}"):
                return get_correlation_id()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            results = [f.result() for f in futures]

        # Each worker should get its expected ID
        for i, result in enumerate(results):
            assert result == f"worker-{i}"


class TestStructuredFormatter:
    """Tests for StructuredFormatter."""

    def test_formatter_produces_json(self):
        """Test that formatter produces valid JSON."""
        from mcli.lib.logger.structured import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed

    def test_formatter_includes_correlation_id(self):
        """Test that formatter includes correlation ID when set."""
        from mcli.lib.logger.correlation import correlation_context
        from mcli.lib.logger.structured import StructuredFormatter

        formatter = StructuredFormatter()

        with correlation_context("test-cid"):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            parsed = json.loads(output)

            assert parsed["correlation_id"] == "test-cid"

    def test_formatter_excludes_correlation_id_when_not_set(self):
        """Test that formatter excludes correlation ID when not set."""
        from mcli.lib.logger.correlation import clear_correlation_id
        from mcli.lib.logger.structured import StructuredFormatter

        clear_correlation_id()
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert "correlation_id" not in parsed

    def test_formatter_includes_location(self):
        """Test that formatter includes file location."""
        from mcli.lib.logger.structured import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["location"]["file"] == "test.py"
        assert parsed["location"]["line"] == 42
        assert parsed["location"]["function"] == "test_function"

    def test_formatter_includes_exception_info(self):
        """Test that formatter includes exception information."""
        from mcli.lib.logger.structured import StructuredFormatter

        formatter = StructuredFormatter(include_stack_info=True)

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test error"
        assert parsed["exception"]["traceback"] is not None

    def test_formatter_includes_process_info_when_enabled(self):
        """Test that formatter includes process info when enabled."""
        from mcli.lib.logger.structured import StructuredFormatter

        formatter = StructuredFormatter(include_process_info=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "process_id" in parsed
        assert "thread_id" in parsed
        assert "thread_name" in parsed


class TestCorrelationFilter:
    """Tests for CorrelationFilter."""

    def test_filter_adds_correlation_id(self):
        """Test that filter adds correlation_id attribute to record."""
        from mcli.lib.logger.correlation import clear_correlation_id, set_correlation_id
        from mcli.lib.logger.structured import CorrelationFilter

        clear_correlation_id()
        set_correlation_id("filter-test")

        filter_obj = CorrelationFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)

        assert result is True  # Always allows record
        assert record.correlation_id == "filter-test"
        clear_correlation_id()

    def test_filter_uses_dash_when_no_correlation_id(self):
        """Test that filter uses '-' when no correlation ID set."""
        from mcli.lib.logger.correlation import clear_correlation_id
        from mcli.lib.logger.structured import CorrelationFilter

        clear_correlation_id()

        filter_obj = CorrelationFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert record.correlation_id == "-"


class TestStructuredLogger:
    """Tests for StructuredLogger adapter."""

    def test_structured_logger_with_extra_fields(self):
        """Test StructuredLogger with extra fields in log call."""
        from mcli.lib.logger.structured import StructuredFormatter, StructuredLogger

        # Create a logger with a string handler to capture output
        base_logger = logging.getLogger("test_structured_extra")
        base_logger.setLevel(logging.DEBUG)
        base_logger.propagate = False

        # Clear existing handlers
        base_logger.handlers.clear()

        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        logger = StructuredLogger(base_logger)
        logger.info("Test message", user_id="123", action="login")

        handler.flush()
        log_output = output.getvalue()
        parsed = json.loads(log_output.strip())

        assert parsed["message"] == "Test message"
        assert parsed["extra"]["user_id"] == "123"
        assert parsed["extra"]["action"] == "login"

    def test_structured_logger_with_context(self):
        """Test StructuredLogger with_context method."""
        from mcli.lib.logger.structured import StructuredFormatter, StructuredLogger

        base_logger = logging.getLogger("test_structured_context")
        base_logger.setLevel(logging.DEBUG)
        base_logger.propagate = False
        base_logger.handlers.clear()

        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        logger = StructuredLogger(base_logger)
        request_logger = logger.with_context(request_id="req-456", user="alice")

        request_logger.info("Processing request")

        handler.flush()
        log_output = output.getvalue()
        parsed = json.loads(log_output.strip())

        assert parsed["extra"]["request_id"] == "req-456"
        assert parsed["extra"]["user"] == "alice"

    def test_structured_logger_context_merging(self):
        """Test that contexts are properly merged."""
        from mcli.lib.logger.structured import StructuredFormatter, StructuredLogger

        base_logger = logging.getLogger("test_structured_merge")
        base_logger.setLevel(logging.DEBUG)
        base_logger.propagate = False
        base_logger.handlers.clear()

        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        logger = StructuredLogger(base_logger, {"service": "auth"})
        request_logger = logger.with_context(request_id="req-789")

        request_logger.info("Event", event_type="login")

        handler.flush()
        log_output = output.getvalue()
        parsed = json.loads(log_output.strip())

        assert parsed["extra"]["service"] == "auth"
        assert parsed["extra"]["request_id"] == "req-789"
        assert parsed["extra"]["event_type"] == "login"


class TestGetStructuredLogger:
    """Tests for get_structured_logger function."""

    def test_get_structured_logger_returns_structured_logger(self):
        """Test that get_structured_logger returns a StructuredLogger."""
        from mcli.lib.logger.structured import StructuredLogger, get_structured_logger

        logger = get_structured_logger("test_module")
        assert isinstance(logger, StructuredLogger)

    def test_get_structured_logger_with_extra(self):
        """Test get_structured_logger with default extra context."""
        from mcli.lib.logger.structured import get_structured_logger

        logger = get_structured_logger("test_module", extra={"version": "1.0"})
        assert logger.extra["version"] == "1.0"

    def test_get_structured_logger_fallback_on_error(self):
        """Test that logger falls back gracefully on file error."""
        # Reset logger to force recreation
        test_logger = logging.getLogger("test_fallback_error_v2")
        test_logger.handlers.clear()

        with patch("mcli.lib.paths.get_logs_dir") as mock_logs_dir:
            mock_logs_dir.side_effect = Exception("Permission denied")

            from mcli.lib.logger.structured import get_structured_logger

            # Should not raise - falls back to console
            logger = get_structured_logger(
                "test_fallback_error_v2", log_to_file=True, log_to_console=True
            )
            assert logger is not None


class TestConfigureStructuredLogging:
    """Tests for configure_structured_logging function."""

    def test_configure_adds_correlation_filter(self):
        """Test that configure_structured_logging adds correlation filter."""
        from mcli.lib.logger.structured import CorrelationFilter, configure_structured_logging

        configure_structured_logging()

        root_logger = logging.getLogger()
        has_correlation_filter = any(isinstance(f, CorrelationFilter) for f in root_logger.filters)
        assert has_correlation_filter

    def test_configure_sets_level(self):
        """Test that configure_structured_logging sets root level."""
        from mcli.lib.logger.structured import configure_structured_logging

        configure_structured_logging(root_level=logging.WARNING)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING


class TestIntegration:
    """Integration tests for the full logging stack."""

    def test_full_stack_with_correlation_id(self):
        """Test full logging stack with correlation ID."""
        from mcli.lib.logger.correlation import correlation_context
        from mcli.lib.logger.structured import StructuredFormatter, StructuredLogger

        # Set up logger with string output
        base_logger = logging.getLogger("test_full_stack")
        base_logger.setLevel(logging.DEBUG)
        base_logger.propagate = False
        base_logger.handlers.clear()

        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())
        base_logger.addHandler(handler)

        logger = StructuredLogger(base_logger)

        with correlation_context("full-stack-test"):
            logger.info("Request started", endpoint="/api/users")
            logger.debug("Processing", step=1)
            logger.info("Request completed", status=200)

        handler.flush()
        lines = output.getvalue().strip().split("\n")

        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert parsed["correlation_id"] == "full-stack-test"

    def test_nested_function_calls_share_correlation_id(self):
        """Test that nested function calls share correlation ID."""
        from mcli.lib.logger.correlation import correlation_context, get_correlation_id

        captured_ids = []

        def outer():
            captured_ids.append(get_correlation_id())
            inner()

        def inner():
            captured_ids.append(get_correlation_id())
            deepest()

        def deepest():
            captured_ids.append(get_correlation_id())

        with correlation_context("shared-id"):
            outer()

        assert all(cid == "shared-id" for cid in captured_ids)
        assert len(captured_ids) == 3
