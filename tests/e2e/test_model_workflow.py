"""
End-to-end test for model server workflow

Tests the complete lifecycle of using the model server.
"""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock, MagicMock


@pytest.mark.e2e
def test_model_list_and_recommend_workflow():
    """
    Test workflow of discovering available models
    """
    from mcli.app.model_cmd import model

    runner = CliRunner()

    # Step 1: List available models (just check help works)
    result = runner.invoke(model, ['list', '--help'])
    assert result.exit_code == 0

    # Step 2: Get recommendation help
    result = runner.invoke(model, ['recommend', '--help'])
    assert result.exit_code == 0


@pytest.mark.e2e
@pytest.mark.slow
def test_model_download_workflow():
    """
    Test workflow of downloading a model
    """
    from mcli.app.model_cmd import model

    runner = CliRunner()

    with patch('mcli.app.model_cmd.LightweightModelServer') as mock_server_class:
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.download_and_load_model.return_value = True

        result = runner.invoke(model, ['pull', 'distilbert-base-uncased'])

        assert result.exit_code == 0
        # Should indicate success
        assert 'success' in result.output.lower() or 'downloaded' in result.output.lower() or 'pulled' in result.output.lower()


@pytest.mark.e2e
def test_model_server_status_check_workflow():
    """
    Test workflow of checking server status
    """
    from mcli.app.model_cmd import model

    runner = CliRunner()

    # Check status when server not running
    with patch('requests.get') as mock_get:
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = runner.invoke(model, ['status', '--port', '51234'])

        # Should complete (may show not running)
        assert result.exit_code == 0


@pytest.mark.e2e
def test_model_delete_workflow():
    """
    Test workflow of deleting a downloaded model
    """
    from mcli.app.model_cmd import model

    runner = CliRunner()

    # Check delete help
    result = runner.invoke(model, ['delete', '--help'])
    assert result.exit_code == 0
    assert '--force' in result.output


@pytest.mark.e2e
def test_model_workflow_with_config():
    """
    Test that model commands accept port configuration
    """
    from mcli.app.model_cmd import model

    runner = CliRunner()

    # Check that start command accepts port flag
    result = runner.invoke(model, ['start', '--help'])
    assert result.exit_code == 0
    assert '--port' in result.output

    # Check that status command accepts port flag
    result = runner.invoke(model, ['status', '--help'])
    assert result.exit_code == 0
    assert '--port' in result.output

    # Check that stop command accepts port flag
    result = runner.invoke(model, ['stop', '--help'])
    assert result.exit_code == 0
    assert '--port' in result.output


@pytest.mark.e2e
@pytest.mark.slow
def test_complete_model_lifecycle():
    """
    Test complete model lifecycle help commands:
    1. List models
    2. Get recommendation
    3. Download model
    4. Check status
    5. Delete model
    """
    from mcli.app.model_cmd import model

    runner = CliRunner()

    # Step 1: List help
    result = runner.invoke(model, ['list', '--help'])
    assert result.exit_code == 0

    # Step 2: Recommend help
    result = runner.invoke(model, ['recommend', '--help'])
    assert result.exit_code == 0

    # Step 3: Download help
    result = runner.invoke(model, ['pull', '--help'])
    assert result.exit_code == 0

    # Step 4: Status help
    result = runner.invoke(model, ['status', '--help'])
    assert result.exit_code == 0

    # Step 5: Delete help
    result = runner.invoke(model, ['delete', '--help'])
    assert result.exit_code == 0
    assert '--force' in result.output
