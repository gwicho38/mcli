"""
Makefile-based workflow system for mcli.

This module provides support for exposing Makefile targets as mcli commands:
- Parse Makefile in current directory or .mcli/Makefile
- Extract target names and descriptions
- Create Click commands that invoke `make <target>`

Example:
    Makefile with:
        clean:  ## Remove build artifacts
            rm -rf dist/

    Becomes accessible as:
        mcli run make clean
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from mcli.lib.constants.paths import DirNames
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


def find_makefile(start_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Find a Makefile in the current directory or .mcli directory.

    Search order:
    1. .mcli/Makefile
    2. Makefile in current directory
    3. makefile in current directory

    Args:
        start_dir: Directory to start searching from (default: current directory)

    Returns:
        Path to Makefile if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()

    # Check .mcli/Makefile first
    mcli_makefile = start_dir / DirNames.MCLI / "Makefile"
    if mcli_makefile.exists() and mcli_makefile.is_file():
        logger.debug(f"Found Makefile at: {mcli_makefile}")
        return mcli_makefile

    # Check Makefile in current directory
    makefile = start_dir / "Makefile"
    if makefile.exists() and makefile.is_file():
        logger.debug(f"Found Makefile at: {makefile}")
        return makefile

    # Check lowercase makefile
    makefile_lower = start_dir / "makefile"
    if makefile_lower.exists() and makefile_lower.is_file():
        logger.debug(f"Found Makefile at: {makefile_lower}")
        return makefile_lower

    logger.debug("No Makefile found")
    return None


def parse_makefile_targets(makefile_path: Path) -> dict[str, str]:
    """
    Parse Makefile and extract targets with their descriptions.

    Looks for:
    - Targets with inline comments: `target: ## Description`
    - Targets with comment above: `# Description\\ntarget:`
    - Phony targets: `.PHONY: target`

    Args:
        makefile_path: Path to the Makefile

    Returns:
        Dictionary mapping target names to descriptions
        Example: {"clean": "Remove build artifacts", "build": "Build the project"}
    """
    targets = {}

    try:
        with open(makefile_path, encoding="utf-8") as f:
            lines = f.readlines()

        previous_comment = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                previous_comment = None
                continue

            # Track comments for next target
            if stripped.startswith("#") and not stripped.startswith("##"):
                # Single # is a regular comment that might describe next target
                comment_text = stripped[1:].strip()
                if comment_text and not previous_comment:
                    previous_comment = comment_text
                continue

            # Match target lines: "target:" or "target: dependencies"
            # Also capture inline comments with ##
            target_match = re.match(r"^([a-zA-Z0-9_-]+)\s*:\s*([^#]*)(##\s*(.+))?$", stripped)

            if target_match:
                target_name = target_match.group(1)
                inline_comment = target_match.group(4)

                # Skip special targets
                if target_name in [".PHONY", ".SILENT", ".DEFAULT", ".PRECIOUS", ".INTERMEDIATE"]:
                    previous_comment = None
                    continue

                # Use inline comment if available, otherwise use previous comment
                description = None
                if inline_comment:
                    description = inline_comment.strip()
                elif previous_comment:
                    description = previous_comment
                else:
                    description = f"Run make {target_name}"

                targets[target_name] = description
                previous_comment = None

                logger.debug(f"Found Makefile target: {target_name} - {description}")

    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse Makefile at {makefile_path}: {e}")
        return {}

    return targets


def create_make_command(target_name: str, description: str, makefile_path: Path) -> click.Command:
    """
    Create a Click command that runs a make target.

    Args:
        target_name: Name of the make target
        description: Description of what the target does
        makefile_path: Path to the Makefile

    Returns:
        Click Command object
    """

    @click.command(
        name=target_name, help=description, context_settings={"ignore_unknown_options": True}
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def make_cmd(ctx, args):
        """Execute make target."""
        try:
            # Build make command
            # Use -f to specify Makefile path explicitly
            cmd = ["make", "-f", str(makefile_path), target_name] + list(args)

            logger.debug(f"Executing make command: {' '.join(cmd)}")

            # Change to Makefile's directory for execution
            cwd = makefile_path.parent

            # Execute make
            result = subprocess.run(
                cmd,
                capture_output=False,  # Stream output directly
                text=True,
                cwd=cwd,
            )

            # Exit with make's return code (only if non-zero)
            if result.returncode != 0:
                ctx.exit(result.returncode)

        except FileNotFoundError:
            click.echo("Error: 'make' command not found. Please install GNU Make.", err=True)
            logger.error("make command not found")
            ctx.exit(1)
        except Exception as e:
            click.echo(f"Error executing make {target_name}: {e}", err=True)
            logger.error(f"Failed to execute make {target_name}: {e}")
            ctx.exit(1)

    return make_cmd


def create_makefile_group(makefile_path: Path) -> Optional[click.Group]:
    """
    Create a Click command group for Makefile targets.

    Args:
        makefile_path: Path to the Makefile

    Returns:
        Click Group with make targets as subcommands, or None if no targets found
    """
    targets = parse_makefile_targets(makefile_path)

    if not targets:
        logger.debug(f"No targets found in {makefile_path}")
        return None

    # Create the group
    group = click.Group(
        name="make",
        help=f"Make targets from {makefile_path.name}",
    )

    # Register each target as a subcommand
    for target_name, description in targets.items():
        try:
            cmd = create_make_command(target_name, description, makefile_path)
            group.add_command(cmd)
            logger.debug(f"Registered make target: {target_name}")
        except Exception as e:
            logger.error(f"Failed to register make target {target_name}: {e}")
            continue

    return group


def load_makefile_workflow(workflows_dir: Optional[Path] = None) -> Optional[click.Group]:
    """
    Load Makefile workflow group if a Makefile is found.

    Args:
        workflows_dir: Directory to search for Makefile (default: current directory)

    Returns:
        Click Group for make targets, or None if no Makefile found
    """
    makefile_path = find_makefile(workflows_dir)

    if not makefile_path:
        return None

    return create_makefile_group(makefile_path)
