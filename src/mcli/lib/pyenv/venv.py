"""Virtual environment management for mcli workflows.

This module provides functionality for detecting, creating, and managing
Python virtual environments for workflow script execution.
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from mcli.lib.constants import DirNames, VenvMessages, VenvPaths
from mcli.lib.logger import get_logger
from mcli.lib.paths import get_mcli_home

logger = get_logger(__name__)


class VenvManager:
    """Manages virtual environment detection and creation."""

    def __init__(self) -> None:
        """Initialize the venv manager."""
        self._is_windows = platform.system() == "Windows"

    def find_local_venv(self, workspace_dir: Optional[Path] = None) -> Optional[Path]:
        """Find a local venv in the workspace directory.

        Searches for .venv and venv directories in the given workspace.

        Args:
            workspace_dir: Directory to search in. Defaults to current directory.

        Returns:
            Path to the venv if found, None otherwise.
        """
        if workspace_dir is None:
            workspace_dir = Path.cwd()

        for venv_name in VenvPaths.LOCAL_VENV_NAMES:
            venv_path = workspace_dir / venv_name
            if venv_path.is_dir() and self._is_valid_venv(venv_path):
                logger.debug(f"Found local venv at {venv_path}")
                return venv_path

        return None

    def get_global_venv_path(self) -> Path:
        """Get the path to the global MCLI venv.

        Returns:
            Path to ~/.mcli/venv/
        """
        return get_mcli_home() / DirNames.GLOBAL_VENV

    def ensure_global_venv(self) -> Path:
        """Ensure the global MCLI venv exists, creating it if necessary.

        Returns:
            Path to the global venv.

        Raises:
            RuntimeError: If venv creation fails.
        """
        venv_path = self.get_global_venv_path()

        if venv_path.is_dir() and self._is_valid_venv(venv_path):
            logger.debug(f"Global venv already exists at {venv_path}")
            return venv_path

        logger.info(VenvMessages.CREATING_GLOBAL_VENV.format(path=venv_path))
        self.create_venv(venv_path)
        logger.info(VenvMessages.GLOBAL_VENV_CREATED.format(path=venv_path))

        return venv_path

    def create_venv(self, venv_path: Path) -> bool:
        """Create a new virtual environment using uv.

        Args:
            venv_path: Path where the venv should be created.

        Returns:
            True if successful.

        Raises:
            RuntimeError: If uv is not available or venv creation fails.
        """
        if not self.is_uv_available():
            raise RuntimeError(VenvMessages.UV_NOT_INSTALLED)

        # Ensure parent directory exists
        venv_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                ["uv", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                raise RuntimeError(VenvMessages.VENV_CREATE_FAILED.format(error=error_msg))
            return True
        except subprocess.TimeoutExpired:
            raise RuntimeError(VenvMessages.VENV_CREATE_FAILED.format(error="Timeout"))
        except FileNotFoundError:
            raise RuntimeError(VenvMessages.UV_NOT_INSTALLED)

    def get_python_from_venv(self, venv_path: Path) -> Path:
        """Get the Python executable path from a venv.

        Args:
            venv_path: Path to the virtual environment.

        Returns:
            Path to the Python executable.
        """
        if self._is_windows:
            bin_dir = VenvPaths.BIN_DIR_WINDOWS
            python_name = VenvPaths.PYTHON_WINDOWS
        else:
            bin_dir = VenvPaths.BIN_DIR_UNIX
            python_name = VenvPaths.PYTHON_UNIX

        return venv_path / bin_dir / python_name

    def _is_valid_venv(self, venv_path: Path) -> bool:
        """Check if a directory is a valid virtual environment.

        Args:
            venv_path: Path to check.

        Returns:
            True if the directory contains a valid venv structure.
        """
        python_path = self.get_python_from_venv(venv_path)
        return python_path.is_file()

    @staticmethod
    def is_uv_available() -> bool:
        """Check if uv is installed and available.

        Returns:
            True if uv is available on the system.
        """
        return shutil.which("uv") is not None

    def get_venv_env_vars(self, venv_path: Path) -> dict:
        """Get environment variables for activating a venv.

        Args:
            venv_path: Path to the virtual environment.

        Returns:
            Dictionary of environment variables to set.
        """
        if self._is_windows:
            bin_dir = venv_path / VenvPaths.BIN_DIR_WINDOWS
        else:
            bin_dir = venv_path / VenvPaths.BIN_DIR_UNIX

        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(venv_path)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

        # Remove PYTHONHOME if set (it can interfere with venv)
        env.pop("PYTHONHOME", None)

        return env
