import pytest
from click.testing import CliRunner
from mcli.workflow.gcloud.gcloud import gcloud


def test_gcloud_group_help():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['--help'])
    assert result.exit_code == 0
    assert 'gcloud utility' in result.output


def test_start_help():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['start', '--help'])
    assert result.exit_code == 0
    assert 'Start a gcloud instance' in result.output


def test_stop_help():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['stop', '--help'])
    assert result.exit_code == 0
    assert 'Start a gcloud instance' in result.output


def test_describe_help():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['describe', '--help'])
    assert result.exit_code == 0
    assert 'Start a gcloud instance' in result.output


def test_tunnel_help():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['tunnel', '--help'])
    assert result.exit_code == 0
    assert 'Create an alpha tunnel using the instance' in result.output


def test_tunnel_missing_required():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['tunnel'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_login_help():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['login', '--help'])
    assert result.exit_code == 0
    assert 'Login to gcloud' in result.output


def test_login_missing_required():
    runner = CliRunner()
    result = runner.invoke(gcloud, ['login'])
    assert result.exit_code != 0 