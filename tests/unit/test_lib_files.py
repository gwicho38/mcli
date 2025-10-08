"""
Unit tests for mcli.workflow.file.file module

NOTE: This module has been migrated to portable JSON commands.
Tests are skipped as the Python module no longer exists.
"""

import pytest

# Skip all tests in this module - file commands now loaded from JSON
pytestmark = pytest.mark.skip(reason="file commands migrated to portable JSON format")


def test_file_group_help():
    runner = CliRunner()
    result = runner.invoke(file, ['--help'])
    assert result.exit_code == 0
    assert 'Personal file utility' in result.output


def test_oxps_to_pdf_help():
    runner = CliRunner()
    result = runner.invoke(file, ['oxps-to-pdf', '--help'])
    assert result.exit_code == 0
    assert 'Converts an OXPS file' in result.output


def test_oxps_to_pdf_missing_required():
    runner = CliRunner()
    result = runner.invoke(file, ['oxps-to-pdf'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_search_help():
    runner = CliRunner()
    result = runner.invoke(file, ['search', '--help'])
    assert result.exit_code == 0
    assert 'Search for a string with ripgrep' in result.output


def test_search_missing_required():
    runner = CliRunner()
    result = runner.invoke(file, ['search'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output 