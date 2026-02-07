"""Service configuration and decorator for mcli."""

from dataclasses import dataclass, field
from typing import Optional

SERVICE_CONFIG_ATTR = "_mcli_service_config"


@dataclass
class ServiceConfig:
    """Configuration for a managed service."""

    name: str
    description: str = ""
    port: Optional[int] = None
    host: str = "127.0.0.1"
    service_type: str = "daemon"  # http | worker | daemon
    restart_policy: str = "never"  # never | on-failure | always
    env: dict = field(default_factory=dict)
    health_check: Optional[str] = None  # URL path for http, or callable name
    log_file: Optional[str] = None
    command: Optional[str] = None  # Shell command to run (for non-Click services)
    working_dir: Optional[str] = None


def service(**kwargs):
    """Decorator to mark a Click command as a managed service.

    Usage:
        @service(name="my-api", port=8000, service_type="http",
                 restart_policy="on-failure", health_check="/health")
        @click.command()
        def my_api():
            ...
    """

    def decorator(func):
        config = ServiceConfig(**kwargs)
        setattr(func, SERVICE_CONFIG_ATTR, config)
        return func

    return decorator
