"""Tests for shell command execution exceptions and result objects."""

import pytest

from mcli.lib.shell.exceptions import (
    CommandError,
    CommandFailedError,
    CommandInterruptedError,
    CommandNotFoundError,
    CommandResourceError,
    CommandResult,
    CommandSecurityError,
    CommandTimeoutError,
    CommandValidationError,
)


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_property_zero_returncode(self):
        """Test success property returns True for returncode 0."""
        result = CommandResult(
            returncode=0,
            stdout="output",
            stderr="",
            command="echo hello",
        )
        assert result.success is True

    def test_success_property_nonzero_returncode(self):
        """Test success property returns False for non-zero returncode."""
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="error",
            command="false",
        )
        assert result.success is False

    def test_output_property_combines_stdout_stderr(self):
        """Test output property combines stdout and stderr."""
        result = CommandResult(
            returncode=0,
            stdout="standard output",
            stderr="error output",
            command="cmd",
        )
        assert "standard output" in result.output
        assert "error output" in result.output

    def test_output_property_empty_stderr(self):
        """Test output property with only stdout."""
        result = CommandResult(
            returncode=0,
            stdout="only stdout",
            stderr="",
            command="cmd",
        )
        assert result.output == "only stdout"

    def test_output_property_empty_stdout(self):
        """Test output property with only stderr."""
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="only stderr",
            command="cmd",
        )
        assert result.output == "only stderr"

    def test_to_dict_serialization(self):
        """Test to_dict returns proper dictionary."""
        result = CommandResult(
            returncode=0,
            stdout="output",
            stderr="",
            command=["echo", "hello"],
            timed_out=False,
            duration_ms=100.5,
        )
        d = result.to_dict()
        assert d["returncode"] == 0
        assert d["stdout"] == "output"
        assert d["stderr"] == ""
        assert d["command"] == "echo hello"
        assert d["timed_out"] is False
        assert d["duration_ms"] == 100.5
        assert d["success"] is True

    def test_to_dict_string_command(self):
        """Test to_dict with string command."""
        result = CommandResult(
            returncode=0,
            stdout="",
            stderr="",
            command="echo hello world",
        )
        d = result.to_dict()
        assert d["command"] == "echo hello world"

    def test_timed_out_default(self):
        """Test timed_out defaults to False."""
        result = CommandResult(
            returncode=0,
            stdout="",
            stderr="",
            command="cmd",
        )
        assert result.timed_out is False

    def test_duration_ms_default(self):
        """Test duration_ms defaults to None."""
        result = CommandResult(
            returncode=0,
            stdout="",
            stderr="",
            command="cmd",
        )
        assert result.duration_ms is None


class TestCommandError:
    """Tests for base CommandError exception."""

    def test_basic_message(self):
        """Test basic error message."""
        error = CommandError("Something went wrong")
        assert "Something went wrong" in str(error)

    def test_message_with_command(self):
        """Test error message includes command."""
        error = CommandError("Failed", command="echo test")
        assert "Failed" in str(error)
        assert "echo test" in str(error)

    def test_message_with_list_command(self):
        """Test error message with list command."""
        error = CommandError("Failed", command=["echo", "test"])
        assert "echo test" in str(error)

    def test_message_with_result(self):
        """Test error message includes result details."""
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="Permission denied",
            command="cat /etc/shadow",
        )
        error = CommandError("Access error", result=result)
        assert "Exit code: 1" in str(error)
        assert "Permission denied" in str(error)

    def test_long_command_truncated(self):
        """Test very long commands are truncated in message."""
        long_cmd = "x" * 300
        error = CommandError("Failed", command=long_cmd)
        msg = str(error)
        assert "..." in msg
        assert len(msg) < 500

    def test_long_stderr_truncated(self):
        """Test very long stderr is truncated."""
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="e" * 1000,
            command="cmd",
        )
        error = CommandError("Failed", result=result)
        msg = str(error)
        assert "..." in msg

    def test_to_dict(self):
        """Test to_dict returns structured data."""
        result = CommandResult(
            returncode=1,
            stdout="out",
            stderr="err",
            command="cmd",
        )
        error = CommandError("Test error", command="cmd", result=result)
        d = error.to_dict()
        assert d["error_type"] == "CommandError"
        assert d["message"] == "Test error"
        assert d["command"] == "cmd"
        assert d["result"]["returncode"] == 1


class TestCommandNotFoundError:
    """Tests for CommandNotFoundError."""

    def test_basic_message(self):
        """Test error message for missing command."""
        error = CommandNotFoundError("nonexistent-cmd")
        assert "nonexistent-cmd" in str(error)
        assert "not found" in str(error).lower()

    def test_with_search_path(self):
        """Test error message includes search path."""
        error = CommandNotFoundError("kubectl", search_path="/usr/local/bin:/usr/bin")
        assert "kubectl" in str(error)
        assert "/usr/local/bin" in str(error)

    def test_inherits_from_command_error(self):
        """Test inherits from CommandError."""
        error = CommandNotFoundError("missing")
        assert isinstance(error, CommandError)


class TestCommandTimeoutError:
    """Tests for CommandTimeoutError."""

    def test_message_includes_timeout(self):
        """Test error message includes timeout duration."""
        error = CommandTimeoutError(30, "slow-cmd")
        assert "30" in str(error)
        assert "timed out" in str(error).lower()

    def test_creates_result_if_not_provided(self):
        """Test creates CommandResult if not provided."""
        error = CommandTimeoutError(10, ["echo", "test"])
        assert error.result is not None
        assert error.result.timed_out is True
        assert error.result.returncode == -1

    def test_uses_provided_result(self):
        """Test uses provided result."""
        result = CommandResult(
            returncode=-1,
            stdout="partial output",
            stderr="",
            command="cmd",
            timed_out=True,
        )
        error = CommandTimeoutError(5, "cmd", result=result)
        assert error.result.stdout == "partial output"

    def test_inherits_from_command_error(self):
        """Test inherits from CommandError."""
        error = CommandTimeoutError(10, "cmd")
        assert isinstance(error, CommandError)


