"""
Storage abstraction layer for MCLI.

Provides a unified interface for different storage backends:
- IPFS/Storacha (default) - Decentralized storage
- Supabase (legacy) - Centralized database
- SQLite (fallback) - Local storage

Example:
    from mcli.storage import get_storage_backend

    # Get default backend (IPFS/Storacha)
    storage = await get_storage_backend()

    # Store data
    cid = await storage.store("my-key", data, metadata)

    # Retrieve data
    data = await storage.retrieve(cid)
"""

from mcli.storage.base import EncryptedStorageBackend, StorageBackend
from mcli.storage.factory import StorageBackendType, get_storage_backend

__all__ = [
    "StorageBackend",
    "EncryptedStorageBackend",
    "get_storage_backend",
    "StorageBackendType",
]
