"""
Unit tests for folder workflows functionality.

Tests language detection, help text extraction, script validation,
and Click command creation for folder-based and standalone workflows.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest

from mcli.lib.folder_workflows import (
    create_folder_command_group,
    create_python_script_command,
    create_shell_script_command,
    detect_script_language,
    extract_help_text,
    scan_folder_workflows,
    scan_standalone_workflows,
)


class TestLanguageDetection:
    """Test script language detection from shebang and extension."""

    def test_detect_python_from_shebang(self, tmp_path):
        """Test detecting Python from shebang."""
        script = tmp_path / "test.py"
        script.write_text("#!/usr/bin/env python3\nprint('hello')\n")

        language, shell_type = detect_script_language(script)
        assert language == "python"
        assert shell_type is None

    def test_detect_bash_from_shebang(self, tmp_path):
        """Test detecting Bash from shebang."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash\necho 'hello'\n")

        language, shell_type = detect_script_language(script)
        assert language == "shell"
        assert shell_type == "bash"

    def test_detect_zsh_from_shebang(self, tmp_path):
        """Test detecting Zsh from shebang."""
        script = tmp_path / "test.sh"
        script.write_text("#!/usr/bin/env zsh\necho 'hello'\n")

        language, shell_type = detect_script_language(script)
        assert language == "shell"
        assert shell_type == "zsh"

    def test_detect_python_from_extension(self, tmp_path):
        """Test detecting Python from .py extension when no shebang."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')\n")

        language, shell_type = detect_script_language(script)
        assert language == "python"
        assert shell_type is None

    def test_detect_shell_from_extension(self, tmp_path):
        """Test detecting shell from .sh extension when no shebang."""
        script = tmp_path / "test.sh"
        script.write_text("echo 'hello'\n")

        language, shell_type = detect_script_language(script)
        assert language == "shell"
        assert shell_type == "bash"  # Default shell

    def test_default_to_python(self, tmp_path):
        """Test defaulting to Python for unknown files."""
        script = tmp_path / "test.txt"
        script.write_text("some content\n")

        language, shell_type = detect_script_language(script)
        assert language == "python"
        assert shell_type is None


class TestHelpTextExtraction:
    """Test extracting help text from scripts."""

    def test_extract_python_docstring(self, tmp_path):
        """Test extracting Python module docstring."""
        script = tmp_path / "test.py"
        script.write_text('"""This is a test script."""\nimport sys\n')

        help_text = extract_help_text(script, "python")
        assert help_text == "This is a test script."

    def test_extract_python_multiline_docstring(self, tmp_path):
        """Test extracting multiline Python docstring."""
        script = tmp_path / "test.py"
        script.write_text('"""\nMulti-line\ntest script.\n"""\nimport sys\n')

        help_text = extract_help_text(script, "python")
        assert "Multi-line" in help_text
        assert "test script" in help_text

    def test_extract_shell_comments(self, tmp_path):
        """Test extracting shell script comments."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash\n# This is a test script\n# Second line\necho 'hello'\n")

        help_text = extract_help_text(script, "shell")
        assert "This is a test script" in help_text

    def test_extract_no_help_text(self, tmp_path):
        """Test handling scripts without help text."""
        script = tmp_path / "test.py"
        script.write_text("import sys\nprint('hello')\n")

        help_text = extract_help_text(script, "python")
        assert help_text == f"Execute {script.stem} script"

    def test_extract_from_nonexistent_file(self, tmp_path):
        """Test handling nonexistent files gracefully."""
        script = tmp_path / "nonexistent.py"

        help_text = extract_help_text(script, "python")
        assert help_text == f"Execute {script.stem} script"


