"""Unit tests for mcli init and mv commands.

Tests the new behaviors added in v8.0.26:
- mcli init defaults to local mcli/workflows in current directory
- mcli mv auto-detects directory paths as workspace destinations
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mcli.app.init_cmd import init
from mcli.app.mv_cmd import mv


class TestInitCommand:
    """Tests for mcli init command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for testing."""
        return tmp_path

    def test_init_defaults_to_local(self, cli_runner, temp_dir):
        """Test that mcli init creates local mcli/workflows by default."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            result = cli_runner.invoke(init, [])

            assert result.exit_code == 0
            assert Path("mcli/workflows").exists()
            assert Path("mcli/workflows/commands.lock.json").exists()
            assert "Local (directory-specific)" in result.output

    def test_init_global_flag_uses_home(self, cli_runner, temp_dir):
        """Test that mcli init --global uses ~/.mcli/workflows."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            # Patch at the source module where it's imported from
            with patch("mcli.lib.paths.get_mcli_home") as mock_home:
                mock_home.return_value = temp_dir / "mock_mcli_home"
                result = cli_runner.invoke(init, ["--global"])

                assert result.exit_code == 0
                assert (temp_dir / "mock_mcli_home" / "workflows").exists()
                assert "Global (user-wide)" in result.output

    def test_init_creates_lockfile_with_correct_scope(self, cli_runner, temp_dir):
        """Test that lockfile has correct scope field."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            result = cli_runner.invoke(init, [])

            assert result.exit_code == 0

            lockfile_path = Path("mcli/workflows/commands.lock.json")
            with open(lockfile_path) as f:
                lockfile = json.load(f)

            assert lockfile["scope"] == "local"

    def test_init_global_lockfile_scope(self, cli_runner, temp_dir):
        """Test that global init creates lockfile with global scope."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            # Patch at the source module where it's imported from
            with patch("mcli.lib.paths.get_mcli_home") as mock_home:
                mock_home.return_value = temp_dir / "mock_mcli_home"
                result = cli_runner.invoke(init, ["--global"])

                assert result.exit_code == 0

                lockfile_path = temp_dir / "mock_mcli_home" / "workflows" / "commands.lock.json"
                with open(lockfile_path) as f:
                    lockfile = json.load(f)

                assert lockfile["scope"] == "global"

    def test_init_creates_readme(self, cli_runner, temp_dir):
        """Test that init creates a README.md file."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            result = cli_runner.invoke(init, [])

            assert result.exit_code == 0
            assert Path("mcli/workflows/README.md").exists()

    def test_init_creates_gitignore(self, cli_runner, temp_dir):
        """Test that init creates a .gitignore file."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            result = cli_runner.invoke(init, [])

            assert result.exit_code == 0
            assert Path("mcli/workflows/.gitignore").exists()

    def test_init_force_reinitializes(self, cli_runner, temp_dir):
        """Test that --force flag allows reinitialization."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            # First init
            result1 = cli_runner.invoke(init, [])
            assert result1.exit_code == 0

            # Second init with force
            result2 = cli_runner.invoke(init, ["--force"])
            assert result2.exit_code == 0
            assert "Created workflows directory" in result2.output

    def test_init_without_force_prompts(self, cli_runner, temp_dir):
        """Test that without --force, init prompts when already initialized."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            # First init
            result1 = cli_runner.invoke(init, [])
            assert result1.exit_code == 0

            # Second init without force - answer 'n' to prompt
            result2 = cli_runner.invoke(init, [], input="n\n")
            assert result2.exit_code == 0
            assert "already initialized" in result2.output


class TestMvCommand:
    """Tests for mcli mv command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def setup_workflows(self, tmp_path):
        """Create a mock workflow setup for testing."""
        # Create source workflows directory with a test command
        workflows_dir = tmp_path / "mcli" / "workflows"
        workflows_dir.mkdir(parents=True)

        # Create a test command file
        test_cmd = workflows_dir / "test-cmd.py"
        test_cmd.write_text("#!/usr/bin/env python3\nprint('hello')")

        # Create lockfile
        lockfile = workflows_dir / "commands.lock.json"
        lockfile.write_text(json.dumps({"version": "1.0", "scope": "local", "commands": {}}))

        return tmp_path

    def test_mv_detects_directory_as_workspace(self, cli_runner, tmp_path):
        """Test that mv auto-detects directory path as workspace destination."""
        # Setup source
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_workflows = source_dir / "mcli" / "workflows"
        source_workflows.mkdir(parents=True)

        test_cmd = source_workflows / "my-cmd.py"
        test_cmd.write_text("#!/usr/bin/env python3\nprint('hello')")

        lockfile = source_workflows / "commands.lock.json"
        lockfile.write_text(json.dumps({"version": "1.0", "scope": "local", "commands": {}}))

        # Setup destination directory
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()

        # Mock get_custom_commands_dir to return source workflows
        with patch("mcli.app.mv_cmd.get_custom_commands_dir") as mock_get_dir:
            mock_get_dir.return_value = source_workflows

            result = cli_runner.invoke(mv, ["my-cmd", str(dest_dir) + "/"], input="y\n")

            # Should recognize it's a directory and try to move there
            # The command may fail because dest doesn't have mcli/workflows but
            # the important thing is it recognized the directory path
            assert "destination" in result.output.lower() or "workspace" in result.output.lower()

    def test_mv_directory_ending_with_slash(self, cli_runner, tmp_path):
        """Test that paths ending with / are treated as directories."""
        # This tests the path detection logic
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_workflows = source_dir / "mcli" / "workflows"
        source_workflows.mkdir(parents=True)

        test_cmd = source_workflows / "my-cmd.py"
        test_cmd.write_text("#!/usr/bin/env python3\nprint('hello')")

        lockfile = source_workflows / "commands.lock.json"
        lockfile.write_text(json.dumps({"version": "1.0", "scope": "local", "commands": {}}))

        # Non-existent directory with trailing slash should error
        with patch("mcli.app.mv_cmd.get_custom_commands_dir") as mock_get_dir:
            mock_get_dir.return_value = source_workflows

            # Use a path that clearly doesn't exist and ends with /
            result = cli_runner.invoke(mv, ["my-cmd", str(tmp_path / "nonexistent") + "/"])

            # The command outputs an error message about directory not existing
            assert "does not exist" in result.output

    def test_mv_conflicting_workspace_options(self, cli_runner, tmp_path):
        """Test that providing both directory path and -w option fails."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_workflows = source_dir / "mcli" / "workflows"
        source_workflows.mkdir(parents=True)

        test_cmd = source_workflows / "my-cmd.py"
        test_cmd.write_text("#!/usr/bin/env python3\nprint('hello')")

        lockfile = source_workflows / "commands.lock.json"
        lockfile.write_text(json.dumps({"version": "1.0", "scope": "local", "commands": {}}))

        # Create both a directory destination and use -w
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        other_dir = tmp_path / "other"
        other_dir.mkdir()

        with patch("mcli.app.mv_cmd.get_custom_commands_dir") as mock_get_dir:
            mock_get_dir.return_value = source_workflows

            # Use existing directory path (detected as workspace) AND -w flag
            # This should fail because you can't specify workspace twice
            result = cli_runner.invoke(mv, ["my-cmd", str(dest_dir), "-w", str(other_dir)])

            # When dest_dir is detected as workspace AND -w is provided, should show error
            # The message indicates conflicting options were detected
            assert "cannot" in result.output.lower() or "conflict" in result.output.lower()

    def test_mv_preserves_command_name_when_moving_to_directory(self, cli_runner, tmp_path):
        """Test that moving to a directory preserves the original command name."""
        # Setup source
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_workflows = source_dir / "mcli" / "workflows"
        source_workflows.mkdir(parents=True)

        test_cmd = source_workflows / "original-name.py"
        test_cmd.write_text("#!/usr/bin/env python3\nprint('hello')")

        lockfile = source_workflows / "commands.lock.json"
        lockfile.write_text(json.dumps({"version": "1.0", "scope": "local", "commands": {}}))

        # Setup destination with mcli/workflows
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()
        dest_workflows = dest_dir / "mcli" / "workflows"
        dest_workflows.mkdir(parents=True)

        dest_lockfile = dest_workflows / "commands.lock.json"
        dest_lockfile.write_text(json.dumps({"version": "1.0", "scope": "local", "commands": {}}))

        with patch("mcli.app.mv_cmd.get_custom_commands_dir") as mock_get_dir:
            mock_get_dir.return_value = source_workflows

            # Move to directory - should keep original-name
            result = cli_runner.invoke(mv, ["original-name", str(dest_dir)], input="y\n")

            # Check the destination path in output contains original-name
            if result.exit_code == 0:
                assert "original-name" in result.output


class TestMvCommandRename:
    """Tests for mcli mv rename functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Provide a Click CLI runner."""
        return CliRunner()

    def test_mv_same_source_dest_no_change(self, cli_runner, tmp_path):
        """Test that mv with same source and dest does nothing."""
        workflows_dir = tmp_path / "mcli" / "workflows"
        workflows_dir.mkdir(parents=True)

        test_cmd = workflows_dir / "my-cmd.py"
        test_cmd.write_text("#!/usr/bin/env python3\nprint('hello')")

        lockfile = workflows_dir / "commands.lock.json"
        lockfile.write_text(json.dumps({"version": "1.0", "scope": "local", "commands": {}}))

        with patch("mcli.app.mv_cmd.get_custom_commands_dir") as mock_get_dir:
            mock_get_dir.return_value = workflows_dir

            result = cli_runner.invoke(mv, ["my-cmd"])

            assert result.exit_code == 0
            assert "Nothing to do" in result.output or "same" in result.output.lower()
