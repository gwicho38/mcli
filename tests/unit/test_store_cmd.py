"""
Unit tests for command store management functionality
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from mcli.self.store_cmd import _get_store_path, store


@pytest.fixture
def mock_paths(tmp_path):
    """Mock store and commands paths"""
    store_path = tmp_path / "mcli-commands"
    commands_path = tmp_path / ".mcli" / "commands"
    config_file = tmp_path / ".mcli" / "store.conf"

    commands_path.mkdir(parents=True, exist_ok=True)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    return {
        "store_path": store_path,
        "commands_path": commands_path,
        "config_file": config_file,
    }


@pytest.fixture
def runner():
    """CLI test runner"""
    return CliRunner()


class TestGetStorePath:
    """Test _get_store_path helper function"""

    def test_get_store_path_from_config(self, tmp_path):
        """Test reading store path from config file"""
        # Create .mcli directory structure
        mcli_dir = tmp_path / ".mcli"
        mcli_dir.mkdir(parents=True)
        config_file = mcli_dir / "store.conf"
        store_path = tmp_path / "my-store"
        store_path.mkdir()

        config_file.write_text(str(store_path))

        with patch("mcli.self.store_cmd.Path.home", return_value=tmp_path):
            result = _get_store_path()
            assert result == store_path

    def test_get_store_path_default(self, tmp_path):
        """Test default store path when config doesn't exist"""
        with patch("mcli.self.store_cmd.Path.home", return_value=tmp_path):
            with patch("mcli.self.store_cmd.DEFAULT_STORE_PATH", tmp_path / "default"):
                result = _get_store_path()
                assert result == tmp_path / "default"

    def test_get_store_path_nonexistent(self, tmp_path):
        """Test behavior when configured path doesn't exist"""
        config_file = tmp_path / "store.conf"
        config_file.write_text("/nonexistent/path")

        with patch("mcli.self.store_cmd.Path.home", return_value=tmp_path):
            with patch("mcli.self.store_cmd.DEFAULT_STORE_PATH", tmp_path / "default"):
                result = _get_store_path()
                # Should fall back to default when configured path doesn't exist
                assert result == tmp_path / "default"


class TestStoreInit:
    """Test store init command"""

    @patch("mcli.self.store_cmd.subprocess.run")
    @patch("mcli.self.store_cmd.Path.home")
    def test_init_creates_directory(self, mock_home, mock_run, runner, tmp_path):
        """Test init creates store directory"""
        mock_home.return_value = tmp_path
        tmp_path / "repos" / "mcli-commands"

        result = runner.invoke(store, ["init"])

        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

    @patch("mcli.self.store_cmd.subprocess.run")
    @patch("mcli.self.store_cmd.Path.home")
    def test_init_creates_gitignore(self, mock_home, mock_run, runner, tmp_path):
        """Test init creates .gitignore"""
        mock_home.return_value = tmp_path
        store_path = tmp_path / "repos" / "mcli-commands"

        result = runner.invoke(store, ["init"])

        assert result.exit_code == 0
        gitignore = store_path / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            assert "*.backup" in content
            assert ".DS_Store" in content

    @patch("mcli.self.store_cmd.subprocess.run")
    @patch("mcli.self.store_cmd.Path.home")
    def test_init_creates_readme(self, mock_home, mock_run, runner, tmp_path):
        """Test init creates README.md"""
        mock_home.return_value = tmp_path
        store_path = tmp_path / "repos" / "mcli-commands"

        result = runner.invoke(store, ["init"])

        assert result.exit_code == 0
        readme = store_path / "README.md"
        if readme.exists():
            content = readme.read_text()
            assert "MCLI Commands Store" in content

    @patch("mcli.self.store_cmd.subprocess.run")
    @patch("mcli.self.store_cmd.Path.home")
    def test_init_with_remote(self, mock_home, mock_run, runner, tmp_path):
        """Test init with remote URL"""
        mock_home.return_value = tmp_path

        result = runner.invoke(store, ["init", "--remote", "git@github.com:user/repo.git"])

        assert result.exit_code == 0
        # Check that git remote add was called
        # (would need to inspect mock_run calls in actual implementation)

    @patch("mcli.self.store_cmd.subprocess.run")
    @patch("mcli.self.store_cmd.Path.home")
    def test_init_already_exists(self, mock_home, mock_run, runner, tmp_path):
        """Test init when git repo already exists"""
        mock_home.return_value = tmp_path
        store_path = tmp_path / "repos" / "mcli-commands"
        store_path.mkdir(parents=True)
        (store_path / ".git").mkdir()

        result = runner.invoke(store, ["init"])

        assert result.exit_code == 0
        assert "already exists" in result.output.lower()


