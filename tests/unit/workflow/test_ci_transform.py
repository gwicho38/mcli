"""Unit tests for ci.workflow_transform."""
import pytest
from mcli.workflow.ci.workflow_transform import runs_on_is_hosted, is_hosted_label


class TestRunsOnClassification:
    @pytest.mark.parametrize("label,expected", [
        ("ubuntu-latest", True), ("ubuntu-22.04", True),
        ("macos-14", True), ("windows-latest", True),
        ("self-hosted", False),
    ])
    def test_is_hosted_label(self, label, expected):
        assert is_hosted_label(label) is expected

    def test_string_hosted(self):
        assert runs_on_is_hosted("ubuntu-latest") is True

    def test_string_self_hosted(self):
        assert runs_on_is_hosted("self-hosted") is False

    def test_list_with_self_hosted_is_not_hosted(self):
        assert runs_on_is_hosted(["self-hosted", "Linux", "X64"]) is False

    def test_list_hosted(self):
        assert runs_on_is_hosted(["ubuntu-latest"]) is True

    def test_matrix_expression_is_conservatively_hosted(self):
        # Unknown expansion -> assume hosted so we err toward stopping cost.
        assert runs_on_is_hosted("${{ matrix.os }}") is True

    def test_expression_referencing_self_hosted_is_not_hosted(self):
        assert runs_on_is_hosted("${{ inputs.x }}-self-hosted") is False

    def test_none(self):
        assert runs_on_is_hosted(None) is False


from mcli.workflow.ci.workflow_transform import (
    workflow_has_hosted_job, transform_file, MARKER,
)

HOSTED_WF = """\
name: ci
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""

SELFHOSTED_WF = """\
name: ci
on:
  pull_request:
jobs:
  test:
    runs-on: [self-hosted, Linux, X64]
    steps:
      - run: echo hi
"""


class TestStripTriggers:
    def _load(self, text):
        from ruamel.yaml import YAML
        y = YAML()
        y.version = (1, 2)  # keep 'on' a string key, not boolean True
        return y.load(text)

    def test_detects_hosted_job(self):
        assert workflow_has_hosted_job(self._load(HOSTED_WF)) is True

    def test_detects_self_hosted_only(self):
        assert workflow_has_hosted_job(self._load(SELFHOSTED_WF)) is False

    def test_transform_strips_push_and_pr(self, tmp_path):
        wf = tmp_path / "ci.yml"
        wf.write_text(HOSTED_WF)
        changed = transform_file(wf)
        out = wf.read_text()
        assert changed is True
        assert MARKER in out
        assert "push:" not in out
        assert "pull_request:" not in out
        assert "workflow_dispatch:" in out
        # 'on:' must survive as a string key, not become 'true:'
        assert "\non:" in out
        assert "\ntrue:" not in out

    def test_transform_idempotent(self, tmp_path):
        wf = tmp_path / "ci.yml"
        wf.write_text(HOSTED_WF)
        transform_file(wf)
        first = wf.read_text()
        changed_again = transform_file(wf)
        assert changed_again is False
        assert wf.read_text() == first

    def test_transform_skips_self_hosted_only(self, tmp_path):
        wf = tmp_path / "ci.yml"
        wf.write_text(SELFHOSTED_WF)
        assert transform_file(wf) is False
        assert "pull_request:" in wf.read_text()  # untouched
