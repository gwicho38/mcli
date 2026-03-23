"""Tests for the onboarding wizard (mcli setup)."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


class TestSetupCommand:
    """Test the mcli setup command."""

    def test_minimal_setup_creates_dirs(self, runner, tmp_path, monkeypatch):
        """--minimal creates home dir and workflows dir."""
        monkeypatch.setenv("MCLI_HOME", str(tmp_path / "mcli-home"))
        monkeypatch.delenv("MCLI_ENV", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)

        from mcli.lib.config.settings import reset_settings

        reset_settings()

        from mcli.app.setup_cmd import setup

        result = runner.invoke(setup, ["--minimal"])
        assert result.exit_code == 0
        assert (tmp_path / "mcli-home").exists()
        assert (tmp_path / "mcli-home" / "workflows").exists()

    def test_minimal_setup_writes_config_toml(self, runner, tmp_path, monkeypatch):
        """--minimal creates config.toml with default included_dirs."""
        monkeypatch.setenv("MCLI_HOME", str(tmp_path / "mcli-home"))
        monkeypatch.delenv("MCLI_ENV", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)

        from mcli.lib.config.settings import reset_settings

        reset_settings()

        from mcli.app.setup_cmd import setup

        result = runner.invoke(setup, ["--minimal"])
        assert result.exit_code == 0

        config_toml = tmp_path / "mcli-home" / "config.toml"
        assert config_toml.exists()
        content = config_toml.read_text()
        assert "included_dirs" in content
        assert '"app"' in content

    def test_write_env_file_preserves_existing(self, tmp_path):
        """_write_env_file merges with existing keys."""
        from mcli.app.setup_cmd import _write_env_file

        env_path = tmp_path / ".env"
        env_path.write_text("EXISTING_KEY=value\n")

        _write_env_file({"NEW_KEY": "new_value"}, env_path)

        content = env_path.read_text()
        assert "EXISTING_KEY=value" in content
        assert "NEW_KEY=new_value" in content

    def test_write_config_toml(self, tmp_path):
        """_write_config_toml writes valid TOML."""
        from mcli.app.setup_cmd import _write_config_toml

        config_path = tmp_path / "config.toml"
        _write_config_toml(["app", "self", "workflow"], config_path)

        content = config_path.read_text()
        assert "[paths]" in content
        assert '"app"' in content
        assert '"workflow"' in content

    def test_setup_registered_in_cli(self):
        """setup command is registered in the main CLI group."""
        from mcli.app.main import create_app

        app = create_app()
        assert "setup" in [cmd for cmd in app.commands]
