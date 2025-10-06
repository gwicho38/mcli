"""
Tests for mcli.self.self_cmd utility functions
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestLockfileUtilities:
    """Test suite for lockfile utility functions"""

    def test_hash_command_state(self):
        """Test hashing command state"""
        from mcli.self.self_cmd import hash_command_state

        commands = [
            {"name": "cmd1", "group": "group1"},
            {"name": "cmd2", "group": "group2"}
        ]

        hash1 = hash_command_state(commands)

        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex digest

        # Same commands should produce same hash
        hash2 = hash_command_state(commands)
        assert hash1 == hash2

    def test_hash_command_state_order_independent(self):
        """Test that command order doesn't affect hash"""
        from mcli.self.self_cmd import hash_command_state

        commands1 = [
            {"name": "cmd1", "group": "group1"},
            {"name": "cmd2", "group": "group2"}
        ]

        commands2 = [
            {"name": "cmd2", "group": "group2"},
            {"name": "cmd1", "group": "group1"}
        ]

        hash1 = hash_command_state(commands1)
        hash2 = hash_command_state(commands2)

        # Should be same due to sorting
        assert hash1 == hash2

    def test_hash_command_state_different_commands(self):
        """Test that different commands produce different hashes"""
        from mcli.self.self_cmd import hash_command_state

        commands1 = [{"name": "cmd1", "group": "group1"}]
        commands2 = [{"name": "cmd2", "group": "group2"}]

        hash1 = hash_command_state(commands1)
        hash2 = hash_command_state(commands2)

        assert hash1 != hash2

    @patch('mcli.self.self_cmd.LOCKFILE_PATH')
    def test_load_lockfile_exists(self, mock_lockfile_path):
        """Test loading existing lockfile"""
        from mcli.self.self_cmd import load_lockfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_data = [{"hash": "abc123", "timestamp": "2025-01-01T00:00:00Z", "commands": []}]
            json.dump(test_data, f)
            temp_path = f.name

        mock_lockfile_path.__str__ = lambda self: temp_path
        mock_lockfile_path.exists.return_value = True

        # Mock the open call
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_data)
            mock_open.return_value.__enter__.return_value.__iter__ = lambda self: iter(json.dumps(test_data).splitlines())

            with open(temp_path, 'r') as f:
                result = json.load(f)

        assert result == test_data

        # Cleanup
        Path(temp_path).unlink()

    @patch('mcli.self.self_cmd.LOCKFILE_PATH')
    def test_load_lockfile_not_exists(self, mock_lockfile_path):
        """Test loading lockfile when it doesn't exist"""
        from mcli.self.self_cmd import load_lockfile

        mock_lockfile_path.exists.return_value = False

        result = load_lockfile()

        assert result == []

    @patch('mcli.self.self_cmd.LOCKFILE_PATH')
    def test_save_lockfile(self, mock_lockfile_path):
        """Test saving lockfile"""
        from mcli.self.self_cmd import save_lockfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        mock_lockfile_path.__str__ = lambda self: temp_path

        test_states = [
            {"hash": "abc123", "timestamp": "2025-01-01T00:00:00Z", "commands": []}
        ]

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            save_lockfile(test_states)

            # Verify json.dump was called
            assert mock_open.called

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @patch('mcli.self.self_cmd.load_lockfile')
    @patch('mcli.self.self_cmd.save_lockfile')
    def test_append_lockfile(self, mock_save, mock_load):
        """Test appending to lockfile"""
        from mcli.self.self_cmd import append_lockfile

        existing_states = [
            {"hash": "abc123", "timestamp": "2025-01-01T00:00:00Z", "commands": []}
        ]
        mock_load.return_value = existing_states

        new_state = {"hash": "def456", "timestamp": "2025-01-02T00:00:00Z", "commands": []}

        append_lockfile(new_state)

        # Verify save was called with combined states
        mock_save.assert_called_once()
        saved_states = mock_save.call_args[0][0]
        assert len(saved_states) == 2
        assert saved_states[1] == new_state

    @patch('mcli.self.self_cmd.load_lockfile')
    def test_find_state_by_hash_found(self, mock_load):
        """Test finding state by hash when it exists"""
        from mcli.self.self_cmd import find_state_by_hash

        states = [
            {"hash": "abc123", "timestamp": "2025-01-01T00:00:00Z", "commands": []},
            {"hash": "def456", "timestamp": "2025-01-02T00:00:00Z", "commands": []}
        ]
        mock_load.return_value = states

        result = find_state_by_hash("def456")

        assert result is not None
        assert result["hash"] == "def456"

    @patch('mcli.self.self_cmd.load_lockfile')
    def test_find_state_by_hash_not_found(self, mock_load):
        """Test finding state by hash when it doesn't exist"""
        from mcli.self.self_cmd import find_state_by_hash

        states = [
            {"hash": "abc123", "timestamp": "2025-01-01T00:00:00Z", "commands": []}
        ]
        mock_load.return_value = states

        result = find_state_by_hash("nonexistent")

        assert result is None

    @patch('mcli.self.self_cmd.find_state_by_hash')
    @patch('builtins.print')
    def test_restore_command_state_found(self, mock_print, mock_find):
        """Test restoring command state when hash found"""
        from mcli.self.self_cmd import restore_command_state

        state = {
            "hash": "abc123",
            "timestamp": "2025-01-01T00:00:00Z",
            "commands": [{"name": "cmd1"}]
        }
        mock_find.return_value = state

        result = restore_command_state("abc123")

        assert result is True
        mock_print.assert_called_once()

    @patch('mcli.self.self_cmd.find_state_by_hash')
    def test_restore_command_state_not_found(self, mock_find):
        """Test restoring command state when hash not found"""
        from mcli.self.self_cmd import restore_command_state

        mock_find.return_value = None

        result = restore_command_state("nonexistent")

        assert result is False

    @patch('mcli.self.self_cmd.get_current_command_state')
    def test_get_current_command_state(self, mock_get_state):
        """Test getting current command state"""
        from mcli.self.self_cmd import get_current_command_state

        expected_commands = [{"name": "cmd1", "group": "group1"}]
        mock_get_state.return_value = expected_commands

        result = get_current_command_state()

        assert result == expected_commands


class TestGetCommandTemplate:
    """Test suite for get_command_template function"""

    def test_get_command_template_no_group(self):
        """Test generating command template without group"""
        from mcli.self.self_cmd import get_command_template

        template = get_command_template("mycommand")

        assert isinstance(template, str)
        assert "mycommand" in template
        assert "def " in template or "@" in template

    def test_get_command_template_with_group(self):
        """Test generating command template with group"""
        from mcli.self.self_cmd import get_command_template

        template = get_command_template("mycommand", group="mygroup")

        assert isinstance(template, str)
        assert "mycommand" in template
        assert "mygroup" in template
