"""Python environment manager for mcli workflows.

This module provides the main orchestrator for Python environment management,
including environment detection, dependency checking, and script execution.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from mcli.lib.constants import EnvVars, VenvMessages
from mcli.lib.logger import get_logger

from .deps import DependencyChecker
from .venv import VenvManager

logger = get_logger(__name__)


class PyEnvManager:
    """Manages Python environments for workflow execution.

    This class orchestrates:
    - Detection of local vs global virtual environments
    - Dependency checking and installation
    - Script execution in the appropriate environment
    """

    def __init__(self, workspace_dir: Optional[Path] = None) -> None:
        """Initialize the environment manager.

        Args:
            workspace_dir: Optional workspace directory for local venv detection.
                          Defaults to current working directory.
        """
        self.workspace_dir = workspace_dir or Path.cwd()
        self.venv_manager = VenvManager()
        self._resolved_venv: Optional[Path] = None
        self._resolved_source: Optional[str] = None

    def resolve_environment(self) -> Tuple[Optional[Path], str]:
        """Resolve which virtual environment to use.

        Resolution order:
        1. MCLI_VENV_PATH environment variable (explicit override)
        2. MCLI_USE_SYSTEM_PYTHON env var (skip venv detection)
        3. Local venv (.venv or venv in workspace)
        4. Global MCLI venv (~/.mcli/venv/)

        Returns:
            Tuple of (venv_path, source) where source is one of:
            'override', 'system', 'local', 'global'
        """
        if self._resolved_venv is not None:
            return self._resolved_venv, self._resolved_source or "cached"

        # Check for explicit override
        override_path = os.getenv(EnvVars.MCLI_VENV_PATH)
        if override_path:
            venv_path = Path(override_path)
            if venv_path.is_dir():
                self._resolved_venv = venv_path
                self._resolved_source = "override"
                logger.debug(f"Using override venv: {venv_path}")
                return venv_path, "override"

        # Check if user wants system Python
        if os.getenv(EnvVars.MCLI_USE_SYSTEM_PYTHON, "").lower() in ("true", "1", "yes"):
            self._resolved_venv = None
            self._resolved_source = "system"
            logger.debug("Using system Python (MCLI_USE_SYSTEM_PYTHON set)")
            return None, "system"

        # Try to find local venv
        local_venv = self.venv_manager.find_local_venv(self.workspace_dir)
        if local_venv:
            self._resolved_venv = local_venv
            self._resolved_source = "local"
            logger.debug(f"Using local venv: {local_venv}")
            return local_venv, "local"

        # Fall back to global venv
        global_venv = self.venv_manager.get_global_venv_path()
        self._resolved_venv = global_venv
        self._resolved_source = "global"
        logger.debug(f"Using global venv: {global_venv}")
        return global_venv, "global"

    def get_python_executable(self) -> Path:
        """Get the Python executable for the resolved environment.

        Returns:
            Path to the Python executable.
        """
        venv_path, source = self.resolve_environment()

        if source == "system" or venv_path is None:
            return Path(sys.executable)

        return self.venv_manager.get_python_from_venv(venv_path)

    def check_and_install_deps(
        self,
        requires: List[str],
        script_name: str,
        auto_install: bool = False,
    ) -> bool:
        """Check dependencies and prompt for installation if missing.

        Args:
            requires: List of required packages from @requires metadata.
            script_name: Name of the script (for display).
            auto_install: If True, install without prompting.

        Returns:
            True if all dependencies are satisfied or installed.
        """
        if not requires:
            logger.debug("No dependencies specified")
            return True

        venv_path, source = self.resolve_environment()

        # Ensure the venv exists (create global venv if needed)
        if source == "global" and venv_path:
            venv_path = self.venv_manager.ensure_global_venv()

        python_exe = self.get_python_executable()
        checker = DependencyChecker(python_exe)

        # Parse and check dependencies
        packages = checker.parse_requires(requires)
        logger.debug(VenvMessages.CHECKING_DEPS.format(script=script_name))

        installed, missing = checker.check_installed(packages)

        if not missing:
            logger.debug(VenvMessages.DEPS_SATISFIED)
            return True

        # Report missing dependencies
        missing_str = ", ".join(missing)
        click.echo(VenvMessages.MISSING_DEPS.format(packages=missing_str))

        # Check for auto-install environment variable
        env_auto_install = os.getenv(EnvVars.MCLI_AUTO_INSTALL_DEPS, "").lower() in (
            "true",
            "1",
            "yes",
        )

        if auto_install or env_auto_install:
            should_install = True
        else:
            # Prompt user
            venv_display = str(venv_path) if venv_path else "system"
            prompt_msg = VenvMessages.PROMPT_INSTALL_DEPS.format(
                venv=venv_display,
                packages=missing_str,
            )
            should_install = click.confirm(prompt_msg, default=True)

        if should_install:
            try:
                checker.install_packages(missing, venv_path)
                return True
            except RuntimeError as e:
                click.echo(str(e), err=True)
                return False

        return False

    def execute_in_venv(
        self,
        script_path: Path,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """Execute a Python script in the resolved virtual environment.

        Args:
            script_path: Path to the Python script.
            args: Command line arguments for the script.
            env: Additional environment variables.

        Returns:
            CompletedProcess with the execution results.
        """
        venv_path, source = self.resolve_environment()

        # Build execution environment
        if venv_path and source != "system":
            exec_env = self.venv_manager.get_venv_env_vars(venv_path)
        else:
            exec_env = os.environ.copy()

        # Merge additional env vars
        if env:
            exec_env.update(env)

        python_exe = self.get_python_executable()

        return subprocess.run(
            [str(python_exe), str(script_path)] + args,
            env=exec_env,
            capture_output=True,
            text=True,
        )

    def get_status(self) -> Dict[str, str]:
        """Get the current environment status for display.

        Returns:
            Dictionary with status information.
        """
        venv_path, source = self.resolve_environment()

        status = {
            "source": source,
            "python": str(self.get_python_executable()),
        }

        if venv_path:
            status["venv_path"] = str(venv_path)
            status["venv_exists"] = str(venv_path.exists())

        return status
