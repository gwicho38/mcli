"""
Unit tests for mcli.chat.chat module - ChatClient functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from unittest import TestCase
import json

# Import test subjects
from mcli.chat.chat import ChatClient


class TestChatClient:
    """Test suite for ChatClient functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create mocks that will be used in tests
        self.mock_daemon = Mock()
        
        # Patch the imports and create client instance
        with patch('mcli.chat.chat.get_daemon_client', return_value=self.mock_daemon), \
             patch('mcli.chat.chat.read_from_toml', return_value={
                 'provider': 'local',
                 'model': 'test-model', 
                 'temperature': 0.7,
                 'ollama_base_url': 'http://localhost:11434'
             }):
            self.client = ChatClient()
    
    def test_chat_client_initialization(self):
        """Test ChatClient initialization"""
        assert self.client.daemon is not None
        assert self.client.history == []
        assert self.client.session_active is True
        assert self.client.use_remote is False
        assert self.client.model_override is None
    
    def test_chat_client_with_options(self):
        """Test ChatClient initialization with options"""
        with patch('mcli.chat.chat.get_daemon_client') as mock_get_daemon, \
             patch('mcli.chat.chat.read_from_toml') as mock_read_toml:
            
            mock_get_daemon.return_value = Mock()
            mock_read_toml.return_value = {}
            
            client = ChatClient(use_remote=True, model_override='custom-model')
            
            assert client.use_remote is True
            assert client.model_override == 'custom-model'
    
    @patch('mcli.chat.chat.ollama.generate')
    def test_generate_llm_response_success(self, mock_ollama_generate):
        """Test successful LLM response generation"""
        # Mock daemon commands
        self.mock_daemon.list_commands.return_value = [
            {'name': 'test-cmd', 'description': 'Test command'}
        ]
        
        # Mock ollama response
        mock_ollama_generate.return_value = {
            'response': 'This is a test response from the AI assistant.'
        }
        
        with patch('mcli.chat.chat.console') as mock_console:
            result = self.client.generate_llm_response("test query")
            
            # Verify ollama was called correctly
            mock_ollama_generate.assert_called_once()
            args, kwargs = mock_ollama_generate.call_args
            assert 'model' in kwargs
            assert 'prompt' in kwargs
            assert 'options' in kwargs
            assert kwargs['options']['temperature'] == 0.7
            
            # Verify response was printed
            mock_console.print.assert_called()
    
    @patch('mcli.chat.chat.ollama.generate')
    def test_generate_llm_response_model_not_found(self, mock_ollama_generate):
        """Test LLM response when model is not found"""
        import ollama
        
        # Mock daemon commands
        self.mock_daemon.list_commands.return_value = []
        
        # Mock ollama error for model not found
        mock_ollama_generate.side_effect = ollama.ResponseError("model not found")
        
        with patch('mcli.chat.chat.console') as mock_console, \
             patch.object(self.client, '_ensure_lightweight_model_server') as mock_ensure_server, \
             patch.object(self.client, '_pull_model_if_needed') as mock_pull_model:
            
            self.client.generate_llm_response("test query")
            
            # Should attempt to handle the error
            mock_console.print.assert_called()
    
    @patch('mcli.chat.chat.ollama.generate')
    def test_generate_llm_response_connection_error(self, mock_ollama_generate):
        """Test LLM response with connection error"""
        import ollama
        
        # Mock daemon commands  
        self.mock_daemon.list_commands.return_value = []
        
        # Mock ollama connection error
        mock_ollama_generate.side_effect = ollama.RequestError("connection failed")
        
        with patch('mcli.chat.chat.console') as mock_console:
            self.client.generate_llm_response("test query")
            
            # Should print connection error message
            mock_console.print.assert_called()
    
    def test_validate_and_correct_response(self):
        """Test response validation and correction"""
        commands = [
            {'name': 'valid-cmd', 'description': 'Valid command'},
            {'name': 'another-cmd', 'description': 'Another command'}
        ]
        
        # Test with valid response
        response = "Use the valid-cmd command to accomplish this task."
        result = self.client.validate_and_correct_response(response, commands)
        
        # Should return response as-is for valid commands
        assert "valid-cmd" in result
    
    def test_parse_user_input_system_commands(self):
        """Test parsing system commands from user input"""
        # Test process list command
        result = self.client.parse_user_input("list processes")
        assert result['intent'] == 'system_request'
        assert result['action'] == 'list_processes'
        
        # Test process stop command
        result = self.client.parse_user_input("stop process abc123")
        assert result['intent'] == 'system_request'
        assert result['action'] == 'stop_process'
        assert result['args'] == ['abc123']
    
    def test_parse_user_input_regular_query(self):
        """Test parsing regular user queries"""
        result = self.client.parse_user_input("How do I create a new command?")
        
        assert result['intent'] == 'chat'
        assert result['query'] == "How do I create a new command?"
    
    def test_handle_process_list(self):
        """Test listing processes"""
        # Mock daemon response
        self.mock_daemon.list_processes.return_value = [
            {'id': '123', 'name': 'test-process', 'status': 'running'},
            {'id': '456', 'name': 'another-process', 'status': 'stopped'}
        ]
        
        with patch('mcli.chat.chat.console') as mock_console:
            self.client.handle_process_list()
            
            mock_console.print.assert_called()
            # Verify process information was displayed
    
    @patch('mcli.chat.chat.requests.post')
    def test_handle_process_stop_success(self, mock_post):
        """Test stopping a process successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        with patch('mcli.chat.chat.console') as mock_console:
            self.client.handle_process_stop('test-123')
            
            mock_post.assert_called_once()
            mock_console.print.assert_called()
    
    @patch('mcli.chat.chat.requests.post')
    def test_handle_process_stop_not_found(self, mock_post):
        """Test stopping a non-existent process"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        with patch('mcli.chat.chat.console') as mock_console:
            self.client.handle_process_stop('test-123')
            
            mock_console.print.assert_called()
    
    @patch('mcli.chat.chat.requests.post')
    def test_handle_process_start_success(self, mock_post):
        """Test starting a process successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        with patch('mcli.chat.chat.console') as mock_console:
            self.client.handle_process_start('test-123')
            
            mock_post.assert_called_once()
            mock_console.print.assert_called()
    
    def test_get_command_code_from_ai(self):
        """Test AI code generation"""
        with patch('mcli.chat.chat.ollama.generate') as mock_generate:
            mock_generate.return_value = {
                'response': '''
COMMAND_NAME: test_command
FILENAME: test_command.py
DESCRIPTION: Test command
CODE:
```python
import click

@click.command()
def test_command():
    """Test command"""
    click.echo("Test command works!")
```
                '''
            }
            
            # Mock daemon commands
            self.mock_daemon.list_commands.return_value = []
            
            result = self.client._get_command_code_from_ai("create a test command")
            
            assert result is not None
            assert 'COMMAND_NAME: test_command' in result
            assert 'import click' in result
            mock_generate.assert_called_once()
    
    def test_parse_command_response(self):
        """Test parsing AI command response"""
        response = '''
COMMAND_NAME: test_cmd
FILENAME: test_cmd.py  
DESCRIPTION: A test command
CODE:
```python
import click

@click.command()
def test_cmd():
    """Test command"""
    pass
```
        '''
        
        result = self.client._parse_command_response(response)
        
        assert result is not None
        assert result['name'] == 'test_cmd'
        assert result['filename'] == 'test_cmd.py'
        assert result['description'] == 'A test command'
        assert 'import click' in result['code']
    
    def test_parse_command_response_invalid(self):
        """Test parsing invalid AI command response"""
        response = "This is not a valid command response"
        
        result = self.client._parse_command_response(response)
        
        assert result is None
    
    @patch('mcli.chat.chat.subprocess.run')
    def test_pull_model_if_needed(self, mock_subprocess):
        """Test pulling model when needed"""
        mock_subprocess.return_value = Mock(returncode=0)
        
        with patch('mcli.chat.chat.console') as mock_console:
            self.client._pull_model_if_needed('test-model')
            
            mock_subprocess.assert_called()
            mock_console.print.assert_called()
    
    def test_ensure_daemon_running(self):
        """Test ensuring daemon is running"""
        with patch.object(self.client.daemon, 'ping') as mock_ping:
            mock_ping.return_value = True
            
            # Should not raise any exceptions
            self.client._ensure_daemon_running()
            
            mock_ping.assert_called_once()
    
    def test_load_scheduled_jobs(self):
        """Test loading scheduled jobs"""
        mock_jobs = [
            {'id': '1', 'name': 'test-job', 'status': 'running'},
            {'id': '2', 'name': 'backup-job', 'status': 'scheduled'}
        ]
        
        with patch.object(self.client, '_load_jobs_from_daemon') as mock_load:
            mock_load.return_value = mock_jobs
            
            self.client._load_scheduled_jobs()
            
            mock_load.assert_called_once()