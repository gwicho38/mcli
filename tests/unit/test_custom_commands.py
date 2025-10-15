"""
Unit tests for custom_commands module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest

from mcli.lib.custom_commands import CustomCommandManager, get_command_manager


class TestCustomCommandManager:
    """Test suite for CustomCommandManager"""

    def setup_method(self):
        """Setup test environment"""
        # Create a temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # Patch get_custom_commands_dir to return our temp directory
        self.patcher = patch(
            "mcli.lib.custom_commands.get_custom_commands_dir",
            return_value=self.commands_dir,
        )
        self.patcher.start()

        self.manager = CustomCommandManager()

    def teardown_method(self):
        """Cleanup test environment"""
        self.patcher.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager.commands_dir == self.commands_dir
        assert isinstance(self.manager.loaded_commands, dict)
        assert self.manager.lockfile_path == self.commands_dir / "commands.lock.json"

    def test_save_command(self):
        """Test saving a command"""
        code = "import click\n@click.command()\ndef test():\n    click.echo('test')"
        path = self.manager.save_command(name="test_cmd", code=code, description="Test command")

        assert path.exists()
        assert path.name == "test_cmd.json"

        # Verify content
        with open(path, "r") as f:
            data = json.load(f)

        assert data["name"] == "test_cmd"
        assert data["code"] == code
        assert data["description"] == "Test command"
        assert "created_at" in data
        assert "updated_at" in data

    def test_load_command(self):
        """Test loading a command"""
        # Create a test command file
        test_data = {
            "name": "test_cmd",
            "code": "test code",
            "description": "Test",
            "version": "1.0",
        }

        command_file = self.commands_dir / "test_cmd.json"
        with open(command_file, "w") as f:
            json.dump(test_data, f)

        # Load it
        loaded = self.manager.load_command(command_file)

        assert loaded is not None
        assert loaded["name"] == "test_cmd"
        assert loaded["code"] == "test code"

    def test_load_all_commands(self):
        """Test loading all commands"""
        # Create multiple test commands
        for i in range(3):
            test_data = {
                "name": f"test_cmd_{i}",
                "code": f"code {i}",
                "description": f"Test {i}",
            }
            command_file = self.commands_dir / f"test_cmd_{i}.json"
            with open(command_file, "w") as f:
                json.dump(test_data, f)

        # Load all
        commands = self.manager.load_all_commands()

        assert len(commands) == 3
        assert all("name" in cmd for cmd in commands)

    def test_delete_command(self):
        """Test deleting a command"""
        # Create a test command
        self.manager.save_command(name="test_cmd", code="test", description="Test")

        # Verify it exists
        command_file = self.commands_dir / "test_cmd.json"
        assert command_file.exists()

        # Delete it
        result = self.manager.delete_command("test_cmd")

        assert result is True
        assert not command_file.exists()

        # Try deleting non-existent command
        result = self.manager.delete_command("nonexistent")
        assert result is False

    def test_generate_lockfile(self):
        """Test lockfile generation"""
        # Create some test commands
        for i in range(2):
            self.manager.save_command(name=f"cmd_{i}", code=f"code {i}", description=f"Cmd {i}")

        # Generate lockfile
        lockfile_data = self.manager.generate_lockfile()

        assert lockfile_data["version"] == "1.0"
        assert "generated_at" in lockfile_data
        assert "commands" in lockfile_data
        assert len(lockfile_data["commands"]) == 2
        assert "cmd_0" in lockfile_data["commands"]
        assert "cmd_1" in lockfile_data["commands"]

    def test_update_lockfile(self):
        """Test lockfile updating"""
        # Create a test command
        self.manager.save_command(name="test_cmd", code="test", description="Test")

        # Lockfile should be auto-updated via save_command
        assert self.manager.lockfile_path.exists()

        # Load and verify
        with open(self.manager.lockfile_path, "r") as f:
            lockfile = json.load(f)

        assert "test_cmd" in lockfile["commands"]

    def test_load_lockfile(self):
        """Test loading the lockfile"""
        # Create a lockfile
        lockfile_data = {
            "version": "1.0",
            "generated_at": "2025-01-01T00:00:00Z",
            "commands": {"test_cmd": {"name": "test_cmd"}},
        }

        with open(self.manager.lockfile_path, "w") as f:
            json.dump(lockfile_data, f)

        # Load it
        loaded = self.manager.load_lockfile()

        assert loaded is not None
        assert loaded["version"] == "1.0"
        assert "test_cmd" in loaded["commands"]

    def test_verify_lockfile_valid(self):
        """Test lockfile verification when valid"""
        # Create command and update lockfile
        self.manager.save_command(name="test_cmd", code="test", description="Test")
        self.manager.update_lockfile()

        # Verify
        result = self.manager.verify_lockfile()

        assert result["valid"] is True
        assert len(result["missing"]) == 0
        assert len(result["extra"]) == 0
        assert len(result["modified"]) == 0

    def test_verify_lockfile_missing(self):
        """Test lockfile verification with missing commands"""
        # Create command and lockfile
        self.manager.save_command(name="test_cmd", code="test", description="Test")

        # Delete the command file but keep lockfile
        command_file = self.commands_dir / "test_cmd.json"
        command_file.unlink()

        # Verify
        result = self.manager.verify_lockfile()

        assert result["valid"] is False
        assert "test_cmd" in result["missing"]

    def test_verify_lockfile_extra(self):
        """Test lockfile verification with extra commands"""
        # Create a command
        self.manager.save_command(name="test_cmd", code="test", description="Test")

        # Manually delete lockfile entry
        lockfile_data = self.manager.generate_lockfile()
        del lockfile_data["commands"]["test_cmd"]

        with open(self.manager.lockfile_path, "w") as f:
            json.dump(lockfile_data, f)

        # Verify
        result = self.manager.verify_lockfile()

        assert result["valid"] is False
        assert "test_cmd" in result["extra"]

    def test_export_commands(self):
        """Test exporting commands"""
        # Create some commands
        self.manager.save_command(name="cmd1", code="code1", description="Cmd 1")
        self.manager.save_command(name="cmd2", code="code2", description="Cmd 2")

        # Export
        export_path = Path(self.temp_dir) / "export.json"
        result = self.manager.export_commands(export_path)

        assert result is True
        assert export_path.exists()

        # Verify exported data
        with open(export_path, "r") as f:
            exported = json.load(f)

        assert len(exported) == 2

    def test_import_commands(self):
        """Test importing commands"""
        # Create export file
        import_data = [
            {
                "name": "imported_cmd",
                "code": "imported code",
                "description": "Imported",
                "version": "1.0",
            }
        ]

        import_path = Path(self.temp_dir) / "import.json"
        with open(import_path, "w") as f:
            json.dump(import_data, f)

        # Import
        results = self.manager.import_commands(import_path)

        assert results["imported_cmd"] is True
        assert (self.commands_dir / "imported_cmd.json").exists()

    def test_import_commands_no_overwrite(self):
        """Test importing without overwriting existing commands"""
        # Create existing command
        self.manager.save_command(name="existing_cmd", code="original", description="Original")

        # Try to import same command
        import_data = [
            {
                "name": "existing_cmd",
                "code": "new code",
                "description": "New",
                "version": "1.0",
            }
        ]

        import_path = Path(self.temp_dir) / "import.json"
        with open(import_path, "w") as f:
            json.dump(import_data, f)

        # Import without overwrite
        results = self.manager.import_commands(import_path, overwrite=False)

        assert results["existing_cmd"] is False

        # Verify original code is unchanged
        with open(self.commands_dir / "existing_cmd.json", "r") as f:
            data = json.load(f)
        assert data["code"] == "original"

    def test_import_commands_with_overwrite(self):
        """Test importing with overwriting existing commands"""
        # Create existing command
        self.manager.save_command(name="existing_cmd", code="original", description="Original")

        # Import with same command
        import_data = [
            {
                "name": "existing_cmd",
                "code": "new code",
                "description": "New",
                "version": "1.0",
            }
        ]

        import_path = Path(self.temp_dir) / "import.json"
        with open(import_path, "w") as f:
            json.dump(import_data, f)

        # Import with overwrite
        results = self.manager.import_commands(import_path, overwrite=True)

        assert results["existing_cmd"] is True

        # Verify code is updated
        with open(self.commands_dir / "existing_cmd.json", "r") as f:
            data = json.load(f)
        assert data["code"] == "new code"


class TestGetCommandManager:
    """Test get_command_manager singleton"""

    def test_singleton(self):
        """Test that get_command_manager returns the same instance"""
        manager1 = get_command_manager()
        manager2 = get_command_manager()

        assert manager1 is manager2
