"""Tests for ServiceManager process lifecycle."""

import os
from unittest.mock import MagicMock, patch

import pytest

from mcli.lib.services.config import ServiceConfig
from mcli.lib.services.manager import ServiceManager
from mcli.lib.services.state import ServiceState, load_state, save_state


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


@pytest.fixture
def mgr(svc_dirs):
    return ServiceManager()


class TestServiceManagerStart:
    @patch("mcli.lib.services.manager.subprocess.Popen")
    @patch("mcli.lib.services.manager.check_pid_alive", return_value=False)
    def test_start_service(self, mock_alive, mock_popen, mgr, svc_dirs):
        mock_process = MagicMock()
        mock_process.pid = 42
        mock_popen.return_value = mock_process

        config = ServiceConfig(name="test-svc", command="echo hello")
        pid = mgr.start_service(config)

        assert pid == 42
        assert (svc_dirs["pids"] / "test-svc.pid").read_text() == "42"

        state = load_state("test-svc")
        assert state is not None
        assert state.status == "running"
        assert state.pid == 42

    @patch("mcli.lib.services.manager.check_pid_alive", return_value=True)
    def test_start_already_running(self, mock_alive, mgr, svc_dirs):
        # Write a PID file simulating a running service
        (svc_dirs["pids"] / "running-svc.pid").write_text("100")

        config = ServiceConfig(name="running-svc", command="echo hi")
        pid = mgr.start_service(config)
        assert pid is None  # Should not start

    def test_start_no_command(self, mgr):
        config = ServiceConfig(name="no-cmd")
        pid = mgr.start_service(config)
        assert pid is None


class TestServiceManagerStop:
    @patch("mcli.lib.services.manager.psutil.Process")
    @patch("mcli.lib.services.manager.os.killpg")
    @patch("mcli.lib.services.manager.os.getpgid", return_value=42)
    @patch("mcli.lib.services.manager.check_pid_alive", return_value=True)
    def test_stop_service(self, mock_alive, mock_getpgid, mock_killpg, mock_proc, mgr, svc_dirs):
        # Setup running state
        (svc_dirs["pids"] / "svc.pid").write_text("42")
        save_state(ServiceState(name="svc", status="running", pid=42))

        mock_proc.return_value.wait.return_value = None

        result = mgr.stop_service("svc")
        assert result is True
        assert not (svc_dirs["pids"] / "svc.pid").exists()

        state = load_state("svc")
        assert state.status == "stopped"
        assert state.pid is None

    @patch("mcli.lib.services.manager.check_pid_alive", return_value=False)
    def test_stop_already_stopped(self, mock_alive, mgr, svc_dirs):
        save_state(ServiceState(name="dead", status="running", pid=99))
        result = mgr.stop_service("dead")
        assert result is True


class TestServiceManagerStatus:
    def test_status_unknown(self, mgr, svc_dirs):
        status = mgr.get_service_status("nonexistent")
        assert status["status"] == "unknown"

    @patch("mcli.lib.services.manager.check_pid_alive", return_value=True)
    def test_status_running(self, mock_alive, mgr, svc_dirs):
        save_state(ServiceState(name="alive", status="running", pid=100))
        status = mgr.get_service_status("alive")
        assert status["status"] == "running"
        assert status["pid"] == 100

    @patch("mcli.lib.services.manager.check_pid_alive", return_value=False)
    def test_status_stale_pid(self, mock_alive, mgr, svc_dirs):
        save_state(ServiceState(name="stale", status="running", pid=9999))
        status = mgr.get_service_status("stale")
        assert status["status"] == "stopped"
        assert status["pid"] is None


class TestServiceManagerLogs:
    def test_get_logs(self, mgr, svc_dirs):
        (svc_dirs["logs"] / "svc.stdout.log").write_text("line1\nline2\nline3\n")
        (svc_dirs["logs"] / "svc.stderr.log").write_text("err1\n")

        logs = mgr.get_logs("svc", lines=2)
        assert "line2" in logs["stdout"]
        assert "line3" in logs["stdout"]
        assert "err1" in logs["stderr"]

    def test_get_logs_missing(self, mgr, svc_dirs):
        logs = mgr.get_logs("nope")
        assert logs["stdout"] == ""
        assert logs["stderr"] == ""


class TestServiceManagerCleanup:
    @patch("mcli.lib.services.manager.check_pid_alive", return_value=False)
    def test_cleanup_stale(self, mock_alive, mgr, svc_dirs):
        save_state(ServiceState(name="dead1", status="running", pid=111))
        save_state(ServiceState(name="dead2", status="running", pid=222))
        save_state(ServiceState(name="stopped", status="stopped"))

        (svc_dirs["pids"] / "dead1.pid").write_text("111")
        (svc_dirs["pids"] / "dead2.pid").write_text("222")

        count = mgr.cleanup_stale()
        assert count == 2

        state1 = load_state("dead1")
        assert state1.status == "stopped"

    def test_cleanup_nothing(self, mgr, svc_dirs):
        count = mgr.cleanup_stale()
        assert count == 0
