"""Run the actual publisher snippets against failing check executables."""

import os
import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML


@pytest.mark.parametrize(
    ("job", "name"),
    [("test", "Run linting"), ("test", "Run tests"), ("build", "Test basic functionality")],
)
def test_release_checks_propagate_failure(tmp_path, job, name):
    workflow = YAML(typ="safe").load(Path(".github/workflows/publish.yml").read_text())
    script = next(
        step["run"] for step in workflow["jobs"][job]["steps"] if step.get("name") == name
    )
    executable_dir = tmp_path / "bin"
    executable_dir.mkdir()
    for command in ["black", "isort", "pytest", "mcli", "python"]:
        executable = executable_dir / command
        executable.write_text("#!/bin/sh\nexit " + ("0" if command == "python" else "23") + "\n")
        executable.chmod(0o700)
    activation = tmp_path / ".venv" / "bin" / "activate"
    activation.parent.mkdir(parents=True)
    activation.write_text("")
    result = subprocess.run(
        ["/bin/bash", "-e", "-c", script],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(executable_dir) + os.pathsep + os.defpath},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 23, result.stdout + result.stderr
