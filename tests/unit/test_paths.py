"""
Unit tests for mcli.lib.paths module

Tests path resolution utilities that work in different environments.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPathResolution:
    """Test suite for path resolution utilities"""

    def test_get_mcli_home_default(self):
        """Test get_mcli_home with default ~/.mcli location"""
        from mcli.lib.paths import get_mcli_home

        with patch.dict(os.environ, {}, clear=True):
            # Remove any MCLI_HOME or XDG_DATA_HOME from environment
            result = get_mcli_home()

            assert result == Path.home() / ".mcli"
            assert result.exists()
            assert result.is_dir()

    def test_get_mcli_home_with_mcli_home_env(self):
        """Test get_mcli_home with MCLI_HOME environment variable"""
        from mcli.lib.paths import get_mcli_home

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_home = Path(tmpdir) / "custom_mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(custom_home)}):
                result = get_mcli_home()

                assert result == custom_home
                assert result.exists()
                assert result.is_dir()

    def test_get_mcli_home_with_xdg_data_home(self):
        """Test get_mcli_home with XDG_DATA_HOME environment variable"""
        from mcli.lib.paths import get_mcli_home

        with tempfile.TemporaryDirectory() as tmpdir:
            xdg_home = Path(tmpdir) / "xdg_data"
            xdg_home.mkdir()

            # Ensure MCLI_HOME is not set
            env = os.environ.copy()
            env.pop("MCLI_HOME", None)
            env["XDG_DATA_HOME"] = str(xdg_home)

            with patch.dict(os.environ, env, clear=True):
                result = get_mcli_home()

                assert result == xdg_home / "mcli"
                assert result.exists()
                assert result.is_dir()

    def test_get_mcli_home_creates_directory(self):
        """Test that get_mcli_home creates the directory if it doesn't exist"""
        from mcli.lib.paths import get_mcli_home

        with tempfile.TemporaryDirectory() as tmpdir:
            new_home = Path(tmpdir) / "new_mcli_home"

            # Ensure directory doesn't exist
            assert not new_home.exists()

            with patch.dict(os.environ, {"MCLI_HOME": str(new_home)}):
                result = get_mcli_home()

                assert result == new_home
                assert result.exists()
                assert result.is_dir()

    def test_get_logs_dir(self):
        """Test get_logs_dir creates and returns logs directory"""
        from mcli.lib.paths import get_logs_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            mcli_home = Path(tmpdir) / "mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(mcli_home)}):
                result = get_logs_dir()

                assert result == mcli_home / "logs"
                assert result.exists()
                assert result.is_dir()

    def test_get_config_dir(self):
        """Test get_config_dir creates and returns config directory"""
        from mcli.lib.paths import get_config_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            mcli_home = Path(tmpdir) / "mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(mcli_home)}):
                result = get_config_dir()

                assert result == mcli_home / "config"
                assert result.exists()
                assert result.is_dir()

    def test_get_data_dir(self):
        """Test get_data_dir creates and returns data directory"""
        from mcli.lib.paths import get_data_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            mcli_home = Path(tmpdir) / "mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(mcli_home)}):
                result = get_data_dir()

                assert result == mcli_home / "data"
                assert result.exists()
                assert result.is_dir()

    def test_get_cache_dir(self):
        """Test get_cache_dir creates and returns cache directory"""
        from mcli.lib.paths import get_cache_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            mcli_home = Path(tmpdir) / "mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(mcli_home)}):
                result = get_cache_dir()

                assert result == mcli_home / "cache"
                assert result.exists()
                assert result.is_dir()

    def test_all_directories_under_same_mcli_home(self):
        """Test that all directories are created under the same mcli_home"""
        from mcli.lib.paths import (
            get_cache_dir,
            get_config_dir,
            get_data_dir,
            get_logs_dir,
            get_mcli_home,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            mcli_home = Path(tmpdir) / "mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(mcli_home)}):
                home = get_mcli_home()
                logs = get_logs_dir()
                config = get_config_dir()
                data = get_data_dir()
                cache = get_cache_dir()

                # All should be subdirectories of mcli_home
                assert logs.parent == home
                assert config.parent == home
                assert data.parent == home
                assert cache.parent == home

                # All should exist
                assert all(d.exists() for d in [home, logs, config, data, cache])

    def test_directories_created_with_parents(self):
        """Test that directories are created with parents=True"""
        from mcli.lib.paths import get_logs_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a deeply nested path
            deep_home = Path(tmpdir) / "deep" / "nested" / "mcli"

            with patch.dict(os.environ, {"MCLI_HOME": str(deep_home)}):
                result = get_logs_dir()

                # All parent directories should be created
                assert result.exists()
                assert result.parent.exists()  # mcli
                assert result.parent.parent.exists()  # nested
                assert result.parent.parent.parent.exists()  # deep

    def test_mcli_home_precedence_order(self):
        """Test that MCLI_HOME takes precedence over XDG_DATA_HOME"""
        from mcli.lib.paths import get_mcli_home

        with tempfile.TemporaryDirectory() as tmpdir:
            mcli_home_path = Path(tmpdir) / "mcli_home"
            xdg_home_path = Path(tmpdir) / "xdg_home"

            with patch.dict(
                os.environ, {"MCLI_HOME": str(mcli_home_path), "XDG_DATA_HOME": str(xdg_home_path)}
            ):
                result = get_mcli_home()

                # MCLI_HOME should take precedence
                assert result == mcli_home_path
                assert result.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
