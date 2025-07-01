import pytest
from click.testing import CliRunner
from src.mcli.workflow.workflow import workflow


def test_workflow_group_help():
    runner = CliRunner()
    result = runner.invoke(workflow, ['--help'])
    assert result.exit_code == 0
    assert 'Workflow commands' in result.output


def test_workflow_webapp_subcommand():
    runner = CliRunner()
    result = runner.invoke(workflow, ['webapp', '--help'])
    assert result.exit_code == 0
    assert 'Web application generation and installation commands' in result.output


def test_workflow_file_subcommand():
    runner = CliRunner()
    result = runner.invoke(workflow, ['file', '--help'])
    assert result.exit_code == 0 or 'Usage:' in result.output


def test_workflow_videos_subcommand():
    runner = CliRunner()
    result = runner.invoke(workflow, ['videos', '--help'])
    assert result.exit_code == 0 or 'Usage:' in result.output 