"""
IPFS/Storacha storage backend implementation.

Based on lsh-framework TypeScript implementation at ~/repos/lsh.
Provides decentralized storage via Storacha network (formerly web3.storage).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from mcli.lib.logger import get_logger
from mcli.storage.base import EncryptedStorageBackend
from mcli.storage.cache import LocalCache
from mcli.storage.registry import RegistryManager

logger = get_logger(__name__)


class StorachaBackend(EncryptedStorageBackend):
    """
    Storacha/IPFS storage backend.

    Features:
    - Stores encrypted data on IPFS via Storacha
    - Local caching for offline access
    - Registry system for version tracking
    - Email-based authentication
    - Graceful fallback (cache → network → error)

    Based on lsh-framework implementation:
    - dist/lib/storacha-client.js
    - dist/lib/ipfs-secrets-storage.js

    Environment Variables:
        MCLI_STORACHA_ENABLED: Enable network sync (default: true)
        STORACHA_EMAIL: User email for authentication
        STORACHA_SPACE_DID: Space DID (assigned after login)
    """

    def __init__(self, encryption_key: str):
        """
        Initialize Storacha backend.

        Args:
            encryption_key: Master encryption key for AES-256
        """
        super().__init__(encryption_key)

        # Configuration
        self.enabled = os.getenv("MCLI_STORACHA_ENABLED", "true").lower() == "true"

        # API endpoints (TODO: Update with actual Storacha API endpoints)
        # These are placeholders - need to be filled in based on Storacha docs
        self.api_base = "https://api.storacha.network"
        self.gateway_base = "https://{cid}.ipfs.storacha.link"

        # Local directories
        self.cache_dir = Path.home() / ".mcli" / "storage-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = Path.home() / ".mcli" / "storacha-config.json"

        # Components
        self.cache = LocalCache(self.cache_dir)
        self.registry = RegistryManager(self)

        # Load config
        self.config = self._load_config()

        # HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)

    def _load_config(self) -> Dict[str, Any]:
        """
        Load Storacha configuration from disk.

        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        if self.config_path.exists():
            try:
                content = self.config_path.read_text()
                return json.loads(content)
            except Exception as e:
                logger.warning(f"Failed to load Storacha config: {e}")

        return {"enabled": self.enabled}

    def _save_config(self) -> None:
        """Save Storacha configuration to disk."""
        try:
            content = json.dumps(self.config, indent=2)
            self.config_path.write_text(content)
        except Exception as e:
            logger.error(f"Failed to save Storacha config: {e}")

    async def connect(self) -> bool:
        """
        Establish connection to Storacha.

        Returns:
            bool: True if connected (or disabled), False if authentication required
        """
        if not self.enabled:
            logger.info("Storacha is disabled, using local cache only")
            self._connected = True
            return True

        authenticated = await self.is_authenticated()
        if not authenticated:
            logger.warning("Not authenticated with Storacha. Run: mcli storage login <email>")
            # Still return True - we can use local cache
            self._connected = True
            return True

        self._connected = True
        logger.info("✅ Connected to Storacha")
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
            # TODO: Replace with actual Storacha health endpoint
            response = await self.client.get(f"{self.api_base}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    async def is_authenticated(self) -> bool:
        """
        Check if user is authenticated with Storacha.

        Returns:
            bool: True if authenticated
        """
        # TODO: Implement based on Storacha API
        # For now, check if we have stored credentials
        return "email" in self.config and "space_did" in self.config

    async def login(self, email: str) -> None:
        """
        Login with email (triggers email verification).

        Based on lsh-framework implementation:
        1. Send verification email
        2. Wait for email confirmation
        3. Wait for payment plan selection
        4. Create default space if needed

        Args:
            email: User email address

        Raises:
            NotImplementedError: Storacha API integration not yet complete
        """
        logger.info(f"📧 Sending verification email to {email}...")
        logger.info("   Click the link in your email to complete authentication.")

        # TODO: Implement Storacha authentication flow
        # This will require:
        # 1. POST to Storacha API with email
        # 2. Poll for email verification
        # 3. Wait for plan selection
        # 4. Create/select space

        raise NotImplementedError(
            "Storacha login not yet implemented.\n\n"
            "📝 TODO: Implement Storacha HTTP API client\n"
            "   See: https://docs.storacha.network/how-to/http-bridge/\n\n"
            "💡 Alternative: Use lsh-framework for now:\n"
            "   1. cd ~/repos/lsh\n"
            f"   2. lsh storacha login {email}\n"
            "   3. Copy credentials to MCLI config"
        )

    async def _store_encrypted(
        self, key: str, encrypted_data: bytes, metadata: Dict[str, Any]
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
        logger.debug(f"📦 Cached locally: {cid}")

        # Upload to Storacha if enabled
        if self.enabled and await self.is_authenticated():
            try:
                # Generate filename
                timestamp = metadata.get("timestamp", "unknown")
                filename = f"mcli-{key}-{timestamp}.encrypted"

                # Upload to Storacha
                uploaded_cid = await self._upload_to_storacha(encrypted_data, filename)

                logger.info(f"📤 Uploaded to Storacha: {uploaded_cid}")
                logger.info(f"   Gateway: {self.gateway_base.format(cid=uploaded_cid)}")

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
                logger.warning(f"⚠️  Storacha upload failed: {e}")
                logger.warning("   Data is cached locally")
                return cid
        else:
            if not self.enabled:
                logger.debug("Storacha disabled, using local cache only")
            else:
                logger.debug("Not authenticated, using local cache only")
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
                logger.info(f"📥 Downloading from Storacha: {storage_id}...")
                data = await self._download_from_storacha(storage_id)

                # Cache for future use
                await self.cache.store(storage_id, data, {})
                logger.info(f"✅ Downloaded and cached from Storacha")

                return data

            except Exception as e:
                logger.error(f"Failed to download from Storacha: {e}")
                return None

        logger.error(f"Data not in cache and Storacha unavailable: {storage_id}")
        return None

    async def _upload_to_storacha(self, data: bytes, filename: str) -> str:
        """
        Upload file to Storacha and return CID.

        TODO: Implement using Storacha HTTP API
        Based on @storacha/client uploadFile() method

        Args:
            data: Binary data to upload
            filename: File name

        Returns:
            str: Content identifier (CID)

        Raises:
            NotImplementedError: Storacha API integration not yet complete
        """
        # TODO: Implement Storacha upload API
        # Reference: lsh-framework storacha-client.js upload() method
        #
        # Steps:
        # 1. Convert data to File/multipart format
        # 2. POST to Storacha upload endpoint
        # 3. Parse CID from response
        # 4. Return CID

        raise NotImplementedError(
            "Storacha upload not yet implemented.\n\n"
            "📝 TODO: Implement Storacha HTTP API upload\n"
            "   See: https://docs.storacha.network/how-to/http-bridge/"
        )

    async def _download_from_storacha(
        self, cid: str, timeout: Optional[int] = None
    ) -> bytes:
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
            response = await self.client.get(gateway_url, timeout=timeout or 30)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Gateway download failed for {cid}: {e}")
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
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
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

    async def get_metadata(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for storage ID.

        Args:
            storage_id: CID

        Returns:
            Optional[Dict[str, Any]]: Metadata dictionary
        """
        return await self.cache.get_metadata(storage_id)

    async def list_all(self, prefix: Optional[str] = None, limit: int = 100) -> List[str]:
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

    async def list_recent_uploads(self, limit: int = 20) -> List[str]:
        """
        List recent uploads from Storacha.

        TODO: Implement using Storacha API

        Args:
            limit: Maximum number of uploads to return

        Returns:
            List[str]: List of recent CIDs

        Raises:
            NotImplementedError: Storacha API integration not yet complete
        """
        # TODO: Implement using Storacha capability.upload.list()
        # Reference: lsh-framework storacha-client.js checkRegistry() method

        raise NotImplementedError("Storacha list uploads not yet implemented")

    def enable(self) -> None:
        """Enable Storacha network sync."""
        self.enabled = True
        self.config["enabled"] = True
        self._save_config()
        logger.info("✅ Storacha network sync enabled")

    def disable(self) -> None:
        """Disable Storacha network sync (use local cache only)."""
        self.enabled = False
        self.config["enabled"] = False
        self._save_config()
        logger.info("⏸️  Storacha network sync disabled (using local cache only)")
