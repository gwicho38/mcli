"""Unit tests for IPFS daemon auto-management."""

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest


class TestEnsureDaemonRunning:
    """Tests for ensure_daemon_running()."""

    def test_returns_true_when_already_running(self):
        """Returns True immediately if daemon is already on port 5001."""
        from mcli.lib.ipfs_utils import ensure_daemon_running

        with patch("mcli.lib.ipfs_utils.ipfs_daemon_running", return_value=True):
            assert ensure_daemon_running() is True

    def test_starts_daemon_when_installed_and_initialized(self):
        """Installs nothing, just starts daemon when binary + repo exist."""
        from mcli.lib.ipfs_utils import ensure_daemon_running

        running_calls = [False, False, True]  # not running, not running, then running

        with (
            patch("mcli.lib.ipfs_utils.ipfs_daemon_running", side_effect=running_calls),
            patch("mcli.lib.ipfs_utils.ipfs_installed", return_value=True),
            patch("mcli.lib.ipfs_utils.ipfs_initialized", return_value=True),
            patch("subprocess.Popen") as mock_popen,
            patch("time.sleep"),
        ):
            mock_popen.return_value.pid = 12345
            assert ensure_daemon_running() is True

    def test_initializes_repo_before_starting(self):
        """Runs ipfs init if repo not initialized."""
        from mcli.lib.ipfs_utils import ensure_daemon_running

        running_calls = [False, False, True]

        with (
            patch("mcli.lib.ipfs_utils.ipfs_daemon_running", side_effect=running_calls),
            patch("mcli.lib.ipfs_utils.ipfs_installed", return_value=True),
            patch("mcli.lib.ipfs_utils.ipfs_initialized", return_value=False),
            patch("subprocess.run") as mock_run,
            patch("subprocess.Popen") as mock_popen,
            patch("time.sleep"),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            mock_popen.return_value.pid = 12345
            assert ensure_daemon_running() is True
            # Verify ipfs init was called
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["ipfs", "init"]

    def test_returns_false_when_not_installed_non_interactive(self):
        """Returns False when IPFS not installed and non-interactive."""
        from mcli.lib.ipfs_utils import ensure_daemon_running

        with (
            patch("mcli.lib.ipfs_utils.ipfs_daemon_running", return_value=False),
            patch("mcli.lib.ipfs_utils.ipfs_installed", return_value=False),
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = False
            assert ensure_daemon_running() is False

    def test_returns_false_when_daemon_fails_to_start(self):
        """Returns False if daemon doesn't respond after timeout."""
        from mcli.lib.ipfs_utils import ensure_daemon_running

        with (
            patch("mcli.lib.ipfs_utils.ipfs_daemon_running", return_value=False),
            patch("mcli.lib.ipfs_utils.ipfs_installed", return_value=True),
            patch("mcli.lib.ipfs_utils.ipfs_initialized", return_value=True),
            patch("subprocess.Popen"),
            patch("time.sleep"),
        ):
            assert ensure_daemon_running() is False
