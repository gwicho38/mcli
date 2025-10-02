"""
Unit tests for mcli utility functions and helper modules
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import os

# Import utility modules to test  
from mcli.lib.toml.toml import read_from_toml
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console


class TestTomlUtilities:
    """Test suite for TOML utility functions"""
    
    @patch('builtins.open', new_callable=mock_open, read_data='[test]\nkey = "value"')
    @patch('mcli.lib.toml.toml.tomllib.load')
    def test_read_from_toml_success(self, mock_tomllib_load, mock_file):
        """Test successful TOML reading"""
        mock_tomllib_load.return_value = {'test': {'key': 'value'}}
        
        result = read_from_toml('config.toml', 'test')
        
        assert result == {'key': 'value'}
        mock_file.assert_called_once_with('config.toml', 'rb')
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_read_from_toml_file_not_found(self, mock_file):
        """Test TOML reading with missing file"""
        result = read_from_toml('nonexistent.toml', 'test')
        
        assert result is None
    
    @patch('builtins.open', new_callable=mock_open, read_data='invalid toml content')
    @patch('mcli.lib.toml.toml.tomllib.load')
    def test_read_from_toml_invalid_content(self, mock_tomllib_load, mock_file):
        """Test TOML reading with invalid content"""
        import tomllib
        mock_tomllib_load.side_effect = tomllib.TOMLDecodeError("Invalid TOML", "", 0)
        
        with pytest.raises(tomllib.TOMLDecodeError):
            read_from_toml('invalid.toml', 'test')


class TestLoggerUtilities:
    """Test suite for logger utility functions"""
    
    def test_get_logger_singleton(self):
        """Test logger singleton behavior"""
        logger1 = get_logger('test_module')
        logger2 = get_logger('test_module')
        
        assert logger1 is logger2
    
    def test_get_logger_different_modules(self):
        """Test loggers for different modules"""
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')
        
        assert logger1 is not logger2
        assert logger1.name != logger2.name
    
    @patch('mcli.lib.logger.logger.sys.settrace')
    def test_enable_runtime_tracing(self, mock_settrace):
        """Test enabling runtime tracing"""
        enable_runtime_tracing(level=2)
        
        mock_settrace.assert_called_once()
    
    @patch('mcli.lib.logger.logger.sys.settrace')
    def test_disable_runtime_tracing(self, mock_settrace):
        """Test disabling runtime tracing"""
        disable_runtime_tracing()
        
        mock_settrace.assert_called_once_with(None)
    
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
    
    @patch('mcli.lib.ui.styling.console')
    def test_success_message(self, mock_console):
        """Test success message styling"""
        success("Test success message")
        
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0]
        assert "success" in str(args[0]).lower() or "[green]" in str(args[0])
    
    @patch('mcli.lib.ui.styling.console')
    def test_info_message(self, mock_console):
        """Test info message styling"""
        info("Test info message")
        
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0]
        assert "info" in str(args[0]).lower() or "[blue]" in str(args[0])
    
    @patch('mcli.lib.ui.styling.console')
    def test_warning_message(self, mock_console):
        """Test warning message styling"""
        warning("Test warning message")
        
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0]
        assert "warning" in str(args[0]).lower() or "[yellow]" in str(args[0])
    
    @patch('mcli.lib.ui.styling.console')
    def test_error_message(self, mock_console):
        """Test error message styling"""
        error("Test error message")
        
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0]
        assert "error" in str(args[0]).lower() or "[red]" in str(args[0])


class TestFileSystemUtilities:
    """Test suite for filesystem utility functions"""
    
    @patch('mcli.lib.fs.fs.Path.mkdir')
    @patch('mcli.lib.fs.fs.Path.exists')
    def test_ensure_directory_new(self, mock_exists, mock_mkdir):
        """Test creating new directory"""
        mock_exists.return_value = False
        
        result = ensure_directory(Path('/test/new/dir'))
        
        assert result is True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('mcli.lib.fs.fs.Path.exists')
    def test_ensure_directory_exists(self, mock_exists):
        """Test directory that already exists"""
        mock_exists.return_value = True
        
        result = ensure_directory(Path('/test/existing/dir'))
        
        assert result is True
    
    @patch('mcli.lib.fs.fs.Path.mkdir')
    @patch('mcli.lib.fs.fs.Path.exists')
    def test_ensure_directory_permission_error(self, mock_exists, mock_mkdir):
        """Test directory creation with permission error"""
        mock_exists.return_value = False
        mock_mkdir.side_effect = PermissionError("Permission denied")
        
        result = ensure_directory(Path('/root/restricted'))
        
        assert result is False
    
    @patch('builtins.open', new_callable=mock_open, read_data='test file content')
    def test_read_file_success(self, mock_file):
        """Test successful file reading"""
        result = read_file(Path('/test/file.txt'))
        
        assert result == 'test file content'
        mock_file.assert_called_once_with(Path('/test/file.txt'), 'r', encoding='utf-8')
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_read_file_not_found(self, mock_file):
        """Test reading non-existent file"""
        result = read_file(Path('/test/nonexistent.txt'))
        
        assert result is None
    
    @patch('builtins.open', new_callable=mock_open)
    def test_write_file_success(self, mock_file):
        """Test successful file writing"""
        result = write_file(Path('/test/output.txt'), 'test content')
        
        assert result is True
        mock_file.assert_called_once_with(Path('/test/output.txt'), 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with('test content')
    
    @patch('builtins.open', side_effect=PermissionError)
    def test_write_file_permission_error(self, mock_file):
        """Test file writing with permission error"""
        result = write_file(Path('/root/restricted.txt'), 'content')
        
        assert result is False


class TestConfigUtilities:
    """Test suite for configuration utility functions"""
    
    @patch('mcli.lib.config.config.read_from_toml')
    def test_load_config_success(self, mock_read_toml):
        """Test successful config loading"""
        mock_read_toml.return_value = {
            'database': {'host': 'localhost', 'port': 5432},
            'api': {'key': 'secret123'}
        }
        
        result = load_config('app.toml')
        
        assert result is not None
        assert 'database' in result
        assert result['database']['host'] == 'localhost'
    
    @patch('mcli.lib.config.config.read_from_toml')
    def test_load_config_file_not_found(self, mock_read_toml):
        """Test config loading with missing file"""
        mock_read_toml.return_value = None
        
        result = load_config('nonexistent.toml')
        
        assert result == {}
    
    @patch('mcli.lib.config.config.write_to_toml')
    def test_save_config_success(self, mock_write_toml):
        """Test successful config saving"""
        mock_write_toml.return_value = True
        
        config_data = {'test': {'value': 123}}
        result = save_config('app.toml', config_data)
        
        assert result is True
        mock_write_toml.assert_called_once_with('app.toml', config_data)
    
    def test_get_config_value_existing_key(self):
        """Test getting existing config value"""
        config = {
            'database': {'host': 'localhost', 'port': 5432},
            'api': {'timeout': 30}
        }
        
        result = get_config_value(config, 'database.host')
        assert result == 'localhost'
        
        result = get_config_value(config, 'database.port')
        assert result == 5432
    
    def test_get_config_value_missing_key(self):
        """Test getting missing config value"""
        config = {'database': {'host': 'localhost'}}
        
        result = get_config_value(config, 'database.port', default=5432)
        assert result == 5432
        
        result = get_config_value(config, 'nonexistent.key')
        assert result is None
    
    def test_get_config_value_nested_missing(self):
        """Test getting value from missing nested section"""
        config = {'database': {'host': 'localhost'}}
        
        result = get_config_value(config, 'api.key', default='default_key')
        assert result == 'default_key'


class TestPerformanceUtilities:
    """Test suite for performance utility functions"""
    
    @patch('mcli.lib.performance.optimizer.asyncio')
    @patch('mcli.lib.performance.optimizer.sys.platform', 'linux')
    def test_enable_uvloop_linux(self, mock_asyncio):
        """Test enabling uvloop on Linux"""
        from mcli.lib.performance.optimizer import enable_uvloop
        
        result = enable_uvloop()
        
        assert result is True
    
    @patch('mcli.lib.performance.optimizer.sys.platform', 'win32')
    def test_enable_uvloop_windows(self):
        """Test uvloop on Windows (should be disabled)"""
        from mcli.lib.performance.optimizer import enable_uvloop
        
        result = enable_uvloop()
        
        assert result is False  # uvloop not supported on Windows
    
    def test_rust_bridge_import(self):
        """Test Rust bridge import"""
        try:
            from mcli.lib.performance.rust_bridge import get_rust_extensions
            
            # Should not raise ImportError
            extensions = get_rust_extensions()
            assert isinstance(extensions, dict)
            
        except ImportError:
            # Rust extensions may not be compiled in test environment
            pytest.skip("Rust extensions not available")


class TestAuthUtilities:
    """Test suite for authentication utility functions"""
    
    @patch('mcli.lib.auth.credential_manager.keyring')
    def test_store_credential(self, mock_keyring):
        """Test storing credentials"""
        from mcli.lib.auth.credential_manager import store_credential
        
        mock_keyring.set_password.return_value = None
        
        result = store_credential('test_service', 'test_user', 'test_password')
        
        assert result is True
        mock_keyring.set_password.assert_called_once_with('test_service', 'test_user', 'test_password')
    
    @patch('mcli.lib.auth.credential_manager.keyring')
    def test_get_credential(self, mock_keyring):
        """Test retrieving credentials"""
        from mcli.lib.auth.credential_manager import get_credential
        
        mock_keyring.get_password.return_value = 'stored_password'
        
        result = get_credential('test_service', 'test_user')
        
        assert result == 'stored_password'
        mock_keyring.get_password.assert_called_once_with('test_service', 'test_user')
    
    @patch('mcli.lib.auth.credential_manager.keyring')
    def test_get_credential_not_found(self, mock_keyring):
        """Test retrieving non-existent credentials"""
        from mcli.lib.auth.credential_manager import get_credential
        
        mock_keyring.get_password.return_value = None
        
        result = get_credential('test_service', 'nonexistent_user')
        
        assert result is None