"""Regression coverage for semantic and corruption-safe lockfile updates."""

import json

import pytest

from mcli.lib.script_loader import ScriptLoader

PYTHON_SCRIPT = "#!/usr/bin/env python3\n# @description: {description}\nprint('{body}')\n"


def _write_script(path, description, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PYTHON_SCRIPT.format(description=description, body=body))


def _read_lockfile(loader):
    return json.loads(loader.lockfile_path.read_text())


def test_add_and_delete_only_change_the_command_map_membership(tmp_path):
    workflows_dir = tmp_path / "workflows"
    stable_script = workflows_dir / "stable.py"
    added_script = workflows_dir / "added.py"
    _write_script(stable_script, "stable", "stable")
    loader = ScriptLoader(workflows_dir)
    assert loader.save_lockfile() is True
    original = _read_lockfile(loader)

    _write_script(added_script, "added", "added")
    assert loader.save_lockfile() is True
    after_add = _read_lockfile(loader)
    assert after_add["commands"]["stable"] == original["commands"]["stable"]
    assert set(after_add["commands"]) == {"added", "stable"}
    assert after_add["generated_at"] != original["generated_at"]

    added_script.unlink()
    assert loader.save_lockfile() is True
    after_delete = _read_lockfile(loader)
    assert after_delete["commands"] == {"stable": original["commands"]["stable"]}
    assert after_delete["generated_at"] != after_add["generated_at"]


def test_malformed_json_is_replaced_with_a_valid_lockfile(tmp_path):
    workflows_dir = tmp_path / "workflows"
    _write_script(workflows_dir / "stable.py", "stable", "stable")
    loader = ScriptLoader(workflows_dir)
    loader.lockfile_path.write_text("{not-json")

    assert loader.save_lockfile() is True

    assert _read_lockfile(loader)["commands"]["stable"]["file"] == "stable.py"


def test_malformed_command_entry_is_replaced(tmp_path):
    workflows_dir = tmp_path / "workflows"
    _write_script(workflows_dir / "stable.py", "stable", "stable")
    loader = ScriptLoader(workflows_dir)
    loader.lockfile_path.write_text(
        json.dumps(
            {
                "version": "2.0",
                "generated_at": "2026-09-01T12:00:00Z",
                "commands": {"stable": ["invalid"]},
            }
        )
    )

    assert loader.save_lockfile() is True

    assert _read_lockfile(loader)["commands"]["stable"]["file"] == "stable.py"


def test_semantic_metadata_drift_is_repaired_even_when_hash_matches(tmp_path):
    workflows_dir = tmp_path / "workflows"
    _write_script(workflows_dir / "stable.py", "source description", "stable")
    loader = ScriptLoader(workflows_dir)
    assert loader.save_lockfile() is True
    lockfile = _read_lockfile(loader)
    original_hash = lockfile["commands"]["stable"]["content_hash"]
    lockfile["commands"]["stable"]["description"] = "stale lock metadata"
    loader.lockfile_path.write_text(json.dumps(lockfile, indent=2))

    assert loader.save_lockfile() is True

    repaired = _read_lockfile(loader)
    assert repaired["commands"]["stable"]["content_hash"] == original_hash
    assert repaired["commands"]["stable"]["description"] == "source description"
    assert repaired["generated_at"] != lockfile["generated_at"]


def test_no_op_with_stem_language_and_path_collisions_is_byte_stable(tmp_path):
    workflows_dir = tmp_path / "workflows"
    _write_script(workflows_dir / "a" / "task.py", "python a", "python-a")
    _write_script(workflows_dir / "b" / "task.py", "python b", "python-b")
    shell_script = workflows_dir / "a" / "task.sh"
    shell_script.write_text("#!/usr/bin/env bash\n# @description: shell\necho shell\n")
    loader = ScriptLoader(workflows_dir)
    assert loader.save_lockfile() is True
    first_bytes = loader.lockfile_path.read_bytes()

    assert loader.save_lockfile() is True

    assert loader.lockfile_path.read_bytes() == first_bytes
    commands = _read_lockfile(loader)["commands"]
    assert sorted(entry["file"] for entry in commands.values()) == [
        "a/task.py",
        "a/task.sh",
        "b/task.py",
    ]


def test_old_schema_command_entry_is_regenerated(tmp_path):
    workflows_dir = tmp_path / "workflows"
    _write_script(workflows_dir / "stable.py", "stable", "stable")
    loader = ScriptLoader(workflows_dir)
    assert loader.save_lockfile() is True
    lockfile = _read_lockfile(loader)
    lockfile["version"] = "1.0"
    lockfile["commands"]["stable"]["last_modified"] = "2000-01-01T00:00:00Z"
    loader.lockfile_path.write_text(json.dumps(lockfile, indent=2))

    assert loader.save_lockfile() is True

    regenerated = _read_lockfile(loader)
    assert regenerated["version"] == "2.0"
    assert regenerated["commands"]["stable"]["last_modified"] != "2000-01-01T00:00:00Z"


@pytest.mark.parametrize(
    "invalid_last_modified",
    [pytest.param("missing", id="missing"), None, "not-a-timestamp", 123],
)
def test_invalid_last_modified_is_regenerated(tmp_path, invalid_last_modified):
    workflows_dir = tmp_path / "workflows"
    _write_script(workflows_dir / "stable.py", "stable", "stable")
    loader = ScriptLoader(workflows_dir)
    assert loader.save_lockfile() is True
    lockfile = _read_lockfile(loader)
    if invalid_last_modified == "missing":
        lockfile["commands"]["stable"].pop("last_modified")
    else:
        lockfile["commands"]["stable"]["last_modified"] = invalid_last_modified
    loader.lockfile_path.write_text(json.dumps(lockfile, indent=2))

    assert loader.save_lockfile() is True

    regenerated = _read_lockfile(loader)
    last_modified = regenerated["commands"]["stable"]["last_modified"]
    assert isinstance(last_modified, str)
    assert last_modified.endswith("Z")
    assert last_modified != invalid_last_modified
