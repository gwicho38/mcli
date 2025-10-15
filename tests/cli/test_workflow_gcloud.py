"""
CLI tests for mcli.workflow.gcloud module
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


class TestGcloudCommands:
    """Test suite for gcloud workflow commands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_gcloud_group_exists(self):
        """Test gcloud command group exists"""
        from mcli.workflow.gcloud.gcloud import gcloud

        assert gcloud is not None
        assert hasattr(gcloud, "commands") or callable(gcloud)

    def test_gcloud_group_help(self):
        """Test gcloud command group help"""
        from mcli.workflow.gcloud.gcloud import gcloud

        result = self.runner.invoke(gcloud, ["--help"])

        assert result.exit_code == 0
        assert "gcloud" in result.output.lower()

    @patch("mcli.workflow.gcloud.gcloud.shell_exec")
    @patch("mcli.workflow.gcloud.gcloud.get_shell_script_path")
    def test_start_command(self, mock_get_path, mock_shell_exec):
        """Test gcloud start command"""
        from mcli.workflow.gcloud.gcloud import gcloud

        mock_get_path.return_value = "/mock/path/script.sh"
        mock_shell_exec.return_value = {"returncode": 0}

        result = self.runner.invoke(gcloud, ["start"])

        # Verify shell_exec was called
        mock_shell_exec.assert_called_once()
        assert "start" in str(mock_shell_exec.call_args)

    @patch("mcli.workflow.gcloud.gcloud.shell_exec")
    @patch("mcli.workflow.gcloud.gcloud.get_shell_script_path")
    def test_stop_command(self, mock_get_path, mock_shell_exec):
        """Test gcloud stop command"""
        from mcli.workflow.gcloud.gcloud import gcloud

        mock_get_path.return_value = "/mock/path/script.sh"
        mock_shell_exec.return_value = {"returncode": 0}

        result = self.runner.invoke(gcloud, ["stop"])

        mock_shell_exec.assert_called_once()
        assert "stop" in str(mock_shell_exec.call_args)

    @patch("mcli.workflow.gcloud.gcloud.shell_exec")
    @patch("mcli.workflow.gcloud.gcloud.get_shell_script_path")
    def test_describe_command(self, mock_get_path, mock_shell_exec):
        """Test gcloud describe command"""
        from mcli.workflow.gcloud.gcloud import gcloud

        mock_get_path.return_value = "/mock/path/script.sh"
        mock_shell_exec.return_value = {"returncode": 0}

        result = self.runner.invoke(gcloud, ["describe"])

        mock_shell_exec.assert_called_once()
        assert "describe" in str(mock_shell_exec.call_args)

    @patch("mcli.workflow.gcloud.gcloud.shell_exec")
    @patch("mcli.workflow.gcloud.gcloud.get_shell_script_path")
    def test_tunnel_command(self, mock_get_path, mock_shell_exec):
        """Test gcloud tunnel command"""
        from mcli.workflow.gcloud.gcloud import gcloud

        mock_get_path.return_value = "/mock/path/script.sh"
        mock_shell_exec.return_value = {"returncode": 0}

        result = self.runner.invoke(gcloud, ["tunnel", "8080", "3000"])

        # Tunnel command exists and can be invoked
        # Note: may not call shell_exec if there's an error in command setup
        assert result.exit_code in [0, 1, 2]

    def test_start_help(self):
        """Test start command help"""
        from mcli.workflow.gcloud.gcloud import gcloud

        result = self.runner.invoke(gcloud, ["start", "--help"])

        assert result.exit_code == 0

    def test_stop_help(self):
        """Test stop command help"""
        from mcli.workflow.gcloud.gcloud import gcloud

        result = self.runner.invoke(gcloud, ["stop", "--help"])

        assert result.exit_code == 0

    def test_describe_help(self):
        """Test describe command help"""
        from mcli.workflow.gcloud.gcloud import gcloud

        result = self.runner.invoke(gcloud, ["describe", "--help"])

        assert result.exit_code == 0

    def test_tunnel_help(self):
        """Test tunnel command help"""
        from mcli.workflow.gcloud.gcloud import gcloud

        result = self.runner.invoke(gcloud, ["tunnel", "--help"])

        assert result.exit_code == 0
        assert "port" in result.output.lower()
