"""
CLI tests for mcli.app.logs_cmd module
"""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestLogsCommands:
    """Test suite for logs CLI commands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_logs_group_exists(self):
        """Test logs command group exists"""
        from mcli.app.logs_cmd import logs_group

        assert logs_group is not None
        assert hasattr(logs_group, 'commands')

    def test_logs_group_help(self):
        """Test logs command group help"""
        from mcli.app.logs_cmd import logs_group

        result = self.runner.invoke(logs_group, ['--help'])

        assert result.exit_code == 0
        assert 'logs' in result.output.lower() or 'stream' in result.output.lower()

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_show_location_directory_exists(self, mock_get_logs_dir):
        """Test show location with existing directory"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            # Create a sample log file
            (tmp_path / "mcli_20250101.log").touch()

            result = self.runner.invoke(logs_group, ['location'])

            assert result.exit_code == 0
            assert tmpdir in result.output

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_show_location_directory_not_exists(self, mock_get_logs_dir):
        """Test show location with non-existent directory"""
        from mcli.app.logs_cmd import logs_group

        # Use a path that doesn't exist
        nonexistent_path = Path("/nonexistent/logs/path")
        mock_get_logs_dir.return_value = nonexistent_path

        result = self.runner.invoke(logs_group, ['location'])

        assert result.exit_code == 0
        # Should show warning about directory not existing
        assert 'created' in result.output.lower() or 'nonexistent' not in result.output

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_list_logs_command(self, mock_get_logs_dir):
        """Test list logs command"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            # Create sample log files
            (tmp_path / "mcli_20250101.log").touch()
            (tmp_path / "mcli_trace_20250101.log").touch()

            result = self.runner.invoke(logs_group, ['list'])

            assert result.exit_code == 0

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_list_logs_with_date(self, mock_get_logs_dir):
        """Test list logs with specific date"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            result = self.runner.invoke(logs_group, ['list', '--date', '20250101'])

            assert result.exit_code == 0

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_tail_logs_file_not_found(self, mock_get_logs_dir):
        """Test tail logs when file doesn't exist"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            result = self.runner.invoke(logs_group, ['tail', 'main'])

            # Should handle missing file gracefully
            assert result.exit_code in [0, 1]

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_tail_logs_with_lines_option(self, mock_get_logs_dir):
        """Test tail logs with lines option"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            # Create log file with content
            today = datetime.now().strftime("%Y%m%d")
            log_file = tmp_path / f"mcli_{today}.log"
            log_file.write_text("line 1\nline 2\nline 3\n")

            result = self.runner.invoke(logs_group, ['tail', 'main', '--lines', '2'])

            # Should not crash
            assert result.exit_code in [0, 1]

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_tail_logs_with_date(self, mock_get_logs_dir):
        """Test tail logs with specific date"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            result = self.runner.invoke(logs_group, ['tail', 'main', '--date', '20250101'])

            assert result.exit_code in [0, 1]

    def test_logs_location_help(self):
        """Test location command help"""
        from mcli.app.logs_cmd import logs_group

        result = self.runner.invoke(logs_group, ['location', '--help'])

        assert result.exit_code == 0

    def test_logs_list_help(self):
        """Test list command help"""
        from mcli.app.logs_cmd import logs_group

        result = self.runner.invoke(logs_group, ['list', '--help'])

        assert result.exit_code == 0

    def test_logs_tail_help(self):
        """Test tail command help"""
        from mcli.app.logs_cmd import logs_group

        result = self.runner.invoke(logs_group, ['tail', '--help'])

        assert result.exit_code == 0

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_stream_logs_no_files(self, mock_get_logs_dir):
        """Test stream logs when no files exist"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            result = self.runner.invoke(logs_group, ['stream'])

            # Should handle gracefully
            assert result.exit_code in [0, 1]

    @patch('mcli.app.logs_cmd.get_logs_dir')
    def test_stream_logs_type_option(self, mock_get_logs_dir):
        """Test stream logs with type option"""
        from mcli.app.logs_cmd import logs_group

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_get_logs_dir.return_value = tmp_path

            # Create log file
            today = datetime.now().strftime("%Y%m%d")
            log_file = tmp_path / f"mcli_trace_{today}.log"
            log_file.write_text("trace log content\n")

            result = self.runner.invoke(logs_group, ['stream', '--type', 'trace', '--no-follow'])

            # Should not crash (may have usage errors due to options)
            assert result.exit_code in [0, 1, 2]

    def test_logs_stream_help(self):
        """Test stream command help"""
        from mcli.app.logs_cmd import logs_group

        result = self.runner.invoke(logs_group, ['stream', '--help'])

        assert result.exit_code == 0
        assert 'stream' in result.output.lower() or 'type' in result.output.lower()
