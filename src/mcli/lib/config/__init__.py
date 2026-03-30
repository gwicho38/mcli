"""Config module for MCLI.

Provides both legacy config constants and the new Pydantic-validated settings system.

Usage (new):
    from mcli.lib.config import get_settings
    settings = get_settings()

Usage (legacy, preserved for backward compatibility):
    from mcli.lib.config import USER_CONFIG_ROOT
"""

from .config import (
    DEV_SECRETS_ROOT,
    ENDPOINT,
    PACKAGES_TO_SYNC,
    PATH_TO_PACKAGE_REPO,
    PRIVATE_KEY_PATH,
    USER_CONFIG_ROOT,
    USER_INFO_FILE,
    get_config_directory,
    get_config_file_name,
    get_config_for_file,
    get_mcli_rc,
)
from .settings import MCLISettings, get_settings, reset_settings

__all__ = [
    # New Pydantic settings
    "MCLISettings",
    "get_settings",
    "reset_settings",
    # Legacy exports (backward compat)
    "DEV_SECRETS_ROOT",
    "ENDPOINT",
    "PACKAGES_TO_SYNC",
    "PATH_TO_PACKAGE_REPO",
    "PRIVATE_KEY_PATH",
    "USER_CONFIG_ROOT",
    "USER_INFO_FILE",
    "get_config_directory",
    "get_config_file_name",
    "get_config_for_file",
    "get_mcli_rc",
]
