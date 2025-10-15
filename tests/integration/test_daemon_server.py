"""
Integration tests for mcli.workflow.daemon module

NOTE: Daemon CLI commands have been migrated to portable JSON format.
Some daemon classes referenced in these tests (like CommandDatabase) were removed.
Tests are skipped until they can be refactored for the new architecture.
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Skip all tests in this module - daemon commands now loaded from JSON
pytestmark = pytest.mark.skip(
    reason="daemon commands migrated to portable JSON format, needs test refactoring"
)


class TestCommand:
    """Test the Command dataclass"""

    def test_command_creation(self):
        """Test creating a command with all fields"""
        cmd = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('hello')",
            language="python",
            group="test-group",
            tags=["test", "python"],
        )

        assert cmd.id == "test-id"
        assert cmd.name == "test-command"
        assert cmd.description == "A test command"
        assert cmd.code == "print('hello')"
        assert cmd.language == "python"
        assert cmd.group == "test-group"
        assert cmd.tags == ["test", "python"]
        assert cmd.execution_count == 0
        assert cmd.is_active is True
        assert isinstance(cmd.created_at, datetime)
        assert isinstance(cmd.updated_at, datetime)

    def test_command_defaults(self):
        """Test command creation with defaults"""
        cmd = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('hello')",
            language="python",
        )

        assert cmd.group is None
        assert cmd.tags == []
        assert cmd.execution_count == 0
        assert cmd.is_active is True
        assert cmd.last_executed is None


class TestCommandDatabase:
    """Test the CommandDatabase class"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_database_initialization(self, temp_db):
        """Test database initialization"""
        db = CommandDatabase(temp_db)

        # Check if tables were created
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check commands table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commands'")
        assert cursor.fetchone() is not None

        # Check groups table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
        assert cursor.fetchone() is not None

        # Check executions table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='executions'")
        assert cursor.fetchone() is not None

        conn.close()

    def test_add_command(self, temp_db):
        """Test adding a command to the database"""
        db = CommandDatabase(temp_db)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('hello')",
            language="python",
            group="test-group",
            tags=["test", "python"],
        )

        command_id = db.add_command(command)
        assert command_id == "test-id"

        # Verify command was added
        retrieved = db.get_command("test-id")
        assert retrieved is not None
        assert retrieved.name == "test-command"
        assert retrieved.description == "A test command"
        assert retrieved.code == "print('hello')"
        assert retrieved.language == "python"
        assert retrieved.group == "test-group"
        assert retrieved.tags == ["test", "python"]

    def test_get_command_not_found(self, temp_db):
        """Test getting a non-existent command"""
        db = CommandDatabase(temp_db)

        command = db.get_command("non-existent")
        assert command is None

    def test_get_all_commands(self, temp_db):
        """Test getting all commands"""
        db = CommandDatabase(temp_db)

        # Add multiple commands
        commands = [
            Command(id="1", name="cmd1", description="First", code="print(1)", language="python"),
            Command(id="2", name="cmd2", description="Second", code="print(2)", language="node"),
            Command(id="3", name="cmd3", description="Third", code="print(3)", language="lua"),
        ]

        for cmd in commands:
            db.add_command(cmd)

        all_commands = db.get_all_commands()
        assert len(all_commands) == 3

        # Check that all commands are active
        for cmd in all_commands:
            assert cmd.is_active is True

    def test_search_commands(self, temp_db):
        """Test searching commands"""
        db = CommandDatabase(temp_db)

        # Add commands with different content
        commands = [
            Command(
                id="1",
                name="data-processor",
                description="Process data",
                code="print('data')",
                language="python",
            ),
            Command(
                id="2",
                name="file-handler",
                description="Handle files",
                code="print('file')",
                language="python",
            ),
            Command(
                id="3",
                name="web-scraper",
                description="Scrape websites",
                code="print('web')",
                language="node",
            ),
        ]

        for cmd in commands:
            db.add_command(cmd)

        # Search by name
        results = db.search_commands("data", limit=10)
        assert len(results) == 1
        assert results[0].name == "data-processor"

        # Search by description
        results = db.search_commands("files", limit=10)
        assert len(results) == 1
        assert results[0].name == "file-handler"

        # Search by language
        results = db.search_commands("node", limit=10)
        assert len(results) == 1
        assert results[0].language == "node"

    def test_update_command(self, temp_db):
        """Test updating a command"""
        db = CommandDatabase(temp_db)

        # Add a command
        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('hello')",
            language="python",
        )

        db.add_command(command)

        # Update the command
        command.description = "Updated description"
        command.tags = ["updated", "tags"]

        success = db.update_command(command)
        assert success is True

        # Verify update
        updated = db.get_command("test-id")
        assert updated.description == "Updated description"
        assert updated.tags == ["updated", "tags"]

    def test_delete_command(self, temp_db):
        """Test deleting a command (soft delete)"""
        db = CommandDatabase(temp_db)

        # Add a command
        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('hello')",
            language="python",
        )

        db.add_command(command)

        # Verify command exists
        assert db.get_command("test-id") is not None

        # Delete command
        success = db.delete_command("test-id")
        assert success is True

        # Verify command is soft deleted (not in get_all_commands)
        all_commands = db.get_all_commands()
        assert len(all_commands) == 0

    def test_record_execution(self, temp_db):
        """Test recording command execution"""
        db = CommandDatabase(temp_db)

        # Add a command
        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('hello')",
            language="python",
        )

        db.add_command(command)

        # Record execution
        db.record_execution(
            command_id="test-id",
            status="completed",
            output="hello",
            error="",
            execution_time_ms=100,
        )

        # Verify execution was recorded
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM executions WHERE command_id = ?", ("test-id",))
        count = cursor.fetchone()[0]
        assert count == 1

        # Verify command execution count was updated
        updated_command = db.get_command("test-id")
        assert updated_command.execution_count == 1
        assert updated_command.last_executed is not None

        conn.close()


