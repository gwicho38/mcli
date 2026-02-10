"""Unit tests for the mcli self ipfs command group and shared IPFS utilities."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mcli.lib.ipfs_utils import (
    check_port_available,
    detect_platform,
    ipfs_daemon_running,
    ipfs_initialized,
    ipfs_installed,
    ipfs_version,
    validate_ipfs_config,
    which_package_manager,
)
from mcli.self.ipfs_cmd import ipfs


@pytest.fixture
def runner():
    return CliRunner()


# ==================================================================
# TestIpfsUtils — shared utility functions
# ==================================================================


class TestIpfsUtils:
    """Unit tests for ipfs_utils.py functions."""

    def test_ipfs_installed_true(self):
        with patch("mcli.lib.ipfs_utils.shutil.which", return_value="/usr/local/bin/ipfs"):
            assert ipfs_installed() is True

    def test_ipfs_installed_false(self):
        with patch("mcli.lib.ipfs_utils.shutil.which", return_value=None):
            assert ipfs_installed() is False

    def test_ipfs_version_success(self):
        with patch("mcli.lib.ipfs_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ipfs version 0.27.0\n")
            assert ipfs_version() == "ipfs version 0.27.0"

    def test_ipfs_version_not_installed(self):
        with patch("mcli.lib.ipfs_utils.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            assert ipfs_version() is None

    def test_ipfs_initialized_true(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            ipfs_dir = tmp_path / ".ipfs"
            ipfs_dir.mkdir()
            (ipfs_dir / "config").write_text("{}")
            assert ipfs_initialized() is True

    def test_ipfs_initialized_false(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            assert ipfs_initialized() is False

    def test_ipfs_daemon_running_true(self):
        with patch("mcli.lib.ipfs_utils.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert ipfs_daemon_running() is True

    def test_ipfs_daemon_running_false(self):
        with patch("mcli.lib.ipfs_utils.requests.post") as mock_post:
            mock_post.side_effect = ConnectionError
            assert ipfs_daemon_running() is False

    def test_detect_platform_returns_tuple(self):
        result = detect_platform()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_check_port_available_open(self):
        # Use a high ephemeral port unlikely to be in use
        assert check_port_available(59999) is True

    def test_which_package_manager_found(self):
        with patch(
            "mcli.lib.ipfs_utils.shutil.which",
            side_effect=lambda n: "/usr/bin/apt-get" if n == "apt-get" else None,
        ):
            assert which_package_manager() == "apt-get"

    def test_which_package_manager_none(self):
        with patch("mcli.lib.ipfs_utils.shutil.which", return_value=None):
            assert which_package_manager() is None

    def test_validate_ipfs_config_valid(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            ipfs_dir = tmp_path / ".ipfs"
            ipfs_dir.mkdir()
            (ipfs_dir / "config").write_text(json.dumps({"API": {}}))
            assert validate_ipfs_config() is True

    def test_validate_ipfs_config_invalid(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            ipfs_dir = tmp_path / ".ipfs"
            ipfs_dir.mkdir()
            (ipfs_dir / "config").write_text("not json{{{")
            assert validate_ipfs_config() is False

    def test_validate_ipfs_config_missing(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            assert validate_ipfs_config() is False


# ==================================================================
# TestIpfsGroup — top-level help
# ==================================================================


class TestIpfsGroup:
    """Tests for the ipfs command group itself."""

    def test_help_shows_subcommands(self, runner):
        result = runner.invoke(ipfs, ["--help"])
        assert result.exit_code == 0
        assert "setup" in result.output
        assert "status" in result.output
        assert "doctor" in result.output


# ==================================================================
# TestIpfsSetup
# ==================================================================


class TestIpfsSetup:
    """Tests for the ``ipfs setup`` subcommand."""

    def test_setup_already_complete(self, runner):
        """When everything is already set up, say so."""
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_version", return_value="ipfs version 0.27.0"),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", return_value=True),
        ):
            result = runner.invoke(ipfs, ["setup"])
            assert result.exit_code == 0
            assert "already" in result.output.lower()

    def test_setup_no_install_flag(self, runner):
        """--no-install skips installation and shows manual instructions."""
        with patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=False):
            result = runner.invoke(ipfs, ["setup", "--no-install"])
            assert result.exit_code == 0
            assert "no-install" in result.output.lower() or "skip" in result.output.lower()

    def test_setup_no_pkg_manager(self, runner):
        """When no package manager is found, show manual instructions."""
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=False),
            patch("mcli.self.ipfs_cmd.which_package_manager", return_value=None),
        ):
            result = runner.invoke(ipfs, ["setup"])
            assert result.exit_code == 0
            assert "No supported package manager" in result.output

    def test_setup_auto_install_macos(self, runner):
        """--auto triggers install via detected package manager."""
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", side_effect=[False, True]),
            patch("mcli.self.ipfs_cmd.ipfs_version", return_value="ipfs version 0.27.0"),
            patch("mcli.self.ipfs_cmd.which_package_manager", return_value="brew"),
            patch("mcli.self.ipfs_cmd.subprocess.run", return_value=MagicMock(returncode=0)),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", return_value=True),
        ):
            result = runner.invoke(ipfs, ["setup", "--auto"])
            assert result.exit_code == 0

    def test_setup_auto_install_failure(self, runner):
        """When install command fails, show error."""
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", side_effect=[False, False]),
            patch("mcli.self.ipfs_cmd.which_package_manager", return_value="brew"),
            patch("mcli.self.ipfs_cmd.subprocess.run", return_value=MagicMock(returncode=1)),
        ):
            result = runner.invoke(ipfs, ["setup", "--auto"])
            assert result.exit_code == 0
            assert "Failed" in result.output or "not installed" in result.output.lower()

    def test_setup_init_step(self, runner):
        """When installed but not initialized, run ipfs init."""
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_version", return_value="ipfs version 0.27.0"),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", side_effect=[False, True]),
            patch(
                "mcli.self.ipfs_cmd.subprocess.run",
                return_value=MagicMock(returncode=0, stderr=""),
            ),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", return_value=True),
        ):
            result = runner.invoke(ipfs, ["setup"])
            assert result.exit_code == 0
            assert "initialized" in result.output.lower()

    def test_setup_starts_daemon(self, runner):
        """When installed and initialized but daemon not running, start it."""
        call_count = {"n": 0}

        def daemon_side_effect():
            call_count["n"] += 1
            # First call (check before starting) returns False, rest True
            return call_count["n"] > 1

        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_version", return_value="ipfs version 0.27.0"),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", side_effect=daemon_side_effect),
            patch("mcli.self.ipfs_cmd.subprocess.Popen", return_value=MagicMock(pid=12345)),
            patch("mcli.self.ipfs_cmd.time.sleep"),
        ):
            result = runner.invoke(ipfs, ["setup"])
            assert result.exit_code == 0
            assert "12345" in result.output


# ==================================================================
# TestIpfsStatus
# ==================================================================


class TestIpfsStatus:
    """Tests for the ``ipfs status`` subcommand."""

    def test_status_not_installed(self, runner):
        with patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=False):
            result = runner.invoke(ipfs, ["status"])
            assert result.exit_code == 0
            assert "No" in result.output

    def test_status_not_initialized(self, runner):
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_version", return_value="ipfs version 0.27.0"),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=False),
        ):
            result = runner.invoke(ipfs, ["status"])
            assert result.exit_code == 0
            assert "No" in result.output

    def test_status_daemon_stopped(self, runner):
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_version", return_value="ipfs version 0.27.0"),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", return_value=False),
        ):
            result = runner.invoke(ipfs, ["status"])
            assert result.exit_code == 0
            assert "No" in result.output

    def test_status_fully_running(self, runner):
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_version", return_value="ipfs version 0.27.0"),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_peer_count", return_value=42),
            patch(
                "mcli.self.ipfs_cmd.ipfs_id_info",
                return_value={"ID": "QmPeerID1234567890abcdef"},
            ),
            patch("mcli.self.ipfs_cmd.ipfs_config_get", return_value="/ip4/127.0.0.1/tcp/5001"),
        ):
            result = runner.invoke(ipfs, ["status"])
            assert result.exit_code == 0
            assert "42" in result.output
            assert "QmPeerID12345678" in result.output


# ==================================================================
# TestIpfsDoctor
# ==================================================================


class TestIpfsDoctor:
    """Tests for the ``ipfs doctor`` subcommand."""

    def test_doctor_not_installed(self, runner):
        with patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=False):
            result = runner.invoke(ipfs, ["doctor"])
            assert result.exit_code == 0
            assert "FAIL" in result.output

    def test_doctor_all_healthy(self, runner):
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=True),
            patch("mcli.self.ipfs_cmd.validate_ipfs_config", return_value=True),
            patch("mcli.self.ipfs_cmd.check_port_available", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_peer_count", return_value=10),
        ):
            result = runner.invoke(ipfs, ["doctor"])
            assert result.exit_code == 0
            assert "All checks passed" in result.output

    def test_doctor_daemon_not_running(self, runner):
        with (
            patch("mcli.self.ipfs_cmd.ipfs_installed", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_initialized", return_value=True),
            patch("mcli.self.ipfs_cmd.validate_ipfs_config", return_value=True),
            patch("mcli.self.ipfs_cmd.check_port_available", return_value=True),
            patch("mcli.self.ipfs_cmd.ipfs_daemon_running", return_value=False),
        ):
            result = runner.invoke(ipfs, ["doctor"])
            assert result.exit_code == 0
            assert "issue" in result.output.lower()
