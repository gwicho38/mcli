"""Tests for the model_cmd stub (#178 coverage) + #165 RCE regression guard.

model_cmd was the module that previously `exec()`'d arbitrary code from a
``model.json`` workflow file. It is now a safe stub: it must NEVER execute
code found in model.json, regardless of whether such a file exists.
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import patch


def _reload_model_cmd():
    """Re-import model_cmd so its module-level loading logic runs now."""
    sys.modules.pop("mcli.app.model_cmd", None)
    return importlib.import_module("mcli.app.model_cmd")


def test_does_not_execute_code_from_model_json(tmp_path):
    """A malicious model.json must NOT run on import (#165)."""
    home = tmp_path
    workflows = home / ".mcli" / "workflows"
    workflows.mkdir(parents=True)
    canary = tmp_path / "model_cmd_pwned_canary"
    # A model.json whose "code" would create the canary if exec()'d.
    (workflows / "model.json").write_text(
        '{"name": "model", "code": "open(r\'%s\', \'w\').write(\'pwned\')"}' % canary
    )

    with patch.object(Path, "home", return_value=home):
        mod = _reload_model_cmd()

    # The gadget must not have executed.
    assert not canary.exists(), "model.json code was executed — RCE regression!"
    # The stub exposes the symbols but they are inert (None).
    assert mod.model is None
    assert mod.download is None


def test_exposes_backwards_compat_symbols(tmp_path):
    with patch.object(Path, "home", return_value=tmp_path):
        mod = _reload_model_cmd()
    for sym in [
        "model",
        "list",
        "download",
        "start",
        "recommend",
        "status",
        "stop",
        "pull",
        "delete",
    ]:
        assert sym in mod.__all__
        assert getattr(mod, sym) is None


def test_no_model_json_is_safe(tmp_path):
    """No model.json present → module still imports cleanly with inert symbols."""
    with patch.object(Path, "home", return_value=tmp_path):
        mod = _reload_model_cmd()
    assert mod.model is None


def teardown_module(_):
    # Restore a clean import for any later test that imports model_cmd.
    sys.modules.pop("mcli.app.model_cmd", None)
