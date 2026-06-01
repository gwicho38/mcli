"""Unit tests for ci.act_runner."""

import subprocess
from unittest.mock import patch

from mcli.workflow.ci.act_runner import PreflightResult, build_act_command, probe, run_act


def _cp(returncode=0, stdout=""):
    return subprocess.CompletedProcess(
        args=["act"], returncode=returncode, stdout=stdout, stderr=""
    )


class TestProbe:
    def test_probe_false_when_act_missing(self):
        with patch("shutil.which", return_value=None):
            assert probe() is False

    def test_probe_false_when_docker_down(self):
        with (
            patch("shutil.which", return_value="/usr/bin/act"),
            patch("mcli.workflow.ci.act_runner.docker_running", return_value=False),
        ):
            assert probe() is False

    def test_probe_true_when_all_ok(self):
        with (
            patch("shutil.which", return_value="/usr/bin/act"),
            patch("mcli.workflow.ci.act_runner.docker_running", return_value=True),
            patch("subprocess.run", return_value=_cp(0)),
        ):
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

    def test_no_stages_is_pass_not_fail(self):
        """workflow_dispatch-only workflows have no pull_request stages; act
        exits non-zero with 'Could not find any stages to run' — a no-op, not
        a failure, so the gate must not block (#205)."""
        out = "Error: Could not find any stages to run. View the valid jobs with `act --list`."
        with patch("subprocess.run", return_value=_cp(1, stdout=out)):
            assert run_act("pull_request") == PreflightResult.PASS


class TestRunActDockerRateLimit:
    """Docker Hub rate limits are retried, then treated as cannot-validate."""

    _RL = (
        "Error response from daemon: toomanyrequests: You have reached your "
        "unauthenticated pull rate limit. https://www.docker.com/increase-rate-limit"
    )

    def test_rate_limit_exhausted_is_unreachable(self):
        # every attempt hits the rate limit -> UNREACHABLE (not FAIL), so the gate
        # does not block the push.
        with (
            patch("subprocess.run", return_value=_cp(1, stdout=self._RL)) as m,
            patch("time.sleep"),
        ):
            assert run_act("pull_request", retries=2, backoff=(0, 0)) == PreflightResult.UNREACHABLE
        assert m.call_count == 3  # initial + 2 retries

    def test_rate_limit_then_success_on_retry(self):
        seq = [_cp(1, stdout=self._RL), _cp(0)]
        with patch("subprocess.run", side_effect=seq), patch("time.sleep"):
            assert run_act("pull_request", retries=2, backoff=(0, 0)) == PreflightResult.PASS

    def test_real_failure_is_not_retried(self):
        with (
            patch("subprocess.run", return_value=_cp(1, stdout="3 tests failed")) as m,
            patch("time.sleep"),
        ):
            assert run_act("pull_request") == PreflightResult.FAIL
        assert m.call_count == 1


from mcli.workflow.ci.act_runner import preflight


class TestPreflight:
    def test_act_passes(self):
        with (
            patch("mcli.workflow.ci.act_runner.probe", return_value=True),
            patch("mcli.workflow.ci.act_runner.run_act", return_value=PreflightResult.PASS),
        ):
            assert preflight("o/r") == PreflightResult.PASS

    def test_act_fails_blocks(self):
        with (
            patch("mcli.workflow.ci.act_runner.probe", return_value=True),
            patch("mcli.workflow.ci.act_runner.run_act", return_value=PreflightResult.FAIL),
        ):
            assert preflight("o/r") == PreflightResult.FAIL

    def test_unreachable_with_runner_is_unreachable(self):
        # Fallback to runner is handled by the CLI layer; preflight reports UNREACHABLE.
        with patch("mcli.workflow.ci.act_runner.probe", return_value=False):
            assert preflight("o/r") == PreflightResult.UNREACHABLE
