"""Unit tests for IPNS-aware sync operations."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestIPNSPush:
    """Tests for push with IPNS publishing."""

    def test_push_publishes_to_ipns_when_sync_key_set(self, tmp_path):
        """Push uploads to IPFS and publishes CID to IPNS."""
        from mcli.lib.ipfs_sync import IPFSSync

        lockfile = tmp_path / "commands.lock.json"
        lockfile.write_text(json.dumps({"commands": {"test": {}}}))

        sync = IPFSSync()

        with (
            patch.object(sync, "upload_to_ipfs", return_value="QmTestCid123"),
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name", return_value="my-repo"),
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value="12D3KooW..."),
            patch("mcli.lib.ipfs_sync.publish_to_ipns", return_value="/ipns/12D3KooW...") as mock_pub,
            patch.object(sync, "_save_sync_history"),
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc123")
            cid = sync.push(lockfile)
            assert cid == "QmTestCid123"
            mock_pub.assert_called_once_with("QmTestCid123", "mcli-abc123")

    def test_push_succeeds_without_sync_key(self, tmp_path):
        """Push works without IPNS when MCLI_SYNC_KEY is not set."""
        from mcli.lib.ipfs_sync import IPFSSync

        lockfile = tmp_path / "commands.lock.json"
        lockfile.write_text(json.dumps({"commands": {"test": {}}}))

        sync = IPFSSync()

        with (
            patch.object(sync, "upload_to_ipfs", return_value="QmTestCid123"),
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value=None),
            patch("mcli.lib.ipfs_sync.publish_to_ipns") as mock_pub,
            patch.object(sync, "_save_sync_history"),
        ):
            cid = sync.push(lockfile)
            assert cid == "QmTestCid123"
            mock_pub.assert_not_called()


class TestIPNSPull:
    """Tests for pull with IPNS resolution."""

    def test_pull_resolves_via_ipns_when_no_cid(self):
        """pull_latest resolves CID via IPNS then retrieves it."""
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()

        with (
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name", return_value="my-repo"),
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value="12D3KooW..."),
            patch("mcli.lib.ipfs_sync.resolve_ipns", return_value="QmResolved123"),
            patch.object(sync, "pull", return_value={"commands": {"a": {}}}) as mock_pull,
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc123")
            result = sync.pull_latest(scope="global")
            assert result == {"commands": {"a": {}}}
            mock_pull.assert_called_once_with("QmResolved123", verify=True)

    def test_pull_latest_returns_none_without_sync_key(self):
        """pull_latest returns None when MCLI_SYNC_KEY is not set."""
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()

        with patch("mcli.lib.ipfs_sync.get_sync_key", return_value=None):
            result = sync.pull_latest(scope="global")
            assert result is None

    def test_pull_latest_returns_none_on_resolve_failure(self):
        """pull_latest returns None when IPNS resolution fails."""
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()

        with (
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name", return_value="my-repo"),
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value="12D3KooW..."),
            patch("mcli.lib.ipfs_sync.resolve_ipns", return_value=None),
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc123")
            result = sync.pull_latest(scope="global")
            assert result is None

    def test_pull_latest_uses_repo_override(self):
        """pull_latest uses --repo override when provided."""
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()

        with (
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name") as mock_repo,
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value="12D3KooW..."),
            patch("mcli.lib.ipfs_sync.resolve_ipns", return_value="QmResolved"),
            patch.object(sync, "pull", return_value={"commands": {}}),
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc123")
            sync.pull_latest(scope="global", repo_name="other-repo")
            # get_repo_name should NOT be called when repo_name is provided
            mock_repo.assert_not_called()
            mock_derive.assert_called_once_with("my-secret", "other-repo", "global")
