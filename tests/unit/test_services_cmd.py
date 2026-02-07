"""Tests for the services CLI command group."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mcli.app.services_cmd import services
from mcli.lib.services.state import ServiceState


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def svc_dirs(tmp_path, monkeypatch):
    """Override service directories to temp locations."""
    pids = tmp_path / "pids"
    pids.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()
    state = tmp_path / "state"
    state.mkdir()

    monkeypatch.setattr("mcli.lib.services.manager.get_services_pids_dir", lambda: pids)
    monkeypatch.setattr("mcli.lib.services.manager.get_services_logs_dir", lambda: logs)
    monkeypatch.setattr("mcli.lib.services.state.get_services_state_dir", lambda: state)

    return {"pids": pids, "logs": logs, "state": state}


class TestServicesList:
    def test_list_empty(self, runner, svc_dirs):
        result = runner.invoke(services, ["list"])
        assert result.exit_code == 0
        assert "No services" in result.output

    def test_list_with_services(self, runner, svc_dirs):
        from mcli.lib.services.state import save_state

        save_state(ServiceState(name="web", status="running", pid=100, config={"port": 8080}))
        save_state(ServiceState(name="worker", status="stopped"))

        result = runner.invoke(services, ["list"])
        assert result.exit_code == 0
        assert "web" in result.output
        assert "worker" in result.output


class TestServicesStart:
    @patch("mcli.app.services_cmd.manager")
    def test_start_with_command(self, mock_mgr, runner, svc_dirs):
        mock_mgr.start_service.return_value = 42

        result = runner.invoke(services, ["start", "my-svc", "-c", "echo hello"])
        assert result.exit_code == 0
        assert "42" in result.output
        mock_mgr.start_service.assert_called_once()

    @patch("mcli.app.services_cmd.manager")
    def test_start_no_command(self, mock_mgr, runner, svc_dirs):
        result = runner.invoke(services, ["start", "my-svc"])
        assert result.exit_code != 0

    @patch("mcli.app.services_cmd.manager")
    def test_start_already_running(self, mock_mgr, runner, svc_dirs):
        from mcli.lib.services.state import save_state

        save_state(ServiceState(name="running", status="running", pid=100))

        with patch("mcli.app.services_cmd.load_state") as mock_load:
            mock_state = ServiceState(name="running", status="running", pid=100)
            mock_load.return_value = mock_state

            with patch("mcli.lib.services.health.check_pid_alive", return_value=True):
                result = runner.invoke(services, ["start", "running", "-c", "echo hi"])
                assert "already running" in result.output


class TestServicesStop:
    @patch("mcli.app.services_cmd.manager")
    @patch("mcli.app.services_cmd.load_state")
    def test_stop_running(self, mock_load, mock_mgr, runner, svc_dirs):
        mock_load.return_value = ServiceState(name="svc", status="running", pid=42)
        mock_mgr.stop_service.return_value = True

        result = runner.invoke(services, ["stop", "svc"])
        assert result.exit_code == 0
        assert "stopped" in result.output

    @patch("mcli.app.services_cmd.load_state")
    def test_stop_not_found(self, mock_load, runner, svc_dirs):
        mock_load.return_value = None

        result = runner.invoke(services, ["stop", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestServicesStatus:
    @patch("mcli.app.services_cmd.manager")
    def test_status_running(self, mock_mgr, runner, svc_dirs):
        mock_mgr.get_service_status.return_value = {
            "name": "web",
            "status": "running",
            "pid": 42,
            "started_at": "2026-01-01T00:00:00",
            "stopped_at": None,
            "restart_count": 0,
            "health_status": None,
            "config": {"port": 8080, "service_type": "http"},
        }

        result = runner.invoke(services, ["status", "web"])
        assert result.exit_code == 0
        assert "web" in result.output

    @patch("mcli.app.services_cmd.manager")
    def test_status_not_found(self, mock_mgr, runner, svc_dirs):
        mock_mgr.get_service_status.return_value = {"name": "x", "status": "unknown"}

        result = runner.invoke(services, ["status", "x"])
        assert result.exit_code != 0


class TestServicesCleanup:
    @patch("mcli.app.services_cmd.manager")
    def test_cleanup_with_stale(self, mock_mgr, runner, svc_dirs):
        mock_mgr.cleanup_stale.return_value = 3

        result = runner.invoke(services, ["cleanup"])
        assert result.exit_code == 0
        assert "3" in result.output

    @patch("mcli.app.services_cmd.manager")
    def test_cleanup_none(self, mock_mgr, runner, svc_dirs):
        mock_mgr.cleanup_stale.return_value = 0

        result = runner.invoke(services, ["cleanup"])
        assert result.exit_code == 0
        assert "No stale" in result.output


class TestServicesLogs:
    @patch("mcli.app.services_cmd.manager")
    @patch("mcli.app.services_cmd.load_state")
    def test_logs_stdout(self, mock_load, mock_mgr, runner, svc_dirs):
        mock_load.return_value = ServiceState(name="svc", status="running", pid=1)
        mock_mgr.get_logs.return_value = {"stdout": "hello world\n", "stderr": ""}

        result = runner.invoke(services, ["logs", "svc"])
        assert result.exit_code == 0
        assert "hello world" in result.output

    @patch("mcli.app.services_cmd.load_state")
    def test_logs_not_found(self, mock_load, runner, svc_dirs):
        mock_load.return_value = None

        result = runner.invoke(services, ["logs", "nope"])
        assert result.exit_code != 0
