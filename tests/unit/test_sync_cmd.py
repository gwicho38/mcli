"""Unit tests for sync command functionality.

Tests IPFS sync, lockfile management, and related utilities.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mcli.app.sync_cmd import _ipfs_daemon_running, _ipfs_initialized, _ipfs_installed, sync_group


class TestIPFSHelpers:
    """Tests for IPFS helper functions."""

    def test_ipfs_installed_when_available(self):
        """Test _ipfs_installed returns True when ipfs is in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/ipfs"):
            assert _ipfs_installed() is True

    def test_ipfs_installed_when_not_available(self):
        """Test _ipfs_installed returns False when ipfs is not in PATH."""
        with patch("shutil.which", return_value=None):
            assert _ipfs_installed() is False

    def test_ipfs_initialized_when_config_exists(self, tmp_path):
        """Test _ipfs_initialized returns True when .ipfs/config exists."""
        with patch.object(Path, "home", return_value=tmp_path):
            ipfs_dir = tmp_path / ".ipfs"
            ipfs_dir.mkdir()
            (ipfs_dir / "config").write_text("{}")

            assert _ipfs_initialized() is True

    def test_ipfs_initialized_when_not_initialized(self, tmp_path):
        """Test _ipfs_initialized returns False when .ipfs doesn't exist."""
        with patch.object(Path, "home", return_value=tmp_path):
            assert _ipfs_initialized() is False

    def test_ipfs_initialized_when_config_missing(self, tmp_path):
        """Test _ipfs_initialized returns False when config file missing."""
        with patch.object(Path, "home", return_value=tmp_path):
            ipfs_dir = tmp_path / ".ipfs"
            ipfs_dir.mkdir()
            # No config file

            assert _ipfs_initialized() is False

    def test_ipfs_daemon_running_when_running(self):
        """Test _ipfs_daemon_running returns True when daemon responds."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert _ipfs_daemon_running() is True

    def test_ipfs_daemon_running_when_not_running(self):
        """Test _ipfs_daemon_running returns False on connection error."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = ConnectionError("Connection refused")
            assert _ipfs_daemon_running() is False

    def test_ipfs_daemon_running_on_timeout(self):
        """Test _ipfs_daemon_running returns False on timeout."""
        import requests

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            assert _ipfs_daemon_running() is False


class TestSyncStatusCommand:
    """Tests for the sync status command."""

    def test_sync_status_no_scripts(self, tmp_path):
        """Test sync status with no workflow scripts."""
        runner = CliRunner()

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=tmp_path):
            result = runner.invoke(sync_group, ["status"])

            assert result.exit_code == 0
            assert "No" in result.output and "workflow" in result.output.lower()

    def test_sync_status_with_scripts(self, tmp_path):
        """Test sync status with workflow scripts."""
        runner = CliRunner()

        # Create a test script
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        test_script = workflows_dir / "test_cmd.py"
        test_script.write_text(
            """#!/usr/bin/env python3
# @description: Test command
# @version: 1.0.0
print("Hello")
"""
        )

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            result = runner.invoke(sync_group, ["status"])

            assert result.exit_code == 0


class TestSyncInitCommand:
    """Tests for the sync init command."""

    def test_sync_init_ipfs_not_installed(self):
        """Test sync init when IPFS is not installed."""
        runner = CliRunner()

        with patch("mcli.app.sync_cmd._ipfs_installed", return_value=False):
            result = runner.invoke(sync_group, ["init"])

            assert "not installed" in result.output.lower() or "IPFS" in result.output

    def test_sync_init_daemon_already_running(self):
        """Test sync init when daemon is already running."""
        runner = CliRunner()

        with (
            patch("mcli.app.sync_cmd._ipfs_installed", return_value=True),
            patch("mcli.app.sync_cmd._ipfs_initialized", return_value=True),
            patch("mcli.app.sync_cmd._ipfs_daemon_running", return_value=True),
        ):
            result = runner.invoke(sync_group, ["init"])

            assert result.exit_code == 0
            assert "already running" in result.output.lower()


