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