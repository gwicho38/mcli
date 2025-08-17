import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

logger = get_logger(__name__)


@dataclass
class DaemonClientConfig:
    """Configuration for daemon client"""

    host: str = "localhost"
    port: int = 8000
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


class APIDaemonClient:
    """Client for interacting with the MCLI API Daemon or Flask shell daemon"""

    def __init__(self, config: Optional[DaemonClientConfig] = None, shell_mode: bool = False):
        self.config = config or self._load_config()
        self.shell_mode = shell_mode
        # If shell_mode, always use Flask test server at 0.0.0.0:5005
        if shell_mode:
            self.base_url = "http://localhost:5005"
        else:
            self.base_url = f"http://{self.config.host}:{self.config.port}"
        self.session = requests.Session()

    def execute_shell_command(self, command: str) -> Dict[str, Any]:
        """Execute a raw shell command via the Flask test server"""
        url = f"http://localhost:5005/execute"
        try:
            response = self.session.post(
                url, json={"command": command}, timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to Flask shell daemon at {url}: {e}")

    def _load_config(self) -> DaemonClientConfig:
        """Load configuration from config files"""
        config = DaemonClientConfig()

        # Try to load from config.toml files
        config_paths = [
            Path("config.toml"),  # Current directory
            Path.home() / ".config" / "mcli" / "config.toml",  # User config
            Path(__file__).parent.parent.parent.parent.parent / "config.toml",  # Project root
        ]

        for path in config_paths:
            if path.exists():
                try:
                    daemon_config = read_from_toml(str(path), "api_daemon")
                    if daemon_config:
                        if daemon_config.get("host"):
                            config.host = daemon_config["host"]
                        if daemon_config.get("port"):
                            config.port = daemon_config["port"]
                        logger.debug(f"Loaded daemon client config from {path}")
                        break
                except Exception as e:
                    logger.debug(f"Could not load daemon client config from {path}: {e}")

        return config

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make HTTP request to daemon with retry logic"""
        url = f"{self.base_url}{endpoint}"
        for attempt in range(self.config.retry_attempts):
            try:
                if method.upper() == "GET":
                    response = self.session.request(
                        method=method, url=url, params=params, timeout=self.config.timeout, **kwargs
                    )
                else:
                    response = self.session.request(
                        method=method, url=url, json=data, timeout=self.config.timeout, **kwargs
                    )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.config.retry_attempts - 1:
                    raise Exception(f"Failed to connect to API daemon at {url}: {e}")
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {self.config.retry_delay}s..."
                )
                time.sleep(self.config.retry_delay)
        return {}  # Always return a dict

    def health_check(self) -> Dict[str, Any]:
        """Check daemon health"""
        return self._make_request("GET", "/health")

    def status(self) -> Dict[str, Any]:
        """Get daemon status"""
        return self._make_request("GET", "/status")

    def list_commands(self, all: bool = False) -> Dict[str, Any]:
        """List available commands with metadata. If all=True, include inactive."""
        params = {"all": str(all).lower()} if all else None
        return self._make_request("GET", "/commands", params=params)

    def get_command_details(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific command"""
        return self._make_request("GET", f"/commands/{command_id}")

    def execute_command(
        self,
        command_id: Optional[str] = None,
        command_name: Optional[str] = None,
        args: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a command via the daemon"""
        if not command_id and not command_name:
            raise ValueError("Either command_id or command_name must be provided")

        data = {
            "args": args or [],
        }
        if command_id is not None:
            data["command_id"] = command_id
        if command_name is not None:
            data["command_name"] = command_name
        if timeout is not None:
            data["timeout"] = timeout
        return self._make_request("POST", "/execute", data=data)

    def start_daemon(self) -> Dict[str, Any]:
        """Start the daemon via HTTP"""
        return self._make_request("POST", "/daemon/start")

    def stop_daemon(self) -> Dict[str, Any]:
        """Stop the daemon via HTTP"""
        return self._make_request("POST", "/daemon/stop")

    def is_running(self) -> bool:
        """Check if daemon is running"""
        try:
            status = self.status()
            return status.get("running", False)
        except Exception:
            return False

    def wait_for_daemon(self, timeout: int = 30) -> bool:
        """Wait for daemon to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_running():
                return True
            time.sleep(1)
        return False


# Convenience functions for easy usage
def execute_shell_command_via_flask(command: str) -> Dict[str, Any]:
    """Execute a raw shell command via the Flask test server (convenience function)"""
    client = APIDaemonClient(shell_mode=True)
    return client.execute_shell_command(command)


def get_daemon_client() -> APIDaemonClient:
    """Get a configured daemon client"""
    return APIDaemonClient()


def execute_command_via_daemon(
    command_name: str, args: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Execute a command via the daemon (convenience function)"""
    client = get_daemon_client()
    return client.execute_command(command_name=command_name, args=args)


def check_daemon_status() -> Dict[str, Any]:
    """Check daemon status (convenience function)"""
    client = get_daemon_client()
    return client.status()


def list_available_commands() -> Dict[str, Any]:
    """List available commands (convenience function)"""
    client = get_daemon_client()
    return client.list_commands()
