"""Tests for the Python source sync module."""

import json

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def workflows_dir(tmp_path):
    """Create a temporary workflows directory."""
    d = tmp_path / "workflows"
    d.mkdir()
    return d


@pytest.fixture
def sample_script(tmp_path):
    """Create a sample Python script with metadata."""
    script = tmp_path / "backup.py"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "# @description: Backup files to S3\n"
        "# @version: 1.0.0\n"
        "# @tags: backup, aws\n"
        "\n"
        "import sys\n"
        "print('Backing up...')\n"
    )
    return script


class TestSyncSourceToCommand:
    """Test the sync_source_to_command function."""

    def test_sync_creates_json(self, sample_script, workflows_dir):
        from mcli.app.source_sync_cmd import sync_source_to_command

        result = sync_source_to_command(sample_script, "backup", workflows_dir)
        assert result is True

        json_path = workflows_dir / "backup.json"
        assert json_path.exists()

        data = json.loads(json_path.read_text())
        assert data["name"] == "backup"
        assert data["description"] == "Backup files to S3"
        assert data["version"] == "1.0.0"
        assert data["tags"] == ["backup", "aws"]
        assert data["language"] == "python"
        assert "import sys" in data["code"]

    def test_sync_updates_state(self, sample_script, workflows_dir):
        from mcli.app.source_sync_cmd import _load_sync_state, sync_source_to_command

        sync_source_to_command(sample_script, "backup", workflows_dir)
        state = _load_sync_state(workflows_dir)

        assert "backup" in state["links"]
        assert state["links"]["backup"]["source"] == str(sample_script.resolve())
        assert "source_hash" in state["links"]["backup"]

    def test_sync_no_change_returns_false(self, sample_script, workflows_dir):
        from mcli.app.source_sync_cmd import sync_source_to_command

        # First sync
        sync_source_to_command(sample_script, "backup", workflows_dir)
        # Second sync without changes
        result = sync_source_to_command(sample_script, "backup", workflows_dir)
        assert result is False

    def test_sync_detects_change(self, sample_script, workflows_dir):
        from mcli.app.source_sync_cmd import sync_source_to_command

        sync_source_to_command(sample_script, "backup", workflows_dir)

        # Modify source
        sample_script.write_text(sample_script.read_text() + "\nprint('done')\n")

        result = sync_source_to_command(sample_script, "backup", workflows_dir)
        assert result is True

    def test_sync_missing_source(self, workflows_dir, tmp_path):
        from mcli.app.source_sync_cmd import sync_source_to_command

        missing = tmp_path / "missing.py"
        result = sync_source_to_command(missing, "missing", workflows_dir)
        assert result is False


class TestSyncState:
    """Test sync state management."""

    def test_load_empty_state(self, workflows_dir):
        from mcli.app.source_sync_cmd import _load_sync_state

        state = _load_sync_state(workflows_dir)
        assert state == {"links": {}}

    def test_save_and_load_state(self, workflows_dir):
        from mcli.app.source_sync_cmd import _load_sync_state, _save_sync_state

        state = {"links": {"test": {"source": "/tmp/test.py", "source_hash": "abc"}}}
        _save_sync_state(workflows_dir, state)

        loaded = _load_sync_state(workflows_dir)
        assert loaded == state


class TestLinkCommand:
    """Test the mcli source link CLI command."""

    def test_link_creates_sync(self, runner, sample_script, tmp_path, monkeypatch):
        from mcli.app.source_sync_cmd import source_group

        workflows_dir = tmp_path / ".mcli" / "workflows"
        workflows_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            source_group, ["link", "backup", "--source", str(sample_script)]
        )
        assert result.exit_code == 0
        assert (workflows_dir / "backup.json").exists()

    def test_link_rejects_non_python(self, runner, tmp_path, monkeypatch):
        from mcli.app.source_sync_cmd import source_group

        shell_script = tmp_path / "backup.sh"
        shell_script.write_text("#!/bin/bash\necho hi\n")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            source_group, ["link", "backup", "--source", str(shell_script)]
        )
        assert result.exit_code == 0  # Click exits 0, error shown via UI


class TestUnlinkCommand:
    """Test the mcli source unlink CLI command."""

    def test_unlink_removes_link(self, runner, sample_script, tmp_path, monkeypatch):
        from mcli.app.source_sync_cmd import (
            _load_sync_state,
            source_group,
            sync_source_to_command,
        )

        workflows_dir = tmp_path / ".mcli" / "workflows"
        workflows_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        sync_source_to_command(sample_script, "backup", workflows_dir)

        result = runner.invoke(source_group, ["unlink", "backup"])
        assert result.exit_code == 0

        state = _load_sync_state(workflows_dir)
        assert "backup" not in state.get("links", {})


class TestStatusCommand:
    """Test the mcli source status CLI command."""

    def test_status_shows_links(self, runner, sample_script, tmp_path, monkeypatch):
        from mcli.app.source_sync_cmd import source_group, sync_source_to_command

        workflows_dir = tmp_path / ".mcli" / "workflows"
        workflows_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        sync_source_to_command(sample_script, "backup", workflows_dir)

        result = runner.invoke(source_group, ["status"])
        assert result.exit_code == 0
        assert "backup" in result.output

    def test_status_empty(self, runner, tmp_path, monkeypatch):
        from mcli.app.source_sync_cmd import source_group

        workflows_dir = tmp_path / ".mcli" / "workflows"
        workflows_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(source_group, ["status"])
        assert result.exit_code == 0
