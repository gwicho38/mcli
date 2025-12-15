"""
Integration tests for notebook workflow discovery and execution.

Tests the end-to-end integration of notebook files as workflow commands.

NOTE: Dynamic notebook discovery as CLI commands is a planned feature that
requires additional work. These tests are skipped until the feature is complete.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mcli.lib.custom_commands import get_command_manager
from mcli.workflow.workflow import workflows

pytestmark = pytest.mark.skip(reason="Dynamic notebook command discovery not yet implemented")


@pytest.fixture
def temp_notebook_file(tmp_path):
    """Create a temporary notebook file for testing."""
    notebook_content = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Test Notebook\n", "Integration test notebook"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ["import click\n"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "@click.command()\n",
                    "@click.option('--count', default=1, help='Number of greetings')\n",
                    "def greet(count):\n",
                    '    """Greet the user"""\n',
                    "    for i in range(count):\n",
                    '        click.echo(f"Hello {i+1}!")\n',
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "@click.command()\n",
                    "@click.argument('name')\n",
                    "def goodbye(name):\n",
                    '    """Say goodbye"""\n',
                    '    click.echo(f"Goodbye, {name}!")\n',
                ],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0",
            },
            "mcli": {
                "name": "testbook",
                "description": "Integration test notebook",
                "version": "1.0.0",
                "language": "python",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }

    notebook_file = tmp_path / "testbook.ipynb"
    with open(notebook_file, "w") as f:
        json.dump(notebook_content, f, indent=2)

    return notebook_file


@pytest.fixture
def temp_commands_dir_with_notebook(tmp_path, temp_notebook_file, monkeypatch):
    """Set up a temporary commands directory with a notebook."""
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()

    # Copy notebook to commands directory
    import shutil

    dest = commands_dir / "testbook.ipynb"
    shutil.copy(temp_notebook_file, dest)

    # Mock the commands directory
    def mock_get_custom_commands_dir(global_mode=False):
        return commands_dir

    monkeypatch.setattr(
        "mcli.lib.custom_commands.get_custom_commands_dir",
        mock_get_custom_commands_dir,
    )

    return commands_dir


class TestNotebookDiscovery:
    """Test notebook discovery in workflow system."""

    def test_notebook_discovered_in_list_commands(
        self, temp_commands_dir_with_notebook, monkeypatch
    ):
        """Test that notebook appears in workflow list."""
        # Mock get_command_manager to use test directory
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(temp_commands_dir_with_notebook)

        # Patch at import location
        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        result = runner.invoke(workflows, ["--help"])

        assert result.exit_code == 0
        assert "testbook" in result.output

    def test_notebook_command_group_loads(self, temp_commands_dir_with_notebook, monkeypatch):
        """Test that notebook loads as a command group."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(temp_commands_dir_with_notebook)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        result = runner.invoke(workflows, ["testbook", "--help"])

        assert result.exit_code == 0
        assert "greet" in result.output
        assert "goodbye" in result.output

    def test_notebook_subcommand_executes(self, temp_commands_dir_with_notebook, monkeypatch):
        """Test that notebook subcommands execute correctly."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(temp_commands_dir_with_notebook)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        result = runner.invoke(workflows, ["testbook", "greet", "--count", "3"])

        assert result.exit_code == 0
        assert "Hello 1!" in result.output
        assert "Hello 2!" in result.output
        assert "Hello 3!" in result.output

    def test_notebook_subcommand_with_argument(self, temp_commands_dir_with_notebook, monkeypatch):
        """Test notebook subcommand with arguments."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(temp_commands_dir_with_notebook)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        result = runner.invoke(workflows, ["testbook", "goodbye", "Alice"])

        assert result.exit_code == 0
        assert "Goodbye, Alice!" in result.output


