"""
Unit tests for mcli.lib.toml module
"""

import os
import tempfile
from pathlib import Path

import pytest


class TestTomlUtils:
    """Test suite for TOML utilities"""

    def test_read_from_toml_success(self):
        """Test reading from a valid TOML file"""
        from mcli.lib.toml.toml import read_from_toml

        toml_content = """
[database]
host = "localhost"
port = 5432

[api]
timeout = 30
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "database")
            assert result is not None
            assert result["host"] == "localhost"
            assert result["port"] == 5432
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_simple_key(self):
        """Test reading simple key-value pair"""
        from mcli.lib.toml.toml import read_from_toml

        toml_content = """
name = "mcli"
version = "1.0.0"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "name")
            assert result == "mcli"
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_nested_section(self):
        """Test reading nested TOML section"""
        from mcli.lib.toml.toml import read_from_toml

        toml_content = """
[server]
host = "localhost"

[server.ssl]
enabled = true
cert_path = "/path/to/cert"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "server")
            assert result["host"] == "localhost"
            assert result["ssl"]["enabled"] is True
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_missing_key(self):
        """Test reading non-existent key returns None"""
        from mcli.lib.toml.toml import read_from_toml

        toml_content = """
[section]
key = "value"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "nonexistent")
            assert result is None
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_file_not_found(self):
        """Test reading from non-existent file raises error"""
        from mcli.lib.toml.toml import read_from_toml

        with pytest.raises(FileNotFoundError):
            read_from_toml("/nonexistent/path/to/file.toml", "key")

    def test_read_from_toml_invalid_syntax(self):
        """Test reading invalid TOML raises error"""
        from mcli.lib.toml.toml import read_from_toml

        invalid_toml = """
[section
key = "missing closing bracket"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(invalid_toml)
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # TOMLDecodeError
                read_from_toml(temp_path, "section")
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_array_values(self):
        """Test reading TOML with array values"""
        from mcli.lib.toml.toml import read_from_toml

        toml_content = """
[features]
supported = ["async", "video", "ml"]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "features")
            assert result["supported"] == ["async", "video", "ml"]
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_numeric_values(self):
        """Test reading various numeric types"""
        from mcli.lib.toml.toml import read_from_toml

        toml_content = """
[numbers]
integer = 42
float = 3.14
negative = -10
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "numbers")
            assert result["integer"] == 42
            assert result["float"] == 3.14
            assert result["negative"] == -10
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_boolean_values(self):
        """Test reading boolean values"""
        from mcli.lib.toml.toml import read_from_toml

        toml_content = """
[flags]
enabled = true
disabled = false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "flags")
            assert result["enabled"] is True
            assert result["disabled"] is False
        finally:
            os.unlink(temp_path)

    def test_read_from_toml_empty_file(self):
        """Test reading from empty TOML file"""
        from mcli.lib.toml.toml import read_from_toml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            result = read_from_toml(temp_path, "anykey")
            assert result is None
        finally:
            os.unlink(temp_path)
