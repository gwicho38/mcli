import pytest
from click.testing import CliRunner
from mcli.workflow.wakatime.wakatime import wakatime


def test_wakatime_group_help():
    runner = CliRunner()
    result = runner.invoke(wakatime, ['--help'])
    assert result.exit_code == 0
    assert 'WakaTime commands' in result.output 