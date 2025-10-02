"""
End-to-end test for update workflow

Tests the complete mcli self-update process.
"""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock


@pytest.mark.e2e
def test_update_check_workflow():
    """
    Test complete update check workflow:
    1. Check current version
    2. Check for updates
    3. Review update information
    """
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get:

        # Mock current version
        mock_version.return_value = "7.0.5"

        # Mock PyPI response with newer version
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "version": "7.0.6",
                "project_urls": {
                    "Changelog": "https://github.com/gwicho38/mcli/releases"
                }
            },
            "releases": {
                "7.0.5": [],
                "7.0.6": []
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Step 1: Check for updates
        result = runner.invoke(self_app, ['update', '--check'])

        # Should show update available
        assert result.exit_code == 0
        assert '7.0.6' in result.output
        assert any(word in result.output.lower() for word in ['update', 'available', 'newer'])


@pytest.mark.e2e
def test_update_with_confirmation_workflow():
    """
    Test update workflow with user confirmation
    """
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Setup mocks
        mock_version.return_value = "7.0.5"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"version": "7.0.6", "project_urls": {}},
            "releases": {"7.0.5": [], "7.0.6": []}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_ci.return_value = (True, None)

        # User says no to update
        result = runner.invoke(self_app, ['update'], input='n\n')

        assert result.exit_code == 0
        assert 'cancelled' in result.output.lower() or 'abort' in result.output.lower()


@pytest.mark.e2e
def test_update_with_ci_check_workflow():
    """
    Test update workflow with CI status checking
    """
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Setup mocks
        mock_version.return_value = "7.0.5"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"version": "7.0.6", "project_urls": {}},
            "releases": {"7.0.5": [], "7.0.6": []}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock CI failing
        mock_ci.return_value = (False, "https://github.com/gwicho38/mcli/actions")

        # Try to update with failing CI
        result = runner.invoke(self_app, ['update', '--yes'])

        # Should be blocked
        assert result.exit_code == 0
        assert any(word in result.output.lower() for word in ['ci', 'failing', 'blocked'])


@pytest.mark.e2e
def test_update_skip_ci_check_workflow():
    """
    Test update workflow skipping CI check
    """
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get, \
         patch('subprocess.run') as mock_subprocess, \
         patch('mcli.self.self_cmd.check_ci_status') as mock_ci:

        # Setup mocks
        mock_version.return_value = "7.0.5"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"version": "7.0.6", "project_urls": {}},
            "releases": {"7.0.5": [], "7.0.6": []}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Use --skip-ci-check flag
        result = runner.invoke(self_app, ['update', '--yes', '--skip-ci-check'])

        # CI check should not be called
        mock_ci.assert_not_called()

        # Update should proceed
        assert result.exit_code == 0


@pytest.mark.e2e
def test_already_latest_version_workflow():
    """
    Test workflow when already on latest version
    """
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    with patch('importlib.metadata.version') as mock_version, \
         patch('requests.get') as mock_get:

        # Mock same version
        mock_version.return_value = "7.0.6"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"version": "7.0.6", "project_urls": {}},
            "releases": {"7.0.6": []}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = runner.invoke(self_app, ['update', '--check'])

        assert result.exit_code == 0
        assert any(word in result.output.lower() for word in ['latest', 'up to date', 'already'])
