"""
CLI tests for mcli.app.redis_cmd module
"""

import pytest
import asyncio
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock

# Check if redis is available
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


@pytest.mark.skipif(not HAS_REDIS, reason="redis module not installed")
class TestRedisCommands:
    """Test suite for Redis CLI commands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_redis_group_exists(self):
        """Test redis command group exists"""
        from mcli.app.redis_cmd import redis_group

        assert redis_group is not None
        assert hasattr(redis_group, 'commands')

    def test_redis_group_help(self):
        """Test redis command group help"""
        from mcli.app.redis_cmd import redis_group

        result = self.runner.invoke(redis_group, ['--help'])

        assert result.exit_code == 0
        assert 'redis' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_start_redis_not_running(self, mock_get_service):
        """Test starting Redis when not running"""
        from mcli.app.redis_cmd import redis_group

        # Create mock service
        mock_service = AsyncMock()
        mock_service.is_running.return_value = False
        mock_service.start.return_value = True
        mock_service.get_status.return_value = {
            'host': 'localhost',
            'port': 6379,
            'data_dir': '/tmp/redis',
            'process_id': 12345
        }
        mock_service.get_connection_url.return_value = 'redis://localhost:6379'

        # Make get_redis_service return the mock
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['start'])

        assert result.exit_code == 0
        assert 'started' in result.output.lower() or 'redis' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_start_redis_already_running(self, mock_get_service):
        """Test starting Redis when already running"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.is_running.return_value = True
        mock_service.get_status.return_value = {
            'host': 'localhost',
            'port': 6379,
            'uptime': 3600
        }
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['start'])

        assert result.exit_code == 0
        assert 'already running' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_start_redis_failure(self, mock_get_service):
        """Test starting Redis with failure"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.is_running.return_value = False
        mock_service.start.return_value = False
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['start'])

        assert result.exit_code == 0
        assert 'failed' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_stop_redis_running(self, mock_get_service):
        """Test stopping Redis when running"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.is_running.return_value = True
        mock_service.stop.return_value = True
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['stop'])

        assert result.exit_code == 0
        assert 'stopped' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_stop_redis_not_running(self, mock_get_service):
        """Test stopping Redis when not running"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.is_running.return_value = False
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['stop'])

        assert result.exit_code == 0
        assert 'not running' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_restart_redis_success(self, mock_get_service):
        """Test restarting Redis successfully"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.restart.return_value = True
        mock_service.get_status.return_value = {
            'host': 'localhost',
            'port': 6379
        }
        mock_service.get_connection_url.return_value = 'redis://localhost:6379'
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['restart'])

        assert result.exit_code == 0
        assert 'restarted' in result.output.lower() or 'restart' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_restart_redis_failure(self, mock_get_service):
        """Test restarting Redis with failure"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.restart.return_value = False
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['restart'])

        assert result.exit_code == 0
        assert 'failed' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_redis_status_running(self, mock_get_service):
        """Test Redis status when running"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.get_status.return_value = {
            'running': True,
            'host': 'localhost',
            'port': 6379,
            'version': '7.0.0',
            'memory_usage': '1.2M',
            'connected_clients': 3,
            'uptime': 3600,
            'total_commands': 10000,
            'keyspace_hits': 8000,
            'keyspace_misses': 2000,
            'data_dir': '/tmp/redis',
            'process_id': 12345
        }
        mock_service.get_connection_url.return_value = 'redis://localhost:6379'
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['status'])

        assert result.exit_code == 0
        assert 'running' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_redis_status_not_running(self, mock_get_service):
        """Test Redis status when not running"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.get_status.return_value = {
            'running': False,
            'host': 'localhost',
            'port': 6379,
            'data_dir': '/tmp/redis'
        }
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['status'])

        assert result.exit_code == 0
        assert 'not running' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_test_redis_connection_success(self, mock_get_service):
        """Test Redis connection test success"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.is_running.return_value = True
        mock_service.test_connection.return_value = {
            'status': 'success',
            'latency_ms': 2.5
        }
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['test'])

        assert result.exit_code == 0
        assert 'passed' in result.output.lower() or 'success' in result.output.lower()

    @patch('mcli.app.redis_cmd.get_redis_service')
    def test_test_redis_not_running(self, mock_get_service):
        """Test Redis connection test when not running"""
        from mcli.app.redis_cmd import redis_group

        mock_service = AsyncMock()
        mock_service.is_running.return_value = False
        mock_get_service.return_value = mock_service

        result = self.runner.invoke(redis_group, ['test'])

        assert result.exit_code == 0
        assert 'not running' in result.output.lower()

    def test_redis_start_help(self):
        """Test start command help"""
        from mcli.app.redis_cmd import redis_group

        result = self.runner.invoke(redis_group, ['start', '--help'])

        assert result.exit_code == 0

    def test_redis_stop_help(self):
        """Test stop command help"""
        from mcli.app.redis_cmd import redis_group

        result = self.runner.invoke(redis_group, ['stop', '--help'])

        assert result.exit_code == 0

    def test_redis_restart_help(self):
        """Test restart command help"""
        from mcli.app.redis_cmd import redis_group

        result = self.runner.invoke(redis_group, ['restart', '--help'])

        assert result.exit_code == 0

    def test_redis_status_help(self):
        """Test status command help"""
        from mcli.app.redis_cmd import redis_group

        result = self.runner.invoke(redis_group, ['status', '--help'])

        assert result.exit_code == 0

    def test_redis_test_help(self):
        """Test test command help"""
        from mcli.app.redis_cmd import redis_group

        result = self.runner.invoke(redis_group, ['test', '--help'])

        assert result.exit_code == 0
