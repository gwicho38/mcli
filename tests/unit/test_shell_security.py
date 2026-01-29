"""Unit tests for shell command execution security."""

import pytest

from mcli.lib.shell.exceptions import (
    CommandError,
    CommandFailedError,
    CommandSecurityError,
    CommandTimeoutError,
    CommandValidationError,
)
from mcli.lib.shell.shell import _sanitize_for_log, execute_command_safe, execute_os_command


class TestExecuteOsCommand:
    """Tests for execute_os_command function."""

    def test_simple_command(self):
        """Test simple command execution."""
        result = execute_os_command("echo hello", fail_on_error=False)
        assert result == "hello"

    def test_empty_command_raises(self):
        """Test empty command raises CommandValidationError."""
        with pytest.raises(CommandValidationError) as exc_info:
            execute_os_command("", fail_on_error=False)
        assert "empty" in str(exc_info.value).lower()

    def test_null_bytes_rejected(self):
        """Test command with null bytes is rejected."""
        with pytest.raises(CommandSecurityError) as exc_info:
            execute_os_command("echo\x00hello", fail_on_error=False)
        assert "null" in str(exc_info.value).lower()

    def test_command_as_list(self):
        """Test command as list uses shell=False."""
        result = execute_os_command(["echo", "hello"], fail_on_error=False)
        assert result == "hello"

    def test_command_with_stdin(self):
        """Test command with stdin input."""
        result = execute_os_command("cat", fail_on_error=False, stdin="hello")
        assert result == "hello"

    def test_command_failure_raises(self):
        """Test failed command raises CommandFailedError when fail_on_error=False."""
        with pytest.raises(CommandFailedError):
            execute_os_command("exit 1", fail_on_error=False)

    def test_command_timeout(self):
        """Test command timeout."""
        with pytest.raises(CommandTimeoutError) as exc_info:
            execute_os_command("sleep 10", fail_on_error=False, timeout=1)
        assert "timed out" in str(exc_info.value).lower()

    def test_very_long_command_rejected(self):
        """Test very long command is rejected."""
        long_cmd = "echo " + "x" * 200000
        with pytest.raises(CommandValidationError) as exc_info:
            execute_os_command(long_cmd, fail_on_error=False)
        assert "length" in str(exc_info.value).lower()


class TestExecuteCommandSafe:
    """Tests for execute_command_safe function."""

    def test_simple_command(self):
        """Test simple safe command execution."""
        result = execute_command_safe(["echo", "hello"], fail_on_error=False)
        assert result == "hello"

    def test_empty_args_raises(self):
        """Test empty args raises CommandValidationError."""
        with pytest.raises(CommandValidationError) as exc_info:
            execute_command_safe([], fail_on_error=False)
        assert "empty" in str(exc_info.value).lower()

    def test_command_with_spaces(self):
        """Test command with arguments containing spaces."""
        result = execute_command_safe(["echo", "hello world"], fail_on_error=False)
        assert result == "hello world"

    def test_command_with_special_chars(self):
        """Test command with special characters is safe."""
        # These would be dangerous with shell=True but safe with shell=False
        result = execute_command_safe(["echo", "hello; rm -rf /"], fail_on_error=False)
        assert "hello; rm -rf /" in result

    def test_command_with_env(self):
        """Test command with custom environment."""
        result = execute_command_safe(
            ["sh", "-c", "echo $TEST_VAR"],
            fail_on_error=False,
            env={"TEST_VAR": "test_value"},
        )
        assert result == "test_value"

    def test_command_with_cwd(self, tmp_path):
        """Test command with working directory."""
        result = execute_command_safe(["pwd"], fail_on_error=False, cwd=str(tmp_path))
        assert str(tmp_path) in result

    def test_command_with_stdin(self):
        """Test command with stdin."""
        result = execute_command_safe(["cat"], fail_on_error=False, stdin="test input")
        assert result == "test input"

    def test_command_timeout(self):
        """Test command timeout."""
        with pytest.raises(CommandTimeoutError) as exc_info:
            execute_command_safe(["sleep", "10"], fail_on_error=False, timeout=1)
        assert "timed out" in str(exc_info.value).lower()

    def test_no_shell_injection(self):
        """Test that shell injection attempts are safely handled."""
        # This would execute rm if shell=True was used
        result = execute_command_safe(
            ["echo", "$(rm -rf /)"],
            fail_on_error=False,
        )
        # The literal string is echoed, not executed
        assert "$(rm -rf /)" in result

    def test_backtick_injection_safe(self):
        """Test that backtick injection is safely handled."""
        result = execute_command_safe(
            ["echo", "`rm -rf /`"],
            fail_on_error=False,
        )
        # The literal string is echoed, not executed
        assert "`rm -rf /`" in result


class TestSanitizeForLog:
    """Tests for _sanitize_for_log function."""

    def test_empty_command(self):
        """Test empty command returns placeholder."""
        assert _sanitize_for_log("") == "<empty>"
        assert _sanitize_for_log(None) == "<empty>"

    def test_short_command_unchanged(self):
        """Test short command is unchanged."""
        cmd = "echo hello"
        assert _sanitize_for_log(cmd) == cmd

    def test_long_command_truncated(self):
        """Test long command is truncated."""
        cmd = "echo " + "x" * 500
        result = _sanitize_for_log(cmd, max_length=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_password_masked(self):
        """Test password values are masked."""
        cmd = "mysql --password=secret123"
        result = _sanitize_for_log(cmd)
        assert "secret123" not in result
        assert "****" in result

    def test_token_masked(self):
        """Test token values are masked."""
        cmd = "curl -H 'Authorization: Bearer abc123'"
        result = _sanitize_for_log(cmd)
        assert "abc123" not in result
        assert "****" in result

    def test_api_key_masked(self):
        """Test api_key values are masked."""
        cmd = "export API_KEY=mysecret"
        result = _sanitize_for_log(cmd)
        assert "mysecret" not in result

    def test_multiple_secrets_masked(self):
        """Test multiple secrets are all masked."""
        cmd = "cmd --password=pass1 --token=tok1 --secret=sec1"
        result = _sanitize_for_log(cmd)
        assert "pass1" not in result
        assert "tok1" not in result
        assert "sec1" not in result


class TestShellSecurityPatterns:
    """Tests for shell security patterns."""

    def test_command_substitution_safe(self):
        """Test that command substitution is safe with execute_command_safe."""
        # $(command) substitution should not execute
        result = execute_command_safe(["echo", "$(whoami)"], fail_on_error=False)
        assert result == "$(whoami)"

    def test_semicolon_injection_safe(self):
        """Test that semicolon injection is safe."""
        result = execute_command_safe(["echo", "hello; whoami"], fail_on_error=False)
        assert "hello; whoami" in result

    def test_pipe_injection_safe(self):
        """Test that pipe injection is safe."""
        result = execute_command_safe(["echo", "hello | cat"], fail_on_error=False)
        assert "hello | cat" in result

    def test_redirect_injection_safe(self):
        """Test that redirect injection is safe."""
        result = execute_command_safe(["echo", "hello > /tmp/test"], fail_on_error=False)
        assert "hello > /tmp/test" in result

    def test_and_injection_safe(self):
        """Test that && injection is safe."""
        result = execute_command_safe(["echo", "hello && whoami"], fail_on_error=False)
        assert "hello && whoami" in result

    def test_or_injection_safe(self):
        """Test that || injection is safe."""
        result = execute_command_safe(["echo", "hello || whoami"], fail_on_error=False)
        assert "hello || whoami" in result
