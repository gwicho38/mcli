import json
import os
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class ProcessStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    EXITED = "exited"
    KILLED = "killed"
    FAILED = "failed"


@dataclass
class ProcessInfo:
    """Information about a managed process"""

    id: str
    name: str
    command: str
    args: List[str]
    status: ProcessStatus
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    working_dir: Optional[str] = None
    environment: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class ProcessContainer:
    """Manages a single containerized process"""

    def __init__(self, process_info: ProcessInfo):
        self.info = process_info
        self.process: Optional[subprocess.Popen] = None
        self.stdout_file: Optional[Path] = None
        self.stderr_file: Optional[Path] = None
        self.container_dir: Optional[Path] = None
        self._setup_container_environment()

    def _setup_container_environment(self):
        """Setup isolated environment for the process"""
        # Create container directory
        base_dir = Path.home() / ".local" / "mcli" / "containers"
        self.container_dir = base_dir / self.info.id
        self.container_dir.mkdir(parents=True, exist_ok=True)

        # Setup log files
        self.stdout_file = self.container_dir / "stdout.log"
        self.stderr_file = self.container_dir / "stderr.log"

        # Create metadata file
        metadata_file = self.container_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(asdict(self.info), f, indent=2, default=str)

    def start(self) -> bool:
        """Start the containerized process"""
        try:
            if self.process and self.process.poll() is None:
                logger.warning(f"Process {self.info.id} is already running")
                return False

            # Open log files
            stdout_handle = open(self.stdout_file, "w")
            stderr_handle = open(self.stderr_file, "w")

            # Start process
            self.process = subprocess.Popen(
                [self.info.command] + self.info.args,
                stdout=stdout_handle,
                stderr=stderr_handle,
                cwd=self.info.working_dir or str(self.container_dir),
                env=self.info.environment or os.environ.copy(),
                preexec_fn=os.setsid,  # Create new process group for better control
            )

            self.info.pid = self.process.pid
            self.info.status = ProcessStatus.RUNNING
            self.info.started_at = datetime.now()

            logger.info(f"Started process {self.info.id} with PID {self.process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start process {self.info.id}: {e}")
            self.info.status = ProcessStatus.FAILED
            return False

    def stop(self, timeout: int = 10) -> bool:
        """Stop the process gracefully"""
        if not self.process or self.process.poll() is not None:
            return True

        try:
            # Send SIGTERM
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if timeout
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()
                self.info.status = ProcessStatus.KILLED
            else:
                self.info.status = ProcessStatus.EXITED

            self.info.exit_code = self.process.returncode
            self.info.finished_at = datetime.now()

            logger.info(f"Stopped process {self.info.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop process {self.info.id}: {e}")
            return False

    def kill(self) -> bool:
        """Force kill the process"""
        if not self.process or self.process.poll() is not None:
            return True

        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.process.wait()

            self.info.status = ProcessStatus.KILLED
            self.info.exit_code = self.process.returncode
            self.info.finished_at = datetime.now()

            logger.info(f"Killed process {self.info.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to kill process {self.info.id}: {e}")
            return False

    def is_running(self) -> bool:
        """Check if process is currently running"""
        if not self.process:
            return False
        return self.process.poll() is None

    def get_logs(self, lines: Optional[int] = None, follow: bool = False) -> Dict[str, str]:
        """Get process logs"""
        logs = {"stdout": "", "stderr": ""}

        try:
            if self.stdout_file and self.stdout_file.exists():
                with open(self.stdout_file, "r") as f:
                    content = f.read()
                    if lines:
                        content = "\n".join(content.split("\n")[-lines:])
                    logs["stdout"] = content

            if self.stderr_file and self.stderr_file.exists():
                with open(self.stderr_file, "r") as f:
                    content = f.read()
                    if lines:
                        content = "\n".join(content.split("\n")[-lines:])
                    logs["stderr"] = content

        except Exception as e:
            logger.error(f"Failed to read logs for process {self.info.id}: {e}")

        return logs

    def get_stats(self) -> Dict[str, Any]:
        """Get process statistics"""
        stats = {
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "num_threads": 0,
            "uptime_seconds": 0,
        }

        try:
            if self.process and self.is_running():
                proc = psutil.Process(self.process.pid)
                stats["cpu_percent"] = proc.cpu_percent()
                stats["memory_mb"] = proc.memory_info().rss / (1024 * 1024)
                stats["num_threads"] = proc.num_threads()

            if self.info.started_at:
                uptime = datetime.now() - self.info.started_at
                stats["uptime_seconds"] = int(uptime.total_seconds())

        except Exception as e:
            logger.error(f"Failed to get stats for process {self.info.id}: {e}")

        return stats

    def cleanup(self):
        """Clean up container resources"""
        try:
            # Stop process if running
            if self.is_running():
                self.stop()

            # Optionally remove container directory
            # (keeping logs for now, but this could be configurable)

        except Exception as e:
            logger.error(f"Failed to cleanup process {self.info.id}: {e}")


