"""Unit tests for Pydantic workflow configuration models."""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from mcli.lib.workflow_models import (
    LockfileData,
    LockfileEntry,
    ScriptLanguage,
    ScriptMetadata,
    ShellType,
    SyncData,
    SyncHistoryEntry,
)


class TestScriptMetadata:
    """Tests for ScriptMetadata model."""

    def test_default_values(self):
        """Test ScriptMetadata with default values."""
        metadata = ScriptMetadata()
        assert metadata.description == ""
        assert metadata.version == "1.0.0"
        assert metadata.author == ""
        assert metadata.group == "workflows"
        assert metadata.requires == []
        assert metadata.tags == []
        assert metadata.shell == ShellType.BASH

    def test_with_custom_values(self):
        """Test ScriptMetadata with custom values."""
        metadata = ScriptMetadata(
            description="My utility script",
            version="2.0.0",
            author="John Doe",
            group="utilities",
            requires=["requests", "pandas"],
            tags=["data", "processing"],
            shell=ShellType.ZSH,
        )
        assert metadata.description == "My utility script"
        assert metadata.version == "2.0.0"
        assert metadata.author == "John Doe"
        assert metadata.group == "utilities"
        assert metadata.requires == ["requests", "pandas"]
        assert metadata.tags == ["data", "processing"]
        assert metadata.shell == ShellType.ZSH

    def test_requires_from_comma_string(self):
        """Test parsing requires from comma-separated string."""
        metadata = ScriptMetadata(requires="requests, pandas, numpy")
        assert metadata.requires == ["requests", "pandas", "numpy"]

    def test_tags_from_comma_string(self):
        """Test parsing tags from comma-separated string."""
        metadata = ScriptMetadata(tags="data, ml, production")
        assert metadata.tags == ["data", "ml", "production"]

    def test_empty_requires_string(self):
        """Test empty requires string."""
        metadata = ScriptMetadata(requires="")
        assert metadata.requires == []

    def test_shell_string_conversion(self):
        """Test shell type conversion from string."""
        metadata = ScriptMetadata(shell="zsh")
        assert metadata.shell == ShellType.ZSH

    def test_shell_unknown_defaults_bash(self):
        """Test unknown shell defaults to bash."""
        metadata = ScriptMetadata(shell="unknown_shell")
        assert metadata.shell == ShellType.BASH

    def test_version_validation_valid(self):
        """Test version validation with valid formats."""
        for version in ["1.0.0", "2.1", "3", "1.0.0-beta", "v1.2.3"]:
            metadata = ScriptMetadata(version=version)
            assert version in metadata.version

    def test_version_validation_invalid(self):
        """Test version validation rejects invalid formats."""
        with pytest.raises(ValidationError) as exc_info:
            ScriptMetadata(version="invalid")
        assert "version" in str(exc_info.value)

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from fields."""
        metadata = ScriptMetadata(
            description="  My script  ",
            version="  1.0.0  ",
            author="  Author  ",
        )
        assert metadata.description == "My script"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Author"


class TestLockfileEntry:
    """Tests for LockfileEntry model."""

    def test_minimal_entry(self):
        """Test LockfileEntry with minimal required fields."""
        entry = LockfileEntry(
            file="my_script.py",
            language=ScriptLanguage.PYTHON,
            content_hash="abc123def456",
        )
        assert entry.file == "my_script.py"
        assert entry.language == ScriptLanguage.PYTHON
        assert entry.content_hash == "abc123def456"
        assert entry.version == "1.0.0"
        assert entry.group == "workflows"

    def test_full_entry(self):
        """Test LockfileEntry with all fields."""
        now = datetime.now()
        entry = LockfileEntry(
            file="utils/backup.sh",
            language=ScriptLanguage.SHELL,
            content_hash="hash123",
            version="2.1.0",
            group="utilities",
            description="Backup script",
            author="Admin",
            requires=["aws-cli"],
            tags=["backup", "production"],
            shell="bash",
            last_modified=now,
        )
        assert entry.file == "utils/backup.sh"
        assert entry.language == ScriptLanguage.SHELL
        assert entry.shell == "bash"
        assert entry.last_modified == now

    def test_language_string_conversion(self):
        """Test language conversion from string."""
        entry = LockfileEntry(
            file="script.js",
            language="javascript",
            content_hash="hash123",
        )
        assert entry.language == ScriptLanguage.JAVASCRIPT

    def test_language_unknown(self):
        """Test unknown language defaults to UNKNOWN."""
        entry = LockfileEntry(
            file="script.unknown",
            language="fortran",
            content_hash="hash123",
        )
        assert entry.language == ScriptLanguage.UNKNOWN

    def test_file_required(self):
        """Test that file is required."""
        with pytest.raises(ValidationError) as exc_info:
            LockfileEntry(language="python", content_hash="hash")
        assert "file" in str(exc_info.value)

    def test_content_hash_required(self):
        """Test that content_hash is required."""
        with pytest.raises(ValidationError) as exc_info:
            LockfileEntry(file="script.py", language="python")
        assert "content_hash" in str(exc_info.value)


class TestLockfileData:
    """Tests for LockfileData model."""

    def test_empty_lockfile(self):
        """Test empty lockfile creation."""
        lockfile = LockfileData()
        assert lockfile.version == "1.0"
        assert lockfile.commands == {}
        assert lockfile.command_count == 0
        assert lockfile.generated_at is not None

    def test_lockfile_with_commands(self):
        """Test lockfile with commands."""
        entry = LockfileEntry(
            file="script.py",
            language=ScriptLanguage.PYTHON,
            content_hash="hash123",
        )
        lockfile = LockfileData(commands={"my_command": entry})
        assert lockfile.command_count == 1
        assert lockfile.has_command("my_command")
        assert not lockfile.has_command("nonexistent")

    def test_get_command(self):
        """Test getting a command by name."""
        entry = LockfileEntry(
            file="script.py",
            language=ScriptLanguage.PYTHON,
            content_hash="hash123",
        )
        lockfile = LockfileData(commands={"test_cmd": entry})

        cmd = lockfile.get_command("test_cmd")
        assert cmd is not None
        assert cmd.file == "script.py"

        assert lockfile.get_command("nonexistent") is None

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        entry = LockfileEntry(
            file="script.py",
            language=ScriptLanguage.PYTHON,
            content_hash="hash123",
            description="Test script",
        )
        lockfile = LockfileData(
            version="2.0",
            commands={"test": entry},
        )

        # Serialize
        data = lockfile.model_dump(mode="json")

        # Deserialize
        restored = LockfileData.model_validate(data)

        assert restored.version == "2.0"
        assert restored.command_count == 1
        assert restored.commands["test"].file == "script.py"


class TestSyncData:
    """Tests for SyncData model."""

    def test_default_sync_data(self):
        """Test SyncData with defaults."""
        sync = SyncData()
        assert sync.version == "1.0"
        assert sync.source == "mcli"
        assert sync.description == ""
        assert sync.commands == {}
        assert sync.hash is None

    def test_sync_data_with_hash(self):
        """Test SyncData with valid hash."""
        valid_hash = "a" * 64  # SHA256 produces 64 hex chars
        sync = SyncData(hash=valid_hash)
        assert sync.hash == valid_hash

    def test_sync_data_invalid_hash_length(self):
        """Test SyncData rejects invalid hash length."""
        with pytest.raises(ValidationError) as exc_info:
            SyncData(hash="tooshort")
        assert "hash" in str(exc_info.value).lower()

    def test_sync_data_invalid_hash_chars(self):
        """Test SyncData rejects non-hex hash."""
        invalid_hash = "g" * 64  # 'g' is not a hex char
        with pytest.raises(ValidationError) as exc_info:
            SyncData(hash=invalid_hash)
        assert "hex" in str(exc_info.value).lower()

    def test_sync_data_hash_normalized(self):
        """Test that hash is normalized to lowercase."""
        upper_hash = "A" * 64
        sync = SyncData(hash=upper_hash)
        assert sync.hash == "a" * 64


class TestSyncHistoryEntry:
    """Tests for SyncHistoryEntry model."""

    def test_minimal_entry(self):
        """Test SyncHistoryEntry with minimal fields."""
        entry = SyncHistoryEntry(cid="QmTest123")
        assert entry.cid == "QmTest123"
        assert entry.description == ""
        assert entry.command_count == 0
        assert entry.timestamp is not None

    def test_full_entry(self):
        """Test SyncHistoryEntry with all fields."""
        now = datetime.now()
        entry = SyncHistoryEntry(
            cid="QmTestCID",
            timestamp=now,
            description="v1.0 release",
            hash="a" * 64,
            command_count=5,
        )
        assert entry.cid == "QmTestCID"
        assert entry.timestamp == now
        assert entry.description == "v1.0 release"
        assert entry.command_count == 5

    def test_cid_required(self):
        """Test that CID is required."""
        with pytest.raises(ValidationError) as exc_info:
            SyncHistoryEntry()
        assert "cid" in str(exc_info.value)

    def test_command_count_non_negative(self):
        """Test that command_count must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            SyncHistoryEntry(cid="QmTest", command_count=-1)
        assert "command_count" in str(exc_info.value)


class TestScriptLanguageEnum:
    """Tests for ScriptLanguage enum."""

    def test_all_languages(self):
        """Test all supported languages are defined."""
        languages = [lang.value for lang in ScriptLanguage]
        assert "python" in languages
        assert "shell" in languages
        assert "javascript" in languages
        assert "typescript" in languages
        assert "ipynb" in languages
        assert "unknown" in languages

    def test_enum_string_conversion(self):
        """Test enum to string conversion."""
        assert ScriptLanguage.PYTHON.value == "python"
        assert str(ScriptLanguage.PYTHON.value) == "python"


class TestShellTypeEnum:
    """Tests for ShellType enum."""

    def test_all_shells(self):
        """Test all supported shells are defined."""
        shells = [s.value for s in ShellType]
        assert "bash" in shells
        assert "zsh" in shells
        assert "fish" in shells
        assert "sh" in shells
