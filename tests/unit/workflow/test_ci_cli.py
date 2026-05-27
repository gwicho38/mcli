"""CliRunner tests for the `mcli ci` group."""
from unittest.mock import patch

from click.testing import CliRunner

from mcli.workflow.ci.ci import ci

HOSTED_WF = """\
name: ci
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""


class TestMigrate:
    def test_migrate_strips_triggers_and_adds_fallback(self, tmp_path, monkeypatch):
        wfdir = tmp_path / ".github" / "workflows"
        wfdir.mkdir(parents=True)
        (wfdir / "ci.yml").write_text(HOSTED_WF)
        monkeypatch.chdir(tmp_path)
        with patch("mcli.workflow.ci.ci.has_online_runner", return_value=False), \
             patch("mcli.workflow.ci.ci.detect_test_command", return_value="make test"):
            res = CliRunner().invoke(ci, ["migrate"])
        assert res.exit_code == 0, res.output
        out = (wfdir / "ci.yml").read_text()
        assert "push:" not in out and "pull_request:" not in out
        assert (wfdir / "self-hosted-ci.yml").exists()
        # no runner -> fallback has no pull_request trigger
        assert "pull_request:" not in (wfdir / "self-hosted-ci.yml").read_text()

    def test_migrate_dry_run_makes_no_changes(self, tmp_path, monkeypatch):
        wfdir = tmp_path / ".github" / "workflows"
        wfdir.mkdir(parents=True)
        (wfdir / "ci.yml").write_text(HOSTED_WF)
        monkeypatch.chdir(tmp_path)
        with patch("mcli.workflow.ci.ci.has_online_runner", return_value=False), \
             patch("mcli.workflow.ci.ci.detect_test_command", return_value="make test"):
            res = CliRunner().invoke(ci, ["migrate", "--dry-run"])
        assert res.exit_code == 0
        assert (wfdir / "ci.yml").read_text() == HOSTED_WF  # unchanged
        assert not (wfdir / "self-hosted-ci.yml").exists()


from mcli.workflow.ci.act_runner import PreflightResult


class TestPreflightCommand:
    def _run(self, result, has_runner):
        with patch("mcli.workflow.ci.ci.current_repo_slug", return_value="o/r"), \
             patch("mcli.workflow.ci.ci.preflight_fn", return_value=result), \
             patch("mcli.workflow.ci.ci.has_online_runner", return_value=has_runner):
            return CliRunner().invoke(ci, ["preflight"])

    def test_pass_exit_0(self):
        assert self._run(PreflightResult.PASS, False).exit_code == 0

    def test_fail_exit_1(self):
        assert self._run(PreflightResult.FAIL, False).exit_code == 1

    def test_unreachable_no_runner_exit_2(self):
        res = self._run(PreflightResult.UNREACHABLE, False)
        assert res.exit_code == 2
        assert "cannot validate" in res.output.lower()

    def test_unreachable_with_runner_exit_3(self):
        res = self._run(PreflightResult.UNREACHABLE, True)
        assert res.exit_code == 3  # signals: push and let runner validate
        assert "runner" in res.output.lower()
