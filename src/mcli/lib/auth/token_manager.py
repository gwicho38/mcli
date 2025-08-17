from typing import Optional

from mcli.lib.logger import get_logger

from .credential_manager import CredentialManager

logger = get_logger(__name__)


class TokenManager(CredentialManager):
    """
    Specialized credential manager for handling authentication tokens and environment URLs.
    """

    def __init__(self, app_name: str = "mcli"):
        """
        Initialize TokenManager with a specific configuration filename.

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
