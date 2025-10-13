import base64
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from mcli.lib.config import DEV_SECRETS_ROOT
from mcli.lib.fs import get_absolute_path
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class CredentialManager:
    """
    A base class for managing credentials and configuration files
    with secure file handling and permissions.
    """

    def __init__(self, app_name: str = "mcli", config_filename: str = "mcli.key.config.json"):
        """
        Initialize the CredentialManager.

        Args:
            app_name (str, optional): Name of the application. Defaults to "mcli".
            config_filename (str, optional): Name of the configuration file. Defaults to "mcli.key.config.json".
        """
        self.config_dir = Path.home() / ".config" / app_name
        self.config_file = self.config_dir / config_filename
        self._ensure_config_dir()
        # logger.info("config file:", self.config_file)

    def _ensure_config_dir(self):
        """
        Create config directory with secure permissions.
        Ensures parent directories exist and sets proper access modes.
        """
        logger.info("Insure of ensure config dir")
        logger.info("config file:", self.config_file)
        logger.info("config dir:", self.config_dir)
        try:
            # Create parent directories if they don't exist
            # 0o700 means read, write, execute permissions for owner only
            self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

            # Set secure permissions for config file if it exists
            if self.config_file.exists():
                self.config_file.chmod(0o600)
        except Exception as e:
            raise Exception(f"Failed to create config directory: {str(e)}")

    def read_config(self) -> Dict[str, Any]:
        """
        Read configuration from file.

        Returns:
            Dict[str, Any]: Configuration dictionary, empty if file doesn't exist or is invalid.
        """
        try:
            logger.info("Reading config file:", self.config_file)
            if not self.config_file.exists():
                return {}

            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config if isinstance(config, dict) else {}
        except json.JSONDecodeError:
            logger.info(
                f"Warning: Config file {self.config_file} is corrupted, creating new configuration"
            )
            return {}
        except Exception as e:
            logger.info(f"Warning: Error reading config file: {str(e)}")
            return {}

    def write_config(self, config: Dict[str, Any]):
        """
        Write configuration to file with secure permissions.

        Args:
            config (Dict[str, Any]): Configuration dictionary to write.

        Raises:
            ValueError: If config is not a dictionary.
            Exception: If writing configuration fails.
        """
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        try:
            # Ensure directory exists before writing
            self._ensure_config_dir()

            # Write with proper encoding
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            # Set secure permissions (read/write only for owner)
            self.config_file.chmod(0o600)
        except Exception as e:
            raise Exception(f"Failed to write configuration: {str(e)}")

    def get_config_path(self) -> str:
        """
        Get the path to the configuration file.

        Returns:
            str: Path to the configuration file.
        """
        return str(self.config_file)

    def clear_config(self):
        """
        Clear the stored configuration by removing the config file.
        """
        try:
            if self.config_file.exists():
                self.config_file.unlink()
        except Exception as e:
            raise Exception(f"Failed to clear configuration: {str(e)}")

    def update_config(self, key: str, value: Any):
        """
        Update a specific key in the configuration.

        Args:
            key (str): Configuration key to update.
            value (Any): Value to set for the key.
        """
        try:
            config = self.read_config()
            config[key] = value
            self.write_config(config)
        except Exception as e:
            raise Exception(f"Failed to update configuration: {str(e)}")

    def get_config_value(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Retrieve a specific value from the configuration.

        Args:
            key (str): Configuration key to retrieve.
            default (Optional[Any], optional): Default value if key doesn't exist. Defaults to None.

        Returns:
            Optional[Any]: Value of the configuration key or default.
        """
        try:
            config = self.read_config()
            return config.get(key, default)
        except Exception as e:
            logger.info(f"Warning: Error retrieving configuration value: {str(e)}")
            return default

    @staticmethod
    def generate_signature(private_key_path):
        private_key_path = get_absolute_path(private_key_path)
        if not os.path.exists(private_key_path):
            raise Exception("Private key does not exist at path:" + private_key_path)
        nonce = str(math.floor(time.time() * 1000))
        # Generate the signature using the private key
        sig = os.popen(
            "logger.info('Generating signature') && echo -n "
            + nonce
            + " | openssl dgst -hex -sigopt rsa_padding_mode:pss -sha256 -sign "
            + private_key_path
        ).read()
        # Remove the '(stdin)=' prefix from the output
        sig = sig[len("SHA2-256(stdin)=") :].strip()
        # Encode the nonce in hexadecimal format
        hex_nonce = nonce.encode("ascii").hex()
        return (sig, hex_nonce)

    @staticmethod
    def persist_generic_creds(thirdPartyApiKind, creds):
        filepath = get_absolute_path(DEV_SECRETS_ROOT + "thirdParty/" + thirdPartyApiKind + ".txt")
        with open(filepath, "w") as f:
            f.write(json.dumps(str(creds)))
        logger.info(thirdPartyApiKind + " secrets have been persisted into:", filepath)

    @staticmethod
    def create_key_auth_token(user_id, private_key_path):
        sig, hex_nonce = CredentialManager.generate_signature(private_key_path)
        key = user_id + ":" + hex_nonce + ":" + sig
        key_bytes = key.encode("utf-8")
        key_b64 = base64.b64encode(key_bytes).decode("ascii")
        return key_b64


class CloudProviderManager(CredentialManager):
    """
    Abstract base class for cloud provider credential managers.
    Provides common token and URL management functionality for AWS, GCP, and Azure.
    """

    def __init__(self, app_name: str = "mcli"):
        """
        Initialize CloudProviderManager with token configuration filename.

        Args:
            app_name (str, optional): Name of the application. Defaults to "mcli".
        """
        super().__init__(app_name, config_filename="mcli.token.config.json")

    def save_token(self, token: str):
        """
        Save authentication token to configuration.

        Args:
            token (str): Authentication token to save.

        Raises:
            ValueError: If token is empty or not a string.
        """
        if not token or not isinstance(token, str):
            raise ValueError("Token must be a non-empty string")

        try:
            self.update_config("auth_token", token)
        except Exception as e:
            raise Exception(f"Failed to save token: {str(e)}")

    def get_token(self) -> Optional[str]:
        """
        Retrieve the stored authentication token.

        Returns:
            Optional[str]: Stored authentication token or None if not found.
        """
        try:
            logger.info("getting token")
            return self.get_config_value("auth_token")
        except Exception as e:
            logger.info(f"Warning: Error retrieving token: {str(e)}")
            return None

    def clear_token(self):
        """
        Clear the stored authentication token.
        Uses the base class clear_config method.
        """
        self.clear_config()

    def get_url(self) -> Optional[str]:
        """
        Retrieve environment URL from configuration.

        Returns:
            Optional[str]: Stored environment URL or None if not found.
        """
        try:
            logger.info("getting url")
            return self.get_config_value("env_url")
        except Exception as e:
            logger.info(f"Warning: Error retrieving environment URL: {str(e)}")
            return None


__all__ = ["CredentialManager", "CloudProviderManager"]
