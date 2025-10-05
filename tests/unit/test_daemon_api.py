"""
Unit tests for mcli.workflow.daemon.daemon_api module
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Check if watchdog is available
try:
    import watchdog
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False


@pytest.mark.skipif(not HAS_WATCHDOG, reason="watchdog module not installed")
class TestDaemonAPI:
    """Test suite for daemon API endpoints"""

    @patch('mcli.workflow.daemon.daemon_api.service')
    def test_list_commands_basic(self, mock_service):
        """Test listing commands"""
        from fastapi.testclient import TestClient
        from mcli.workflow.daemon.daemon_api import app

        # Mock command data
        mock_cmd = MagicMock()
        mock_cmd.id = "cmd-123"
        mock_cmd.name = "test_command"
        mock_cmd.description = "A test command"
        mock_cmd.language = "python"
        mock_cmd.group = "test"
        mock_cmd.tags = ["test", "demo"]
        mock_cmd.created_at = datetime(2025, 1, 1, 12, 0, 0)
        mock_cmd.updated_at = datetime(2025, 1, 2, 12, 0, 0)
        mock_cmd.execution_count = 5
        mock_cmd.last_executed = datetime(2025, 1, 3, 12, 0, 0)
        mock_cmd.is_active = True

        mock_service.db.get_all_commands.return_value = [mock_cmd]

        client = TestClient(app)
        response = client.get("/commands")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_command"
        assert data[0]["language"] == "python"
        assert data[0]["execution_count"] == 5

    @patch('mcli.workflow.daemon.daemon_api.service')
    def test_list_commands_empty(self, mock_service):
        """Test listing commands when none exist"""
        from fastapi.testclient import TestClient
        from mcli.workflow.daemon.daemon_api import app

        mock_service.db.get_all_commands.return_value = []

        client = TestClient(app)
        response = client.get("/commands")

        assert response.status_code == 200
        assert response.json() == []

    @patch('mcli.workflow.daemon.daemon_api.service')
    def test_list_commands_with_all_parameter(self, mock_service):
        """Test listing all commands including inactive"""
        from fastapi.testclient import TestClient
        from mcli.workflow.daemon.daemon_api import app

        mock_cmd_active = MagicMock()
        mock_cmd_active.id = "cmd-1"
        mock_cmd_active.name = "active_command"
        mock_cmd_active.description = None
        mock_cmd_active.language = "bash"
        mock_cmd_active.group = None
        mock_cmd_active.tags = []
        mock_cmd_active.created_at = None
        mock_cmd_active.updated_at = None
        mock_cmd_active.execution_count = 0
        mock_cmd_active.last_executed = None
        mock_cmd_active.is_active = True

        mock_cmd_inactive = MagicMock()
        mock_cmd_inactive.id = "cmd-2"
        mock_cmd_inactive.name = "inactive_command"
        mock_cmd_inactive.description = None
        mock_cmd_inactive.language = "bash"
        mock_cmd_inactive.group = None
        mock_cmd_inactive.tags = []
        mock_cmd_inactive.created_at = None
        mock_cmd_inactive.updated_at = None
        mock_cmd_inactive.execution_count = 0
        mock_cmd_inactive.last_executed = None
        mock_cmd_inactive.is_active = False

        mock_service.db.get_all_commands.return_value = [mock_cmd_active, mock_cmd_inactive]

        client = TestClient(app)
        response = client.get("/commands?all=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify get_all_commands was called with include_inactive=True
        mock_service.db.get_all_commands.assert_called_once_with(include_inactive=True)

    @patch('mcli.workflow.daemon.daemon_api.service')
    def test_execute_command_success(self, mock_service):
        """Test executing a command successfully"""
        from fastapi.testclient import TestClient
        from mcli.workflow.daemon.daemon_api import app

        # Mock command
        mock_cmd = MagicMock()
        mock_cmd.name = "test_command"

        mock_service.db.get_all_commands.return_value = [mock_cmd]
        mock_service.executor.execute_command.return_value = {
            "status": "success",
            "output": "Command executed",
            "exit_code": 0
        }

        client = TestClient(app)
        response = client.post(
            "/execute",
            json={"command_name": "test_command", "args": ["arg1", "arg2"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["output"] == "Command executed"

        # Verify executor was called with correct args
        mock_service.executor.execute_command.assert_called_once()
        call_args = mock_service.executor.execute_command.call_args
        assert call_args[0][1] == ["arg1", "arg2"]

    @patch('mcli.workflow.daemon.daemon_api.service')
    def test_execute_command_not_found(self, mock_service):
        """Test executing a non-existent command"""
        from fastapi.testclient import TestClient
        from mcli.workflow.daemon.daemon_api import app

        mock_service.db.get_all_commands.return_value = []

        client = TestClient(app)
        response = client.post(
            "/execute",
            json={"command_name": "nonexistent_command"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('mcli.workflow.daemon.daemon_api.service')
    def test_execute_command_no_args(self, mock_service):
        """Test executing a command without arguments"""
        from fastapi.testclient import TestClient
        from mcli.workflow.daemon.daemon_api import app

        mock_cmd = MagicMock()
        mock_cmd.name = "simple_command"

        mock_service.db.get_all_commands.return_value = [mock_cmd]
        mock_service.executor.execute_command.return_value = {
            "status": "success",
            "output": "Done",
            "exit_code": 0
        }

        client = TestClient(app)
        response = client.post(
            "/execute",
            json={"command_name": "simple_command"}
        )

        assert response.status_code == 200

        # Verify executor was called with empty args list
        call_args = mock_service.executor.execute_command.call_args
        assert call_args[0][1] == []

    @patch('mcli.workflow.daemon.daemon_api.service')
    def test_list_commands_with_optional_fields(self, mock_service):
        """Test listing commands with None values for optional fields"""
        from fastapi.testclient import TestClient
        from mcli.workflow.daemon.daemon_api import app

        # Mock command with None values
        mock_cmd = MagicMock()
        mock_cmd.id = "cmd-123"
        mock_cmd.name = "minimal_command"
        mock_cmd.description = None
        mock_cmd.language = "bash"
        mock_cmd.group = None
        mock_cmd.tags = []
        mock_cmd.created_at = None
        mock_cmd.updated_at = None
        mock_cmd.execution_count = 0
        mock_cmd.last_executed = None
        mock_cmd.is_active = True

        mock_service.db.get_all_commands.return_value = [mock_cmd]

        client = TestClient(app)
        response = client.get("/commands")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "minimal_command"
        assert data[0]["description"] is None
        assert data[0]["group"] is None
        assert data[0]["created_at"] is None

    def test_api_root_exists(self):
        """Test that API application exists"""
        from mcli.workflow.daemon.daemon_api import app

        assert app is not None
        assert app.title == "MCLI Daemon API"

    def test_command_out_model(self):
        """Test CommandOut pydantic model"""
        from mcli.workflow.daemon.daemon_api import CommandOut

        cmd_out = CommandOut(
            id="test-id",
            name="test_cmd",
            description="Test",
            language="python",
            group="test",
            tags=["tag1"],
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-02T00:00:00",
            execution_count=10,
            last_executed="2025-01-03T00:00:00",
            is_active=True
        )

        assert cmd_out.name == "test_cmd"
        assert cmd_out.execution_count == 10

    def test_execute_request_model(self):
        """Test ExecuteRequest pydantic model"""
        from mcli.workflow.daemon.daemon_api import ExecuteRequest

        req = ExecuteRequest(command_name="test", args=["arg1", "arg2"])

        assert req.command_name == "test"
        assert req.args == ["arg1", "arg2"]

    def test_execute_request_model_no_args(self):
        """Test ExecuteRequest with default args"""
        from mcli.workflow.daemon.daemon_api import ExecuteRequest

        req = ExecuteRequest(command_name="test")

        assert req.command_name == "test"
        assert req.args == []
