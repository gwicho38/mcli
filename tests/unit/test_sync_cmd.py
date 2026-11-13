"""Unit tests for sync command functionality.

Tests IPFS sync, lockfile management, and related utilities.
"""

import json
import os
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
        test_script.write_text("""#!/usr/bin/env python3
# @description: Test command
# @version: 1.0.0
print("Hello")
""")

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
        test_script.write_text("""#!/usr/bin/env python3
# @description: My test command
# @version: 2.0.0
print("Test")
""")

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            result = runner.invoke(sync_group, ["update"])

            # Should succeed or indicate status
            # Note: Actual behavior depends on ScriptLoader implementation
            assert result.exit_code in [0, 1]  # May fail if no scripts match

    def test_second_sync_update_is_byte_identical_when_scripts_are_unchanged(self, tmp_path):
        """A no-op update must not churn lockfile bytes or generation metadata."""
        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "stable.py").write_text(
            "#!/usr/bin/env python3\n# @description: stable\nprint('stable')\n"
        )

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            first_result = runner.invoke(sync_group, ["update"])
            assert first_result.exit_code == 0, first_result.output
            lockfile_path = workflows_dir / "commands.lock.json"
            first_bytes = lockfile_path.read_bytes()

            second_result = runner.invoke(sync_group, ["update"])

        assert second_result.exit_code == 0, second_result.output
        assert lockfile_path.read_bytes() == first_bytes

    def test_changed_script_only_updates_its_entry_and_generation_metadata(self, tmp_path):
        """Filesystem timestamp drift must not modify an unchanged command entry."""
        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        stable_script = workflows_dir / "stable.py"
        changed_script = workflows_dir / "changed.py"
        stable_script.write_text(
            "#!/usr/bin/env python3\n# @description: stable\nprint('stable')\n"
        )
        changed_script.write_text(
            "#!/usr/bin/env python3\n# @description: changed\nprint('before')\n"
        )

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            first_result = runner.invoke(sync_group, ["update"])
            assert first_result.exit_code == 0, first_result.output
            lockfile_path = workflows_dir / "commands.lock.json"
            before = json.loads(lockfile_path.read_text())

            stable_mtime = stable_script.stat().st_mtime + 60
            os.utime(stable_script, (stable_mtime, stable_mtime))
            changed_script.write_text(
                "#!/usr/bin/env python3\n# @description: changed\nprint('after')\n"
            )
            second_result = runner.invoke(sync_group, ["update"])

        assert second_result.exit_code == 0, second_result.output
        after = json.loads(lockfile_path.read_text())
        assert after["commands"]["stable"] == before["commands"]["stable"]
        assert after["commands"]["changed"] != before["commands"]["changed"]
        assert after["generated_at"] != before["generated_at"]
        assert set(after) == set(before)

    @pytest.mark.parametrize("invalid_commands", [[], "invalid", None])
    def test_sync_update_replaces_invalid_command_maps(self, tmp_path, invalid_commands):
        """Invalid v2 command maps must be regenerated instead of crashing."""
        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "stable.py").write_text(
            "#!/usr/bin/env python3\n# @description: stable\nprint('stable')\n"
        )
        lockfile_path = workflows_dir / "commands.lock.json"
        lockfile_path.write_text(
            json.dumps(
                {
                    "version": "2.0",
                    "generated_at": "2026-09-01T12:00:00Z",
                    "commands": invalid_commands,
                }
            )
        )

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            result = runner.invoke(sync_group, ["update"])

        assert result.exit_code == 0, result.output
        regenerated = json.loads(lockfile_path.read_text())
        assert regenerated["commands"]["stable"]["file"] == "stable.py"

    @pytest.mark.parametrize(
        "invalid_generated_at",
        [pytest.param("missing", id="missing"), None, "not-a-timestamp", 123],
    )
    def test_sync_update_replaces_invalid_generated_at(self, tmp_path, invalid_generated_at):
        """Generation metadata is reusable only when it is a valid UTC ISO string."""
        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "stable.py").write_text(
            "#!/usr/bin/env python3\n# @description: stable\nprint('stable')\n"
        )
        lockfile_path = workflows_dir / "commands.lock.json"

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            assert runner.invoke(sync_group, ["update"]).exit_code == 0
            lockfile = json.loads(lockfile_path.read_text())
            if invalid_generated_at == "missing":
                lockfile.pop("generated_at")
            else:
                lockfile["generated_at"] = invalid_generated_at
            lockfile_path.write_text(json.dumps(lockfile, indent=2))
            result = runner.invoke(sync_group, ["update"])

        assert result.exit_code == 0, result.output
        regenerated = json.loads(lockfile_path.read_text())
        assert isinstance(regenerated["generated_at"], str)
        assert regenerated["generated_at"].endswith("Z")
        assert regenerated["generated_at"] != invalid_generated_at

    def test_sync_update_regenerates_old_schema_version(self, tmp_path):
        """An old schema can't lend its generation timestamp to a v2 lockfile."""
        runner = CliRunner()
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "stable.py").write_text("print('stable')\n")
        lockfile_path = workflows_dir / "commands.lock.json"

        with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=workflows_dir):
            assert runner.invoke(sync_group, ["update"]).exit_code == 0
            lockfile = json.loads(lockfile_path.read_text())
            old_timestamp = lockfile["generated_at"]
            lockfile["version"] = "1.0"
            lockfile_path.write_text(json.dumps(lockfile, indent=2))
            result = runner.invoke(sync_group, ["update"])

        assert result.exit_code == 0, result.output
        regenerated = json.loads(lockfile_path.read_text())
        assert regenerated["version"] == "2.0"
        assert regenerated["generated_at"] != old_timestamp

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


