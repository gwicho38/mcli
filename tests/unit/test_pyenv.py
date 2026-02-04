"""
Unit tests for mcli.lib.pyenv module.

Tests Python virtual environment management for workflow execution.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestVenvManager:
    """Test suite for VenvManager class."""

    def test_find_local_venv_with_dot_venv(self):
        """Test finding .venv directory."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            venv_dir = workspace / ".venv"
            venv_dir.mkdir()

            # Create a valid venv structure
            if sys.platform == "win32":
                bin_dir = venv_dir / "Scripts"
                python_name = "python.exe"
            else:
                bin_dir = venv_dir / "bin"
                python_name = "python"

            bin_dir.mkdir()
            (bin_dir / python_name).touch()

            manager = VenvManager()
            result = manager.find_local_venv(workspace)

            assert result == venv_dir

    def test_find_local_venv_with_venv(self):
        """Test finding venv directory."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            venv_dir = workspace / "venv"
            venv_dir.mkdir()

            # Create a valid venv structure
            if sys.platform == "win32":
                bin_dir = venv_dir / "Scripts"
                python_name = "python.exe"
            else:
                bin_dir = venv_dir / "bin"
                python_name = "python"

            bin_dir.mkdir()
            (bin_dir / python_name).touch()

            manager = VenvManager()
            result = manager.find_local_venv(workspace)

            assert result == venv_dir

    def test_find_local_venv_none_found(self):
        """Test when no venv is found."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            manager = VenvManager()
            result = manager.find_local_venv(workspace)

            assert result is None

    def test_find_local_venv_invalid_venv_structure(self):
        """Test that invalid venv structure is not detected."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            venv_dir = workspace / ".venv"
            venv_dir.mkdir()
            # No bin/python - invalid structure

            manager = VenvManager()
            result = manager.find_local_venv(workspace)

            assert result is None

    def test_get_global_venv_path(self):
        """Test global venv path resolution."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mcli_home = Path(tmpdir) / "mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(mcli_home)}):
                manager = VenvManager()
                result = manager.get_global_venv_path()

                assert result == mcli_home / "venv"

    def test_get_python_from_venv_unix(self):
        """Test getting Python path from venv on Unix."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"

            manager = VenvManager()
            manager._is_windows = False
            result = manager.get_python_from_venv(venv_path)

            assert result == venv_path / "bin" / "python"

    def test_get_python_from_venv_windows(self):
        """Test getting Python path from venv on Windows."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"

            manager = VenvManager()
            manager._is_windows = True
            result = manager.get_python_from_venv(venv_path)

            assert result == venv_path / "Scripts" / "python.exe"

    def test_is_uv_available(self):
        """Test uv availability check."""
        from mcli.lib.pyenv import VenvManager

        # This test just verifies the method runs without error
        # The actual result depends on whether uv is installed
        result = VenvManager.is_uv_available()
        assert isinstance(result, bool)

    def test_get_venv_env_vars(self):
        """Test environment variables for venv activation."""
        from mcli.lib.pyenv import VenvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            venv_path.mkdir()

            manager = VenvManager()
            manager._is_windows = False
            result = manager.get_venv_env_vars(venv_path)

            assert result["VIRTUAL_ENV"] == str(venv_path)
            assert str(venv_path / "bin") in result["PATH"]
            assert "PYTHONHOME" not in result


class TestDependencyChecker:
    """Test suite for DependencyChecker class."""

    def test_parse_requires_simple(self):
        """Test parsing simple requirements."""
        from mcli.lib.pyenv import DependencyChecker

        checker = DependencyChecker(Path(sys.executable))
        result = checker.parse_requires(["pandas", "numpy"])

        assert result == ["pandas", "numpy"]

    def test_parse_requires_comma_separated(self):
        """Test parsing comma-separated requirements."""
        from mcli.lib.pyenv import DependencyChecker

        checker = DependencyChecker(Path(sys.executable))
        result = checker.parse_requires(["pandas, numpy", "requests"])

        assert result == ["pandas", "numpy", "requests"]

    def test_parse_requires_with_whitespace(self):
        """Test parsing requirements with extra whitespace."""
        from mcli.lib.pyenv import DependencyChecker

        checker = DependencyChecker(Path(sys.executable))
        result = checker.parse_requires(["  pandas  ", "  numpy,  requests  "])

        assert result == ["pandas", "numpy", "requests"]

    def test_extract_package_name(self):
        """Test extracting package name from spec."""
        from mcli.lib.pyenv import DependencyChecker

        checker = DependencyChecker(Path(sys.executable))

        assert checker._extract_package_name("pandas") == "pandas"
        assert checker._extract_package_name("pandas>=1.0.0") == "pandas"
        assert checker._extract_package_name("numpy==1.21.0") == "numpy"
        assert checker._extract_package_name("scikit-learn>=0.24") == "scikit-learn"

    def test_normalize_package_name(self):
        """Test package name normalization."""
        from mcli.lib.pyenv import DependencyChecker

        checker = DependencyChecker(Path(sys.executable))

        assert checker._normalize_package_name("Pandas") == "pandas"
        assert checker._normalize_package_name("scikit_learn") == "scikit-learn"
        assert checker._normalize_package_name("scikit-learn") == "scikit-learn"
        assert checker._normalize_package_name("NUMPY") == "numpy"

    def test_check_version_constraint_exact(self):
        """Test exact version constraint checking."""
        from mcli.lib.pyenv import DependencyChecker

        checker = DependencyChecker(Path(sys.executable))

        assert checker._check_version_constraint("pandas==1.0.0", "1.0.0") is True
        assert checker._check_version_constraint("pandas==1.0.0", "2.0.0") is False

    def test_check_version_constraint_other(self):
        """Test non-exact version constraints (should pass if installed)."""
        from mcli.lib.pyenv import DependencyChecker

        checker = DependencyChecker(Path(sys.executable))

        # Non-exact constraints should return True (defer to pip)
        assert checker._check_version_constraint("pandas>=1.0.0", "1.5.0") is True
        assert checker._check_version_constraint("pandas", "1.0.0") is True


