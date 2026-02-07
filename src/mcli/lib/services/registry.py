"""Service registry for mcli.

Discovers Click commands decorated with @service and collects their configs.
"""

from typing import Dict

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.services.config import SERVICE_CONFIG_ATTR, ServiceConfig

logger = get_logger(__name__)


class ServiceRegistry:
    """Discovers @service-decorated Click commands."""

    @staticmethod
    def discover(app: click.Group) -> Dict[str, ServiceConfig]:
        """Walk the Click command tree and find commands with service config.

        Args:
            app: The root Click group to walk.

        Returns:
            Dict mapping service name to ServiceConfig.
        """
        services: Dict[str, ServiceConfig] = {}
        ServiceRegistry._walk_commands(app, services)
        return services

    @staticmethod
    def _walk_commands(group: click.Group, services: Dict[str, ServiceConfig]) -> None:
        """Recursively walk Click command tree looking for @service decorators."""
        try:
            commands = group.commands if hasattr(group, "commands") else {}
        except Exception:
            return

        for name, cmd in commands.items():
            # Check if this command has a service config
            callback = getattr(cmd, "callback", None)
            if callback and hasattr(callback, SERVICE_CONFIG_ATTR):
                config = getattr(callback, SERVICE_CONFIG_ATTR)
                services[config.name] = config
                logger.debug(f"Discovered service: {config.name}")

            # Recurse into groups
            if isinstance(cmd, click.Group):
                ServiceRegistry._walk_commands(cmd, services)
