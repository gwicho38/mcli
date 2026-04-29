"""Unit tests for the persistent sync key store.

The store provides a generate / set / get / clear API backed by
``~/.mcli/sync_key.json`` (chmod 0600). ``ipns_manager.get_sync_key``
prefers the ``MCLI_SYNC_KEY`` environment variable but falls back to
the store, so users do not have to export the env var on every shell.
"""

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest


def _isolate_home(tmp_path: Path):
    """Force get_mcli_home() to point inside tmp_path for the duration of a test."""
    return patch("mcli.lib.sync_key_store.get_mcli_home", return_value=tmp_path)


class TestGenerate:
    def test_generate_returns_64_hex_chars(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            key = store.generate()

        assert len(key) == 64
        int(key, 16)  # valid hex

    def test_generate_persists_key(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            key = store.generate()
            assert store.get() == key

    def test_generate_writes_file_with_0600_perms(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            store.generate()
            path = tmp_path / "sync_key.json"

        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600

    def test_generate_does_not_overwrite_without_force(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            first = store.generate()
            with pytest.raises(FileExistsError):
                store.generate()
            assert store.get() == first

    def test_generate_force_overwrites(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            first = store.generate()
            second = store.generate(force=True)

        assert first != second


class TestSetClearGet:
    def test_set_validates_hex_and_length(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            with pytest.raises(ValueError, match="64-char hex"):
                store.set("not-hex")
            with pytest.raises(ValueError, match="64-char hex"):
                store.set("abc")
            with pytest.raises(ValueError, match="64-char hex"):
                store.set("z" * 64)

    def test_set_accepts_valid_key(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        valid = "a" * 64
        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            store.set(valid)
            assert store.get() == valid

    def test_get_returns_none_when_unset(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            assert store.get() is None

    def test_clear_removes_key(self, tmp_path):
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            store = SyncKeyStore()
            store.generate()
            assert store.get() is not None
            store.clear()
            assert store.get() is None


class TestGetSyncKeyFallback:
    """``ipns_manager.get_sync_key`` should: env var first, store second."""

    def test_env_var_wins(self, tmp_path, monkeypatch):
        from mcli.lib import ipns_manager
        from mcli.lib.sync_key_store import SyncKeyStore

        with _isolate_home(tmp_path):
            SyncKeyStore().set("b" * 64)
            monkeypatch.setenv("MCLI_SYNC_KEY", "env-key-value")
            assert ipns_manager.get_sync_key() == "env-key-value"

    def test_falls_back_to_store_when_env_missing(self, tmp_path, monkeypatch):
        from mcli.lib import ipns_manager
        from mcli.lib.sync_key_store import SyncKeyStore

        monkeypatch.delenv("MCLI_SYNC_KEY", raising=False)
        with _isolate_home(tmp_path):
            SyncKeyStore().set("c" * 64)
            assert ipns_manager.get_sync_key() == "c" * 64

    def test_returns_none_when_nothing_configured(self, tmp_path, monkeypatch):
        from mcli.lib import ipns_manager

        monkeypatch.delenv("MCLI_SYNC_KEY", raising=False)
        with _isolate_home(tmp_path):
            assert ipns_manager.get_sync_key() is None