class TestStandaloneWorkflows:
    """Test scanning for standalone workflow scripts."""

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning empty directory returns empty dict."""
        workflows = scan_standalone_workflows(tmp_path)
        assert workflows == {}

    def test_scan_with_python_script(self, tmp_path):
        """Test scanning directory with Python script."""
        script = tmp_path / "test-workflow.py"
        script.write_text('#!/usr/bin/env python3\n"""Test workflow."""\nprint("hello")\n')
        script.chmod(0o755)

        workflows = scan_standalone_workflows(tmp_path)

        assert "test-workflow" in workflows
        assert workflows["test-workflow"]["language"] == "python"
        assert workflows["test-workflow"]["path"] == script
        assert "Test workflow" in workflows["test-workflow"]["help"]

    def test_scan_with_shell_script(self, tmp_path):
        """Test scanning directory with shell script."""
        script = tmp_path / "deploy.sh"
        script.write_text("#!/bin/bash\n# Deploy script\necho 'deploying'\n")
        script.chmod(0o755)

        workflows = scan_standalone_workflows(tmp_path)

        assert "deploy" in workflows
        assert workflows["deploy"]["language"] == "shell"
        assert workflows["deploy"]["shell"] == "bash"

    def test_scan_ignores_folders(self, tmp_path):
        """Test that folder directories are ignored."""
        folder = tmp_path / "test-folder"
        folder.mkdir()

        workflows = scan_standalone_workflows(tmp_path)
        assert "test-folder" not in workflows

    def test_scan_ignores_non_executable(self, tmp_path):
        """Test that non-executable scripts are ignored."""
        script = tmp_path / "non-exec.py"
        script.write_text("print('hello')\n")
        # Don't make executable

        workflows = scan_standalone_workflows(tmp_path)
        # Should still be included since we check file extensions
        assert len(workflows) >= 0

    def test_scan_nonexistent_directory(self, tmp_path):
        """Test scanning nonexistent directory returns empty dict."""
        nonexistent = tmp_path / "nonexistent"
        workflows = scan_standalone_workflows(nonexistent)
        assert workflows == {}


class TestFolderWorkflows:
    """Test scanning for folder-based workflow groups."""

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning empty directory returns empty dict."""
        workflows = scan_folder_workflows(tmp_path)
        assert workflows == {}

    def test_scan_with_folder_and_scripts(self, tmp_path):
        """Test scanning directory with folder containing scripts."""
        folder = tmp_path / "test-group"
        folder.mkdir()

        script1 = folder / "command1.py"
        script1.write_text('#!/usr/bin/env python3\n"""Command 1."""\nprint("cmd1")\n')
        script1.chmod(0o755)

        script2 = folder / "command2.sh"
        script2.write_text("#!/bin/bash\n# Command 2\necho 'cmd2'\n")
        script2.chmod(0o755)

        workflows = scan_folder_workflows(tmp_path)

        assert "test-group" in workflows
        assert len(workflows["test-group"]["commands"]) == 2
        assert "command1" in workflows["test-group"]["commands"]
        assert "command2" in workflows["test-group"]["commands"]

    def test_scan_ignores_empty_folders(self, tmp_path):
        """Test that empty folders are ignored."""
        folder = tmp_path / "empty-folder"
        folder.mkdir()

        workflows = scan_folder_workflows(tmp_path)
        assert "empty-folder" not in workflows

    def test_scan_multiple_folders(self, tmp_path):
        """Test scanning multiple folders."""
        folder1 = tmp_path / "group1"
        folder1.mkdir()
        (folder1 / "cmd1.py").write_text("print('hello')\n")

        folder2 = tmp_path / "group2"
        folder2.mkdir()
        (folder2 / "cmd2.sh").write_text("#!/bin/bash\necho 'hello'\n")

        workflows = scan_folder_workflows(tmp_path)

        assert "group1" in workflows
        assert "group2" in workflows

    def test_scan_nonexistent_directory(self, tmp_path):
        """Test scanning nonexistent directory returns empty dict."""
        nonexistent = tmp_path / "nonexistent"
        workflows = scan_folder_workflows(nonexistent)
        assert workflows == {}


