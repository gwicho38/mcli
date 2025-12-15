"""
Integration tests for direct file execution via mcli run.

Tests running files directly without placing them in workflows directory.

NOTE: Direct file execution (mcli run /path/to/script.py) is a planned feature
that hasn't been fully implemented yet. These tests are skipped until the
feature is complete.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mcli.workflow.workflow import workflows

pytestmark = pytest.mark.skip(
    reason="Direct file execution feature not yet implemented - see issue for tracking"
)


@pytest.fixture
def test_python_script(tmp_path):
    """Create a test Python script."""
    script = tmp_path / "test.py"
    script.write_text(
        """#!/usr/bin/env python3
import sys
print("Hello from Python!")
if sys.argv[1:]:
    print(f"Args: {sys.argv[1:]}")
"""
    )
    return script


@pytest.fixture
def test_shell_script(tmp_path):
    """Create a test shell script."""
    script = tmp_path / "test.sh"
    script.write_text(
        """#!/bin/bash
echo "Hello from shell!"
if [ $# -gt 0 ]; then
    echo "Args: $@"
fi
"""
    )
    script.chmod(0o755)
    return script


@pytest.fixture
def test_notebook(tmp_path):
    """Create a test Jupyter notebook."""
    notebook = tmp_path / "test.ipynb"
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
                    "@click.option('--name', default='World')\n",
                    "def greet(name):\n",
                    '    """Greet someone"""\n',
                    '    click.echo(f"Hello, {name}!")\n',
                ],
            },
        ],
        "metadata": {
            "mcli": {
                "name": "test",
                "description": "Test notebook",
                "version": "1.0.0",
                "language": "python",
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    with open(notebook, "w") as f:
        json.dump(notebook_content, f)
    return notebook


class TestPythonScriptExecution:
    """Test direct execution of Python scripts."""

    def test_execute_python_script(self, test_python_script):
        """Test executing a Python script directly."""
        runner = CliRunner()
        result = runner.invoke(workflows, [str(test_python_script)], catch_exceptions=False)

        assert result.exit_code == 0
        # Note: Output goes directly to stdout, not captured by Click

    def test_execute_python_script_with_args(self, test_python_script):
        """Test executing Python script with arguments."""
        runner = CliRunner()
        result = runner.invoke(
            workflows, [str(test_python_script), "arg1", "arg2"], catch_exceptions=False
        )

        assert result.exit_code == 0
        # Note: Output goes directly to stdout, not captured by Click

    def test_execute_python_script_relative_path(self, test_python_script, monkeypatch):
        """Test executing Python script with relative path."""
        # Change to script directory
        monkeypatch.chdir(test_python_script.parent)

        runner = CliRunner()
        result = runner.invoke(workflows, [test_python_script.name], catch_exceptions=False)

        assert result.exit_code == 0
        # Note: Output goes directly to stdout, not captured by Click


class TestShellScriptExecution:
    """Test direct execution of shell scripts."""

    def test_execute_shell_script(self, test_shell_script):
        """Test executing a shell script directly."""
        runner = CliRunner()
        result = runner.invoke(workflows, [str(test_shell_script)], catch_exceptions=False)

        assert result.exit_code == 0
        # Note: Output goes directly to stdout, not captured by Click

    def test_execute_shell_script_with_args(self, test_shell_script):
        """Test executing shell script with arguments."""
        runner = CliRunner()
        result = runner.invoke(
            workflows, [str(test_shell_script), "foo", "bar"], catch_exceptions=False
        )

        assert result.exit_code == 0
        # Note: Output goes directly to stdout, not captured by Click

    def test_execute_non_executable_shell_script(self, tmp_path):
        """Test executing a shell script that's not marked executable."""
        script = tmp_path / "test.sh"
        script.write_text(
            """#!/bin/bash
echo "Not executable initially!"
"""
        )
        # Don't make it executable

        runner = CliRunner()
        result = runner.invoke(workflows, [str(script)], catch_exceptions=False)

        # Should work - the code makes it executable automatically
        assert result.exit_code == 0
        # Note: Output goes directly to stdout, not captured by Click


class TestNotebookExecution:
    """Test direct execution of Jupyter notebooks."""

    def test_execute_notebook_command(self, test_notebook):
        """Test executing a Jupyter notebook command directly."""
        runner = CliRunner()
        result = runner.invoke(workflows, [str(test_notebook), "greet"])

        assert result.exit_code == 0
        assert "Hello, World!" in result.output

    def test_execute_notebook_command_with_options(self, test_notebook):
        """Test executing notebook command with options."""
        runner = CliRunner()
        result = runner.invoke(workflows, [str(test_notebook), "greet", "--name", "Alice"])

        assert result.exit_code == 0
        assert "Hello, Alice!" in result.output

    def test_execute_notebook_shows_help(self, test_notebook):
        """Test that notebook shows help when requested."""
        runner = CliRunner()
        result = runner.invoke(workflows, [str(test_notebook), "--help"])

        assert result.exit_code == 0
        assert "greet" in result.output.lower()


class TestErrorHandling:
    """Test error handling for direct file execution."""

    def test_nonexistent_file(self):
        """Test executing a file that doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(workflows, ["/nonexistent/file.py"])

        # Should fail gracefully - file doesn't exist so falls through to normal command lookup
        assert result.exit_code != 0

    def test_directory_instead_of_file(self, tmp_path):
        """Test passing a directory instead of a file."""
        runner = CliRunner()
        result = runner.invoke(workflows, [str(tmp_path)])

        # Should fail - directories aren't files
        assert result.exit_code != 0

    def test_unsupported_file_type(self, tmp_path):
        """Test executing an unsupported file type."""
        unsupported = tmp_path / "test.txt"
        unsupported.write_text("Just a text file")

        runner = CliRunner()
        result = runner.invoke(workflows, [str(unsupported)])

        # Should fail - unsupported file type
        assert result.exit_code != 0


class TestMixedUsage:
    """Test mixing direct file execution with normal workflow commands."""

    def test_can_still_use_normal_workflows(self, test_python_script):
        """Test that normal workflow commands still work."""
        runner = CliRunner()
        # Try to list workflows - should still work
        result = runner.invoke(workflows, ["--help"])

        assert result.exit_code == 0
        assert "workflows" in result.output.lower() or "commands" in result.output.lower()

    def test_file_takes_precedence_over_workflow_name(
        self, test_python_script, tmp_path, monkeypatch
    ):
        """Test that an actual file takes precedence over a workflow name."""
        # Create a file named "secrets" which conflicts with builtin workflow
        secrets_script = tmp_path / "secrets.py"
        secrets_script.write_text(
            """
print("This is the secrets file, not the workflow!")
"""
        )

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(workflows, ["secrets.py"], catch_exceptions=False)

        # Should execute the file, not the workflow
        assert result.exit_code == 0
        # Note: Output goes directly to stdout, not captured by Click
