import base64
import json
import time
from pathlib import Path
from urllib.request import urlopen

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class MCLIManager:
    """
    Class for managing MCLI cluster connections and authentication.
    """

    def __init__(self, env_url: str):
        self.env_url = env_url

    def create_mcli_basic_auth_token(self):
        """Create a basic auth token for MCLI authentication"""
        basic_content_bytes = "BA:BA".encode("ASCII")
        basic_token_b64 = base64.b64encode(basic_content_bytes).decode("ASCII")
        return basic_token_b64

    def create_mcli_basic_auth_header(self, token: str):
        """Create a basic auth header for MCLI authentication"""
        return "Basic " + token

    def mcli_as_dev_user(self, url, authHeader):
        """Connect to MCLI as a dev user"""
        src = urlopen(url + "/remote/mcli.py").read()
        exec_scope = {}
        exec(src, exec_scope)
        return exec_scope["get_mcli"](url=url, authz=authHeader)

    def mcli_as_basic_user(self):
        """Connect to MCLI as a BA user"""
        url = self.env_url
        token = self.create_mcli_basic_auth_token()
        basicAuthHeader = self.create_mcli_basic_auth_header(token)
        mcli = self.mcli_as_dev_user(url, basicAuthHeader)
        return mcli


class MCLIConnectionParams:
    """A picklable class to store MCLI connection parameters"""

    def __init__(self, url, auth_token):
        self.url = url
        self.auth_token = auth_token


class MCLIInstance:
    def __init__(self, url, auth_token):
        self.url = self._normalize_url(url)
        self.auth_token = auth_token
        self._mcli = self._initialize_mcli()

    def _normalize_url(self, url):
        """Normalize URL to ensure it's properly formatted"""
        if not url:
            raise ValueError("URL cannot be empty")

        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        return url.rstrip("/")

    def _initialize_mcli(self):
        """Initialize the MCLI connection"""
        mcli_url = f"{self.url}/remote/mcli.py"

        try:
            logger.info(f"Attempting to connect to: {mcli_url}")
            src = urlopen(mcli_url).read()
            exec_scope = {}
            exec(src, exec_scope)  # pylint: disable=exec-used
            return exec_scope["get_mcli"](url=self.url, authz=self.auth_token)
        except Exception as e:
            logger.info(f"Failed to initialize MCLI connection: {str(e)}")
            raise

    def __getattr__(self, name):
        return getattr(self._mcli, name)


def create_mcli_instance(url, token):
    """Returns mcli remote type system for python."""
    return MCLIInstance(url, token)
