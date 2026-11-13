"""Daemon HTTP contracts, retry boundaries and local config precedence."""

from unittest.mock import Mock, patch

import pytest
import requests

from mcli.lib.api.daemon_client import APIDaemonClient, DaemonClientConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def daemon():
    client = APIDaemonClient(DaemonClientConfig(host="daemon.test", port=8765, retry_delay=0))
    client.session.close()
    client.session = Mock()
    client.session.request.return_value.json.return_value = {"accepted": True}
    return client


@pytest.mark.parametrize(
    "operation,args,method,path,params,payload",
    [
        ("health_check", (), "GET", "/health", None, None),
        ("status", (), "GET", "/status", None, None),
        ("list_commands", (), "GET", "/commands", None, None),
        ("list_commands", (True,), "GET", "/commands", {"all": "true"}, None),
        ("get_command_details", ("backup",), "GET", "/commands/backup", None, None),
        ("start_daemon", (), "POST", "/daemon/start", None, None),
        ("stop_daemon", (), "POST", "/daemon/stop", None, None),
    ],
)
def test_routes_and_payloads(daemon, operation, args, method, path, params, payload):
    assert getattr(daemon, operation)(*args) == {"accepted": True}
    arguments = {"params": params} if method == "GET" else {"json": payload}
    daemon.session.request.assert_called_once_with(
        method=method, url="http://daemon.test:8765" + path, timeout=30, **arguments
    )


def test_execute_validation_and_optional_fields(daemon):
    with pytest.raises(ValueError, match="must be provided"):
        daemon.execute_command()
    daemon.session.request.assert_not_called()
    assert daemon.execute_command(
        command_id="id", command_name="backup", args=["--dry"], timeout=7
    ) == {"accepted": True}
    assert daemon.session.request.call_args.kwargs["json"] == {
        "command_id": "id",
        "command_name": "backup",
        "args": ["--dry"],
        "timeout": 7,
    }


@pytest.mark.parametrize(
    "error",
    [
        requests.ConnectionError("offline"),
        requests.Timeout("slow"),
        requests.HTTPError("unavailable", response=Mock(status_code=503)),
    ],
)
def test_transient_errors_retry_then_succeed(daemon, error):
    good = Mock()
    good.json.return_value = {"running": True}
    daemon.session.request.side_effect = [error, good]
    with patch("mcli.lib.api.daemon_client.time.sleep") as sleep:
        assert daemon.is_running() is True
    assert daemon.session.request.call_count == 2
    sleep.assert_called_once_with(0)


def test_client_error_is_not_retried(daemon):
    daemon.session.request.side_effect = requests.HTTPError(
        "forbidden", response=Mock(status_code=403)
    )
    with patch("mcli.lib.api.daemon_client.time.sleep") as sleep:
        with pytest.raises(Exception, match="API daemon.*forbidden"):
            daemon.status()
    assert daemon.session.request.call_count == 1
    sleep.assert_not_called()
    assert daemon.is_running() is False


def test_transient_failures_exhaust_retry_budget(daemon):
    daemon.session.request.side_effect = requests.Timeout("slow")
    with patch("mcli.lib.api.daemon_client.time.sleep") as sleep:
        with pytest.raises(Exception, match="slow"):
            daemon.status()
    assert daemon.session.request.call_count == 3
    assert sleep.call_count == 2


def test_wait_for_daemon_success_and_deadline(daemon):
    with (
        patch.object(daemon, "is_running", side_effect=[False, True]),
        patch("mcli.lib.api.daemon_client.time.sleep"),
    ):
        assert daemon.wait_for_daemon(1) is True
    with (
        patch("mcli.lib.api.daemon_client.time.time", side_effect=[0, 0, 2]),
        patch.object(daemon, "is_running", return_value=False),
        patch("mcli.lib.api.daemon_client.time.sleep") as sleep,
    ):
        assert daemon.wait_for_daemon(1) is False
        sleep.assert_called_once_with(1)


def test_local_configuration_overrides_user_configuration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path / "home")
    (tmp_path / "config.toml").write_text('[api_daemon]\nhost="local.test"\nport=8009\n')
    user = tmp_path / "home" / ".config" / "mcli"
    user.mkdir(parents=True)
    (user / "config.toml").write_text('[api_daemon]\nhost="user.test"\nport=9001\n')
    client = APIDaemonClient()
    try:
        assert client.base_url == "http://local.test:8009"
    finally:
        client.session.close()


def test_shell_execution_uses_separate_endpoint(daemon):
    daemon.session.post.return_value.json.return_value = {"stdout": "done", "exit_code": 0}
    assert daemon.execute_shell_command("echo done")["stdout"] == "done"
    daemon.session.post.assert_called_once_with(
        "http://localhost:5005/execute", json={"command": "echo done"}, timeout=30
    )
    daemon.session.post.side_effect = requests.ConnectionError("offline")
    with pytest.raises(Exception, match="Flask shell daemon"):
        daemon.execute_shell_command("echo done")
