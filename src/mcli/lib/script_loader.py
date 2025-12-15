"""
Native script loading for mcli workflows.

Loads and executes script files directly without JSON intermediate layer.
Supports Python (.py), Shell (.sh, .bash), JavaScript (.js), TypeScript (.ts),
and Jupyter notebooks (.ipynb).

Example:
    >>> from mcli.lib.script_loader import ScriptLoader
    >>> loader = ScriptLoader(Path("~/.mcli/workflows"))
    >>> loader.register_all_commands(app)  # Register with Click group
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import click

from mcli.lib.logger.logger import get_logger, register_subprocess

logger = get_logger(__name__)


# Supported script extensions and their language mappings
SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".py": "python",
    ".sh": "shell",
    ".bash": "shell",
    ".js": "javascript",
    ".ts": "typescript",
    ".ipynb": "ipynb",
}

# Shebang patterns for language detection
SHEBANG_PATTERNS: Dict[str, re.Pattern] = {
    "python": re.compile(r"#!/.*python"),
    "shell": re.compile(r"#!/.*(?:bash|sh|zsh|fish)"),
    "javascript": re.compile(r"#!/.*(?:node|bun)"),
    "typescript": re.compile(r"#!/.*(?:ts-node|deno|bun)"),
}

# Comment prefixes by language
COMMENT_PREFIX: Dict[str, str] = {
    "python": "#",
    "shell": "#",
    "javascript": "//",
    "typescript": "//",
}

# Default metadata values
DEFAULT_METADATA: Dict[str, Any] = {
    "description": "",
    "version": "1.0.0",
    "author": "",
    "group": "workflows",
    "requires": [],
    "tags": [],
    "shell": "bash",
}


class ScriptLoader:
    """
    Loads and executes native script files directly.

    This class handles:
    - Discovery of script files in the workflows directory
    - Detection of script language from shebang or extension
    - Extraction of metadata from comments
    - Registration of scripts as Click commands
    - Execution of scripts using appropriate runtime
    """

    def __init__(self, workflows_dir: Path):
        """
        Initialize the script loader.

        Args:
            workflows_dir: Directory containing workflow scripts
        """
        self.workflows_dir = Path(workflows_dir).expanduser()
        self.lockfile_path = self.workflows_dir / "workflows.lock.json"
        self.loaded_commands: Dict[str, click.Command] = {}

    def discover_scripts(self) -> List[Path]:
        """
        Find all supported script files in the workflows directory.

        Returns:
            List of paths to script files, sorted by name
        """
        scripts: List[Path] = []

        if not self.workflows_dir.exists():
            logger.debug(f"Workflows directory does not exist: {self.workflows_dir}")
            return scripts

        include_test = os.environ.get("MCLI_INCLUDE_TEST_COMMANDS", "false").lower() == "true"

        for script_path in self.workflows_dir.rglob("*"):
            # Skip directories
            if script_path.is_dir():
                continue

            # Skip files with unsupported extensions
            if script_path.suffix not in SUPPORTED_EXTENSIONS:
                continue

            # Skip hidden files and directories (only check path relative to workflows_dir)
            try:
                relative_path = script_path.relative_to(self.workflows_dir)
                if any(part.startswith(".") for part in relative_path.parts):
                    continue
            except ValueError:
                # Not relative to workflows_dir, skip
                continue

            # Skip test scripts unless explicitly included
            if not include_test and script_path.stem.startswith(("test_", "test-")):
                logger.debug(f"Skipping test script: {script_path.name}")
                continue

            scripts.append(script_path)

        return sorted(scripts, key=lambda p: p.stem)

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
        # Special case for notebooks
        if script_path.suffix == ".ipynb":
            return "ipynb"

        try:
            # Check shebang first (more reliable)
            with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
                if first_line.startswith("#!"):
                    for lang, pattern in SHEBANG_PATTERNS.items():
                        if pattern.search(first_line):
                            logger.debug(f"Detected {lang} from shebang: {first_line}")
                            return lang
        except Exception as e:
            logger.warning(f"Failed to read shebang from {script_path}: {e}")

        # Fallback to extension
        language = SUPPORTED_EXTENSIONS.get(script_path.suffix, "unknown")
        if language != "unknown":
            logger.debug(f"Detected {language} from extension: {script_path.suffix}")
        else:
            logger.warning(f"Unknown language for {script_path}")

        return language

    def extract_metadata(self, script_path: Path, language: str) -> Dict[str, Any]:
        """
        Extract metadata from script comments.

        Looks for @-prefixed metadata in comments:
            # @description: Backup utility for production databases
            # @version: 1.2.0
            # @author: John Doe
            # @group: data
            # @requires: psql, aws-cli
            # @tags: backup, database, production
            # @shell: bash

        Args:
            script_path: Path to the script file
            language: Script language

        Returns:
            Dictionary of extracted metadata with defaults
        """
        metadata = DEFAULT_METADATA.copy()
        metadata["requires"] = []  # Ensure fresh list
        metadata["tags"] = []  # Ensure fresh list

        # Handle notebooks separately
        if language == "ipynb":
            return self._extract_notebook_metadata(script_path)

        comment_prefix = COMMENT_PREFIX.get(language, "#")
        metadata_pattern = re.compile(rf"^{re.escape(comment_prefix)}\s*@(\w+):\s*(.+)$")

        try:
            with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    match = metadata_pattern.match(line)
                    if match:
                        key, value = match.groups()
                        key = key.strip().lower()
                        value = value.strip()

                        if key in ["requires", "tags"]:
                            # Handle comma-separated lists
                            metadata[key] = [v.strip() for v in value.split(",") if v.strip()]
                        else:
                            metadata[key] = value

                        logger.debug(f"Extracted metadata: {key} = {value}")

        except Exception as e:
            logger.warning(f"Failed to extract metadata from {script_path}: {e}")

        # Set default description if not provided
        if not metadata.get("description"):
            metadata["description"] = f"{script_path.stem} command"

        return metadata

    def _extract_notebook_metadata(self, notebook_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from Jupyter notebook.

        Looks for metadata in notebook's metadata.mcli section.

        Args:
            notebook_path: Path to the notebook file

        Returns:
            Dictionary of extracted metadata
        """
        metadata = DEFAULT_METADATA.copy()
        metadata["requires"] = []
        metadata["tags"] = []

        try:
            with open(notebook_path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            # Check for mcli metadata section
            mcli_metadata = notebook.get("metadata", {}).get("mcli", {})
            if mcli_metadata:
                for key in ["description", "version", "author", "group", "requires", "tags"]:
                    if key in mcli_metadata:
                        metadata[key] = mcli_metadata[key]

            # Fallback: try to extract from first markdown cell
            if not metadata.get("description"):
                cells = notebook.get("cells", [])
                for cell in cells:
                    if cell.get("cell_type") == "markdown":
                        source = "".join(cell.get("source", []))
                        # Look for first heading or paragraph
                        lines = source.strip().split("\n")
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                metadata["description"] = line[:200]  # Limit length
                                break
                            elif line.startswith("# "):
                                metadata["description"] = line[2:].strip()
                                break
                        break

        except Exception as e:
            logger.warning(f"Failed to extract notebook metadata from {notebook_path}: {e}")

        if not metadata.get("description"):
            metadata["description"] = f"{notebook_path.stem} notebook"

        return metadata

    def calculate_hash(self, script_path: Path) -> str:
        """
        Calculate SHA256 hash of script file.

        Args:
            script_path: Path to the script file

        Returns:
            Hexadecimal hash string prefixed with "sha256:"
        """
        try:
            with open(script_path, "rb") as f:
                hash_value = hashlib.sha256(f.read()).hexdigest()
                return f"sha256:{hash_value}"
        except Exception as e:
            logger.error(f"Failed to calculate hash for {script_path}: {e}")
            return ""

    def get_script_info(self, script_path: Path) -> Dict[str, Any]:
        """
        Get complete information about a script.

        Args:
            script_path: Path to the script file

        Returns:
            Dictionary containing script metadata, language, hash, etc.
        """
        language = self.detect_language(script_path)
        metadata = self.extract_metadata(script_path, language)
        content_hash = self.calculate_hash(script_path)

        try:
            mtime = datetime.fromtimestamp(script_path.stat().st_mtime).isoformat() + "Z"
        except Exception:
            mtime = datetime.utcnow().isoformat() + "Z"

        return {
            "file": script_path.name,
            "language": language,
            "content_hash": content_hash,
            "version": metadata.get("version", "1.0.0"),
            "group": metadata.get("group", "workflows"),
            "description": metadata.get("description", ""),
            "author": metadata.get("author", ""),
            "requires": metadata.get("requires", []),
            "tags": metadata.get("tags", []),
            "shell": metadata.get("shell", "bash") if language == "shell" else None,
            "last_modified": mtime,
        }

    def load_python_command(
        self, script_path: Path, metadata: Dict[str, Any]
    ) -> Optional[click.Command]:
        """
        Load Python script with Click decorators.

        Args:
            script_path: Path to the Python script
            metadata: Script metadata

        Returns:
            Click command/group or None if loading failed
        """
        name = script_path.stem
        module_name = f"mcli_workflow_{name}"

        try:
            # Load the module directly from file
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            if not spec or not spec.loader:
                logger.error(f"Failed to create spec for {script_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Look for a command or command group in the module
            # Prioritize Groups over Commands
            command_obj = None
            found_commands: List[click.Command] = []

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, click.Group):
                    command_obj = attr
                    break
                elif isinstance(attr, click.Command):
                    found_commands.append(attr)

            if not command_obj and found_commands:
                command_obj = found_commands[0]

            if command_obj:
                logger.debug(f"Loaded Python command: {name}")
                return command_obj
            else:
                logger.warning(f"No Click command found in: {script_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to load Python command {name}: {e}")
            return None

    def load_shell_command(self, script_path: Path, metadata: Dict[str, Any]) -> click.Command:
        """
        Create Click wrapper for shell script.

        Args:
            script_path: Path to the shell script
            metadata: Script metadata

        Returns:
            Click command that executes the shell script
        """
        name = script_path.stem
        description = metadata.get("description", "Shell command")
        shell_type = metadata.get("shell", "bash")

        @click.command(name=name, help=description)
        @click.argument("args", nargs=-1)
        @click.pass_context
        def shell_command(ctx: click.Context, args: Tuple[str, ...]) -> None:
            """Execute shell script command."""
            try:
                # Make script executable if not already
                script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)

                # Execute the shell script directly
                logger.info(f"Executing shell command: {name}")
                process = subprocess.Popen(
                    [str(script_path)] + list(args),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={**os.environ, "MCLI_COMMAND": name},
                )

                register_subprocess(process)

                stdout, stderr = process.communicate()

                if stdout:
                    click.echo(stdout, nl=False)
                if stderr:
                    click.echo(stderr, nl=False, err=True)

                if process.returncode != 0:
                    logger.warning(f"Shell command {name} exited with code {process.returncode}")
                    ctx.exit(process.returncode)

            except Exception as e:
                logger.error(f"Failed to execute shell command {name}: {e}")
                click.echo(f"Error executing shell command: {e}", err=True)
                ctx.exit(1)

        return shell_command

    def load_bun_command(self, script_path: Path, metadata: Dict[str, Any]) -> click.Command:
        """
        Create Click wrapper for JavaScript/TypeScript script using Bun.

        Args:
            script_path: Path to the JS/TS script
            metadata: Script metadata

        Returns:
            Click command that executes the script with Bun
        """
        name = script_path.stem
        description = metadata.get("description", "JavaScript/TypeScript command")
        language = "TypeScript" if script_path.suffix == ".ts" else "JavaScript"

        @click.command(name=name, help=description)
        @click.argument("args", nargs=-1)
        @click.pass_context
        def bun_command(ctx: click.Context, args: Tuple[str, ...]) -> None:
            """Execute JS/TS script with Bun."""
            # Check if bun is available
            bun_path = shutil.which("bun")
            if not bun_path:
                click.echo(
                    f"Error: Bun is required to run {language} scripts. "
                    "Install from https://bun.sh",
                    err=True,
                )
                ctx.exit(1)
                return

            try:
                logger.info(f"Executing {language} command with Bun: {name}")
                process = subprocess.Popen(
                    [bun_path, "run", str(script_path)] + list(args),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={**os.environ, "MCLI_COMMAND": name},
                )

                register_subprocess(process)

                stdout, stderr = process.communicate()

                if stdout:
                    click.echo(stdout, nl=False)
                if stderr:
                    click.echo(stderr, nl=False, err=True)

                if process.returncode != 0:
                    logger.warning(f"Bun command {name} exited with code {process.returncode}")
                    ctx.exit(process.returncode)

            except Exception as e:
                logger.error(f"Failed to execute Bun command {name}: {e}")
                click.echo(f"Error executing {language} command: {e}", err=True)
                ctx.exit(1)

        return bun_command

    def load_ipynb_command(self, script_path: Path, metadata: Dict[str, Any]) -> click.Command:
        """
        Create Click wrapper for Jupyter notebook using papermill.

        Args:
            script_path: Path to the notebook file
            metadata: Script metadata

        Returns:
            Click command that executes the notebook
        """
        name = script_path.stem
        description = metadata.get("description", "Jupyter notebook command")

        @click.command(name=name, help=description)
        @click.option(
            "--param",
            "-p",
            multiple=True,
            type=(str, str),
            help="Parameter key-value pairs (can be used multiple times)",
        )
        @click.option(
            "--output",
            "-o",
            type=click.Path(),
            help="Output notebook path (default: {name}.output.ipynb)",
        )
        @click.option(
            "--no-output",
            is_flag=True,
            help="Don't save output notebook",
        )
        @click.pass_context
        def notebook_command(
            ctx: click.Context,
            param: Tuple[Tuple[str, str], ...],
            output: Optional[str],
            no_output: bool,
        ) -> None:
            """Execute Jupyter notebook with papermill."""
            try:
                import papermill as pm
            except ImportError:
                click.echo(
                    "Error: papermill is required to run Jupyter notebooks. "
                    "Install with: pip install papermill",
                    err=True,
                )
                ctx.exit(1)
                return

            try:
                # Build parameters dict
                parameters = dict(param)

                # Determine output path
                if no_output:
                    output_path = tempfile.mktemp(suffix=".ipynb")
                elif output:
                    output_path = output
                else:
                    output_path = str(script_path.with_suffix(".output.ipynb"))

                logger.info(f"Executing notebook: {name}")
                click.echo(f"Running notebook: {script_path.name}")

                pm.execute_notebook(
                    str(script_path),
                    output_path,
                    parameters=parameters,
                    progress_bar=True,
                )

                if no_output:
                    Path(output_path).unlink(missing_ok=True)
                    click.echo("Notebook executed successfully (output discarded)")
                else:
                    click.echo(f"Output saved to: {output_path}")

            except Exception as e:
                logger.error(f"Failed to execute notebook {name}: {e}")
                click.echo(f"Error executing notebook: {e}", err=True)
                ctx.exit(1)

        return notebook_command

    def load_command(self, script_path: Path) -> Optional[click.Command]:
        """
        Load a script file as a Click command.

        Args:
            script_path: Path to the script file

        Returns:
            Click command or None if loading failed
        """
        language = self.detect_language(script_path)
        metadata = self.extract_metadata(script_path, language)

        if language == "python":
            return self.load_python_command(script_path, metadata)
        elif language == "shell":
            return self.load_shell_command(script_path, metadata)
        elif language in ("javascript", "typescript"):
            return self.load_bun_command(script_path, metadata)
        elif language == "ipynb":
            return self.load_ipynb_command(script_path, metadata)
        else:
            logger.warning(f"Unsupported language '{language}' for {script_path}")
            return None

    def register_all_commands(self, target_group: click.Group) -> int:
        """
        Discover and register all script commands with a Click group.

        Args:
            target_group: Click group to register commands with

        Returns:
            Number of successfully registered commands
        """
        scripts = self.discover_scripts()
        registered = 0

        for script_path in scripts:
            try:
                command = self.load_command(script_path)
                if command:
                    name = script_path.stem
                    target_group.add_command(command, name=name)
                    self.loaded_commands[name] = command
                    registered += 1
                    logger.debug(f"Registered script command: {name}")
            except Exception as e:
                logger.error(f"Failed to register {script_path}: {e}")

        if registered:
            logger.info(f"Registered {registered} script command(s)")

        return registered

    def generate_lockfile(self) -> Dict[str, Any]:
        """
        Generate lockfile data for all scripts.

        Returns:
            Dictionary containing lockfile data with v2 schema
        """
        scripts = self.discover_scripts()

        lockfile_data = {
            "version": "2.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "commands": {},
        }

        for script_path in scripts:
            name = script_path.stem
            info = self.get_script_info(script_path)
            lockfile_data["commands"][name] = info

        return lockfile_data

    def save_lockfile(self) -> bool:
        """
        Save lockfile to disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            lockfile_data = self.generate_lockfile()
            with open(self.lockfile_path, "w") as f:
                json.dump(lockfile_data, f, indent=2)
            logger.info(f"Saved lockfile: {self.lockfile_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save lockfile: {e}")
            return False

    def load_lockfile(self) -> Optional[Dict[str, Any]]:
        """
        Load lockfile from disk.

        Returns:
            Lockfile data or None if not found/invalid
        """
        if not self.lockfile_path.exists():
            return None

        try:
            with open(self.lockfile_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load lockfile: {e}")
            return None

    def verify_lockfile(self) -> Dict[str, Any]:
        """
        Verify scripts match the lockfile.

        Returns:
            Dictionary with verification results:
            - valid: bool - True if all scripts match
            - missing: list - Scripts in lockfile but not found
            - extra: list - Scripts on disk but not in lockfile
            - hash_mismatch: list - Scripts with different content hash
            - version_mismatch: list - Scripts with different version
        """
        result = {
            "valid": True,
            "missing": [],
            "extra": [],
            "hash_mismatch": [],
            "version_mismatch": [],
        }

        lockfile = self.load_lockfile()
        if not lockfile:
            result["valid"] = False
            return result

        locked_commands = lockfile.get("commands", {})
        current_scripts = {p.stem: p for p in self.discover_scripts()}

        # Check for missing scripts (in lockfile but not on disk)
        for name in locked_commands:
            if name not in current_scripts:
                result["missing"].append(name)
                result["valid"] = False

        # Check for extra scripts (on disk but not in lockfile)
        for name in current_scripts:
            if name not in locked_commands:
                result["extra"].append(name)
                result["valid"] = False

        # Check hash and version for existing scripts
        for name, script_path in current_scripts.items():
            if name not in locked_commands:
                continue

            locked = locked_commands[name]
            current_hash = self.calculate_hash(script_path)
            language = self.detect_language(script_path)
            current_metadata = self.extract_metadata(script_path, language)

            if current_hash != locked.get("content_hash"):
                result["hash_mismatch"].append(name)
                result["valid"] = False

            if current_metadata.get("version") != locked.get("version"):
                result["version_mismatch"].append(name)
                # Version mismatch alone doesn't invalidate (hash is primary)

        return result


def get_script_loader(global_mode: bool = False) -> ScriptLoader:
    """
    Get a ScriptLoader instance for the appropriate directory.

    Args:
        global_mode: If True, use global workflows directory

    Returns:
        ScriptLoader instance
    """
    from mcli.lib.paths import get_custom_commands_dir

    workflows_dir = get_custom_commands_dir(global_mode=global_mode)
    return ScriptLoader(workflows_dir)
