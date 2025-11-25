"""
Abstract base classes for storage backends.

Defines the interface that all storage backends must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcli.lib.logger import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    All storage backends must implement these methods to provide
    a consistent interface for data storage and retrieval.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to storage backend.

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage backend."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if backend is healthy and accessible.

        Returns:
            bool: True if backend is healthy, False otherwise
        """
        pass

    # Data operations
    @abstractmethod
    async def store(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store data and return storage ID (CID/UUID/etc).

        Args:
            key: Identifier for the data
            data: Binary data to store
            metadata: Optional metadata dictionary

        Returns:
            str: Storage ID (e.g., IPFS CID, database UUID)
        """
        pass

    @abstractmethod
    async def retrieve(self, storage_id: str) -> Optional[bytes]:
        """
        Retrieve data by storage ID.

        Args:
            storage_id: Storage identifier (CID, UUID, etc)

        Returns:
            Optional[bytes]: Retrieved data, or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, storage_id: str) -> bool:
        """
        Delete data by storage ID.

        Args:
            storage_id: Storage identifier to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass

    # Query operations (for structured data)
    @abstractmethod
    async def query(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query structured data with filters.

        Args:
            filters: Dictionary of filter criteria
            limit: Maximum number of results to return
            offset: Number of results to skip (pagination)

        Returns:
            List[Dict[str, Any]]: List of matching records
        """
        pass

    # Metadata operations
    @abstractmethod
    async def get_metadata(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for storage ID.

        Args:
            storage_id: Storage identifier

        Returns:
            Optional[Dict[str, Any]]: Metadata dictionary, or None if not found
        """
        pass

    @abstractmethod
    async def list_all(self, prefix: Optional[str] = None, limit: int = 100) -> List[str]:
        """
        List all storage IDs, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter by
            limit: Maximum number of IDs to return

        Returns:
            List[str]: List of storage IDs
        """
        pass

    # Utility methods
    def is_connected(self) -> bool:
        """
        Check if backend is currently connected.

        Returns:
            bool: True if connected, False otherwise
        """
        return False


class EncryptedStorageBackend(StorageBackend):
    """
    Storage backend with built-in encryption.

    Automatically encrypts data before storing and decrypts when retrieving.
    Uses AES-256-CBC encryption (same as lsh-framework).
    """

    def __init__(self, encryption_key: str):
        """
        Initialize encrypted storage backend.

        Args:
            encryption_key: Master encryption key for AES-256
        """
        self.encryption_key = encryption_key
        self._connected = False

    async def store(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Encrypt data before storing.

        Args:
            key: Identifier for the data
            data: Binary data to store (will be encrypted)
            metadata: Optional metadata dictionary

        Returns:
            str: Storage ID of encrypted data
        """
        # Import here to avoid circular dependency
        from mcli.storage.encryption import encrypt_data

        encrypted_data = encrypt_data(data, self.encryption_key)

        # Add encryption metadata
        if metadata is None:
            metadata = {}
        metadata["encrypted"] = True
        metadata["encryption_algorithm"] = "AES-256-CBC"
        metadata["encrypted_at"] = datetime.utcnow().isoformat()

        return await self._store_encrypted(key, encrypted_data, metadata)

    async def retrieve(self, storage_id: str) -> Optional[bytes]:
        """
        Retrieve and decrypt data.

        Args:
            storage_id: Storage identifier

        Returns:
            Optional[bytes]: Decrypted data, or None if not found
        """
        encrypted_data = await self._retrieve_encrypted(storage_id)
        if encrypted_data is None:
            return None

        # Import here to avoid circular dependency
        from mcli.storage.encryption import decrypt_data

        try:
            return decrypt_data(encrypted_data, self.encryption_key)
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            return None

    @abstractmethod
    async def _store_encrypted(
        self, key: str, encrypted_data: bytes, metadata: Dict[str, Any]
    ) -> str:
        """
        Backend-specific encrypted storage implementation.

        Args:
            key: Identifier for the data
            encrypted_data: Already encrypted binary data
            metadata: Metadata dictionary (includes encryption info)

        Returns:
            str: Storage ID
        """
        pass

    @abstractmethod
    async def _retrieve_encrypted(self, storage_id: str) -> Optional[bytes]:
        """
        Backend-specific encrypted retrieval implementation.

        Args:
            storage_id: Storage identifier

        Returns:
            Optional[bytes]: Encrypted data, or None if not found
        """
        pass

    def is_connected(self) -> bool:
        """Check if backend is connected."""
        return self._connected
