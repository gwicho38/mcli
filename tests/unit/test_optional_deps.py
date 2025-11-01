"""Tests for optional dependency handling utilities."""

import pytest

from mcli.lib.optional_deps import (
    OptionalDependency,
    check_dependencies,
    optional_import,
    register_optional_dependency,
    require_dependency,
    requires,
)


def test_optional_dependency_available():
    """Test OptionalDependency with an available module."""
    # 'os' is always available in Python
    dep = OptionalDependency("os")
    assert dep.available is True
    assert dep.module is not None
    assert dep.error is None


def test_optional_dependency_unavailable():
    """Test OptionalDependency with an unavailable module."""
    dep = OptionalDependency("nonexistent_module_12345")
    assert dep.available is False
    assert dep.module is None
    assert dep.error is not None


def test_optional_dependency_require_available():
    """Test require() with an available dependency."""
    dep = OptionalDependency("os")
    module = dep.require("testing")
    assert module is not None


def test_optional_dependency_require_unavailable():
    """Test require() raises ImportError for unavailable dependency."""
    dep = OptionalDependency("nonexistent_module_12345")
    with pytest.raises(ImportError) as exc_info:
        dep.require("testing")

    assert "nonexistent_module_12345" in str(exc_info.value)
    assert "testing" in str(exc_info.value)
    assert "pip install" in str(exc_info.value)


def test_optional_dependency_getattr_available():
    """Test attribute access on available module."""
    dep = OptionalDependency("os")
    # Should be able to access os.path
    path = dep.path
    assert path is not None


def test_optional_dependency_getattr_unavailable():
    """Test attribute access raises ImportError for unavailable module."""
    dep = OptionalDependency("nonexistent_module_12345")
    with pytest.raises(ImportError) as exc_info:
        _ = dep.some_attribute

    assert "nonexistent_module_12345" in str(exc_info.value)


def test_optional_dependency_custom_install_hint():
    """Test custom installation hint."""
    dep = OptionalDependency("nonexistent_module", install_hint="conda install nonexistent_module")

    with pytest.raises(ImportError) as exc_info:
        dep.require()

    assert "conda install" in str(exc_info.value)


def test_optional_import_available():
    """Test optional_import with available module."""
    module, available = optional_import("os")
    assert available is True
    assert module is not None


def test_optional_import_unavailable():
    """Test optional_import with unavailable module."""
    module, available = optional_import("nonexistent_module_12345")
    assert available is False
    assert module is None


def test_optional_import_with_custom_hint():
    """Test optional_import with custom installation hint."""
    module, available = optional_import(
        "nonexistent_module", install_hint="pip install nonexistent[extra]"
    )
    assert available is False


def test_require_dependency_available():
    """Test require_dependency with available module."""
    module = require_dependency("os", "testing")
    assert module is not None


def test_require_dependency_unavailable():
    """Test require_dependency raises ImportError for unavailable module."""
    with pytest.raises(ImportError) as exc_info:
        require_dependency("nonexistent_module_12345", "testing feature")

    assert "nonexistent_module_12345" in str(exc_info.value)
    assert "testing feature" in str(exc_info.value)


def test_requires_decorator_all_available():
    """Test @requires decorator when all dependencies are available."""

    @requires("os", "sys")
    def func_with_deps():
        return "success"

    result = func_with_deps()
    assert result == "success"


def test_requires_decorator_missing_dependency():
    """Test @requires decorator raises ImportError for missing dependency."""

    @requires("os", "nonexistent_module_12345")
    def func_with_missing_dep():
        return "should not execute"

    with pytest.raises(ImportError) as exc_info:
        func_with_missing_dep()

    assert "nonexistent_module_12345" in str(exc_info.value)
    assert "func_with_missing_dep" in str(exc_info.value)


def test_requires_decorator_custom_install_hint():
    """Test @requires decorator with custom install hint."""

    @requires("nonexistent_module", install_all_hint="pip install special-package")
    def func_with_custom_hint():
        return "should not execute"

    with pytest.raises(ImportError) as exc_info:
        func_with_custom_hint()

    assert "pip install special-package" in str(exc_info.value)


def test_register_optional_dependency():
    """Test registering an optional dependency."""
    dep = register_optional_dependency("os", install_hint="always available")
    assert dep.available is True

    # Should return cached instance on second call
    dep2 = register_optional_dependency("os")
    assert dep is dep2


def test_check_dependencies():
    """Test checking multiple dependencies."""
    status = check_dependencies("os", "sys", "nonexistent_module_12345")

    assert status["os"] is True
    assert status["sys"] is True
    assert status["nonexistent_module_12345"] is False


def test_check_dependencies_empty():
    """Test checking no dependencies."""
    status = check_dependencies()
    assert status == {}


def test_optional_dependency_different_import_name():
    """Test OptionalDependency with different import name."""
    # Example: package name might be different from import name
    dep = OptionalDependency("pillow", import_name="PIL", install_hint="pip install Pillow")

    # This might be available or not depending on environment
    if dep.available:
        assert dep.module is not None
    else:
        with pytest.raises(ImportError) as exc_info:
            dep.require()
        assert "pillow" in str(exc_info.value)
        assert "pip install Pillow" in str(exc_info.value)


def test_requires_decorator_preserves_function_metadata():
    """Test that @requires decorator preserves function metadata."""

    @requires("os")
    def documented_function():
        """This function has documentation."""
        return 42

    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ == "This function has documentation."


def test_optional_dependency_module_with_submodule():
    """Test accessing submodules through OptionalDependency."""
    dep = OptionalDependency("os")
    # Should be able to access submodule
    path_module = dep.path
    assert path_module is not None
    # And call functions on it
    assert callable(path_module.exists)
