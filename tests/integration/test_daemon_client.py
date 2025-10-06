"""
Unit tests for mcli.lib.api.daemon_client module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import json

# Try to import daemon client
try:
    from mcli.lib.api.daemon_client import (
        get_daemon_client,
        APIDaemonClient as DaemonClient
    )
    HAS_DAEMON_CLIENT = True
except ImportError:
    HAS_DAEMON_CLIENT = False


@pytest.mark.skipif(not HAS_DAEMON_CLIENT, reason="daemon_client module not available")
class TestDaemonClient:
    """Test suite for DaemonClient functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = DaemonClient(base_url='http://localhost:8000')
    
    def test_daemon_client_initialization(self):
        """Test DaemonClient initialization"""
        assert self.client.base_url == 'http://localhost:8000'
        assert self.client.session is not None
        assert isinstance(self.client.session, requests.Session)
    
    def test_daemon_client_custom_base_url(self):
        """Test DaemonClient with custom base URL"""
        client = DaemonClient(base_url='http://custom.host:9000')
        
        assert client.base_url == 'http://custom.host:9000'
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_ping_success(self, mock_get):
        """Test successful ping to daemon"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'ok'}
        mock_get.return_value = mock_response
        
        result = self.client.ping()
        
        assert result is True
        mock_get.assert_called_once_with(f'{self.client.base_url}/health')
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_ping_failure(self, mock_get):
        """Test failed ping to daemon"""
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        
        result = self.client.ping()
        
        assert result is False
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_ping_http_error(self, mock_get):
        """Test ping with HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = self.client.ping()
        
        assert result is False
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_list_commands_success(self, mock_get):
        """Test successful command listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'commands': [
                {'name': 'test-cmd', 'description': 'Test command'},
                {'name': 'another-cmd', 'description': 'Another command'}
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.client.list_commands()
        
        assert len(result) == 2
        assert result[0]['name'] == 'test-cmd'
        assert result[1]['name'] == 'another-cmd'
        mock_get.assert_called_once_with(f'{self.client.base_url}/commands')
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_list_commands_failure(self, mock_get):
        """Test failed command listing"""
        mock_get.side_effect = requests.RequestException("Request failed")
        
        result = self.client.list_commands()
        
        assert result == []
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_get_command_success(self, mock_get):
        """Test successfully getting a specific command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'test-cmd',
            'description': 'Test command',
            'parameters': []
        }
        mock_get.return_value = mock_response
        
        result = self.client.get_command('test-cmd')
        
        assert result is not None
        assert result['name'] == 'test-cmd'
        mock_get.assert_called_once_with(f'{self.client.base_url}/commands/test-cmd')
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_get_command_not_found(self, mock_get):
        """Test getting a non-existent command"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.client.get_command('nonexistent-cmd')
        
        assert result is None
    
    @patch('mcli.lib.api.daemon_client.requests.Session.post')
    def test_execute_command_success(self, mock_post):
        """Test successful command execution"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'output': 'Command executed successfully',
            'execution_time': 0.5
        }
        mock_post.return_value = mock_response
        
        result = self.client.execute_command('test-cmd', {'param1': 'value1'})
        
        assert result is not None
        assert result['status'] == 'success'
        assert result['output'] == 'Command executed successfully'
        mock_post.assert_called_once()
    
    @patch('mcli.lib.api.daemon_client.requests.Session.post')
    def test_execute_command_failure(self, mock_post):
        """Test failed command execution"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'status': 'error',
            'error': 'Invalid parameters'
        }
        mock_post.return_value = mock_response
        
        result = self.client.execute_command('test-cmd', {'invalid': 'params'})
        
        assert result is not None
        assert result['status'] == 'error'
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_list_processes_success(self, mock_get):
        """Test successful process listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'processes': [
                {'id': '123', 'name': 'test-process', 'status': 'running'},
                {'id': '456', 'name': 'another-process', 'status': 'stopped'}
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.client.list_processes()
        
        assert len(result) == 2
        assert result[0]['id'] == '123'
        assert result[1]['status'] == 'stopped'
        mock_get.assert_called_once_with(f'{self.client.base_url}/processes')
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_get_process_status_success(self, mock_get):
        """Test getting process status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '123',
            'name': 'test-process',
            'status': 'running',
            'cpu_usage': 15.5,
            'memory_usage': 128
        }
        mock_get.return_value = mock_response
        
        result = self.client.get_process_status('123')
        
        assert result is not None
        assert result['status'] == 'running'
        assert result['cpu_usage'] == 15.5
        mock_get.assert_called_once_with(f'{self.client.base_url}/processes/123')
    
    @patch('mcli.lib.api.daemon_client.requests.Session.post')
    def test_start_process_success(self, mock_post):
        """Test starting a process"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'process_id': '789',
            'message': 'Process started successfully'
        }
        mock_post.return_value = mock_response
        
        result = self.client.start_process('test-command', ['arg1', 'arg2'])
        
        assert result is not None
        assert result['status'] == 'success'
        assert result['process_id'] == '789'
        mock_post.assert_called_once()
    
    @patch('mcli.lib.api.daemon_client.requests.Session.post')
    def test_stop_process_success(self, mock_post):
        """Test stopping a process"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'message': 'Process stopped successfully'
        }
        mock_post.return_value = mock_response
        
        result = self.client.stop_process('123')
        
        assert result is not None
        assert result['status'] == 'success'
        mock_post.assert_called_once_with(f'{self.client.base_url}/processes/123/stop')
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_get_system_status_success(self, mock_get):
        """Test getting system status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'cpu_usage': 45.2,
            'memory_usage': 67.8,
            'disk_usage': 23.4,
            'uptime': '5 days, 12:34:56',
            'active_processes': 15
        }
        mock_get.return_value = mock_response
        
        result = self.client.get_system_status()
        
        assert result is not None
        assert result['cpu_usage'] == 45.2
        assert result['active_processes'] == 15
        mock_get.assert_called_once_with(f'{self.client.base_url}/system/status')
    
    @patch('mcli.lib.api.daemon_client.requests.Session.get')
    def test_get_logs_success(self, mock_get):
        """Test getting daemon logs"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'logs': [
                {'timestamp': '2023-01-01T00:00:00', 'level': 'INFO', 'message': 'Test log'},
                {'timestamp': '2023-01-01T00:01:00', 'level': 'ERROR', 'message': 'Error log'}
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.client.get_logs(limit=100)
        
        assert len(result) == 2
        assert result[0]['level'] == 'INFO'
        assert result[1]['level'] == 'ERROR'
        mock_get.assert_called_once()
    
    def test_build_url(self):
        """Test URL building helper"""
        url = self.client._build_url('/test/endpoint')
        
        assert url == 'http://localhost:8000/test/endpoint'
    
    def test_handle_response_success(self):
        """Test response handling for successful responses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        
        result = self.client._handle_response(mock_response)
        
        assert result == {'data': 'test'}
    
    def test_handle_response_error(self):
        """Test response handling for error responses"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Bad request'}
        
        result = self.client._handle_response(mock_response)
        
        assert result == {'error': 'Bad request'}
    
    def test_handle_response_json_error(self):
        """Test response handling with JSON decode error"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid response"
        
        result = self.client._handle_response(mock_response)
        
        assert result is None


class TestDaemonClientGlobalFunction:
    """Test suite for global daemon client functions"""
    
    def test_get_daemon_client_singleton(self):
        """Test that get_daemon_client returns a singleton"""
        client1 = get_daemon_client()
        client2 = get_daemon_client()
        
        assert client1 is client2
        assert isinstance(client1, DaemonClient)
    
    @patch('mcli.lib.api.daemon_client.DaemonClient')
    def test_get_daemon_client_initialization(self, mock_client_class):
        """Test daemon client initialization"""
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance
        
        # Clear any existing singleton
        if hasattr(get_daemon_client, '_instance'):
            delattr(get_daemon_client, '_instance')
        
        result = get_daemon_client()
        
        mock_client_class.assert_called_once()
        assert result == mock_instance
    
    @patch.dict('os.environ', {'MCLI_DAEMON_URL': 'http://custom:8888'})
    def test_get_daemon_client_custom_url(self):
        """Test daemon client with custom URL from environment"""
        # Clear singleton to test environment variable
        if hasattr(get_daemon_client, '_instance'):
            delattr(get_daemon_client, '_instance')
        
        client = get_daemon_client()
        
        # Should use custom URL from environment
        assert 'custom' in client.base_url or '8888' in client.base_url