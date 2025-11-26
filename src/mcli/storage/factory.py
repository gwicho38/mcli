"""
Factory for creating storage backend instances.

Provides a convenient interface for getting the appropriate storage backend
based on environment configuration.
"""

import os
from enum import Enum
from typing import Optional

from mcli.lib.logger import get_logger
from mcli.storage.base import StorageBackend

logger = get_logger(__name__)


class StorageBackendType(Enum):
    """Supported storage backend types."""

    IPFS = "ipfs"  # Storacha/IPFS (default)
    SUPABASE = "supabase"  # Supabase (legacy)
    SQLITE = "sqlite"  # Local SQLite (fallback)


def get_storage_backend(
    backend_type: Optional[StorageBackendType] = None,
    encryption_key: Optional[str] = None,
) -> StorageBackend:
    """
    Get storage backend instance.

    Args:
        backend_type: Type of backend to create (defaults to env var STORAGE_BACKEND)
        encryption_key: Encryption key (defaults to env var MCLI_ENCRYPTION_KEY)

    Returns:
        StorageBackend: Configured storage backend instance

    Environment Variables:
        STORAGE_BACKEND: Backend type (ipfs, supabase, sqlite) - default: ipfs
        MCLI_ENCRYPTION_KEY: Master encryption key

    Example:
        # Get default backend (IPFS/Storacha)
        storage = get_storage_backend()

        # Get specific backend
        storage = get_storage_backend(StorageBackendType.IPFS)

        # With custom encryption key
        storage = get_storage_backend(encryption_key="my-secret-key")
    """
    # Determine backend type
    if backend_type is None:
        backend_str = os.getenv("STORAGE_BACKEND", "ipfs").lower()
        try:
            backend_type = StorageBackendType(backend_str)
        except ValueError:
            logger.warning(f"Invalid STORAGE_BACKEND: {backend_str}, defaulting to IPFS")
            backend_type = StorageBackendType.IPFS

    # Get encryption key
    if encryption_key is None:
        encryption_key = os.getenv("MCLI_ENCRYPTION_KEY")
        if not encryption_key:
            logger.warning(
                "No MCLI_ENCRYPTION_KEY found, generating random key.\n"
                "💡 Set MCLI_ENCRYPTION_KEY to use the same key across sessions."
            )
            # Generate random key
            from mcli.storage.encryption import generate_encryption_key

            encryption_key = generate_encryption_key()

    # Create backend
    if backend_type == StorageBackendType.IPFS:
        from mcli.storage.backends.ipfs_backend import StorachaBackend

        logger.info("Using IPFS/Storacha storage backend")
        return StorachaBackend(encryption_key)

    elif backend_type == StorageBackendType.SUPABASE:
        # TODO: Implement Supabase backend (refactored from existing code)
        raise NotImplementedError(
            "Supabase backend not yet implemented.\n"
            "📝 TODO: Refactor existing Supabase code to use storage abstraction"
        )

    elif backend_type == StorageBackendType.SQLITE:
        # TODO: Implement SQLite backend (local fallback)
        raise NotImplementedError(
            "SQLite backend not yet implemented.\n" "📝 TODO: Create local SQLite storage backend"
        )

    else:
        raise ValueError(f"Unknown backend type: {backend_type}")


async def get_default_storage() -> StorageBackend:
    """
    Get default storage backend and connect.

    Convenience function that creates backend and establishes connection.

    Returns:
        StorageBackend: Connected storage backend

    Raises:
        Exception: If connection fails

    Example:
        storage = await get_default_storage()
        cid = await storage.store("my-key", data, metadata)
    """
    backend = get_storage_backend()
    connected = await backend.connect()

    if not connected:
        logger.warning("Failed to connect to storage backend, using cache-only mode")

    return backend
