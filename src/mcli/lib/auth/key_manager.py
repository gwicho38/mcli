from typing import Optional
from .credential_manager import CredentialManager
from mcli.lib.logger.logger import get_logger
logger = get_logger(__name__)


ALLOWED_ACTIONS = [
    "REVOKE_AZURE",
    "REVOKE_AWS",
    "PROVISION_AZURE",
    "REVOKE_GCP",
    "PROVISION_AWS",
    "PROVISION_GCP",
    "PROVISION_THIRDPARTY",
]


class KeyManager(CredentialManager):
    """
    Specialized credential manager for handling authentication tokens and keys.
    """

    def save_key(self, token: str):
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

    def get_key(self) -> Optional[str]:
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

    def clear_key(self):
        """
        Clear the stored authentication token.
        Uses the base class clear_config method.
        """
        self.clear_config()

    def create_key_pair(self) -> Optional[str]:
        """
        Create a key pair (placeholder method).
        Retrieve environment URL from configuration.

        Returns:
            Optional[str]: Environment URL or None if not found.
        """
        try:
            logger.info("getting url")
            return self.get_config_value("env_url")
        except Exception as e:
            logger.info(f"Warning: Error retrieving environment URL: {str(e)}")
            return None

    @staticmethod
    def allowed_action(action: str) -> bool:
        """
        Check if the given action is allowed.

        Args:
            action (str): Action to validate.

        Returns:
            bool: True if action is allowed, False otherwise.
        """
        return action in ALLOWED_ACTIONS

    @staticmethod
    def logger_info_allowed_actions():
        """
        logger.info the list of allowed actions.
        """
        logger.info("Allowed actions:")
        for action in ALLOWED_ACTIONS:
            logger.info(f"  - {action}")
