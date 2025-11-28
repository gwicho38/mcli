"""
Package.json-based workflow system for mcli.

This module provides support for exposing package.json scripts as mcli commands:
- Parse package.json in current directory or .mcli/package.json
- Extract script names and commands
- Create Click commands that invoke `npm run <script>`

Example:
    package.json with:
        {
          "scripts": {
            "test": "jest",
            "build": "webpack"
          }
        }

    Becomes accessible as:
        mcli run npm test
        mcli run npm build
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional

import click

from mcli.lib.constants.paths import DirNames
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


def find_package_json(start_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Find a package.json in the current directory or .mcli directory.

    Search order:
    1. .mcli/package.json
    2. package.json in current directory

    Args:
        start_dir: Directory to start searching from (default: current directory)

    Returns:
        Path to package.json if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()

    # Check .mcli/package.json first
    mcli_package_json = start_dir / DirNames.MCLI / "package.json"
    if mcli_package_json.exists() and mcli_package_json.is_file():
        logger.debug(f"Found package.json at: {mcli_package_json}")
        return mcli_package_json

    # Check package.json in current directory
    package_json = start_dir / "package.json"
    if package_json.exists() and package_json.is_file():
        logger.debug(f"Found package.json at: {package_json}")
        return package_json

    logger.debug("No package.json found")
    return None


def parse_package_json_scripts(package_json_path: Path) -> dict[str, str]:
    """
    Parse package.json and extract scripts.

    Args:
        package_json_path: Path to the package.json file

    Returns:
        Dictionary mapping script names to their commands
        Example: {"test": "jest", "build": "webpack"}
    """
    scripts = {}

    try:
        with open(package_json_path, encoding="utf-8") as f:
            data = json.load(f)

        # Extract scripts section
        if "scripts" in data and isinstance(data["scripts"], dict):
            for script_name, command in data["scripts"].items():
                scripts[script_name] = command
                logger.debug(f"Found npm script: {script_name} -> {command}")

    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse package.json at {package_json_path}: {e}")
        return {}

    return scripts


def create_npm_command(script_name: str, command: str, package_json_path: Path) -> click.Command:
    """
    Create a Click command that runs an npm script.

    Args:
        script_name: Name of the npm script
        command: The actual command that will be run
        package_json_path: Path to the package.json file

    Returns:
        Click Command object
    """

    @click.command(
        name=script_name,
        help=f"Run: {command}",
        context_settings={"ignore_unknown_options": True},
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def npm_cmd(ctx, args):
        """Execute npm script."""
        try:
            # Build npm command
            cmd = ["npm", "run", script_name]
            if args:
                cmd.append("--")
                cmd.extend(list(args))

            logger.debug(f"Executing npm command: {' '.join(cmd)}")

            # Change to package.json's directory for execution
            cwd = package_json_path.parent

            # Execute npm
            result = subprocess.run(
                cmd,
                capture_output=False,  # Stream output directly
                text=True,
                cwd=cwd,
            )

            # Exit with npm's return code (only if non-zero)
            if result.returncode != 0:
                ctx.exit(result.returncode)

        except FileNotFoundError:
            click.echo("Error: 'npm' command not found. Please install Node.js and npm.", err=True)
            logger.error("npm command not found")
            ctx.exit(1)
        except Exception as e:
            click.echo(f"Error executing npm run {script_name}: {e}", err=True)
            logger.error(f"Failed to execute npm run {script_name}: {e}")
            ctx.exit(1)

    return npm_cmd


def create_package_json_group(package_json_path: Path) -> Optional[click.Group]:
    """
    Create a Click command group for package.json scripts.

    Args:
        package_json_path: Path to the package.json file

    Returns:
        Click Group with npm scripts as subcommands, or None if no scripts found
    """
    scripts = parse_package_json_scripts(package_json_path)

    if not scripts:
        logger.debug(f"No scripts found in {package_json_path}")
        return None

    # Create the group
    group = click.Group(
        name="npm",
        help=f"npm scripts from {package_json_path.name}",
    )

    # Register each script as a subcommand
    for script_name, command in scripts.items():
        try:
            cmd = create_npm_command(script_name, command, package_json_path)
            group.add_command(cmd)
            logger.debug(f"Registered npm script: {script_name}")
        except Exception as e:
            logger.error(f"Failed to register npm script {script_name}: {e}")
            continue

    return group


def load_package_json_workflow(workflows_dir: Optional[Path] = None) -> Optional[click.Group]:
    """
    Load package.json workflow group if a package.json is found.

    Args:
        workflows_dir: Directory to search for package.json (default: current directory)

    Returns:
        Click Group for npm scripts, or None if no package.json found
    """
    package_json_path = find_package_json(workflows_dir)

    if not package_json_path:
        return None

    return create_package_json_group(package_json_path)
