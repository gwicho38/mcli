"""Regression tests for the hosted security workflow."""

from pathlib import Path


def test_safety_runner_upgrades_setuptools_before_scanning():
    workflow = Path(".github/workflows/security.yml").read_text()

    assert 'pip install --upgrade "setuptools>=83" safety' in workflow
