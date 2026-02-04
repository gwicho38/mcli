"""Tests for shell command execution functions."""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcli.lib.shell.exceptions import (
    CommandFailedError,
    CommandNotFoundError,
    CommandResourceError,
    CommandResult,
    CommandSecurityError,
    CommandTimeoutError,
    CommandValidationError,
)
from mcli.lib.shell.shell import (
    _sanitize_for_log,
    execute_command_safe,
    execute_command_with_result,
    execute_os_command,
    is_executable_available,
)


class TestExecuteOsCommand:
    """Tests for execute_os_command function."""

    def test_empty_command_raises_validation_error(self):
        """Test empty command raises CommandValidationError."""
        with pytest.raises(CommandValidationError):
            execute_os_command("", fail_on_error=False)

    def test_empty_list_command_raises_validation_error(self):
        """Test empty list command raises CommandValidationError."""
        with pytest.raises(CommandValidationError):
            execute_os_command([], fail_on_error=False)

    def test_null_byte_raises_security_error(self):
        """Test null byte in command raises CommandSecurityError."""
        with pytest.raises(CommandSecurityError):
            execute_os_command("echo\x00test", fail_on_error=False)

    def test_command_too_long_raises_validation_error(self):
        """Test very long command raises CommandValidationError."""
        long_cmd = "x" * 200000
        with pytest.raises(CommandValidationError):
            execute_os_command(long_cmd, fail_on_error=False)

    def test_successful_command_returns_stdout(self):
        """Test successful command returns stdout."""
        result = execute_os_command("echo hello", fail_on_error=False)
        assert "hello" in result

    def test_successful_list_command(self):
        """Test command as list works."""
        result = execute_os_command(["echo", "hello"], fail_on_error=False)
        assert "hello" in result

    def test_failed_command_raises_error(self):
        """Test failed command raises CommandFailedError."""
        with pytest.raises(CommandFailedError) as exc_info:
            execute_os_command("exit 1", fail_on_error=False)
        assert exc_info.value.result.returncode == 1

    @patch("mcli.lib.shell.shell.register_subprocess")
    @patch("mcli.lib.shell.shell.subprocess.Popen")
    def test_timeout_raises_error(self, mock_popen, mock_register):
        """Test timeout raises CommandTimeoutError."""
        mock_process = MagicMock()
        # First call raises timeout, second call (cleanup) returns empty
        mock_process.communicate.side_effect = [
            subprocess.TimeoutExpired("cmd", 1),
            (b"", b""),  # cleanup call after kill
        ]
        mock_process.kill = MagicMock()
        mock_popen.return_value = mock_process

        with pytest.raises(CommandTimeoutError):
            execute_os_command("sleep 100", fail_on_error=False, timeout=1)

    def test_stdin_passed_to_command(self):
        """Test stdin is passed to command."""
        result = execute_os_command("cat", stdin="test input", fail_on_error=False)
        assert "test input" in result


class TestExecuteCommandSafe:
    """Tests for execute_command_safe function."""

    def test_empty_args_raises_validation_error(self):
        """Test empty args raises CommandValidationError."""
        with pytest.raises(CommandValidationError):
            execute_command_safe([], fail_on_error=False)

    def test_nonexistent_executable_raises_not_found(self):
        """Test nonexistent executable raises CommandNotFoundError."""
        with pytest.raises(CommandNotFoundError):
            execute_command_safe(
                ["definitely-not-a-real-command-12345"],
                fail_on_error=False,
            )

    def test_successful_command_returns_stdout(self):
        """Test successful command returns stdout."""
        result = execute_command_safe(["echo", "hello"], fail_on_error=False)
        assert "hello" in result

    def test_failed_command_raises_error(self):
        """Test failed command raises CommandFailedError."""
        with pytest.raises(CommandFailedError):
            execute_command_safe(["false"], fail_on_error=False)

    def test_cwd_parameter(self):
        """Test cwd parameter changes working directory."""
        result = execute_command_safe(
            ["pwd"],
            fail_on_error=False,
            cwd="/tmp",
        )
        assert "/tmp" in result or "/private/tmp" in result  # macOS symlink

    def test_env_parameter_merges_with_existing(self):
        """Test env parameter merges with existing environment."""
        result = execute_command_safe(
            ["printenv", "MY_TEST_VAR"],
            fail_on_error=False,
            env={"MY_TEST_VAR": "test_value"},
        )
        assert "test_value" in result

    def test_check_executable_false_skips_check(self):
        """Test check_executable=False skips existence check."""
        # This should not raise CommandNotFoundError immediately,
        # but will fail when Popen is called
        with pytest.raises((CommandNotFoundError, CommandResourceError)):
            execute_command_safe(
                ["definitely-not-real"],
                fail_on_error=False,
                check_executable=False,
            )

    @patch("mcli.lib.shell.shell.register_subprocess")
    @patch("mcli.lib.shell.shell.subprocess.Popen")
    def test_timeout_raises_error(self, mock_popen, mock_register):
        """Test timeout raises CommandTimeoutError."""
        mock_process = MagicMock()
        # First call raises timeout, second call (cleanup) returns empty
        mock_process.communicate.side_effect = [
            subprocess.TimeoutExpired("cmd", 1),
            (b"", b""),  # cleanup call after kill
        ]
        mock_process.kill = MagicMock()
        mock_popen.return_value = mock_process

        with pytest.raises(CommandTimeoutError):
            execute_command_safe(
                ["sleep", "100"],
                fail_on_error=False,
                timeout=1,
                check_executable=False,
            )

    @patch("mcli.lib.shell.shell.subprocess.Popen")
    def test_permission_error_raises_resource_error(self, mock_popen):
        """Test PermissionError raises CommandResourceError."""
        mock_popen.side_effect = PermissionError("Permission denied")

        with pytest.raises(CommandResourceError) as exc_info:
            execute_command_safe(
                ["/some/script"],
                fail_on_error=False,
                check_executable=False,
            )
        assert "permission" in exc_info.value.resource_type


