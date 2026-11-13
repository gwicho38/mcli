"""Encrypted cache fallback, remote transport and version discovery contracts."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from mcli.storage.backends.ipfs_backend import StorachaBackend
from mcli.storage.registry import RegistryManager

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
async def backend(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("MCLI_STORACHA_ENABLED", "false")
    backend = StorachaBackend("fixture-only-password")
    await backend.client.aclose()
    backend.client = AsyncMock()
    backend.cli = Mock(config={})
    backend.cli.is_cli_installed.return_value = True
    backend.cli.is_authenticated.return_value = True
    yield backend
    await backend.disconnect()


async def test_cache_only_roundtrip_query_and_deletion(backend):
    assert await backend.connect() is True
    assert backend.is_connected()
    assert await backend.health_check() is True
    cid = await backend.store("backup", b"opaque fixture", {"scope": "test"})
    assert await backend.retrieve(cid) == b"opaque fixture"
    raw = await backend.cache.retrieve(cid)
    assert b"opaque fixture" not in raw
    metadata = await backend.get_metadata(cid)
    assert metadata["encrypted"] is True
    assert (await backend.query({"scope": "test"}))[0]["cid"] == cid
    assert await backend.list_all(limit=1) == [cid]
    assert await backend.delete(cid) is True
    assert await backend.retrieve(cid) is None
    backend.client.get.assert_not_awaited()


@pytest.mark.parametrize(
    "installed,authenticated,tokens",
    [(False, False, None), (True, False, None), (True, True, None), (True, True, Mock())],
)
async def test_connection_keeps_cache_available_without_remote_credentials(
    backend, installed, authenticated, tokens
):
    backend.enabled = True
    backend.cli.is_cli_installed.return_value = installed
    backend.cli.is_authenticated.return_value = authenticated
    backend.cli.get_bridge_tokens.return_value = tokens
    assert await backend.connect() is True
    assert backend.is_connected()
    assert backend._bridge_tokens is (tokens if installed and authenticated else None)


async def test_remote_upload_failure_retains_recoverable_encrypted_cache(backend):
    backend.enabled = True
    backend._upload_to_storacha = AsyncMock(side_effect=RuntimeError("remote offline"))
    cid = await backend.store("backup", b"recoverable", {"scope": "test"})
    assert await backend.retrieve(cid) == b"recoverable"
    backend._upload_to_storacha.assert_awaited_once()
    assert (await backend.get_metadata(cid))["scope"] == "test"


async def test_successful_upload_updates_metadata_and_registry(backend):
    backend.enabled = True
    backend._upload_to_storacha = AsyncMock(return_value="remote-cid")
    backend.registry.upload_registry = AsyncMock()
    assert (
        await backend.store("backup", b"fixture", {"repo_name": "demo", "environment": "test"})
        == "remote-cid"
    )
    backend.registry.upload_registry.assert_awaited_once_with("demo", "test", "remote-cid")
    cached = await backend.list_all()
    assert (await backend.get_metadata(cached[0]))["storacha_cid"] == "remote-cid"
    backend.registry.upload_registry.side_effect = RuntimeError("registry unavailable")
    assert (
        await backend.store("other", b"another", {"repo_name": "demo", "environment": "test"})
        == "remote-cid"
    )


async def test_download_is_cached_then_survives_network_failure(backend):
    from mcli.storage.encryption import encrypt_data

    backend.enabled = True
    encrypted = encrypt_data(b"downloaded fixture", backend.encryption_key)
    response = Mock(content=encrypted)
    backend.client.get.return_value = response
    assert await backend.retrieve("remote-cid") == b"downloaded fixture"
    response.raise_for_status.assert_called_once()
    backend.client.get.side_effect = httpx.ConnectError("offline")
    assert await backend.retrieve("remote-cid") == b"downloaded fixture"
    assert backend.client.get.await_count == 1
    assert await backend.retrieve("missing-cid") is None


async def test_cli_upload_tempfile_is_removed_on_success_and_error(backend):
    observed = []

    def upload(path):
        assert path.read_bytes() == b"fixture payload"
        observed.append(path)
        return "fixture-cid"

    backend.cli.upload_file.side_effect = upload
    assert await backend._upload_to_storacha(b"fixture payload", "backup.bin") == "fixture-cid"
    assert not observed[0].exists()
    backend.cli.upload_file.side_effect = None
    backend.cli.upload_file.return_value = None
    backend.cli.get_bridge_tokens.return_value = None
    with pytest.raises(Exception, match="No valid bridge tokens"):
        await backend._upload_to_storacha(b"fixture payload", "backup.bin")


@pytest.mark.parametrize("status,expected", [(200, True), (503, False)])
async def test_remote_health_response(backend, status, expected):
    backend.enabled = True
    backend.client.get.return_value = Mock(status_code=status)
    assert await backend.health_check() is expected
    backend.client.get.side_effect = httpx.ConnectError("offline")
    assert await backend.health_check() is False


async def test_login_setup_and_enablement(backend):
    backend.cli.is_cli_installed.return_value = False
    assert await backend.login("fixture@example.test") is False
    assert await backend.setup() is False
    backend.cli.is_cli_installed.return_value = True
    backend.cli.is_authenticated.return_value = False
    assert await backend.setup() is False
    backend.cli.login.return_value = False
    assert await backend.setup("fixture@example.test") is False
    backend.cli.login.return_value = True
    backend.cli.list_spaces.return_value = []
    backend.cli.create_space.return_value = None
    assert await backend.setup("fixture@example.test") is False
    backend.cli.create_space.return_value = "space-did"
    backend.cli.generate_bridge_tokens.return_value = Mock()
    assert await backend.setup("fixture@example.test") is True
    backend.cli.is_authenticated.return_value = True
    backend.cli.list_spaces.return_value = ["space-did"]
    backend.cli.get_current_space.return_value = None
    assert await backend.setup() is True
    backend.cli.select_space.assert_called_once_with("space-did")
    assert await backend.login("fixture@example.test") is True
    backend.enable()
    assert backend.enabled and backend.cli.config["enabled"] is True
    backend.disable()
    assert not backend.enabled and backend.cli.config["enabled"] is False
    assert backend.cli._save_config.call_count == 2
    backend.cli.list_uploads.return_value = [{"cid": "first"}, {}, {"cid": "second"}]
    assert await backend.list_recent_uploads(2) == ["first", "second"]
    assert backend.get_status()["enabled"] is False


async def test_registry_upload_and_latest_selection():
    backend = Mock()
    backend._upload_to_storacha = AsyncMock(return_value="registry-cid")
    registry = RegistryManager(backend)
    assert (
        await registry.upload_registry("demo", "test", "data-cid", {"build": "1"}) == "registry-cid"
    )
    data, filename = backend._upload_to_storacha.call_args.args
    encoded = json.loads(data)
    assert encoded["data_cid"] == "data-cid" and encoded["metadata"] == {"build": "1"}
    assert filename == "mcli-registry-demo-test.json"
    backend.list_recent_uploads = AsyncMock(return_value=["old", "large", "bad", "other", "new"])

    def download(cid, timeout):
        assert timeout == 5
        if cid == "large":
            return b"x" * 1025
        if cid == "bad":
            return b"not json"
        return json.dumps(
            {
                "repo_name": "other" if cid == "other" else "demo",
                "environment": "test",
                "data_cid": cid + "-data",
                "timestamp": "2026-11-13T00:00:00" if cid == "new" else "2026-11-12T00:00:00",
            }
        ).encode()

    backend._download_from_storacha = AsyncMock(side_effect=download)
    assert await registry.get_latest_cid("demo", "test") == "new-data"
    assert await registry.check_registry_exists("absent", "test") is False
    listed = await registry.list_registries()
    assert listed["demo/test"]["data_cid"] == "new-data"
    assert listed["demo/test"]["registry_cid"] == "new"
    backend.list_recent_uploads.side_effect = RuntimeError("offline")
    assert await registry.get_latest_cid("demo", "test") is None
    assert await registry.list_registries() == {}
    backend._upload_to_storacha.side_effect = RuntimeError("offline")
    with pytest.raises(RuntimeError, match="offline"):
        await registry.upload_registry("demo", "test", "data")
