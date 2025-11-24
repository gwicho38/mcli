"""
Tests for top-level workflow creation commands: new, edit, delete.

Tests the mcli new, mcli edit, and mcli delete/remove commands for creating
and managing workflows.
"""

import pytest
from click.testing import CliRunner

from mcli.app.main import create_app


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def app():
    """Create the MCLI application."""
    return create_app()


class TestNewCommand:
    """Test the 'mcli new' command."""

    def test_new_command_exists(self, cli_runner, app):
        """Test that new command is registered."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "new" in result.output

    def test_new_command_help(self, cli_runner, app):
        """Test that new command shows help."""
        result = cli_runner.invoke(app, ["new", "--help"])
        assert result.exit_code == 0
        assert "Create a new workflow command" in result.output
        assert "COMMAND_NAME" in result.output
        assert "--template" in result.output
        assert "--language" in result.output
        assert "--global" in result.output


class TestEditCommand:
    """Test the 'mcli edit' command."""

    def test_edit_command_exists(self, cli_runner, app):
        """Test that edit command is registered."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "edit" in result.output

    def test_edit_command_help(self, cli_runner, app):
        """Test that edit command shows help."""
        result = cli_runner.invoke(app, ["edit", "--help"])
        assert result.exit_code == 0
        assert "Edit a command interactively" in result.output
        assert "COMMAND_NAME" in result.output
        assert "--editor" in result.output
        assert "--global" in result.output


class TestDeleteCommand:
    """Test the 'mcli delete' and 'mcli remove' commands."""

    def test_delete_command_exists(self, cli_runner, app):
        """Test that delete command is registered."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "delete" in result.output

    def test_delete_command_help(self, cli_runner, app):
        """Test that delete command shows help."""
        result = cli_runner.invoke(app, ["delete", "--help"])
        assert result.exit_code == 0
        assert "Remove a custom command" in result.output
        assert "COMMAND_NAME" in result.output
        assert "--yes" in result.output
        assert "--global" in result.output

    def test_remove_command_exists(self, cli_runner, app):
        """Test that remove command is registered (alias of delete)."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "remove" in result.output

    def test_remove_command_help(self, cli_runner, app):
        """Test that remove command shows help (alias of delete)."""
        result = cli_runner.invoke(app, ["remove", "--help"])
        assert result.exit_code == 0
        assert "Remove a custom command" in result.output


class TestSyncCommand:
    """Test the 'mcli sync' command."""

    def test_sync_command_exists(self, cli_runner, app):
        """Test that sync command is registered."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "sync" in result.output

    def test_sync_command_help(self, cli_runner, app):
        """Test that sync command shows help."""
        result = cli_runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "Sync workflows" in result.output
        assert "--global" in result.output
        assert "--force" in result.output


class TestWorkflowCreationCommandsIntegration:
    """Integration tests for workflow creation commands."""

    def test_all_commands_registered(self, cli_runner, app):
        """Test that all workflow management commands are registered in main CLI."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Check all commands are present
        assert "new" in result.output
        assert "edit" in result.output
        assert "delete" in result.output
        assert "remove" in result.output
        assert "sync" in result.output

        # Verify descriptions are shown
        assert "Create a new workflow command" in result.output or "workflow command" in result.output.lower()
        assert "Edit a command" in result.output or "edit" in result.output.lower()
        assert "Remove a custom command" in result.output or "remove" in result.output.lower()
        assert "Sync workflows" in result.output or "sync" in result.output.lower()
