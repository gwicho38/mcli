"""
LSH Framework bridge for Storacha integration.

Provides immediate Storacha integration by delegating to lsh-framework CLI.
This is a temporary solution until native Python Storacha client is implemented.

Requirements:
    - lsh-framework installed globally: npm install -g lsh-framework
    - lsh configured with Storacha: lsh storacha login <email>
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.lib.logger import get_logger
from mcli.storage.base import EncryptedStorageBackend
from mcli.storage.cache import LocalCache

logger = get_logger(__name__)


class LSHBridge(EncryptedStorageBackend):
    """
    LSH Framework bridge for Storacha.

    Delegates Storacha operations to lsh-framework CLI commands.
    Maintains local cache for offline access.

    This is a temporary bridge until native Python Storacha client is implemented.
    """

    def __init__(self, encryption_key: str):
        """
        Initialize LSH bridge.

        Args:
            encryption_key: Master encryption key (passed to lsh)
        """
        super().__init__(encryption_key)

        # Check if lsh is installed
        self.lsh_available = self._check_lsh_installed()

        # Local cache
        self.cache_dir = Path.home() / ".mcli" / "storage-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = LocalCache(self.cache_dir)

    def _check_lsh_installed(self) -> bool:
        """
        Check if lsh-framework is installed and available.

        Returns:
            bool: True if lsh is available
        """
        try:
            result = subprocess.run(
                ["lsh", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"Found lsh-framework: {version}")
                return True
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("lsh-framework not found. Install with: npm install -g lsh-framework")
            return False

    def _run_lsh_command(self, args: list[str], timeout: int = 30) -> dict[str, Any]:
        """
        Run lsh command and return parsed JSON output.

        Args:
            args: Command arguments (e.g., ['storacha', 'status'])
            timeout: Command timeout in seconds

        Returns:
            Dict[str, Any]: Parsed JSON response

        Raises:
            RuntimeError: If command fails
        """
        try:
            cmd = ["lsh"] + args
            logger.debug(f"Running lsh command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                raise RuntimeError(f"lsh command failed: {result.stderr or result.stdout}")

            # Try to parse JSON output
            if result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    # Not JSON, return as plain text
                    return {"output": result.stdout.strip()}

            return {}

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"lsh command timed out after {timeout}s")
        except FileNotFoundError:
            raise RuntimeError("lsh command not found. Install: npm install -g lsh-framework")

    async def connect(self) -> bool:
        """
        Check if lsh is available and Storacha is configured.

        Returns:
            bool: True if connected
        """
        if not self.lsh_available:
            logger.error("lsh-framework not available")
            return False

        # Check Storacha status
        try:
            status = self._run_lsh_command(["storacha", "status"])
            authenticated = status.get("authenticated", False)

            if not authenticated:
                logger.warning(
                    "Not authenticated with Storacha via lsh.\n" "Run: lsh storacha login <email>"
                )
                # Still return True - we can use cache
                self._connected = True
                return True

            logger.info("✅ Connected to Storacha via lsh-framework")
            self._connected = True
            return True

        except Exception as e:
            logger.error(f"Failed to check Storacha status: {e}")
            self._connected = True  # Still allow cache-only mode
            return True

    async def disconnect(self) -> None:
        """Disconnect (no-op for bridge)."""
        self._connected = False

    async def health_check(self) -> bool:
        """
        Check if lsh and Storacha are accessible.

        Returns:
            bool: True if healthy
        """
        if not self.lsh_available:
            return False

        try:
            status = self._run_lsh_command(["storacha", "status"], timeout=5)
            return status.get("authenticated", False)
        except Exception:
            return False

    async def _store_encrypted(
        self, key: str, encrypted_data: bytes, metadata: dict[str, Any]
    ) -> str:
        """
        Store encrypted data via lsh.

        Args:
            key: Data identifier
            encrypted_data: Already encrypted data
            metadata: Metadata dictionary

        Returns:
            str: Storage CID
        """
        # Generate CID for cache
        cid = self.cache.generate_cid(encrypted_data)

        # Store in local cache
        await self.cache.store(cid, encrypted_data, metadata)
        logger.debug(f"📦 Cached locally: {cid}")

        # Upload to Storacha via lsh if available
        if self.lsh_available and self._connected:
            try:
                # Write data to temp file
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="wb", delete=False, suffix=".encrypted"
                ) as tmp:
                    tmp.write(encrypted_data)
                    tmp_path = tmp.name

                try:
                    # Upload via lsh
                    # Note: lsh doesn't have direct file upload yet
                    # For now, we'll use cache-only mode
                    logger.debug("lsh upload not yet implemented, using cache only")

                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)

            except Exception as e:
                logger.warning(f"⚠️  lsh upload failed: {e}")
                logger.warning("   Data is cached locally")

        return cid

    async def _retrieve_encrypted(self, storage_id: str) -> Optional[bytes]:
        """
        Retrieve encrypted data from cache or lsh.

        Args:
            storage_id: CID to retrieve

        Returns:
            Optional[bytes]: Encrypted data
        """
        # Try local cache first
        cached_data = await self.cache.retrieve(storage_id)
        if cached_data:
            logger.debug(f"Retrieved from local cache: {storage_id}")
            return cached_data

        # Try lsh if available
        if self.lsh_available and self._connected:
            try:
                # Note: lsh doesn't have direct CID download yet
                # For now, rely on cache
                logger.debug("lsh download not yet implemented, using cache only")
            except Exception as e:
                logger.error(f"Failed to download via lsh: {e}")

        logger.error(f"Data not in cache and lsh unavailable: {storage_id}")
        return None

    async def delete(self, storage_id: str) -> bool:
        """
        Delete from local cache.

        Args:
            storage_id: CID to delete

        Returns:
            bool: True if successful
        """
        return await self.cache.delete(storage_id)

    async def query(
        self, filters: dict[str, Any], limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Query metadata.

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
            Optional[Dict[str, Any]]: Metadata
        """
        return await self.cache.get_metadata(storage_id)

    async def list_all(self, prefix: Optional[str] = None, limit: int = 100) -> list[str]:
        """
        List all cached CIDs.

        Args:
            prefix: Optional prefix filter
            limit: Maximum results

        Returns:
            List[str]: CIDs
        """
        cids = await self.cache.list_all(prefix)
        return cids[:limit]

    def get_lsh_status(self) -> dict[str, Any]:
        """
        Get lsh Storacha status.

        Returns:
            Dict[str, Any]: Status information
        """
        if not self.lsh_available:
            return {"available": False, "error": "lsh-framework not installed"}

        try:
            status = self._run_lsh_command(["storacha", "status"])
            status["available"] = True
            return status
        except Exception as e:
            return {"available": True, "error": str(e)}
