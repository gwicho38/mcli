"""Exercise the selected coverage configuration through its command-line gate."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.parametrize("exercise_branch, expected_status", [(False, 2), (True, 0)])
def test_selected_configuration_enforces_branch_coverage(
    tmp_path, exercise_branch, expected_status
):
    root = Path(__file__).resolve().parents[2]
    source = tmp_path / "sample"
    source.mkdir()
    module = source / "example.py"
    module.write_text(
        "def choose(enabled):\n"
        "    if enabled:\n"
        "        first = 1\n"
        "        second = 2\n"
        "        third = 3\n"
        "        fourth = 4\n"
        "        return first + second + third + fourth\n"
        "    return 0\n"
        "choose(False)\n" + ("choose(True)\n" if exercise_branch else "")
    )
    environment = {**os.environ, "COVERAGE_FILE": str(tmp_path / ".coverage")}
    measured = subprocess.run(
        [sys.executable, "-m", "coverage", "run", "--source", str(source), str(module)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert measured.returncode == 0, measured.stderr
    reported = subprocess.run(
        [sys.executable, "-m", "coverage", "report"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert reported.returncode == expected_status, reported.stdout + reported.stderr
    assert "Branch" in reported.stdout
    if not exercise_branch:
        assert "fail-under=50" in reported.stdout


def test_unimported_namespace_modules_are_counted(tmp_path):
    """A never-imported namespace module must still lower the package result."""
    root = Path(__file__).resolve().parents[2]
    source = tmp_path / "sample"
    namespace = source / "namespace"
    namespace.mkdir(parents=True)
    (source / "__init__.py").write_text("")
    (namespace / "untouched.py").write_text("def untouched():\n    return 42\n")
    exercised = source / "exercised.py"
    exercised.write_text("value = 1\n")
    environment = {**os.environ, "COVERAGE_FILE": str(tmp_path / ".coverage")}
    measured = subprocess.run(
        [sys.executable, "-m", "coverage", "run", "--source", str(source), str(exercised)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert measured.returncode == 0, measured.stderr
    report = tmp_path / "coverage.json"
    subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", str(report)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
    )
    files = json.loads(report.read_text())["files"]
    untouched = next(
        (data for name, data in files.items() if name.endswith("namespace/untouched.py")), None
    )
    assert untouched is not None, "namespace source was silently excluded from coverage"
    assert untouched["summary"]["num_statements"] == 2
    assert untouched["summary"]["covered_lines"] == 0
