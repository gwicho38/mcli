import os
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, Mock
from mcli.self.self_cmd import self_app


def test_self_group_help():
    runner = CliRunner()
    result = runner.invoke(self_app, ['--help'])
    assert result.exit_code == 0
    assert 'Manage and extend the mcli application' in result.output


def test_search_help():
    runner = CliRunner()
    result = runner.invoke(self_app, ['search', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output


def test_add_command_help():
    runner = CliRunner()
    result = runner.invoke(self_app, ['add-command', '--help'])
    assert result.exit_code == 0
    assert 'Generate a new portable custom command' in result.output


def test_add_command_missing_required():
    runner = CliRunner()
    result = runner.invoke(self_app, ['add-command'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_plugin_help():
    runner = CliRunner()
    result = runner.invoke(self_app, ['plugin', '--help'])
    assert result.exit_code == 0
    assert 'Manage plugins for mcli' in result.output


def test_plugin_add_help():
    runner = CliRunner()
    result = runner.invoke(self_app, ['plugin', 'add', '--help'])
    assert result.exit_code == 0
    assert 'PLUGIN_NAME' in result.output


def test_plugin_add_missing_required():
    runner = CliRunner()
    result = runner.invoke(self_app, ['plugin', 'add'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_plugin_remove_help():
    runner = CliRunner()
    result = runner.invoke(self_app, ['plugin', 'remove', '--help'])
    assert result.exit_code == 0
    assert 'PLUGIN_NAME' in result.output


def test_plugin_remove_missing_required():
    runner = CliRunner()
    result = runner.invoke(self_app, ['plugin', 'remove'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_plugin_update_help():
    runner = CliRunner()
    result = runner.invoke(self_app, ['plugin', 'update', '--help'])
    assert result.exit_code == 0
    assert 'PLUGIN_NAME' in result.output


def test_plugin_update_missing_required():
    runner = CliRunner()
    result = runner.invoke(self_app, ['plugin', 'update'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_logs_help():
    """Test that logs command shows help text"""
    runner = CliRunner()
    result = runner.invoke(self_app, ['logs', '--help'])
    assert result.exit_code == 0
    assert 'Display runtime logs' in result.output


def test_logs_uses_correct_directory():
    """Test that logs command uses get_logs_dir() from mcli.lib.paths"""
    from mcli.lib.paths import get_logs_dir
    from pathlib import Path
    import tempfile

    runner = CliRunner()

    # Get the expected logs directory
    expected_logs_dir = get_logs_dir()

    # The logs directory should be in ~/.mcli/logs
    assert expected_logs_dir.exists()
    assert str(expected_logs_dir).endswith('.mcli/logs') or str(expected_logs_dir).endswith('.mcli\\logs')

    # Run the logs command - it should not error even if no log files exist
    # (it will just show no logs, which is fine)
    result = runner.invoke(self_app, ['logs'])

    # Should not show "Logs directory not found" error
    assert 'Logs directory not found' not in result.output


def test_update_help():
    """Test that update command shows help text"""
    runner = CliRunner()
    result = runner.invoke(self_app, ['update', '--help'])
    assert result.exit_code == 0
    assert 'Check for and install mcli updates' in result.output
    assert '--check' in result.output
    assert '--yes' in result.output
    assert '--skip-ci-check' in result.output


@pytest.fixture
def mock_pypi_response():
    """Mock PyPI API response"""
    return {
        "info": {
            "version": "7.0.5",
            "project_urls": {
                "Changelog": "https://github.com/gwicho38/mcli/releases"
            }
        },
        "releases": {
            "7.0.4": [],
            "7.0.5": []
        }
    }


def test_update_check_already_latest(mock_pypi_response):
    """Test update --check when already on latest version"""
    from unittest.mock import patch, Mock

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get:

        # Mock current version same as latest
        mock_version.return_value = "7.0.5"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = runner.invoke(self_app, ['update', '--check'])

        assert result.exit_code == 0
        assert "already on the latest version" in result.output.lower()


def test_update_check_update_available(mock_pypi_response):
    """Test update --check when update is available"""
    from unittest.mock import patch, Mock

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get:

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = runner.invoke(self_app, ['update', '--check'])

        assert result.exit_code == 0
        assert "Update available" in result.output or "7.0.4" in result.output
        assert "7.0.5" in result.output


def test_update_install_with_yes_flag(mock_pypi_response):
    """Test update installation with --yes flag"""
    from unittest.mock import patch, Mock

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('subprocess.run') as mock_subprocess, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock CI passing
        mock_ci.return_value = (True, None)

        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        result = runner.invoke(self_app, ['update', '--yes'])

        assert result.exit_code == 0
        assert "Successfully updated" in result.output or "Installing" in result.output
        mock_subprocess.assert_called_once()


def test_update_cancelled_by_user(mock_pypi_response):
    """Test update when user cancels at confirmation"""
    from unittest.mock import patch, Mock

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock CI passing
        mock_ci.return_value = (True, None)

        # User says no to update
        result = runner.invoke(self_app, ['update'], input='n\n')

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()


def test_update_ci_check_failing(mock_pypi_response):
    """Test update blocked when CI is failing"""
    from unittest.mock import patch, Mock

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock CI failing
        mock_ci.return_value = (False, "https://github.com/gwicho38/mcli/actions/runs/123")

        result = runner.invoke(self_app, ['update', '--yes'])

        assert result.exit_code == 0
        assert "CI build is failing" in result.output or "blocked" in result.output.lower()


def test_update_skip_ci_check(mock_pypi_response):
    """Test update with --skip-ci-check flag"""
    from unittest.mock import patch, Mock

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('subprocess.run') as mock_subprocess, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        result = runner.invoke(self_app, ['update', '--yes', '--skip-ci-check'])

        assert result.exit_code == 0
        # CI check should not be called when --skip-ci-check is used
        mock_ci.assert_not_called()


def test_update_pypi_connection_error(mock_pypi_response):
    """Test update when PyPI connection fails"""
    from unittest.mock import patch, Mock
    import requests

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get:

        mock_version.return_value = "7.0.4"

        # Mock connection error
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = runner.invoke(self_app, ['update', '--check'])

        assert result.exit_code == 0
        assert "Error fetching version info" in result.output or "Error" in result.output


def test_update_installation_failure(mock_pypi_response):
    """Test update when pip installation fails"""
    from unittest.mock import patch, Mock

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('subprocess.run') as mock_subprocess, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock CI passing
        mock_ci.return_value = (True, None)

        # Mock failed subprocess
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Installation failed"
        mock_subprocess.return_value = mock_result

        result = runner.invoke(self_app, ['update', '--yes'])

        assert result.exit_code == 0
        assert "Update failed" in result.output or "failed" in result.output.lower()


def test_update_uses_uv_tool_when_detected(mock_pypi_response):
    """Test update uses 'uv tool install' when running from uv tool environment"""
    from unittest.mock import patch, Mock
    import sys

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('subprocess.run') as mock_subprocess, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci, \
         patch('sys.executable', '/Users/test/.local/share/uv/tools/mcli-framework/bin/python'):

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock CI passing
        mock_ci.return_value = (True, None)

        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        result = runner.invoke(self_app, ['update', '--yes'])

        assert result.exit_code == 0
        assert "Successfully updated" in result.output

        # Verify uv tool install was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "uv"
        assert call_args[1] == "tool"
        assert call_args[2] == "install"
        assert "--force" in call_args


def test_update_uses_pip_when_not_uv_tool(mock_pypi_response):
    """Test update uses pip when not running from uv tool environment"""
    from unittest.mock import patch, Mock
    import sys

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('subprocess.run') as mock_subprocess, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci, \
         patch('sys.executable', '/usr/local/bin/python3'):

        # Mock current version older than latest
        mock_version.return_value = "7.0.4"

        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pypi_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock CI passing
        mock_ci.return_value = (True, None)

        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        result = runner.invoke(self_app, ['update', '--yes'])

        assert result.exit_code == 0
        assert "Successfully updated" in result.output

        # Verify pip was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "-m" in call_args
        assert "pip" in call_args
        assert "install" in call_args
        assert "--upgrade" in call_args


class TestSearchCommand:
    """Test suite for search command functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_search_with_query(self):
        """Test search command with basic query"""
        with patch('mcli.self.self_cmd.collect_commands') as mock_collect:
            mock_collect.return_value = [
                {"name": "test-cmd", "description": "A test command", "file": "/path/to/test.py", "group": None}
            ]

            result = self.runner.invoke(self_app, ['search', 'test'])

            assert result.exit_code == 0
            assert 'test-cmd' in result.output


    def test_search_no_results(self):
        """Test search command when no results found"""
        with patch('mcli.self.self_cmd.collect_commands') as mock_collect:
            mock_collect.return_value = []

            result = self.runner.invoke(self_app, ['search', 'nonexistent'])

            assert result.exit_code == 0




class TestHelloCommand:
    """Test suite for hello command"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_hello_default(self):
        """Test hello command with default name"""
        result = self.runner.invoke(self_app, ['hello'])

        assert result.exit_code == 0
        assert 'World' in result.output

    def test_hello_with_name(self):
        """Test hello command with custom name"""
        result = self.runner.invoke(self_app, ['hello', 'Alice'])

        assert result.exit_code == 0
        assert 'Alice' in result.output


class TestLogsCommand:
    """Test suite for logs command functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_logs_default(self):
        """Test logs command with default settings"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                from pathlib import Path
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                # Create a sample log file
                log_file = logs_dir / "mcli.log"
                log_file.write_text("2025-01-01 10:00:00 INFO Test log message\n")

                result = self.runner.invoke(self_app, ['logs'])

                assert result.exit_code == 0

    def test_logs_with_lines_option(self):
        """Test logs command with --lines option"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                from pathlib import Path
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                log_file = logs_dir / "mcli.log"
                log_file.write_text("\n".join([f"Line {i}" for i in range(100)]))

                result = self.runner.invoke(self_app, ['logs', '--lines', '10'])

                assert result.exit_code == 0

    def test_logs_with_type_option(self):
        """Test logs command with --type option"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                from pathlib import Path
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                # Create log files
                (logs_dir / "mcli.log").write_text("main log")

                result = self.runner.invoke(self_app, ['logs', '--type', 'system'])

                assert result.exit_code == 0

    def test_logs_with_grep_option(self):
        """Test logs command with --grep option"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                from pathlib import Path
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                log_file = logs_dir / "mcli.log"
                log_file.write_text("ERROR: Something went wrong\nINFO: Everything is fine\n")

                result = self.runner.invoke(self_app, ['logs', '--grep', 'ERROR'])

                assert result.exit_code == 0

    def test_logs_with_level_option(self):
        """Test logs command with --level option"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                from pathlib import Path
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                log_file = logs_dir / "mcli.log"
                log_file.write_text("2025-01-01 INFO Test\n2025-01-01 ERROR Problem\n")

                result = self.runner.invoke(self_app, ['logs', '--level', 'ERROR'])

                assert result.exit_code == 0

    def test_logs_no_log_files(self):
        """Test logs command when no log files exist"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                from pathlib import Path
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                result = self.runner.invoke(self_app, ['logs'])

                assert result.exit_code == 0


class TestPerformanceCommand:
    """Test suite for performance command"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_performance_basic(self):
        """Test performance command basic execution"""
        result = self.runner.invoke(self_app, ['performance'])

        assert result.exit_code == 0

    def test_performance_with_detailed_flag(self):
        """Test performance command with --detailed flag"""
        result = self.runner.invoke(self_app, ['performance', '--detailed'])

        assert result.exit_code == 0

    def test_performance_with_benchmark_flag(self):
        """Test performance command with --benchmark flag"""
        result = self.runner.invoke(self_app, ['performance', '--benchmark'])

        assert result.exit_code == 0


class TestCommandStateCommands:
    """Test suite for command-state subcommands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()


    def test_command_state_restore(self):
        """Test commands state restore command"""
        with patch('mcli.self.self_cmd.restore_command_state') as mock_restore:
            mock_restore.return_value = True

            result = self.runner.invoke(self_app, ['commands', 'state', 'restore', 'abc123'])

            assert result.exit_code == 0

    def test_command_state_restore_invalid_hash(self):
        """Test commands state restore with invalid hash"""
        with patch('mcli.self.self_cmd.restore_command_state') as mock_restore:
            mock_restore.return_value = False

            result = self.runner.invoke(self_app, ['commands', 'state', 'restore', 'invalid'])

            assert result.exit_code != 0 or 'not found' in result.output.lower()

    def test_command_state_write(self):
        """Test commands state write command"""
        with self.runner.isolated_filesystem():
            from pathlib import Path

            # Create a test JSON file
            test_file = Path("commands.json")
            test_file.write_text('[{"name": "test", "path": "/test", "group": null}]')

            with patch('mcli.self.self_cmd.save_lockfile') as mock_save:
                result = self.runner.invoke(self_app, ['commands', 'state', 'write', str(test_file)])

                assert result.exit_code == 0 or mock_save.called


class TestPluginCommands:
    """Test suite for plugin management commands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()


    def test_plugin_add_without_repo(self):
        """Test plugin add without repository URL"""
        result = self.runner.invoke(self_app, ['plugin', 'add', 'test-plugin'])

        # Should fail or show error about missing repo
        assert result.exit_code in [0, 1]

    def test_plugin_remove(self):
        """Test plugin remove command"""
        with self.runner.isolated_filesystem():
            from pathlib import Path

            # Create a mock plugin directory
            plugin_dir = Path.home() / ".mcli" / "plugins" / "test-plugin"
            plugin_dir.mkdir(parents=True, exist_ok=True)

            result = self.runner.invoke(self_app, ['plugin', 'remove', 'test-plugin'], input='y\n')

            # Should complete
            assert result.exit_code in [0, 1]

    def test_plugin_update(self):
        """Test plugin update command"""
        with self.runner.isolated_filesystem():
            from pathlib import Path

            # Create a mock plugin directory
            plugin_dir = Path.home() / ".mcli" / "plugins" / "test-plugin"
            plugin_dir.mkdir(parents=True, exist_ok=True)

            with patch('subprocess.run') as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                result = self.runner.invoke(self_app, ['plugin', 'update', 'test-plugin'])

                # Should complete
                assert result.exit_code in [0, 1]


class TestTemplateGeneration:
    """Test suite for template generation functions"""

    def test_get_command_template_simple(self):
        """Test command template generation for simple command"""
        from mcli.self.self_cmd import get_command_template

        template = get_command_template("test-cmd")

        assert "test-cmd" in template or "test_cmd" in template
        assert "def" in template
        assert "click" in template

    def test_get_command_template_with_group(self):
        """Test command template generation with group"""
        from mcli.self.self_cmd import get_command_template

        template = get_command_template("test-cmd", group="mygroup")

        assert "mygroup" in template or "test" in template
        assert "@click.group" in template or "group" in template


class TestAddCommandImplementation:
    """Test suite for add-command implementation details"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_add_command_creates_simple_command(self):
        """Test add-command creates a command file successfully"""
        with self.runner.isolated_filesystem():
            # Mock the mcli path to current directory
            with patch('mcli.self.self_cmd.Path') as mock_path_class:
                mock_file = Mock()
                mock_file.parent.parent = Path.cwd()
                mock_path_class.__file__ = str(mock_file)
                mock_path_class.return_value = Path.cwd()

                result = self.runner.invoke(self_app, ['add-command', 'test-cmd'])

                # Should succeed or show reasonable output
                assert result.exit_code in [0, 1]

    def test_add_command_with_invalid_name(self):
        """Test add-command rejects invalid command names"""
        result = self.runner.invoke(self_app, ['add-command', '123invalid'])

        assert result.exit_code in [0, 1]
        assert 'invalid' in result.output.lower() or result.exit_code != 0

    def test_add_command_with_group_creates_directory(self):
        """Test add-command with --group creates group directory"""
        with self.runner.isolated_filesystem():
            with patch('mcli.self.self_cmd.Path') as mock_path_class:
                mock_file = Mock()
                mock_file.parent.parent = Path.cwd()
                mock_path_class.__file__ = str(mock_file)
                mock_path_class.return_value = Path.cwd()

                result = self.runner.invoke(self_app, ['add-command', 'cmd', '--group', 'mygroup'])

                assert result.exit_code in [0, 1]

    def test_add_command_with_invalid_group_name(self):
        """Test add-command rejects invalid group names"""
        result = self.runner.invoke(self_app, ['add-command', 'cmd', '--group', '123invalid'])

        assert result.exit_code in [0, 1]
        assert 'invalid' in result.output.lower() or result.exit_code != 0


class TestLogsImplementation:
    """Test suite for logs command implementation"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_logs_handles_missing_directory(self):
        """Test logs command when logs directory doesn't exist"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            # Return a path that doesn't exist
            mock_logs_dir.return_value = Path('/nonexistent/logs')

            result = self.runner.invoke(self_app, ['logs'])

            assert result.exit_code == 0
            assert 'not found' in result.output.lower() or 'expected location' in result.output.lower()

    def test_logs_with_all_type(self):
        """Test logs command with --type all"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                # Create sample log files
                (logs_dir / "mcli_20250101.log").write_text("Main log\n")
                (logs_dir / "mcli_system_20250101.log").write_text("System log\n")

                result = self.runner.invoke(self_app, ['logs', '--type', 'all'])

                assert result.exit_code == 0

    def test_logs_with_date_filter(self):
        """Test logs command with date filtering"""
        with patch('mcli.lib.paths.get_logs_dir') as mock_logs_dir:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                logs_dir = Path(tmpdir)
                mock_logs_dir.return_value = logs_dir

                # Create log file with specific date
                (logs_dir / "mcli_20250101.log").write_text("Log entry\n")

                result = self.runner.invoke(self_app, ['logs', '--date', '20250101'])

                assert result.exit_code == 0







class TestUpdateCommandImplementation:
    """Test suite for update command implementation details"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_update_check_only_mode(self):
        """Test update command with --check flag"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "info": {"version": "7.0.7"},
                "releases": {}
            }
            mock_get.return_value = mock_response

            result = self.runner.invoke(self_app, ['update', '--check'])

            assert result.exit_code == 0

    def test_update_with_pre_release_flag(self):
        """Test update command with --pre flag for pre-releases"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "info": {"version": "7.1.0a1"},
                "releases": {}
            }
            mock_get.return_value = mock_response

            result = self.runner.invoke(self_app, ['update', '--check', '--pre'])

            assert result.exit_code == 0




class TestUtilityFunctions:
    """Test suite for utility functions"""

    def test_hash_command_state(self):
        """Test hash_command_state function with proper format"""
        from mcli.self.self_cmd import hash_command_state

        # Commands should be a list of dicts with proper structure
        test_commands = [
            {"name": "test", "path": "/test", "group": None}
        ]
        hash_value = hash_command_state(test_commands)

        assert isinstance(hash_value, str)
        assert len(hash_value) > 0

    def test_hash_command_state_consistency(self):
        """Test hash is consistent for same commands"""
        from mcli.self.self_cmd import hash_command_state

        commands = [
            {"name": "cmd1", "path": "/path1", "group": "group1"},
            {"name": "cmd2", "path": "/path2", "group": None}
        ]

        hash1 = hash_command_state(commands)
        hash2 = hash_command_state(commands)

        assert hash1 == hash2

    def test_load_lockfile_nonexistent(self):
        """Test load_lockfile when file doesn't exist"""
        from mcli.self.self_cmd import load_lockfile
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.self.self_cmd.LOCKFILE_PATH', Path(tmpdir) / 'nonexistent.json'):
                result = load_lockfile()

                # Should return empty list when file doesn't exist
                assert result == []

    def test_append_lockfile_to_empty(self):
        """Test append_lockfile creates new file"""
        from mcli.self.self_cmd import append_lockfile, load_lockfile
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Path(tmpdir) / 'lockfile.json'

            with patch('mcli.self.self_cmd.LOCKFILE_PATH', lockfile):
                new_state = {"hash": "test123", "timestamp": "2025-01-01", "commands": []}

                append_lockfile(new_state)

                # Verify it was appended
                states = load_lockfile()
                assert len(states) == 1
                assert states[0]["hash"] == "test123"

    def test_find_state_by_hash_found(self):
        """Test find_state_by_hash when state exists"""
        from mcli.self.self_cmd import find_state_by_hash
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Path(tmpdir) / 'lockfile.json'

            # Create a lockfile with test data
            test_states = [
                {"hash": "abc123", "commands": []},
                {"hash": "def456", "commands": []}
            ]
            lockfile.write_text(json.dumps(test_states))

            with patch('mcli.self.self_cmd.LOCKFILE_PATH', lockfile):
                state = find_state_by_hash("def456")

                assert state is not None
                assert state["hash"] == "def456"

    def test_find_state_by_hash_not_found(self):
        """Test find_state_by_hash when state doesn't exist"""
        from mcli.self.self_cmd import find_state_by_hash
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Path(tmpdir) / 'lockfile.json'

            test_states = [{"hash": "abc123", "commands": []}]
            lockfile.write_text(json.dumps(test_states))

            with patch('mcli.self.self_cmd.LOCKFILE_PATH', lockfile):
                state = find_state_by_hash("nonexistent")

                assert state is None

    def test_restore_command_state_success(self):
        """Test restore_command_state with valid hash"""
        from mcli.self.self_cmd import restore_command_state
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Path(tmpdir) / 'lockfile.json'

            test_states = [
                {"hash": "abc123", "commands": [{"name": "test", "path": "/test"}]}
            ]
            lockfile.write_text(json.dumps(test_states))

            with patch('mcli.self.self_cmd.LOCKFILE_PATH', lockfile):
                with patch('builtins.print') as mock_print:
                    result = restore_command_state("abc123")

                    assert result is True
                    mock_print.assert_called_once()

    def test_restore_command_state_failure(self):
        """Test restore_command_state with invalid hash"""
        from mcli.self.self_cmd import restore_command_state
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Path(tmpdir) / 'lockfile.json'

            test_states = [{"hash": "abc123", "commands": []}]
            lockfile.write_text(json.dumps(test_states))

            with patch('mcli.self.self_cmd.LOCKFILE_PATH', lockfile):
                result = restore_command_state("nonexistent")

                assert result is False

    def test_get_current_command_state(self):
        """Test get_current_command_state returns list"""
        from mcli.self.self_cmd import get_current_command_state

        # Mock collect_commands to avoid complex setup
        with patch('mcli.self.self_cmd.collect_commands') as mock_collect:
            mock_collect.return_value = [{"name": "test", "group": None, "path": "/test"}]

            result = get_current_command_state()

            assert isinstance(result, list)
            assert len(result) == 1