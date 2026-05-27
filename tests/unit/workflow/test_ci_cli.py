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
