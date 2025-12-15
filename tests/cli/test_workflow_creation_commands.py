"""
Tests for workflow creation commands under 'mcli workflow'.

Tests the mcli workflow add, edit, remove, and sync commands for creating
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
    """Test the 'mcli workflow edit' command."""

    def test_edit_command_exists(self, cli_runner, app):
        """Test that edit command is registered under workflow."""
        result = cli_runner.invoke(app, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "edit" in result.output

    def test_edit_command_help(self, cli_runner, app):
        """Test that edit command shows help."""
        result = cli_runner.invoke(app, ["workflow", "edit", "--help"])
        assert result.exit_code == 0
        assert "Edit a command" in result.output
        assert "COMMAND_NAME" in result.output
        assert "--editor" in result.output
        assert "--global" in result.output


class TestDeleteCommand:
    """Test the 'mcli workflow remove' command."""

    def test_remove_command_exists(self, cli_runner, app):
        """Test that remove command is registered under workflow."""
        result = cli_runner.invoke(app, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "remove" in result.output

    def test_remove_command_help(self, cli_runner, app):
        """Test that remove command shows help."""
        result = cli_runner.invoke(app, ["workflow", "remove", "--help"])
        assert result.exit_code == 0
        assert "Remove a custom command" in result.output
        assert "COMMAND_NAME" in result.output
        assert "--yes" in result.output
        assert "--global" in result.output


class TestSyncCommand:
    """Test the 'mcli workflow sync' command."""

    def test_sync_command_exists(self, cli_runner, app):
        """Test that sync command is registered under workflow."""
        result = cli_runner.invoke(app, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "sync" in result.output

    def test_sync_command_help(self, cli_runner, app):
        """Test that sync command shows help."""
        result = cli_runner.invoke(app, ["workflow", "sync", "--help"])
        assert result.exit_code == 0
        # Sync command should show help about syncing
        assert result.exit_code == 0


class TestWorkflowCreationCommandsIntegration:
    """Integration tests for workflow creation commands."""

    def test_all_commands_registered(self, cli_runner, app):
        """Test that all workflow management commands are registered."""
        # Check top-level has new command
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "new" in result.output
        assert "workflow" in result.output

        # Check workflow subcommands
        result = cli_runner.invoke(app, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "edit" in result.output
        assert "remove" in result.output
        assert "sync" in result.output
        assert "add" in result.output
