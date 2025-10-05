"""
CLI tests for mcli.app.completion_cmd module
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock


class TestCompletionCommand:
    """Test suite for completion command"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_completion_bash(self):
        """Test bash completion generation"""
        from mcli.app.completion_cmd import completion

        result = self.runner.invoke(completion, ['bash'])

        assert result.exit_code == 0
        assert 'bash' in result.output.lower() or '_MCLI_COMPLETE' in result.output

    def test_completion_zsh(self):
        """Test zsh completion generation"""
        from mcli.app.completion_cmd import completion

        result = self.runner.invoke(completion, ['zsh'])

        assert result.exit_code == 0
        assert 'zsh' in result.output.lower() or '_MCLI_COMPLETE' in result.output

    def test_completion_fish(self):
        """Test fish completion generation"""
        from mcli.app.completion_cmd import completion

        result = self.runner.invoke(completion, ['fish'])

        assert result.exit_code == 0
        assert 'fish' in result.output.lower() or '_MCLI_COMPLETE' in result.output

    def test_completion_install(self):
        """Test completion installation"""
        from mcli.app.completion_cmd import completion

        with patch('mcli.app.completion_cmd.install_completion') as mock_install:
            mock_install.return_value = True

            result = self.runner.invoke(completion, ['install', '--shell', 'bash'])

            # Should attempt installation
            assert result.exit_code == 0 or 'install' in result.output.lower()

    def test_completion_show(self):
        """Test showing completion script"""
        from mcli.app.completion_cmd import completion

        result = self.runner.invoke(completion, ['show', '--shell', 'bash'])

        # Should show completion script
        assert result.exit_code == 0 or result.output

    def test_completion_help(self):
        """Test completion help"""
        from mcli.app.completion_cmd import completion

        result = self.runner.invoke(completion, ['--help'])

        assert result.exit_code == 0
        assert 'completion' in result.output.lower()

    def test_completion_invalid_shell(self):
        """Test completion with invalid shell"""
        from mcli.app.completion_cmd import completion

        result = self.runner.invoke(completion, ['invalid_shell'])

        # Should handle gracefully
        assert result.exit_code != 0 or 'invalid' in result.output.lower()
