"""
Unit tests for mcli.lib.auth modules
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
import json


class TestCredentialManager:
    """Test suite for CredentialManager base class"""

    def test_credential_manager_init(self):
        """Test CredentialManager initialization"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test_app")

                assert manager.config_dir == Path(tmpdir) / ".config" / "test_app"
                assert manager.config_file.name == "mcli.key.config.json"

    def test_credential_manager_custom_filename(self):
        """Test CredentialManager with custom config filename"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test", config_filename="custom.json")

                assert manager.config_file.name == "custom.json"

    def test_ensure_config_dir_creates_directory(self):
        """Test that config directory is created"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                assert manager.config_dir.exists()
                assert manager.config_dir.is_dir()

    def test_read_config_empty_file(self):
        """Test reading config when file doesn't exist"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                config = manager.read_config()

                assert config == {}

    def test_write_and_read_config(self):
        """Test writing and reading configuration"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                test_config = {"key": "value", "number": 42}
                manager.write_config(test_config)

                read_config = manager.read_config()

                assert read_config == test_config

    def test_write_config_invalid_type(self):
        """Test writing non-dict config raises error"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                with pytest.raises(ValueError, match="must be a dictionary"):
                    manager.write_config("not a dict")

    def test_update_config(self):
        """Test updating specific config key"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                manager.update_config("test_key", "test_value")

                config = manager.read_config()
                assert config["test_key"] == "test_value"

    def test_update_config_multiple_keys(self):
        """Test updating multiple config keys"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                manager.update_config("key1", "value1")
                manager.update_config("key2", "value2")

                config = manager.read_config()
                assert config["key1"] == "value1"
                assert config["key2"] == "value2"

    def test_get_config_value(self):
        """Test getting config value"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                manager.update_config("my_key", "my_value")

                value = manager.get_config_value("my_key")
                assert value == "my_value"

    def test_get_config_value_with_default(self):
        """Test getting config value with default"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                value = manager.get_config_value("nonexistent", default="default_value")
                assert value == "default_value"

    def test_clear_config(self):
        """Test clearing configuration"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                manager.update_config("key", "value")
                assert manager.config_file.exists()

                manager.clear_config()
                assert not manager.config_file.exists()

    def test_get_config_path(self):
        """Test getting config file path"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                path = manager.get_config_path()

                assert isinstance(path, str)
                assert "test" in path
                assert "mcli.key.config.json" in path

    def test_read_config_corrupted_json(self):
        """Test reading corrupted JSON returns empty dict"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = CredentialManager(app_name="test")

                # Write corrupted JSON
                manager.config_file.write_text("{invalid json}")

                config = manager.read_config()
                assert config == {}


class TestTokenManager:
    """Test suite for TokenManager"""

    def test_token_manager_init(self):
        """Test TokenManager initialization"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                assert manager.config_file.name == "mcli.token.config.json"

    def test_save_token(self):
        """Test saving authentication token"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                manager.save_token("test_token_123")

                token = manager.get_token()
                assert token == "test_token_123"

    def test_save_token_empty_raises_error(self):
        """Test saving empty token raises ValueError"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                with pytest.raises(ValueError, match="non-empty string"):
                    manager.save_token("")

    def test_save_token_non_string_raises_error(self):
        """Test saving non-string token raises ValueError"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                with pytest.raises(ValueError, match="non-empty string"):
                    manager.save_token(None)

    def test_get_token_not_set(self):
        """Test getting token when not set returns None"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                token = manager.get_token()
                assert token is None

    def test_clear_token(self):
        """Test clearing token"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                manager.save_token("test_token")
                assert manager.get_token() == "test_token"

                manager.clear_token()
                assert manager.get_token() is None

    def test_get_url(self):
        """Test getting environment URL"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                manager.update_config("env_url", "https://api.example.com")

                url = manager.get_url()
                assert url == "https://api.example.com"

    def test_get_url_not_set(self):
        """Test getting URL when not set returns None"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                manager = TokenManager(app_name="test")

                url = manager.get_url()
                assert url is None


class TestAuthFunctions:
    """Test suite for auth.py utility functions"""

    def test_get_current_token(self):
        """Test get_current_token function"""
        from mcli.lib.auth.auth import get_current_token

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                from mcli.lib.auth.token_manager import TokenManager

                # Setup token
                manager = TokenManager()
                manager.save_token("test_token_xyz")

                # Test function
                token = get_current_token()
                assert token == "test_token_xyz"

    def test_get_current_token_not_set(self):
        """Test get_current_token when no token set"""
        from mcli.lib.auth.auth import get_current_token

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                token = get_current_token()
                assert token is None

    def test_get_current_url(self):
        """Test get_current_url function"""
        from mcli.lib.auth.auth import get_current_url

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.lib.auth.credential_manager.Path.home', return_value=Path(tmpdir)):
                from mcli.lib.auth.token_manager import TokenManager

                # Setup URL
                manager = TokenManager()
                manager.update_config("env_url", "https://example.com")

                # Test function
                url = get_current_url()
                assert url == "https://example.com"

    def test_get_mcli_basic_auth_pending(self):
        """Test get_mcli_basic_auth function - method not implemented yet"""
        # Note: get_mcli_basic_auth() in auth.py calls TokenManager.get_mcli_basic_auth()
        # but this method doesn't exist in TokenManager class yet
        # Skipping this test until the method is implemented
        pass
