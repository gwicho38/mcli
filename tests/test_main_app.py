import pytest
from click.testing import CliRunner
from src.mcli.app.main import create_app


def test_main_app_help():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'mcli' in result.output


def test_hello_command():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ['hello'])
    assert result.exit_code == 0
    assert 'Hello from mcli!' in result.output


def test_version_command():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ['version'])
    assert result.exit_code == 0
    assert 'mcli version' in result.output


def test_version_verbose():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ['version', '--verbose'])
    assert result.exit_code == 0
    assert 'mcli version' in result.output
    assert 'Python:' in result.output 