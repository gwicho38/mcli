"""Unit tests for mcli logs commands"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from mcli.self.logs_cmd import logs_group


@pytest.fixture
def temp_logs_dir():
    """Create a temporary logs directory with sample log files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs_dir = Path(tmpdir)

        # Create sample log files
        today = "20251006"

        # Main log
        main_log = logs_dir / f"mcli_{today}.log"
        main_log.write_text(
            "INFO: Application started\n"
            "DEBUG: Loading configuration\n"
            "WARNING: Deprecated feature used\n"
            "ERROR: Connection failed\n"
            "INFO: Retrying connection\n"
        )

        # Trace log
        trace_log = logs_dir / f"mcli_trace_{today}.log"
        trace_log.write_text(
            "TRACE: Function call: init()\n"
            "TRACE: Function call: connect()\n"
            "TRACE: Function call: process()\n"
        )

        # System log
        system_log = logs_dir / f"mcli_system_{today}.log"
        system_log.write_text("SYSTEM: CPU usage: 25%\n" "SYSTEM: Memory usage: 512MB\n")

        yield logs_dir


@pytest.fixture
def runner():
    """Create a Click CLI runner"""
    return CliRunner()


def test_logs_location(runner):
    """Test logs location command"""
    result = runner.invoke(logs_group, ["location"])
    assert result.exit_code == 0
    assert "Logs directory:" in result.output


def test_logs_list(runner, temp_logs_dir):
    """Test logs list command"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        result = runner.invoke(logs_group, ["list"])
        assert result.exit_code == 0
        assert "mcli_20251006.log" in result.output
        assert "mcli_trace_20251006.log" in result.output
        assert "mcli_system_20251006.log" in result.output


def test_logs_tail_basic(runner, temp_logs_dir):
    """Test basic tail command without follow"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            result = runner.invoke(logs_group, ["tail", "main", "-n", "3"])
            assert result.exit_code == 0
            assert "Last" in result.output
            # Should show last 3 lines
            assert "ERROR: Connection failed" in result.output
            assert "INFO: Retrying connection" in result.output


def test_logs_tail_with_lines_option(runner, temp_logs_dir):
    """Test tail command with custom line count"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            result = runner.invoke(logs_group, ["tail", "main", "-n", "2"])
            assert result.exit_code == 0
            # Should only show last 2 lines
            assert "ERROR: Connection failed" in result.output
            assert "INFO: Retrying connection" in result.output
            # Should NOT show earlier lines
            assert "Application started" not in result.output


def test_logs_tail_trace_log(runner, temp_logs_dir):
    """Test tail command on trace log"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            result = runner.invoke(logs_group, ["tail", "trace"])
            assert result.exit_code == 0
            assert "Function call: init()" in result.output
            assert "Function call: connect()" in result.output


def test_logs_tail_system_log(runner, temp_logs_dir):
    """Test tail command on system log"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            result = runner.invoke(logs_group, ["tail", "system"])
            assert result.exit_code == 0
            assert "CPU usage" in result.output
            assert "Memory usage" in result.output


def test_logs_tail_nonexistent_file(runner, temp_logs_dir):
    """Test tail command with nonexistent log file"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20991231"  # Future date

            result = runner.invoke(logs_group, ["tail", "main"])
            assert result.exit_code == 0
            assert "Log file not found" in result.output


