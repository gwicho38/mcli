# Storage Abstraction Layer Design

**Status:** Planning Phase
**Created:** 2025-11-25
**Issue:** [#117](https://github.com/gwicho38/mcli/issues/117)

## Overview

Design document for replacing Supabase with IPFS/Storacha as the default storage backend in MCLI, while maintaining a clean abstraction layer for multiple storage backends.

## Goals

1. **Replace Supabase with IPFS/Storacha** as default storage
2. **Maintain backward compatibility** with existing Supabase users
3. **Create storage abstraction** for easy backend swapping
4. **Port lsh-framework patterns** to Python

## Reference Implementation

The lsh-framework (TypeScript) provides an excellent reference implementation:
- **Location:** `~/repos/lsh`
- **Package:** `@storacha/client` v1.8.18
- **Files:** `storacha-client.js`, `ipfs-secrets-storage.js`

### Key Patterns from lsh-framework

1. **Storacha Client Wrapper**
   - Email-based authentication with verification flow
   - Space management for data organization
   - Upload returns CID, download via IPFS gateway
   - Registry pattern for version tracking

2. **Storage Layer**
   - AES-256-CBC encryption before upload
   - Local caching in `~/.lsh/secrets-cache/`
   - Metadata tracking in `~/.lsh/secrets-metadata.json`
   - Graceful fallbacks: cache → network → error

3. **Configuration**
   - `LSH_STORACHA_ENABLED` - Toggle network sync
   - Config file: `~/.lsh/storacha-config.json`
   - Default: enabled unless explicitly disabled

## Architecture Design

### Module Structure

```
src/mcli/storage/
├── __init__.py                 # Public API exports
├── base.py                     # Abstract base classes
├── backends/
│   ├── __init__.py
│   ├── ipfs_backend.py         # Storacha/IPFS implementation
│   ├── supabase_backend.py     # Refactored Supabase code
│   └── sqlite_backend.py       # Local SQLite fallback
├── cache.py                    # Local caching layer
├── encryption.py               # AES-256 encryption utilities
└── registry.py                 # Version registry system
```

### Abstract Base Classes

```python
# src/mcli/storage/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to storage backend."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage backend."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is healthy and accessible."""
        pass

    # Data operations
    @abstractmethod
    async def store(self, key: str, data: bytes, metadata: Dict[str, Any]) -> str:
        """Store data and return storage ID (CID/UUID)."""
        pass

    @abstractmethod
    async def retrieve(self, storage_id: str) -> Optional[bytes]:
        """Retrieve data by storage ID."""
        pass

    @abstractmethod
    async def delete(self, storage_id: str) -> bool:
        """Delete data by storage ID."""
        pass

    # Query operations (for structured data)
    @abstractmethod
    async def query(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query structured data with filters."""
        pass

    # Metadata operations
    @abstractmethod
    async def get_metadata(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for storage ID."""
        pass

    @abstractmethod
    async def list_all(self, prefix: Optional[str] = None) -> List[str]:
        """List all storage IDs, optionally filtered by prefix."""
        pass


class EncryptedStorageBackend(StorageBackend):
    """Storage backend with built-in encryption."""

    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key

    async def store(self, key: str, data: bytes, metadata: Dict[str, Any]) -> str:
        """Encrypt data before storing."""
        encrypted_data = self._encrypt(data)
        return await self._store_encrypted(key, encrypted_data, metadata)

    async def retrieve(self, storage_id: str) -> Optional[bytes]:
        """Retrieve and decrypt data."""
        encrypted_data = await self._retrieve_encrypted(storage_id)
        if encrypted_data:
            return self._decrypt(encrypted_data)
        return None

    @abstractmethod
    async def _store_encrypted(self, key: str, encrypted_data: bytes, metadata: Dict[str, Any]) -> str:
        """Backend-specific encrypted storage."""
        pass

    @abstractmethod
    async def _retrieve_encrypted(self, storage_id: str) -> Optional[bytes]:
        """Backend-specific encrypted retrieval."""
        pass

    def _encrypt(self, data: bytes) -> bytes:
        """AES-256-CBC encryption."""
        # Implementation in encryption.py
        pass

    def _decrypt(self, encrypted_data: bytes) -> bytes:
        """AES-256-CBC decryption."""
        # Implementation in encryption.py
        pass
```

### IPFS/Storacha Backend

```python
# src/mcli/storage/backends/ipfs_backend.py

import os
import json
import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.storage.base import EncryptedStorageBackend
from mcli.storage.cache import LocalCache
from mcli.storage.registry import RegistryManager
from mcli.lib.logger import get_logger

logger = get_logger(__name__)


class StorachaBackend(EncryptedStorageBackend):
    """
    Storacha/IPFS storage backend.

    Based on lsh-framework implementation:
    - Stores encrypted data on IPFS via Storacha
    - Local caching for offline access
    - Registry system for version tracking
    - Email-based authentication
    """

    def __init__(self, encryption_key: str):
        super().__init__(encryption_key)

        self.enabled = os.getenv("MCLI_STORACHA_ENABLED", "true").lower() == "true"
        self.api_base = "https://api.storacha.network"  # Placeholder - actual API TBD
        self.gateway_base = "https://{cid}.ipfs.storacha.link"

        # Local cache directory
        self.cache_dir = Path.home() / ".mcli" / "storage-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file
        self.metadata_path = Path.home() / ".mcli" / "storage-metadata.json"

        # Components
        self.cache = LocalCache(self.cache_dir)
        self.registry = RegistryManager(self)

        # Load config
        self.config_path = Path.home() / ".mcli" / "storacha-config.json"
        self.config = self._load_config()

        # HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)

    def _load_config(self) -> Dict[str, Any]:
        """Load Storacha configuration."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text())
            except Exception as e:
                logger.warning(f"Failed to load Storacha config: {e}")

        return {"enabled": self.enabled}

    def _save_config(self) -> None:
        """Save Storacha configuration."""
        try:
            self.config_path.write_text(json.dumps(self.config, indent=2))
        except Exception as e:
            logger.error(f"Failed to save Storacha config: {e}")

    async def connect(self) -> bool:
        """Check authentication status."""
        if not self.enabled:
            logger.info("Storacha is disabled, using local cache only")
            return True

        return await self.is_authenticated()

    async def disconnect(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """Check if Storacha is accessible."""
        if not self.enabled:
            return True

        try:
            response = await self.client.get(f"{self.api_base}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def is_authenticated(self) -> bool:
        """Check if user is authenticated with Storacha."""
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
        """
        logger.info(f"📧 Sending verification email to {email}...")

        # TODO: Implement Storacha authentication flow
        # This will require:
        # 1. POST to Storacha API with email
        # 2. Poll for email verification
        # 3. Wait for plan selection
        # 4. Create/select space

        # For now, placeholder
        raise NotImplementedError("Storacha login not yet implemented")

    async def _store_encrypted(self, key: str, encrypted_data: bytes, metadata: Dict[str, Any]) -> str:
        """Store encrypted data on Storacha."""

        # Generate filename
        filename = f"mcli-{key}-{metadata.get('timestamp', 'unknown')}.encrypted"

        # Store locally first (cache)
        cid = self.cache.generate_cid(encrypted_data)
        await self.cache.store(cid, encrypted_data, metadata)

        # Upload to Storacha if enabled
        if self.enabled and await self.is_authenticated():
            try:
                uploaded_cid = await self._upload_to_storacha(encrypted_data, filename)
                logger.info(f"📤 Uploaded to Storacha: {uploaded_cid}")
                logger.info(f"   Gateway: {self.gateway_base.format(cid=uploaded_cid)}")

                # Update metadata with Storacha CID
                metadata["storacha_cid"] = uploaded_cid
                await self.cache.update_metadata(cid, metadata)

                return uploaded_cid
            except Exception as e:
                logger.warning(f"⚠️  Storacha upload failed: {e}")
                logger.warning("   Data is cached locally")
                return cid
        else:
            logger.debug("Storacha disabled, using local cache only")
            return cid

    async def _retrieve_encrypted(self, storage_id: str) -> Optional[bytes]:
        """Retrieve encrypted data from cache or Storacha."""

        # Try local cache first
        cached_data = await self.cache.retrieve(storage_id)
        if cached_data:
            logger.debug(f"Retrieved from local cache: {storage_id}")
            return cached_data

        # Try downloading from Storacha
        if self.enabled:
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

        return None

    async def _upload_to_storacha(self, data: bytes, filename: str) -> str:
        """Upload file to Storacha and return CID."""
        # TODO: Implement Storacha upload API
        # Based on @storacha/client uploadFile() method
        raise NotImplementedError("Storacha upload not yet implemented")

    async def _download_from_storacha(self, cid: str) -> bytes:
        """Download file from Storacha IPFS gateway."""
        gateway_url = self.gateway_base.format(cid=cid)

        response = await self.client.get(gateway_url)
        response.raise_for_status()

        return response.content

    async def delete(self, storage_id: str) -> bool:
        """Delete from local cache (IPFS data is immutable)."""
        return await self.cache.delete(storage_id)

    async def query(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query metadata (IPFS doesn't support queries directly)."""
        # Use local metadata for queries
        return await self.cache.query_metadata(filters, limit)

    async def get_metadata(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for storage ID."""
        return await self.cache.get_metadata(storage_id)

    async def list_all(self, prefix: Optional[str] = None) -> List[str]:
        """List all cached CIDs."""
        return await self.cache.list_all(prefix)
```

## Configuration

### Environment Variables

```bash
# Storage backend selection
STORAGE_BACKEND=ipfs          # Options: ipfs, supabase, sqlite

# IPFS/Storacha configuration
MCLI_STORACHA_ENABLED=true    # Enable network sync (default: true)
STORACHA_EMAIL=user@example.com
STORACHA_SPACE_DID=did:key:xxx

# Encryption
MCLI_ENCRYPTION_KEY=your-encryption-key

# Supabase (legacy/optional)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx
```

### Migration Path

1. **Phase 1: Create abstraction layer** (Current phase)
   - Define base classes
   - Implement IPFS backend
   - Refactor Supabase to use abstraction

2. **Phase 2: Update consumers**
   - Modify `session.py` to use storage abstraction
   - Update dashboard to use storage abstraction
   - Update utilities

3. **Phase 3: Make IPFS default**
   - Change default from Supabase to IPFS
   - Update documentation
   - Create migration tool

4. **Phase 4: Data migration**
   - Export data from Supabase
   - Import to IPFS
   - Verify integrity

## Data Model Mapping

### Supabase → IPFS Translation

| Supabase | IPFS/Storacha | Strategy |
|----------|---------------|----------|
| Table rows | Individual files | Store each row as JSON file |
| SQL queries | Metadata search | Maintain local metadata index |
| Relationships | References (CIDs) | Store related CIDs in metadata |
| Real-time | Polling/PubSub | Implement polling or use IPFS PubSub |
| Transactions | Batch operations | Upload multiple files, track in registry |

### Example: Politician Trading Data

**Current (Supabase):**
```sql
SELECT * FROM trading_disclosures
WHERE politician_id = 'xxx'
ORDER BY disclosure_date DESC
LIMIT 10;
```

**New (IPFS):**
```python
# Each disclosure stored as individual file
# Metadata index maintained locally:
{
  "cid": "bafkreixxx",
  "type": "trading_disclosure",
  "politician_id": "xxx",
  "disclosure_date": "2024-01-01",
  "indexed_at": "2024-01-01T10:00:00Z"
}

# Query local metadata index
results = await storage.query({
    "type": "trading_disclosure",
    "politician_id": "xxx"
}, limit=10)

# Sort by date
results.sort(key=lambda x: x["disclosure_date"], reverse=True)
```

## Testing Strategy

1. **Unit Tests**
   - Test each backend independently
   - Test encryption/decryption
   - Test cache operations
   - Test registry operations

2. **Integration Tests**
   - Test with real Storacha API
   - Test fallback scenarios
   - Test migration tools

3. **Performance Tests**
   - Compare Supabase vs IPFS latency
   - Test cache effectiveness
   - Test bulk operations

## Timeline

- **Week 1:** Design abstraction layer (✅ Complete)
- **Week 2:** Implement IPFS backend skeleton
- **Week 3:** Implement Storacha API integration
- **Week 4:** Refactor existing code to use abstraction
- **Week 5:** Testing and documentation
- **Week 6:** Migration tools and rollout

## Related Issues

- Issue #117: Replace Supabase with IPFS/Storacha
- lsh-framework: Reference implementation

## References

- [Storacha Documentation](https://docs.storacha.network/)
- [IPFS Documentation](https://docs.ipfs.io/)
- [lsh-framework Source](https://github.com/gwicho38/lsh)
