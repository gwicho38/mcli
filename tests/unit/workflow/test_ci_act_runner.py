"""Unit tests for ci.act_runner."""
import subprocess
from unittest.mock import patch

from mcli.workflow.ci.act_runner import (
    PreflightResult, probe, run_act, build_act_command,
)


def _cp(returncode=0, stdout=""):
    return subprocess.CompletedProcess(args=["act"], returncode=returncode, stdout=stdout, stderr="")


class TestProbe:
    def test_probe_false_when_act_missing(self):
        with patch("shutil.which", return_value=None):
            assert probe() is False

    def test_probe_false_when_docker_down(self):
        with patch("shutil.which", return_value="/usr/bin/act"), \
             patch("mcli.workflow.ci.act_runner.docker_running", return_value=False):
            assert probe() is False

    def test_probe_true_when_all_ok(self):
        with patch("shutil.which", return_value="/usr/bin/act"), \
             patch("mcli.workflow.ci.act_runner.docker_running", return_value=True), \
             patch("subprocess.run", return_value=_cp(0)):
            assert probe() is True


class TestBuildCommand:
    def test_adds_secret_file_when_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".secrets").write_text("X=1\n")
        cmd = build_act_command("pull_request")
        assert cmd[:2] == ["act", "pull_request"]
        assert "--secret-file" in cmd

    def test_no_secret_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd = build_act_command("push")
        assert "--secret-file" not in cmd


class TestRunAct:
    def test_pass(self):
        with patch("subprocess.run", return_value=_cp(0)):
            assert run_act("pull_request") == PreflightResult.PASS

    def test_fail(self):
        with patch("subprocess.run", return_value=_cp(1)):
            assert run_act("pull_request") == PreflightResult.FAIL


from mcli.workflow.ci.act_runner import preflight


class TestPreflight:
    def test_act_passes(self):
        with patch("mcli.workflow.ci.act_runner.probe", return_value=True), \
             patch("mcli.workflow.ci.act_runner.run_act", return_value=PreflightResult.PASS):
            assert preflight("o/r") == PreflightResult.PASS

    def test_act_fails_blocks(self):
        with patch("mcli.workflow.ci.act_runner.probe", return_value=True), \
             patch("mcli.workflow.ci.act_runner.run_act", return_value=PreflightResult.FAIL):
            assert preflight("o/r") == PreflightResult.FAIL

    def test_unreachable_with_runner_is_unreachable(self):
        # Fallback to runner is handled by the CLI layer; preflight reports UNREACHABLE.
        with patch("mcli.workflow.ci.act_runner.probe", return_value=False):
            assert preflight("o/r") == PreflightResult.UNREACHABLE
