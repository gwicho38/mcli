"""Unit tests for IPFSSync.resolve_latest_cid().

Adds a thin helper used by the CLI so that ``mcli sync pull`` (no CID)
can capture the resolved CID and fall through to the same explicit-CID
flow that handles ``-w / --workflows-dir`` script extraction.

Without this, the CLI's pre-existing IPNS-auto-resolve path wraps the
CID inside ``pull_latest()`` and never surfaces it, so the extraction
guard ``if workflows_dir and cid`` always falls through.
"""

from unittest.mock import MagicMock, patch


class TestResolveLatestCid:
    def test_returns_cid_when_sync_key_present(self):
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()
        with (
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name", return_value="my-repo"),
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value="12D3KooW..."),
            patch("mcli.lib.ipfs_sync.resolve_ipns", return_value="QmResolved"),
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc")
            assert sync.resolve_latest_cid(scope="global") == "QmResolved"

    def test_returns_none_when_sync_key_missing(self):
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()
        with patch("mcli.lib.ipfs_sync.get_sync_key", return_value=None):
            assert sync.resolve_latest_cid() is None

    def test_returns_none_when_key_import_fails(self):
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()
        with (
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name", return_value="my-repo"),
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value=None),
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc")
            assert sync.resolve_latest_cid() is None

    def test_returns_none_when_ipns_resolve_fails(self):
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()
        with (
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name", return_value="my-repo"),
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value="12D3KooW..."),
            patch("mcli.lib.ipfs_sync.resolve_ipns", return_value=None),
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc")
            assert sync.resolve_latest_cid() is None

    def test_uses_repo_override(self):
        from mcli.lib.ipfs_sync import IPFSSync

        sync = IPFSSync()
        with (
            patch("mcli.lib.ipfs_sync.get_sync_key", return_value="my-secret"),
            patch("mcli.lib.ipfs_sync.get_repo_name") as mock_repo,
            patch("mcli.lib.ipfs_sync.derive_key_info") as mock_derive,
            patch("mcli.lib.ipfs_sync.ensure_key_imported", return_value="12D3KooW"),
            patch("mcli.lib.ipfs_sync.resolve_ipns", return_value="QmX"),
        ):
            mock_derive.return_value = MagicMock(key_name="mcli-abc")
            sync.resolve_latest_cid(scope="global", repo_name="other")
            mock_repo.assert_not_called()
            mock_derive.assert_called_once_with("my-secret", "other", "global")