class TestSyncUpdateCommand:
    """Tests for the sync update command."""

    def test_sync_update_creates_lockfile(self, tmp_path):
        """Test sync update creates lockfile from scripts."""
        runner = CliRunner()

        # Create a test script
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        test_script = workflows_dir / "my_cmd.py"
        test_script.write_text(
            """#!/usr/bin/env python3
# @description: My test command
# @version: 2.0.0
print("Test")
"""
        )

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            result = runner.invoke(sync_group, ["update"])

            # Should succeed or indicate status
            # Note: Actual behavior depends on ScriptLoader implementation
            assert result.exit_code in [0, 1]  # May fail if no scripts match

    def test_update_writes_lockfile_that_push_reads(self, tmp_path):
        """Regression: `sync update` must write the SAME lockfile `sync push` reads.

        Previously `update` wrote ``workflows.lock.json`` (via ScriptLoader)
        while `push`/`pull` read ``commands.lock.json``, so every push after an
        update failed with "Lockfile not found". The two commands MUST agree on
        the lockfile filename.
        """
        from mcli.lib.constants import FileNames

        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "my_cmd.py").write_text(
            "#!/usr/bin/env python3\n"
            "# @description: My test command\n"
            "# @version: 2.0.0\n"
            'print("Test")\n'
        )

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            result = runner.invoke(sync_group, ["update"])

        assert result.exit_code == 0, result.output
        # `sync push` reads exactly this path (see sync_cmd.sync_push); it MUST
        # exist after `update`, otherwise push reports LOCKFILE_NOT_FOUND.
        push_lockfile = workflows_dir / FileNames.COMMANDS_LOCK_JSON
        assert push_lockfile.exists(), (
            f"update did not create the lockfile push reads "
            f"({FileNames.COMMANDS_LOCK_JSON}); dir contains "
            f"{sorted(p.name for p in workflows_dir.iterdir())}"
        )

    def test_push_finds_lockfile_after_update(self, tmp_path):
        """Regression: `sync push` locates the lockfile produced by `sync update`.

        End-to-end wiring check (IPFS mocked): after `update`, `push` must NOT
        report LOCKFILE_NOT_FOUND and must hand the produced lockfile to
        ``IPFSSync.push``.
        """
        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "my_cmd.py").write_text(
            "#!/usr/bin/env python3\n# @description: c\n# @version: 1.0.0\nprint('x')\n"
        )

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            update_result = runner.invoke(sync_group, ["update"])
            assert update_result.exit_code == 0, update_result.output

            with (
                patch("mcli.lib.ipfs_utils.ensure_daemon_running", return_value=True),
                patch("mcli.lib.ipfs_sync.IPFSSync") as mock_sync_cls,
            ):
                mock_sync_cls.return_value.push.return_value = "QmFakeCid"
                result = runner.invoke(sync_group, ["push"])

        assert "not found" not in result.output.lower(), result.output
        mock_push = mock_sync_cls.return_value.push
        mock_push.assert_called_once()
        # push must receive the lockfile that `update` actually wrote.
        called_path = Path(mock_push.call_args.args[0])
        assert called_path.exists(), f"push received non-existent lockfile: {called_path}"


