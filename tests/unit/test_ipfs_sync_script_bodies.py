"""Unit tests for script-body sync via IPFS.

Validates the fix for the bug where push() only uploaded the lockfile
manifest and pull() returned only metadata — script bodies never made
it to IPFS.

After the fix:
- push() should add each workflow script to IPFS and embed the resulting
  per-script CID into the lockfile entry (under the key ``script_cid``).
- pull_workflows() should fetch each script CID, write the file content
  to a destination workflows directory, and verify the SHA-256
  ``content_hash`` recorded in the lockfile.
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SAMPLE_SCRIPT = (
    "#!/usr/bin/env python3\n"
    "# @description: example\n"
    "import click\n\n"
    "@click.command()\n"
    "def hello():\n"
    "    click.echo('hi')\n"
)


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _build_lockfile(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal v2.0-style workflows.lock.json plus the script."""
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    script_path = workflows_dir / "hello.py"
    script_path.write_text(SAMPLE_SCRIPT)

    lockfile_path = workflows_dir / "commands.lock.json"
    lockfile_path.write_text(
        json.dumps(
            {
                "version": "2.0",
                "generated_at": "2026-04-29T00:00:00Z",
                "commands": {
                    "hello": {
                        "file": "hello.py",
                        "language": "python",
                        "version": "1.0.0",
                        "description": "example",
                        "content_hash": _sha256(SAMPLE_SCRIPT),
                        "group": "workflows",
                        "shell": None,
                        "tags": [],
                        "requires": [],
                        "author": "",
                        "last_modified": "2026-04-29T00:00:00Z",
                    }
                },
            }
        )
    )
    return lockfile_path, script_path


class TestPushEmbedsScriptCids:
    """push() must add each script to IPFS and embed its CID in the lockfile."""

    def test_push_adds_script_to_ipfs_and_records_cid(self, tmp_path):
        from mcli.lib.ipfs_sync import IPFSSync

        lockfile_path, script_path = _build_lockfile(tmp_path)
        sync = IPFSSync()

        # add_file_to_ipfs is the new helper we expect for individual files
        with (
            patch.object(sync, "add_file_to_ipfs", return_value="QmScriptCid") as mock_add,
            patch.object(sync, "upload_to_ipfs", return_value="QmManifestCid") as mock_upload,
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value=None),
            patch.object(sync, "_save_sync_history"),
        ):
            cid = sync.push(lockfile_path)

        assert cid == "QmManifestCid"
        # Each script was uploaded
        mock_add.assert_called_once()
        called_path = mock_add.call_args[0][0]
        assert Path(called_path) == script_path
        # The uploaded manifest carried the script CID inside the entry
        uploaded_payload = mock_upload.call_args[0][0]
        commands = uploaded_payload["commands"]["commands"]
        assert commands["hello"]["script_cid"] == "QmScriptCid"
        assert uploaded_payload["commands"]["version"] == "2.1"

    def test_push_skips_script_upload_when_file_missing(self, tmp_path):
        """If the script file is missing, push must not crash — entry has no script_cid."""
        from mcli.lib.ipfs_sync import IPFSSync

        lockfile_path, script_path = _build_lockfile(tmp_path)
        script_path.unlink()
        sync = IPFSSync()

        with (
            patch.object(sync, "add_file_to_ipfs") as mock_add,
            patch.object(sync, "upload_to_ipfs", return_value="QmManifestCid") as mock_upload,
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value=None),
            patch.object(sync, "_save_sync_history"),
        ):
            cid = sync.push(lockfile_path)

        assert cid == "QmManifestCid"
        mock_add.assert_not_called()
        commands = mock_upload.call_args[0][0]["commands"]["commands"]
        assert "script_cid" not in commands["hello"]


class TestPullWorkflowsExtractsScripts:
    """pull_workflows() reconstructs script files from per-script CIDs."""

    def test_pull_workflows_writes_script_and_verifies_hash(self, tmp_path):
        from mcli.lib.ipfs_sync import IPFSSync

        target = tmp_path / "out"
        target.mkdir()

        manifest = {
            "version": "2.1",
            "commands": {
                "hello": {
                    "file": "hello.py",
                    "content_hash": _sha256(SAMPLE_SCRIPT),
                    "script_cid": "QmScriptCid",
                }
            },
        }

        sync = IPFSSync()
        with (
            patch.object(sync, "pull", return_value=manifest),
            patch.object(
                sync, "fetch_file_from_ipfs", return_value=SAMPLE_SCRIPT.encode()
            ) as mock_fetch,
        ):
            written = sync.pull_workflows("QmManifestCid", target)

        mock_fetch.assert_called_once_with("QmScriptCid")
        assert (target / "hello.py").read_text() == SAMPLE_SCRIPT
        assert written == [target / "hello.py"]

    def test_pull_workflows_rejects_hash_mismatch(self, tmp_path):
        from mcli.lib.ipfs_sync import IPFSSync

        target = tmp_path / "out"
        target.mkdir()

        manifest = {
            "version": "2.1",
            "commands": {
                "hello": {
                    "file": "hello.py",
                    "content_hash": _sha256("totally different content"),
                    "script_cid": "QmScriptCid",
                }
            },
        }

        sync = IPFSSync()
        with (
            patch.object(sync, "pull", return_value=manifest),
            patch.object(sync, "fetch_file_from_ipfs", return_value=SAMPLE_SCRIPT.encode()),
        ):
            with pytest.raises(ValueError, match="hash mismatch"):
                sync.pull_workflows("QmManifestCid", target)

        assert not (target / "hello.py").exists()

    def test_pull_workflows_handles_legacy_v2_lockfile(self, tmp_path):
        """A v2.0 manifest without script_cid should warn but not crash."""
        from mcli.lib.ipfs_sync import IPFSSync

        target = tmp_path / "out"
        target.mkdir()

        manifest = {
            "version": "2.0",
            "commands": {
                "hello": {
                    "file": "hello.py",
                    "content_hash": _sha256(SAMPLE_SCRIPT),
                }
            },
        }

        sync = IPFSSync()
        with patch.object(sync, "pull", return_value=manifest):
            written = sync.pull_workflows("QmManifestCid", target)

        assert written == []
        assert not (target / "hello.py").exists()


