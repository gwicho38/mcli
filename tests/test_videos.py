import pytest
from click.testing import CliRunner
from mcli.workflow.videos.videos import videos


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