class TestCommandFailedError:
    """Tests for CommandFailedError."""

    def test_message_includes_exit_code(self):
        """Test error message includes exit code."""
        result = CommandResult(
            returncode=2,
            stdout="",
            stderr="",
            command="exit 2",
        )
        error = CommandFailedError(result)
        assert "2" in str(error)

    def test_message_includes_first_stderr_line(self):
        """Test error message includes first line of stderr."""
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="Error: file not found\nMore details here",
            command="cmd",
        )
        error = CommandFailedError(result)
        assert "file not found" in str(error)

    def test_long_first_line_truncated(self):
        """Test long first line is truncated."""
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="x" * 200,
            command="cmd",
        )
        error = CommandFailedError(result)
        assert "..." in str(error)

    def test_inherits_from_command_error(self):
        """Test inherits from CommandError."""
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="",
            command="cmd",
        )
        error = CommandFailedError(result)
        assert isinstance(error, CommandError)


class TestCommandValidationError:
    """Tests for CommandValidationError."""

    def test_basic_message(self):
        """Test basic validation error."""
        error = CommandValidationError("Command cannot be empty")
        assert "empty" in str(error).lower()

    def test_with_command(self):
        """Test validation error with command context."""
        error = CommandValidationError("Invalid argument", command="cmd --invalid")
        assert "Invalid argument" in str(error)
        assert "--invalid" in str(error)

    def test_inherits_from_command_error(self):
        """Test inherits from CommandError."""
        error = CommandValidationError("test")
        assert isinstance(error, CommandError)


class TestCommandSecurityError:
    """Tests for CommandSecurityError."""

    def test_basic_message(self):
        """Test basic security error."""
        error = CommandSecurityError("Injection detected", "cmd; rm -rf /")
        assert "Injection" in str(error)

    def test_with_dangerous_pattern(self):
        """Test message includes dangerous pattern."""
        error = CommandSecurityError(
            "Null byte detected",
            "cmd\x00arg",
            dangerous_pattern="\\x00",
        )
        assert "\\x00" in str(error)

    def test_inherits_from_validation_error(self):
        """Test inherits from CommandValidationError."""
        error = CommandSecurityError("test", "cmd")
        assert isinstance(error, CommandValidationError)
        assert isinstance(error, CommandError)


class TestCommandInterruptedError:
    """Tests for CommandInterruptedError."""

    def test_sigint_name(self):
        """Test SIGINT is named correctly."""
        error = CommandInterruptedError(2, "cmd")
        assert "SIGINT" in str(error)

    def test_sigterm_name(self):
        """Test SIGTERM is named correctly."""
        error = CommandInterruptedError(15, "cmd")
        assert "SIGTERM" in str(error)

    def test_sigkill_name(self):
        """Test SIGKILL is named correctly."""
        error = CommandInterruptedError(9, "cmd")
        assert "SIGKILL" in str(error)

    def test_unknown_signal(self):
        """Test unknown signal number is shown."""
        error = CommandInterruptedError(42, "cmd")
        assert "42" in str(error) or "signal" in str(error).lower()

    def test_inherits_from_command_error(self):
        """Test inherits from CommandError."""
        error = CommandInterruptedError(9, "cmd")
        assert isinstance(error, CommandError)


class TestCommandResourceError:
    """Tests for CommandResourceError."""

    def test_permission_error(self):
        """Test permission error message."""
        error = CommandResourceError("permission", "Permission denied: /root/.ssh", "cmd")
        assert "permission" in str(error).lower()
        assert "Permission denied" in str(error)

    def test_os_error(self):
        """Test OS error message."""
        error = CommandResourceError("os", "No such file or directory", ["cat", "/missing"])
        assert "os" in str(error).lower()
        assert "No such file" in str(error)

    def test_inherits_from_command_error(self):
        """Test inherits from CommandError."""
        error = CommandResourceError("test", "details", "cmd")
        assert isinstance(error, CommandError)


class TestExceptionHierarchy:
    """Tests for exception hierarchy allowing broad catches."""

    def test_catch_all_command_errors(self):
        """Test all exceptions can be caught with CommandError."""
        exceptions = [
            CommandError("base"),
            CommandNotFoundError("cmd"),
            CommandTimeoutError(10, "cmd"),
            CommandFailedError(CommandResult(returncode=1, stdout="", stderr="", command="cmd")),
            CommandValidationError("test"),
            CommandSecurityError("test", "cmd"),
            CommandInterruptedError(9, "cmd"),
            CommandResourceError("type", "details", "cmd"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except CommandError as e:
                # All should be caught
                assert isinstance(e, CommandError)
            except Exception:
                pytest.fail(f"{exc.__class__.__name__} not caught by CommandError")

    def test_specific_catches_work(self):
        """Test specific exception types can be caught separately."""
        try:
            raise CommandNotFoundError("missing")
        except CommandNotFoundError:
            pass  # Expected
        except CommandError:
            pytest.fail("Should have been caught by specific type")

    def test_validation_catches_security(self):
        """Test CommandValidationError catches CommandSecurityError."""
        try:
            raise CommandSecurityError("danger", "cmd")
        except CommandValidationError:
            pass  # Expected - security is a subclass
        except CommandError:
            pytest.fail("Should have been caught by CommandValidationError")
