"""Unit tests for ci.act_runner."""

import subprocess
from unittest.mock import patch

from mcli.workflow.ci.act_runner import (
    PreflightResult,
    build_act_command,
    default_container_arch,
    list_jobs,
    native_gate_available,
    preflight,
    probe,
    run_act,
    run_native,
)


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

    def test_workflow_job_arch_flags(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd = build_act_command(
            "workflow_dispatch",
            workflow=".github/workflows/ci.yml",
            job="primary",
            arch="linux/amd64",
        )
        assert cmd[:2] == ["act", "workflow_dispatch"]
        assert cmd[cmd.index("-W") + 1] == ".github/workflows/ci.yml"
        assert cmd[cmd.index("-j") + 1] == "primary"
        assert cmd[cmd.index("--container-architecture") + 1] == "linux/amd64"


class TestDefaultArch:
    def test_amd64_on_macos_arm(self):
        with (
            patch("mcli.workflow.ci.act_runner.sys.platform", "darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            assert default_container_arch() == "linux/amd64"

    def test_none_on_linux(self):
        with (
            patch("mcli.workflow.ci.act_runner.sys.platform", "linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            assert default_container_arch() is None


class TestRunAct:
    def test_pass(self):
        with patch("subprocess.run", return_value=_cp(0)):
            assert run_act("pull_request") == PreflightResult.PASS

    def test_fail(self):
        with patch("subprocess.run", return_value=_cp(1)):
            assert run_act("pull_request") == PreflightResult.FAIL

    def test_no_stages_without_entrypoint_is_pass(self, tmp_path, monkeypatch):
        """No pull_request stages AND no ci.yml dispatch entrypoint -> genuine
        no-op, so the gate must not block (#205)."""
        monkeypatch.chdir(tmp_path)  # no .github/workflows/ci.yml here
        out = "Error: Could not find any stages to run. View the valid jobs with `act --list`."
        with patch("subprocess.run", return_value=_cp(1, stdout=out)):
            assert run_act("pull_request") == PreflightResult.PASS


# `act --list` table output. The job id lives under the `Job ID` column; it is
# NOT always `primary` — for a typical migrated repo it's whatever the original
# job was called (here, `test`). Preflight must discover it, not assume it.
_ACT_LIST_TEST_JOB = (
    "Stage  Job ID  Job name  Workflow name  Workflow file  Events\n"
    "0      test    test      ci             ci.yml         workflow_dispatch\n"
)
_ACT_LIST_TWO_JOBS = (
    "Stage  Job ID  Job name  Workflow name  Workflow file  Events\n"
    "0      lint    lint      ci             ci.yml         workflow_dispatch\n"
    "0      test    test      ci             ci.yml         workflow_dispatch\n"
)
_ACT_LIST_EMPTY = "Stage  Job ID  Job name  Workflow name  Workflow file  Events\n"


class TestListJobs:
    """`list_jobs` parses real job ids out of the `act --list` table so the
    dispatch fallback never has to guess (`primary` was a wrong guess: defect 1)."""

    def test_parses_single_job_id(self):
        with patch("subprocess.run", return_value=_cp(0, stdout=_ACT_LIST_TEST_JOB)):
            assert list_jobs("workflow_dispatch", ".github/workflows/ci.yml") == ["test"]

    def test_parses_multiple_job_ids(self):
        with patch("subprocess.run", return_value=_cp(0, stdout=_ACT_LIST_TWO_JOBS)):
            assert list_jobs("workflow_dispatch", ".github/workflows/ci.yml") == [
                "lint",
                "test",
            ]

    def test_empty_table_is_no_jobs(self):
        with patch("subprocess.run", return_value=_cp(0, stdout=_ACT_LIST_EMPTY)):
            assert list_jobs("workflow_dispatch", ".github/workflows/ci.yml") == []

    def test_no_stages_output_is_no_jobs(self):
        out = "Error: Could not find any stages to run."
        with patch("subprocess.run", return_value=_cp(1, stdout=out)):
            assert list_jobs("workflow_dispatch", ".github/workflows/ci.yml") == []


class TestDispatchFallback:
    """workflow_dispatch-only repos (migrated by `mcli ci migrate`) have no
    pull_request stages. Rather than hollow-pass, preflight must discover the
    real ci.yml job id(s) via `act --list` and run them via workflow_dispatch so
    it actually validates the gates."""

    _NO_STAGES = "Error: Could not find any stages to run."

    def _with_ci_yml(self, tmp_path, monkeypatch):
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: ci\non:\n  workflow_dispatch:\n")
        monkeypatch.chdir(tmp_path)

    def test_dispatch_uses_discovered_job_not_primary(self, tmp_path, monkeypatch):
        """Defect 1: the dispatch run must target the real job id from
        `act --list` (`test`), never the hardcoded `primary`."""
        self._with_ci_yml(tmp_path, monkeypatch)
        with (
            patch("mcli.workflow.ci.act_runner.list_jobs", return_value=["test"]) as list_m,
            # 1st run: pull_request -> no stages; 2nd run: dispatch -> exit 0.
            patch("subprocess.run", side_effect=[_cp(1, stdout=self._NO_STAGES), _cp(0)]) as run_m,
        ):
            assert run_act("pull_request") == PreflightResult.PASS
        list_m.assert_called_once()
        dispatch_cmd = run_m.call_args_list[1].args[0]
        assert "workflow_dispatch" in dispatch_cmd
        assert "-j" in dispatch_cmd and "test" in dispatch_cmd
        assert "primary" not in dispatch_cmd

    def test_no_stages_then_dispatch_passes(self, tmp_path, monkeypatch):
        self._with_ci_yml(tmp_path, monkeypatch)
        with (
            patch("mcli.workflow.ci.act_runner.list_jobs", return_value=["test"]),
            patch("subprocess.run", side_effect=[_cp(1, stdout=self._NO_STAGES), _cp(0)]),
        ):
            assert run_act("pull_request") == PreflightResult.PASS

    def test_no_stages_then_dispatch_fails(self, tmp_path, monkeypatch):
        self._with_ci_yml(tmp_path, monkeypatch)
        with (
            patch("mcli.workflow.ci.act_runner.list_jobs", return_value=["test"]),
            patch(
                "subprocess.run",
                side_effect=[
                    _cp(1, stdout=self._NO_STAGES),
                    _cp(1, stdout="3 tests failed"),
                ],
            ),
        ):
            assert run_act("pull_request") == PreflightResult.FAIL

    def test_dispatch_no_stages_despite_listed_job_is_fail(self, tmp_path, monkeypatch):
        """Defect 2: if `act --list` shows a job but the dispatch run still says
        'could not find any stages' (e.g. wrong `-j` / act ran nothing), that is a
        FAILURE, not a hollow pass. Green must mean a job actually executed."""
        self._with_ci_yml(tmp_path, monkeypatch)
        with (
            patch("mcli.workflow.ci.act_runner.list_jobs", return_value=["test"]),
            patch(
                "subprocess.run",
                side_effect=[
                    _cp(1, stdout=self._NO_STAGES),
                    _cp(1, stdout=self._NO_STAGES),
                ],
            ),
        ):
            assert run_act("pull_request") == PreflightResult.FAIL

    def test_genuinely_no_jobs_is_pass(self, tmp_path, monkeypatch):
        """If `act --list` shows the dispatch entrypoint has NO jobs at all, it's a
        real no-op and the gate passes without claiming a job ran."""
        self._with_ci_yml(tmp_path, monkeypatch)
        with (
            patch("mcli.workflow.ci.act_runner.list_jobs", return_value=[]),
            patch("subprocess.run", side_effect=[_cp(1, stdout=self._NO_STAGES)]) as run_m,
        ):
            assert run_act("pull_request") == PreflightResult.PASS
        # only the initial pull_request probe ran; no dispatch run attempted.
        assert run_m.call_count == 1


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


class TestNativeGate:
    def test_available_true_on_exit0(self):
        with patch("subprocess.run", return_value=_cp(0)):
            assert native_gate_available() is True

    def test_available_false_when_target_missing(self):
        # `make -n ci-native` exits 2 when the target doesn't exist.
        with patch("subprocess.run", return_value=_cp(2)):
            assert native_gate_available() is False

    def test_available_false_when_make_missing(self):
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            assert native_gate_available() is False

    def test_run_native_pass(self):
        with patch("subprocess.run", return_value=_cp(0)):
            assert run_native() == PreflightResult.PASS

    def test_run_native_fail(self):
        with patch("subprocess.run", return_value=_cp(1)):
            assert run_native() == PreflightResult.FAIL


class TestPreflight:
    def test_prefers_native_gate_over_act(self):
        # When a native `make ci-native` exists, run it and SKIP act entirely.
        with (
            patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=True),
            patch(
                "mcli.workflow.ci.act_runner.run_native",
                return_value=PreflightResult.PASS,
            ),
            patch("mcli.workflow.ci.act_runner.probe") as probe_m,
            patch("mcli.workflow.ci.act_runner.run_act") as act_m,
        ):
            assert preflight("o/r") == PreflightResult.PASS
            probe_m.assert_not_called()
            act_m.assert_not_called()

    def test_native_fail_blocks(self):
        with (
            patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=True),
            patch(
                "mcli.workflow.ci.act_runner.run_native",
                return_value=PreflightResult.FAIL,
            ),
        ):
            assert preflight("o/r") == PreflightResult.FAIL

    def test_falls_back_to_act_without_native_gate(self):
        with (
            patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=False),
            patch("mcli.workflow.ci.act_runner.probe", return_value=True),
            patch("mcli.workflow.ci.act_runner.run_act", return_value=PreflightResult.PASS),
        ):
            assert preflight("o/r") == PreflightResult.PASS

    def test_act_passes(self):
        with (
            patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=False),
            patch("mcli.workflow.ci.act_runner.probe", return_value=True),
            patch("mcli.workflow.ci.act_runner.run_act", return_value=PreflightResult.PASS),
        ):
            assert preflight("o/r") == PreflightResult.PASS

    def test_act_fails_blocks(self):
        with (
            patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=False),
            patch("mcli.workflow.ci.act_runner.probe", return_value=True),
            patch("mcli.workflow.ci.act_runner.run_act", return_value=PreflightResult.FAIL),
        ):
            assert preflight("o/r") == PreflightResult.FAIL

    def test_unreachable_with_runner_is_unreachable(self):
        # Fallback to runner is handled by the CLI layer; preflight reports UNREACHABLE.
        with (
            patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=False),
            patch("mcli.workflow.ci.act_runner.probe", return_value=False),
        ):
            assert preflight("o/r") == PreflightResult.UNREACHABLE
