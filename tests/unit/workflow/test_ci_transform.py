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
