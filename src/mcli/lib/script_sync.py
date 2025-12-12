"""
Script → JSON synchronization system.

DEPRECATION NOTICE:
This module is deprecated. Scripts are now loaded directly without JSON conversion.
Use `mcli.lib.script_loader.ScriptLoader` instead.

The JSON intermediate layer has been removed in favor of direct script loading.
Existing JSON files can be migrated to native scripts using `mcli workflow migrate`.

This module is kept for backward compatibility and will be removed in a future version.

Legacy Architecture (deprecated):
    User's Script (source of truth)
        ↓
    Auto-generate JSON (if missing)
        ↓
    Keep JSON in sync with script (file watching)
        ↓
    Load from JSON (fast startup)

New Architecture:
    User's Script (source of truth)
        ↓
    Load directly via ScriptLoader
        ↓
    Execute with appropriate runtime (Python, Bun, shell, etc.)

Example (deprecated):
    >>> from mcli.lib.script_sync import ScriptSyncManager
    >>> manager = ScriptSyncManager(Path("~/.mcli/commands"))
    >>> manager.sync_all()  # Sync all scripts to JSON
    >>> manager.generate_json(Path("~/.mcli/commands/utils/backup.sh"))

New approach:
    >>> from mcli.lib.script_loader import ScriptLoader
    >>> loader = ScriptLoader(Path("~/.mcli/workflows"))
    >>> loader.register_all_commands(app)
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

# Supported script extensions and their language mappings
LANGUAGE_MAP = {
    ".py": "python",
    ".ipynb": "python",  # Jupyter notebooks
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".fish": "shell",
    ".js": "javascript",
    ".ts": "typescript",
    ".rb": "ruby",
    ".pl": "perl",
    ".lua": "lua",
}

# Shebang patterns for language detection
SHEBANG_PATTERNS = {
    "python": re.compile(r"#!/.*python"),
    "shell": re.compile(r"#!/.*(?:bash|sh|zsh|fish)"),
    "javascript": re.compile(r"#!/.*node"),
    "typescript": re.compile(r"#!/.*(?:ts-node|deno)"),
    "ruby": re.compile(r"#!/.*ruby"),
    "perl": re.compile(r"#!/.*perl"),
    "lua": re.compile(r"#!/.*lua"),
}

# Comment prefixes by language
COMMENT_PREFIX = {
    "python": "#",
    "shell": "#",
    "ruby": "#",
    "perl": "#",
    "lua": "--",
    "javascript": "//",
    "typescript": "//",
}


class ScriptSyncManager:
    """
    Manages synchronization between raw scripts and JSON workflow definitions.

    This class handles:
    - Detection of script language
    - Extraction of metadata from comments
    - Generation of JSON workflow files
    - Synchronization when scripts change
    - Hash-based change detection
    """

    def __init__(self, commands_dir: Path):
        """
        Initialize the script sync manager.

        Args:
            commands_dir: Root directory containing command scripts
        """
        self.commands_dir = Path(commands_dir).expanduser()
        self.sync_cache_path = self.commands_dir / ".sync_cache.json"
        self.sync_cache = self._load_sync_cache()

    def _load_sync_cache(self) -> dict:
        """Load the sync cache from disk."""
        if not self.sync_cache_path.exists():
            return {}

        try:
            with open(self.sync_cache_path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load sync cache: {e}")
            return {}

    def _save_sync_cache(self):
        """Save the sync cache to disk."""
        try:
            self.sync_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.sync_cache_path, "w") as f:
                json.dump(self.sync_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sync cache: {e}")

    def detect_language(self, script_path: Path) -> str:
        """
        Detect script language from shebang or extension.

        Priority:
        1. Shebang line (#!/usr/bin/env python)
        2. File extension (.py, .sh, etc.)

        Args:
            script_path: Path to the script file

        Returns:
            Language name (e.g., "python", "shell", "javascript")
        """
        try:
            # Check shebang first (more reliable)
            with open(script_path, encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
                if first_line.startswith("#!"):
                    for lang, pattern in SHEBANG_PATTERNS.items():
                        if pattern.search(first_line):
                            logger.debug(f"Detected {lang} from shebang: {first_line}")
                            return lang
        except Exception as e:
            logger.warning(f"Failed to read shebang from {script_path}: {e}")

        # Fallback to extension
        language = LANGUAGE_MAP.get(script_path.suffix, "unknown")
        if language != "unknown":
            logger.debug(f"Detected {language} from extension: {script_path.suffix}")
        else:
            logger.warning(f"Unknown language for {script_path}")

        return language

    def extract_metadata(self, script_path: Path, language: str) -> dict:
        """
        Extract metadata from script comments.

        Looks for @-prefixed metadata in comments:
            # @description: Backup utility for production databases
            # @author: John Doe
            # @version: 1.2.0
            # @requires: psql, aws-cli
            # @tags: backup, database, production

        Args:
            script_path: Path to the script file
            language: Script language

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {
            "description": "",
            "version": "1.0.0",
            "author": "",
            "requires": [],
            "tags": [],
            "shell": None,
        }

        comment_prefix = COMMENT_PREFIX.get(language, "#")
        metadata_pattern = re.compile(rf"^{re.escape(comment_prefix)}\s*@(\w+):\s*(.+)$")

        try:
            with open(script_path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    match = metadata_pattern.match(line)
                    if match:
                        key, value = match.groups()
                        key = key.strip().lower()
                        value = value.strip()

                        if key in ["requires", "tags"]:
                            # Handle comma-separated lists
                            metadata[key] = [v.strip() for v in value.split(",")]
                        else:
                            metadata[key] = value

                        logger.debug(f"Extracted metadata: {key} = {value}")

        except Exception as e:
            logger.warning(f"Failed to extract metadata from {script_path}: {e}")

        return metadata

    def calculate_hash(self, script_path: Path) -> str:
        """
        Calculate SHA256 hash of script file.

        Args:
            script_path: Path to the script file

        Returns:
            Hexadecimal hash string
        """
        try:
            with open(script_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {script_path}: {e}")
            return ""

    def needs_sync(self, script_path: Path, json_path: Path) -> bool:
        """
        Check if JSON needs to be regenerated from script.

        Uses multiple checks:
        1. JSON doesn't exist → needs sync
        2. Script modified more recently than JSON → needs sync
        3. Script hash differs from cached hash → needs sync

        Args:
            script_path: Path to the script file
            json_path: Path to the JSON file

        Returns:
            True if sync is needed, False otherwise
        """
        if not json_path.exists():
            logger.debug(f"JSON missing for {script_path}, needs sync")
            return True

        # Check modification times
        try:
            script_mtime = script_path.stat().st_mtime
            json_mtime = json_path.stat().st_mtime
            if script_mtime > json_mtime:
                logger.debug(f"Script {script_path} modified after JSON, needs sync")
                return True
        except Exception as e:
            logger.warning(f"Failed to compare mtimes: {e}")
            return True

        # Check hash (most reliable)
        script_hash = self.calculate_hash(script_path)
        if not script_hash:
            return True

        try:
            with open(json_path) as f:
                json_data = json.load(f)
                cached_hash = json_data.get("metadata", {}).get("source_hash", "")
                if script_hash != cached_hash:
                    logger.debug(f"Hash mismatch for {script_path}, needs sync")
                    return True
        except Exception as e:
            logger.warning(f"Failed to read JSON hash: {e}")
            return True

        logger.debug(f"Script {script_path} in sync with JSON")
        return False

    def generate_json(
        self, script_path: Path, group: Optional[str] = None, force: bool = False
    ) -> Optional[Path]:
        """
        Generate JSON workflow from script file.

        Creates a JSON file with:
        - Script code embedded
        - Metadata extracted from comments
        - Language and execution info
        - Source hash for change detection

        Special handling for .ipynb files:
        - .ipynb files are already in notebook JSON format, so they're used directly
        - The file itself serves as the JSON workflow representation

        Args:
            script_path: Path to the script file
            group: Optional command group (auto-detected from path if None)
            force: Force regeneration even if up-to-date

        Returns:
            Path to the generated JSON file, or None if generation failed
        """
        # Special handling for .ipynb files - they're already JSON notebooks
        if script_path.suffix == ".ipynb":
            logger.debug(f"Notebook file {script_path} is already in JSON format")
            # Validate it's a proper notebook and return the path itself
            try:
                with open(script_path) as f:
                    data = json.load(f)
                    # Check if it has nbformat field (standard Jupyter format)
                    if "nbformat" in data:
                        return script_path
                    # Otherwise, we need to convert it to proper notebook format
                    logger.warning(f"{script_path} is not a valid Jupyter notebook")
            except Exception as e:
                logger.error(f"Failed to validate notebook {script_path}: {e}")
            return None

        json_path = script_path.with_suffix(".json")

        # Skip if already up-to-date
        if not force and not self.needs_sync(script_path, json_path):
            logger.debug(f"Skipping {script_path}, already in sync")
            return json_path

        logger.info(f"Generating JSON for {script_path}")

        # Detect language
        language = self.detect_language(script_path)
        if language == "unknown":
            logger.warning(f"Skipping {script_path}, unknown language")
            return None

        # Extract metadata
        metadata = self.extract_metadata(script_path, language)

        # Calculate hash
        script_hash = self.calculate_hash(script_path)

        # Read script code
        try:
            with open(script_path, encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            logger.error(f"Failed to read script {script_path}: {e}")
            return None

        # Determine group from directory structure
        if group is None:
            try:
                relative = script_path.relative_to(self.commands_dir)
                if len(relative.parts) > 1:
                    group = relative.parts[0]
            except ValueError:
                pass  # Not relative to commands_dir

        # Generate JSON data
        json_data = {
            "name": script_path.stem,
            "group": group,
            "description": metadata.get("description") or f"{script_path.stem} command",
            "language": language,
            "version": metadata.get("version", "1.0.0"),
            "code": code,
            "metadata": {
                "source_file": str(script_path.relative_to(self.commands_dir)),
                "source_hash": script_hash,
                "author": metadata.get("author", ""),
                "requires": metadata.get("requires", []),
                "tags": metadata.get("tags", []),
                "auto_generated": True,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        # Shell-specific metadata
        if language == "shell":
            json_data["shell"] = metadata.get("shell") or "bash"

        # Save JSON
        try:
            with open(json_path, "w") as f:
                json.dump(json_data, f, indent=2)
            logger.info(f"Generated JSON: {json_path}")

            # Update sync cache
            cache_key = str(script_path.relative_to(self.commands_dir))
            self.sync_cache[cache_key] = {
                "hash": script_hash,
                "json_path": str(json_path.relative_to(self.commands_dir)),
                "synced_at": datetime.utcnow().isoformat() + "Z",
            }
            self._save_sync_cache()

            return json_path

        except Exception as e:
            logger.error(f"Failed to save JSON for {script_path}: {e}")
            return None

    def sync_all(self, force: bool = False) -> list[Path]:
        """
        Sync all scripts in commands directory to JSON.

        Recursively scans the commands directory for script files and
        generates/updates their JSON workflow files.

        Args:
            force: Force regeneration of all JSONs

        Returns:
            List of paths to synced JSON files
        """
        if not self.commands_dir.exists():
            logger.warning(f"Commands directory does not exist: {self.commands_dir}")
            return []

        synced = []
        skipped = []

        logger.info(f"Syncing scripts in {self.commands_dir}")

        for script_path in self.commands_dir.rglob("*"):
            # Skip directories
            if script_path.is_dir():
                continue

            # Skip non-script files
            if script_path.suffix not in LANGUAGE_MAP:
                continue

            # Skip JSON files themselves
            if script_path.suffix == ".json":
                continue

            # Skip hidden files and directories (but not the commands_dir itself)
            # Get the relative path from commands_dir to check for hidden parts
            try:
                relative_parts = script_path.relative_to(self.commands_dir).parts
                if any(part.startswith(".") for part in relative_parts):
                    continue
            except ValueError:
                # Not relative to commands_dir, skip
                continue

            # Generate/update JSON
            json_path = self.generate_json(script_path, force=force)
            if json_path:
                synced.append(json_path)
            else:
                skipped.append(script_path)

        if synced:
            logger.info(f"Synced {len(synced)} scripts to JSON")
        if skipped:
            logger.warning(f"Skipped {len(skipped)} scripts")

        return synced

    def cleanup_orphaned_json(self) -> list[Path]:
        """
        Remove JSON files that no longer have corresponding scripts.

        Returns:
            List of paths to removed JSON files
        """
        removed = []

        for json_path in self.commands_dir.rglob("*.json"):
            # Skip sync cache
            if json_path == self.sync_cache_path:
                continue

            # Skip lockfile
            if json_path.name == "commands.lock.json":
                continue

            # Check if auto-generated
            try:
                with open(json_path) as f:
                    json_data = json.load(f)
                    if not json_data.get("metadata", {}).get("auto_generated"):
                        continue  # Manual JSON, don't delete
            except Exception:
                continue

            # Check if source script exists
            script_extensions = list(LANGUAGE_MAP.keys())
            script_exists = False

            for ext in script_extensions:
                script_path = json_path.with_suffix(ext)
                if script_path.exists():
                    script_exists = True
                    break

            if not script_exists:
                logger.info(f"Removing orphaned JSON: {json_path}")
                json_path.unlink()
                removed.append(json_path)

        if removed:
            logger.info(f"Removed {len(removed)} orphaned JSON files")

        return removed
