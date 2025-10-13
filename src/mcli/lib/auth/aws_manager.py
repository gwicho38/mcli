import json

from mcli.lib.config import DEV_SECRETS_ROOT
from mcli.lib.fs import get_absolute_path
from mcli.lib.logger.logger import get_logger

from .credential_manager import CloudProviderManager

logger = get_logger(__name__)


class AwsManager(CloudProviderManager):
    """
    AWS credential manager for handling authentication tokens and storage credentials.
    Inherits common token management from CloudProviderManager.
    """

    @staticmethod
    def persist_aws_storage_creds(access_key, secret_key):
        """
        Persist AWS storage credentials to file.

        Args:
            access_key (str): AWS access key.
            secret_key (str): AWS secret key.
        """
        filepath = get_absolute_path(DEV_SECRETS_ROOT + "aws/aws.json")
        with open(filepath, "w") as f:
            json.dump({"access_key": access_key, "secret_key": secret_key}, f)
        logger.info("Aws secrets have been persisted into:", filepath)
