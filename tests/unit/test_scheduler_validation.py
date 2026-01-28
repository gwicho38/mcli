"""Unit tests for scheduler job validation."""

import pytest

from mcli.workflow.scheduler.validation import (
    ValidationResult,
    sanitize_command_for_logging,
    validate_cron_expression,
    validate_environment,
    validate_job_command,
    validate_job_config,
    validate_job_name,
    validate_working_directory,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_initial_valid(self):
        """Test ValidationResult starts as valid."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_marks_invalid(self):
        """Test adding error marks result as invalid."""
        result = ValidationResult(valid=True)
        result.add_error("Test error")
        assert result.valid is False
        assert "Test error" in result.errors

    def test_add_warning_keeps_valid(self):
        """Test adding warning keeps result valid."""
        result = ValidationResult(valid=True)
        result.add_warning("Test warning")
        assert result.valid is True
        assert "Test warning" in result.warnings

    def test_merge_combines_results(self):
        """Test merge combines two results."""
        result1 = ValidationResult(valid=True)
        result1.add_warning("Warning 1")

        result2 = ValidationResult(valid=True)
        result2.add_error("Error 1")

        result1.merge(result2)

        assert result1.valid is False
        assert "Warning 1" in result1.warnings
        assert "Error 1" in result1.errors


class TestValidateJobCommand:
    """Tests for validate_job_command function."""

    def test_empty_command_invalid(self):
        """Test empty command is invalid."""
        result = validate_job_command("")
        assert result.valid is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_whitespace_command_invalid(self):
        """Test whitespace-only command is invalid."""
        result = validate_job_command("   ")
        assert result.valid is False

    def test_valid_command(self):
        """Test valid command passes."""
        result = validate_job_command("echo hello")
        assert result.valid is True
        assert result.errors == []

    def test_command_with_null_bytes_invalid(self):
        """Test command with null bytes is invalid."""
        result = validate_job_command("echo\x00hello")
        assert result.valid is False
        assert any("null" in e.lower() for e in result.errors)

    def test_dangerous_rm_rf_warning(self):
        """Test dangerous rm -rf pattern generates warning."""
        result = validate_job_command("rm -rf /")
        assert "rm -rf" in result.warnings[0].lower() or "dangerous" in result.warnings[0].lower()

    def test_dangerous_rm_rf_strict_error(self):
        """Test dangerous rm -rf pattern generates error in strict mode."""
        result = validate_job_command("rm -rf /", strict=True)
        assert result.valid is False
        assert any("dangerous" in e.lower() for e in result.errors)

    def test_fork_bomb_pattern_warning(self):
        """Test fork bomb pattern generates warning."""
        result = validate_job_command(":(){:|:&};:")
        assert len(result.warnings) > 0

    def test_dd_pattern_warning(self):
        """Test dd to device generates warning."""
        result = validate_job_command("dd if=/dev/zero of=/dev/sda")
        assert len(result.warnings) > 0

    def test_command_length_limit(self):
        """Test command length limit."""
        long_command = "echo " + "x" * 200000
        result = validate_job_command(long_command)
        assert result.valid is False
        assert any("length" in e.lower() for e in result.errors)

    def test_python_eval_warning(self):
        """Test Python code with eval generates warning."""
        result = validate_job_command("eval(user_input)", job_type="python")
        assert len(result.warnings) > 0
        assert any("eval" in w.lower() for w in result.warnings)

    def test_python_os_system_warning(self):
        """Test Python code with os.system generates warning."""
        result = validate_job_command("os.system('ls')", job_type="python")
        assert len(result.warnings) > 0

    def test_api_call_valid_json(self):
        """Test valid API call config."""
        config = '{"url": "https://api.example.com", "method": "GET"}'
        result = validate_job_command(config, job_type="api_call")
        assert result.valid is True

    def test_api_call_invalid_json(self):
        """Test invalid JSON for API call."""
        result = validate_job_command("not json", job_type="api_call")
        assert result.valid is False
        assert any("json" in e.lower() for e in result.errors)

    def test_api_call_missing_url(self):
        """Test API call config without URL."""
        result = validate_job_command('{"method": "GET"}', job_type="api_call")
        assert result.valid is False
        assert any("url" in e.lower() for e in result.errors)


class TestValidateWorkingDirectory:
    """Tests for validate_working_directory function."""

    def test_none_is_valid(self):
        """Test None working directory is valid."""
        result = validate_working_directory(None)
        assert result.valid is True

    def test_empty_string_invalid(self):
        """Test empty string is invalid."""
        result = validate_working_directory("")
        assert result.valid is False

    def test_existing_directory_valid(self):
        """Test existing directory is valid."""
        result = validate_working_directory("/tmp")
        assert result.valid is True

    def test_nonexistent_directory_warning(self):
        """Test non-existent directory generates warning."""
        result = validate_working_directory("/nonexistent/path/12345")
        assert any("not exist" in w.lower() for w in result.warnings)

    def test_file_not_directory_error(self):
        """Test file path (not directory) generates error."""
        # /etc/passwd exists on most Unix systems
        result = validate_working_directory("/etc/passwd")
        if result.errors:  # May not exist on all systems
            assert any("not a directory" in e.lower() for e in result.errors)

    def test_home_expansion(self):
        """Test home directory expansion works."""
        result = validate_working_directory("~")
        assert result.valid is True


class TestValidateEnvironment:
    """Tests for validate_environment function."""

    def test_none_is_valid(self):
        """Test None environment is valid."""
        result = validate_environment(None)
        assert result.valid is True

    def test_valid_environment(self):
        """Test valid environment passes."""
        result = validate_environment({"PATH": "/usr/bin", "HOME": "/home/user"})
        assert result.valid is True

    def test_invalid_key_format(self):
        """Test invalid key format generates error."""
        result = validate_environment({"123invalid": "value"})
        assert result.valid is False
        assert any("invalid" in e.lower() for e in result.errors)

    def test_key_with_hyphen_invalid(self):
        """Test key with hyphen is invalid."""
        result = validate_environment({"MY-VAR": "value"})
        assert result.valid is False

    def test_valid_key_with_underscore(self):
        """Test key with underscore is valid."""
        result = validate_environment({"MY_VAR": "value"})
        assert result.valid is True

    def test_key_starting_with_number_invalid(self):
        """Test key starting with number is invalid."""
        result = validate_environment({"9VAR": "value"})
        assert result.valid is False

    def test_non_string_value_converted(self):
        """Test non-string value (int, bool, float) is silently converted."""
        # These types are commonly used in env vars and can be safely converted
        result = validate_environment({"COUNT": 123, "DEBUG": True, "RATE": 1.5})
        assert result.valid is True
        # No warnings for simple scalar types that convert cleanly to strings

    def test_value_with_null_bytes_error(self):
        """Test value with null bytes generates error."""
        result = validate_environment({"VAR": "hello\x00world"})
        assert result.valid is False
        assert any("null" in e.lower() for e in result.errors)

    def test_very_long_value_error(self):
        """Test very long value generates error."""
        result = validate_environment({"VAR": "x" * 50000})
        assert result.valid is False
        assert any("length" in e.lower() for e in result.errors)


class TestValidateCronExpression:
    """Tests for validate_cron_expression function."""

    def test_empty_cron_invalid(self):
        """Test empty cron expression is invalid."""
        result = validate_cron_expression("")
        assert result.valid is False

    def test_valid_5_field_cron(self):
        """Test valid 5-field cron expression."""
        result = validate_cron_expression("0 * * * *")
        assert result.valid is True

    def test_valid_6_field_cron(self):
        """Test valid 6-field cron expression (with seconds)."""
        result = validate_cron_expression("0 0 * * * *")
        assert result.valid is True

    def test_too_few_fields_error(self):
        """Test too few fields generates error."""
        result = validate_cron_expression("* * *")
        assert result.valid is False
        assert any("few" in e.lower() for e in result.errors)

    def test_too_many_fields_error(self):
        """Test too many fields generates error."""
        result = validate_cron_expression("* * * * * * * *")
        assert result.valid is False
        assert any("many" in e.lower() for e in result.errors)

    def test_special_expression_reboot(self):
        """Test @reboot special expression is valid."""
        result = validate_cron_expression("@reboot")
        assert result.valid is True

    def test_special_expression_daily(self):
        """Test @daily special expression is valid."""
        result = validate_cron_expression("@daily")
        assert result.valid is True

    def test_special_expression_hourly(self):
        """Test @hourly special expression is valid."""
        result = validate_cron_expression("@hourly")
        assert result.valid is True


class TestValidateJobName:
    """Tests for validate_job_name function."""

    def test_empty_name_invalid(self):
        """Test empty name is invalid."""
        result = validate_job_name("")
        assert result.valid is False

    def test_valid_name(self):
        """Test valid name passes."""
        result = validate_job_name("my_backup_job")
        assert result.valid is True

    def test_name_with_null_bytes_invalid(self):
        """Test name with null bytes is invalid."""
        result = validate_job_name("my\x00job")
        assert result.valid is False

    def test_very_long_name_invalid(self):
        """Test very long name is invalid."""
        result = validate_job_name("x" * 300)
        assert result.valid is False

    def test_dot_prefix_warning(self):
        """Test name starting with dot generates warning."""
        result = validate_job_name(".hidden_job")
        assert any("dot" in w.lower() or "hidden" in w.lower() for w in result.warnings)

    def test_path_separator_warning(self):
        """Test name with path separator generates warning."""
        result = validate_job_name("job/name")
        assert len(result.warnings) > 0


class TestValidateJobConfig:
    """Tests for validate_job_config function."""

    def test_valid_config(self):
        """Test valid complete config passes."""
        result = validate_job_config(
            name="backup",
            cron_expression="0 1 * * *",
            command="tar -czf backup.tar.gz /data",
            working_directory="/tmp",
            environment={"BACKUP_DIR": "/backup"},
        )
        assert result.valid is True

    def test_invalid_name_fails_config(self):
        """Test invalid name fails whole config."""
        result = validate_job_config(
            name="",
            cron_expression="0 * * * *",
            command="echo hello",
        )
        assert result.valid is False

    def test_invalid_cron_fails_config(self):
        """Test invalid cron fails whole config."""
        result = validate_job_config(
            name="test",
            cron_expression="invalid",
            command="echo hello",
        )
        assert result.valid is False

    def test_invalid_command_fails_config(self):
        """Test invalid command fails whole config."""
        result = validate_job_config(
            name="test",
            cron_expression="0 * * * *",
            command="",
        )
        assert result.valid is False


class TestSanitizeCommandForLogging:
    """Tests for sanitize_command_for_logging function."""

    def test_empty_command(self):
        """Test empty command returns placeholder."""
        assert sanitize_command_for_logging("") == "<empty>"
        assert sanitize_command_for_logging(None) == "<empty>"

    def test_short_command_unchanged(self):
        """Test short command is not truncated."""
        cmd = "echo hello"
        assert sanitize_command_for_logging(cmd) == cmd

    def test_long_command_truncated(self):
        """Test long command is truncated."""
        cmd = "echo " + "x" * 500
        result = sanitize_command_for_logging(cmd, max_length=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_password_masked(self):
        """Test password values are masked."""
        cmd = "mysql --password=secret123 -u admin"
        result = sanitize_command_for_logging(cmd)
        assert "secret123" not in result
        assert "****" in result

    def test_token_masked(self):
        """Test token values are masked."""
        cmd = "curl -H 'Authorization: Bearer abc123def'"
        result = sanitize_command_for_logging(cmd)
        assert "abc123def" not in result
        assert "****" in result

    def test_api_key_masked(self):
        """Test api_key values are masked."""
        cmd = "export API_KEY=mysecretkey && run_script"
        result = sanitize_command_for_logging(cmd)
        assert "mysecretkey" not in result
