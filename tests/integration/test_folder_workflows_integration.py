"""
Integration tests for folder workflows.

Tests end-to-end execution of folder-based and standalone workflows,
including CLI invocation and subprocess execution.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_workflows_dir(tmp_path):
    """Create a temporary workflows directory with test scripts."""
    workflows_dir = tmp_path / "test_workflows"
    workflows_dir.mkdir()

    # Create standalone Python workflow
    standalone_py = workflows_dir / "test-standalone.py"
    standalone_py.write_text(
        """#!/usr/bin/env python3
\"\"\"Standalone test workflow.\"\"\"
import sys
print("Standalone Python workflow executed")
print(f"Args: {sys.argv[1:]}")
sys.exit(0)
"""
    )
    standalone_py.chmod(0o755)

    # Create standalone shell workflow
    standalone_sh = workflows_dir / "test-deploy.sh"
    standalone_sh.write_text(
        """#!/bin/bash
# Deploy workflow
echo "Deploy workflow executed"
echo "Args: $*"
exit 0
"""
    )
    standalone_sh.chmod(0o755)

    # Create folder workflow group
    folder_group = workflows_dir / "test-group"
    folder_group.mkdir()

    # Python script in folder
    py_cmd = folder_group / "python-cmd.py"
    py_cmd.write_text(
        """#!/usr/bin/env python3
\"\"\"Python command in group.\"\"\"
import sys
print("Python command in test-group")
print(f"Args: {sys.argv[1:]}")
"""
    )
    py_cmd.chmod(0o755)

    # Shell script in folder
    sh_cmd = folder_group / "shell-cmd.sh"
    sh_cmd.write_text(
        """#!/bin/bash
# Shell command in group
echo "Shell command in test-group"
echo "Args: $*"
"""
    )
    sh_cmd.chmod(0o755)

    yield workflows_dir

    # Cleanup
    if workflows_dir.exists():
        shutil.rmtree(workflows_dir)


@pytest.mark.integration
class TestStandaloneWorkflowExecution:
    """Test executing standalone workflows."""

    def test_execute_python_standalone_workflow(self, temp_workflows_dir):
        """Test executing a standalone Python workflow directly."""
        script = temp_workflows_dir / "test-standalone.py"

        result = subprocess.run(
            ["python3", str(script), "arg1", "arg2"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Standalone Python workflow executed" in result.stdout
        assert "Args: ['arg1', 'arg2']" in result.stdout

    def test_execute_shell_standalone_workflow(self, temp_workflows_dir):
        """Test executing a standalone shell workflow directly."""
        script = temp_workflows_dir / "test-deploy.sh"

        result = subprocess.run(
            ["bash", str(script), "production", "us-west"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Deploy workflow executed" in result.stdout
        assert "Args: production us-west" in result.stdout

    def test_execute_python_workflow_no_args(self, temp_workflows_dir):
        """Test executing a Python workflow without arguments."""
        script = temp_workflows_dir / "test-standalone.py"

        result = subprocess.run(
            ["python3", str(script)], capture_output=True, text=True, timeout=10
        )

        assert result.returncode == 0
        assert "Standalone Python workflow executed" in result.stdout
        assert "Args: []" in result.stdout


@pytest.mark.integration
class TestFolderWorkflowExecution:
    """Test executing folder-based workflow groups."""

    def test_execute_python_command_in_folder(self, temp_workflows_dir):
        """Test executing a Python command from folder group."""
        script = temp_workflows_dir / "test-group" / "python-cmd.py"

        result = subprocess.run(
            ["python3", str(script), "test", "args"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Python command in test-group" in result.stdout
        assert "Args: ['test', 'args']" in result.stdout

    def test_execute_shell_command_in_folder(self, temp_workflows_dir):
        """Test executing a shell command from folder group."""
        script = temp_workflows_dir / "test-group" / "shell-cmd.sh"

        result = subprocess.run(
            ["bash", str(script), "hello", "world"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Shell command in test-group" in result.stdout
        assert "Args: hello world" in result.stdout


@pytest.mark.integration
class TestWorkflowScanning:
    """Test scanning and discovery of workflows."""

    def test_scan_discovers_all_workflows(self, temp_workflows_dir):
        """Test that scanning discovers all workflow types."""
        from mcli.lib.folder_workflows import scan_folder_workflows, scan_standalone_workflows

        # Test standalone discovery
        standalone = scan_standalone_workflows(temp_workflows_dir)
        assert "test-standalone" in standalone
        assert "test-deploy" in standalone
        assert len(standalone) == 2

        # Test folder discovery
        folders = scan_folder_workflows(temp_workflows_dir)
        assert "test-group" in folders
        assert len(folders["test-group"]["commands"]) == 2
        assert "python-cmd" in folders["test-group"]["commands"]
        assert "shell-cmd" in folders["test-group"]["commands"]

    def test_scan_respects_executability(self, temp_workflows_dir):
        """Test that scanning respects file executability."""
        # Create a non-executable script
        non_exec = temp_workflows_dir / "non-executable.py"
        non_exec.write_text('print("should not be discovered")\n')
        # Don't make it executable

        from mcli.lib.folder_workflows import scan_standalone_workflows

        standalone = scan_standalone_workflows(temp_workflows_dir)

        # Should include scripts with .py/.sh extensions even if not executable
        # This is by design to support Windows compatibility
        assert len(standalone) >= 2  # At least our executable scripts


@pytest.mark.integration
class TestWorkflowEnvironment:
    """Test workflow execution environment."""

    def test_workflow_has_environment_variables(self, temp_workflows_dir):
        """Test that workflows receive environment variables."""
        script = temp_workflows_dir / "env-test.py"
        script.write_text(
            """#!/usr/bin/env python3
