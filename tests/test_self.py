import pytest
from click.testing import CliRunner
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
    assert 'Generate a new command template' in result.output


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