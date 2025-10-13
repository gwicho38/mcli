import json

from mcli.lib.config import DEV_SECRETS_ROOT
from mcli.lib.fs import get_absolute_path
from mcli.lib.logger.logger import get_logger

from .credential_manager import CloudProviderManager

logger = get_logger(__name__)


class AzureManager(CloudProviderManager):
    """
    Azure credential manager for handling authentication tokens and storage credentials.
    Inherits common token management from CloudProviderManager.
    """

    @staticmethod
    def persist_azure_storage_creds(account_name, access_key):
        """
        Persist Azure storage credentials to file.

        Args:
            account_name (str): Azure storage account name.
            access_key (str): Azure storage access key.
        """
        filepath = get_absolute_path(DEV_SECRETS_ROOT + "azure/azure.json")
        with open(filepath, "w") as f:
            json.dump(
                {
                    "storage_account_name": account_name,
                    "storage_access_key": access_key,
                },
                f,
            )
        logger.info("Azure secrets have been persisted into:", filepath)