def test_logs_tail_with_date_option(runner, temp_logs_dir):
    """Test tail command with specific date"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        result = runner.invoke(logs_group, ["tail", "main", "-d", "20251006"])
        assert result.exit_code == 0
        assert "Application started" in result.output or "Retrying connection" in result.output


def test_logs_tail_follow_flag_exists(runner):
    """Test that --follow/-f flag is available"""
    result = runner.invoke(logs_group, ["tail", "--help"])
    assert result.exit_code == 0
    assert "--follow" in result.output or "-f" in result.output
    assert "Follow log output" in result.output or "tail -f" in result.output


def test_logs_tail_follow_mode_subprocess_called(runner, temp_logs_dir):
    """Test that follow mode calls subprocess.Popen with tail -f"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            with patch("mcli.self.logs_cmd.subprocess.Popen") as mock_popen:
                # Mock the process
                mock_process = MagicMock()
                mock_process.stdout.readline.side_effect = [
                    "INFO: Line 1\n",
                    "",
                ]  # Simulate 1 line then EOF
                mock_popen.return_value = mock_process

                # Run with --follow flag
                result = runner.invoke(logs_group, ["tail", "main", "-f"], catch_exceptions=False)

                # Verify Popen was called with tail -f
                mock_popen.assert_called_once()
                call_args = mock_popen.call_args[0][0]
                assert "tail" in call_args
                assert "-f" in call_args
                assert any("mcli_20251006.log" in str(arg) for arg in call_args)


def test_logs_tail_follow_short_flag(runner, temp_logs_dir):
    """Test that -f short flag works"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            with patch("mcli.self.logs_cmd.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.stdout.readline.side_effect = [""]  # EOF immediately
                mock_popen.return_value = mock_process

                # Use -f instead of --follow
                result = runner.invoke(logs_group, ["tail", "main", "-f"], catch_exceptions=False)

                # Should call Popen
                assert mock_popen.called


def test_logs_tail_follow_with_custom_lines(runner, temp_logs_dir):
    """Test that follow mode respects -n/--lines option"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            with patch("mcli.self.logs_cmd.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.stdout.readline.side_effect = [""]
                mock_popen.return_value = mock_process

                # Test with custom line count
                result = runner.invoke(
                    logs_group, ["tail", "main", "-f", "-n", "50"], catch_exceptions=False
                )

                # Verify tail is called with -n50
                call_args = mock_popen.call_args[0][0]
                assert "-n50" in call_args or any(
                    "-n" in str(arg) and "50" in str(arg) for arg in call_args
                )


def test_logs_tail_without_follow_doesnt_use_subprocess(runner, temp_logs_dir):
    """Test that without --follow, we don't use subprocess"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            with patch("mcli.self.logs_cmd.subprocess.Popen") as mock_popen:
                # Run without --follow
                result = runner.invoke(logs_group, ["tail", "main"])

                # subprocess should NOT be called
                assert not mock_popen.called
                assert result.exit_code == 0


def test_logs_grep_basic(runner, temp_logs_dir):
    """Test basic grep functionality"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            result = runner.invoke(logs_group, ["grep", "ERROR"])
            assert result.exit_code == 0
            assert "Connection failed" in result.output


def test_logs_stream_help(runner):
    """Test that stream command has help"""
    result = runner.invoke(logs_group, ["stream", "--help"])
    assert result.exit_code == 0
    assert "--follow" in result.output
    assert "--type" in result.output


def test_logs_clear_help(runner):
    """Test that clear command has help"""
    result = runner.invoke(logs_group, ["clear", "--help"])
    assert result.exit_code == 0
    assert "--older-than" in result.output


def test_logs_tail_follow_keyboard_interrupt_handling(runner, temp_logs_dir):
    """Test that KeyboardInterrupt is handled gracefully in follow mode"""
    with patch("mcli.self.logs_cmd.get_logs_dir", return_value=temp_logs_dir):
        with patch("mcli.self.logs_cmd.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20251006"

            with patch("mcli.self.logs_cmd.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                # Simulate KeyboardInterrupt during readline
                mock_process.stdout.readline.side_effect = KeyboardInterrupt()
                mock_popen.return_value = mock_process

                result = runner.invoke(logs_group, ["tail", "main", "-f"], catch_exceptions=False)

                # Process should be terminated
                mock_process.terminate.assert_called_once()
                assert "stopped" in result.output.lower()


def main():
    """Run all tests"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
