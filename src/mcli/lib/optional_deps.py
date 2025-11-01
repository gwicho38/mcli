"""
Utilities for graceful handling of optional dependencies.

This module provides helper functions and decorators to handle optional
dependencies gracefully, with clear error messages when features are unavailable.
"""

import functools
from typing import Any, Callable, Dict, Optional, Tuple

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class OptionalDependency:
    """
    Container for an optional dependency with availability tracking.

    Example:
        >>> ollama = OptionalDependency("ollama")
        >>> if ollama.available:
        ...     client = ollama.module.Client()
    """

    def __init__(
        self,
        module_name: str,
        import_name: Optional[str] = None,
        install_hint: Optional[str] = None,
    ):
        """
        Initialize optional dependency handler.

        Args:
            module_name: Name of the module to import (e.g., "ollama")
            import_name: Alternative import name if different from module_name
            install_hint: Custom installation instruction
        """
        self.module_name = module_name
        self.import_name = import_name or module_name
        self.install_hint = install_hint or f"pip install {module_name}"
        self.module: Optional[Any] = None
        self.available = False
        self.error: Optional[Exception] = None

        self._try_import()

    def _try_import(self):
        """Attempt to import the module."""
        try:
            self.module = __import__(self.import_name)
            self.available = True
            logger.debug(f"Optional dependency '{self.module_name}' is available")
        except ImportError as e:
            self.available = False
            self.error = e
            logger.debug(f"Optional dependency '{self.module_name}' is not available: {e}")

    def require(self, feature_name: Optional[str] = None) -> Any:
        """
        Require the dependency to be available, raising an error if not.

        Args:
            feature_name: Name of the feature requiring this dependency

        Returns:
            The imported module

        Raises:
            ImportError: If the dependency is not available
        """
        if not self.available:
            feature_msg = f" for {feature_name}" if feature_name else ""
            raise ImportError(
                f"'{self.module_name}' is required{feature_msg} but not installed.\n"
                f"Install it with: {self.install_hint}"
            )
        return self.module

    def __getattr__(self, name: str) -> Any:
        """Allow direct attribute access to the module."""
        if not self.available:
            raise ImportError(
                f"Cannot access '{name}' from '{self.module_name}' - module not installed.\n"
                f"Install it with: {self.install_hint}"
            )
        return getattr(self.module, name)


def optional_import(
    module_name: str, import_name: Optional[str] = None, install_hint: Optional[str] = None
) -> Tuple[Optional[Any], bool]:
    """
    Try to import an optional dependency.

    Args:
        module_name: Name of the module to import
        import_name: Alternative import name if different from module_name
        install_hint: Custom installation instruction

    Returns:
        Tuple of (module, available) where module is None if unavailable

    Example:
        >>> ollama, OLLAMA_AVAILABLE = optional_import("ollama")
        >>> if OLLAMA_AVAILABLE:
        ...     client = ollama.Client()
    """
    dep = OptionalDependency(module_name, import_name, install_hint)
    return (dep.module, dep.available)


def require_dependency(
    module_name: str, feature_name: str, install_hint: Optional[str] = None
) -> Any:
    """
    Require a dependency, raising clear error if not available.

    Args:
        module_name: Name of the module to import
        feature_name: Name of the feature requiring this dependency
        install_hint: Custom installation instruction

    Returns:
        The imported module

    Raises:
        ImportError: If the dependency is not available

    Example:
        >>> streamlit = require_dependency("streamlit", "dashboard")
    """
    dep = OptionalDependency(module_name, install_hint=install_hint)
    return dep.require(feature_name)


def requires(*dependencies: str, install_all_hint: Optional[str] = None):
    """
    Decorator to mark a function as requiring specific dependencies.

    Args:
        *dependencies: Module names required by the function
        install_all_hint: Custom installation instruction for all dependencies

    Raises:
        ImportError: If any required dependency is not available

    Example:
        >>> @requires("torch", "transformers")
        ... def train_model():
        ...     import torch
        ...     import transformers
        ...     # training code
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            missing = []
            for dep_name in dependencies:
                dep = OptionalDependency(dep_name)
                if not dep.available:
                    missing.append(dep_name)

            if missing:
                if install_all_hint:
                    hint = install_all_hint
                else:
                    hint = f"pip install {' '.join(missing)}"

                raise ImportError(
                    f"Function '{func.__name__}' requires missing dependencies: {', '.join(missing)}\n"
                    f"Install them with: {hint}"
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Common optional dependencies registry
OPTIONAL_DEPS: Dict[str, OptionalDependency] = {}


def register_optional_dependency(
    module_name: str, import_name: Optional[str] = None, install_hint: Optional[str] = None
) -> OptionalDependency:
    """
    Register and cache an optional dependency.

    Args:
        module_name: Name of the module to import
        import_name: Alternative import name if different from module_name
        install_hint: Custom installation instruction

    Returns:
        OptionalDependency instance
    """
    if module_name not in OPTIONAL_DEPS:
        OPTIONAL_DEPS[module_name] = OptionalDependency(module_name, import_name, install_hint)
    return OPTIONAL_DEPS[module_name]


def check_dependencies(*module_names: str) -> Dict[str, bool]:
    """
    Check availability of multiple dependencies.

    Args:
        *module_names: Module names to check

    Returns:
        Dictionary mapping module names to availability status

    Example:
        >>> status = check_dependencies("torch", "transformers", "streamlit")
        >>> print(status)
        {'torch': True, 'transformers': False, 'streamlit': True}
    """
    return {name: OptionalDependency(name).available for name in module_names}


# Pre-register common optional dependencies
_COMMON_DEPS = {
    "ollama": ("ollama", "pip install ollama"),
    "streamlit": ("streamlit", "pip install streamlit"),
    "torch": ("torch", "pip install torch"),
    "transformers": ("transformers", "pip install transformers"),
    "mlflow": ("mlflow", "pip install mlflow"),
    "plotly": ("plotly", "pip install plotly"),
    "pandas": ("pandas", "pip install pandas"),
    "numpy": ("numpy", "pip install numpy"),
}

for module_name, (import_name, hint) in _COMMON_DEPS.items():
    register_optional_dependency(module_name, import_name, hint)
