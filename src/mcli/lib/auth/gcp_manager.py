import json

from mcli.lib.config import DEV_SECRETS_ROOT
from mcli.lib.fs import get_absolute_path
from mcli.lib.logger.logger import get_logger

from .credential_manager import CloudProviderManager

logger = get_logger(__name__)


class GcpManager(CloudProviderManager):
    """
    GCP credential manager for handling authentication tokens and storage credentials.
    Inherits common token management from CloudProviderManager.
    """

    @staticmethod
    def persist_gcp_storage_creds(account_id, account_email, access_key, secret_key):
        """
        Persist GCP storage credentials to file.

        Args:
            account_id (str): GCP account ID.
            account_email (str): GCP account email.
            access_key (str): GCP access key.
            secret_key (str): GCP secret key.
        """
        filepath = get_absolute_path(DEV_SECRETS_ROOT + "gcp/gcp.json")
        with open(filepath, "w") as f:
            json.dump(
                {
                    "accountId": account_id,
                    "accountEmail": account_email,
                    "accessKey": access_key,
                    "secretKey": secret_key,
                },
                f,
            )
        logger.info("Gcp secrets have been persisted into:", filepath)
