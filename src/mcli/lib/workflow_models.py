"""
Pydantic models for workflow configuration validation.

Provides type-safe validation for:
- Script metadata (ScriptMetadata)
- Lockfile structure (LockfileData, LockfileEntry)
- IPFS sync data (SyncData)

These models ensure consistent validation across the workflow system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScriptLanguage(str, Enum):
    """Supported script languages."""

    PYTHON = "python"
    SHELL = "shell"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    IPYNB = "ipynb"
    UNKNOWN = "unknown"


class ShellType(str, Enum):
    """Supported shell types for shell scripts."""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    SH = "sh"


class ScriptMetadata(BaseModel):
    """
    Metadata extracted from script files.

    Validates metadata from @-prefixed comments like:
        # @description: My utility script
        # @version: 1.0.0
        # @requires: requests, pandas
        # @tags: utility, data
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    description: str = Field(default="")
    version: str = Field(default="1.0.0")
    author: str = Field(default="")
    group: str = Field(default="workflows")
    requires: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    shell: ShellType = Field(default=ShellType.BASH)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure version follows semver-like format."""
        if not v:
            return "1.0.0"
        # Basic validation: at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError(f"Invalid version format: {v}")
        return v.strip()

    @field_validator("requires", "tags", mode="before")
    @classmethod
    def parse_list_fields(cls, v: Any) -> list[str]:
        """Parse list fields from comma-separated string or list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if item]
        return []

    @field_validator("shell", mode="before")
    @classmethod
    def validate_shell(cls, v: Any) -> ShellType:
        """Convert string to ShellType enum."""
        if v is None:
            return ShellType.BASH
        if isinstance(v, ShellType):
            return v
        v_str = str(v).lower().strip()
        try:
            return ShellType(v_str)
        except ValueError:
            # Default to bash for unknown shells
            return ShellType.BASH


class LockfileEntry(BaseModel):
    """
    Entry for a single command in the lockfile.

    Tracks the script file, its hash for change detection,
    and all extracted metadata.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    file: str = Field(..., min_length=1)
    language: ScriptLanguage
    content_hash: str = Field(..., min_length=1)
    version: str = Field(default="1.0.0")
    group: str = Field(default="workflows")
    description: str = Field(default="")
    author: str = Field(default="")
    requires: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    shell: Optional[str] = Field(default=None)
    last_modified: Optional[datetime] = Field(default=None)

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, v: Any) -> ScriptLanguage:
        """Convert string to ScriptLanguage enum."""
        if isinstance(v, ScriptLanguage):
            return v
        v_str = str(v).lower().strip()
        try:
            return ScriptLanguage(v_str)
        except ValueError:
            return ScriptLanguage.UNKNOWN


class LockfileData(BaseModel):
    """
    Schema for workflows.lock.json lockfile.

    The lockfile tracks all registered workflow commands,
    their content hashes, and metadata for change detection.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    version: str = Field(default="1.0")
    generated_at: datetime = Field(default_factory=datetime.now)
    commands: dict[str, LockfileEntry] = Field(default_factory=dict)

    @property
    def command_count(self) -> int:
        """Return the number of registered commands."""
        return len(self.commands)

    def get_command(self, name: str) -> Optional[LockfileEntry]:
        """Get a command entry by name."""
        return self.commands.get(name)

    def has_command(self, name: str) -> bool:
        """Check if a command exists."""
        return name in self.commands


class SyncData(BaseModel):
    """
    Schema for IPFS sync payload.

    Contains the commands lockfile data plus sync metadata
    for upload/download from IPFS gateways.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    version: str = Field(default="1.0")
    synced_at: datetime = Field(default_factory=datetime.now)
    description: str = Field(default="")
    source: str = Field(default="mcli")
    commands: dict[str, Any] = Field(default_factory=dict)
    hash: Optional[str] = Field(default=None)

    @field_validator("hash")
    @classmethod
    def validate_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate hash format (SHA256 hex string)."""
        if v is None:
            return None
        v = v.strip()
        # SHA256 produces 64 hex characters
        if len(v) != 64:
            raise ValueError(f"Invalid hash length: expected 64, got {len(v)}")
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("Hash must be a valid hex string")
        return v.lower()


class SyncHistoryEntry(BaseModel):
    """Entry in the IPFS sync history."""

    model_config = ConfigDict(str_strip_whitespace=True)

    cid: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.now)
    description: str = Field(default="")
    hash: Optional[str] = Field(default=None)
    command_count: int = Field(default=0, ge=0)


# Convenience type exports
__all__ = [
    "ScriptLanguage",
    "ShellType",
    "ScriptMetadata",
    "LockfileEntry",
    "LockfileData",
    "SyncData",
    "SyncHistoryEntry",
]