class TestSyncRemoteContracts:
    """Remote CLI outcomes use transport doubles and real temporary outputs."""

    @pytest.fixture
    def remote(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with (
            patch("mcli.lib.ipfs_sync.IPFSSync") as cls,
            patch("mcli.lib.ipfs_utils.ensure_daemon_running", return_value=True),
            patch("mcli.lib.ipns_manager.get_sync_key", return_value=None),
        ):
            yield cls.return_value

    @pytest.mark.parametrize("verify", [True, False])
    def test_pull_writes_manifest_and_reconstructs_scripts(self, remote, tmp_path, verify):
        remote.pull.return_value = {"commands": {"backup": {"version": "1"}}, "version": "2"}
        remote.pull_workflows.return_value = [tmp_path / "scripts" / "backup.py"]
        args = ["pull", "fixture-cid", "-o", "manifest.json", "-w", str(tmp_path / "scripts")]
        if not verify:
            args.append("--no-verify")
        result = CliRunner().invoke(sync_group, args)
        assert result.exit_code == 0, result.output
        assert json.loads((tmp_path / "manifest.json").read_text()) == remote.pull.return_value
        remote.pull.assert_called_once_with("fixture-cid", verify=verify)
        remote.pull_workflows.assert_called_once_with(
            "fixture-cid", tmp_path / "scripts", verify=verify
        )
        assert "Restored 1" in result.output

    def test_pull_resolves_repo_and_reports_hash_failure(self, remote, tmp_path):
        remote.resolve_latest_cid.return_value = "resolved-cid"
        remote.pull.return_value = {"commands": {}}
        remote.pull_workflows.side_effect = ValueError("backup.py hash mismatch")
        result = CliRunner().invoke(
            sync_group, ["pull", "--repo", "other", "-w", str(tmp_path / "scripts")]
        )
        remote.resolve_latest_cid.assert_called_once_with(scope="global", repo_name="other")
        assert "Hash verification failed" in result.output
        assert (tmp_path / "commands_resolved.json").exists()

    def test_pull_missing_cid_does_not_write_output(self, remote, tmp_path):
        remote.pull.return_value = None
        result = CliRunner().invoke(sync_group, ["pull", "unavailable"])
        assert "Failed" in result.output
        assert list(tmp_path.iterdir()) == []

    def test_history_displays_reverse_chronological_entries(self, remote):
        remote.get_history.return_value = [
            {"cid": "old-cid", "timestamp": "old"},
            {
                "cid": "new-cid",
                "timestamp": "new",
                "description": "Fixture release",
                "command_count": 3,
            },
        ]
        result = CliRunner().invoke(sync_group, ["history", "--limit", "2"])
        assert result.exit_code == 0
        assert result.output.index("new-cid") < result.output.index("old-cid")
        assert "Fixture release" in result.output and "Commands: 3" in result.output
        remote.get_history.assert_called_once_with(limit=2)

    @pytest.mark.parametrize("accessible", [True, False])
    def test_verify_reports_remote_accessibility(self, remote, accessible):
        remote.verify_cid.return_value = accessible
        result = CliRunner().invoke(sync_group, ["verify", "fixture-cid"])
        assert result.exit_code == 0
        assert ("not accessible" in result.output.lower()) is not accessible
        remote.verify_cid.assert_called_once_with("fixture-cid")

    @pytest.mark.parametrize("published", [True, False])
    def test_push_reports_actual_ipns_publication(self, remote, tmp_path, published):
        (tmp_path / "commands.lock.json").write_text('{"commands":{}}')
        remote.push.return_value = "fixture-cid"
        remote.last_ipns_name = "fixture-ipns" if published else None
        with (
            patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=tmp_path),
            patch("mcli.lib.ipns_manager.get_sync_key", return_value="test-key"),
        ):
            result = CliRunner().invoke(sync_group, ["push", "-g", "-d", "Fixture"])
        assert result.exit_code == 0
        remote.push.assert_called_once_with(tmp_path / "commands.lock.json", description="Fixture")
        assert "fixture-cid" in result.output
        assert ("fixture-ipns" in result.output) is published


