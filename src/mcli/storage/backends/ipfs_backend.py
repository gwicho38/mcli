"""
IPFS/Storacha storage backend implementation.

Provides decentralized storage via Storacha network (formerly web3.storage).
Uses the Storacha CLI for authentication and HTTP bridge API for uploads.

Does NOT use lsh-framework for secrets management.
Credentials are stored in MCLI's own config at ~/.mcli/storacha-config.json.
"""

import hashlib
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from mcli.lib.constants import StorageDefaults, StorageEnvVars, StorageMessages, StoragePaths
from mcli.lib.logger import get_logger
from mcli.storage.base import EncryptedStorageBackend
from mcli.storage.cache import LocalCache
from mcli.storage.registry import RegistryManager
from mcli.storage.storacha_cli import BridgeTokens, StorachaCLI

logger = get_logger(__name__)


class StorachaBackend(EncryptedStorageBackend):
    """
    Storacha/IPFS storage backend.

    Features:
    - Stores encrypted data on IPFS via Storacha
    - Local caching for offline access
    - Registry system for version tracking
    - Email-based authentication via Storacha CLI
    - HTTP bridge API for programmatic uploads
    - Graceful fallback (cache → network → error)

    Environment Variables:
        MCLI_STORACHA_ENABLED: Enable network sync (default: true)
        STORACHA_EMAIL: User email for authentication (optional)
    """

    def __init__(self, encryption_key: str):
        """
        Initialize Storacha backend.

        Args:
            encryption_key: Master encryption key for AES-256
        """
        super().__init__(encryption_key)

        # Configuration
        self.enabled = (
            os.getenv(
                StorageEnvVars.STORACHA_ENABLED, StorageDefaults.STORACHA_ENABLED_DEFAULT
            ).lower()
            == "true"
        )

        # API endpoints
        self.bridge_url = StorageDefaults.STORACHA_HTTP_BRIDGE_URL
        self.gateway_base = StorageDefaults.STORACHA_GATEWAY_BASE

        # Local directories
        self.cache_dir = Path.home() / StoragePaths.STORAGE_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = Path.home() / StoragePaths.STORACHA_CONFIG_FILE

        # Components
        self.cache = LocalCache(self.cache_dir)
        self.registry = RegistryManager(self)
        self.cli = StorachaCLI(self.config_path)

        # HTTP client for bridge API
        self.client = httpx.AsyncClient(timeout=StorageDefaults.UPLOAD_TIMEOUT_SECONDS)

        # Cached bridge tokens
        self._bridge_tokens: Optional[BridgeTokens] = None

    async def connect(self) -> bool:
        """
        Establish connection to Storacha.

        Returns:
            bool: True if connected (or disabled), False if authentication required
        """
        if not self.enabled:
            logger.info(StorageMessages.USING_CACHE_ONLY)
            self._connected = True
            return True

        # Check CLI status
        if not self.cli.is_cli_installed():
            logger.warning(StorageMessages.STORACHA_CLI_NOT_FOUND)
            # Still return True - we can use local cache
            self._connected = True
            return True

        authenticated = self.cli.is_authenticated()
        if not authenticated:
            logger.warning(StorageMessages.NOT_AUTHENTICATED_WARNING)
            # Still return True - we can use local cache
            self._connected = True
            return True

        # Try to get/refresh bridge tokens
        self._bridge_tokens = self.cli.get_bridge_tokens(auto_refresh=True)
        if self._bridge_tokens:
            logger.info(StorageMessages.CONNECTED_STORACHA)
        else:
            logger.warning("Could not obtain bridge tokens, using cache only")

        self._connected = True
        return True

    async def disconnect(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        self._connected = False

    async def health_check(self) -> bool:
        """
        Check if Storacha is accessible.

        Returns:
            bool: True if healthy (or disabled)
        """
        if not self.enabled:
            return True

        try:
            # Try to access gateway to verify connectivity
            response = await self.client.get(
                "https://storacha.link",
                timeout=StorageDefaults.HEALTH_CHECK_TIMEOUT_SECONDS,
            )
            return response.status_code == 200
        except Exception:
            return False

    async def is_authenticated(self) -> bool:
        """
        Check if user is authenticated with Storacha.

        Returns:
            bool: True if authenticated
        """
        return self.cli.is_authenticated()

    async def login(self, email: str) -> bool:
        """
        Login with email (triggers email verification).

        Args:
            email: User email address

        Returns:
            bool: True if login successful
        """
        if not self.cli.is_cli_installed():
            logger.error(StorageMessages.STORACHA_CLI_NOT_FOUND)
            return False

        return self.cli.login(email)

    async def setup(self, email: Optional[str] = None) -> bool:
        """
        Complete setup flow: login, create space, generate tokens.

        Args:
            email: Optional email for login (prompts if not provided)

        Returns:
            bool: True if setup successful
        """
        if not self.cli.is_cli_installed():
            logger.error(StorageMessages.STORACHA_CLI_NOT_FOUND)
            return False

        # Check authentication
        if not self.cli.is_authenticated():
            if email:
                success = self.cli.login(email)
                if not success:
                    return False
            else:
                logger.error("Not authenticated. Run: mcli storage login <email>")
                return False

        # Check for space
        spaces = self.cli.list_spaces()
        if not spaces:
            logger.info("No spaces found, creating one...")
            space_did = self.cli.create_space("mcli-storage")
            if not space_did:
                return False
        else:
            current = self.cli.get_current_space()
            if not current:
                # Select first available space
                self.cli.select_space(spaces[0])

        # Generate bridge tokens
        self._bridge_tokens = self.cli.generate_bridge_tokens()
        return self._bridge_tokens is not None

    async def _store_encrypted(
        self, key: str, encrypted_data: bytes, metadata: dict[str, Any]
    ) -> str:
        """
        Store encrypted data on Storacha.

        Workflow:
        1. Generate CID from content
        2. Store in local cache
        3. Upload to Storacha (if enabled and authenticated)
        4. Upload registry file (for version tracking)

        Args:
            key: Data identifier
            encrypted_data: Already encrypted binary data
            metadata: Metadata dictionary

        Returns:
            str: Content identifier (CID)
        """
        # Generate CID
        cid = self.cache.generate_cid(encrypted_data)

        # Store locally first (cache)
        await self.cache.store(cid, encrypted_data, metadata)
        logger.debug(StorageMessages.CACHED_LOCALLY.format(cid=cid))

        # Upload to Storacha if enabled
        if self.enabled and await self.is_authenticated():
            try:
                # Generate filename
                timestamp = metadata.get("timestamp", datetime.utcnow().isoformat())
                filename = f"mcli-{key}-{timestamp}.encrypted"

                # Upload to Storacha
                uploaded_cid = await self._upload_to_storacha(encrypted_data, filename)

                logger.info(StorageMessages.UPLOADED_TO_STORACHA.format(cid=uploaded_cid))
                logger.info(
                    StorageMessages.GATEWAY_URL.format(
                        url=self.gateway_base.format(cid=uploaded_cid)
                    )
                )

                # Update metadata with Storacha CID
                metadata["storacha_cid"] = uploaded_cid
                await self.cache.update_metadata(cid, metadata)

                # Upload registry if repo context available
                repo_name = metadata.get("repo_name")
                environment = metadata.get("environment")
                if repo_name and environment:
                    try:
                        await self.registry.upload_registry(repo_name, environment, uploaded_cid)
                    except Exception as reg_error:
                        logger.debug(f"Registry upload failed: {reg_error}")

                return uploaded_cid

            except Exception as e:
                logger.warning(StorageMessages.STORACHA_UPLOAD_FAILED.format(error=str(e)))
                logger.warning(StorageMessages.DATA_CACHED_LOCALLY)
                return cid
        else:
            if not self.enabled:
                logger.debug(StorageMessages.USING_CACHE_ONLY)
            else:
                logger.debug(StorageMessages.NOT_AUTHENTICATED)
            return cid

    async def _retrieve_encrypted(self, storage_id: str) -> Optional[bytes]:
        """
        Retrieve encrypted data from cache or Storacha.

        Workflow:
        1. Try local cache first
        2. If not in cache, download from Storacha
        3. Cache downloaded data for future use

        Args:
            storage_id: CID to retrieve

        Returns:
            Optional[bytes]: Encrypted data, or None if not found
        """
        # Try local cache first
        cached_data = await self.cache.retrieve(storage_id)
        if cached_data:
            logger.debug(f"Retrieved from local cache: {storage_id}")
            return cached_data

        # Try downloading from Storacha
        if self.enabled and await self.is_authenticated():
            try:
                logger.info(StorageMessages.DOWNLOADED_FROM_STORACHA.format(cid=storage_id))
                data = await self._download_from_storacha(storage_id)

                # Cache for future use
                await self.cache.store(storage_id, data, {})
                logger.info("Downloaded and cached from Storacha")

                return data

            except Exception as e:
                logger.error(
                    StorageMessages.GATEWAY_DOWNLOAD_FAILED.format(cid=storage_id, error=str(e))
                )
                return None

        logger.error(StorageMessages.DATA_NOT_FOUND.format(cid=storage_id))
        return None

    async def _upload_to_storacha(self, data: bytes, filename: str) -> str:
        """
        Upload file to Storacha and return CID.

        Uses the Storacha CLI for upload (most reliable method).
        Falls back to HTTP bridge API if CLI upload fails.

        Args:
            data: Binary data to upload
            filename: File name

        Returns:
            str: Content identifier (CID)

        Raises:
            Exception: If upload fails
        """
        # Method 1: Use CLI upload (most reliable)
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=f"_{filename}", delete=False
        ) as tmp_file:
            tmp_file.write(data)
            tmp_path = Path(tmp_file.name)

        try:
            cid = self.cli.upload_file(tmp_path)
            if cid:
                return cid

            # CLI upload failed, try HTTP bridge
            logger.debug("CLI upload failed, trying HTTP bridge API")
            return await self._upload_via_http_bridge(data, filename)

        finally:
            # Clean up temp file
            try:
                tmp_path.unlink()
            except Exception:
                pass

    async def _upload_via_http_bridge(self, data: bytes, filename: str) -> str:
        """
        Upload file via HTTP bridge API.

        Uses the UCAN-HTTP bridge at up.storacha.network/bridge.

        Args:
            data: Binary data to upload
            filename: File name

        Returns:
            str: Content identifier (CID)

        Raises:
            Exception: If upload fails
        """
        # Ensure we have valid tokens
        if not self._bridge_tokens or self._bridge_tokens.is_expired():
            self._bridge_tokens = self.cli.get_bridge_tokens(auto_refresh=True)

        if not self._bridge_tokens:
            raise Exception("No valid bridge tokens available")

        # The HTTP bridge uses a specific UCAN invocation format
        # For now, we'll use the simpler approach of generating a CID locally
        # and using the CLI for actual uploads

        # Generate CID locally (content-addressed) - unused but kept for future HTTP bridge impl
        _cid = self._generate_cid_from_data(data)  # noqa: F841

        # For HTTP bridge, we'd need to implement the full UCAN invocation protocol
        # This is complex and requires CAR encoding, IPLD DAGs, etc.
        # For MVP, we rely on CLI upload

        raise NotImplementedError("HTTP bridge direct upload not implemented. Use CLI upload.")

    def _generate_cid_from_data(self, data: bytes) -> str:
        """
        Generate IPFS-compatible CID from data.

        Args:
            data: Binary data

        Returns:
            str: Content identifier (CID)
        """
        hash_hex = hashlib.sha256(data).hexdigest()
        return f"bafkrei{hash_hex[:52]}"

    async def _download_from_storacha(self, cid: str, timeout: Optional[int] = None) -> bytes:
        """
        Download file from Storacha IPFS gateway.

        Args:
            cid: Content identifier
            timeout: Optional timeout in seconds (default: 30)

        Returns:
            bytes: File contents

        Raises:
            httpx.HTTPError: If download fails
        """
        gateway_url = self.gateway_base.format(cid=cid)

        try:
            response = await self.client.get(
                gateway_url, timeout=timeout or StorageDefaults.DOWNLOAD_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as e:
            logger.error(StorageMessages.GATEWAY_DOWNLOAD_FAILED.format(cid=cid, error=str(e)))
            raise

    async def delete(self, storage_id: str) -> bool:
        """
        Delete from local cache.

        Note: IPFS data is immutable and cannot be deleted from the network,
        but we can remove it from our local cache.

        Args:
            storage_id: CID to delete

        Returns:
            bool: True if deletion successful
        """
        return await self.cache.delete(storage_id)

    async def query(
        self, filters: dict[str, Any], limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Query metadata (IPFS doesn't support queries directly).

        Uses local metadata cache for queries.

        Args:
            filters: Filter criteria
            limit: Maximum results
            offset: Skip results

        Returns:
            List[Dict[str, Any]]: Matching records
        """
        return await self.cache.query_metadata(filters, limit, offset)

    async def get_metadata(self, storage_id: str) -> Optional[dict[str, Any]]:
        """
        Get metadata for storage ID.

        Args:
            storage_id: CID

        Returns:
            Optional[Dict[str, Any]]: Metadata dictionary
        """
        return await self.cache.get_metadata(storage_id)

    async def list_all(self, prefix: Optional[str] = None, limit: int = 100) -> list[str]:
        """
        List all cached CIDs.

        Args:
            prefix: Optional prefix filter
            limit: Maximum results

        Returns:
            List[str]: List of CIDs
        """
        cids = await self.cache.list_all(prefix)
        return cids[:limit]

    async def list_recent_uploads(self, limit: int = 20) -> list[str]:
        """
        List recent uploads from Storacha.

        Args:
            limit: Maximum number of uploads to return

        Returns:
            List[str]: List of recent CIDs
        """
        uploads = self.cli.list_uploads(limit=limit)
        return [u.get("cid", "") for u in uploads if u.get("cid")]

    def enable(self) -> None:
        """Enable Storacha network sync."""
        self.enabled = True
        self.cli.config["enabled"] = True
        self.cli._save_config()
        logger.info(StorageMessages.STORACHA_ENABLED)

    def disable(self) -> None:
        """Disable Storacha network sync (use local cache only)."""
        self.enabled = False
        self.cli.config["enabled"] = False
        self.cli._save_config()
        logger.info(StorageMessages.STORACHA_DISABLED)

    def get_status(self) -> dict[str, Any]:
        """
        Get current backend status.

        Returns:
            Dict[str, Any]: Status information
        """
        cli_status = self.cli.get_status()
        cache_stats = self.cache.get_stats()

        return {
            "enabled": self.enabled,
            "connected": self._connected,
            "cli": cli_status,
            "cache": cache_stats,
            "has_tokens": bool(self._bridge_tokens and not self._bridge_tokens.is_expired()),
            "bridge_url": self.bridge_url,
            "gateway_base": self.gateway_base,
        }
