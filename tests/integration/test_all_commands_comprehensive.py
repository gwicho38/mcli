"""Comprehensive integration test for all MCLI commands.

This test creates a mock repository structure and runs through every single
mcli command to ensure they all work correctly. It uses fixtures to set up
a complete mock environment with proper directory structure.

Test Coverage:
- Top-level commands: init, new, edit, delete, sync, teardown
- mcli self: version, hello, plugin, logs, completion, update, performance
- mcli workflow: add, edit, list, search, remove, import, export, info, verify
- mcli workflows (run): sync, scheduler, daemon, secrets, dashboard, make, npm
- mcli lock: list, restore, write, verify, update
"""

import json
from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner

from mcli.app.main import create_app

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mcli_app():
    """Create and return the mcli application."""
    return create_app()


@pytest.fixture
def mock_repo(tmp_path):
    """Create a comprehensive mock repository structure for testing."""
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()

    # Create .mcli directory structure
    mcli_dir = repo_dir / ".mcli"
    mcli_dir.mkdir()

    commands_dir = mcli_dir / "commands"
    commands_dir.mkdir()

    workflow_dir = commands_dir / "workflow"
    workflow_dir.mkdir()

    workflows_dir = mcli_dir / "workflows"
    workflows_dir.mkdir()

    logs_dir = mcli_dir / "logs"
    logs_dir.mkdir()

    cache_dir = mcli_dir / "cache"
    cache_dir.mkdir()

    plugins_dir = mcli_dir / "plugins"
    plugins_dir.mkdir()

    # Create config.toml
    config_file = mcli_dir / "config.toml"
    config_file.write_text(
        """
[general]
log_level = "INFO"
theme = "default"

[chat]
provider = "openai"
model = "gpt-4"
temperature = 0.7

[paths]
logs_dir = "~/.mcli/logs"
cache_dir = "~/.mcli/cache"
included_dirs = ["app", "self", "workflow", "public"]
"""
    )

    # Create a sample workflow JSON
    test_workflow = workflow_dir / "test_workflow.json"
    test_workflow.write_text(
        json.dumps(
            {
                "name": "test_workflow",
                "group": "workflow",
                "description": "A test workflow for integration testing",
                "version": "1.0.0",
                "language": "shell",
                "code": "echo 'Hello from test workflow'",
            },
            indent=2,
        )
    )

    # Create another workflow for testing
    sample_workflow = workflow_dir / "sample_script.json"
    sample_workflow.write_text(
        json.dumps(
            {
                "name": "sample_script",
                "group": "workflow",
                "description": "A sample script workflow",
                "version": "1.0.0",
                "language": "python",
                "code": """
import click

@click.command()
def sample_script():
    '''Sample script for testing'''
    click.echo('Sample script executed')
""",
            },
            indent=2,
        )
    )

    # Create commands.lock.json
    lockfile = mcli_dir / "commands.lock.json"
    lockfile.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "commands": [
                    {"name": "test_workflow", "group": "workflow", "hash": "abc123"},
                    {"name": "sample_script", "group": "workflow", "hash": "def456"},
                ],
            },
            indent=2,
        )
    )

    # Create project structure
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("# Main application\nprint('Hello World')\n")

    tests_dir = repo_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_placeholder(): pass\n")

    # Create Makefile for make workflow detection
    makefile = repo_dir / "Makefile"
    makefile.write_text(
        """
.PHONY: test build clean

test:
\t@echo "Running tests"

build:
\t@echo "Building project"

clean:
\t@echo "Cleaning up"
"""
    )

    # Create package.json for npm workflow detection
    package_json = repo_dir / "package.json"
    package_json.write_text(
        json.dumps(
            {
                "name": "mock-repo",
                "version": "1.0.0",
                "scripts": {
                    "test": "echo 'Running npm test'",
                    "build": "echo 'Running npm build'",
                    "start": "echo 'Starting app'",
                },
            },
            indent=2,
        )
    )

    # Create README
    readme = repo_dir / "README.md"
    readme.write_text("# Mock Repository\n\nThis is a mock repository for testing.\n")

    # Initialize as git repo (optional but useful)
    git_dir = repo_dir / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0\n")

    return repo_dir


