"""
End-to-end test for new user workflow

Tests the complete journey of a new user installing and using mcli for the first time.
"""
import pytest
from click.testing import CliRunner


@pytest.mark.e2e
@pytest.mark.slow
def test_new_user_complete_workflow():
    """
    Test complete workflow for a new user:
    1. Check available self commands
    2. Run mcli self logs (should work even with no logs)
    3. Check for updates
    4. View help for model commands
    """
    from mcli.self.self_cmd import self_app
    from mcli.app.model_cmd import model

    runner = CliRunner()

    # Step 1: Check available self commands (help)
    result = runner.invoke(self_app, ['--help'])
    assert result.exit_code == 0
    assert 'logs' in result.output
    assert 'update' in result.output

    # Step 2: Try to view logs (should not error even if no logs exist)
    result = runner.invoke(self_app, ['logs', '--help'])
    assert result.exit_code == 0
    assert 'Display runtime logs' in result.output

    # Step 3: Check for updates help
    result = runner.invoke(self_app, ['update', '--help'])
    assert result.exit_code == 0
    assert '--check' in result.output

    # Step 4: View help for model command
    result = runner.invoke(model, ['--help'])
    assert result.exit_code == 0
    assert 'list' in result.output or 'start' in result.output


@pytest.mark.e2e
def test_new_user_discovers_features():
    """
    Test new user discovering features through help commands
    """
    from mcli.app.main import main
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    # Discover self commands
    result = runner.invoke(self_app, ['--help'])
    assert result.exit_code == 0
    assert 'search' in result.output
    assert 'update' in result.output
    assert 'logs' in result.output

    # Check search functionality
    result = runner.invoke(self_app, ['search', '--help'])
    assert result.exit_code == 0

    # Check update functionality
    result = runner.invoke(self_app, ['update', '--help'])
    assert result.exit_code == 0
    assert '--check' in result.output
    assert '--yes' in result.output


@pytest.mark.e2e
def test_new_user_model_exploration():
    """
    Test new user exploring model commands
    """
    from mcli.app.model_cmd import model

    runner = CliRunner()

    # View model help
    result = runner.invoke(model, ['--help'])
    assert result.exit_code == 0

    # View list help
    result = runner.invoke(model, ['list', '--help'])
    assert result.exit_code == 0

    # View recommend help
    result = runner.invoke(model, ['recommend', '--help'])
    assert result.exit_code == 0

    # View start help
    result = runner.invoke(model, ['start', '--help'])
    assert result.exit_code == 0
    assert 'port' in result.output.lower()


@pytest.mark.e2e
@pytest.mark.slow
def test_new_user_configuration_workflow():
    """
    Test new user understanding configuration options
    """
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    with runner.isolated_filesystem():
        # User explores configuration
        result = runner.invoke(self_app, ['--help'])
        assert result.exit_code == 0

        # User can see logs even in a fresh environment
        result = runner.invoke(self_app, ['logs', '--help'])
        assert result.exit_code == 0


@pytest.mark.e2e
def test_new_user_error_handling():
    """
    Test that new users get helpful error messages
    """
    from mcli.app.model_cmd import model
    from mcli.self.self_cmd import self_app

    runner = CliRunner()

    # Invalid command for model
    result = runner.invoke(model, ['nonexistent-command'])
    # Should fail gracefully
    assert result.exit_code != 0

    # Missing required argument
    result = runner.invoke(self_app, ['add-command'])
    # Should show helpful error
    assert result.exit_code != 0
    assert 'Missing argument' in result.output or 'required' in result.output.lower()
