"""Type definitions for mcli.

This module provides TypedDict and dataclass definitions for structured data
used throughout the mcli application. Using these types improves code clarity
and enables better static analysis.

Example:
    from mcli.lib.types import CommandMetadata, ScriptInfo

    def process_metadata(metadata: CommandMetadata) -> None:
        print(f"Command: {metadata['name']}")
        print(f"Version: {metadata['version']}")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

# =============================================================================
# Command Metadata Types
# =============================================================================


class CommandMetadata(TypedDict, total=False):
    """Metadata for a workflow command.

    This TypedDict represents the metadata extracted from or assigned to
    a workflow command script.

    Required fields:
        name: Command name (e.g., "backup_db")
        description: Human-readable description

    Optional fields:
        version: Semantic version string (default: "1.0.0")
        group: Command group for organization (default: "workflows")
        author: Author name or email
        requires: List of dependencies
        tags: List of tags for categorization
        shell: Shell type for shell scripts (bash, zsh, etc.)
        language: Script language (python, shell, javascript, etc.)
        path: Path to the script file

    Example:
        metadata: CommandMetadata = {
            "name": "backup_db",
            "description": "Backup database to S3",
            "version": "1.2.0",
            "group": "utils",
            "requires": ["aws-cli", "psql"],
            "tags": ["backup", "database"],
        }
    """

    # Required
    name: str
    description: str

    # Optional with defaults
    version: str
    group: str
    author: str
    requires: List[str]
    tags: List[str]
    shell: str
    language: str
    path: str


class CommandMetadataDefaults(TypedDict):
    """Default values for CommandMetadata fields.

    Used when creating new commands or when metadata is missing.
    """

    description: str
    version: str
    author: str
    group: str
    requires: List[str]
    tags: List[str]
    shell: str


# Default metadata values as a constant dict
DEFAULT_COMMAND_METADATA: CommandMetadataDefaults = {
    "description": "",
    "version": "1.0.0",
    "author": "",
    "group": "workflows",
    "requires": [],
    "tags": [],
    "shell": "bash",
}


# =============================================================================
# Script Info Types
# =============================================================================


@dataclass
class ScriptInfo:
    """Information about a script file.

    This dataclass holds all relevant information about a script file,
    including its path, detected language, and extracted metadata.

    Attributes:
        path: Path to the script file
        name: Command name derived from filename
        language: Detected or specified language
        metadata: Extracted or assigned metadata
        content_hash: SHA256 hash of file contents (for change detection)
        is_valid: Whether the script passed validation

    Example:
        info = ScriptInfo(
            path=Path("~/.mcli/workflows/backup.py"),
            name="backup",
            language="python",
            metadata={"description": "Backup utility", "version": "1.0.0"},
        )
    """

    path: Path
    name: str
    language: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: Optional[str] = None
    is_valid: bool = True

    @property
    def extension(self) -> str:
        """Get the file extension."""
        return self.path.suffix

    @property
    def description(self) -> str:
        """Get the description from metadata."""
        return self.metadata.get("description", f"{self.name} command")

    @property
    def version(self) -> str:
        """Get the version from metadata."""
        return self.metadata.get("version", "1.0.0")

    @property
    def group(self) -> str:
        """Get the group from metadata."""
        return self.metadata.get("group", "workflows")


@dataclass
class ScriptTemplate:
    """Template information for generating new scripts.

    Attributes:
        name: Command name
        description: Command description
        group: Command group
        version: Initial version
        language: Script language
        shell: Shell type (for shell scripts)
        content: Generated template content
    """

    name: str
    description: str
    group: str
    version: str
    language: str
    shell: Optional[str] = None
    content: str = ""


# =============================================================================
# Lockfile Types
# =============================================================================


class LockfileEntry(TypedDict, total=False):
    """Entry in the workflows lockfile.

    Each entry represents a single script in the lockfile.
    """

    name: str
    path: str
    language: str
    hash: str
    description: str
    version: str
    group: str
    requires: List[str]
    tags: List[str]
    updated_at: str


class LockfileSchema(TypedDict):
    """Schema for the workflows.lock.json file.

    Attributes:
        version: Lockfile schema version
        generated_at: ISO timestamp of generation
        scripts: Dictionary of script entries keyed by name
    """

    version: str
    generated_at: str
    scripts: Dict[str, LockfileEntry]


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class CommandResult:
    """Result of a command execution.

    Attributes:
        success: Whether the command succeeded
        exit_code: Process exit code (0 = success)
        stdout: Standard output
        stderr: Standard error
        duration_ms: Execution duration in milliseconds
    """

    success: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: Optional[float] = None

    @classmethod
    def ok(cls, stdout: str = "", duration_ms: Optional[float] = None) -> "CommandResult":
        """Create a successful result."""
        return cls(success=True, exit_code=0, stdout=stdout, duration_ms=duration_ms)

    @classmethod
    def error(
        cls,
        exit_code: int,
        stderr: str = "",
        stdout: str = "",
        duration_ms: Optional[float] = None,
    ) -> "CommandResult":
        """Create an error result."""
        return cls(
            success=False,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )


__all__ = [
    # Command metadata
    "CommandMetadata",
    "CommandMetadataDefaults",
    "DEFAULT_COMMAND_METADATA",
    # Script info
    "ScriptInfo",
    "ScriptTemplate",
    # Lockfile
    "LockfileEntry",
    "LockfileSchema",
    # Results
    "CommandResult",
]
