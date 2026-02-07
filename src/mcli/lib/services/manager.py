"""Service lifecycle manager for mcli.

Handles starting, stopping, restarting services as background daemons with
PID file tracking and log capture.
"""

import os
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from mcli.lib.constants import DateFormats, ServiceDefaults
from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_services_logs_dir, get_services_pids_dir
from mcli.lib.services.config import ServiceConfig
from mcli.lib.services.health import check_http_health, check_pid_alive
from mcli.lib.services.state import ServiceState, list_states, load_state, remove_state, save_state

logger = get_logger(__name__)


class ServiceManager:
    """Manages service lifecycle (start/stop/restart) with PID tracking."""

    def _pid_file(self, name: str) -> Path:
        return get_services_pids_dir() / f"{name}.pid"

    def _stdout_log(self, name: str) -> Path:
        return get_services_logs_dir() / f"{name}.stdout.log"

    def _stderr_log(self, name: str) -> Path:
        return get_services_logs_dir() / f"{name}.stderr.log"

    def _read_pid(self, name: str) -> Optional[int]:
        pid_file = self._pid_file(name)
        if not pid_file.exists():
            return None
        try:
            return int(pid_file.read_text().strip())
        except (ValueError, OSError):
            return None

    def _write_pid(self, name: str, pid: int) -> None:
        self._pid_file(name).write_text(str(pid))

    def _remove_pid(self, name: str) -> None:
        pid_file = self._pid_file(name)
        if pid_file.exists():
            pid_file.unlink()

    def start_service(self, config: ServiceConfig) -> Optional[int]:
        """Start a service as a background daemon.

        Returns the PID of the started process, or None on failure.
        """
        name = config.name

        # Check if already running
        existing_pid = self._read_pid(name)
        if existing_pid and check_pid_alive(existing_pid):
            logger.warning(f"Service {name} already running with PID {existing_pid}")
            return None

        # Determine the command to run
        if config.command:
            cmd_parts = config.command.split()
        else:
            logger.error(f"No command configured for service {name}")
            return None

        # Prepare environment
        env = os.environ.copy()
        if config.env:
            env.update(config.env)

        # Open log files
        stdout_path = self._stdout_log(name)
        stderr_path = self._stderr_log(name)

        try:
            stdout_handle = open(stdout_path, "a")  # noqa: SIM115
            stderr_handle = open(stderr_path, "a")  # noqa: SIM115

            process = subprocess.Popen(
                cmd_parts,
                stdout=stdout_handle,
                stderr=stderr_handle,
                cwd=config.working_dir,
                env=env,
                start_new_session=True,
            )

            pid = process.pid
            self._write_pid(name, pid)

            # Save state
            now = datetime.now().strftime(DateFormats.ISO_8601)
            state = ServiceState(
                name=name,
                status="running",
                pid=pid,
                started_at=now,
                config={
                    "service_type": config.service_type,
                    "restart_policy": config.restart_policy,
                    "port": config.port,
                    "host": config.host,
                    "command": config.command,
                    "health_check": config.health_check,
                },
            )
            save_state(state)

            logger.info(f"Started service {name} with PID {pid}")
            return pid

        except Exception as e:
            logger.error(f"Failed to start service {name}: {e}")
            # Record failure
            state = ServiceState(
                name=name,
                status="failed",
                stopped_at=datetime.now().strftime(DateFormats.ISO_8601),
            )
            save_state(state)
            return None

    def stop_service(self, name: str, timeout: int = ServiceDefaults.GRACEFUL_TIMEOUT) -> bool:
        """Stop a running service gracefully."""
        pid = self._read_pid(name)
        if not pid or not check_pid_alive(pid):
            # Clean up stale state
            self._remove_pid(name)
            state = load_state(name)
            if state:
                state.status = "stopped"
                state.pid = None
                state.stopped_at = datetime.now().strftime(DateFormats.ISO_8601)
                save_state(state)
            return True

        try:
            # SIGTERM for graceful shutdown
            os.killpg(os.getpgid(pid), signal.SIGTERM)

            # Wait for process to exit
            proc = psutil.Process(pid)
            try:
                proc.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                # Force kill
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                logger.warning(f"Force-killed service {name} after {timeout}s timeout")

        except (ProcessLookupError, psutil.NoSuchProcess):
            pass  # Already gone
        except Exception as e:
            logger.error(f"Error stopping service {name}: {e}")
            return False

        # Clean up
        self._remove_pid(name)
        state = load_state(name)
        if state:
            state.status = "stopped"
            state.pid = None
            state.stopped_at = datetime.now().strftime(DateFormats.ISO_8601)
            save_state(state)

        logger.info(f"Stopped service {name}")
        return True

    def restart_service(self, config: ServiceConfig) -> Optional[int]:
        """Restart a service (stop then start)."""
        self.stop_service(config.name)
        return self.start_service(config)

    def get_service_status(self, name: str) -> Dict[str, Any]:
        """Get current status of a service."""
        state = load_state(name)
        if not state:
            return {"name": name, "status": "unknown"}

        # Verify the PID is still alive
        if state.status == "running" and state.pid:
            if not check_pid_alive(state.pid):
                state.status = "stopped"
                state.stopped_at = datetime.now().strftime(DateFormats.ISO_8601)
                state.pid = None
                save_state(state)

        return {
            "name": state.name,
            "status": state.status,
            "pid": state.pid,
            "started_at": state.started_at,
            "stopped_at": state.stopped_at,
            "restart_count": state.restart_count,
            "health_status": state.health_status,
            "config": state.config or {},
        }

    def get_service_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a service including process stats."""
        status = self.get_service_status(name)
        if status["status"] == "unknown":
            return None

        info = dict(status)

        # Add process stats if running
        if status["status"] == "running" and status["pid"]:
            try:
                proc = psutil.Process(status["pid"])
                info["cpu_percent"] = proc.cpu_percent()
                info["memory_mb"] = proc.memory_info().rss / (1024 * 1024)
                info["num_threads"] = proc.num_threads()
                if status["started_at"]:
                    started = datetime.strptime(status["started_at"], DateFormats.ISO_8601)
                    uptime = datetime.now() - started
                    info["uptime_seconds"] = int(uptime.total_seconds())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Add log file paths
        info["stdout_log"] = str(self._stdout_log(name))
        info["stderr_log"] = str(self._stderr_log(name))

        return info

    def list_services(self) -> List[Dict[str, Any]]:
        """List all known services with their status."""
        results = []
        for state in list_states():
            results.append(self.get_service_status(state.name))
        return results

    def cleanup_stale(self) -> int:
        """Remove state and PID files for services that are no longer running.

        Returns the number of stale services cleaned up.
        """
        count = 0
        for state in list_states():
            if state.status == "running" and state.pid:
                if not check_pid_alive(state.pid):
                    state.status = "stopped"
                    state.pid = None
                    state.stopped_at = datetime.now().strftime(DateFormats.ISO_8601)
                    save_state(state)
                    self._remove_pid(state.name)
                    count += 1
            elif state.status in ("stopped", "failed"):
                # Clean up PID file if it exists
                self._remove_pid(state.name)
        return count

    def get_logs(self, name: str, lines: int = ServiceDefaults.LOG_TAIL_LINES) -> Dict[str, str]:
        """Get the last N lines of stdout/stderr logs for a service."""
        logs = {"stdout": "", "stderr": ""}

        stdout_path = self._stdout_log(name)
        if stdout_path.exists():
            content = stdout_path.read_text()
            if lines:
                content = "\n".join(content.splitlines()[-lines:])
            logs["stdout"] = content

        stderr_path = self._stderr_log(name)
        if stderr_path.exists():
            content = stderr_path.read_text()
            if lines:
                content = "\n".join(content.splitlines()[-lines:])
            logs["stderr"] = content

        return logs

    def run_foreground(self, config: ServiceConfig) -> int:
        """Run a service in the foreground (blocking).

        Returns the exit code of the process.
        """
        if not config.command:
            logger.error(f"No command configured for service {config.name}")
            return 1

        cmd_parts = config.command.split()
        env = os.environ.copy()
        if config.env:
            env.update(config.env)

        try:
            process = subprocess.Popen(
                cmd_parts,
                cwd=config.working_dir,
                env=env,
            )
            return process.wait()
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=ServiceDefaults.GRACEFUL_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
            return 130  # Standard exit code for SIGINT

    def check_health(self, name: str) -> Optional[bool]:
        """Run health check for a service. Returns None if no health check configured."""
        state = load_state(name)
        if not state or not state.config:
            return None

        health_check = state.config.get("health_check")
        if not health_check:
            return None

        service_type = state.config.get("service_type", "daemon")
        host = state.config.get("host", ServiceDefaults.DEFAULT_HOST)
        port = state.config.get("port", ServiceDefaults.DEFAULT_PORT)

        if service_type == "http" and health_check.startswith("/"):
            result = check_http_health(host, port, health_check)
        else:
            # PID-based check as fallback
            result = check_pid_alive(state.pid) if state.pid else False

        # Update state
        now = datetime.now().strftime(DateFormats.ISO_8601)
        state.last_health_check = now
        state.health_status = "healthy" if result else "unhealthy"
        save_state(state)

        return result
