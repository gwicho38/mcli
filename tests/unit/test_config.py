"""
Unit tests for mcli.lib.config module
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import tempfile
import os


class TestConfig:
    """Test suite for config module"""

    def test_load_config_default(self):
        """Test loading config with default values"""
        from mcli.lib.config.config import load_config

        with patch('mcli.lib.config.config.CONFIG_FILE') as mock_path:
            mock_path.exists.return_value = False

            result = load_config()

            assert result == {}

    def test_load_config_file_exists(self):
        """Test loading config when file exists"""
        from mcli.lib.config.config import load_config

        test_config = """
        [model]
        server_port = 8080

        [api]
        timeout = 30
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(test_config)
            temp_path = f.name

        try:
            with patch('mcli.lib.config.config.CONFIG_FILE', Path(temp_path)):
                result = load_config()

                assert 'model' in result
                assert result['model']['server_port'] == 8080
                assert result['api']['timeout'] == 30
        finally:
            os.unlink(temp_path)

    def test_save_config(self):
        """Test saving config to file"""
        from mcli.lib.config.config import save_config

        test_config = {
            'model': {'server_port': 9000},
            'api': {'timeout': 60}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.toml'

            with patch('mcli.lib.config.config.CONFIG_FILE', config_path):
                save_config(test_config)

                assert config_path.exists()
                content = config_path.read_text()
                assert 'server_port = 9000' in content
                assert 'timeout = 60' in content

    def test_get_config_value_existing(self):
        """Test getting existing config value"""
        from mcli.lib.config.config import get_config_value

        test_config = """
        [model]
        server_port = 8080
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(test_config)
            temp_path = f.name

        try:
            with patch('mcli.lib.config.config.CONFIG_FILE', Path(temp_path)):
                result = get_config_value('model.server_port')
                assert result == 8080
        finally:
            os.unlink(temp_path)

    def test_get_config_value_missing(self):
        """Test getting missing config value returns default"""
        from mcli.lib.config.config import get_config_value

        with patch('mcli.lib.config.config.CONFIG_FILE') as mock_path:
            mock_path.exists.return_value = False

            result = get_config_value('missing.key', default='default_value')
            assert result == 'default_value'

    def test_get_config_value_nested(self):
        """Test getting nested config value"""
        from mcli.lib.config.config import get_config_value

        test_config = """
        [section]
        [section.nested]
        value = "test"
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(test_config)
            temp_path = f.name

        try:
            with patch('mcli.lib.config.config.CONFIG_FILE', Path(temp_path)):
                result = get_config_value('section.nested.value')
                assert result == 'test'
        finally:
            os.unlink(temp_path)

    def test_config_file_path(self):
        """Test CONFIG_FILE path is set correctly"""
        from mcli.lib.config.config import CONFIG_FILE
        from mcli.lib.paths import get_mcli_home

        expected_path = get_mcli_home() / 'config.toml'
        assert CONFIG_FILE == expected_path
