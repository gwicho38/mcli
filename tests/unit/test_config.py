"""
Unit tests for mcli.lib.config module
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os


class TestConfig:
    """Test suite for config module"""

    def test_get_config_for_file(self):
        """Test getting config file path for a file"""
        from mcli.lib.config.config import get_config_for_file

        result = get_config_for_file('test')

        assert 'test' in str(result)
        assert 'mcli.test.config.json' in str(result)

    def test_get_config_for_file_custom_type(self):
        """Test getting config file with custom type"""
        from mcli.lib.config.config import get_config_for_file

        result = get_config_for_file('myfile', config_type='settings')

        assert 'myfile' in str(result)
        assert 'mcli.myfile.settings.json' in str(result)

    def test_get_config_directory(self):
        """Test getting config directory"""
        from mcli.lib.config.config import get_config_directory

        result = get_config_directory()

        assert result is not None
        assert isinstance(result, Path)
        assert '.config/mcli' in str(result) or 'mcli' in str(result).lower()

    def test_get_config_file_name(self):
        """Test extracting config file name from path"""
        from mcli.lib.config.config import get_config_file_name

        result = get_config_file_name('/path/to/myconfig/file.json')

        assert result == 'myconfig'

    def test_get_config_file_name_nested(self):
        """Test config file name extraction with nested paths"""
        from mcli.lib.config.config import get_config_file_name

        result = get_config_file_name('/deep/nested/path/config/file.json')

        # Function returns second-to-last path component
        assert result == 'config'

    def test_user_config_root_exists(self):
        """Test USER_CONFIG_ROOT is defined"""
        from mcli.lib.config.config import USER_CONFIG_ROOT

        assert USER_CONFIG_ROOT is not None
        assert isinstance(USER_CONFIG_ROOT, str)
        assert 'mcli' in USER_CONFIG_ROOT.lower()

    def test_dev_secrets_root_exists(self):
        """Test DEV_SECRETS_ROOT is defined"""
        from mcli.lib.config.config import DEV_SECRETS_ROOT

        assert DEV_SECRETS_ROOT is not None
        assert isinstance(DEV_SECRETS_ROOT, str)
        assert 'secrets' in DEV_SECRETS_ROOT

    def test_private_key_path_defined(self):
        """Test PRIVATE_KEY_PATH is defined"""
        from mcli.lib.config.config import PRIVATE_KEY_PATH

        assert PRIVATE_KEY_PATH is not None
        assert 'private_key.pem' in PRIVATE_KEY_PATH

    def test_user_info_file_defined(self):
        """Test USER_INFO_FILE is defined"""
        from mcli.lib.config.config import USER_INFO_FILE

        assert USER_INFO_FILE is not None
        assert 'user_info.json' in USER_INFO_FILE

    def test_packages_to_sync_defined(self):
        """Test PACKAGES_TO_SYNC constant"""
        from mcli.lib.config.config import PACKAGES_TO_SYNC

        assert PACKAGES_TO_SYNC is not None
        assert isinstance(PACKAGES_TO_SYNC, list)

    def test_get_mcli_rc(self):
        """Test get_mcli_rc function"""
        from mcli.lib.config.config import get_mcli_rc

        # Should not raise an error
        result = get_mcli_rc()

        # Function currently has no return, just logs
