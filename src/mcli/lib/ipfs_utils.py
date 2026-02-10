"""Shared IPFS utility functions for mcli.

Provides detection, status, and diagnostic helpers used by both
``mcli sync`` and ``mcli self ipfs`` command groups.
"""

import json
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Optional

import requests


def ipfs_installed() -> bool:
    """Check if the ``ipfs`` binary is on PATH."""
    return shutil.which("ipfs") is not None


def ipfs_version() -> Optional[str]:
    """Return the IPFS version string, or *None* if unavailable."""
    try:
        result = subprocess.run(
            ["ipfs", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def ipfs_initialized() -> bool:
    """Return *True* when ``~/.ipfs/config`` exists."""
    ipfs_dir = Path.home() / ".ipfs"
    return ipfs_dir.exists() and (ipfs_dir / "config").exists()


def ipfs_daemon_running() -> bool:
    """Ping the local IPFS API to check if the daemon is up."""
    try:
        response = requests.post("http://127.0.0.1:5001/api/v0/id", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def ipfs_peer_count() -> Optional[int]:
    """Return the number of connected swarm peers, or *None*."""
    try:
        response = requests.post("http://127.0.0.1:5001/api/v0/swarm/peers", timeout=5)
        if response.status_code == 200:
            data = response.json()
            peers = data.get("Peers") or []
            return len(peers)
    except Exception:
        pass
    return None


def ipfs_id_info() -> Optional[dict]:
    """Return the node identity dict from the ``/api/v0/id`` endpoint."""
    try:
        response = requests.post("http://127.0.0.1:5001/api/v0/id", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def ipfs_config_get(key: str) -> Optional[str]:
    """Read a single IPFS config value via ``ipfs config``."""
    try:
        result = subprocess.run(
            ["ipfs", "config", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def ipfs_repo_stat() -> Optional[dict]:
    """Return IPFS repo statistics or *None*."""
    try:
        response = requests.post("http://127.0.0.1:5001/api/v0/repo/stat", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def detect_platform() -> tuple:
    """Return ``(os_name, arch)`` — e.g. ``('darwin', 'arm64')``."""
    import sys as _sys

    os_name = _sys.platform  # 'darwin', 'linux', 'win32'
    arch = platform.machine()  # 'arm64', 'x86_64', 'AMD64'
    return (os_name, arch)


def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Return *True* when *port* is not in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0  # 0 means connected → port in use
    except Exception:
        return True  # assume available on error


def which_package_manager() -> Optional[str]:
    """Detect the first available package manager.

    Returns one of ``brew``, ``apt-get``, ``dnf``, ``winget``, ``choco``,
    or *None*.
    """
    for pm in ("brew", "apt-get", "dnf", "winget", "choco"):
        if shutil.which(pm) is not None:
            return pm
    return None


def validate_ipfs_config() -> bool:
    """Return *True* if ``~/.ipfs/config`` is valid JSON."""
    config_path = Path.home() / ".ipfs" / "config"
    if not config_path.exists():
        return False
    try:
        with open(config_path) as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False
