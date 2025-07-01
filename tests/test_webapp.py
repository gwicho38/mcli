import pytest
from click.testing import CliRunner
from src.mcli.workflow.webapp.webapp import webapp
import os
from pathlib import Path


def test_webapp_group_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['--help'])
    assert result.exit_code == 0
    assert 'Web application generation and installation commands' in result.output


def test_generate_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['generate', '--help'])
    assert result.exit_code == 0
    assert 'Generate a template web application' in result.output


def test_generate_missing_required():
    runner = CliRunner()
    result = runner.invoke(webapp, ['generate'])
    assert result.exit_code != 0
    assert 'Missing option' in result.output


def test_list_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['list', '--help'])
    assert result.exit_code == 0
    assert 'List all generated web applications' in result.output


def test_delete_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['delete', '--help'])
    assert result.exit_code == 0
    assert 'Delete a generated web application' in result.output


def test_install_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['install', '--help'])
    assert result.exit_code == 0
    assert 'Install a generated web application' in result.output


def test_run_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['run', '--help'])
    assert result.exit_code == 0
    assert 'Run a generated web application in development mode' in result.output

# More detailed tests (e.g., for actual generation, install, delete) would use tmp_path and monkeypatch for isolation and to avoid side effects. 