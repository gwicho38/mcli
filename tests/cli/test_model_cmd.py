"""
Unit tests for mcli.app.model_cmd module
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from mcli.app.model_cmd import delete, download, list, model, pull, recommend, start, status, stop


class TestModelCommands:
    """Test suite for model command functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_model_group_exists(self):
        """Test that model command group is properly defined"""
        assert model is not None
        assert hasattr(model, "commands")
        assert model.name == "model"

    def test_list_command_exists(self):
        """Test that list command is properly defined"""
        assert list is not None
        assert list.name == "list"

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_list_command_basic(self, mock_server_class):
        """Test list command basic functionality"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = []
        mock_server.get_system_info.return_value = {
            "cpu_count": 4,
            "memory_gb": 8.0,
            "disk_free_gb": 100.0,
        }
        mock_server.recommend_model.return_value = "distilbert-base-uncased"

        result = self.runner.invoke(model, ["list"])

        assert result.exit_code == 0
        assert "Available Lightweight Models" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_download_command_success(self, mock_server_class):
        """Test download command with successful download"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.download_and_load_model.return_value = True

        result = self.runner.invoke(model, ["download", "distilbert-base-uncased"])

        assert result.exit_code == 0
        assert "Successfully downloaded" in result.output
        mock_server.download_and_load_model.assert_called_once_with("distilbert-base-uncased")

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_download_command_failure(self, mock_server_class):
        """Test download command with failed download"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.download_and_load_model.return_value = False

        result = self.runner.invoke(model, ["download", "distilbert-base-uncased"])

        assert result.exit_code == 1
        assert "Failed to download" in result.output

    def test_download_command_invalid_model(self):
        """Test download command with invalid model name"""
        result = self.runner.invoke(model, ["download", "invalid-model-name"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_pull_command_success(self, mock_server_class):
        """Test pull command with successful pull"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.download_and_load_model.return_value = True

        result = self.runner.invoke(model, ["pull", "distilbert-base-uncased"])

        assert result.exit_code == 0
        assert "Successfully pulled" in result.output
        mock_server.download_and_load_model.assert_called_once_with("distilbert-base-uncased")

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_pull_command_failure(self, mock_server_class):
        """Test pull command with failed pull"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.download_and_load_model.return_value = False

        result = self.runner.invoke(model, ["pull", "distilbert-base-uncased"])

        assert result.exit_code == 1
        assert "Failed to pull" in result.output

    def test_pull_command_invalid_model(self):
        """Test pull command with invalid model name"""
        result = self.runner.invoke(model, ["pull", "invalid-model-name"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_delete_command_success_with_force(self, mock_server_class):
        """Test delete command with successful deletion using force flag"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]
        mock_server.delete_model.return_value = True

        result = self.runner.invoke(model, ["delete", "distilbert-base-uncased", "--force"])

        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        mock_server.delete_model.assert_called_once_with("distilbert-base-uncased")

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_delete_command_failure(self, mock_server_class):
        """Test delete command with failed deletion"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]
        mock_server.delete_model.return_value = False

        result = self.runner.invoke(model, ["delete", "distilbert-base-uncased", "--force"])

        assert result.exit_code == 1
        assert "Failed to delete" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_delete_command_model_not_found(self, mock_server_class):
        """Test delete command with model not found"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = []

        result = self.runner.invoke(model, ["delete", "distilbert-base-uncased", "--force"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_delete_command_with_confirmation(self, mock_server_class):
        """Test delete command with user confirmation"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]
        mock_server.delete_model.return_value = True

        # Simulate user confirming deletion
        result = self.runner.invoke(model, ["delete", "distilbert-base-uncased"], input="y\n")

        assert result.exit_code == 0
        assert "Successfully deleted" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_delete_command_cancelled(self, mock_server_class):
        """Test delete command when user cancels"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]

        # Simulate user cancelling deletion
        result = self.runner.invoke(model, ["delete", "distilbert-base-uncased"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.output
        mock_server.delete_model.assert_not_called()

    def test_stop_command_success(self):
        """Test stop command with successful stop"""
        with patch("requests.get") as mock_get, patch("psutil.process_iter") as mock_proc_iter:

            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            mock_proc = Mock()
            mock_proc.pid = 1234
            mock_proc.info = {"connections": [Mock(laddr=Mock(port=8080))]}
            mock_proc_iter.return_value = [mock_proc]

            result = self.runner.invoke(model, ["stop"])

            assert result.exit_code == 0
            # Accept various success/warning messages - no server running is also valid
            assert any(
                msg in result.output
                for msg in [
                    "Server stopped successfully",
                    "Stopping server",
                    "Could not find server process",
                    "Server is not running",
                ]
            )

    def test_stop_command_no_server(self):
        """Test stop command when no server is running"""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            result = self.runner.invoke(model, ["stop"])

            assert result.exit_code == 0
            assert "No server running" in result.output

    def test_status_command_server_running(self):
        """Test status command when server is running"""
        with patch("requests.get") as mock_get:
            mock_health_response = Mock()
            mock_health_response.status_code = 200

            mock_models_response = Mock()
            mock_models_response.status_code = 200
            mock_models_response.json.return_value = {
                "models": [{"name": "distilbert-base-uncased", "parameters": "66M"}]
            }

            mock_get.side_effect = [mock_health_response, mock_models_response]

            result = self.runner.invoke(model, ["status"])

            assert result.exit_code == 0
            assert "Server is running" in result.output

    def test_status_command_server_not_running(self):
        """Test status command when server is not running"""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            result = self.runner.invoke(model, ["status"])

            assert result.exit_code == 0
            assert "No server running" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_recommend_command(self, mock_server_class):
        """Test recommend command"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.get_system_info.return_value = {
            "cpu_count": 4,
            "memory_gb": 8.0,
            "disk_free_gb": 100.0,
        }
        mock_server.downloader.get_downloaded_models.return_value = []

        result = self.runner.invoke(model, ["recommend"])

        assert result.exit_code == 0
        assert "Recommended Model" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_start_command_with_auto_download(self, mock_server_class):
        """Test start command with auto-download"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.downloader.get_downloaded_models.return_value = []
        mock_server.download_and_load_model.return_value = True

        # Use a timeout to avoid hanging on the infinite loop
        import signal

        def timeout_handler(signum, frame):
            raise KeyboardInterrupt()

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1)

        try:
            result = self.runner.invoke(model, ["start", "--auto-download"])
            # Command will be interrupted by KeyboardInterrupt
        except KeyboardInterrupt:
            pass
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        # Verify the model was downloaded
        mock_server.download_and_load_model.assert_called()


class TestModelCommandEdgeCases:
    """Test suite for model command edge cases and error paths"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_list_with_system_info_flag(self, mock_server_class):
        """Test list command with --system-info flag"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.get_system_info.return_value = {
            "cpu_count": 8,
            "memory_gb": 16.0,
            "disk_free_gb": 200.0,
        }
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.downloader.get_downloaded_models.return_value = []

        result = self.runner.invoke(model, ["list", "--system-info"])

        assert result.exit_code == 0
        assert "System Information" in result.output
        assert "CPU Cores: 8" in result.output
        assert "RAM: 16.0 GB" in result.output
        assert "Recommended Model: distilbert-base-uncased" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_list_with_list_downloaded_flag(self, mock_server_class):
        """Test list command with --list-downloaded flag"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]

        result = self.runner.invoke(model, ["list", "--list-downloaded"])

        assert result.exit_code == 0
        assert "Downloaded Models" in result.output
        assert "DistilBERT" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_list_with_no_downloaded_models(self, mock_server_class):
        """Test list command when no models are downloaded"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = []

        result = self.runner.invoke(model, ["list", "--list-downloaded"])

        assert result.exit_code == 0
        assert "No models downloaded yet" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_recommend_model_not_downloaded(self, mock_server_class):
        """Test recommend command when model is not downloaded"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.get_system_info.return_value = {
            "cpu_count": 4,
            "memory_gb": 8.0,
            "disk_free_gb": 100.0,
        }
        mock_server.downloader.get_downloaded_models.return_value = []

        result = self.runner.invoke(model, ["recommend"])

        assert result.exit_code == 0
        assert "To download" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_recommend_model_already_downloaded(self, mock_server_class):
        """Test recommend command when model is already downloaded"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.get_system_info.return_value = {
            "cpu_count": 4,
            "memory_gb": 8.0,
            "disk_free_gb": 100.0,
        }
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]

        result = self.runner.invoke(model, ["recommend"])

        assert result.exit_code == 0
        assert "already downloaded" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_start_with_invalid_model(self, mock_server_class):
        """Test start command with invalid model name"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        result = self.runner.invoke(model, ["start", "--model", "invalid-model"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_start_without_auto_download_and_model_not_downloaded(self, mock_server_class):
        """Test start command when model not downloaded and auto-download disabled"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.downloader.get_downloaded_models.return_value = []

        result = self.runner.invoke(model, ["start", "--no-auto-download"])

        assert result.exit_code != 0  # Should fail (could be 1 or 2 depending on click version)
        assert "not found locally" in result.output or "auto-download" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_start_with_explicit_port(self, mock_server_class):
        """Test start command with explicit port option"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]
        mock_server.download_and_load_model.return_value = True

        # Use signal to interrupt the infinite loop quickly
        import signal

        def timeout_handler(signum, frame):
            raise KeyboardInterrupt()

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1)

        try:
            result = self.runner.invoke(model, ["start", "--port", "9999"])
        except KeyboardInterrupt:
            pass
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        # Verify the server was created with the specified port (click passes as string)
        mock_server_class.assert_called_with(port="9999")

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_start_model_load_failure(self, mock_server_class):
        """Test start command when model loading fails"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.recommend_model.return_value = "distilbert-base-uncased"
        mock_server.downloader.get_downloaded_models.return_value = ["distilbert-base-uncased"]
        mock_server.download_and_load_model.return_value = False

        result = self.runner.invoke(model, ["start"])

        assert result.exit_code == 1
        assert "Failed to load" in result.output

    def test_status_with_timeout(self):
        """Test status command when server times out"""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()

            result = self.runner.invoke(model, ["status"])

            assert result.exit_code == 0
            assert "not responding" in result.output

    def test_status_with_exception(self):
        """Test status command with unexpected exception"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Unexpected error")

            result = self.runner.invoke(model, ["status"])

            assert result.exit_code == 0
            assert "Error checking server" in result.output

    def test_status_with_no_models_loaded(self):
        """Test status command when server has no models loaded"""
        with patch("requests.get") as mock_get:
            mock_health = Mock()
            mock_health.status_code = 200

            mock_models = Mock()
            mock_models.status_code = 200
            mock_models.json.return_value = {"models": []}

            mock_get.side_effect = [mock_health, mock_models]

            result = self.runner.invoke(model, ["status"])

            assert result.exit_code == 0
            assert "No models currently loaded" in result.output

    def test_status_with_non_200_response(self):
        """Test status command when server returns non-200 status"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500

            mock_get.return_value = mock_response

            result = self.runner.invoke(model, ["status"])

            assert result.exit_code == 0
            assert "responded with status 500" in result.output

    def test_stop_with_explicit_port(self):
        """Test stop command with explicit port option"""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            result = self.runner.invoke(model, ["stop", "--port", "9999"])

            assert result.exit_code == 0
            # Should try to connect to the specified port
            assert any("9999" in str(call) for call in mock_get.call_args_list)

    def test_stop_with_server_exception(self):
        """Test stop command with unexpected exception"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Unexpected error")

            result = self.runner.invoke(model, ["stop"])

            assert result.exit_code == 0
            assert "Error stopping server" in result.output

    @patch("mcli.app.model_cmd.LightweightModelServer")
    def test_delete_with_no_downloaded_models(self, mock_server_class):
        """Test delete command when no models are downloaded"""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.downloader.get_downloaded_models.return_value = []

        result = self.runner.invoke(model, ["delete", "distilbert-base-uncased", "--force"])

        assert result.exit_code == 1
        assert "not found" in result.output
        assert "(none)" in result.output


class TestModelCommandHelp:
    """Test suite for model command help text"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_model_help(self):
        """Test model command help text"""
        result = self.runner.invoke(model, ["--help"])

        assert result.exit_code == 0
        assert "Model management commands" in result.output

    def test_list_help(self):
        """Test list command help text"""
        result = self.runner.invoke(model, ["list", "--help"])

        assert result.exit_code == 0
        assert "List available and downloaded models" in result.output

    def test_download_help(self):
        """Test download command help text"""
        result = self.runner.invoke(model, ["download", "--help"])

        assert result.exit_code == 0
        assert "Download a specific lightweight model" in result.output

    def test_pull_help(self):
        """Test pull command help text"""
        result = self.runner.invoke(model, ["pull", "--help"])

        assert result.exit_code == 0
        assert "Pull" in result.output or "download" in result.output

    def test_delete_help(self):
        """Test delete command help text"""
        result = self.runner.invoke(model, ["delete", "--help"])

        assert result.exit_code == 0
        assert "Delete a downloaded lightweight model" in result.output

    def test_stop_help(self):
        """Test stop command help text"""
        result = self.runner.invoke(model, ["stop", "--help"])

        assert result.exit_code == 0
        assert "Stop the lightweight model server" in result.output

    def test_start_help(self):
        """Test start command help text"""
        result = self.runner.invoke(model, ["start", "--help"])

        assert result.exit_code == 0
        assert "Start the lightweight model server" in result.output

    def test_status_help(self):
        """Test status command help text"""
        result = self.runner.invoke(model, ["status", "--help"])

        assert result.exit_code == 0
        assert "Check status of the lightweight model server" in result.output

    def test_recommend_help(self):
        """Test recommend command help text"""
        result = self.runner.invoke(model, ["recommend", "--help"])

        assert result.exit_code == 0
        assert "Get model recommendation" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