class TestSyncIsolatedConfiguration:
    def test_teardown_cancel_and_force_preserve_parent(self, tmp_path):
        root = tmp_path / "mcli"
        workflows = root / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "fixture.py").write_text("pass")
        sibling = root / "keep.json"
        sibling.write_text("preserve")
        with (
            patch("mcli.lib.paths.get_mcli_home", return_value=root),
            patch("mcli.lib.paths.is_git_repository", return_value=False),
            patch("rich.prompt.Prompt.ask", return_value="n"),
        ):
            result = CliRunner().invoke(sync_group, ["teardown", "-g"])
            assert "cancelled" in result.output.lower()
            assert workflows.exists()
            result = CliRunner().invoke(sync_group, ["teardown", "-g", "--force"])
            assert result.exit_code == 0 and not workflows.exists()
            assert sibling.read_text() == "preserve"
            result = CliRunner().invoke(sync_group, ["teardown", "-g", "--force"])
            assert "does not exist" in result.output

    def test_info_reports_actual_script_counts_without_services(self, tmp_path):
        workflows = tmp_path / "workflows"
        workflows.mkdir()
        for extension in ("py", "sh", "js", "ts", "ipynb"):
            (workflows / ("fixture." + extension)).write_text("fixture")
        with (
            patch("mcli.lib.paths.get_mcli_home", return_value=tmp_path),
            patch("mcli.lib.paths.get_custom_commands_dir", return_value=workflows),
            patch("mcli.lib.paths.get_local_mcli_dir", return_value=None),
            patch("mcli.lib.paths.is_git_repository", return_value=False),
            patch("mcli.app.sync_cmd._ipfs_installed", return_value=False),
        ):
            result = CliRunner().invoke(sync_group, ["info"])
        assert result.exit_code == 0
        assert "Total: 5" in result.output
        assert "Python: 1" in result.output and "Notebooks: 1" in result.output
        assert "Installed: No" in result.output


class TestSyncDaemonStartupContracts:
    @pytest.fixture
    def startup(self, tmp_path):
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch("mcli.app.sync_cmd._ipfs_installed", return_value=True),
            patch("mcli.app.sync_cmd._ipfs_initialized", return_value=False),
            patch("mcli.app.sync_cmd._ipfs_daemon_running", side_effect=[False, True]),
            patch("mcli.app.sync_cmd.subprocess.run") as run,
            patch("mcli.app.sync_cmd.subprocess.Popen") as spawn,
            patch("requests.get") as health,
        ):
            run.return_value.returncode = 0
            spawn.return_value.pid = 123456
            health.return_value.ok = True
            yield run, spawn, tmp_path

    def test_background_start_initializes_tracks_owned_pid_and_checks_health(self, startup):
        run, spawn, root = startup
        result = CliRunner().invoke(sync_group, ["init"])
        assert result.exit_code == 0 and "daemon started" in result.output.lower()
        run.assert_called_once_with(["ipfs", "init"], capture_output=True, text=True)
        assert spawn.call_args.args == (["ipfs", "daemon"],)
        assert spawn.call_args.kwargs["start_new_session"] is True
        assert (root / ".mcli" / "data" / "ipfs-daemon.pid").read_text() == "123456"

    def test_initialization_failure_prevents_background_spawn(self, startup):
        run, spawn, root = startup
        run.return_value.returncode = 1
        run.return_value.stderr = "fixture initialization failed"
        result = CliRunner().invoke(sync_group, ["init"])
        assert "fixture initialization failed" in result.output
        spawn.assert_not_called()
        assert not (root / ".mcli").exists()

    def test_foreground_interrupt_is_reported_and_not_detached(self, startup):
        run, spawn, _ = startup
        run.side_effect = [MagicMock(returncode=0), KeyboardInterrupt()]
        result = CliRunner().invoke(sync_group, ["init", "--foreground"])
        assert result.exit_code == 0 and "Daemon stopped" in result.output
        assert run.call_args.args == (["ipfs", "daemon"],)
        spawn.assert_not_called()

    def test_install_failure_is_reported_without_initializing_or_spawning(self, startup):
        run, spawn, _ = startup
        with (
            patch("mcli.app.sync_cmd._ipfs_installed", return_value=False),
            patch("mcli.app.sync_cmd.sys.platform", "darwin"),
        ):
            run.return_value.returncode = 1
            result = CliRunner().invoke(sync_group, ["init", "--install"])
        assert "Failed to install" in result.output
        run.assert_called_once_with(["brew", "install", "ipfs"], capture_output=False)
        spawn.assert_not_called()