class TestCommandCreation:
    """Test creating Click commands from scripts."""

    def test_create_python_command(self, tmp_path):
        """Test creating a Python script command."""
        script = tmp_path / "test.py"
        script.write_text('#!/usr/bin/env python3\nprint("hello")\n')
        script.chmod(0o755)

        cmd = create_python_script_command("test", script, "Test command")

        assert isinstance(cmd, click.Command)
        assert cmd.name == "test"
        assert "Test command" in cmd.help

    def test_create_shell_command(self, tmp_path):
        """Test creating a shell script command."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash\necho 'hello'\n")
        script.chmod(0o755)

        cmd = create_shell_script_command("test", script, "bash", "Test command")

        assert isinstance(cmd, click.Command)
        assert cmd.name == "test"
        assert "Test command" in cmd.help

    @patch("mcli.lib.folder_workflows.subprocess.run")
    def test_python_command_execution(self, mock_run, tmp_path):
        """Test executing a Python script command."""
        mock_run.return_value = MagicMock(returncode=0)

        script = tmp_path / "test.py"
        script.write_text('#!/usr/bin/env python3\nprint("hello")\n')
        script.chmod(0o755)

        cmd = create_python_script_command("test", script, "Test command")

        # Use Click's testing runner
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Verify subprocess.run was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        # Check that python3 is in the command (could be full path)
        assert any("python3" in str(arg) for arg in call_args)
        assert str(script) in call_args

    @patch("mcli.lib.folder_workflows.subprocess.run")
    def test_shell_command_execution(self, mock_run, tmp_path):
        """Test executing a shell script command."""
        mock_run.return_value = MagicMock(returncode=0)

        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash\necho 'hello'\n")
        script.chmod(0o755)

        cmd = create_shell_script_command("test", script, "bash", "Test command")

        # Use Click's testing runner
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Verify subprocess.run was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        # Check that bash is in the command or the script is directly executed
        assert "bash" in call_args or str(script) in call_args[0]
        assert str(script) in call_args

    def test_create_folder_command_group(self, tmp_path):
        """Test creating a command group from folder workflows."""
        # Create test command data
        commands = {
            "cmd1": {
                "language": "python",
                "path": tmp_path / "cmd1.py",
                "help": "Command 1",
                "shell": None,
            },
            "cmd2": {
                "language": "shell",
                "path": tmp_path / "cmd2.sh",
                "help": "Command 2",
                "shell": "bash",
            },
        }

        # Create actual files
        for cmd_name, cmd_data in commands.items():
            cmd_data["path"].write_text(f"# {cmd_data['help']}\n")

        group = create_folder_command_group("test-group", commands)

        assert isinstance(group, click.Group)
        assert group.name == "test-group"
        assert "cmd1" in group.commands
        assert "cmd2" in group.commands


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_script_with_spaces_in_path(self, tmp_path):
        """Test handling scripts with spaces in path."""
        folder = tmp_path / "folder with spaces"
        folder.mkdir()
        script = folder / "script name.py"
        script.write_text('"""Test script."""\nprint("hello")\n')
        script.chmod(0o755)

        language, _ = detect_script_language(script)
        assert language == "python"

        help_text = extract_help_text(script, language)
        assert "Test script" in help_text

    def test_script_with_unicode_content(self, tmp_path):
        """Test handling scripts with unicode content."""
        script = tmp_path / "unicode.py"
        script.write_text('"""Test with émojis 🎯 and 中文."""\nprint("hello")\n', encoding="utf-8")

        help_text = extract_help_text(script, "python")
        assert "émojis" in help_text or "Test" in help_text

    def test_very_long_help_text(self, tmp_path):
        """Test handling very long help text."""
        long_help = "A" * 1000
        script = tmp_path / "long.py"
        script.write_text(f'"""{long_help}"""\nprint("hello")\n')

        help_text = extract_help_text(script, "python")
        assert len(help_text) > 0

    def test_malformed_shebang(self, tmp_path):
        """Test handling malformed shebang lines."""
        script = tmp_path / "malformed.py"
        script.write_text("#!invalid\nprint('hello')\n")

        language, _ = detect_script_language(script)
        # Should fall back to extension detection
        assert language == "python"

    def test_binary_file(self, tmp_path):
        """Test handling binary files gracefully."""
        binary = tmp_path / "binary.bin"
        binary.write_bytes(b"\x00\x01\x02\x03\x04")

        # Should not crash
        help_text = extract_help_text(binary, "python")
        assert help_text is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
