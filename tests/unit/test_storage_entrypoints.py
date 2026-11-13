"""CLI contracts at the secrets and storage backend boundaries."""

import asyncio
import importlib
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from click.testing import CliRunner


@pytest.fixture
def storage_command(monkeypatch):
    module = importlib.import_module("mcli.workflow.storage.storage_cmd")
    storage = importlib.import_module("mcli.storage")
    backend = Mock()
    for name in (
        "connect",
        "login",
        "setup",
        "store",
        "retrieve",
        "list_all",
        "list_recent_uploads",
        "get_metadata",
        "delete",
    ):
        setattr(backend, name, AsyncMock())
    backend.get_status.return_value = {
        "enabled": True,
        "connected": True,
        "cli": {"agent_did": "a" * 50, "space_did": "s" * 50},
        "cache": {"total_files": 2},
    }
    backend.cache.get_stats.return_value = {
        "total_files": 2,
        "total_size_mb": 1,
        "types": {"text": 2},
    }
    backend.cache.cleanup = AsyncMock(return_value=2)
    monkeypatch.setattr(storage, "get_storage_backend", lambda: backend)
    monkeypatch.setattr(module, "run_async", asyncio.run)
    return module, backend, CliRunner()


def test_storage_upload_download_roundtrip_contract(storage_command, tmp_path):
    module, backend, runner = storage_command
    source = tmp_path / "input.bin"
    source.write_bytes(b"payload\x00")
    backend.store.return_value = "bafy-test"
    uploaded = runner.invoke(
        module.storage, ["upload", str(source), "--metadata", "tag=a=b", "--metadata", "invalid"]
    )
    assert uploaded.exit_code == 0, uploaded.output
    backend.store.assert_awaited_once_with("input.bin", b"payload\x00", {"tag": "a=b"})
    assert "bafy-test" in uploaded.output
    backend.retrieve.return_value = b"payload\x00"
    destination = tmp_path / "output.bin"
    downloaded = runner.invoke(
        module.storage, ["download", "bafy-test", "--output", str(destination)]
    )
    assert downloaded.exit_code == 0 and destination.read_bytes() == source.read_bytes()
    assert runner.invoke(module.storage, ["download", "bafy-test"]).exit_code == 0
    backend.retrieve.return_value = None
    assert runner.invoke(module.storage, ["download", "missing"]).exit_code == 1


@pytest.mark.parametrize(
    "args,fragment",
    [
        (["status"], "Storage Status"),
        (["status", "--json"], '"enabled": true'),
        (["login", "driver@example.invalid"], "Login successful"),
        (["setup", "--email", "driver@example.invalid"], "Setup complete"),
        (["enable"], "enabled"),
        (["disable"], "disabled"),
        (["cache"], "Cache: 2 files"),
        (["cache", "--stats"], "By Type"),
        (["cache", "--cleanup", "--max-age", "7"], "Cleaned up 2"),
        (["delete", "cid", "--yes"], "Deleted"),
    ],
)
def test_storage_commands_report_backend_outcomes(storage_command, args, fragment):
    module, backend, runner = storage_command
    result = runner.invoke(module.storage, args)
    assert result.exit_code == 0, result.output
    assert fragment in result.output
    if args[0] == "login":
        backend.login.assert_awaited_once_with("driver@example.invalid")
    if args[0] == "delete":
        backend.delete.assert_awaited_once_with("cid")
    if "--cleanup" in args:
        backend.cache.cleanup.assert_awaited_once_with(max_age_days=7)


def test_storage_list_handles_metadata_and_empty_backend(storage_command):
    module, backend, runner = storage_command
    backend.list_all.return_value = ["cid-a", "cid-b"]
    backend.get_metadata.side_effect = [{"size": 20, "cached_at": "2026-11-13"}, None]
    result = runner.invoke(module.storage, ["list", "--limit", "2", "--prefix", "cid"])
    assert result.exit_code == 0 and "Total: 2 files" in result.output
    backend.list_all.assert_awaited_once_with(prefix="cid", limit=2)
    backend.list_recent_uploads.return_value = []
    result = runner.invoke(module.storage, ["list", "--remote"])
    assert "No files found" in result.output
    backend.list_recent_uploads.assert_awaited_once_with(limit=20)


@pytest.mark.parametrize(
    "args",
    [["status"], ["login", "a@example.invalid"], ["setup"], ["list"], ["delete", "cid", "--yes"]],
)
def test_storage_network_failures_abort_instead_of_success(storage_command, args):
    module, backend, runner = storage_command
    backend.connect.side_effect = OSError("offline")
    backend.login.side_effect = OSError("offline")
    backend.setup.side_effect = OSError("offline")
    result = runner.invoke(module.storage, args)
    assert result.exit_code == 1 and "offline" in result.output


def test_space_selection_and_token_metadata_do_not_print_secret(monkeypatch):
    module = importlib.import_module("mcli.workflow.storage.storage_cmd")
    cli_module = importlib.import_module("mcli.storage.storacha_cli")
    cli = Mock()
    cli.list_spaces.return_value = ["did:a", "did:b"]
    cli.get_current_space.return_value = "did:a"
    cli.create_space.return_value = "did:new"
    cli.select_space.return_value = True
    tokens = SimpleNamespace(
        agent_did="did:agent",
        space_did="did:space",
        expires_at=datetime(2027, 1, 1),
        capabilities=["store/add"],
        secret="never-print-this",
    )
    cli.get_bridge_tokens.return_value = tokens
    cli.generate_bridge_tokens.return_value = tokens
    monkeypatch.setattr(cli_module, "StorachaCLI", lambda: cli)
    runner = CliRunner()
    cases = [
        (["space", "list"], "* did:a"),
        (["space", "create", "--name", "Test"], "did:new"),
        (["space", "use", "did:b"], "Selected"),
        (["tokens"], "store/add"),
        (["tokens", "--refresh", "--expiration", "3"], "2027"),
    ]
    for args, expected in cases:
        result = runner.invoke(module.storage, args)
        assert result.exit_code == 0 and expected in result.output
        assert "never-print-this" not in result.output
    cli.generate_bridge_tokens.assert_called_once_with(expiration_hours=3)
    cli.list_spaces.return_value = []
    assert "No spaces" in runner.invoke(module.storage, ["space", "list"]).output
    cli.get_bridge_tokens.return_value = None
    assert "No tokens available" in runner.invoke(module.storage, ["tokens"]).output


