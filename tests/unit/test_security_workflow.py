"""Regression tests for the hosted security workflow."""

from pathlib import Path


def test_dependency_audit_uses_frozen_export_without_ignored_advisories():
    workflow = Path(".github/workflows/security.yml").read_text()

    assert "uv export --frozen --extra dev" in workflow
    assert "--no-emit-project" in workflow
    assert "--ignore" not in workflow


def test_dependency_audit_runs_in_isolated_tool_environment():
    workflow = Path(".github/workflows/security.yml").read_text()

    assert "uv tool run --python 3.11" in workflow
    assert "--from 'pip-audit>=2.9.0' pip-audit" in workflow
    assert "--requirement" in workflow
