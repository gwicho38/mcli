"""Regression: the legacy JSON command loader must skip ALL lockfiles.

Bug: `CustomCommandManager.load_all_commands` skipped only
``commands.lock.json``. A stale ``workflows.lock.json`` (left behind by the
v8.0.49 lockfile rename) was then loaded as if it were a legacy command,
producing ``ERROR Command data missing 'name' key: ['version',
'generated_at', 'commands']`` on every mcli invocation.
"""

import json
from unittest.mock import patch

from mcli.lib.custom_commands import CustomCommandManager

LOCKFILE_BODY = {
    "version": "2.0",
    "generated_at": "2026-06-01T00:00:00Z",
    "commands": {"foo": {"file": "foo.py"}},
}
VALID_CMD = {
    "name": "real_cmd",
    "code": "print('hi')",
    "language": "python",
    "description": "a real command",
}


def _manager(tmp_path):
    cmds = tmp_path / "commands"
    cmds.mkdir()
    with (
        patch("mcli.lib.custom_commands.get_custom_commands_dir", return_value=cmds),
        patch(
            "mcli.lib.custom_commands.get_lockfile_path", return_value=cmds / "commands.lock.json"
        ),
    ):
        return CustomCommandManager(global_mode=True), cmds


def test_load_all_commands_skips_workflows_lockfile(tmp_path):
    mgr, cmds = _manager(tmp_path)
    (cmds / "workflows.lock.json").write_text(json.dumps(LOCKFILE_BODY))
    (cmds / "commands.lock.json").write_text(json.dumps(LOCKFILE_BODY))
    (cmds / "real_cmd.json").write_text(json.dumps(VALID_CMD))

    loaded = mgr.load_all_commands()

    names = [c.get("name") for c in loaded]
    # Only the genuine command is loaded; neither lockfile leaks in.
    assert names == ["real_cmd"], names
    # No lockfile-shaped dict (version/generated_at/commands) sneaks through.
    assert all("generated_at" not in c for c in loaded), loaded


def test_legacy_loader_does_not_error_on_stale_lockfile(tmp_path, caplog):
    """No 'missing name key' ERROR should be logged for the stale lockfile."""
    import logging

    mgr, cmds = _manager(tmp_path)
    (cmds / "workflows.lock.json").write_text(json.dumps(LOCKFILE_BODY))

    with caplog.at_level(logging.ERROR):
        mgr.load_all_commands()

    assert "missing 'name' key" not in caplog.text, caplog.text
