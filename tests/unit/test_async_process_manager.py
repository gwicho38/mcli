"""
Unit tests for mcli.workflow.daemon.async_process_manager module

NOTE: This module requires aiosqlite and other async dependencies.
Tests are conditional on dependencies being available.
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# Check for async dependencies
try:
    import aiosqlite
    from mcli.workflow.daemon.async_process_manager import (
        ProcessStatus,
        ProcessInfo,
        AsyncProcessContainer,
        AsyncProcessManager,
    )
    HAS_ASYNC_DEPS = True
except (ImportError, ModuleNotFoundError):
    HAS_ASYNC_DEPS = False
    # Create stubs for type hints
    ProcessStatus = None
    ProcessInfo = None
    AsyncProcessContainer = None
    AsyncProcessManager = None

# Skip all tests if dependencies not available
if not HAS_ASYNC_DEPS:
    pytestmark = pytest.mark.skip(reason="aiosqlite or async dependencies not available")


class TestProcessStatus:
    """Test ProcessStatus enum"""

    def test_process_status_values(self):
        """Test ProcessStatus enum values"""
        assert ProcessStatus.CREATED.value == "created"
        assert ProcessStatus.RUNNING.value == "running"
        assert ProcessStatus.EXITED.value == "exited"
        assert ProcessStatus.KILLED.value == "killed"
        assert ProcessStatus.FAILED.value == "failed"
        assert ProcessStatus.TIMEOUT.value == "timeout"


class TestProcessInfo:
    """Test ProcessInfo dataclass"""

    def test_process_info_initialization(self):
        """Test ProcessInfo initialization"""
        proc_info = ProcessInfo(
            id="test-123",
            name="test_process",
            command="echo",
            args=["hello"],
            status=ProcessStatus.CREATED,
        )

        assert proc_info.id == "test-123"
        assert proc_info.name == "test_process"
        assert proc_info.command == "echo"
        assert proc_info.args == ["hello"]
        assert proc_info.status == ProcessStatus.CREATED
        assert proc_info.pid is None
        assert proc_info.exit_code is None
        assert proc_info.created_at is not None  # Auto-set in __post_init__
        assert proc_info.stdout_lines == []  # Auto-set in __post_init__
        assert proc_info.stderr_lines == []  # Auto-set in __post_init__

    def test_process_info_with_optional_fields(self):
        """Test ProcessInfo with optional fields"""
        env = {"TEST_VAR": "value"}
        proc_info = ProcessInfo(
            id="test-456",
            name="test_process",
            command="pwd",
            args=[],
            status=ProcessStatus.RUNNING,
            pid=1234,
            working_dir="/tmp",
            environment=env,
        )

        assert proc_info.pid == 1234
        assert proc_info.working_dir == "/tmp"
        assert proc_info.environment == env


class TestAsyncProcessContainer:
    """Test AsyncProcessContainer"""

    @pytest.fixture
    def process_info(self):
        """Create a test ProcessInfo"""
        return ProcessInfo(
            id="test-container-1",
            name="test_process",
            command="echo",
            args=["hello"],
            status=ProcessStatus.CREATED,
        )

    def test_container_initialization(self, process_info):
        """Test container initialization"""
        container = AsyncProcessContainer(process_info)

        assert container.info == process_info
        assert container.process is None
        assert container.container_dir is not None
        assert container.container_dir.exists()

        # Verify metadata file was created
        metadata_file = container.container_dir / "metadata.json"
        assert metadata_file.exists()

    @pytest.mark.asyncio
    async def test_start_process_success(self, process_info):
        """Test starting a process successfully"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Mock the process
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_exec.return_value = mock_process

            result = await container.start()

            assert result is True
            assert container.info.status == ProcessStatus.RUNNING
            assert container.info.pid == 12345
            assert container.info.started_at is not None

    @pytest.mark.asyncio
    async def test_start_process_already_running(self, process_info):
        """Test starting a process that's already running"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_exec.return_value = mock_process

            # Start first time
            await container.start()

            # Try to start again
            result = await container.start()
            assert result is False

    @pytest.mark.asyncio
    async def test_start_process_failure(self, process_info):
        """Test handling start process failure"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec", side_effect=Exception("Start failed")):
            result = await container.start()

            assert result is False
            assert container.info.status == ProcessStatus.FAILED

    @pytest.mark.asyncio
    async def test_stop_process_success(self, process_info):
        """Test stopping a process successfully"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            # Start the process
            await container.start()

            # Mock the process completing
            mock_process.returncode = 0

            # Stop the process
            result = await container.stop()

            assert result is True
            assert container.info.status == ProcessStatus.EXITED
            assert container.info.exit_code == 0
            assert container.info.finished_at is not None

    @pytest.mark.asyncio
    async def test_stop_process_timeout(self, process_info):
        """Test stopping a process with timeout"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_process.kill = AsyncMock()
            mock_exec.return_value = mock_process

            await container.start()

            # Stop with timeout - should force kill
            result = await container.stop(timeout=0.1)

            assert result is True
            assert container.info.status == ProcessStatus.KILLED
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_kill_process(self, process_info):
        """Test force killing a process"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.kill = AsyncMock()
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            await container.start()

            # Kill the process
            mock_process.returncode = -9
            result = await container.kill()

            assert result is True
            assert container.info.status == ProcessStatus.KILLED
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_process(self, process_info):
        """Test waiting for process completion"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            await container.start()

            # Simulate process completing
            mock_process.returncode = 0

            exit_code = await container.wait()

            assert exit_code == 0
            assert container.info.status == ProcessStatus.EXITED
            assert container.info.exit_code == 0

    @pytest.mark.asyncio
    async def test_wait_for_process_with_timeout(self, process_info):
        """Test waiting for process with timeout"""
        container = AsyncProcessContainer(process_info)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_exec.return_value = mock_process

            await container.start()

            # Wait with timeout
            with pytest.raises(asyncio.TimeoutError):
                await container.wait(timeout=0.1)

            assert container.info.status == ProcessStatus.TIMEOUT


