"""Encrypted secret persistence and local Git synchronization without real credentials."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from git import Repo

from mcli.lib.secrets.manager import SecretsManager
from mcli.lib.secrets.store import SecretsStore

pytestmark = pytest.mark.unit


def test_encryption_namespaces_reopen_and_tamper(tmp_path):
    with patch("mcli.lib.secrets.manager.click.prompt", return_value="fixture-password") as prompt:
        manager = SecretsManager(tmp_path / "encrypted")
    prompt.assert_called_once()
    manager.set("api-key", "private-value")
    manager.set("api-key", "other-value", "production")
    stored = tmp_path / "encrypted" / "default" / "api-key.secret"
    assert b"private-value" not in stored.read_bytes()
    assert stored.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "encrypted" / ".key").stat().st_mode & 0o777 == 0o600
    reopened = SecretsManager(tmp_path / "encrypted")
    assert reopened.get("api-key") == "private-value"
    assert reopened.get("api-key", "production") == "other-value"
    assert reopened.list() == ["default/api-key", "production/api-key"]
    assert reopened.list("production") == ["api-key"]
    assert reopened.list("missing") == []
    assert reopened.export_env("production") == {"API_KEY": "other-value"}
    stored.write_bytes(b"invalid ciphertext")
    assert reopened.get("api-key") is None
    assert reopened.get("absent") is None
    assert reopened.delete("api-key") is True
    assert reopened.delete("api-key") is False


def test_import_and_export_environment_roundtrip(tmp_path):
    source = tmp_path / "fixture.env"
    source.write_text("# ignored\n\nAPI_KEY=\"a=b\"\nSECOND = 'two'\ninvalid\nEMPTY=\n")
    with patch("mcli.lib.secrets.manager.click.prompt", return_value="fixture-password"):
        manager = SecretsManager(tmp_path / "encrypted")
    assert manager.import_env(source, "demo") == 3
    assert manager.get("api-key", "demo") == "a=b"
    assert manager.export_env("demo") == {"API_KEY": "a=b", "SECOND": "two"}
    assert manager.export_env() == {"API_KEY": "a=b", "SECOND": "two"}


def test_git_store_push_pull_preserves_encrypted_bytes_and_backup(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    store = SecretsStore(tmp_path / "store")
    assert store.status()["initialized"] is False
    store.init()
    initial = store.status()
    assert initial["initialized"] is True and initial["clean"] is True
    source = tmp_path / "encrypted"
    source.mkdir()
    (source / "secret").write_bytes(b"opaque-encrypted-fixture")
    store.push(source, "Store fixture")
    repo = Repo(store.store_path)
    assert repo.head.commit.message.strip() == "Store fixture"
    first_commit = repo.head.commit.hexsha
    store.push(source)
    assert repo.head.commit.hexsha == first_commit
    destination = tmp_path / "restored"
    destination.mkdir()
    (destination / "old").write_text("previous backup")
    store.pull(destination)
    assert (destination / "secret").read_bytes() == b"opaque-encrypted-fixture"
    assert (tmp_path / "restored.backup" / "old").read_text() == "previous backup"
    store.pull(destination)
    assert (tmp_path / "restored.backup" / "secret").read_bytes() == b"opaque-encrypted-fixture"
    store.init()
    assert repo.head.commit.hexsha == first_commit
    store.store_config = {
        "store_path": str(tmp_path / "alternate"),
        "remote_url": "https://invalid.test/repo",
    }
    store.save_config()
    assert SecretsStore().store_path == tmp_path / "alternate"


def test_uninitialized_git_store_is_non_destructive(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    store = SecretsStore(tmp_path / "missing")
    source = tmp_path / "encrypted"
    source.mkdir()
    (source / "preserved").write_text("fixture")
    store.push(source)
    store.pull(source)
    store.sync(source)
    assert (source / "preserved").read_text() == "fixture"
    assert not store.store_path.exists()
