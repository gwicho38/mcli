"""Unit tests for mcli self migrate --rename-dir functionality."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mcli.self.migrate_cmd import migrate_command


class TestMigrateRenameDir:
    """Tests for the --rename-dir flag on mcli self migrate."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_rename_dir_success(self, cli_runner, tmp_path):
        """Test successful rename of .mcli/ to mcli/."""
        (tmp_path / ".git").mkdir()
        old_dir = tmp_path / ".mcli"
        old_dir.mkdir()
        (old_dir / "workflows").mkdir()
        (old_dir / "workflows" / "test.py").write_text("print('hi')")

        with patch("mcli.lib.paths.is_git_repository", return_value=True):
            with patch("mcli.lib.paths.get_git_root", return_value=tmp_path):
                result = cli_runner.invoke(migrate_command, ["--rename-dir"])

        assert result.exit_code == 0
        assert "Renamed" in result.output
        assert not old_dir.exists()
        assert (tmp_path / "mcli").exists()
        assert (tmp_path / "mcli" / "workflows" / "test.py").exists()

    def test_rename_dir_dry_run(self, cli_runner, tmp_path):
        """Test --rename-dir with --dry-run shows what would happen."""
        (tmp_path / ".git").mkdir()
        old_dir = tmp_path / ".mcli"
        old_dir.mkdir()

        with patch("mcli.lib.paths.is_git_repository", return_value=True):
            with patch("mcli.lib.paths.get_git_root", return_value=tmp_path):
                result = cli_runner.invoke(migrate_command, ["--rename-dir", "--dry-run"])

        assert result.exit_code == 0
        assert "Would rename" in result.output
        assert old_dir.exists()  # Not actually renamed

    def test_rename_dir_already_migrated(self, cli_runner, tmp_path):
        """Test --rename-dir when mcli/ already exists and .mcli/ doesn't."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "mcli").mkdir()

        with patch("mcli.lib.paths.is_git_repository", return_value=True):
            with patch("mcli.lib.paths.get_git_root", return_value=tmp_path):
                result = cli_runner.invoke(migrate_command, ["--rename-dir"])

        assert result.exit_code == 0
        assert "Already using" in result.output

    def test_rename_dir_no_mcli_dir(self, cli_runner, tmp_path):
        """Test --rename-dir when no .mcli/ directory exists."""
        (tmp_path / ".git").mkdir()

        with patch("mcli.lib.paths.is_git_repository", return_value=True):
            with patch("mcli.lib.paths.get_git_root", return_value=tmp_path):
                result = cli_runner.invoke(migrate_command, ["--rename-dir"])

        assert result.exit_code == 0
        assert "nothing to migrate" in result.output.lower()

    def test_rename_dir_both_exist(self, cli_runner, tmp_path):
        """Test --rename-dir when both mcli/ and .mcli/ exist."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".mcli").mkdir()
        (tmp_path / "mcli").mkdir()

        with patch("mcli.lib.paths.is_git_repository", return_value=True):
            with patch("mcli.lib.paths.get_git_root", return_value=tmp_path):
                result = cli_runner.invoke(migrate_command, ["--rename-dir"])

        assert result.exit_code == 0
        assert "Both" in result.output

    def test_rename_dir_not_in_git_repo(self, cli_runner, tmp_path):
        """Test --rename-dir when not in a git repository."""
        with patch("mcli.lib.paths.is_git_repository", return_value=False):
            result = cli_runner.invoke(migrate_command, ["--rename-dir"])

        assert result.exit_code == 0
        assert "Not in a git repository" in result.output

    def test_migration_status_shows_dir_rename_needed(self, cli_runner, tmp_path):
        """Test --status shows directory rename needed."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".mcli" / "workflows").mkdir(parents=True)

        with patch("mcli.lib.paths.is_git_repository", return_value=True):
            with patch("mcli.lib.paths.get_git_root", return_value=tmp_path):
                result = cli_runner.invoke(migrate_command, ["--status"])

        assert result.exit_code == 0
        assert "rename" in result.output.lower()
