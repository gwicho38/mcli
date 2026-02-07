"""Service management package for mcli.

Provides lifecycle management for long-running processes (HTTP servers,
workers, daemons) as named services with start/stop/restart, health checks,
restart policies, and log tailing.
"""

from mcli.lib.services.config import SERVICE_CONFIG_ATTR, ServiceConfig, service
from mcli.lib.services.health import check_http_health, check_pid_alive
from mcli.lib.services.manager import ServiceManager
from mcli.lib.services.registry import ServiceRegistry
from mcli.lib.services.state import ServiceState, list_states, load_state, remove_state, save_state
from mcli.lib.services.supervisor import ServiceSupervisor

__all__ = [
    "ServiceConfig",
    "SERVICE_CONFIG_ATTR",
    "service",
    "ServiceState",
    "load_state",
    "save_state",
    "remove_state",
    "list_states",
    "check_http_health",
    "check_pid_alive",
    "ServiceManager",
    "ServiceSupervisor",
    "ServiceRegistry",
]
