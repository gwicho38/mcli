"""Tests for custom command test filtering functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from mcli.lib.custom_commands import CustomCommandManager


@pytest.fixture
def temp_commands_dir():
    """Create a temporary commands directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def command_manager(temp_commands_dir, monkeypatch):
    """Create a CustomCommandManager with a temporary directory."""
    # Patch get_custom_commands_dir to return our temp dir
    monkeypatch.setattr(
        "mcli.lib.custom_commands.get_custom_commands_dir",
        lambda global_mode=False: temp_commands_dir,
    )
    return CustomCommandManager()


def create_test_command_file(commands_dir: Path, name: str, description: str = "Test command"):
    """Helper to create a command JSON file."""
    command_data = {
        "name": name,
        "code": "print('hello')",
        "description": description,
        "language": "python",
        "version": "1.0",
    }
    command_file = commands_dir / f"{name}.json"
    with open(command_file, "w") as f:
        json.dump(command_data, f)
    return command_file


def test_filter_test_commands_by_default(command_manager, temp_commands_dir):
    """Test that test commands are filtered out by default."""
    # Create regular and test commands
    create_test_command_file(temp_commands_dir, "regular_command")
    create_test_command_file(temp_commands_dir, "test_command1")
    create_test_command_file(temp_commands_dir, "test-command2")
    create_test_command_file(temp_commands_dir, "another_regular")

    # Load commands (should exclude test commands by default)
    commands = command_manager.load_all_commands()

    # Should only load regular commands
    command_names = [cmd["name"] for cmd in commands]
    assert "regular_command" in command_names
    assert "another_regular" in command_names
    assert "test_command1" not in command_names
    assert "test-command2" not in command_names
    assert len(commands) == 2


def test_include_test_commands_with_env_var(command_manager, temp_commands_dir, monkeypatch):
    """Test that test commands are included when MCLI_INCLUDE_TEST_COMMANDS=true."""
    # Set environment variable
    monkeypatch.setenv("MCLI_INCLUDE_TEST_COMMANDS", "true")

    # Create regular and test commands
    create_test_command_file(temp_commands_dir, "regular_command")
    create_test_command_file(temp_commands_dir, "test_command1")
    create_test_command_file(temp_commands_dir, "test-command2")

    # Load commands (should include test commands)
    commands = command_manager.load_all_commands()

    # Should load all commands
    command_names = [cmd["name"] for cmd in commands]
    assert "regular_command" in command_names
    assert "test_command1" in command_names
    assert "test-command2" in command_names
    assert len(commands) == 3


def test_case_insensitive_env_var(command_manager, temp_commands_dir, monkeypatch):
    """Test that env var is case insensitive."""
    # Test various case combinations
    for value in ["TRUE", "True", "true"]:
        monkeypatch.setenv("MCLI_INCLUDE_TEST_COMMANDS", value)
        create_test_command_file(temp_commands_dir, "test_cmd")

        commands = command_manager.load_all_commands()
        command_names = [cmd["name"] for cmd in commands]

        assert "test_cmd" in command_names


def test_false_env_var_filters_test_commands(command_manager, temp_commands_dir, monkeypatch):
    """Test that explicitly setting to false still filters test commands."""
    monkeypatch.setenv("MCLI_INCLUDE_TEST_COMMANDS", "false")

    create_test_command_file(temp_commands_dir, "test_command")
    create_test_command_file(temp_commands_dir, "regular_command")

    commands = command_manager.load_all_commands()
    command_names = [cmd["name"] for cmd in commands]

    assert "regular_command" in command_names
    assert "test_command" not in command_names


def test_lockfile_still_skipped(command_manager, temp_commands_dir):
    """Test that lockfile is still skipped regardless of filtering."""
    # Create lockfile
    lockfile = temp_commands_dir / "commands.lock.json"
    with open(lockfile, "w") as f:
        json.dump({"version": "1.0", "commands": {}}, f)

    # Create regular command
    create_test_command_file(temp_commands_dir, "regular_command")

    commands = command_manager.load_all_commands()

    # Should only have the regular command, not the lockfile
    assert len(commands) == 1
    assert commands[0]["name"] == "regular_command"


def test_test_prefix_variations(command_manager, temp_commands_dir):
    """Test different test prefix variations."""
    # Create commands with various prefixes
    create_test_command_file(temp_commands_dir, "test_with_underscore")
    create_test_command_file(temp_commands_dir, "test-with-dash")
    create_test_command_file(temp_commands_dir, "testNoPrefixSeparator")  # Should NOT be filtered
    create_test_command_file(temp_commands_dir, "my_test_command")  # Should NOT be filtered
    create_test_command_file(temp_commands_dir, "regular_command")

    commands = command_manager.load_all_commands()
    command_names = [cmd["name"] for cmd in commands]

    # Only those starting with test_ or test- should be filtered
    assert "test_with_underscore" not in command_names
    assert "test-with-dash" not in command_names
    assert "testNoPrefixSeparator" in command_names  # No separator, so not filtered
    assert "my_test_command" in command_names  # test not at start
    assert "regular_command" in command_names
    assert len(commands) == 3


def test_empty_directory(command_manager, temp_commands_dir):
    """Test loading from empty directory."""
    commands = command_manager.load_all_commands()
    assert len(commands) == 0


def test_only_test_commands(command_manager, temp_commands_dir):
    """Test directory with only test commands."""
    create_test_command_file(temp_commands_dir, "test_cmd1")
    create_test_command_file(temp_commands_dir, "test_cmd2")
    create_test_command_file(temp_commands_dir, "test-cmd3")

    commands = command_manager.load_all_commands()
    assert len(commands) == 0  # All should be filtered
