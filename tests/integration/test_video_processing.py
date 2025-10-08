"""
Integration tests for mcli.workflow.videos module

NOTE: This module has been migrated to portable JSON commands.
Tests are skipped as the Python module no longer exists.
"""

import pytest

# Skip all tests in this module - videos commands now loaded from JSON
pytestmark = pytest.mark.skip(reason="videos commands migrated to portable JSON format")


def test_videos_group_help():
    runner = CliRunner()
    result = runner.invoke(videos, ['--help'])
    assert result.exit_code == 0
    assert 'Video processing and overlay removal tools' in result.output


def test_remove_overlay_help():
    runner = CliRunner()
    result = runner.invoke(videos, ['remove-overlay', '--help'])
    assert result.exit_code == 0
    assert 'Remove overlays from videos with intelligent content reconstruction' in result.output


def test_remove_overlay_missing_required():
    runner = CliRunner()
    result = runner.invoke(videos, ['remove-overlay'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_extract_frames_help():
    runner = CliRunner()
    result = runner.invoke(videos, ['extract-frames', '--help'])
    assert result.exit_code == 0
    assert 'Extract frames from video to timestamped directory' in result.output


def test_extract_frames_missing_required():
    runner = CliRunner()
    result = runner.invoke(videos, ['extract-frames'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output


def test_frames_to_video_help():
    runner = CliRunner()
    result = runner.invoke(videos, ['frames-to-video', '--help'])
    assert result.exit_code == 0
    assert 'Convert frames back to video' in result.output


def test_frames_to_video_missing_required():
    runner = CliRunner()
    result = runner.invoke(videos, ['frames-to-video'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output 