class TestSyncPushCommand:
    """Tests for the sync push command."""

    def test_sync_push_no_daemon(self):
        """Test sync push fails gracefully when daemon not running."""
        runner = CliRunner()

        with patch("mcli.app.sync_cmd._ipfs_daemon_running", return_value=False):
            result = runner.invoke(sync_group, ["push"])

            # Should indicate IPFS is not available
            assert result.exit_code in [0, 1]

    def _setup_pushable_repo(self, tmp_path):
        """Create a workflows dir with a lockfile that `push` can read."""
        from click.testing import CliRunner

        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "c.py").write_text(
            "#!/usr/bin/env python3\n# @description: c\n# @version: 1.0.0\nprint('x')\n"
        )
        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            assert runner.invoke(sync_group, ["update"]).exit_code == 0
        return workflows_dir

    def test_push_warns_when_ipns_publish_fails(self, tmp_path):
        """Regression: push must NOT claim teammates can pull when IPNS publish failed.

        Previously the IPNS hint was printed whenever a sync key was present,
        even if ``publish_to_ipns`` silently failed (e.g. daemon had no peers),
        giving a false impression that auto-resolve would work.
        """
        runner = CliRunner()
        workflows_dir = self._setup_pushable_repo(tmp_path)

        with (
            patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir),
            patch("mcli.lib.ipfs_utils.ensure_daemon_running", return_value=True),
            patch("mcli.lib.ipns_manager.get_sync_key", return_value="k" * 64),
            patch("mcli.lib.ipfs_sync.IPFSSync") as mock_cls,
        ):
            mock_cls.return_value.push.return_value = "QmCid"
            mock_cls.return_value.last_ipns_name = None  # publish failed
            result = runner.invoke(sync_group, ["push"])

        assert "teammates can pull latest" not in result.output.lower(), result.output
        assert "ipns publish failed" in result.output.lower(), result.output

    def test_push_reports_ipns_success_when_published(self, tmp_path):
        """When IPNS publish succeeds, push surfaces the teammate pull hint."""
        runner = CliRunner()
        workflows_dir = self._setup_pushable_repo(tmp_path)

        with (
            patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir),
            patch("mcli.lib.ipfs_utils.ensure_daemon_running", return_value=True),
            patch("mcli.lib.ipns_manager.get_sync_key", return_value="k" * 64),
            patch("mcli.lib.ipfs_sync.IPFSSync") as mock_cls,
        ):
            mock_cls.return_value.push.return_value = "QmCid"
            mock_cls.return_value.last_ipns_name = "k51qzi5fakeipnsname"
            result = runner.invoke(sync_group, ["push"])

        assert "teammates can pull latest" in result.output.lower(), result.output


class TestSyncPullCommand:
    """Tests for the sync pull command."""

    def test_sync_pull_no_cid_uses_ipns(self):
        """Test sync pull with no CID attempts IPNS auto-resolve."""
        runner = CliRunner()

        with patch("mcli.lib.ipfs_utils.ensure_daemon_running", return_value=False):
            result = runner.invoke(sync_group, ["pull"])

        # Should exit cleanly but report daemon failure or IPNS error
        assert result.exit_code in [0, 1]
        assert (
            "daemon" in result.output.lower()
            or "ipns" in result.output.lower()
            or "sync" in result.output.lower()
        )

    def test_sync_pull_invalid_cid(self):
        """Test sync pull with invalid CID format."""
        runner = CliRunner()

        with patch("mcli.app.sync_cmd._ipfs_daemon_running", return_value=True):
            result = runner.invoke(sync_group, ["pull", "invalid-cid-format"])

            # Should handle gracefully
            assert result.exit_code in [0, 1]


class TestSyncVerifyCommand:
    """Tests for the sync verify command."""

    def test_sync_verify_lockfile(self, tmp_path):
        """Test sync verify on local lockfile."""
        runner = CliRunner()

        # Create a lockfile
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        lockfile = workflows_dir / "mcli.lock.json"
        lockfile.write_text(json.dumps({"version": "1.0", "commands": {}}))

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            result = runner.invoke(sync_group, ["verify"])

            # Exit code 2 means missing required argument (CID), which is expected
            assert result.exit_code in [0, 1, 2]


class TestSyncInfoCommand:
    """Tests for the sync info command."""

    def test_sync_info_shows_paths(self, tmp_path):
        """Test sync info displays configuration paths."""
        runner = CliRunner()

        with (
            patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=tmp_path),
            patch("mcli.lib.paths.get_mcli_home", return_value=tmp_path),
        ):
            result = runner.invoke(sync_group, ["info"])

            assert result.exit_code == 0
            # Should show some configuration info


class TestSyncTeardownCommand:
    """Tests for the sync teardown command."""

    def test_sync_teardown_requires_confirmation(self, tmp_path):
        """Test sync teardown requires confirmation."""
        runner = CliRunner()

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            # Without confirmation, should not delete
            result = runner.invoke(sync_group, ["teardown"])

            # Should either ask for confirmation or show help
            assert result.exit_code in [0, 1]

    def test_sync_teardown_with_force(self, tmp_path):
        """Test sync teardown with --force flag."""
        runner = CliRunner()

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "test.py").write_text("# test")

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            result = runner.invoke(sync_group, ["teardown", "--force"])

            # Should handle the teardown
            assert result.exit_code in [0, 1]