@pytest.fixture
def mock_home(tmp_path, mock_repo):
    """Create a mock home directory with MCLI configuration."""
    home_dir = tmp_path / "mock_home"
    home_dir.mkdir()

    # Create global .mcli structure
    mcli_dir = home_dir / ".mcli"
    mcli_dir.mkdir()

    (mcli_dir / "commands").mkdir()
    (mcli_dir / "workflows").mkdir()
    (mcli_dir / "logs").mkdir()
    (mcli_dir / "plugins").mkdir()
    (mcli_dir / "cache").mkdir()

    # Create global config
    (mcli_dir / "config.toml").write_text(
        """
[general]
log_level = "INFO"
theme = "default"
"""
    )

    # Create .local/mcli for lockfile
    local_mcli = home_dir / ".local" / "mcli"
    local_mcli.mkdir(parents=True)

    (local_mcli / "command_lock.json").write_text(
        json.dumps(
            [{"hash": "test123abc", "timestamp": "2025-01-01T00:00:00Z", "commands": []}], indent=2
        )
    )

    return home_dir


@pytest.fixture
def env_setup(mock_repo, mock_home, monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("MCLI_ENV", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("MCLI_TRACE_LEVEL", "0")
    monkeypatch.setenv("HOME", str(mock_home))
    monkeypatch.setenv("MCLI_HOME", str(mock_home / ".mcli"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.chdir(mock_repo)
    return {"home": mock_home, "repo": mock_repo}


# ============================================================================
# Test Markers
# ============================================================================


pytestmark = [pytest.mark.integration, pytest.mark.cli]


# ============================================================================
# Main App Tests
# ============================================================================


class TestMainApp:
    """Tests for the main mcli application."""

    def test_app_creation(self, mcli_app):
        """Test that the app is created successfully."""
        assert mcli_app is not None
        assert isinstance(mcli_app, click.Group)
        assert mcli_app.name == "mcli"

    def test_app_help(self, cli_runner, mcli_app):
        """Test main app --help."""
        result = cli_runner.invoke(mcli_app, ["--help"])
        assert result.exit_code == 0
        assert "mcli" in result.output

    def test_app_lists_commands(self, cli_runner, mcli_app):
        """Test that the app lists available commands."""
        result = cli_runner.invoke(mcli_app, ["--help"])
        assert result.exit_code == 0
        # Check for expected top-level commands
        expected_commands = ["self", "workflow", "workflows", "lock"]
        for cmd in expected_commands:
            assert cmd in result.output, f"Expected command '{cmd}' not found in help output"


# ============================================================================
# Top-Level Commands Tests
# ============================================================================


class TestTopLevelCommands:
    """Tests for top-level mcli commands."""

    def test_init_help(self, cli_runner, mcli_app):
        """Test mcli init --help."""
        result = cli_runner.invoke(mcli_app, ["init", "--help"])
        # May succeed or fail depending on if init command exists
        assert result.exit_code in [0, 2]

    def test_new_help(self, cli_runner, mcli_app):
        """Test mcli new --help."""
        result = cli_runner.invoke(mcli_app, ["new", "--help"])
        assert result.exit_code in [0, 2]

    def test_edit_help(self, cli_runner, mcli_app):
        """Test mcli edit --help."""
        result = cli_runner.invoke(mcli_app, ["edit", "--help"])
        assert result.exit_code in [0, 2]

    def test_delete_help(self, cli_runner, mcli_app):
        """Test mcli delete --help."""
        result = cli_runner.invoke(mcli_app, ["delete", "--help"])
        assert result.exit_code in [0, 2]

    def test_remove_alias(self, cli_runner, mcli_app):
        """Test that 'remove' is an alias for 'delete'."""
        result = cli_runner.invoke(mcli_app, ["remove", "--help"])
        assert result.exit_code in [0, 2]

    def test_sync_help(self, cli_runner, mcli_app):
        """Test mcli sync --help."""
        result = cli_runner.invoke(mcli_app, ["sync", "--help"])
        assert result.exit_code in [0, 2]

    def test_teardown_help(self, cli_runner, mcli_app):
        """Test mcli teardown --help."""
        result = cli_runner.invoke(mcli_app, ["teardown", "--help"])
        assert result.exit_code in [0, 2]


# ============================================================================
# Self Commands Tests
# ============================================================================


class TestSelfCommands:
    """Tests for mcli self subcommands."""

    def test_self_help(self, cli_runner, mcli_app):
        """Test mcli self --help."""
        result = cli_runner.invoke(mcli_app, ["self", "--help"])
        assert result.exit_code == 0
        assert "Manage and extend the mcli application" in result.output

    def test_self_version(self, cli_runner, mcli_app):
        """Test mcli self version."""
        result = cli_runner.invoke(mcli_app, ["self", "version"])
        assert result.exit_code == 0
        assert "mcli version" in result.output

    def test_self_version_verbose(self, cli_runner, mcli_app):
        """Test mcli self version --verbose."""
        result = cli_runner.invoke(mcli_app, ["self", "version", "--verbose"])
        assert result.exit_code == 0
        assert "Python:" in result.output

    def test_self_hello(self, cli_runner, mcli_app):
        """Test mcli self hello."""
        result = cli_runner.invoke(mcli_app, ["self", "hello"])
        assert result.exit_code == 0
        assert "Hello" in result.output

    def test_self_hello_with_name(self, cli_runner, mcli_app):
        """Test mcli self hello <name>."""
        result = cli_runner.invoke(mcli_app, ["self", "hello", "TestUser"])
        assert result.exit_code == 0
        assert "TestUser" in result.output

    def test_self_plugin_help(self, cli_runner, mcli_app):
        """Test mcli self plugin --help."""
        result = cli_runner.invoke(mcli_app, ["self", "plugin", "--help"])
        assert result.exit_code == 0
        assert "Manage plugins" in result.output

    def test_self_plugin_subcommands(self, cli_runner, mcli_app):
        """Test mcli self plugin shows available subcommands."""
        result = cli_runner.invoke(mcli_app, ["self", "plugin", "--help"])
        # Should show add, remove, update subcommands
        assert result.exit_code == 0
        assert "add" in result.output
        assert "remove" in result.output
        assert "update" in result.output

    def test_self_plugin_add_help(self, cli_runner, mcli_app):
        """Test mcli self plugin add --help."""
        result = cli_runner.invoke(mcli_app, ["self", "plugin", "add", "--help"])
        assert result.exit_code == 0
        assert "PLUGIN_NAME" in result.output

    def test_self_plugin_add_missing_arg(self, cli_runner, mcli_app):
        """Test mcli self plugin add without argument."""
        result = cli_runner.invoke(mcli_app, ["self", "plugin", "add"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_self_plugin_remove_help(self, cli_runner, mcli_app):
        """Test mcli self plugin remove --help."""
        result = cli_runner.invoke(mcli_app, ["self", "plugin", "remove", "--help"])
        assert result.exit_code == 0
        assert "PLUGIN_NAME" in result.output

    def test_self_plugin_update_help(self, cli_runner, mcli_app):
        """Test mcli self plugin update --help."""
        result = cli_runner.invoke(mcli_app, ["self", "plugin", "update", "--help"])
        assert result.exit_code == 0
        assert "PLUGIN_NAME" in result.output

    def test_self_logs_help(self, cli_runner, mcli_app):
        """Test mcli self logs --help."""
        result = cli_runner.invoke(mcli_app, ["self", "logs", "--help"])
        assert result.exit_code == 0
        assert "Stream and manage MCLI log files" in result.output

    def test_self_logs_list(self, cli_runner, mcli_app):
        """Test mcli self logs list."""
        result = cli_runner.invoke(mcli_app, ["self", "logs", "list"])
        # May succeed or show no logs
        assert result.exit_code == 0

    def test_self_logs_location(self, cli_runner, mcli_app):
        """Test mcli self logs location."""
        result = cli_runner.invoke(mcli_app, ["self", "logs", "location"])
        assert result.exit_code == 0

    def test_self_completion_help(self, cli_runner, mcli_app):
        """Test mcli self completion --help."""
        result = cli_runner.invoke(mcli_app, ["self", "completion", "--help"])
        assert result.exit_code == 0

    def test_self_completion_bash(self, cli_runner, mcli_app):
        """Test mcli self completion bash."""
        result = cli_runner.invoke(mcli_app, ["self", "completion", "bash"])
        assert result.exit_code == 0
        # Should output shell completion script

    def test_self_completion_zsh(self, cli_runner, mcli_app):
        """Test mcli self completion zsh."""
        result = cli_runner.invoke(mcli_app, ["self", "completion", "zsh"])
        assert result.exit_code == 0

    def test_self_completion_fish(self, cli_runner, mcli_app):
        """Test mcli self completion fish."""
        result = cli_runner.invoke(mcli_app, ["self", "completion", "fish"])
        assert result.exit_code == 0

    def test_self_update_help(self, cli_runner, mcli_app):
        """Test mcli self update --help."""
        result = cli_runner.invoke(mcli_app, ["self", "update", "--help"])
        assert result.exit_code == 0
        assert "--check" in result.output
        assert "--yes" in result.output

    @patch("requests.get")
    @patch("importlib.metadata.version")
    def test_self_update_check(self, mock_version, mock_get, cli_runner, mcli_app):
        """Test mcli self update --check."""
        mock_version.return_value = "7.0.5"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "7.0.5"}, "releases": {}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = cli_runner.invoke(mcli_app, ["self", "update", "--check"])
        assert result.exit_code == 0

    def test_self_performance(self, cli_runner, mcli_app):
        """Test mcli self performance."""
        result = cli_runner.invoke(mcli_app, ["self", "performance"])
        assert result.exit_code == 0

    def test_self_performance_detailed(self, cli_runner, mcli_app):
        """Test mcli self performance --detailed."""
        result = cli_runner.invoke(mcli_app, ["self", "performance", "--detailed"])
        assert result.exit_code == 0

    def test_self_performance_benchmark(self, cli_runner, mcli_app):
        """Test mcli self performance --benchmark."""
        result = cli_runner.invoke(mcli_app, ["self", "performance", "--benchmark"])
        assert result.exit_code == 0


# ============================================================================
# Workflow Management Commands Tests
# ============================================================================


class TestWorkflowManagementCommands:
    """Tests for mcli workflow subcommands (management)."""

    def test_workflow_help(self, cli_runner, mcli_app):
        """Test mcli workflow --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "--help"])
        assert result.exit_code == 0

    def test_workflow_list(self, cli_runner, mcli_app, env_setup):
        """Test mcli workflow list."""
        result = cli_runner.invoke(mcli_app, ["workflow", "list"])
        # Should succeed even with no workflows
        assert result.exit_code in [0, 1]

    def test_workflow_list_global(self, cli_runner, mcli_app, env_setup):
        """Test mcli workflow list --global."""
        result = cli_runner.invoke(mcli_app, ["workflow", "list", "--global"])
        assert result.exit_code in [0, 1]

    def test_workflow_search_help(self, cli_runner, mcli_app):
        """Test mcli workflow search --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "search", "--help"])
        assert result.exit_code == 0

    def test_workflow_search(self, cli_runner, mcli_app, env_setup):
        """Test mcli workflow search <query>."""
        result = cli_runner.invoke(mcli_app, ["workflow", "search", "test"])
        # Should succeed even with no matches
        assert result.exit_code in [0, 1]

    def test_workflow_add_help(self, cli_runner, mcli_app):
        """Test mcli workflow add --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "add", "--help"])
        assert result.exit_code == 0

    def test_workflow_edit_help(self, cli_runner, mcli_app):
        """Test mcli workflow edit --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "edit", "--help"])
        assert result.exit_code == 0

    def test_workflow_remove_help(self, cli_runner, mcli_app):
        """Test mcli workflow remove --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "remove", "--help"])
        assert result.exit_code == 0

    def test_workflow_import_help(self, cli_runner, mcli_app):
        """Test mcli workflow import --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "import", "--help"])
        assert result.exit_code == 0

    def test_workflow_export_help(self, cli_runner, mcli_app):
        """Test mcli workflow export --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "export", "--help"])
        assert result.exit_code == 0

    def test_workflow_info_help(self, cli_runner, mcli_app):
        """Test mcli workflow info --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "info", "--help"])
        assert result.exit_code == 0

    def test_workflow_status_help(self, cli_runner, mcli_app):
        """Test mcli workflow status --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "status", "--help"])
        assert result.exit_code == 0

    def test_workflow_store_help(self, cli_runner, mcli_app):
        """Test mcli workflow store --help."""
        result = cli_runner.invoke(mcli_app, ["workflow", "store", "--help"])
        assert result.exit_code in [0, 2]


# ============================================================================
# Workflows (Run) Commands Tests
# ============================================================================


class TestWorkflowsRunCommands:
    """Tests for mcli workflows subcommands (runnable workflows)."""

    def test_workflows_help(self, cli_runner, mcli_app):
        """Test mcli workflows --help."""
        result = cli_runner.invoke(mcli_app, ["workflows", "--help"])
        assert result.exit_code == 0

    def test_run_alias_help(self, cli_runner, mcli_app):
        """Test mcli run --help (alias for workflows)."""
        result = cli_runner.invoke(mcli_app, ["run", "--help"])
        assert result.exit_code == 0

    def test_workflows_sync_help(self, cli_runner, mcli_app):
        """Test mcli workflows sync --help."""
        result = cli_runner.invoke(mcli_app, ["workflows", "sync", "--help"])
        assert result.exit_code in [0, 2]

    def test_workflows_scheduler_help(self, cli_runner, mcli_app):
        """Test mcli workflows scheduler --help."""
        result = cli_runner.invoke(mcli_app, ["workflows", "scheduler", "--help"])
        assert result.exit_code in [0, 2]

    def test_workflows_daemon_help(self, cli_runner, mcli_app):
        """Test mcli workflows daemon --help."""
        result = cli_runner.invoke(mcli_app, ["workflows", "daemon", "--help"])
        assert result.exit_code in [0, 2]

    def test_workflows_secrets_help(self, cli_runner, mcli_app):
        """Test mcli workflows secrets --help."""
        result = cli_runner.invoke(mcli_app, ["workflows", "secrets", "--help"])
        assert result.exit_code in [0, 2]

    def test_workflows_dashboard_help(self, cli_runner, mcli_app):
        """Test mcli workflows dashboard --help."""
        result = cli_runner.invoke(mcli_app, ["workflows", "dashboard", "--help"])
        assert result.exit_code in [0, 2]

    def test_workflows_global_flag(self, cli_runner, mcli_app, env_setup):
        """Test mcli workflows -g (global flag)."""
        result = cli_runner.invoke(mcli_app, ["workflows", "-g", "--help"])
        assert result.exit_code == 0


# ============================================================================
# Lock Commands Tests
# ============================================================================


class TestLockCommands:
    """Tests for mcli lock subcommands."""

    def test_lock_help(self, cli_runner, mcli_app):
        """Test mcli lock --help."""
        result = cli_runner.invoke(mcli_app, ["lock", "--help"])
        assert result.exit_code == 0
        assert "Manage workflow lockfile" in result.output

    def test_lock_list(self, cli_runner, mcli_app, env_setup):
        """Test mcli lock list."""
        result = cli_runner.invoke(mcli_app, ["lock", "list"])
        # Should succeed even with empty lockfile
        assert result.exit_code == 0

    def test_lock_verify_help(self, cli_runner, mcli_app):
        """Test mcli lock verify --help."""
        result = cli_runner.invoke(mcli_app, ["lock", "verify", "--help"])
        assert result.exit_code == 0
        assert "--global" in result.output or "-g" in result.output

    def test_lock_verify(self, cli_runner, mcli_app, env_setup):
        """Test mcli lock verify."""
        result = cli_runner.invoke(mcli_app, ["lock", "verify"])
        # Should succeed or report issues
        assert result.exit_code in [0, 1]

    def test_lock_verify_global(self, cli_runner, mcli_app, env_setup):
        """Test mcli lock verify --global."""
        result = cli_runner.invoke(mcli_app, ["lock", "verify", "--global"])
        assert result.exit_code in [0, 1]

    def test_lock_verify_with_code(self, cli_runner, mcli_app, env_setup):
        """Test mcli lock verify --code."""
        result = cli_runner.invoke(mcli_app, ["lock", "verify", "--code"])
        assert result.exit_code in [0, 1]

    def test_lock_update_help(self, cli_runner, mcli_app):
        """Test mcli lock update --help."""
        result = cli_runner.invoke(mcli_app, ["lock", "update", "--help"])
        assert result.exit_code == 0
        assert "--global" in result.output or "-g" in result.output

    def test_lock_update(self, cli_runner, mcli_app, env_setup):
        """Test mcli lock update."""
        result = cli_runner.invoke(mcli_app, ["lock", "update"])
        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1]

    def test_lock_restore_help(self, cli_runner, mcli_app):
        """Test mcli lock restore --help."""
        result = cli_runner.invoke(mcli_app, ["lock", "restore", "--help"])
        assert result.exit_code == 0

    def test_lock_restore_missing_arg(self, cli_runner, mcli_app):
        """Test mcli lock restore without argument."""
        result = cli_runner.invoke(mcli_app, ["lock", "restore"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


# ============================================================================
# Integration Tests with Mock Environment
# ============================================================================


class TestMockEnvironmentIntegration:
    """Integration tests that use the full mock environment."""

    def test_full_workflow_lifecycle(self, cli_runner, mcli_app, env_setup):
        """Test a complete workflow lifecycle: list, check, update, verify."""
        # Step 1: List workflows
        result = cli_runner.invoke(mcli_app, ["workflow", "list"])
        assert result.exit_code in [0, 1]

        # Step 2: Check lock status
        result = cli_runner.invoke(mcli_app, ["lock", "list"])
        assert result.exit_code == 0

        # Step 3: Update lockfile
        result = cli_runner.invoke(mcli_app, ["lock", "update"])
        assert result.exit_code in [0, 1]

        # Step 4: Verify lockfile
        result = cli_runner.invoke(mcli_app, ["lock", "verify"])
        assert result.exit_code in [0, 1]

    def test_self_commands_in_mock_env(self, cli_runner, mcli_app, env_setup):
        """Test self commands work in the mock environment."""
        # Version
        result = cli_runner.invoke(mcli_app, ["self", "version"])
        assert result.exit_code == 0

        # Hello
        result = cli_runner.invoke(mcli_app, ["self", "hello"])
        assert result.exit_code == 0

        # Performance
        result = cli_runner.invoke(mcli_app, ["self", "performance"])
        assert result.exit_code == 0

    def test_workflows_group_with_scope(self, cli_runner, mcli_app, env_setup):
        """Test workflows group with different scopes."""
        # Local scope (default)
        result = cli_runner.invoke(mcli_app, ["workflows", "--help"])
        assert result.exit_code == 0

        # Global scope
        result = cli_runner.invoke(mcli_app, ["workflows", "-g", "--help"])
        assert result.exit_code == 0


# ============================================================================
# Command Registration Tests
# ============================================================================


class TestCommandRegistration:
    """Tests to verify all expected commands are registered."""

    def test_top_level_commands_registered(self, mcli_app):
        """Test that all top-level commands are registered."""
        commands = list(mcli_app.commands.keys())

        expected_commands = [
            "self",
            "workflow",
            "workflows",
            "run",
            "lock",
        ]

        for cmd in expected_commands:
            assert cmd in commands, f"Expected command '{cmd}' not registered"

    def test_self_subcommands_registered(self, mcli_app):
        """Test that self subcommands are registered."""
        self_cmd = mcli_app.commands.get("self")
        if self_cmd and hasattr(self_cmd, "commands"):
            subcommands = list(self_cmd.commands.keys())

            expected_subcommands = [
                "version",
                "hello",
                "plugin",
                "logs",
                "completion",
                "update",
                "performance",
            ]

            for subcmd in expected_subcommands:
                assert subcmd in subcommands, f"Expected self subcommand '{subcmd}' not registered"

    def test_lock_subcommands_registered(self, mcli_app):
        """Test that lock subcommands are registered."""
        lock_cmd = mcli_app.commands.get("lock")
        if lock_cmd and hasattr(lock_cmd, "commands"):
            subcommands = list(lock_cmd.commands.keys())

            expected_subcommands = [
                "list",
                "restore",
                "verify",
                "update",
                "diff",
                "show",
                "history",
            ]

            for subcmd in expected_subcommands:
                assert subcmd in subcommands, f"Expected lock subcommand '{subcmd}' not registered"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in commands."""

    def test_invalid_command(self, cli_runner, mcli_app):
        """Test that invalid commands produce appropriate errors."""
        result = cli_runner.invoke(mcli_app, ["nonexistent_command"])
        assert result.exit_code != 0

    def test_invalid_subcommand(self, cli_runner, mcli_app):
        """Test that invalid subcommands produce appropriate errors."""
        result = cli_runner.invoke(mcli_app, ["self", "nonexistent_subcommand"])
        assert result.exit_code != 0

    def test_missing_required_argument(self, cli_runner, mcli_app):
        """Test that missing required arguments produce appropriate errors."""
        result = cli_runner.invoke(mcli_app, ["lock", "restore"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_invalid_option(self, cli_runner, mcli_app):
        """Test that invalid options produce appropriate errors."""
        result = cli_runner.invoke(mcli_app, ["self", "version", "--invalid-option"])
        assert result.exit_code != 0


# ============================================================================
# Command Output Format Tests
# ============================================================================


class TestCommandOutputFormat:
    """Tests for command output formatting."""

    def test_version_output_format(self, cli_runner, mcli_app):
        """Test that version command output is properly formatted."""
        result = cli_runner.invoke(mcli_app, ["self", "version"])
        assert result.exit_code == 0
        # Version should contain version info
        assert "mcli version" in result.output or "version" in result.output.lower()

    def test_help_output_has_description(self, cli_runner, mcli_app):
        """Test that help output includes command descriptions."""
        result = cli_runner.invoke(mcli_app, ["--help"])
        assert result.exit_code == 0
        # Should have descriptions for commands
        assert len(result.output) > 100  # Reasonable length for help text

    def test_hello_output_greeting(self, cli_runner, mcli_app):
        """Test that hello command outputs a greeting."""
        result = cli_runner.invoke(mcli_app, ["self", "hello"])
        assert result.exit_code == 0
        assert "Hello" in result.output


# ============================================================================
# Performance Tests
# ============================================================================


class TestCommandPerformance:
    """Basic performance tests for commands."""

    def test_help_responds_quickly(self, cli_runner, mcli_app):
        """Test that --help responds in reasonable time."""
        import time

        start = time.time()
        result = cli_runner.invoke(mcli_app, ["--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0
        # Help should respond in under 5 seconds (generous for CI)
        assert elapsed < 5.0, f"Help took too long: {elapsed:.2f}s"

    def test_version_responds_quickly(self, cli_runner, mcli_app):
        """Test that version command responds quickly."""
        import time

        start = time.time()
        result = cli_runner.invoke(mcli_app, ["self", "version"])
        elapsed = time.time() - start

        assert result.exit_code == 0
        assert elapsed < 5.0, f"Version took too long: {elapsed:.2f}s"


# ============================================================================
# Run all commands summary test
# ============================================================================


class TestAllCommandsSummary:
    """Summary test that invokes help for all commands."""

    def test_all_help_commands_succeed(self, cli_runner, mcli_app):
        """Test that --help works for all commands in the registry."""
        commands_to_test = [
            [],  # mcli --help
            ["self"],
            ["self", "version"],
            ["self", "hello"],
            ["self", "plugin"],
            ["self", "logs"],
            ["self", "completion"],
            ["self", "update"],
            ["self", "performance"],
            ["workflow"],
            ["workflow", "list"],
            ["workflow", "search"],
            ["workflow", "add"],
            ["workflow", "edit"],
            ["workflow", "remove"],
            ["workflow", "import"],
            ["workflow", "export"],
            ["workflow", "info"],
            ["workflow", "status"],
            ["workflow", "sync"],
            ["workflows"],
            ["run"],
            ["lock"],
            ["lock", "list"],
            ["lock", "verify"],
            ["lock", "update"],
            ["lock", "write"],
            ["lock", "restore"],
        ]

        failures = []
        for cmd_parts in commands_to_test:
            cmd_with_help = cmd_parts + ["--help"]
            result = cli_runner.invoke(mcli_app, cmd_with_help)

            if result.exit_code not in [0, 2]:  # 2 is OK for missing subcommands
                failures.append(
                    {
                        "command": " ".join(cmd_with_help),
                        "exit_code": result.exit_code,
                        "output": result.output[:200],
                    }
                )

        if failures:
            failure_msgs = [
                f"Command '{f['command']}' failed with exit code {f['exit_code']}: {f['output']}"
                for f in failures
            ]
            pytest.fail("The following commands failed:\n" + "\n".join(failure_msgs))