class TestCommandExecutor:
    """Test the CommandExecutor class"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_executor_initialization(self, temp_dir):
        """Test executor initialization"""
        executor = CommandExecutor(temp_dir)

        assert executor.temp_dir == Path(temp_dir)
        assert executor.temp_dir.exists()
        assert "python" in executor.language_handlers
        assert "node" in executor.language_handlers
        assert "lua" in executor.language_handlers
        assert "shell" in executor.language_handlers

    def test_execute_python_command(self, temp_dir):
        """Test executing a Python command"""
        executor = CommandExecutor(temp_dir)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('Hello, World!')",
            language="python",
        )

        result = executor.execute_command(command, [])

        assert result["success"] is True
        assert "Hello, World!" in result["output"]
        assert result["error"] == ""
        assert result["status"] == "completed"
        assert result["execution_time_ms"] > 0

    def test_execute_python_command_with_args(self, temp_dir):
        """Test executing a Python command with arguments"""
        executor = CommandExecutor(temp_dir)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="""
import sys
print(f"Arguments: {sys.argv[1:]}")
""",
            language="python",
        )

        result = executor.execute_command(command, ["arg1", "arg2"])

        assert result["success"] is True
        assert "Arguments: ['arg1', 'arg2']" in result["output"]

    def test_execute_python_command_with_error(self, temp_dir):
        """Test executing a Python command that raises an error"""
        executor = CommandExecutor(temp_dir)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="raise ValueError('Test error')",
            language="python",
        )

        result = executor.execute_command(command, [])

        assert result["success"] is False
        assert "Test error" in result["error"]
        assert result["status"] == "failed"

    def test_execute_unsupported_language(self, temp_dir):
        """Test executing a command with unsupported language"""
        executor = CommandExecutor(temp_dir)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('hello')",
            language="unsupported",
        )

        result = executor.execute_command(command, [])

        assert result["success"] is False
        assert "Unsupported language" in result["error"]

    @pytest.mark.skipif(not os.path.exists("/usr/bin/node"), reason="Node.js not available")
    def test_execute_node_command(self, temp_dir):
        """Test executing a Node.js command"""
        executor = CommandExecutor(temp_dir)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="console.log('Hello from Node.js!');",
            language="node",
        )

        result = executor.execute_command(command, [])

        assert result["success"] is True
        assert "Hello from Node.js!" in result["output"]

    @pytest.mark.skipif(not os.path.exists("/usr/bin/lua"), reason="Lua not available")
    def test_execute_lua_command(self, temp_dir):
        """Test executing a Lua command"""
        executor = CommandExecutor(temp_dir)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="print('Hello from Lua!')",
            language="lua",
        )

        result = executor.execute_command(command, [])

        assert result["success"] is True
        assert "Hello from Lua!" in result["output"]

    def test_execute_shell_command(self, temp_dir):
        """Test executing a shell command"""
        executor = CommandExecutor(temp_dir)

        command = Command(
            id="test-id",
            name="test-command",
            description="A test command",
            code="echo 'Hello from shell!'",
            language="shell",
        )

        result = executor.execute_command(command, [])

        assert result["success"] is True
        assert "Hello from shell!" in result["output"]


class TestDaemonService:
    """Test the DaemonService class"""

    @pytest.fixture
    def temp_daemon_dir(self):
        """Create a temporary daemon directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            daemon_dir = Path(temp_dir) / "daemon"
            daemon_dir.mkdir()
            yield daemon_dir

    @patch("src.mcli.workflow.daemon.commands.Path.home")
    def test_daemon_service_initialization(self, mock_home, temp_daemon_dir):
        """Test daemon service initialization"""
        mock_home.return_value = temp_daemon_dir.parent

        service = DaemonService()

        assert service.db is not None
        assert service.executor is not None
        assert service.running is False
        expected_daemon_dir = temp_daemon_dir.parent / ".local" / "mcli" / "daemon"
        assert service.pid_file == expected_daemon_dir / "daemon.pid"
        assert service.socket_file == expected_daemon_dir / "daemon.sock"

    @patch("src.mcli.workflow.daemon.commands.Path.home")
    def test_daemon_status_not_running(self, mock_home, temp_daemon_dir):
        """Test daemon status when not running"""
        mock_home.return_value = temp_daemon_dir.parent

        service = DaemonService()
        status = service.status()

        assert status["running"] is False
        assert status["pid"] is None
        assert "daemon.pid" in status["pid_file"]
        assert "daemon.sock" in status["socket_file"]

    @patch("src.mcli.workflow.daemon.commands.Path.home")
    @patch("src.mcli.workflow.daemon.commands.psutil.pid_exists")
    def test_daemon_status_running(self, mock_pid_exists, mock_home, temp_daemon_dir):
        """Test daemon status when running"""
        mock_home.return_value = temp_daemon_dir.parent
        mock_pid_exists.return_value = True

        # Create a PID file in the expected location
        expected_daemon_dir = temp_daemon_dir.parent / ".local" / "mcli" / "daemon"
        expected_daemon_dir.mkdir(parents=True, exist_ok=True)
        pid_file = expected_daemon_dir / "daemon.pid"
        with open(pid_file, "w") as f:
            f.write("12345")

        service = DaemonService()
        status = service.status()

        assert status["running"] is True
        assert status["pid"] == 12345


