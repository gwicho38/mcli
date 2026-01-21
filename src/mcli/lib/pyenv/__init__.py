"""Python environment management for mcli workflows.

This module provides tools for managing Python virtual environments
and dependencies for workflow script execution.

Usage:
    from mcli.lib.pyenv import PyEnvManager

    # Get the appropriate Python executable
    manager = PyEnvManager()
    python_exe = manager.get_python_executable()

    # Check and install dependencies
    manager.check_and_install_deps(requires=["pandas", "numpy"], script_name="my-script")

    # Execute a script in the venv
    result = manager.execute_in_venv(script_path, args=[])
"""

from .deps import DependencyChecker
from .manager import PyEnvManager
from .venv import VenvManager

__all__ = ["PyEnvManager", "VenvManager", "DependencyChecker"]
