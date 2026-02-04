"""Tests for command mocking fixtures.

These tests verify that the command fixtures work correctly
and can be used to mock shell command execution in tests.
"""

import subprocess
from unittest.mock import MagicMock

import pytest

# MockCommandResponse is imported via pytest_plugins in conftest.py
from fixtures.command_fixtures import MockCommandResponse

from mcli.lib.shell.exceptions import CommandNotFoundError, CommandResult, CommandTimeoutError


class TestMockCommandResponse:
    """Tests for the MockCommandResponse dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        response = MockCommandResponse()
        assert response.returncode == 0
        assert response.stdout == ""
        assert response.stderr == ""
        assert response.duration_ms == 10.0
        assert response.exception is None

    def test_custom_values(self):
        """Test custom values are set correctly."""
        response = MockCommandResponse(
            returncode=1,
            stdout="output",
            stderr="error",
            duration_ms=100.0,
        )
        assert response.returncode == 1
        assert response.stdout == "output"
        assert response.stderr == "error"
        assert response.duration_ms == 100.0

    def test_to_result_creates_command_result(self):
        """Test to_result() creates a valid CommandResult."""
        response = MockCommandResponse(
            returncode=0,
            stdout="success",
            stderr="",
            duration_ms=50.0,
        )
        result = response.to_result(["test", "command"])

        assert isinstance(result, CommandResult)
        assert result.returncode == 0
        assert result.stdout == "success"
        assert result.stderr == ""
        assert result.command == ["test", "command"]
        assert result.duration_ms == 50.0

    def test_to_result_with_default_command(self):
        """Test to_result() uses default command when none provided."""
        response = MockCommandResponse()
        result = response.to_result()

        assert result.command == ["mocked", "command"]


class TestMockCommandSuccess:
    """Tests for the mock_command_success fixture."""

    def test_returns_success_response(self, mock_command_success):
        """Test fixture provides successful command response."""
        assert mock_command_success.returncode == 0
        assert "successfully" in mock_command_success.stdout.lower()
        assert mock_command_success.stderr == ""
        assert mock_command_success.exception is None


class TestMockCommandFailure:
    """Tests for the mock_command_failure fixture."""

    def test_returns_failure_response(self, mock_command_failure):
        """Test fixture provides failed command response."""
        assert mock_command_failure.returncode == 1
        assert mock_command_failure.stdout == ""
        assert "error" in mock_command_failure.stderr.lower()


class TestMockCommandTimeout:
    """Tests for the mock_command_timeout fixture."""

    def test_returns_timeout_response(self, mock_command_timeout):
        """Test fixture provides timeout command response."""
        assert mock_command_timeout.returncode == -1
        assert "timed out" in mock_command_timeout.stderr.lower()
        assert isinstance(mock_command_timeout.exception, CommandTimeoutError)


class TestMockCommandNotFound:
    """Tests for the mock_command_not_found fixture."""

    def test_returns_not_found_response(self, mock_command_not_found):
        """Test fixture provides command not found response."""
        assert mock_command_not_found.returncode == 127
        assert "not found" in mock_command_not_found.stderr.lower()
        assert isinstance(mock_command_not_found.exception, CommandNotFoundError)


class TestMockSubprocessRun:
    """Tests for the mock_subprocess_run fixture."""

    def test_can_mock_subprocess_run(self, mock_subprocess_run):
        """Test fixture mocks subprocess.run correctly."""
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=["test"], returncode=0, stdout="mocked output", stderr=""
        )

        result = subprocess.run(["test"], capture_output=True, text=True)

        assert result.returncode == 0
        assert result.stdout == "mocked output"
        mock_subprocess_run.assert_called_once()


class TestMockSubprocessPopen:
    """Tests for the mock_subprocess_popen fixture."""

    def test_can_mock_subprocess_popen(self, mock_subprocess_popen):
        """Test fixture mocks subprocess.Popen correctly."""
        process_mock = MagicMock()
        process_mock.communicate.return_value = ("stdout", "stderr")
        process_mock.returncode = 0
        mock_subprocess_popen.return_value = process_mock

        proc = subprocess.Popen(["test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()

        assert stdout == "stdout"
        assert stderr == "stderr"
        assert proc.returncode == 0
        mock_subprocess_popen.assert_called_once()


class TestCommandResponseFactory:
    """Tests for the command_response_factory fixture."""

    def test_creates_custom_response(self, command_response_factory):
        """Test factory creates custom responses."""
        response = command_response_factory(
            returncode=42,
            stdout="custom output",
            stderr="custom error",
            duration_ms=123.45,
        )

        assert response.returncode == 42
        assert response.stdout == "custom output"
        assert response.stderr == "custom error"
        assert response.duration_ms == 123.45

    def test_creates_response_with_exception(self, command_response_factory):
        """Test factory can include exceptions."""
        exc = ValueError("test error")
        response = command_response_factory(exception=exc)

        assert response.exception is exc


class TestMockGitCommands:
    """Tests for the mock_git_commands fixture."""

    def test_mocks_git_status(self, mock_git_commands):
        """Test git status is mocked correctly."""
        result = subprocess.run(["git", "status"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "main" in result.stdout

    def test_mocks_git_branch(self, mock_git_commands):
        """Test git branch is mocked correctly."""
        result = subprocess.run(["git", "branch"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "main" in result.stdout
        assert "develop" in result.stdout

    def test_mocks_git_log(self, mock_git_commands):
        """Test git log is mocked correctly."""
        result = subprocess.run(["git", "log"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "commit" in result.stdout.lower()


class TestMockCliCommand:
    """Tests for the mock_cli_command fixture."""

    def test_configure_sets_values(self, mock_cli_command):
        """Test configure method sets values correctly."""
        mock_cli_command.configure(exit_code=1, output="error output")

        assert mock_cli_command.exit_code == 1
        assert mock_cli_command.output == "error output"

    def test_records_calls(self, mock_cli_command):
        """Test call recording works."""
        mock_cli_command.record_call("arg1", "arg2", key="value")

        assert mock_cli_command.call_count == 1
        assert mock_cli_command.last_call == {"args": ("arg1", "arg2"), "kwargs": {"key": "value"}}

    def test_multiple_calls_tracked(self, mock_cli_command):
        """Test multiple calls are tracked."""
        mock_cli_command.record_call("first")
        mock_cli_command.record_call("second")

        assert mock_cli_command.call_count == 2
        assert mock_cli_command.last_call["args"] == ("second",)


class TestCaptureCommands:
    """Tests for the capture_commands fixture."""

    def test_captures_subprocess_run(self, capture_commands):
        """Test captures subprocess.run commands."""
        with capture_commands:
            subprocess.run(["echo", "hello"])
            subprocess.run(["ls", "-la"])

        assert len(capture_commands.commands) == 2
        assert capture_commands.commands[0] == ["echo", "hello"]
        assert capture_commands.commands[1] == ["ls", "-la"]

    def test_clear_removes_captured(self, capture_commands):
        """Test clear removes captured commands."""
        with capture_commands:
            subprocess.run(["test"])
            capture_commands.clear()

        assert len(capture_commands.commands) == 0