@pytest.mark.asyncio
class TestAsyncProcessManager:
    """Test AsyncProcessManager"""

    @pytest.fixture
    async def manager(self):
        """Create a test AsyncProcessManager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_processes.db"
            mgr = AsyncProcessManager(db_path=str(db_path), redis_url="redis://localhost:6379")

            # Mock Redis to avoid connection errors
            with patch.object(mgr, "_init_redis", new=AsyncMock()):
                await mgr.initialize()

            yield mgr

            # Cleanup
            await mgr.close()

    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test manager initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_processes.db"
            manager = AsyncProcessManager(db_path=str(db_path))

            with patch.object(manager, "_init_redis", new=AsyncMock()):
                await manager.initialize()

            assert manager.db_path.exists()
            assert manager.processes == {}

            await manager.close()

    @pytest.mark.asyncio
    async def test_start_process_success(self, manager):
        """Test starting a process successfully"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_exec.return_value = mock_process

            process_id = await manager.start_process("test_proc", "echo", ["hello"])

            assert process_id is not None
            assert process_id in manager.processes
            assert manager.processes[process_id].info.status == ProcessStatus.RUNNING

    @pytest.mark.asyncio
    async def test_start_process_failure(self, manager):
        """Test handling start process failure"""
        with patch(
            "asyncio.create_subprocess_exec", side_effect=Exception("Failed to start")
        ) as mock_exec:
            with pytest.raises(RuntimeError, match="Failed to start process"):
                await manager.start_process("failing_proc", "invalid_command", [])

    @pytest.mark.asyncio
    async def test_stop_process_success(self, manager):
        """Test stopping a process"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            # Start a process
            process_id = await manager.start_process("test_proc", "sleep", ["10"])

            # Mock process completing
            mock_process.returncode = 0

            # Stop it
            result = await manager.stop_process(process_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_stop_nonexistent_process(self, manager):
        """Test stopping a process that doesn't exist"""
        with pytest.raises(KeyError, match="Process not found"):
            await manager.stop_process("nonexistent-id")

    @pytest.mark.asyncio
    async def test_kill_process_success(self, manager):
        """Test killing a process"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.kill = AsyncMock()
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            # Start a process
            process_id = await manager.start_process("test_proc", "sleep", ["10"])

            # Kill it
            mock_process.returncode = -9
            result = await manager.kill_process(process_id)

            assert result is True
            assert manager.processes[process_id].info.status == ProcessStatus.KILLED

    @pytest.mark.asyncio
    async def test_get_process_info_active(self, manager):
        """Test getting info for an active process"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_exec.return_value = mock_process

            process_id = await manager.start_process("test_proc", "echo", ["hello"])

            info = await manager.get_process_info(process_id)

            assert info.id == process_id
            assert info.name == "test_proc"
            assert info.command == "echo"
            assert info.status == ProcessStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_process_info_nonexistent(self, manager):
        """Test getting info for nonexistent process"""
        with pytest.raises(KeyError, match="Process not found"):
            await manager.get_process_info("nonexistent-id")

    @pytest.mark.asyncio
    async def test_list_processes_all(self, manager):
        """Test listing all processes"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_exec.return_value = mock_process

            # Start multiple processes
            id1 = await manager.start_process("proc1", "echo", ["1"])
            id2 = await manager.start_process("proc2", "echo", ["2"])

            processes = await manager.list_processes()

            assert len(processes) >= 2
            assert any(p.id == id1 for p in processes)
            assert any(p.id == id2 for p in processes)

    @pytest.mark.asyncio
    async def test_list_processes_with_filter(self, manager):
        """Test listing processes with status filter"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_exec.return_value = mock_process

            # Start a process
            await manager.start_process("running_proc", "sleep", ["10"])

            # List only running processes
            running = await manager.list_processes(status_filter="running")

            assert len(running) > 0
            assert all(p.status == ProcessStatus.RUNNING for p in running)

    @pytest.mark.asyncio
    async def test_cleanup_finished_processes(self, manager):
        """Test cleanup of finished processes"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            # Start and stop a process
            process_id = await manager.start_process("test_proc", "echo", ["done"])
            mock_process.returncode = 0
            await manager.stop_process(process_id)

            # Cleanup
            cleaned_ids = await manager.cleanup_finished()

            assert process_id in cleaned_ids
            assert process_id not in manager.processes

    @pytest.mark.asyncio
    async def test_database_persistence(self):
        """Test process info persistence to database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_processes.db"

            # Create manager and start process
            manager1 = AsyncProcessManager(db_path=str(db_path))
            with patch.object(manager1, "_init_redis", new=AsyncMock()):
                await manager1.initialize()

            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.returncode = None
                mock_process.stdout = AsyncMock()
                mock_process.stdout.readline = AsyncMock(return_value=b"")
                mock_process.stderr = AsyncMock()
                mock_process.stderr.readline = AsyncMock(return_value=b"")
                mock_exec.return_value = mock_process

                process_id = await manager1.start_process("persistent_proc", "echo", ["hello"])

            await manager1.close()

            # Create new manager with same database
            manager2 = AsyncProcessManager(db_path=str(db_path))
            with patch.object(manager2, "_init_redis", new=AsyncMock()):
                await manager2.initialize()

            # Should be able to retrieve process info
            info = await manager2.get_process_info(process_id)

            assert info.id == process_id
            assert info.name == "persistent_proc"

            await manager2.close()