class TestDaemonCLI:
    """Test the daemon CLI commands"""

    def test_daemon_group_help(self):
        """Test daemon group help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["--help"])
        assert result.exit_code == 0
        assert "Daemon service for command management" in result.output

    def test_daemon_start_help(self):
        """Test daemon start help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["start", "--help"])
        assert result.exit_code == 0
        assert "Start the daemon service" in result.output

    def test_daemon_stop_help(self):
        """Test daemon stop help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["stop", "--help"])
        assert result.exit_code == 0
        assert "Stop the daemon service" in result.output

    def test_daemon_status_help(self):
        """Test daemon status help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show daemon status" in result.output

    def test_daemon_add_file_help(self):
        """Test daemon add-file help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["add-file", "--help"])
        assert result.exit_code == 0
        assert "Add a command from a file" in result.output

    def test_daemon_add_stdin_help(self):
        """Test daemon add-stdin help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["add-stdin", "--help"])
        assert result.exit_code == 0
        assert "Add a command from stdin" in result.output

    def test_daemon_add_interactive_help(self):
        """Test daemon add-interactive help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["add-interactive", "--help"])
        assert result.exit_code == 0
        assert "Add a command interactively" in result.output

    def test_daemon_execute_help(self):
        """Test daemon execute help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["execute", "--help"])
        assert result.exit_code == 0
        assert "Execute a command" in result.output

    def test_daemon_search_help(self):
        """Test daemon search help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search for commands" in result.output

    def test_daemon_list_help(self):
        """Test daemon list help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["list", "--help"])
        assert result.exit_code == 0
        assert "List all commands" in result.output

    def test_daemon_show_help(self):
        """Test daemon show help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["show", "--help"])
        assert result.exit_code == 0
        assert "Show command details" in result.output

    def test_daemon_delete_help(self):
        """Test daemon delete help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["delete", "--help"])
        assert result.exit_code == 0
        assert "Delete a command" in result.output

    def test_daemon_edit_help(self):
        """Test daemon edit help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["edit", "--help"])
        assert result.exit_code == 0
        assert "Edit a command" in result.output

    def test_daemon_groups_help(self):
        """Test daemon groups help"""
        runner = CliRunner()
        result = runner.invoke(daemon, ["groups", "--help"])
        assert result.exit_code == 0
        assert "List all command groups" in result.output


class TestDaemonIntegration:
    """Integration tests for the daemon functionality"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for integration tests"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_add_and_execute_command(self, temp_db):
        """Test adding a command and then executing it"""
        db = CommandDatabase(temp_db)
        executor = CommandExecutor()

        # Add a command
        command = Command(
            id="test-id",
            name="hello-world",
            description="A simple hello world command",
            code="print('Hello, World!')",
            language="python",
            group="test",
            tags=["hello", "python"],
        )

        command_id = db.add_command(command)
        assert command_id == "test-id"

        # Execute the command
        result = executor.execute_command(command, [])

        assert result["success"] is True
        assert "Hello, World!" in result["output"]

        # Record execution in database (this would normally be done by the daemon service)
        db.record_execution(
            command_id=command.id,
            status=result["status"],
            output=result["output"],
            error=result.get("error", ""),
            execution_time_ms=result.get("execution_time_ms", 0),
        )

        # Verify execution was recorded
        updated_command = db.get_command("test-id")
        assert updated_command.execution_count == 1
        assert updated_command.last_executed is not None

    def test_search_and_similarity(self, temp_db):
        """Test search and similarity functionality"""
        db = CommandDatabase(temp_db)

        # Add commands with similar content
        commands = [
            Command(
                id="1",
                name="data-processor",
                description="Process data files",
                code="print('data')",
                language="python",
                tags=["data", "processing"],
            ),
            Command(
                id="2",
                name="file-processor",
                description="Process file operations",
                code="print('file')",
                language="python",
                tags=["file", "processing"],
            ),
            Command(
                id="3",
                name="web-scraper",
                description="Scrape web content",
                code="print('web')",
                language="node",
                tags=["web", "scraping"],
            ),
        ]

        for cmd in commands:
            db.add_command(cmd)

        # Test text search
        results = db.search_commands("processing", limit=10)
        assert len(results) == 2

        # Test similarity search
        similar = db.find_similar_commands("data processing", limit=5)
        assert len(similar) > 0

        # Verify similarity scores are reasonable
        for cmd, similarity in similar:
            assert 0 <= similarity <= 1

    def test_command_lifecycle(self, temp_db):
        """Test the complete command lifecycle"""
        db = CommandDatabase(temp_db)

        # 1. Add command
        command = Command(
            id="lifecycle-test",
            name="lifecycle-test",
            description="Test command lifecycle",
            code="print('lifecycle')",
            language="python",
        )

        command_id = db.add_command(command)
        assert command_id == "lifecycle-test"

        # 2. Verify command exists
        retrieved = db.get_command("lifecycle-test")
        assert retrieved is not None
        assert retrieved.name == "lifecycle-test"

        # 3. Update command
        retrieved.description = "Updated description"
        retrieved.tags = ["updated"]

        success = db.update_command(retrieved)
        assert success is True

        # 4. Verify update
        updated = db.get_command("lifecycle-test")
        assert updated.description == "Updated description"
        assert updated.tags == ["updated"]

        # 5. Delete command
        success = db.delete_command("lifecycle-test")
        assert success is True

        # 6. Verify deletion
        all_commands = db.get_all_commands()
        assert len(all_commands) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
