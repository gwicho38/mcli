"""
Unit tests for mcli.chat.enhanced_chat module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from mcli.chat.enhanced_chat import EnhancedChatClient


class TestEnhancedChatClient:
    """Test suite for EnhancedChatClient functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create mocks that will be used in tests
        self.mock_daemon = Mock()
        self.mock_rag = Mock()
        
        # Patch the imports and create client instance
        with patch('mcli.chat.enhanced_chat.get_daemon_client', return_value=self.mock_daemon), \
             patch('mcli.chat.enhanced_chat.get_command_rag_system', return_value=self.mock_rag), \
             patch('mcli.chat.enhanced_chat.read_from_toml', return_value={
                 'provider': 'local',
                 'model': 'test-model',
                 'temperature': 0.7,
                 'ollama_base_url': 'http://localhost:11434'
             }):
            self.client = EnhancedChatClient()
    
    def test_enhanced_chat_client_initialization(self):
        """Test EnhancedChatClient initialization"""
        assert self.client.daemon is not None
        assert self.client.rag_system is not None
        assert self.client.conversation_history == []
        assert self.client.session_active is True
    
    def test_enhanced_chat_with_options(self):
        """Test EnhancedChatClient with initialization options"""
        with patch('mcli.chat.enhanced_chat.get_daemon_client') as mock_get_daemon, \
             patch('mcli.chat.enhanced_chat.get_command_rag_system') as mock_get_rag, \
             patch('mcli.chat.enhanced_chat.read_from_toml') as mock_read_toml:
            
            mock_get_daemon.return_value = Mock()
            mock_get_rag.return_value = Mock()
            mock_read_toml.return_value = {}
            
            client = EnhancedChatClient(use_remote=True, model_override='custom-model')
            
            assert client.use_remote is True
            assert client.model_override == 'custom-model'
    
    def test_search_relevant_commands(self):
        """Test command search functionality"""
        # Mock RAG system search
        self.mock_rag.search_commands.return_value = [
            {'name': 'file-cmd', 'description': 'File operations', 'score': 0.9},
            {'name': 'process-cmd', 'description': 'Process management', 'score': 0.7}
        ]
        
        result = self.client._search_relevant_commands("manage files")
        
        assert len(result) == 2
        assert result[0]['name'] == 'file-cmd'
        assert result[0]['score'] == 0.9
        self.mock_rag.search_commands.assert_called_once_with("manage files")
    
    def test_analyze_user_intent(self):
        """Test user intent analysis"""
        # Test command search intent
        result = self.client._analyze_user_intent("how do I list files?")
        assert result['primary_intent'] in ['command_search', 'general_question']
        assert 'confidence' in result
        assert 'keywords' in result
        
        # Test system status intent
        result = self.client._analyze_user_intent("what processes are running?")
        assert 'system' in result['keywords'] or 'process' in result['keywords']
    
    def test_generate_contextual_response(self):
        """Test contextual response generation"""
        mock_commands = [
            {'name': 'ls-cmd', 'description': 'List directory contents'},
            {'name': 'ps-cmd', 'description': 'List processes'}
        ]
        
        with patch.object(self.client, '_search_relevant_commands', return_value=mock_commands), \
             patch.object(self.client, '_analyze_user_intent') as mock_analyze:
            
            mock_analyze.return_value = {
                'primary_intent': 'command_search',
                'confidence': 0.8,
                'keywords': ['list', 'files']
            }
            
            result = self.client._generate_contextual_response("list my files")
            
            assert isinstance(result, dict)
            assert 'relevant_commands' in result
            assert 'intent_analysis' in result
            assert len(result['relevant_commands']) == 2
    
    def test_format_enhanced_response(self):
        """Test enhanced response formatting"""
        context = {
            'relevant_commands': [
                {'name': 'test-cmd', 'description': 'Test command', 'score': 0.9}
            ],
            'intent_analysis': {
                'primary_intent': 'command_search',
                'confidence': 0.8
            },
            'system_status': {
                'active_processes': 3,
                'cpu_usage': 45.2
            }
        }
        
        with patch('mcli.chat.enhanced_chat.console') as mock_console:
            self.client._format_enhanced_response("test query", "AI response", context)
            
            # Should display formatted response
            mock_console.print.assert_called()
    
    def test_update_conversation_history(self):
        """Test conversation history updates"""
        self.client._update_conversation_history("user", "test message")
        
        assert len(self.client.conversation_history) == 1
        assert self.client.conversation_history[0]['role'] == 'user'
        assert self.client.conversation_history[0]['content'] == 'test message'
        assert 'timestamp' in self.client.conversation_history[0]
    
    def test_get_conversation_context(self):
        """Test getting conversation context"""
        # Add some history
        self.client._update_conversation_history("user", "first message")
        self.client._update_conversation_history("assistant", "first response")
        self.client._update_conversation_history("user", "second message")
        
        context = self.client._get_conversation_context(max_messages=2)
        
        assert len(context) == 2
        assert context[0]['content'] == "first response"
        assert context[1]['content'] == "second message"
    
    def test_handle_system_status_request(self):
        """Test system status request handling"""
        # Mock daemon system status
        self.mock_daemon.get_system_status.return_value = {
            'cpu_usage': 45.2,
            'memory_usage': 67.8,
            'disk_usage': 23.4,
            'active_processes': 15
        }
        
        result = self.client._handle_system_status_request()
        
        assert isinstance(result, dict)
        assert 'cpu_usage' in result
        assert 'memory_usage' in result
        assert result['active_processes'] == 15
    
    def test_suggest_next_actions(self):
        """Test next action suggestions"""
        context = {
            'relevant_commands': [
                {'name': 'file-list', 'description': 'List files'}
            ],
            'intent_analysis': {
                'primary_intent': 'command_search',
                'keywords': ['file', 'list']
            }
        }
        
        suggestions = self.client._suggest_next_actions(context)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Should suggest relevant actions based on context
    
    def test_process_enhanced_query_command_search(self):
        """Test processing query with command search"""
        with patch.object(self.client, '_search_relevant_commands') as mock_search, \
             patch.object(self.client, '_analyze_user_intent') as mock_analyze, \
             patch.object(self.client, '_format_enhanced_response') as mock_format:
            
            mock_search.return_value = [{'name': 'test-cmd', 'score': 0.9}]
            mock_analyze.return_value = {'primary_intent': 'command_search', 'confidence': 0.8}
            
            self.client.process_enhanced_query("find a command to list files")
            
            mock_search.assert_called_once()
            mock_analyze.assert_called_once()
            mock_format.assert_called_once()
    
    def test_process_enhanced_query_system_status(self):
        """Test processing system status query"""
        with patch.object(self.client, '_handle_system_status_request') as mock_status, \
             patch.object(self.client, '_format_enhanced_response') as mock_format:
            
            mock_status.return_value = {'cpu_usage': 45.2}
            
            self.client.process_enhanced_query("what's my system status?")
            
            mock_status.assert_called_once()
            mock_format.assert_called_once()
    
    def test_export_conversation_history(self):
        """Test exporting conversation history"""
        # Add some conversation history
        self.client._update_conversation_history("user", "test message 1")
        self.client._update_conversation_history("assistant", "test response 1")
        
        with patch('builtins.open', mock_open()) as mock_file:
            self.client.export_conversation_history("/tmp/test_export.json")
            
            mock_file.assert_called_once_with("/tmp/test_export.json", 'w')
    
    def test_import_conversation_history(self):
        """Test importing conversation history"""
        test_history = [
            {'role': 'user', 'content': 'test', 'timestamp': '2023-01-01T00:00:00'}
        ]
        
        with patch('builtins.open', mock_open(read_data=json.dumps(test_history))):
            self.client.import_conversation_history("/tmp/test_import.json")
            
            assert len(self.client.conversation_history) == 1
            assert self.client.conversation_history[0]['content'] == 'test'
    
    def test_clear_conversation_history(self):
        """Test clearing conversation history"""
        # Add some history first
        self.client._update_conversation_history("user", "test")
        assert len(self.client.conversation_history) == 1
        
        self.client.clear_conversation_history()
        assert len(self.client.conversation_history) == 0
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics"""
        # Add some history to generate metrics
        self.client._update_conversation_history("user", "test1")
        self.client._update_conversation_history("assistant", "response1")
        
        metrics = self.client.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'total_queries' in metrics
        assert 'average_response_time' in metrics
        assert metrics['total_queries'] >= 0
    
    @patch('mcli.chat.enhanced_chat.console')
    def test_display_welcome_message(self, mock_console):
        """Test enhanced welcome message display"""
        self.client._display_welcome_message()
        
        mock_console.print.assert_called()
        # Should display enhanced features information
    
    @patch('mcli.chat.enhanced_chat.console')
    def test_display_help_commands(self, mock_console):
        """Test help commands display"""
        self.client._display_help_commands()
        
        mock_console.print.assert_called()
        # Should display available help commands


def mock_open(read_data=""):
    """Mock open function for file operations"""
    mock = MagicMock()
    mock.return_value.__enter__.return_value.read.return_value = read_data
    return mock