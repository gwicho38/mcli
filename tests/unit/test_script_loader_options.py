"""
Unit tests for script_loader option passthrough.

Tests that shell scripts receive all arguments including options like -w, --option, etc.
This fixes the bug where `mcli run -g clawdbot -w /path logs` would fail because
Click was trying to parse -w as an option instead of passing it through to the script.
"""

import stat
import tempfile
from pathlib import Path

import click
from click.testing import CliRunner

from mcli.lib.script_loader import ScriptLoader


class TestShellCommandOptionPassthrough:
    """Test that shell commands receive all arguments including options."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = Path(self.temp_dir) / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.loader = ScriptLoader(self.workflows_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_shell_script(self, name: str, content: str) -> Path:
        """Create a shell script file."""
        script_path = self.workflows_dir / f"{name}.sh"
        script_path.write_text(content)
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
        return script_path

    def test_shell_command_passes_option_arguments(self):
        """Test that shell commands receive option-like arguments (-w, --foo)."""
        # Create a script that echoes all arguments
        script_content = """#!/usr/bin/env bash
# @description: Test script that echoes arguments
echo "ARGS: $@"
"""
        script_path = self._create_shell_script("test_options", script_content)

        # Load the command
        command = self.loader.load_shell_command(
            script_path,
            {"description": "Test script", "shell": "bash"},
        )

        # Create a test group with the command
        @click.group()
        def cli():
            pass

        cli.add_command(command, name="test_options")

        # Run with option-like arguments
        runner = CliRunner()
        result = runner.invoke(cli, ["test_options", "-w", "/some/path", "logs"])

        # The script should receive all arguments including -w
        assert result.exit_code == 0
        assert "-w" in result.output
        assert "/some/path" in result.output
        assert "logs" in result.output

    def test_shell_command_passes_long_options(self):
        """Test that shell commands receive long options (--workspace)."""
        script_content = """#!/usr/bin/env bash
# @description: Test script that echoes arguments
echo "ARGS: $@"
"""
        script_path = self._create_shell_script("test_long_opts", script_content)

        command = self.loader.load_shell_command(
            script_path,
            {"description": "Test script", "shell": "bash"},
        )

        @click.group()
        def cli():
            pass

        cli.add_command(command, name="test_long_opts")

        runner = CliRunner()
        result = runner.invoke(cli, ["test_long_opts", "--workspace", "/my/project", "status"])

        assert result.exit_code == 0
        assert "--workspace" in result.output
        assert "/my/project" in result.output
        assert "status" in result.output

    def test_shell_command_mixed_args_and_options(self):
        """Test that shell commands receive mixed positional args and options."""
        script_content = """#!/usr/bin/env bash
# @description: Test script
echo "ARGS: $@"
"""
        script_path = self._create_shell_script("test_mixed", script_content)

        command = self.loader.load_shell_command(
            script_path,
            {"description": "Test script", "shell": "bash"},
        )

        @click.group()
        def cli():
            pass

        cli.add_command(command, name="test_mixed")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["test_mixed", "subcommand", "-v", "--output", "file.txt", "arg1"]
        )

        assert result.exit_code == 0
        output = result.output
        assert "subcommand" in output
        assert "-v" in output
        assert "--output" in output
        assert "file.txt" in output
        assert "arg1" in output


class TestPythonVenvCommandOptionPassthrough:
    """Test that Python venv commands receive all arguments including options."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = Path(self.temp_dir) / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.loader = ScriptLoader(self.workflows_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_python_venv_command_context_settings(self):
        """Test that Python venv commands have correct context settings."""
        script_path = self.workflows_dir / "test_py.py"
        script_path.write_text(
            """#!/usr/bin/env python
# @description: Test Python script
# @requires: requests
import sys
print(f"ARGS: {sys.argv[1:]}")
"""
        )

        # Load the command using _load_python_with_deps
        command = self.loader._load_python_with_deps(
            script_path,
            {"description": "Test script", "requires": ["requests"]},
        )

        # Verify context settings
        assert command.context_settings is not None
        assert command.context_settings.get("ignore_unknown_options") is True
        assert command.context_settings.get("allow_extra_args") is True
        assert command.context_settings.get("allow_interspersed_args") is False


class TestBunCommandOptionPassthrough:
    """Test that Bun commands receive all arguments including options."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = Path(self.temp_dir) / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.loader = ScriptLoader(self.workflows_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bun_command_context_settings(self):
        """Test that Bun commands have correct context settings."""
        script_path = self.workflows_dir / "test_js.js"
        script_path.write_text(
            """#!/usr/bin/env bun
// @description: Test JavaScript script
console.log("ARGS:", process.argv.slice(2));
"""
        )

        command = self.loader.load_bun_command(
            script_path,
            {"description": "Test script"},
        )

        # Verify context settings
        assert command.context_settings is not None
        assert command.context_settings.get("ignore_unknown_options") is True
        assert command.context_settings.get("allow_extra_args") is True
        assert command.context_settings.get("allow_interspersed_args") is False
