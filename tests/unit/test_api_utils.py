"""
Unit tests for mcli.lib.api utility functions
"""

import pytest
from unittest.mock import patch, MagicMock
import socket
import os


class TestApiUtils:
    """Test suite for API utility functions"""

    def test_find_free_port(self):
        """Test finding a free port"""
        from mcli.lib.api.api import find_free_port

        port = find_free_port()

        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_find_free_port_with_start_port(self):
        """Test finding free port from specific start port"""
        from mcli.lib.api.api import find_free_port

        port = find_free_port(start_port=9000)

        assert isinstance(port, int)
        assert port >= 9000

    def test_find_free_port_fallback_to_random(self):
        """Test fallback to random port when no port available"""
        from mcli.lib.api.api import find_free_port

        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_sock.bind.side_effect = OSError("Address already in use")
            mock_socket.return_value.__enter__.return_value = mock_sock

            port = find_free_port(start_port=8000, max_attempts=2)

            # Should return a random port in safe range
            assert 49152 <= port <= 65535

    def test_get_api_config_defaults(self):
        """Test getting default API config"""
        from mcli.lib.api.api import get_api_config

        with patch('mcli.lib.api.api.read_from_toml', return_value=None):
            with patch.dict(os.environ, {}, clear=True):
                config = get_api_config()

                assert config['enabled'] is False
                assert config['host'] == '0.0.0.0'
                assert config['use_random_port'] is True

    def test_get_api_config_from_env(self):
        """Test getting API config from environment variables"""
        from mcli.lib.api.api import get_api_config

        env = {
            'MCLI_API_SERVER': 'true',
            'MCLI_API_HOST': '127.0.0.1',
            'MCLI_API_PORT': '9000'
        }

        with patch('mcli.lib.api.api.read_from_toml', return_value=None):
            with patch.dict(os.environ, env, clear=True):
                config = get_api_config()

                assert config['enabled'] is True
                assert config['host'] == '127.0.0.1'
                assert config['port'] == 9000
                assert config['use_random_port'] is False

    def test_get_api_config_from_toml(self):
        """Test getting API config from TOML file"""
        from mcli.lib.api.api import get_api_config

        toml_config = {
            'enabled': True,
            'port': 8080,
            'debug': True
        }

        with patch('mcli.lib.api.api.read_from_toml', return_value=toml_config):
            with patch('pathlib.Path.exists', return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    config = get_api_config()

                    assert config['enabled'] is True
                    assert config['port'] == 8080
                    assert config['debug'] is True

    def test_get_api_config_env_overrides_toml(self):
        """Test that environment variables override TOML config"""
        from mcli.lib.api.api import get_api_config

        toml_config = {
            'enabled': False,
            'port': 8080
        }

        env = {
            'MCLI_API_SERVER': 'true',
            'MCLI_API_PORT': '9000'
        }

        with patch('mcli.lib.api.api.read_from_toml', return_value=toml_config):
            with patch('pathlib.Path.exists', return_value=True):
                with patch.dict(os.environ, env, clear=True):
                    config = get_api_config()

                    assert config['enabled'] is True  # Overridden by env
                    assert config['port'] == 9000  # Overridden by env
