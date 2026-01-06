"""
Tests for workflow creation commands (top-level commands in simplified CLI).

Tests the mcli new, edit, rm, and sync commands for creating
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
    """Test the 'mcli edit' command (top-level)."""

    def test_edit_command_exists(self, cli_runner, app):
        """Test that edit command is registered at top-level."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "edit" in result.output

    def test_edit_command_help(self, cli_runner, app):
        """Test that edit command shows help."""
        result = cli_runner.invoke(app, ["edit", "--help"])
        assert result.exit_code == 0
        assert "Edit" in result.output
        assert "COMMAND_NAME" in result.output


class TestDeleteCommand:
    """Test the 'mcli rm' command (top-level)."""

    def test_remove_command_exists(self, cli_runner, app):
        """Test that rm command is registered at top-level."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "rm" in result.output

    def test_remove_command_help(self, cli_runner, app):
        """Test that rm command shows help."""
        result = cli_runner.invoke(app, ["rm", "--help"])
        assert result.exit_code == 0
        assert "Delete" in result.output
        assert "COMMAND_NAME" in result.output


class TestSyncCommand:
    """Test the 'mcli sync' command (top-level)."""

    def test_sync_command_exists(self, cli_runner, app):
        """Test that sync command is registered at top-level."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "sync" in result.output

    def test_sync_command_help(self, cli_runner, app):
        """Test that sync command shows help."""
        result = cli_runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        # Sync command should show help about syncing
        assert result.exit_code == 0


class TestWorkflowCreationCommandsIntegration:
    """Integration tests for workflow creation commands."""

    def test_all_commands_registered(self, cli_runner, app):
        """Test that all workflow management commands are registered at top-level."""
        # Check top-level has all workflow management commands
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "new" in result.output
        assert "edit" in result.output
        assert "rm" in result.output
        assert "sync" in result.output
        assert "run" in result.output