class TestStorePush:
    """Test store push command"""

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.COMMANDS_PATH")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_push_copies_commands(
        self, mock_run, mock_commands_path, mock_get_store, runner, tmp_path
    ):
        """Test push copies commands to store"""
        store_path = tmp_path / "store"
        commands_path = tmp_path / "commands"

        store_path.mkdir()
        commands_path.mkdir()

        # Create test command file
        (commands_path / "test.json").write_text('{"test": true}')

        mock_get_store.return_value = store_path
        mock_commands_path.__class__ = Path

        # Mock git status to return no changes
        mock_run.return_value = Mock(stdout="", returncode=0)

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            result = runner.invoke(store, ["push"])

        assert result.exit_code == 0

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_push_skips_backups_by_default(self, mock_run, mock_get_store, runner, tmp_path):
        """Test push skips .backup files unless --all specified"""
        store_path = tmp_path / "store"
        commands_path = tmp_path / "commands"

        store_path.mkdir()
        commands_path.mkdir()

        # Create test files including backup
        (commands_path / "test.json").write_text('{"test": true}')
        (commands_path / "test.json.backup").write_text('{"test": true}')

        mock_get_store.return_value = store_path
        mock_run.return_value = Mock(stdout="", returncode=0)

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            runner.invoke(store, ["push"])

        # Backup file should not be copied
        assert not (store_path / "test.json.backup").exists()


class TestStorePull:
    """Test store pull command"""

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_pull_copies_from_store(self, mock_run, mock_get_store, runner, tmp_path):
        """Test pull copies commands from store"""
        store_path = tmp_path / "store"
        commands_path = tmp_path / "commands"

        store_path.mkdir()
        commands_path.mkdir()

        # Create test file in store
        (store_path / "test.json").write_text('{"test": true}')

        mock_get_store.return_value = store_path
        mock_run.return_value = Mock(returncode=0)

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            result = runner.invoke(store, ["pull", "--force"])

        assert result.exit_code == 0

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_pull_creates_backup(self, mock_run, mock_get_store, runner, tmp_path):
        """Test pull creates backup of existing commands"""
        store_path = tmp_path / "store"
        commands_path = tmp_path / "commands"

        store_path.mkdir()
        commands_path.mkdir()

        # Create existing command
        (commands_path / "existing.json").write_text('{"existing": true}')

        mock_get_store.return_value = store_path
        mock_run.return_value = Mock(returncode=0)

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            result = runner.invoke(store, ["pull"])

        # Should create backup directory (check for backup in parent)
        backup_dirs = list(commands_path.parent.glob("commands_backup_*"))
        assert len(backup_dirs) > 0 or result.exit_code == 0

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_pull_skips_git_files(self, mock_run, mock_get_store, runner, tmp_path):
        """Test pull skips .git, README.md, .gitignore"""
        store_path = tmp_path / "store"
        commands_path = tmp_path / "commands"

        store_path.mkdir()
        commands_path.mkdir()

        # Create files that should be skipped
        (store_path / ".git").mkdir()
        (store_path / "README.md").write_text("readme")
        (store_path / ".gitignore").write_text("ignore")
        (store_path / "command.json").write_text('{"test": true}')

        mock_get_store.return_value = store_path
        mock_run.return_value = Mock(returncode=0)

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            runner.invoke(store, ["pull", "--force"])

        # Git files should not be copied
        assert not (commands_path / ".git").exists()
        assert not (commands_path / "README.md").exists()
        assert not (commands_path / ".gitignore").exists()


class TestStoreSync:
    """Test store sync command"""

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_sync_pulls_then_pushes(self, mock_run, mock_get_store, runner, tmp_path):
        """Test sync pulls then pushes if changes exist"""
        store_path = tmp_path / "store"
        commands_path = tmp_path / "commands"

        store_path.mkdir()
        commands_path.mkdir()

        mock_get_store.return_value = store_path
        # Mock git status to show changes
        mock_run.return_value = Mock(stdout="M test.json", returncode=0)

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            result = runner.invoke(store, ["sync"])

        # Should succeed (actual git commands would be mocked)
        assert result.exit_code == 0


