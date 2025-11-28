"""
Secrets manager for handling secure storage and retrieval of secrets.
"""

import base64
import os
from pathlib import Path
from typing import Dict, List, Optional

import click
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from mcli.lib.constants.paths import DirNames
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class SecretsManager:
    """Manages secrets storage with encryption."""

    def __init__(self, secrets_dir: Optional[Path] = None):
        """Initialize the secrets manager.

        Args:
            secrets_dir: Directory to store secrets. Defaults to ~/.mcli/secrets/
        """
        self.secrets_dir = secrets_dir or Path.home() / DirNames.MCLI / "secrets"
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self._cipher_suite = self._get_cipher_suite()

    def _get_cipher_suite(self) -> Fernet:
        """Get or create encryption key."""
        key_file = self.secrets_dir / ".key"

        if key_file.exists():
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            # Generate a new key from a password
            password = click.prompt("Enter a password for secrets encryption", hide_input=True)
            password_bytes = password.encode()

            # Use PBKDF2 to derive a key from the password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"mcli-secrets-salt",  # In production, use a random salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password_bytes))

            # Save the key (in production, this should be stored more securely)
            with open(key_file, "wb") as f:
                f.write(key)

            # Set restrictive permissions
            os.chmod(key_file, 0o600)

        return Fernet(key)

    def set(self, key: str, value: str, namespace: Optional[str] = None) -> None:
        """Set a secret value.

        Args:
            key: Secret key
            value: Secret value
            namespace: Optional namespace for grouping secrets
        """
        namespace = namespace or "default"
        namespace_dir = self.secrets_dir / namespace
        namespace_dir.mkdir(exist_ok=True)

        # Encrypt the value
        encrypted_value = self._cipher_suite.encrypt(value.encode())

        # Store the encrypted value
        secret_file = namespace_dir / f"{key}.secret"
        with open(secret_file, "wb") as f:
            f.write(encrypted_value)

        # Set restrictive permissions
        os.chmod(secret_file, 0o600)

        logger.debug(f"Secret '{key}' stored in namespace '{namespace}'")

    def get(self, key: str, namespace: Optional[str] = None) -> Optional[str]:
        """Get a secret value.

        Args:
            key: Secret key
            namespace: Optional namespace

        Returns:
            Decrypted secret value or None if not found
        """
        namespace = namespace or "default"
        secret_file = self.secrets_dir / namespace / f"{key}.secret"

        if not secret_file.exists():
            return None

        with open(secret_file, "rb") as f:
            encrypted_value = f.read()

        try:
            decrypted_value = self._cipher_suite.decrypt(encrypted_value)
            return decrypted_value.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt secret '{key}': {e}")
            return None

    def list(self, namespace: Optional[str] = None) -> list[str]:
        """List all secret keys.

        Args:
            namespace: Optional namespace filter

        Returns:
            List of secret keys
        """
        if namespace:
            namespace_dirs = [self.secrets_dir / namespace]
        else:
            namespace_dirs = [
                d for d in self.secrets_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]

        secrets = []
        for namespace_dir in namespace_dirs:
            if namespace_dir.exists():
                for secret_file in namespace_dir.glob("*.secret"):
                    key = secret_file.stem
                    ns = namespace_dir.name
                    secrets.append(f"{ns}/{key}" if not namespace else key)

        return sorted(secrets)

    def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete a secret.

        Args:
            key: Secret key
            namespace: Optional namespace

        Returns:
            True if deleted, False if not found
        """
        namespace = namespace or "default"
        secret_file = self.secrets_dir / namespace / f"{key}.secret"

        if secret_file.exists():
            secret_file.unlink()
            logger.debug(f"Secret '{key}' deleted from namespace '{namespace}'")
            return True

        return False

    def export_env(self, namespace: Optional[str] = None) -> dict[str, str]:
        """Export secrets as environment variables.

        Args:
            namespace: Optional namespace filter

        Returns:
            Dictionary of key-value pairs
        """
        env_vars = {}

        for secret_key in self.list(namespace):
            if "/" in secret_key:
                ns, key = secret_key.split("/", 1)
                value = self.get(key, ns)
            else:
                value = self.get(secret_key, namespace)

            if value:
                # Convert to uppercase for environment variable convention
                if "/" in secret_key:
                    env_key = key.upper().replace("-", "_")
                else:
                    env_key = secret_key.upper().replace("-", "_")
                env_vars[env_key] = value

        return env_vars

    def import_env(self, env_file: Path, namespace: Optional[str] = None) -> int:
        """Import secrets from an environment file.

        Args:
            env_file: Path to .env file
            namespace: Optional namespace

        Returns:
            Number of secrets imported
        """
        namespace = namespace or "default"
        count = 0

        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    self.set(key.lower().replace("_", "-"), value, namespace)
                    count += 1

        return count
