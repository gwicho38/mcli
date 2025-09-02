"""
Unit tests for mcli.app.main module functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

from mcli.app.main import (
    discover_modules,
    create_app,
    main,
    get_version_info
)


class TestMainAppFunctions:
    """Test suite for main app functionality"""
    
    def test_discover_modules_basic(self):
        """Test basic module discovery"""
        with patch('mcli.app.main.Path.iterdir') as mock_iterdir, \
             patch('mcli.app.main.Path.is_dir') as mock_is_dir, \
             patch('mcli.app.main.Path.exists') as mock_exists:
            
            # Mock directory structure
            mock_module = Mock()
            mock_module.name = 'test_module.py'
            mock_module.suffix = '.py'
            mock_module.stem = 'test_module'
            
            mock_init = Mock()
            mock_init.name = '__init__.py'
            
            mock_iterdir.return_value = [mock_module, mock_init]
            mock_is_dir.return_value = False
            mock_exists.return_value = True
            
            base_path = Path('/test/path')
            result = discover_modules(base_path)
            
            assert isinstance(result, list)
            # Should find modules in the path
    
    def test_discover_modules_with_config(self):
        """Test module discovery with config file"""
        with patch('mcli.app.main.Path.iterdir') as mock_iterdir, \
             patch('mcli.app.main.Path.is_dir') as mock_is_dir, \
             patch('mcli.app.main.Path.exists') as mock_exists, \
             patch('mcli.app.main.tomli.load') as mock_tomli:
            
            mock_iterdir.return_value = []
            mock_is_dir.return_value = False
            mock_exists.return_value = True
            mock_tomli.return_value = {'exclude': []}
            
            base_path = Path('/test/path')
            config_path = Path('/test/config.toml')
            
            result = discover_modules(base_path, config_path)
            
            assert isinstance(result, list)
    
    def test_discover_modules_nonexistent_path(self):
        """Test module discovery with non-existent path"""
        with patch('mcli.app.main.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            base_path = Path('/nonexistent/path')
            result = discover_modules(base_path)
            
            assert result == []
    
    def test_get_version_info_basic(self):
        """Test getting version info"""
        result = get_version_info()
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_version_info_verbose(self):
        """Test getting verbose version info"""
        result = get_version_info(verbose=True)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Verbose should contain more information
    
    @patch('mcli.app.main.click')
    def test_create_app_basic(self, mock_click):
        """Test basic app creation"""
        mock_group = Mock()
        mock_click.Group.return_value = mock_group
        
        with patch('mcli.app.main.discover_modules') as mock_discover, \
             patch('mcli.app.main.importlib.import_module') as mock_import:
            
            mock_discover.return_value = ['test_module']
            mock_module = Mock()
            mock_module.cli = Mock()
            mock_import.return_value = mock_module
            
            app = create_app()
            
            assert app is not None
            mock_click.Group.assert_called()
    
    @patch('mcli.app.main.create_app')
    @patch('mcli.app.main.sys.argv', ['mcli', '--help'])
    def test_main_function_help(self, mock_create_app):
        """Test main function with help flag"""
        mock_app = Mock()
        mock_create_app.return_value = mock_app
        
        # Mock app invocation
        mock_app.invoke = Mock(side_effect=SystemExit(0))
        
        with pytest.raises(SystemExit):
            main()
        
        mock_create_app.assert_called_once()
    
    @patch('mcli.app.main.create_app')
    def test_main_function_exception_handling(self, mock_create_app):
        """Test main function exception handling"""
        mock_create_app.side_effect = Exception("Test error")
        
        with patch('mcli.app.main.logger') as mock_logger, \
             patch('mcli.app.main.sys.exit') as mock_exit:
            
            main()
            
            mock_logger.error.assert_called()
            mock_exit.assert_called_with(1)
    
    # Additional tests can be added for other main functions as needed
    pass


def mock_open(*args, **kwargs):
    """Mock open function for file operations"""
    return MagicMock()