"""Fixtures for mocking command execution in tests.

These fixtures provide easy ways to mock subprocess calls, shell commands,
and command results without actually executing anything on the system.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from mcli.lib.shell.exceptions import (
    CommandError,
    CommandFailedError,
    CommandNotFoundError,
    CommandResult,
    CommandTimeoutError,
)


@dataclass
class MockCommandResponse:
    """Configurable mock response for command execution."""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 10.0
    exception: Optional[Exception] = None

    def to_result(self, command: Optional[list[str]] = None) -> CommandResult:
        """Convert to a CommandResult object."""
        return CommandResult(
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            command=command or ["mocked", "command"],
            duration_ms=self.duration_ms,
        )


@pytest.fixture
def mock_command_success():
    """Fixture that provides a successful command response."""
    return MockCommandResponse(
        returncode=0,
        stdout="Command executed successfully",
        stderr="",
        duration_ms=15.0,
    )


@pytest.fixture
def mock_command_failure():
    """Fixture that provides a failed command response."""
    return MockCommandResponse(
        returncode=1,
        stdout="",
        stderr="Error: Command failed",
        duration_ms=5.0,
    )


@pytest.fixture
def mock_command_timeout():
    """Fixture that provides a timeout command response."""
    return MockCommandResponse(
        returncode=-1,
        stdout="",
        stderr="Command timed out",
        duration_ms=30000.0,
        exception=CommandTimeoutError(30, ["test", "command"]),
    )


@pytest.fixture
def mock_command_not_found():
    """Fixture that provides a command not found response."""
    return MockCommandResponse(
        returncode=127,
        stdout="",
        stderr="command not found: nonexistent",
        exception=CommandNotFoundError("nonexistent"),
    )


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing command execution.

    Usage:
        def test_example(mock_subprocess_run):
            mock_subprocess_run.return_value = subprocess.CompletedProcess(
                args=["test"], returncode=0, stdout="output", stderr=""
            )
            # ... test code that uses subprocess.run
    """
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_popen():
    """Mock subprocess.Popen for testing async command execution.

    Usage:
        def test_example(mock_subprocess_popen):
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("stdout", "stderr")
            process_mock.returncode = 0
            mock_subprocess_popen.return_value = process_mock
            # ... test code that uses subprocess.Popen
    """
    with patch("subprocess.Popen") as mock_popen:
        yield mock_popen


@pytest.fixture
def mock_shell_exec():
    """Mock the shell_exec function from mcli.lib.shell.shell.

    Usage:
        def test_example(mock_shell_exec):
            mock_shell_exec.return_value = {"success": True, "stdout": "output"}
            # ... test code that uses shell_exec
    """
    with patch("mcli.lib.shell.shell.shell_exec") as mock:
        yield mock


@pytest.fixture
def mock_execute_os_command():
    """Mock the execute_os_command function.

    Usage:
        def test_example(mock_execute_os_command):
            mock_execute_os_command.return_value = (0, "output", "")
            # ... test code that uses execute_os_command
    """
    with patch("mcli.lib.shell.shell.execute_os_command") as mock:
        yield mock


@pytest.fixture
def mock_execute_command_safe():
    """Mock the execute_command_safe function.

    Usage:
        def test_example(mock_execute_command_safe):
            mock_execute_command_safe.return_value = CommandResult(...)
            # ... test code that uses execute_command_safe
    """
    with patch("mcli.lib.shell.shell.execute_command_safe") as mock:
        yield mock


@pytest.fixture
def command_response_factory():
    """Factory fixture to create custom command responses.

    Usage:
        def test_example(command_response_factory):
            response = command_response_factory(
                returncode=0,
                stdout="custom output",
                stderr=""
            )
            # use response.to_result() to get a CommandResult
    """

    def factory(
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        duration_ms: float = 10.0,
        exception: Optional[Exception] = None,
    ) -> MockCommandResponse:
        return MockCommandResponse(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            exception=exception,
        )

    return factory


@pytest.fixture
def mock_git_commands(mock_subprocess_run):
    """Pre-configured mock for common git commands.

    Usage:
        def test_example(mock_git_commands):
            # Git commands will return predefined responses
            result = subprocess.run(["git", "status"], ...)
    """
    import subprocess

    def git_side_effect(args, **kwargs):
        # Convert args to a space-separated command string for matching
        if isinstance(args, (list, tuple)):
            cmd = " ".join(args)
        else:
            cmd = str(args)

        responses = {
            "git status": subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="On branch main\nnothing to commit, working tree clean",
                stderr="",
            ),
            "git branch": subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="* main\n  develop\n  feature/test",
                stderr="",
            ),
            "git log": subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="commit abc1234 (HEAD -> main) Latest commit\ncommit def5678 Previous commit",
                stderr="",
            ),
            "git diff": subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="",
                stderr="",
            ),
        }

        # Find matching command
        for pattern, response in responses.items():
            if cmd.startswith(pattern):
                return response

        # Default response
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    mock_subprocess_run.side_effect = git_side_effect
    return mock_subprocess_run


@pytest.fixture
def mock_cli_command():
    """Mock for Click CLI command invocation.

    Usage:
        def test_example(cli_runner, mock_cli_command):
            mock_cli_command.configure(exit_code=0, output="Success")
            result = cli_runner.invoke(my_command)
    """

    class MockCliCommand:
        def __init__(self):
            self.exit_code = 0
            self.output = ""
            self.exception = None
            self._calls = []

        def configure(
            self,
            exit_code: int = 0,
            output: str = "",
            exception: Optional[Exception] = None,
        ):
            self.exit_code = exit_code
            self.output = output
            self.exception = exception

        def record_call(self, *args, **kwargs):
            self._calls.append({"args": args, "kwargs": kwargs})

        @property
        def call_count(self):
            return len(self._calls)

        @property
        def last_call(self):
            return self._calls[-1] if self._calls else None

    return MockCliCommand()


@pytest.fixture
def capture_commands():
    """Fixture to capture executed commands without running them.

    Usage:
        def test_example(capture_commands):
            # Code that would normally run commands
            # ...
            assert len(capture_commands.commands) == 2
            assert "git" in capture_commands.commands[0]
    """

    class CommandCapture:
        def __init__(self):
            self.commands: list[list[str]] = []
            self._patches = []

        def _capture(self, args, **kwargs):
            self.commands.append(args if isinstance(args, list) else [args])
            return MagicMock(returncode=0, stdout="", stderr="")

        def __enter__(self):
            import subprocess

            self._patches.append(patch.object(subprocess, "run", side_effect=self._capture))
            self._patches.append(patch.object(subprocess, "Popen", side_effect=self._capture))
            for p in self._patches:
                p.start()
            return self

        def __exit__(self, *args):
            for p in self._patches:
                p.stop()

        def clear(self):
            self.commands = []

    return CommandCapture()
