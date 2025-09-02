"""
Unit tests for mcli.lib.discovery.command_discovery module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from mcli.lib.discovery.command_discovery import (
    get_command_discovery,
    CommandDiscovery
)


class TestCommandDiscovery:
    """Test suite for CommandDiscovery functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.discovery = CommandDiscovery()
    
    def test_command_discovery_initialization(self):
        """Test CommandDiscovery initialization"""
        assert self.discovery is not None
        assert hasattr(self.discovery, 'discovered_commands')
        assert isinstance(self.discovery.discovered_commands, dict)
    
    @patch('mcli.lib.discovery.command_discovery.Path.iterdir')
    @patch('mcli.lib.discovery.command_discovery.Path.is_file')
    def test_discover_commands_in_directory(self, mock_is_file, mock_iterdir):
        """Test discovering commands in a directory"""
        # Mock file structure
        mock_file = Mock()
        mock_file.name = 'test_command.py'
        mock_file.suffix = '.py'
        mock_file.stem = 'test_command'
        
        mock_iterdir.return_value = [mock_file]
        mock_is_file.return_value = True
        
        with patch.object(self.discovery, '_load_command_from_file') as mock_load:
            mock_load.return_value = {
                'name': 'test-command',
                'description': 'Test command',
                'module_path': 'test.test_command'
            }
            
            result = self.discovery.discover_commands_in_directory(Path('/test/path'))
            
            assert isinstance(result, list)
            mock_load.assert_called_once()
    
    @patch('mcli.lib.discovery.command_discovery.importlib.util.spec_from_file_location')
    @patch('mcli.lib.discovery.command_discovery.importlib.util.module_from_spec')
    def test_load_command_from_file_success(self, mock_module_from_spec, mock_spec_from_file):
        """Test successfully loading command from file"""
        # Mock module loading
        mock_spec = Mock()
        mock_module = Mock()
        mock_command = Mock()
        mock_command.name = 'test-cmd'
        mock_command.help = 'Test command help'
        
        mock_spec_from_file.return_value = mock_spec
        mock_module_from_spec.return_value = mock_module
        mock_module.cli = mock_command
        mock_spec.loader = Mock()
        
        file_path = Path('/test/command.py')
        result = self.discovery._load_command_from_file(file_path)
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'description' in result
        assert 'module_path' in result
    
    def test_load_command_from_file_no_cli_attribute(self):
        """Test loading file without cli attribute"""
        with patch('mcli.lib.discovery.command_discovery.importlib.util.spec_from_file_location') as mock_spec, \
             patch('mcli.lib.discovery.command_discovery.importlib.util.module_from_spec') as mock_module_from_spec:
            
            mock_spec.return_value = Mock()
            mock_module = Mock()
            del mock_module.cli  # No cli attribute
            mock_module_from_spec.return_value = mock_module
            mock_spec.return_value.loader = Mock()
            
            result = self.discovery._load_command_from_file(Path('/test/command.py'))
            
            assert result is None
    
    def test_load_command_from_file_import_error(self):
        """Test handling import errors when loading commands"""
        with patch('mcli.lib.discovery.command_discovery.importlib.util.spec_from_file_location') as mock_spec:
            mock_spec.side_effect = ImportError("Module not found")
            
            result = self.discovery._load_command_from_file(Path('/test/command.py'))
            
            assert result is None
    
    def test_register_command(self):
        """Test registering a command"""
        command_info = {
            'name': 'test-cmd',
            'description': 'Test command',
            'module_path': 'test.command',
            'file_path': '/test/command.py'
        }
        
        self.discovery.register_command(command_info)
        
        assert 'test-cmd' in self.discovery.discovered_commands
        assert self.discovery.discovered_commands['test-cmd'] == command_info
    
    def test_get_command(self):
        """Test getting a specific command"""
        # Register a command first
        command_info = {
            'name': 'test-cmd',
            'description': 'Test command'
        }
        self.discovery.register_command(command_info)
        
        result = self.discovery.get_command('test-cmd')
        
        assert result == command_info
    
    def test_get_command_not_found(self):
        """Test getting a non-existent command"""
        result = self.discovery.get_command('nonexistent-cmd')
        
        assert result is None
    
    def test_list_commands(self):
        """Test listing all discovered commands"""
        # Register some commands
        self.discovery.register_command({'name': 'cmd1', 'description': 'Command 1'})
        self.discovery.register_command({'name': 'cmd2', 'description': 'Command 2'})
        
        result = self.discovery.list_commands()
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert any(cmd['name'] == 'cmd1' for cmd in result)
        assert any(cmd['name'] == 'cmd2' for cmd in result)
    
    def test_search_commands_by_name(self):
        """Test searching commands by name"""
        # Register some commands
        self.discovery.register_command({'name': 'file-list', 'description': 'List files'})
        self.discovery.register_command({'name': 'file-copy', 'description': 'Copy files'})
        self.discovery.register_command({'name': 'process-list', 'description': 'List processes'})
        
        result = self.discovery.search_commands('file')
        
        assert len(result) == 2
        assert all('file' in cmd['name'] for cmd in result)
    
    def test_search_commands_by_description(self):
        """Test searching commands by description"""
        # Register some commands
        self.discovery.register_command({'name': 'ls', 'description': 'List directory contents'})
        self.discovery.register_command({'name': 'ps', 'description': 'List running processes'})
        self.discovery.register_command({'name': 'grep', 'description': 'Search text patterns'})
        
        result = self.discovery.search_commands('list')
        
        assert len(result) == 2
        assert all('list' in cmd['description'].lower() for cmd in result)
    
    def test_search_commands_case_insensitive(self):
        """Test case insensitive command search"""
        self.discovery.register_command({'name': 'FILE-cmd', 'description': 'File operations'})
        
        result = self.discovery.search_commands('file')
        
        assert len(result) == 1
        assert result[0]['name'] == 'FILE-cmd'
    
    def test_get_command_categories(self):
        """Test getting command categories"""
        # Register commands with different categories
        self.discovery.register_command({
            'name': 'file-cmd', 
            'description': 'File operations',
            'category': 'file'
        })
        self.discovery.register_command({
            'name': 'process-cmd', 
            'description': 'Process management',
            'category': 'system'
        })
        
        result = self.discovery.get_command_categories()
        
        assert isinstance(result, dict)
        assert 'file' in result
        assert 'system' in result
        assert len(result['file']) == 1
        assert len(result['system']) == 1
    
    def test_validate_command_structure(self):
        """Test command structure validation"""
        valid_command = {
            'name': 'test-cmd',
            'description': 'Test command',
            'module_path': 'test.command'
        }
        
        invalid_command = {
            'name': '',  # Invalid: empty name
            'description': 'Test command'
        }
        
        assert self.discovery._validate_command_structure(valid_command) is True
        assert self.discovery._validate_command_structure(invalid_command) is False
    
    def test_refresh_commands(self):
        """Test refreshing command discovery"""
        with patch.object(self.discovery, 'discover_commands_in_directory') as mock_discover:
            mock_discover.return_value = [
                {'name': 'new-cmd', 'description': 'New command'}
            ]
            
            # Add a command first
            self.discovery.register_command({'name': 'old-cmd', 'description': 'Old command'})
            
            self.discovery.refresh_commands([Path('/test/path')])
            
            mock_discover.assert_called_once()
            # Should have refreshed the commands
    
    def test_get_command_dependencies(self):
        """Test getting command dependencies"""
        command_info = {
            'name': 'test-cmd',
            'description': 'Test command',
            'dependencies': ['click', 'requests']
        }
        self.discovery.register_command(command_info)
        
        deps = self.discovery.get_command_dependencies('test-cmd')
        
        assert deps == ['click', 'requests']
    
    def test_get_command_dependencies_none(self):
        """Test getting dependencies for command without dependencies"""
        command_info = {
            'name': 'simple-cmd',
            'description': 'Simple command'
        }
        self.discovery.register_command(command_info)
        
        deps = self.discovery.get_command_dependencies('simple-cmd')
        
        assert deps == []
    
    def test_export_commands_manifest(self):
        """Test exporting commands manifest"""
        self.discovery.register_command({'name': 'cmd1', 'description': 'Command 1'})
        self.discovery.register_command({'name': 'cmd2', 'description': 'Command 2'})
        
        manifest = self.discovery.export_commands_manifest()
        
        assert isinstance(manifest, dict)
        assert 'commands' in manifest
        assert 'metadata' in manifest
        assert len(manifest['commands']) == 2


class TestCommandDiscoveryGlobalFunction:
    """Test suite for global command discovery functions"""
    
    def test_get_command_discovery_singleton(self):
        """Test that get_command_discovery returns a singleton"""
        discovery1 = get_command_discovery()
        discovery2 = get_command_discovery()
        
        assert discovery1 is discovery2
        assert isinstance(discovery1, CommandDiscovery)
    
    @patch('mcli.lib.discovery.command_discovery.CommandDiscovery')
    def test_get_command_discovery_initialization(self, mock_discovery_class):
        """Test command discovery initialization"""
        mock_instance = Mock()
        mock_discovery_class.return_value = mock_instance
        
        # Clear any existing singleton
        if hasattr(get_command_discovery, '_instance'):
            delattr(get_command_discovery, '_instance')
        
        result = get_command_discovery()
        
        mock_discovery_class.assert_called_once()
        assert result == mock_instance