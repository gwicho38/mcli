"""
Unit tests for mcli.app.chat_cmd module
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from mcli.app.chat_cmd import chat


class TestChatCommand:
    """Test suite for chat command functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_chat_command_exists(self):
        """Test that chat command is properly defined"""
        assert chat is not None
        assert hasattr(chat, "callback")
        assert chat.name == "chat"

    @patch("mcli.app.chat_cmd.ChatClient")
    def test_chat_classic_mode(self, mock_chat_client):
        """Test chat command in classic mode"""
        mock_instance = Mock()
        mock_chat_client.return_value = mock_instance

        result = self.runner.invoke(chat, ["--classic"])

        # Should use ChatClient for classic mode
        mock_chat_client.assert_called_once_with(use_remote=False, model_override=None)
        mock_instance.start_interactive_session.assert_called_once()
        assert result.exit_code == 0

    @patch("mcli.app.chat_cmd.EnhancedChatClient")
    def test_chat_enhanced_mode_default(self, mock_enhanced_client):
        """Test chat command in enhanced mode (default)"""
        mock_instance = Mock()
        mock_enhanced_client.return_value = mock_instance

        result = self.runner.invoke(chat, [])

        # Should use EnhancedChatClient by default
        mock_enhanced_client.assert_called_once_with(use_remote=False, model_override=None)
        mock_instance.start_interactive_session.assert_called_once()
        assert result.exit_code == 0

    @patch("mcli.app.chat_cmd.EnhancedChatClient")
    def test_chat_remote_mode(self, mock_enhanced_client):
        """Test chat command with remote models"""
        mock_instance = Mock()
        mock_enhanced_client.return_value = mock_instance

        result = self.runner.invoke(chat, ["--remote"])

        mock_enhanced_client.assert_called_once_with(use_remote=True, model_override=None)
        mock_instance.start_interactive_session.assert_called_once()
        assert result.exit_code == 0

    @patch("mcli.app.chat_cmd.EnhancedChatClient")
    def test_chat_with_model_override(self, mock_enhanced_client):
        """Test chat command with specific model"""
        mock_instance = Mock()
        mock_enhanced_client.return_value = mock_instance

        result = self.runner.invoke(chat, ["--model", "llama2"])

        mock_enhanced_client.assert_called_once_with(use_remote=False, model_override="llama2")
        mock_instance.start_interactive_session.assert_called_once()
        assert result.exit_code == 0

    @patch("mcli.app.chat_cmd.ChatClient")
    def test_chat_classic_with_remote_and_model(self, mock_chat_client):
        """Test chat command classic mode with all options"""
        mock_instance = Mock()
        mock_chat_client.return_value = mock_instance

        result = self.runner.invoke(chat, ["--classic", "--remote", "--model", "gpt-4"])

        mock_chat_client.assert_called_once_with(use_remote=True, model_override="gpt-4")
        mock_instance.start_interactive_session.assert_called_once()
        assert result.exit_code == 0

    @patch("mcli.app.chat_cmd.ChatClient")
    @patch("mcli.app.chat_cmd.EnhancedChatClient")
    def test_chat_classic_flag_precedence(self, mock_enhanced_client, mock_chat_client):
        """Test that --classic flag takes precedence over --enhanced"""
        mock_instance = Mock()
        mock_chat_client.return_value = mock_instance

        result = self.runner.invoke(chat, ["--classic", "--enhanced"])

        # Should use ChatClient when --classic is specified
        mock_chat_client.assert_called_once()
        mock_enhanced_client.assert_not_called()
        assert result.exit_code == 0

    def test_chat_help_text(self):
        """Test chat command help text"""
        result = self.runner.invoke(chat, ["--help"])

        assert result.exit_code == 0
        assert "Start an interactive chat session" in result.output
        assert "Enhanced Mode" in result.output
        assert "Classic Mode" in result.output
        assert "--remote" in result.output
        assert "--model" in result.output
        assert "--enhanced" in result.output
        assert "--classic" in result.output
