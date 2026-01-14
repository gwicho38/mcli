"""Dependency checking and installation for mcli workflows.

This module provides functionality for checking and installing Python
dependencies required by workflow scripts.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from mcli.lib.constants import VenvMessages
from mcli.lib.logger import get_logger

logger = get_logger(__name__)


class DependencyChecker:
    """Checks and installs Python dependencies."""

    def __init__(self, python_executable: Path) -> None:
        """Initialize the dependency checker.

        Args:
            python_executable: Path to the Python executable to use.
        """
        self.python_executable = python_executable

    def parse_requires(self, requires: List[str]) -> List[str]:
        """Parse @requires list into normalized package specifications.

        Handles comma-separated values and normalizes package names.

        Args:
            requires: List of requirement strings (may be comma-separated).

        Returns:
            List of normalized package specifications.
        """
        packages = []
        for req in requires:
            # Split by comma if multiple packages in one string
            for part in req.split(","):
                part = part.strip()
                if part:
                    packages.append(part)
        return packages

    def check_installed(self, packages: List[str]) -> Tuple[List[str], List[str]]:
        """Check which packages are installed.

        Args:
            packages: List of package specifications to check.

        Returns:
            Tuple of (installed, missing) package lists.
        """
        installed_packages = self.get_installed_packages()
        installed = []
        missing = []

        for pkg in packages:
            # Extract package name (without version specifier)
            pkg_name = self._extract_package_name(pkg)
            normalized_name = self._normalize_package_name(pkg_name)

            if normalized_name in installed_packages:
                # Check version if specified
                if self._check_version_constraint(pkg, installed_packages.get(normalized_name, "")):
                    installed.append(pkg)
                else:
                    missing.append(pkg)
            else:
                missing.append(pkg)

        return installed, missing

    def install_packages(self, packages: List[str], venv_path: Path) -> bool:
        """Install packages using uv pip install.

        Args:
            packages: List of package specifications to install.
            venv_path: Path to the virtual environment.

        Returns:
            True if installation succeeded.

        Raises:
            RuntimeError: If installation fails.
        """
        if not packages:
            return True

        logger.info(VenvMessages.INSTALLING_DEPS.format(packages=", ".join(packages)))

        try:
            # Use uv pip install with the target venv
            result = subprocess.run(
                ["uv", "pip", "install", "--python", str(self.python_executable)] + packages,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for large packages
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                raise RuntimeError(VenvMessages.DEP_INSTALL_FAILED.format(error=error_msg))

            logger.info(VenvMessages.DEPS_INSTALLED)
            return True

        except subprocess.TimeoutExpired:
            raise RuntimeError(VenvMessages.DEP_INSTALL_FAILED.format(error="Installation timeout"))
        except FileNotFoundError:
            raise RuntimeError(VenvMessages.UV_NOT_INSTALLED)

    def get_installed_packages(self) -> Dict[str, str]:
        """Get dictionary of installed packages and their versions.

        Returns:
            Dict mapping normalized package names to versions.
        """
        try:
            result = subprocess.run(
                [str(self.python_executable), "-m", "pip", "list", "--format=freeze"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning(f"Failed to list packages: {result.stderr}")
                return {}

            packages = {}
            for line in result.stdout.strip().split("\n"):
                if "==" in line:
                    name, version = line.split("==", 1)
                    packages[self._normalize_package_name(name)] = version

            return packages

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to get installed packages: {e}")
            return {}

    def _extract_package_name(self, pkg_spec: str) -> str:
        """Extract package name from a specification.

        Args:
            pkg_spec: Package specification (e.g., "pandas>=1.0.0").

        Returns:
            Package name without version specifier.
        """
        # Handle various version specifier patterns
        match = re.match(r"^([a-zA-Z0-9_-]+)", pkg_spec)
        return match.group(1) if match else pkg_spec

    def _normalize_package_name(self, name: str) -> str:
        """Normalize a package name for comparison.

        Follows PEP 503 normalization rules.

        Args:
            name: Package name to normalize.

        Returns:
            Normalized package name (lowercase, hyphens/underscores normalized).
        """
        return re.sub(r"[-_.]+", "-", name).lower()

    def _check_version_constraint(self, pkg_spec: str, installed_version: str) -> bool:
        """Check if installed version satisfies the constraint.

        For simplicity, this only checks exact version matches with ==.
        Other version specifiers (>=, <=, etc.) are considered satisfied
        if the package is installed (actual version comparison is left to pip).

        Args:
            pkg_spec: Package specification with possible version constraint.
            installed_version: Currently installed version.

        Returns:
            True if the constraint is satisfied or no strict check is needed.
        """
        if "==" in pkg_spec:
            _, required_version = pkg_spec.split("==", 1)
            return installed_version == required_version

        # For other specifiers, assume satisfied if installed
        # (uv pip install will handle upgrades if needed)
        return True
