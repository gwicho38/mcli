"""Run the actual Make entrypoints against a recording UV command."""

import json
import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
from ruamel.yaml import YAML


def test_configured_black_hook_matches_frozen_project_formatter():
    root = Path(__file__).resolve().parents[2]
    configuration = YAML(typ="safe").load((root / ".pre-commit-config.yaml").read_text())
    black = next(
        repo for repo in configuration["repos"] if repo["repo"] == "https://github.com/psf/black"
    )
    assert black["rev"] == version("black")


@pytest.mark.parametrize(
    "target,arguments",
    [
        ("pre-commit-install", ["install"]),
        ("pre-commit-run", ["run", "--all-files"]),
        ("pre-commit-update", ["autoupdate"]),
        ("security-check", []),
    ],
)
def test_precommit_uses_secure_isolated_interpreter(tmp_path, target, arguments):
    root = Path(__file__).resolve().parents[2]
    record = tmp_path / "arguments.json"
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['FAKE_UV_LOG']).write_text(json.dumps(sys.argv[1:]))\n"
    )
    fake_uv.chmod(0o755)
    result = subprocess.run(
        ["make", "--no-print-directory", "-o", "setup", target, f"UV={fake_uv}"],
        cwd=root,
        env={**os.environ, "FAKE_UV_LOG": str(record)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    called = json.loads(record.read_text())
    assert called[:4] == ["tool", "run", "--python", "3.11"]
    if target == "security-check":
        assert called[4:7] == ["--from", "pip-audit>=2.9.0", "pip-audit"]
        assert "--requirement" in called
    else:
        assert "filelock>=4.2.1,<5" in called
        assert "virtualenv>=21.14.9,<22" in called
        assert called[-len(arguments) - 1 :] == ["pre-commit", *arguments]


def test_security_check_propagates_dependency_audit_failure(tmp_path):
    root = Path(__file__).resolve().parents[2]
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "if 'pip-audit' in sys.argv:\n"
        "    print('vulnerable fixture rejected', flush=True)\n"
        "    sys.exit(7)\n"
    )
    fake_uv.chmod(0o755)
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-o",
            "setup",
            "security-check",
            f"UV={fake_uv}",
            f"SECURITY_REQUIREMENTS={tmp_path / 'requirements.txt'}",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "vulnerable fixture rejected" in result.stdout
