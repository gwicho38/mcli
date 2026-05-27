"""Transform GitHub Actions workflows for act-first CI on private repos."""
from __future__ import annotations

from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

MARKER = "mcli-ci: hosted-triggers-stripped"
SELF_HOSTED_FILENAME = "self-hosted-ci.yml"
HOSTED_PREFIXES = ("ubuntu", "macos", "windows")


def is_hosted_label(label: str) -> bool:
    """True if a runs-on label names a GitHub-hosted runner image."""
    return str(label).lower().startswith(HOSTED_PREFIXES)


def runs_on_is_hosted(runs_on) -> bool:
    """Classify a job's runs-on. Conservative: unknown expressions count as hosted."""
    if runs_on is None:
        return False
    if isinstance(runs_on, (list, tuple)):
        labels = [str(x) for x in runs_on]
        if any("self-hosted" in lbl for lbl in labels):
            return False
        return any(is_hosted_label(lbl) for lbl in labels)
    text = str(runs_on)
    if "self-hosted" in text:
        return False
    if "${{" in text:
        return True  # unknown matrix/expression -> assume hosted to stop cost
    return is_hosted_label(text)
