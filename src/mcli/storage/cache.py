"""
Local cache layer for storage backends.

Provides local caching for offline access and performance optimization.
Mirrors lsh-framework's ~/.lsh/secrets-cache/ implementation.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.lib.logger import get_logger

logger = get_logger(__name__)


class LocalCache:
    """
    Local file-based cache for storage data.

    Features:
    - CID-based storage (content-addressed)
    - Metadata tracking
    - Query support via metadata index
    - Automatic cleanup

    Directory structure:
        ~/.mcli/storage-cache/
        ├── {cid}.data              # Cached data files
        └── metadata.json           # Metadata index
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize local cache.

        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = cache_dir / "metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        """Load metadata index from disk."""
        if not self.metadata_file.exists():
            return {}

        try:
            content = self.metadata_file.read_text()
            result: dict[str, dict[str, Any]] = json.loads(content)
            return result
        except Exception as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            return {}

    def _save_metadata(self) -> None:
        """Save metadata index to disk."""
        try:
            content = json.dumps(self.metadata, indent=2)
            self.metadata_file.write_text(content)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def generate_cid(self, data: bytes) -> str:
        """
        Generate IPFS-compatible CID from content.

        Matches lsh-framework implementation:
        - Uses SHA-256 hash of content
        - Formats as CIDv1: bafkrei{hash[:52]}

        Args:
            data: Binary data to hash

        Returns:
            str: Content identifier (CID)

        Example:
            cid = cache.generate_cid(b"hello world")
            # Returns: "bafkreixxx..."
        """
        hash_hex = hashlib.sha256(data).hexdigest()
        # Format as IPFS CIDv1 (bafkreixxx...)
        cid = f"bafkrei{hash_hex[:52]}"
        return cid

    async def store(self, cid: str, data: bytes, metadata: Optional[dict[str, Any]] = None) -> bool:
        """
        Store data in local cache.

        Args:
            cid: Content identifier
            data: Binary data to cache
            metadata: Optional metadata dictionary

        Returns:
            bool: True if storage successful
        """
        try:
            # Write data file
            cache_file = self.cache_dir / f"{cid}.data"
            cache_file.write_bytes(data)

            # Update metadata
            if metadata is None:
                metadata = {}

            metadata["cid"] = cid
            metadata["size"] = len(data)
            metadata["cached_at"] = datetime.utcnow().isoformat()

            self.metadata[cid] = metadata
            self._save_metadata()

            logger.debug(f"Cached {len(data)} bytes to {cache_file.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to store in cache: {e}")
            return False

    async def retrieve(self, cid: str) -> Optional[bytes]:
        """
        Retrieve data from local cache.

        Args:
            cid: Content identifier

        Returns:
            Optional[bytes]: Cached data, or None if not found
        """
        try:
            cache_file = self.cache_dir / f"{cid}.data"

            if not cache_file.exists():
                logger.debug(f"Cache miss: {cid}")
                return None

            data = cache_file.read_bytes()
            logger.debug(f"Cache hit: {cid} ({len(data)} bytes)")

            # Update last accessed time
            if cid in self.metadata:
                self.metadata[cid]["last_accessed"] = datetime.utcnow().isoformat()
                self._save_metadata()

            return data

        except Exception as e:
            logger.error(f"Failed to retrieve from cache: {e}")
            return None

    async def delete(self, cid: str) -> bool:
        """
        Delete data from local cache.

        Args:
            cid: Content identifier

        Returns:
            bool: True if deletion successful
        """
        try:
            cache_file = self.cache_dir / f"{cid}.data"

            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Deleted cache file: {cid}")

            # Remove from metadata
            if cid in self.metadata:
                del self.metadata[cid]
                self._save_metadata()

            return True

        except Exception as e:
            logger.error(f"Failed to delete from cache: {e}")
            return False

    async def get_metadata(self, cid: str) -> Optional[dict[str, Any]]:
        """
        Get metadata for CID.

        Args:
            cid: Content identifier

        Returns:
            Optional[Dict[str, Any]]: Metadata dictionary, or None if not found
        """
        return self.metadata.get(cid)

    async def update_metadata(self, cid: str, metadata: dict[str, Any]) -> bool:
        """
        Update metadata for CID.

        Args:
            cid: Content identifier
            metadata: New metadata dictionary (merged with existing)

        Returns:
            bool: True if update successful
        """
        try:
            if cid in self.metadata:
                self.metadata[cid].update(metadata)
            else:
                self.metadata[cid] = metadata

            self._save_metadata()
            return True

        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    async def query_metadata(
        self, filters: dict[str, Any], limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Query cached items by metadata filters.

        Args:
            filters: Dictionary of filter criteria
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List[Dict[str, Any]]: List of matching metadata records

        Example:
            # Find all politician trading disclosures
            results = await cache.query_metadata({
                "type": "trading_disclosure",
                "politician_id": "xxx"
            }, limit=10)
        """
        results = []

        for _cid, metadata in self.metadata.items():
            # Check if metadata matches all filters
            match = True
            for key, value in filters.items():
                if key not in metadata or metadata[key] != value:
                    match = False
                    break

            if match:
                results.append(metadata)

        # Apply offset and limit
        return results[offset : offset + limit]

    async def list_all(self, prefix: Optional[str] = None) -> list[str]:
        """
        List all cached CIDs, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter by

        Returns:
            List[str]: List of CIDs
        """
        cids = list(self.metadata.keys())

        if prefix:
            cids = [cid for cid in cids if cid.startswith(prefix)]

        return cids

    async def cleanup(self, max_age_days: int = 30) -> int:
        """
        Clean up old cached files.

        Args:
            max_age_days: Maximum age in days before deletion

        Returns:
            int: Number of files deleted
        """
        from datetime import timedelta

        deleted = 0
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        for cid, metadata in list(self.metadata.items()):
            # Check if file is old
            cached_at_str = metadata.get("cached_at")
            if not cached_at_str:
                continue

            try:
                cached_at = datetime.fromisoformat(cached_at_str)
                if cached_at < cutoff:
                    await self.delete(cid)
                    deleted += 1
            except Exception:
                continue

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old cache files")

        return deleted

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        total_files = len(self.metadata)
        total_size = sum(m.get("size", 0) for m in self.metadata.values())

        # Count by type
        types: dict[str, int] = {}
        for metadata in self.metadata.values():
            data_type = metadata.get("type", "unknown")
            types[data_type] = types.get(data_type, 0) + 1

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "types": types,
            "cache_dir": str(self.cache_dir),
        }
