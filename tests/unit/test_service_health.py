"""Tests for service health checks."""

from unittest.mock import MagicMock, patch

import pytest

from mcli.lib.services.health import check_callable_health, check_http_health, check_pid_alive


class TestHTTPHealth:
    @patch("mcli.lib.services.health.requests.get")
    def test_healthy_response(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        assert check_http_health("127.0.0.1", 8000, "/health") is True

    @patch("mcli.lib.services.health.requests.get")
    def test_unhealthy_response(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)
        assert check_http_health("127.0.0.1", 8000, "/health") is False

    @patch("mcli.lib.services.health.requests.get")
    def test_connection_error(self, mock_get):
        mock_get.side_effect = ConnectionError("refused")
        assert check_http_health("127.0.0.1", 8000) is False

    @patch("mcli.lib.services.health.requests.get")
    def test_timeout(self, mock_get):
        import requests

        mock_get.side_effect = requests.Timeout("timed out")
        assert check_http_health("127.0.0.1", 8000, timeout=1) is False

    @patch("mcli.lib.services.health.requests.get")
    def test_204_is_healthy(self, mock_get):
        mock_get.return_value = MagicMock(status_code=204)
        assert check_http_health("127.0.0.1", 8000) is True


class TestPIDAlive:
    @patch("mcli.lib.services.health.psutil.pid_exists")
    @patch("mcli.lib.services.health.psutil.Process")
    def test_alive_process(self, mock_process, mock_exists):
        mock_exists.return_value = True
        mock_process.return_value.status.return_value = "running"
        assert check_pid_alive(1234) is True

    @patch("mcli.lib.services.health.psutil.pid_exists")
    def test_dead_process(self, mock_exists):
        mock_exists.return_value = False
        assert check_pid_alive(9999) is False

    def test_none_pid(self):
        assert check_pid_alive(None) is False

    @patch("mcli.lib.services.health.psutil.pid_exists")
    @patch("mcli.lib.services.health.psutil.Process")
    def test_zombie_process(self, mock_process, mock_exists):
        mock_exists.return_value = True
        mock_process.return_value.status.return_value = "zombie"
        assert check_pid_alive(1234) is False

    @patch("mcli.lib.services.health.psutil.pid_exists")
    @patch("mcli.lib.services.health.psutil.Process")
    def test_access_denied(self, mock_process, mock_exists):
        import psutil

        mock_exists.return_value = True
        mock_process.side_effect = psutil.AccessDenied(1234)
        assert check_pid_alive(1234) is False


class TestCallableHealth:
    @patch("mcli.lib.services.health.importlib.import_module")
    def test_healthy_callable(self, mock_import):
        mock_module = MagicMock()
        mock_module.check.return_value = True
        mock_import.return_value = mock_module
        assert check_callable_health("mymod.check") is True

    @patch("mcli.lib.services.health.importlib.import_module")
    def test_unhealthy_callable(self, mock_import):
        mock_module = MagicMock()
        mock_module.check.return_value = False
        mock_import.return_value = mock_module
        assert check_callable_health("mymod.check") is False

    def test_invalid_callable(self):
        assert check_callable_health("nonexistent.module.func") is False