class ProcessManager:
    """Docker-like process management system"""

    def __init__(self):
        self.containers: Dict[str, ProcessContainer] = {}
        self.base_dir = Path.home() / ".local" / "mcli" / "containers"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Load existing containers
        self._load_existing_containers()

    def _load_existing_containers(self):
        """Load existing containers from disk"""
        try:
            for container_dir in self.base_dir.iterdir():
                if container_dir.is_dir():
                    metadata_file = container_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, "r") as f:
                                data = json.load(f)

                            # Convert string datetime back to datetime objects
                            for date_field in ["created_at", "started_at", "finished_at"]:
                                if data.get(date_field):
                                    data[date_field] = datetime.fromisoformat(data[date_field])

                            # Convert status back to enum
                            data["status"] = ProcessStatus(data["status"])

                            process_info = ProcessInfo(**data)
                            container = ProcessContainer(process_info)
                            self.containers[process_info.id] = container

                            # Check if process is still actually running
                            if process_info.pid and not psutil.pid_exists(process_info.pid):
                                container.info.status = ProcessStatus.EXITED
                                container.info.finished_at = datetime.now()

                        except Exception as e:
                            logger.error(f"Failed to load container {container_dir.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to load existing containers: {e}")

    def create(
        self,
        name: str,
        command: str,
        args: List[str] = None,
        working_dir: str = None,
        environment: Dict[str, str] = None,
    ) -> str:
        """Create a new process container"""
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            id=process_id,
            name=name,
            command=command,
            args=args or [],
            status=ProcessStatus.CREATED,
            working_dir=working_dir,
            environment=environment,
        )

        container = ProcessContainer(process_info)
        self.containers[process_id] = container

        logger.info(f"Created container {process_id} for command: {command}")
        return process_id

    def start(self, process_id: str) -> bool:
        """Start a process container"""
        if process_id not in self.containers:
            logger.error(f"Container {process_id} not found")
            return False

        return self.containers[process_id].start()

    def stop(self, process_id: str, timeout: int = 10) -> bool:
        """Stop a process container"""
        if process_id not in self.containers:
            logger.error(f"Container {process_id} not found")
            return False

        return self.containers[process_id].stop(timeout)

    def kill(self, process_id: str) -> bool:
        """Kill a process container"""
        if process_id not in self.containers:
            logger.error(f"Container {process_id} not found")
            return False

        return self.containers[process_id].kill()

    def remove(self, process_id: str, force: bool = False) -> bool:
        """Remove a process container"""
        if process_id not in self.containers:
            logger.error(f"Container {process_id} not found")
            return False

        container = self.containers[process_id]

        # Stop if running (unless force kill)
        if container.is_running():
            if force:
                container.kill()
            else:
                container.stop()

        # Cleanup and remove
        container.cleanup()
        del self.containers[process_id]

        logger.info(f"Removed container {process_id}")
        return True

    def list_processes(self, all_processes: bool = False) -> List[Dict[str, Any]]:
        """List all process containers (Docker ps style)"""
        result = []

        for container in self.containers.values():
            if not all_processes and container.info.status in [
                ProcessStatus.EXITED,
                ProcessStatus.KILLED,
            ]:
                continue

            stats = container.get_stats()

            result.append(
                {
                    "id": container.info.id[:12],  # Short ID like Docker
                    "name": container.info.name,
                    "command": f"{container.info.command} {' '.join(container.info.args)}",
                    "status": container.info.status.value,
                    "pid": container.info.pid,
                    "created": (
                        container.info.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if container.info.created_at
                        else ""
                    ),
                    "uptime": f"{stats['uptime_seconds']}s",
                    "cpu": f"{stats['cpu_percent']:.1f}%",
                    "memory": f"{stats['memory_mb']:.1f}MB",
                }
            )

        return result

    def inspect(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a process container"""
        if process_id not in self.containers:
            return None

        container = self.containers[process_id]
        stats = container.get_stats()

        return {
            "id": container.info.id,
            "name": container.info.name,
            "command": container.info.command,
            "args": container.info.args,
            "status": container.info.status.value,
            "pid": container.info.pid,
            "exit_code": container.info.exit_code,
            "created_at": (
                container.info.created_at.isoformat() if container.info.created_at else None
            ),
            "started_at": (
                container.info.started_at.isoformat() if container.info.started_at else None
            ),
            "finished_at": (
                container.info.finished_at.isoformat() if container.info.finished_at else None
            ),
            "working_dir": container.info.working_dir,
            "environment": container.info.environment,
            "stats": stats,
            "container_dir": str(container.container_dir),
        }

    def logs(
        self, process_id: str, lines: Optional[int] = None, follow: bool = False
    ) -> Optional[Dict[str, str]]:
        """Get logs from a process container"""
        if process_id not in self.containers:
            return None

        return self.containers[process_id].get_logs(lines, follow)

    def run(
        self,
        name: str,
        command: str,
        args: List[str] = None,
        working_dir: str = None,
        environment: Dict[str, str] = None,
        detach: bool = True,
    ) -> str:
        """Create and start a process container in one step"""
        process_id = self.create(name, command, args, working_dir, environment)

        if self.start(process_id):
            return process_id
        else:
            # Clean up failed container
            self.remove(process_id, force=True)
            raise RuntimeError(f"Failed to start container {process_id}")