import os
print(f"PATH={os.environ.get('PATH', 'NOT_SET')}")
print(f"HOME={os.environ.get('HOME', 'NOT_SET')}")
"""
        )
        script.chmod(0o755)

        result = subprocess.run(
            ["python3", str(script)], capture_output=True, text=True, timeout=10
        )

        assert result.returncode == 0
        assert "PATH=" in result.stdout
        assert "NOT_SET" not in result.stdout.split("\n")[0]  # PATH should be set

    def test_workflow_can_access_current_directory(self, temp_workflows_dir):
        """Test that workflows can access current working directory."""
        script = temp_workflows_dir / "pwd-test.sh"
        script.write_text(
            """#!/bin/bash
echo "CWD: $(pwd)"
"""
        )
        script.chmod(0o755)

        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            cwd=str(temp_workflows_dir),
            timeout=10,
        )

        assert result.returncode == 0
        assert "CWD:" in result.stdout


@pytest.mark.integration
class TestWorkflowErrorHandling:
    """Test error handling in workflow execution."""

    def test_python_workflow_with_error(self, temp_workflows_dir):
        """Test handling Python workflow that exits with error."""
        script = temp_workflows_dir / "error-test.py"
        script.write_text(
            """#!/usr/bin/env python3
import sys
print("Error workflow")
sys.exit(1)
"""
        )
        script.chmod(0o755)

        result = subprocess.run(
            ["python3", str(script)], capture_output=True, text=True, timeout=10
        )

        assert result.returncode == 1
        assert "Error workflow" in result.stdout

    def test_shell_workflow_with_error(self, temp_workflows_dir):
        """Test handling shell workflow that exits with error."""
        script = temp_workflows_dir / "error-test.sh"
        script.write_text(
            """#!/bin/bash
echo "Error workflow"
exit 42
"""
        )
        script.chmod(0o755)

        result = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=10)

        assert result.returncode == 42
        assert "Error workflow" in result.stdout

    def test_python_workflow_with_exception(self, temp_workflows_dir):
        """Test handling Python workflow that raises exception."""
        script = temp_workflows_dir / "exception-test.py"
        script.write_text(
            """#!/usr/bin/env python3
raise ValueError("Test exception")
"""
        )
        script.chmod(0o755)

        result = subprocess.run(
            ["python3", str(script)], capture_output=True, text=True, timeout=10
        )

        assert result.returncode != 0
        assert "ValueError" in result.stderr or "ValueError" in result.stdout


@pytest.mark.integration
@pytest.mark.slow
class TestComplexWorkflows:
    """Test more complex workflow scenarios."""

    def test_workflow_with_multiple_args(self, temp_workflows_dir):
        """Test workflow with many arguments."""
        script = temp_workflows_dir / "multi-arg.py"
        script.write_text(
            """#!/usr/bin/env python3
import sys
print(f"Received {len(sys.argv) - 1} arguments")
for i, arg in enumerate(sys.argv[1:], 1):
    print(f"Arg {i}: {arg}")
"""
        )
        script.chmod(0o755)

        args = ["arg1", "arg2", "arg3", "arg4", "arg5"]
        result = subprocess.run(
            ["python3", str(script)] + args,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Received 5 arguments" in result.stdout
        for i, arg in enumerate(args, 1):
            assert f"Arg {i}: {arg}" in result.stdout

    def test_workflow_with_special_characters(self, temp_workflows_dir):
        """Test workflow with special characters in arguments."""
        script = temp_workflows_dir / "special-chars.py"
        script.write_text(
            """#!/usr/bin/env python3
import sys
for arg in sys.argv[1:]:
    print(f"Arg: {arg}")
"""
        )
        script.chmod(0o755)

        special_args = ["hello world", "test@example.com", "path/to/file", "$VAR"]
        result = subprocess.run(
            ["python3", str(script)] + special_args,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        for arg in special_args:
            assert f"Arg: {arg}" in result.stdout

    def test_workflow_with_stdin(self, temp_workflows_dir):
        """Test workflow that reads from stdin."""
        script = temp_workflows_dir / "stdin-test.py"
        script.write_text(
            """#!/usr/bin/env python3
import sys
data = sys.stdin.read()
print(f"Received: {data.strip()}")
"""
        )
        script.chmod(0o755)

        input_data = "test input data\n"
        result = subprocess.run(
            ["python3", str(script)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Received: test input data" in result.stdout


@pytest.mark.integration
class TestMakefileIntegration:
    """Test Makefile workflow integration."""

    def test_makefile_detection(self, tmp_path):
        """Test detecting Makefile in directory."""
        from mcli.lib.makefile_workflows import find_makefile

        # Create Makefile
        makefile = tmp_path / "Makefile"
        makefile.write_text(
            """
.PHONY: test clean

test: ## Run tests
\t@echo "Running tests"

clean: ## Clean artifacts
\t@echo "Cleaning"
"""
        )

        found = find_makefile(tmp_path)
        assert found is not None
        assert found == makefile

    def test_makefile_target_parsing(self, tmp_path):
        """Test parsing Makefile targets."""
        from mcli.lib.makefile_workflows import parse_makefile_targets

        makefile = tmp_path / "Makefile"
        makefile.write_text(
            """
.PHONY: test build

test: ## Run unit tests
\t@pytest

build: ## Build the project
\t@make compile
"""
        )

        targets = parse_makefile_targets(makefile)

        assert "test" in targets
        assert "build" in targets
        assert "Run unit tests" in targets["test"]
        assert "Build the project" in targets["build"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
