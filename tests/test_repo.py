import pytest
from click.testing import CliRunner
from mcli.workflow.repo.repo import repo


def test_repo_group_help():
    runner = CliRunner()
    result = runner.invoke(repo, ['--help'])
    assert result.exit_code == 0
    assert 'repo utility' in result.output


def test_analyze_help():
    runner = CliRunner()
    result = runner.invoke(repo, ['analyze', '--help'])
    assert result.exit_code == 0
    assert 'Provides a source lines of code analysis' in result.output


def test_analyze_missing_required():
    runner = CliRunner()
    result = runner.invoke(repo, ['analyze'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_worktree_help():
    runner = CliRunner()
    result = runner.invoke(repo, ['wt', '--help'])
    assert result.exit_code == 0
    assert 'Create and manage worktrees' in result.output


def test_commit_help():
    runner = CliRunner()
    result = runner.invoke(repo, ['commit', '--help'])
    assert result.exit_code == 0
    assert 'Edit commits to a repository' in result.output


def test_revert_help():
    runner = CliRunner()
    result = runner.invoke(repo, ['revert', '--help'])
    assert result.exit_code == 0
    assert 'Create and manage worktrees' in result.output


def test_migration_loe_help():
    runner = CliRunner()
    result = runner.invoke(repo, ['migration-loe', '--help'])
    assert result.exit_code == 0
    assert 'Create and manage worktrees' in result.output


def test_migration_loe_missing_required():
    runner = CliRunner()
    result = runner.invoke(repo, ['migration-loe'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output 