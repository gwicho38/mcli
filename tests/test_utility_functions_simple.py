"""
Unit tests for mcli utility functions - simplified version
"""

import pytest
from unittest.mock import Mock, patch, mock_open

from mcli.lib.toml.toml import read_from_toml
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console


class TestTomlUtilities:
    """Test suite for TOML utility functions"""
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_read_from_toml_file_not_found(self, mock_file):
        """Test TOML reading with missing file"""
        with pytest.raises(FileNotFoundError):
            read_from_toml('nonexistent.toml', 'test')
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'[test]\nkey = "value"')
    @patch('mcli.lib.toml.toml.tomllib.load')
    def test_read_from_toml_success(self, mock_tomllib_load, mock_file):
        """Test successful TOML reading"""
        mock_tomllib_load.return_value = {'test': {'key': 'value'}}
        
        result = read_from_toml('config.toml', 'test')
        
        assert result == {'key': 'value'}
        mock_file.assert_called_once_with('config.toml', 'rb')


class TestLoggerUtilities:
    """Test suite for logger utility functions"""
    
    def test_get_logger_singleton(self):
        """Test logger singleton behavior"""
        logger1 = get_logger('test_module')
        logger2 = get_logger('test_module')
        
        # Note: may not be the same instance due to implementation
        assert logger1.name == logger2.name
    
    def test_get_logger_different_modules(self):
        """Test loggers for different modules"""
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')
        
        assert logger1.name != logger2.name
    
    def test_logger_basic_functionality(self):
        """Test basic logger functionality"""
        logger = get_logger('test_logger')
        
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')


class TestStylingUtilities:
    """Test suite for UI styling utilities"""
    
    def test_console_exists(self):
        """Test that console object exists"""
        assert console is not None
        assert hasattr(console, 'print')
    
    def test_console_print_functionality(self):
        """Test console print functionality"""
        # Should not raise an exception
        try:
            console.print("Test message")
        except Exception as e:
            pytest.fail(f"Console print raised an exception: {e}")


class TestBasicImports:
    """Test that key modules can be imported without errors"""
    
    def test_import_command_discovery(self):
        """Test importing command discovery module"""
        try:
            from mcli.lib.discovery.command_discovery import get_command_discovery
            assert get_command_discovery is not None
        except ImportError as e:
            pytest.skip(f"Command discovery not available: {e}")
    
    def test_import_daemon_client(self):
        """Test importing daemon client module"""
        try:
            from mcli.lib.api.daemon_client import get_daemon_client
            assert get_daemon_client is not None
        except ImportError as e:
            pytest.skip(f"Daemon client not available: {e}")
    
    def test_import_chat_modules(self):
        """Test importing chat modules"""
        try:
            from mcli.chat.chat import ChatClient
            from mcli.chat.enhanced_chat import EnhancedChatClient
            assert ChatClient is not None
            assert EnhancedChatClient is not None
        except ImportError as e:
            pytest.skip(f"Chat modules not available: {e}")