class TestPyEnvManager:
    """Test suite for PyEnvManager class."""

    def test_resolve_environment_local_venv(self):
        """Test resolving environment with local venv."""
        from mcli.lib.pyenv import PyEnvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            venv_dir = workspace / ".venv"
            venv_dir.mkdir()

            # Create valid venv structure
            if sys.platform == "win32":
                bin_dir = venv_dir / "Scripts"
                python_name = "python.exe"
            else:
                bin_dir = venv_dir / "bin"
                python_name = "python"

            bin_dir.mkdir()
            (bin_dir / python_name).touch()

            manager = PyEnvManager(workspace_dir=workspace)
            venv_path, source = manager.resolve_environment()

            assert source == "local"
            assert venv_path == venv_dir

    def test_resolve_environment_global_fallback(self):
        """Test resolving environment falls back to global."""
        from mcli.lib.pyenv import PyEnvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            mcli_home = Path(tmpdir) / "mcli_home"

            # Clear any override env vars
            env = os.environ.copy()
            env.pop("MCLI_VENV_PATH", None)
            env.pop("MCLI_USE_SYSTEM_PYTHON", None)
            env["MCLI_HOME"] = str(mcli_home)

            with patch.dict(os.environ, env, clear=True):
                manager = PyEnvManager(workspace_dir=workspace)
                venv_path, source = manager.resolve_environment()

                assert source == "global"
                assert venv_path == mcli_home / "venv"

    def test_resolve_environment_system_python(self):
        """Test resolving environment with system Python override."""
        from mcli.lib.pyenv import PyEnvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            with patch.dict(os.environ, {"MCLI_USE_SYSTEM_PYTHON": "true"}):
                manager = PyEnvManager(workspace_dir=workspace)
                venv_path, source = manager.resolve_environment()

                assert source == "system"
                assert venv_path is None

    def test_resolve_environment_override(self):
        """Test resolving environment with explicit override."""
        from mcli.lib.pyenv import PyEnvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            override_venv = Path(tmpdir) / "override_venv"
            override_venv.mkdir()

            with patch.dict(os.environ, {"MCLI_VENV_PATH": str(override_venv)}):
                manager = PyEnvManager(workspace_dir=workspace)
                venv_path, source = manager.resolve_environment()

                assert source == "override"
                assert venv_path == override_venv

    def test_get_python_executable_system(self):
        """Test getting Python executable when using system Python."""
        from mcli.lib.pyenv import PyEnvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            with patch.dict(os.environ, {"MCLI_USE_SYSTEM_PYTHON": "true"}):
                manager = PyEnvManager(workspace_dir=workspace)
                result = manager.get_python_executable()

                assert result == Path(sys.executable)

    def test_get_status(self):
        """Test getting environment status."""
        from mcli.lib.pyenv import PyEnvManager

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            with patch.dict(os.environ, {"MCLI_USE_SYSTEM_PYTHON": "true"}):
                manager = PyEnvManager(workspace_dir=workspace)
                status = manager.get_status()

                assert "source" in status
                assert "python" in status
                assert status["source"] == "system"


class TestPyEnvIntegration:
    """Integration tests for pyenv module."""

    def test_imports_work(self):
        """Test that all public imports work."""
        from mcli.lib.pyenv import DependencyChecker, PyEnvManager, VenvManager

        assert PyEnvManager is not None
        assert VenvManager is not None
        assert DependencyChecker is not None

    def test_constants_available(self):
        """Test that related constants are available."""
        from mcli.lib.constants import EnvVars, VenvMessages, VenvPaths

        assert hasattr(EnvVars, "MCLI_AUTO_INSTALL_DEPS")
        assert hasattr(EnvVars, "MCLI_USE_SYSTEM_PYTHON")
        assert hasattr(EnvVars, "MCLI_VENV_PATH")
        assert hasattr(VenvPaths, "LOCAL_VENV_NAMES")
        assert hasattr(VenvMessages, "MISSING_DEPS")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
