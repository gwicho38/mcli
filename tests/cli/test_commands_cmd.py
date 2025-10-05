"""
CLI tests for mcli.app.commands_cmd module
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, Mock


class TestCommandsCommand:
    """Test suite for commands command"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_commands_list(self):
        """Test listing all commands"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_disco.get_commands.return_value = [
                {'name': 'test-cmd', 'description': 'Test command', 'group': 'test'}
            ]
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['list'])

            assert result.exit_code == 0
            assert 'test-cmd' in result.output or 'Command' in result.output

    def test_commands_search(self):
        """Test searching commands"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_disco.search_commands.return_value = [
                {'name': 'file-cmd', 'description': 'File command', 'group': 'file'}
            ]
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['search', 'file'])

            assert result.exit_code == 0
            mock_disco.search_commands.assert_called_once_with('file')

    def test_commands_info(self):
        """Test getting command info"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_cmd = Mock()
            mock_cmd.name = 'test-cmd'
            mock_cmd.description = 'Test command'
            mock_cmd.module_name = 'test.module'
            mock_disco.get_command_by_name.return_value = mock_cmd
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['info', 'test-cmd'])

            assert result.exit_code == 0
            mock_disco.get_command_by_name.assert_called_once_with('test-cmd')

    def test_commands_info_not_found(self):
        """Test getting info for non-existent command"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_disco.get_command_by_name.return_value = None
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['info', 'nonexistent'])

            assert result.exit_code == 0 or result.exit_code == 1
            mock_disco.get_command_by_name.assert_called_once_with('nonexistent')

    def test_commands_groups(self):
        """Test listing command groups"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_disco.get_commands.return_value = [
                {'name': 'cmd1', 'group': 'group1'},
                {'name': 'cmd2', 'group': 'group2'},
                {'name': 'cmd3', 'group': 'group1'},
            ]
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['groups'])

            assert result.exit_code == 0
            # Should show groups
            assert result.output

    def test_commands_export(self):
        """Test exporting commands"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_disco.get_commands.return_value = [
                {'name': 'test-cmd', 'description': 'Test'}
            ]
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['export', '--format', 'json'])

            assert result.exit_code == 0
            # Should output JSON
            assert result.output

    def test_commands_refresh(self):
        """Test refreshing command discovery"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.refresh_command_discovery') as mock_refresh:
            mock_refresh.return_value = Mock()

            result = self.runner.invoke(commands, ['refresh'])

            assert result.exit_code == 0
            mock_refresh.assert_called_once()

    def test_commands_help(self):
        """Test commands help"""
        from mcli.app.commands_cmd import commands

        result = self.runner.invoke(commands, ['--help'])

        assert result.exit_code == 0
        assert 'commands' in result.output.lower()

    def test_commands_list_by_group(self):
        """Test listing commands by group"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_disco.get_commands.return_value = [
                {'name': 'cmd1', 'group': 'workflow', 'description': 'Workflow command'},
                {'name': 'cmd2', 'group': 'app', 'description': 'App command'},
            ]
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['list', '--group', 'workflow'])

            assert result.exit_code == 0
            # Should filter by group
            assert result.output

    def test_commands_stats(self):
        """Test showing command statistics"""
        from mcli.app.commands_cmd import commands

        with patch('mcli.app.commands_cmd.get_command_discovery') as mock_discovery:
            mock_disco = Mock()
            mock_disco.get_commands.return_value = [
                {'name': 'cmd1', 'group': 'group1'},
                {'name': 'cmd2', 'group': 'group1'},
                {'name': 'cmd3', 'group': 'group2'},
            ]
            mock_discovery.return_value = mock_disco

            result = self.runner.invoke(commands, ['stats'])

            assert result.exit_code == 0
            # Should show statistics
            assert result.output
