"""
Unit tests for mcli.lib.logger module
"""

import pytest
from unittest.mock import patch, MagicMock
import logging


class TestMcliLogger:
    """Test suite for McliLogger"""

    def test_get_logger(self):
        """Test getting logger instance"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger(__name__)

        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')

    def test_get_logger_singleton(self):
        """Test that get_logger returns same instance"""
        from mcli.lib.logger.logger import McliLogger

        logger1 = McliLogger.get_logger()
        logger2 = McliLogger.get_logger()

        assert logger1 is logger2

    def test_get_logger_with_name(self):
        """Test getting logger with custom name"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger("custom.module")

        assert logger is not None

    def test_logger_info(self):
        """Test logging at INFO level"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger(__name__)

        # Should not raise any errors
        logger.info("Test info message")
        logger.info("Test with %s formatting", "params")

    def test_logger_error(self):
        """Test logging at ERROR level"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger(__name__)

        logger.error("Test error message")
        logger.error("Error with %d code", 500)

    def test_logger_warning(self):
        """Test logging at WARNING level"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger(__name__)

        logger.warning("Test warning message")

    def test_logger_debug(self):
        """Test logging at DEBUG level"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger(__name__)

        logger.debug("Test debug message")

    def test_enable_runtime_tracing(self):
        """Test enabling runtime tracing"""
        from mcli.lib.logger.logger import McliLogger

        # Enable tracing
        McliLogger.enable_runtime_tracing(level=1)

        # Should enable successfully
        assert McliLogger._runtime_tracing_enabled is True
        assert McliLogger._trace_level == 1

    def test_enable_runtime_tracing_with_level(self):
        """Test enabling tracing with different levels"""
        from mcli.lib.logger.logger import McliLogger

        McliLogger.enable_runtime_tracing(level=2)
        assert McliLogger._trace_level == 2

        McliLogger.enable_runtime_tracing(level=3)
        assert McliLogger._trace_level == 3

    def test_enable_runtime_tracing_invalid_level(self):
        """Test tracing level is clamped to valid range"""
        from mcli.lib.logger.logger import McliLogger

        McliLogger.enable_runtime_tracing(level=10)
        assert McliLogger._trace_level == 3  # Clamped to max

        McliLogger.enable_runtime_tracing(level=-5)
        assert McliLogger._trace_level == 0  # Clamped to min

    def test_disable_runtime_tracing(self):
        """Test disabling runtime tracing"""
        from mcli.lib.logger.logger import McliLogger

        # Enable first
        McliLogger.enable_runtime_tracing(level=1)
        assert McliLogger._runtime_tracing_enabled is True

        # Disable
        McliLogger.disable_runtime_tracing()
        assert McliLogger._runtime_tracing_enabled is False

    def test_enable_tracing_with_excluded_modules(self):
        """Test enabling tracing with module exclusions"""
        from mcli.lib.logger.logger import McliLogger

        excluded = ['test_module', 'another_module']
        McliLogger.enable_runtime_tracing(level=1, excluded_modules=excluded)

        assert 'test_module' in McliLogger._excluded_modules
        assert 'another_module' in McliLogger._excluded_modules

    def test_get_trace_logger(self):
        """Test getting trace logger instance"""
        from mcli.lib.logger.logger import McliLogger

        trace_logger = McliLogger.get_trace_logger()

        assert trace_logger is not None

    def test_get_system_trace_logger(self):
        """Test getting system trace logger"""
        from mcli.lib.logger.logger import McliLogger

        sys_logger = McliLogger.get_system_trace_logger()

        assert sys_logger is not None

    def test_enable_system_tracing(self):
        """Test enabling system process tracing"""
        from mcli.lib.logger.logger import McliLogger

        McliLogger.enable_system_tracing(level=1)

        assert McliLogger._system_tracing_enabled is True
        assert McliLogger._system_trace_level == 1

    def test_enable_system_tracing_with_interval(self):
        """Test system tracing with custom interval"""
        from mcli.lib.logger.logger import McliLogger

        McliLogger.enable_system_tracing(level=1, interval=10)

        assert McliLogger._system_trace_interval == 10

    def test_disable_system_tracing(self):
        """Test disabling system tracing"""
        from mcli.lib.logger.logger import McliLogger

        # Enable first
        McliLogger.enable_system_tracing(level=1)
        assert McliLogger._system_tracing_enabled is True

        # Disable
        McliLogger.disable_system_tracing()
        assert McliLogger._system_tracing_enabled is False

    def test_logger_instance_isolation(self):
        """Test that loggers are properly isolated"""
        from mcli.lib.logger.logger import get_logger

        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Both should exist
        assert logger1 is not None
        assert logger2 is not None

    def test_logger_handles_exceptions(self):
        """Test logger handles exceptions in messages"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger(__name__)

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            # Should not raise
            logger.error("Exception occurred: %s", e)
            logger.exception("Full traceback:")

    def test_logger_formatting(self):
        """Test logger message formatting"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger(__name__)

        # Various formatting styles
        logger.info("Simple message")
        logger.info("With %s", "string")
        logger.info("Multiple %s %d", "params", 42)
        logger.info("Dict: %s", {"key": "value"})

    def test_get_logger_function_standalone(self):
        """Test standalone get_logger function"""
        from mcli.lib.logger.logger import get_logger

        logger = get_logger()

        assert logger is not None
        assert isinstance(logger, logging.Logger)
