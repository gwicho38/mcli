"""Unit tests for ci.runner_status."""

import json
import subprocess
from unittest.mock import patch

from mcli.workflow.ci.runner_status import has_online_runner


def _completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr="")


class TestHasOnlineRunner:
    def test_online_runner_present(self):
        payload = json.dumps({"total_count": 1, "runners": [{"status": "online"}]})
        with patch("subprocess.run", return_value=_completed(payload)):
            assert has_online_runner("gwicho38/mcli") is True

    def test_only_offline_runner(self):
        payload = json.dumps({"total_count": 1, "runners": [{"status": "offline"}]})
        with patch("subprocess.run", return_value=_completed(payload)):
            assert has_online_runner("gwicho38/x") is False

    def test_no_runners(self):
        with patch("subprocess.run", return_value=_completed('{"total_count":0,"runners":[]}')):
            assert has_online_runner("gwicho38/x") is False

    def test_gh_error_returns_false(self):
        with patch("subprocess.run", return_value=_completed("", returncode=1)):
            assert has_online_runner("gwicho38/x") is False

    def test_gh_missing_returns_false(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert has_online_runner("gwicho38/x") is False