def test_secret_cli_masks_values_and_delegates_export_to_temp_file(monkeypatch, tmp_path):
    module = importlib.import_module("mcli.workflow.secrets.secrets_cmd")
    manager, store = Mock(), Mock()
    monkeypatch.setattr(module, "SecretsManager", lambda: manager)
    monkeypatch.setattr(module, "SecretsStore", lambda: store)
    runner = CliRunner()
    result = runner.invoke(module.secrets, ["--set", "KEY", "abcdefghi", "--namespace", "test"])
    assert result.exit_code == 0
    manager.set.assert_called_once_with("KEY", "abcdefghi", "test")
    manager.get.return_value = "abcdefghi"
    result = runner.invoke(module.secrets, ["--get", "KEY"])
    assert "abc***ghi" in result.output and "abcdefghi" not in result.output
    assert "abcdefghi" in runner.invoke(module.secrets, ["--get", "KEY", "--show"]).output
    manager.get.return_value = "tiny"
    assert "****" in runner.invoke(module.secrets, ["--get", "KEY"]).output
    manager.get.return_value = None
    assert "not found" in runner.invoke(module.secrets, ["--get", "KEY"]).output
    manager.list.return_value = ["KEY"]
    assert "KEY" in runner.invoke(module.secrets, ["--list"]).output
    manager.delete.return_value = True
    assert "deleted" in runner.invoke(module.secrets, ["--delete", "KEY"], input="y\n").output
    manager.export_env.return_value = {"TEST_ONLY": "value"}
    destination = tmp_path / "exports.sh"
    assert runner.invoke(module.secrets, ["--export", "--output", str(destination)]).exit_code == 0
    assert destination.read_text() == "export TEST_ONLY=value\n"
    assert "TEST_ONLY=value" in runner.invoke(module.secrets, ["--export"]).output
    imported = tmp_path / "imports.env"
    imported.write_text("TEST_ONLY=value\n")
    manager.import_env.return_value = 1
    assert "Imported 1" in runner.invoke(module.secrets, ["--import-file", str(imported)]).output
    store.status.return_value = {
        "initialized": True,
        "store_path": str(tmp_path),
        "branch": "main",
        "commit": "abc",
        "clean": True,
        "has_remote": False,
    }
    for args in (
        ["--store-init"],
        ["--store-push"],
        ["--store-pull"],
        ["--store-sync"],
        ["--store-status"],
        [],
    ):
        result = runner.invoke(module.secrets, args)
        assert result.exit_code == 0, result.output


def test_legacy_script_json_sync_preserves_manual_files_and_detects_content_changes(tmp_path):
    from mcli.lib.script_sync import ScriptSyncManager

    folder = tmp_path / "tools"
    folder.mkdir()
    source = folder / "backup.sh"
    source.write_text(
        "#!/usr/bin/env bash\n# @description: Save data\n# @tags: backup, local\n# @shell: bash\necho test\n"
    )
    manager = ScriptSyncManager(tmp_path)
    generated = manager.generate_json(source)
    data = json.loads(generated.read_text())
    assert data["group"] == "tools" and data["shell"] == "bash"
    assert data["metadata"]["tags"] == ["backup", "local"]
    assert data["code"] == source.read_text()
    assert manager.needs_sync(source, generated) is False
    assert manager.generate_json(source) == generated
    source.write_text(source.read_text() + "echo changed\n")
    assert manager.needs_sync(source, generated)
    assert manager.sync_all() == [generated]
    manual = tmp_path / "manual.json"
    manual.write_text('{"code":"manual"}')
    source.unlink()
    assert manager.cleanup_orphaned_json() == [generated]
    assert manual.exists() and manager.sync_cache_path.exists()
    manager.sync_cache_path.write_text("broken json")
    assert ScriptSyncManager(tmp_path).sync_cache == {}


@pytest.mark.parametrize(
    "filename,content,language",
    [
        ("run.txt", "#!/usr/bin/env python3\n", "python"),
        ("run.js", "// test\n", "javascript"),
        ("run.unknown", "test", "unknown"),
    ],
)
def test_script_language_uses_shebang_before_extension(tmp_path, filename, content, language):
    from mcli.lib.script_sync import ScriptSyncManager

    source = tmp_path / filename
    source.write_text(content)
    assert ScriptSyncManager(tmp_path).detect_language(source) == language


def test_script_sync_validates_notebooks_and_missing_sources(tmp_path):
    from mcli.lib.script_sync import ScriptSyncManager

    manager = ScriptSyncManager(tmp_path)
    notebook = tmp_path / "valid.ipynb"
    notebook.write_text('{"nbformat":4,"cells":[]}')
    assert manager.generate_json(notebook) == notebook
    notebook.write_text("{}")
    assert manager.generate_json(notebook) is None
    notebook.write_text("broken")
    assert manager.generate_json(notebook) is None
    assert manager.calculate_hash(tmp_path / "absent") == ""
    assert ScriptSyncManager(tmp_path / "absent").sync_all() == []
