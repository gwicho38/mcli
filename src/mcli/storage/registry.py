"""
Registry system for version tracking.

Mirrors lsh-framework's registry pattern for discovering latest versions
of data across distributed storage.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from mcli.lib.logger import get_logger

if TYPE_CHECKING:
    from mcli.storage.backends.ipfs_backend import StorachaBackend

logger = get_logger(__name__)


class RegistryManager:
    """
    Manages registry files for version tracking.

    Registry Pattern (from lsh-framework):
    - Small JSON files that track latest CIDs
    - Allows discovery of latest versions
    - Format: {"repo_name": "xxx", "environment": "xxx", "cid": "xxx", "timestamp": "..."}
    """

    def __init__(self, backend: "StorachaBackend"):
        """
        Initialize registry manager.

        Args:
            backend: Storage backend (for upload/download)
        """
        self.backend = backend

    async def upload_registry(
        self,
        repo_name: str,
        environment: str,
        data_cid: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Upload registry file for a repo/environment.

        Args:
            repo_name: Repository name
            environment: Environment name (e.g., "production", "development")
            data_cid: CID of the actual data
            metadata: Optional additional metadata

        Returns:
            str: CID of uploaded registry file

        Example:
            registry_cid = await registry.upload_registry(
                "politician-trading-tracker",
                "production",
                "bafkreixxx",
                {"version": "1.0.0"}
            )
        """
        try:
            # Create registry data
            registry: dict[str, Any] = {
                "repo_name": repo_name,
                "environment": environment,
                "data_cid": data_cid,  # CID of actual data
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",  # Registry format version
            }

            # Add optional metadata
            if metadata:
                registry["metadata"] = metadata

            # Convert to JSON bytes
            content = json.dumps(registry, indent=2)
            data = content.encode()

            # Generate filename
            filename = f"mcli-registry-{repo_name}-{environment}.json"

            # Upload to backend (unencrypted registry for discovery)
            registry_cid = await self.backend._upload_to_storacha(data, filename)

            logger.debug(f"📝 Uploaded registry for {repo_name}/{environment}: {registry_cid}")
            logger.debug(f"   Data CID: {data_cid}")

            return registry_cid

        except Exception as e:
            logger.error(f"Failed to upload registry: {e}")
            raise

    async def get_latest_cid(self, repo_name: str, environment: str) -> Optional[str]:
        """
        Get the latest data CID from registry.

        Searches recent uploads for registry files matching repo_name/environment
        and returns the most recent data CID.

        Args:
            repo_name: Repository name
            environment: Environment name

        Returns:
            Optional[str]: Latest data CID, or None if not found

        Example:
            latest_cid = await registry.get_latest_cid(
                "politician-trading-tracker",
                "production"
            )
            if latest_cid:
                data = await storage.retrieve(latest_cid)
        """
        try:
            # List recent uploads from backend
            recent_cids = await self.backend.list_recent_uploads(limit=20)

            # Check each upload for registry files
            registries = []

            for cid in recent_cids:
                try:
                    # Try to download (with timeout)
                    data = await self.backend._download_from_storacha(cid, timeout=5)

                    # Skip large files (registry should be <1KB)
                    if len(data) > 1024:
                        continue

                    # Try to parse as JSON
                    registry = json.loads(data.decode())

                    # Check if it matches our criteria
                    if (
                        registry.get("repo_name") == repo_name
                        and registry.get("environment") == environment
                        and "data_cid" in registry
                        and "timestamp" in registry
                    ):
                        registries.append(registry)

                except Exception:
                    # Not a registry file or failed to parse
                    continue

            # Sort by timestamp (newest first)
            if registries:
                registries.sort(key=lambda r: datetime.fromisoformat(r["timestamp"]), reverse=True)

                latest = registries[0]
                data_cid: str = str(latest["data_cid"])

                logger.debug(f"✅ Found latest CID for {repo_name}/{environment}: {data_cid}")
                logger.debug(f"   Timestamp: {latest['timestamp']}")

                return data_cid

            # No registry found
            logger.debug(f"❌ No registry found for {repo_name}/{environment}")
            return None

        except Exception as e:
            logger.error(f"Failed to get latest CID: {e}")
            return None

    async def check_registry_exists(self, repo_name: str, environment: str) -> bool:
        """
        Check if registry exists for repo/environment.

        Args:
            repo_name: Repository name
            environment: Environment name

        Returns:
            bool: True if registry exists, False otherwise
        """
        latest_cid = await self.get_latest_cid(repo_name, environment)
        return latest_cid is not None

    async def list_registries(self) -> dict[str, dict[str, str]]:
        """
        List all registries found in recent uploads.

        Returns:
            Dict[str, Dict[str, str]]: Dictionary mapping "repo/env" to latest CID info

        Example:
            registries = await registry.list_registries()
            # Returns: {
            #     "repo1/production": {"data_cid": "bafkreixxx", "timestamp": "..."},
            #     "repo1/staging": {"data_cid": "bafkreiyyy", "timestamp": "..."}
            # }
        """
        try:
            recent_cids = await self.backend.list_recent_uploads(limit=50)

            registries: dict[str, dict[str, Any]] = {}

            for cid in recent_cids:
                try:
                    data = await self.backend._download_from_storacha(cid, timeout=5)

                    if len(data) > 1024:
                        continue

                    registry = json.loads(data.decode())

                    if (
                        "repo_name" in registry
                        and "environment" in registry
                        and "data_cid" in registry
                    ):
                        key = f"{registry['repo_name']}/{registry['environment']}"
                        timestamp = datetime.fromisoformat(registry["timestamp"])

                        # Keep most recent
                        if key not in registries or timestamp > datetime.fromisoformat(
                            registries[key]["timestamp"]
                        ):
                            registries[key] = {
                                "data_cid": registry["data_cid"],
                                "timestamp": registry["timestamp"],
                                "registry_cid": cid,
                            }

                except Exception:
                    continue

            return registries

        except Exception as e:
            logger.error(f"Failed to list registries: {e}")
            return {}