class TestPullWorkflowsRejectsPathTraversal:
    """A malicious manifest must not be able to write outside the workflows dir."""

    @pytest.mark.parametrize(
        "evil_name",
        [
            "../escape.py",
            "../../escape.py",
            "sub/../../escape.py",
            "foo/../../../escape.py",
        ],
    )
    def test_pull_workflows_rejects_relative_traversal(self, tmp_path, evil_name):
        from mcli.lib.ipfs_sync import IPFSSync

        target = tmp_path / "out"
        target.mkdir()
        outside = tmp_path / "escape.py"

        manifest = {
            "version": "2.1",
            "commands": {
                "evil": {
                    "file": evil_name,
                    "content_hash": _sha256(SAMPLE_SCRIPT),
                    "script_cid": "QmScriptCid",
                }
            },
        }

        sync = IPFSSync()
        with (
            patch.object(sync, "pull", return_value=manifest),
            patch.object(sync, "fetch_file_from_ipfs", return_value=SAMPLE_SCRIPT.encode()),
        ):
            with pytest.raises(ValueError, match="escapes|unsafe"):
                sync.pull_workflows("QmManifestCid", target)

        # nothing escaped the target directory
        assert not outside.exists()

    def test_pull_workflows_rejects_absolute_path(self, tmp_path):
        from mcli.lib.ipfs_sync import IPFSSync

        target = tmp_path / "out"
        target.mkdir()
        abs_target = tmp_path / "abs_escape.py"

        manifest = {
            "version": "2.1",
            "commands": {
                "evil": {
                    "file": str(abs_target),  # absolute path in manifest
                    "content_hash": _sha256(SAMPLE_SCRIPT),
                    "script_cid": "QmScriptCid",
                }
            },
        }

        sync = IPFSSync()
        with (
            patch.object(sync, "pull", return_value=manifest),
            patch.object(sync, "fetch_file_from_ipfs", return_value=SAMPLE_SCRIPT.encode()),
        ):
            with pytest.raises(ValueError, match="escapes|unsafe"):
                sync.pull_workflows("QmManifestCid", target)

        assert not abs_target.exists()

    def test_pull_workflows_allows_legit_subdir(self, tmp_path):
        """Group subdirectories like 'demo/hello.py' must still work."""
        from mcli.lib.ipfs_sync import IPFSSync

        target = tmp_path / "out"
        target.mkdir()

        manifest = {
            "version": "2.1",
            "commands": {
                "hello": {
                    "file": "demo/hello.py",
                    "content_hash": _sha256(SAMPLE_SCRIPT),
                    "script_cid": "QmScriptCid",
                }
            },
        }

        sync = IPFSSync()
        with (
            patch.object(sync, "pull", return_value=manifest),
            patch.object(sync, "fetch_file_from_ipfs", return_value=SAMPLE_SCRIPT.encode()),
        ):
            written = sync.pull_workflows("QmManifestCid", target)

        assert (target / "demo" / "hello.py").read_text() == SAMPLE_SCRIPT
        assert written == [target / "demo" / "hello.py"]


class TestGroupedScriptPushUploadsBody:
    """push() must locate and upload bodies of scripts in group subdirectories.

    Regression: ScriptLoader recorded only the basename in the lockfile
    ``file`` field, so push() could not find scripts stored in group
    subdirectories (the normal layout from ``mcli new -g <group>``) and never
    uploaded their bodies. ScriptLoader now records the path relative to the
    workflows dir. (The pull-side reconstruction is covered by
    TestPullWorkflowsRejectsPathTraversal.test_pull_workflows_allows_legit_subdir.)
    """

    def test_loader_records_relative_path_and_push_uploads_subdir_script(self, tmp_path):
        from mcli.lib.ipfs_sync import IPFSSync
        from mcli.lib.script_loader import ScriptLoader

        workflows_dir = tmp_path / "workflows"
        (workflows_dir / "demo").mkdir(parents=True)
        script = workflows_dir / "demo" / "hello.py"
        script.write_text(SAMPLE_SCRIPT)

        loader = ScriptLoader(workflows_dir)
        assert loader.save_lockfile() is True

        data = json.loads(loader.lockfile_path.read_text())
        # The `file` field must preserve the subdir so push() can find the body.
        assert data["commands"]["hello"]["file"] == "demo/hello.py"

        sync = IPFSSync()
        with (
            patch.object(sync, "add_file_to_ipfs", return_value="QmScriptCid") as mock_add,
            patch.object(sync, "upload_to_ipfs", return_value="QmManifestCid") as mock_upload,
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value=None),
            patch.object(sync, "_save_sync_history"),
        ):
            cid = sync.push(loader.lockfile_path)

        assert cid == "QmManifestCid"
        mock_add.assert_called_once()
        # push must read the body from the subdir, not the workflows root.
        assert Path(mock_add.call_args[0][0]) == script
        commands = mock_upload.call_args[0][0]["commands"]["commands"]
        assert commands["hello"]["script_cid"] == "QmScriptCid"
