"""Transport contracts and event isolation for the LSH integration."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest

from mcli.lib.services.lsh_client import LSHClient

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(
    "operation, args, method, endpoint, payload",
    [
        ("get_status", (), "GET", "/api/status", None),
        ("list_jobs", (), "GET", "/api/jobs", None),
        ("list_jobs", ({"state": "running"},), "GET", "/api/jobs?state=running", None),
        ("get_job", ("42",), "GET", "/api/jobs/42", None),
        ("create_job", ({"name": "backup"},), "POST", "/api/jobs", {"name": "backup"}),
        ("trigger_job", ("42",), "POST", "/api/jobs/42/trigger", None),
        ("start_job", ("42",), "POST", "/api/jobs/42/start", None),
        ("stop_job", ("42",), "POST", "/api/jobs/42/stop", {"signal": "SIGTERM"}),
        ("stop_job", ("42", "SIGINT"), "POST", "/api/jobs/42/stop", {"signal": "SIGINT"}),
        ("remove_job", ("42",), "DELETE", "/api/jobs/42?force=false", None),
        ("remove_job", ("42", True), "DELETE", "/api/jobs/42?force=true", None),
        (
            "bulk_create_jobs",
            ([{"name": "a"}],),
            "POST",
            "/api/jobs/bulk",
            {"jobs": [{"name": "a"}]},
        ),
        ("export_jobs", (), "GET", "/api/export/jobs?format=json", None),
        ("export_jobs", ("csv",), "GET", "/api/export/jobs?format=csv", None),
        ("list_webhooks", (), "GET", "/api/webhooks", None),
        (
            "add_webhook",
            ("https://receiver.test",),
            "POST",
            "/api/webhooks",
            {"endpoint": "https://receiver.test"},
        ),
        (
            "trigger_supabase_sync",
            ("jobs", "INSERT", {"id": 42}),
            "POST",
            "/api/supabase/sync",
            {"table": "jobs", "operation": "INSERT", "data": {"id": 42}},
        ),
    ],
)
async def test_job_operations_send_authenticated_requests(
    operation, args, method, endpoint, payload
):
    client = LSHClient("https://lsh.test", api_key="test-key")
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"accepted": True})
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    client.session = MagicMock()
    client.session.request.return_value = context

    result = await getattr(client, operation)(*args)

    client.session.request.assert_called_once_with(
        method,
        "https://lsh.test" + endpoint,
        headers={"Content-Type": "application/json", "X-API-Key": "test-key"},
        json=payload,
    )
    response.raise_for_status.assert_called_once()
    assert result == (None if operation == "remove_job" else {"accepted": True})


async def test_authentication_failure_does_not_parse_response():
    client = LSHClient("https://lsh.test", api_key="bad-key")
    response = MagicMock(status=401)
    response.json = AsyncMock()
    client.session = MagicMock()
    client.session.request.return_value.__aenter__ = AsyncMock(return_value=response)
    with pytest.raises(ValueError, match="authentication failed"):
        await client.get_status()
    response.json.assert_not_awaited()


async def test_transport_error_is_preserved():
    client = LSHClient("https://lsh.test", api_key="test-key")
    client.session = MagicMock()
    client.session.request.side_effect = aiohttp.ClientConnectionError("offline")
    with pytest.raises(aiohttp.ClientConnectionError, match="offline"):
        await client.get_status()


async def test_context_reuses_session_and_closes_it_on_failure():
    session = MagicMock()
    session.close = AsyncMock()
    with patch(
        "mcli.lib.services.lsh_client.aiohttp.ClientSession", return_value=session
    ) as factory:
        client = LSHClient("https://lsh.test", api_key="test-key", timeout=7)
        with pytest.raises(RuntimeError, match="work failed"):
            async with client as active:
                assert active is client
                await client.connect()
                assert client.session is session
                raise RuntimeError("work failed")
        assert factory.call_count == 1
        assert factory.call_args.kwargs["timeout"].total == 7
        session.close.assert_awaited_once()
        assert client.session is None
        await client.disconnect()
        session.close.assert_awaited_once()


async def test_handler_failure_does_not_block_later_sync_or_async_subscribers():
    client = LSHClient("https://lsh.test", api_key="test-key")
    broken = Mock(side_effect=RuntimeError("subscriber failed"))
    sync = Mock()
    asynchronous = AsyncMock()
    for subscriber in (broken, sync, asynchronous):
        client.on("job:completed", subscriber)
    payload = {"id": "42"}
    await client._emit_event("job:completed", payload)
    broken.assert_called_once_with(payload)
    sync.assert_called_once_with(payload)
    asynchronous.assert_awaited_once_with(payload)
    await client._emit_event("unregistered", payload)
    assert sync.call_count == 1


@pytest.mark.parametrize("status, healthy", [(200, True), (503, False)])
async def test_health_check_reflects_server_status(status, healthy):
    client = LSHClient("https://lsh.test", api_key="test-key")
    client.session = MagicMock()
    client.session.get.return_value.__aenter__ = AsyncMock(return_value=Mock(status=status))
    assert await client.health_check() is healthy
    client.session.get.assert_called_once_with("https://lsh.test/health")


async def test_health_check_handles_disconnection():
    client = LSHClient("https://lsh.test", api_key="test-key")
    client.session = MagicMock()
    client.session.get.side_effect = aiohttp.ClientConnectionError("offline")
    assert await client.health_check() is False
