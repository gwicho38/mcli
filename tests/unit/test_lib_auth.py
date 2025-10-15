import pytest
from click.testing import CliRunner

from mcli.lib.auth.auth import auth


def test_auth_group_help():
    runner = CliRunner()
    result = runner.invoke(auth, ["--help"])
    assert result.exit_code == 0
    assert "Authentication commands" in result.output
