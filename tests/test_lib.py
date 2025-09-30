import pytest
from click.testing import CliRunner
from mcli.lib.lib import lib


def test_lib_group_help():
    runner = CliRunner()
    result = runner.invoke(lib, ['--help'])
    assert result.exit_code == 0 