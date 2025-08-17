from pathlib import Path

from mcli.lib.fs import get_user_home
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml import read_from_toml

logger = get_logger(__name__)
logger.info("")

# Path to root repo. Exclude trailing slash
# TODO: Needs to be updated for all env variables used in app
PATH_TO_PACKAGE_REPO = "/Users/lefv/mcli/mclifed-guru/cornea"

# Listen to file updates within these packages
PACKAGES_TO_SYNC = ["mcli_ui_package"]

# Exclude trailing slash
ENDPOINT = ""

# Basic auth token for BA:BA
USER_CONFIG_ROOT = f"{get_user_home()}/.config/mcli/"
DEV_SECRETS_ROOT = f"{get_user_home()}/.config/mcli/secrets/"
PRIVATE_KEY_PATH = f"{DEV_SECRETS_ROOT}/keys/private_key.pem"
USER_INFO_FILE = f"{DEV_SECRETS_ROOT}/user/user_info.json"


def get_config_for_file(file_name: str, config_type: str = "config") -> str:
    """Get the config for a file."""
    return f"{get_config_directory()}/{file_name}/mcli.{file_name}.{config_type}.json"


def get_config_directory() -> str:
    """Get the config directory."""
    return Path(USER_CONFIG_ROOT)


def get_config_file_name(raw_file_name: str) -> str:
    """Get the config file name."""
    return raw_file_name.split("/")[-2]


def get_mcli_rc():
    logger.info(__name__)
    logger.info(__package__)
    # case_state_scrambler = read_from_toml(

    # )