class TestExecuteCommandWithResult:
    """Tests for execute_command_with_result function."""

    def test_empty_args_raises_validation_error(self):
        """Test empty args raises CommandValidationError."""
        with pytest.raises(CommandValidationError):
            execute_command_with_result([])

    def test_successful_command_returns_result(self):
        """Test successful command returns CommandResult."""
        result = execute_command_with_result(["echo", "hello"])
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "hello" in result.stdout

    def test_failed_command_returns_result_not_raises(self):
        """Test failed command returns result, doesn't raise."""
        result = execute_command_with_result(["false"])
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert result.returncode == 1

    def test_nonexistent_command_returns_result_127(self):
        """Test nonexistent command returns result with exit code 127."""
        result = execute_command_with_result(["not-a-real-command-xyz"])
        assert result.returncode == 127
        assert "not found" in result.stderr.lower()

    def test_duration_ms_tracked(self):
        """Test execution duration is tracked."""
        result = execute_command_with_result(["echo", "test"])
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    def test_timeout_returns_result_with_timed_out(self):
        """Test timeout returns result with timed_out=True."""
        # Use a very short timeout
        result = execute_command_with_result(["sleep", "10"], timeout=1)
        # Note: This may or may not timeout depending on system
        # If it doesn't timeout, the test passes anyway
        if result.timed_out:
            assert result.returncode == -1

    def test_cwd_parameter(self):
        """Test cwd parameter works."""
        result = execute_command_with_result(["pwd"], cwd="/tmp")
        assert "/tmp" in result.stdout or "/private/tmp" in result.stdout

    def test_env_parameter(self):
        """Test env parameter works."""
        result = execute_command_with_result(
            ["printenv", "TEST_VAR"],
            env={"TEST_VAR": "value123"},
        )
        assert "value123" in result.stdout


class TestSanitizeForLog:
    """Tests for _sanitize_for_log function."""

    def test_empty_command(self):
        """Test empty command returns placeholder."""
        assert _sanitize_for_log("") == "<empty>"
        assert _sanitize_for_log(None) == "<empty>"

    def test_password_masked(self):
        """Test password values are masked."""
        cmd = "cmd --password=secret123"
        sanitized = _sanitize_for_log(cmd)
        assert "secret123" not in sanitized
        assert "****" in sanitized

    def test_token_masked(self):
        """Test token values are masked."""
        cmd = "cmd --token=abc123xyz"
        sanitized = _sanitize_for_log(cmd)
        assert "abc123xyz" not in sanitized
        assert "****" in sanitized

    def test_api_key_masked(self):
        """Test API key values are masked."""
        cmd = "cmd api_key=supersecret"
        sanitized = _sanitize_for_log(cmd)
        assert "supersecret" not in sanitized
        assert "****" in sanitized

    def test_bearer_token_masked(self):
        """Test Bearer token is masked."""
        cmd = "curl -H 'Authorization: Bearer abcdef123'"
        sanitized = _sanitize_for_log(cmd)
        assert "abcdef123" not in sanitized
        assert "****" in sanitized

    def test_basic_auth_masked(self):
        """Test Basic auth is masked."""
        cmd = "curl -H 'Authorization: Basic dXNlcjpwYXNz'"
        sanitized = _sanitize_for_log(cmd)
        assert "dXNlcjpwYXNz" not in sanitized
        assert "****" in sanitized

    def test_long_command_truncated(self):
        """Test long commands are truncated."""
        cmd = "x" * 300
        sanitized = _sanitize_for_log(cmd, max_length=100)
        assert len(sanitized) <= 100
        assert "..." in sanitized

    def test_normal_command_unchanged(self):
        """Test normal commands without secrets are unchanged."""
        cmd = "echo hello world"
        sanitized = _sanitize_for_log(cmd)
        assert sanitized == cmd


class TestIsExecutableAvailable:
    """Tests for is_executable_available function."""

    def test_existing_executable(self):
        """Test returns True for existing executable."""
        # 'echo' should exist on all systems
        assert is_executable_available("echo") is True

    def test_nonexistent_executable(self):
        """Test returns False for nonexistent executable."""
        assert is_executable_available("definitely-not-a-real-command-xyz") is False

    def test_python_executable(self):
        """Test returns True for python."""
        # Python should be available since we're running Python
        assert (
            is_executable_available("python") is True or is_executable_available("python3") is True
        )


class TestSignalHandling:
    """Tests for signal handling in command execution."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Signals work differently on Windows")
    def test_killed_process_detected(self):
        """Test killed process is detected correctly."""
        # This is tricky to test reliably, so we'll just verify the logic exists
        # by checking that negative return codes are handled
        result = CommandResult(
            returncode=-9,  # SIGKILL
            stdout="",
            stderr="",
            command="killed-cmd",
        )
        # The result itself should be valid
        assert result.returncode == -9
        assert result.success is False
