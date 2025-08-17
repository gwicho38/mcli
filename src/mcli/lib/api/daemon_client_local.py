import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

logger = get_logger(__name__)


class LocalDaemonClient:
    """Client for interacting with the MCLI Daemon via CLI subprocess (local IPC)"""

    def __init__(self):
        self.daemon_cmd = ["python", "-m", "mcli.workflow.daemon.daemon"]
        # Optionally, you could use the installed CLI: ["mcli-daemon"]

    def list_commands(self) -> Dict[str, Any]:
        logger.info("[LocalDaemonClient] Invoking 'list-commands' via subprocess")
        result = subprocess.run(
            self.daemon_cmd + ["list-commands", "--json"], capture_output=True, text=True
        )
        logger.info(f"[LocalDaemonClient] stdout: {result.stdout}\nstderr: {result.stderr}")
        if result.returncode != 0:
            raise Exception(f"Daemon list-commands failed: {result.stderr}")
        return json.loads(result.stdout)

    def execute_command(
        self, command_name: str, args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        logger.info(f"[LocalDaemonClient] Invoking 'execute' for {command_name} via subprocess")
        cmd = self.daemon_cmd + ["execute", command_name] + (args or []) + ["--json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        logger.info(f"[LocalDaemonClient] stdout: {result.stdout}\nstderr: {result.stderr}")
        if result.returncode != 0:
            raise Exception(f"Daemon execute failed: {result.stderr}")
        return json.loads(result.stdout)

    # Add more methods as needed for other daemon features


def get_local_daemon_client():
    return LocalDaemonClient()
