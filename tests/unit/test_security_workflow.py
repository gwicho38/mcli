"""Regression tests for the hosted security workflow."""

import shlex
from pathlib import Path

from ruamel.yaml import YAML


def test_security_job_audits_installed_runtime_pins_without_suppressing_findings():
    workflow = YAML(typ="safe").load(Path(".github/workflows/security.yml").read_text())
    steps = workflow["jobs"]["safety"]["steps"]
    install = next(s["run"] for s in steps if "uv pip install" in s.get("run", ""))
    assert install.index("uv pip install") < install.index("uv pip freeze")
    assert "--exclude-editable" in install
    exported = shlex.split(install.split("uv pip freeze", 1)[1])[-1]
    audit = next(s["run"] for s in steps if "pip-audit --requirement" in s.get("run", ""))
    arguments = shlex.split(audit)
    assert arguments[arguments.index("--requirement") + 1] == exported
    assert {"--strict", "--no-deps", "--disable-pip"}.issubset(arguments)
    assert "--ignore-vuln" not in arguments
    assert "||" not in arguments
    upload = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    # Select this job's evidence upload; it must survive a failing audit.
    assert upload["if"] == "always()"
    assert exported in upload["with"]["path"]
