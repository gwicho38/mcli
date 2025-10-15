import pytest
from click.testing import CliRunner

from mcli.public.oi.oi import oi


def test_oi_group_help():
    runner = CliRunner()
    result = runner.invoke(oi, ["--help"])
    assert result.exit_code == 0
    assert "Create an alpha tunnel using the instance" in result.output
