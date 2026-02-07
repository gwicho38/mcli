"""Health check utilities for mcli services."""

import importlib

import psutil
import requests

from mcli.lib.constants import ServiceDefaults
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


def check_http_health(
    host: str,
    port: int,
    path: str = "/",
    timeout: int = ServiceDefaults.HEALTH_CHECK_TIMEOUT,
) -> bool:
    """Check service health via HTTP GET.

    Args:
        host: Service host.
        port: Service port.
        path: Health check path (e.g., "/health").
        timeout: Request timeout in seconds.

    Returns:
        True if the service responds with 2xx status.
    """
    url = f"http://{host}:{port}{path}"
    try:
        resp = requests.get(url, timeout=timeout)
        return 200 <= resp.status_code < 300
    except Exception as e:
        logger.debug(f"HTTP health check failed for {url}: {e}")
        return False


def check_callable_health(callable_ref: str) -> bool:
    """Check service health by calling a Python function.

    Args:
        callable_ref: Dotted path to a callable (e.g., "mymod.health.check").

    Returns:
        True if the callable returns truthy.
    """
    try:
        module_path, func_name = callable_ref.rsplit(".", 1)
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        return bool(func())
    except Exception as e:
        logger.debug(f"Callable health check failed for {callable_ref}: {e}")
        return False


def check_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive.

    Args:
        pid: Process ID to check.

    Returns:
        True if the process exists and is running.
    """
    if pid is None:
        return False
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).status() != "zombie"
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