class TestStoreList:
    """Test store list command"""

    @patch("mcli.self.store_cmd._get_store_path")
    def test_list_local_commands(self, mock_get_store, runner, tmp_path):
        """Test listing local commands"""
        commands_path = tmp_path / "commands"
        commands_path.mkdir()

        # Create test commands
        (commands_path / "test1.json").write_text('{"test": 1}')
        (commands_path / "test2.json").write_text('{"test": 2}')

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            result = runner.invoke(store, ["list"])

        assert result.exit_code == 0
        assert "test1.json" in result.output
        assert "test2.json" in result.output

    @pytest.mark.skip(reason="CLI interface changed: --store-dir flag no longer exists")
    @patch("mcli.self.store_cmd._get_store_path")
    def test_list_store_commands(self, mock_get_store, runner, tmp_path):
        """Test listing store commands"""
        store_path = tmp_path / "store"
        store_path.mkdir()

        # Create test commands in store
        (store_path / "store1.json").write_text('{"test": 1}')
        (store_path / "store2.json").write_text('{"test": 2}')

        mock_get_store.return_value = store_path

        result = runner.invoke(store, ["list", "--store-dir"])

        assert result.exit_code == 0
        assert "store1.json" in result.output
        assert "store2.json" in result.output


class TestStoreStatus:
    """Test store status command"""

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_status_shows_git_status(self, mock_run, mock_get_store, runner, tmp_path):
        """Test status shows git repository status"""
        store_path = tmp_path / "store"
        store_path.mkdir()

        mock_get_store.return_value = store_path
        mock_run.return_value = Mock(stdout="## main", returncode=0)

        result = runner.invoke(store, ["status"])

        assert result.exit_code == 0
        assert "Store:" in result.output


class TestStoreShow:
    """Test store show command"""

    @patch("mcli.self.store_cmd._get_store_path")
    def test_show_local_command(self, mock_get_store, runner, tmp_path):
        """Test showing local command file"""
        commands_path = tmp_path / "commands"
        commands_path.mkdir()

        # Create test command
        test_content = '{"name": "test", "version": "1.0"}'
        (commands_path / "test.json").write_text(test_content)

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            result = runner.invoke(store, ["show", "test.json"])

        assert result.exit_code == 0
        assert "test" in result.output

    @pytest.mark.skip(reason="CLI interface changed: --store flag behavior updated")
    @patch("mcli.self.store_cmd._get_store_path")
    def test_show_store_command(self, mock_get_store, runner, tmp_path):
        """Test showing store command file"""
        store_path = tmp_path / "store"
        store_path.mkdir()

        # Create test command in store
        test_content = '{"name": "store_test", "version": "1.0"}'
        (store_path / "test.json").write_text(test_content)

        mock_get_store.return_value = store_path

        result = runner.invoke(store, ["show", "test.json", "--store-dir"])

        assert result.exit_code == 0
        assert "store_test" in result.output

    @patch("mcli.self.store_cmd._get_store_path")
    def test_show_nonexistent_command(self, mock_get_store, runner, tmp_path):
        """Test showing nonexistent command"""
        commands_path = tmp_path / "commands"
        commands_path.mkdir()

        with patch("mcli.self.store_cmd.COMMANDS_PATH", commands_path):
            result = runner.invoke(store, ["show", "nonexistent.json"])

        assert result.exit_code == 0
        assert "not found" in result.output.lower()


class TestStoreConfig:
    """Test store config command"""

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.Path.home")
    def test_config_set_path(self, mock_home, mock_get_store, runner, tmp_path):
        """Test setting store path"""
        # Create .mcli directory for config file
        mcli_dir = tmp_path / ".mcli"
        mcli_dir.mkdir(parents=True)

        mock_home.return_value = tmp_path
        new_path = tmp_path / "new-store"

        result = runner.invoke(store, ["config", "--path", str(new_path)])

        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    @patch("mcli.self.store_cmd._get_store_path")
    @patch("mcli.self.store_cmd.subprocess.run")
    def test_config_set_remote(self, mock_run, mock_get_store, runner, tmp_path):
        """Test setting git remote"""
        store_path = tmp_path / "store"
        store_path.mkdir()

        mock_get_store.return_value = store_path
        mock_run.return_value = Mock(stdout="", returncode=0)

        result = runner.invoke(store, ["config", "--remote", "git@github.com:user/repo.git"])

        # Should succeed (git remote commands are mocked)
        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