class TestNotebookInSubdirectory:
    """Test notebook discovery in subdirectories."""

    @pytest.fixture
    def commands_dir_with_nested_notebook(self, tmp_path, temp_notebook_file, monkeypatch):
        """Set up commands directory with notebook in subdirectory."""
        commands_dir = tmp_path / "commands"
        subdir = commands_dir / "ml"
        subdir.mkdir(parents=True)

        # Copy notebook to subdirectory
        import shutil

        dest = subdir / "testbook.ipynb"
        shutil.copy(temp_notebook_file, dest)

        def mock_get_custom_commands_dir(global_mode=False):
            return commands_dir

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_custom_commands_dir",
            mock_get_custom_commands_dir,
        )

        return commands_dir

    def test_nested_notebook_discovered(self, commands_dir_with_nested_notebook, monkeypatch):
        """Test that notebook in subdirectory is discovered."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(commands_dir_with_nested_notebook)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        result = runner.invoke(workflows, ["--help"])

        assert result.exit_code == 0
        assert "testbook" in result.output


class TestMultipleNotebooks:
    """Test handling of multiple notebook files."""

    @pytest.fixture
    def commands_dir_with_multiple_notebooks(self, tmp_path, monkeypatch):
        """Set up commands directory with multiple notebooks."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        # Create first notebook
        notebook1 = {
            "cells": [
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "source": ["import click\n"],
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "@click.command()\n",
                        "def cmd1():\n",
                        '    click.echo("Command 1")\n',
                    ],
                },
            ],
            "metadata": {
                "mcli": {
                    "name": "notebook1",
                    "description": "First notebook",
                    "version": "1.0.0",
                    "language": "python",
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        # Create second notebook
        notebook2 = {
            "cells": [
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "source": ["import click\n"],
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "@click.command()\n",
                        "def cmd2():\n",
                        '    click.echo("Command 2")\n',
                    ],
                },
            ],
            "metadata": {
                "mcli": {
                    "name": "notebook2",
                    "description": "Second notebook",
                    "version": "1.0.0",
                    "language": "python",
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        # Write notebooks
        with open(commands_dir / "notebook1.ipynb", "w") as f:
            json.dump(notebook1, f)

        with open(commands_dir / "notebook2.ipynb", "w") as f:
            json.dump(notebook2, f)

        def mock_get_custom_commands_dir(global_mode=False):
            return commands_dir

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_custom_commands_dir",
            mock_get_custom_commands_dir,
        )

        return commands_dir

    def test_multiple_notebooks_discovered(self, commands_dir_with_multiple_notebooks, monkeypatch):
        """Test that multiple notebooks are all discovered."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(commands_dir_with_multiple_notebooks)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        result = runner.invoke(workflows, ["--help"])

        assert result.exit_code == 0
        assert "notebook1" in result.output
        assert "notebook2" in result.output

    def test_multiple_notebooks_execute_independently(
        self, commands_dir_with_multiple_notebooks, monkeypatch
    ):
        """Test that multiple notebooks execute independently."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(commands_dir_with_multiple_notebooks)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()

        # Execute from first notebook
        result1 = runner.invoke(workflows, ["notebook1", "cmd1"])
        assert result1.exit_code == 0
        assert "Command 1" in result1.output

        # Execute from second notebook
        result2 = runner.invoke(workflows, ["notebook2", "cmd2"])
        assert result2.exit_code == 0
        assert "Command 2" in result2.output


class TestHiddenFileFiltering:
    """Test that hidden notebook files are properly filtered."""

    @pytest.fixture
    def commands_dir_with_hidden_notebook(self, tmp_path, temp_notebook_file, monkeypatch):
        """Set up commands directory with hidden notebook file."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        # Create hidden subdirectory
        hidden_dir = commands_dir / ".hidden"
        hidden_dir.mkdir()

        # Copy notebook to hidden directory
        import shutil

        dest = hidden_dir / "testbook.ipynb"
        shutil.copy(temp_notebook_file, dest)

        def mock_get_custom_commands_dir(global_mode=False):
            return commands_dir

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_custom_commands_dir",
            mock_get_custom_commands_dir,
        )

        return commands_dir

    def test_hidden_notebook_not_discovered(self, commands_dir_with_hidden_notebook, monkeypatch):
        """Test that notebooks in hidden directories are not discovered."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(commands_dir_with_hidden_notebook)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        result = runner.invoke(workflows, ["--help"])

        assert result.exit_code == 0
        assert "testbook" not in result.output


class TestNotebookWithoutMCLIMetadata:
    """Test handling of notebooks without MCLI metadata."""

    @pytest.fixture
    def notebook_without_metadata(self, tmp_path, monkeypatch):
        """Create notebook without MCLI metadata."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        notebook_content = {
            "cells": [
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "source": ["import click\n"],
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "@click.command()\n",
                        "def test():\n",
                        '    click.echo("Test")\n',
                    ],
                },
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                }
                # No MCLI metadata
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        notebook_file = commands_dir / "no_metadata.ipynb"
        with open(notebook_file, "w") as f:
            json.dump(notebook_content, f)

        def mock_get_custom_commands_dir(global_mode=False):
            return commands_dir

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_custom_commands_dir",
            mock_get_custom_commands_dir,
        )

        return commands_dir

    def test_notebook_without_metadata_fails_gracefully(
        self, notebook_without_metadata, monkeypatch
    ):
        """Test that notebooks without MCLI metadata fail gracefully."""
        from mcli.lib.custom_commands import CustomCommandManager

        def mock_get_command_manager(global_mode=False):
            return CustomCommandManager(notebook_without_metadata)

        monkeypatch.setattr(
            "mcli.lib.custom_commands.get_command_manager",
            mock_get_command_manager,
        )

        runner = CliRunner()
        # Should not crash, just not show the notebook
        result = runner.invoke(workflows, ["--help"])

        assert result.exit_code == 0
        # Notebook should not appear in listing
        assert "no_metadata" not in result.output
