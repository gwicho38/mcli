"""Path and configuration precedence stays inside explicit temporary workspaces."""

import json
from pathlib import Path

import pytest

from mcli.lib import paths

pytestmark = pytest.mark.unit


def test_environment_precedence_and_scoped_service_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.delenv("MCLI_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert paths.get_mcli_home() == tmp_path / "home" / ".mcli"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert paths.get_mcli_home() == tmp_path / "xdg" / "mcli"
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("MCLI_HOME", str(explicit))
    assert paths.get_mcli_home() == explicit
    for function, suffix in [
        (paths.get_logs_dir, "logs"),
        (paths.get_config_dir, "config"),
        (paths.get_data_dir, "data"),
        (paths.get_cache_dir, "cache"),
        (paths.get_services_pids_dir, "services/pids"),
        (paths.get_services_logs_dir, "services/logs"),
        (paths.get_services_state_dir, "services/state"),
    ]:
        directory = function()
        assert directory == explicit / suffix and directory.is_dir()


def test_nested_git_workspace_and_legacy_workflows_precedence(tmp_path, monkeypatch):
    global_home = tmp_path / "global"
    monkeypatch.setenv("MCLI_HOME", str(global_home))
    repo = tmp_path / "repo"
    nested = repo / "sub" / "nested"
    nested.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: fixture")
    monkeypatch.chdir(nested)
    assert paths.is_git_repository() and paths.get_git_root() == repo
    assert paths.get_local_mcli_dir() == repo / ".mcli"
    legacy = repo / ".mcli" / "commands"
    legacy.mkdir(parents=True)
    assert paths.get_custom_commands_dir() == legacy
    modern = repo / ".mcli" / "workflows"
    modern.mkdir()
    assert paths.get_custom_commands_dir() == modern
    assert paths.get_lockfile_path() == modern / "commands.lock.json"
    assert paths.get_custom_commands_dir(global_mode=True) == global_home / "workflows"
    (global_home / "workflows").rmdir()
    (global_home / "commands").mkdir()
    assert paths.get_custom_commands_dir(global_mode=True) == global_home / "commands"
    monkeypatch.chdir(tmp_path)
    assert not paths.is_git_repository() and paths.get_git_root() is None
    assert paths.get_local_commands_dir() is None


@pytest.mark.parametrize(
    "suffix,body",
    [
        ("json", lambda p: json.dumps({"workflows_dir": str(p)})),
        ("toml", lambda p: 'commands_dir="' + str(p) + '"\n'),
        ("yaml", lambda p: "workflows_dir: " + str(p) + "\n"),
    ],
)
def test_config_formats_resolve_explicit_workflows(tmp_path, suffix, body):
    workflows = tmp_path / "external-workflows"
    workflows.mkdir()
    config = tmp_path / ("fixture." + suffix)
    config.write_text(body(workflows))
    assert paths.resolve_workspace(str(config)) == workflows
    assert paths.resolve_workspace(str(tmp_path / "missing")) is None
    assert paths.resolve_workspace(str(tmp_path)) == tmp_path / ".mcli" / "workflows"
    config.write_text(body(tmp_path / "absent"))
    assert paths.resolve_workspace(str(config)) == tmp_path / ".mcli" / "workflows"


def test_directory_and_invalid_json_fallbacks(tmp_path):
    legacy = tmp_path / ".mcli" / "commands"
    legacy.mkdir(parents=True)
    assert paths.resolve_workspace(str(tmp_path)) == legacy
    invalid = tmp_path / "fixture.json"
    invalid.write_text("invalid JSON")
    assert paths.resolve_workspace(str(invalid)) == legacy
    modern = tmp_path / ".mcli" / "workflows"
    modern.mkdir()
    assert paths.resolve_workspace(str(tmp_path)) == modern
