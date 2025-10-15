"""
CLI tests for mcli.self.self_cmd plugin management
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


class TestPluginCommands:
    """Test suite for plugin CLI commands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_plugin_group_exists(self):
        """Test plugin command group exists"""
        from mcli.self.self_cmd import plugin

        assert plugin is not None
        assert hasattr(plugin, "commands")

    def test_plugin_group_help(self):
        """Test plugin command group help"""
        from mcli.self.self_cmd import self_app

        result = self.runner.invoke(self_app, ["plugin", "--help"])

        assert result.exit_code == 0
        assert "plugin" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_add_no_config(self):
        """Test adding plugin when no config exists"""
        from mcli.self.self_cmd import self_app

        result = self.runner.invoke(self_app, ["plugin", "add", "test_plugin"])

        # Should show error when config not found
        assert "config" in result.output.lower() or "not found" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    @patch("subprocess.run")
    def test_plugin_add_with_url(self, mock_subprocess):
        """Test adding plugin with repository URL"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary config file
            config_path = Path(tmpdir) / "config.toml"

            with open(config_path, "w") as f:
                f.write("[plugins]\n")

            # Set environment variable to point to our test config
            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                # Mock successful git clone
                mock_subprocess.return_value = MagicMock(returncode=0)

                result = self.runner.invoke(
                    self_app, ["plugin", "add", "test_plugin", "https://github.com/test/repo.git"]
                )

                # Should succeed
                assert result.exit_code == 0
                assert "cloned" in result.output.lower() or "clone" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_add_without_url(self):
        """Test adding plugin without repository URL"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            with open(config_path, "w") as f:
                f.write("[plugins]\n")

            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                result = self.runner.invoke(self_app, ["plugin", "add", "test_plugin"])

                # Should notify that no URL was provided
                assert (
                    "no repo url" in result.output.lower()
                    or "not be downloaded" in result.output.lower()
                )

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_add_already_exists(self):
        """Test adding plugin that already exists in config"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            with open(config_path, "w") as f:
                f.write("[plugins.test_plugin]\n")

            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                result = self.runner.invoke(self_app, ["plugin", "add", "test_plugin"])

                # Should show error when plugin already exists
                assert "already exists" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    @patch("subprocess.run")
    def test_plugin_add_git_clone_failure(self, mock_subprocess):
        """Test adding plugin when git clone fails"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            with open(config_path, "w") as f:
                f.write("[plugins]\n")

            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                # Mock failed git clone
                mock_subprocess.side_effect = Exception("Git clone failed")

                result = self.runner.invoke(
                    self_app, ["plugin", "add", "test_plugin", "https://github.com/test/repo.git"]
                )

                # Should show failure message
                assert "failed" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_remove_no_config(self):
        """Test removing plugin when no config exists"""
        from mcli.self.self_cmd import self_app

        result = self.runner.invoke(self_app, ["plugin", "remove", "test_plugin"])

        # Should show error when config not found
        assert "config" in result.output.lower() or "not found" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_remove_not_exists(self):
        """Test removing plugin that doesn't exist"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            with open(config_path, "w") as f:
                f.write("[plugins]\n")

            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                result = self.runner.invoke(self_app, ["plugin", "remove", "nonexistent_plugin"])

                # Should show error when plugin directory doesn't exist
                assert (
                    "does not exist" in result.output.lower()
                    or "nothing to remove" in result.output.lower()
                )

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_remove_success(self):
        """Test successfully removing a plugin"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            plugin_path = Path(tmpdir) / "plugins"
            plugin_dir = plugin_path / "test_plugin"

            # Create plugin directory
            plugin_dir.mkdir(parents=True)

            with open(config_path, "w") as f:
                f.write(f"plugin_location = '{plugin_path}'\n[plugins.test_plugin]\n")

            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                with patch("shutil.rmtree") as mock_rmtree:
                    result = self.runner.invoke(self_app, ["plugin", "remove", "test_plugin"])

                    # Should succeed
                    assert result.exit_code == 0
                    assert "removed" in result.output.lower()
                    mock_rmtree.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_remove_failure(self):
        """Test plugin removal failure"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            plugin_path = Path(tmpdir) / "plugins"
            plugin_dir = plugin_path / "test_plugin"

            # Create plugin directory
            plugin_dir.mkdir(parents=True)

            with open(config_path, "w") as f:
                f.write(f"plugin_location = '{plugin_path}'\n[plugins.test_plugin]\n")

            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                with patch("shutil.rmtree") as mock_rmtree:
                    # Mock removal failure
                    mock_rmtree.side_effect = Exception("Permission denied")

                    result = self.runner.invoke(self_app, ["plugin", "remove", "test_plugin"])

                    # Should show failure message
                    assert "failed" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_update_no_config(self):
        """Test updating plugin when no config exists"""
        from mcli.self.self_cmd import self_app

        result = self.runner.invoke(self_app, ["plugin", "update", "test_plugin"])

        # Should show error when config not found
        assert "config" in result.output.lower() or "not found" in result.output.lower()

    @patch.dict("os.environ", {}, clear=True)
    def test_plugin_update_not_exists(self):
        """Test updating plugin that doesn't exist"""
        from mcli.self.self_cmd import self_app

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            with open(config_path, "w") as f:
                f.write("[plugins]\n")

            with patch.dict("os.environ", {"MCLI_CONFIG": str(config_path)}):
                result = self.runner.invoke(self_app, ["plugin", "update", "nonexistent_plugin"])

                # Should show error when plugin directory doesn't exist
                assert (
                    "does not exist" in result.output.lower()
                    or "cannot update" in result.output.lower()
                )

    def test_plugin_add_help(self):
        """Test plugin add command help"""
        from mcli.self.self_cmd import self_app

        result = self.runner.invoke(self_app, ["plugin", "add", "--help"])

        assert result.exit_code == 0
        assert "add" in result.output.lower()

    def test_plugin_remove_help(self):
        """Test plugin remove command help"""
        from mcli.self.self_cmd import self_app

        result = self.runner.invoke(self_app, ["plugin", "remove", "--help"])

        assert result.exit_code == 0
        assert "remove" in result.output.lower()

    def test_plugin_update_help(self):
        """Test plugin update command help"""
        from mcli.self.self_cmd import self_app

        result = self.runner.invoke(self_app, ["plugin", "update", "--help"])

        assert result.exit_code == 0
        assert "update" in result.output.lower()
