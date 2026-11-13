"""Registered workflow catalogs use real isolated directories and scripts."""

from unittest.mock import patch

import pytest

from mcli.lib import workspace_registry as registry

pytestmark = pytest.mark.unit


def test_register_catalog_and_unregister_preserve_other_workspaces(tmp_path, monkeypatch):
    home = tmp_path / "mcli-home"
    home.mkdir()
    monkeypatch.setattr(registry, "get_mcli_home", lambda: home)
    monkeypatch.setattr(registry, "is_git_repository", lambda: False)
    modern = tmp_path / "modern"
    legacy = tmp_path / "legacy"
    for root, folder in [(modern, "workflows"), (legacy, "commands"), (home, "workflows")]:
        workflows = (root / ".mcli" / folder) if root != home else root / folder
        workflows.mkdir(parents=True)
        (workflows / "backup.py").write_text('# @description: Fixture backup\nprint("fixture")\n')
    assert registry.register_workspace(tmp_path / "missing") is None
    modern_id = registry.register_workspace(modern, "Modern")
    legacy_id = registry.register_workspace(legacy)
    assert modern_id == str(modern.resolve())
    assert legacy_id == str(legacy.resolve())
    assert {x["name"] for x in registry.list_registered_workspaces()} == {"Modern", "legacy"}
    assert all(x["exists"] for x in registry.list_registered_workspaces())
    workflows = registry.get_all_workflows()
    assert len(workflows) == 3
    assert all(entries[0]["name"] == "backup" for entries in workflows.values())
    assert all(entries[0]["description"] == "Fixture backup" for entries in workflows.values())
    assert registry.unregister_workspace(modern) is True
    assert registry.unregister_workspace(modern) is False
    assert [x["id"] for x in registry.list_registered_workspaces()] == [legacy_id]
    monkeypatch.chdir(legacy)
    assert registry.unregister_workspace() is True
    assert registry.list_registered_workspaces() == []
    registry.get_registry_path().write_text("invalid JSON")
    assert registry.load_registry() == {"version": "1.0", "workspaces": {}}


def test_auto_registration_requires_git_workflows_and_is_idempotent(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(registry, "get_mcli_home", lambda: home)
    monkeypatch.setattr(registry, "is_git_repository", lambda: False)
    assert registry.auto_register_current() is None
    monkeypatch.setattr(registry, "is_git_repository", lambda: True)
    monkeypatch.setattr(registry, "get_git_root", lambda: None)
    assert registry.auto_register_current() is None
    assert registry.register_workspace() is None
    assert registry.unregister_workspace() is False
    monkeypatch.setattr(registry, "get_git_root", lambda: tmp_path)
    assert registry.auto_register_current() is None
    (tmp_path / ".mcli" / "workflows").mkdir(parents=True)
    assert registry.auto_register_current() == str(tmp_path)
    before = registry.get_registry_path().read_bytes()
    assert registry.auto_register_current() == str(tmp_path)
    assert registry.get_registry_path().read_bytes() == before
    with patch.object(
        registry, "get_registry_path", return_value=tmp_path / "missing" / "registry.json"
    ):
        assert registry.save_registry({"workspaces": {}}) is False
