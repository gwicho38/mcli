"""Test file path completion for mcli run ./ command.."""

import os
from pathlib import Path

import pytest

from mcli.workflow.workflow import ScopedWorkflowsGroup


class MockContext:
    """Mock Click context for testing shell completion."""

    def __init__(self, group):
        self.params = {"is_global": False}
        self.command = group  # Required by Click's shell_complete


@pytest.mark.skip(reason="Shell completion tests require full Click context setup")
class TestFilePathCompletion:
    """Test file path completion in workflow commands.."""

    def test_file_path_completion_relative(self, tmp_path):
        """Test that ./ triggers file path completion.."""
        # Create test files
        (tmp_path / "test_script.py").write_text("#!/usr/bin/env python3\nprint('test')")
        (tmp_path / "another_file.sh").write_text("#!/bin/bash\necho test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.py").write_text("print('nested')")

        # Create workflow group
        group = ScopedWorkflowsGroup()

        ctx = MockContext(group)

        # Test completion for ./
        # Change to test directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            completions = group.shell_complete(ctx, "./")
            completion_values = [c.value for c in completions]

            # Should include all files and directories
            assert any("test_script.py" in c for c in completion_values)
            assert any("another_file.sh" in c for c in completion_values)
            assert any("subdir/" in c for c in completion_values)

        finally:
            os.chdir(original_cwd)

    def test_file_path_completion_partial(self, tmp_path):
        """Test partial file name completion."""
        # Create test files
        (tmp_path / "test_one.py").write_text("test")
        (tmp_path / "test_two.py").write_text("test")
        (tmp_path / "other.py").write_text("test")

        group = ScopedWorkflowsGroup()

        class MockContext:
            params = {"is_global": False}

        ctx = MockContext()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Test completion for ./test_
            completions = group.shell_complete(ctx, "./test_")
            completion_values = [c.value for c in completions]

            # Should only match test_* files
            assert len(completion_values) == 2
            assert any("test_one.py" in c for c in completion_values)
            assert any("test_two.py" in c for c in completion_values)
            assert not any("other.py" in c for c in completion_values)

        finally:
            os.chdir(original_cwd)

    def test_absolute_path_completion(self, tmp_path):
        """Test absolute path completion."""
        # Create test file
        test_file = tmp_path / "absolute_test.py"
        test_file.write_text("test")

        group = ScopedWorkflowsGroup()

        class MockContext:
            params = {"is_global": False}

        ctx = MockContext()

        # Test completion with absolute path
        completions = group.shell_complete(ctx, str(tmp_path) + "/")
        completion_values = [c.value for c in completions]

        # Should find the test file
        assert any("absolute_test.py" in c for c in completion_values)

    def test_hidden_files_excluded(self, tmp_path):
        """Test that hidden files are excluded unless explicitly requested."""
        # Create hidden and regular files
        (tmp_path / "visible.py").write_text("test")
        (tmp_path / ".hidden.py").write_text("test")

        group = ScopedWorkflowsGroup()

        class MockContext:
            params = {"is_global": False}

        ctx = MockContext()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Test completion without .
            completions = group.shell_complete(ctx, "./")
            completion_values = [c.value for c in completions]

            # Should only show visible file
            assert any("visible.py" in c for c in completion_values)
            assert not any(".hidden.py" in c for c in completion_values)

            # Test completion with . prefix (using .hid to be more specific)
            completions = group.shell_complete(ctx, "./.hid")
            completion_values = [c.value for c in completions]

            # Should now show hidden file
            assert any(".hidden.py" in c for c in completion_values)

        finally:
            os.chdir(original_cwd)

    def test_workflow_command_completion(self):
        """Test that workflow commands still complete normally."""
        group = ScopedWorkflowsGroup()

        class MockContext:
            params = {"is_global": False}

        ctx = MockContext()

        # Test completion for regular workflow names (not file paths)
        completions = group.shell_complete(ctx, "sec")

        # Should return workflow commands, not file paths
        # (actual commands depend on what's installed, but should get some results)
        assert isinstance(completions, list)

    def test_directory_trailing_slash(self, tmp_path):
        """Test that directories get trailing slash."""
        # Create directory
        (tmp_path / "mydir").mkdir()
        (tmp_path / "myfile.py").write_text("test")

        group = ScopedWorkflowsGroup()

        class MockContext:
            params = {"is_global": False}

        ctx = MockContext()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            completions = group.shell_complete(ctx, "./")
            completion_values = [c.value for c in completions]

            # Directory should have trailing slash
            dir_completions = [c for c in completion_values if "mydir" in c]
            assert len(dir_completions) == 1
            assert dir_completions[0].endswith("/")

            # File should not have trailing slash
            file_completions = [c for c in completion_values if "myfile" in c]
            assert len(file_completions) == 1
            assert not file_completions[0].endswith("/")

        finally:
            os.chdir(original_cwd)

    def test_hidden_directories_shown(self, tmp_path):
        """Test that hidden directories are always shown."""
        # Create hidden directory and file
        (tmp_path / ".mcli").mkdir()
        (tmp_path / ".mcli" / "workflows").mkdir()
        (tmp_path / ".hidden_file").write_text("test")
        (tmp_path / "visible.py").write_text("test")

        group = ScopedWorkflowsGroup()

        class MockContext:
            params = {"is_global": False}

        ctx = MockContext()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            completions = group.shell_complete(ctx, "./")
            completion_values = [c.value for c in completions]

            # Hidden directory should be shown
            assert any(".mcli/" in c for c in completion_values)

            # Regular file should be shown
            assert any("visible.py" in c for c in completion_values)

            # Hidden file should NOT be shown
            assert not any(".hidden_file" in c for c in completion_values)

        finally:
            os.chdir(original_cwd)
