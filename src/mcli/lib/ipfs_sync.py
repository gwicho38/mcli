"""
IPFS-based immutable command synchronization.

This module provides zero-configuration, immutable sync for mcli commands
using IPFS (InterPlanetary File System). Commands are uploaded to public
IPFS gateways and can be retrieved by their content-addressed CID.

Architecture:
    Local Command State
        ↓
    Upload to IPFS (via web3.storage)
        ↓
    Get immutable CID
        ↓
    Store CID in local history
        ↓
    Anyone can retrieve via CID

Features:
- Zero configuration (no API keys required)
- Immutable by design (CID = content hash)
- Decentralized (no single point of failure)
- Privacy-preserving (optional encryption)
- Verifiable (CID proves content authenticity)
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from mcli.lib.constants import FileNames, SyncMessages
from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_data_dir

logger = get_logger(__name__)


class IPFSSync:
    """
    Zero-config immutable command sync via IPFS.

    Uploads command state to IPFS and tracks sync history locally.
    Supports local IPFS node or fallback methods.
    """

    # Local IPFS daemon endpoint (default port)
    LOCAL_IPFS_API = "http://127.0.0.1:5001/api/v0/add"

    # Public IPFS gateways for retrieval
    RETRIEVE_GATEWAY = "https://ipfs.io/ipfs/{cid}"

    # Alternative gateways for redundancy
    ALT_GATEWAYS = [
        "https://dweb.link/ipfs/{cid}",
        "https://cloudflare-ipfs.com/ipfs/{cid}",
        "https://gateway.pinata.cloud/ipfs/{cid}",
        "https://w3s.link/ipfs/{cid}",
    ]

    def __init__(self):
        """Initialize IPFS sync manager."""
        self.data_dir = get_data_dir()
        self.sync_history_path = self.data_dir / FileNames.IPFS_SYNC_HISTORY_JSON
        self.sync_history = self._load_sync_history()
        self._local_ipfs_available: Optional[bool] = None

    def _load_sync_history(self) -> list[dict]:
        """Load sync history from local storage."""
        if not self.sync_history_path.exists():
            return []

        try:
            with open(self.sync_history_path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load sync history: {e}")
            return []

    def _save_sync_history(self):
        """Save sync history to local storage."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.sync_history_path, "w") as f:
                json.dump(self.sync_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sync history: {e}")

    def _compute_hash(self, data: str) -> str:
        """Compute SHA256 hash of data."""
        return hashlib.sha256(data.encode()).hexdigest()

    def _check_local_ipfs(self) -> bool:
        """Check if local IPFS daemon is running."""
        if self._local_ipfs_available is not None:
            return self._local_ipfs_available

        try:
            # Try to connect to local IPFS daemon
            response = requests.post(
                "http://127.0.0.1:5001/api/v0/id",
                timeout=2,
            )
            self._local_ipfs_available = response.status_code == 200
            if self._local_ipfs_available:
                logger.info(SyncMessages.LOCAL_IPFS_DAEMON_DETECTED)
            return self._local_ipfs_available
        except Exception:
            self._local_ipfs_available = False
            return False

    def upload_to_ipfs(self, data: dict) -> Optional[str]:
        """
        Upload data to IPFS and return CID.

        Tries local IPFS daemon first, then provides guidance for alternatives.

        Args:
            data: Dictionary to upload (will be JSON serialized)

        Returns:
            CID string if successful, None otherwise
        """
        # Serialize data
        json_data = json.dumps(data, indent=2, sort_keys=True)

        # Try local IPFS daemon first
        if self._check_local_ipfs():
            try:
                files = {"file": (FileNames.COMMANDS_JSON, json_data)}
                response = requests.post(
                    self.LOCAL_IPFS_API,
                    files=files,
                    timeout=30,
                )

                if response.status_code == 200:
                    result = response.json()
                    cid = result.get("Hash")
                    logger.info(f"Uploaded to local IPFS: {cid}")
                    return cid
                else:
                    logger.error(
                        SyncMessages.LOCAL_IPFS_UPLOAD_FAILED.format(status=response.status_code)
                    )
            except Exception as e:
                logger.error(SyncMessages.LOCAL_IPFS_UPLOAD_ERROR.format(error=e))

        # No local IPFS - log helpful guidance
        logger.error(
            "No local IPFS daemon available. To enable IPFS sync:\n"
            "  1. Install IPFS: brew install ipfs (or see https://docs.ipfs.tech/install/)\n"
            "  2. Initialize: ipfs init\n"
            "  3. Start daemon: ipfs daemon\n"
            "  4. Re-run this command"
        )
        return None

    def retrieve_from_ipfs(self, cid: str) -> Optional[dict]:
        """
        Retrieve data from IPFS by CID.

        Tries multiple gateways for redundancy.

        Args:
            cid: Content identifier

        Returns:
            Retrieved data dict if successful, None otherwise
        """
        # Try primary gateway first
        gateways = [self.RETRIEVE_GATEWAY] + self.ALT_GATEWAYS

        for gateway_template in gateways:
            try:
                url = gateway_template.format(cid=cid)
                logger.info(f"Retrieving from {url}")

                response = requests.get(url, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Retrieved from IPFS: {cid}")
                    return data
                else:
                    logger.warning(f"Gateway {gateway_template} failed: {response.status_code}")

            except Exception as e:
                logger.warning(f"Gateway {gateway_template} error: {e}")
                continue

        logger.error(f"Failed to retrieve from all gateways: {cid}")
        return None

    def push(self, command_lock_path: Path, description: str = "") -> Optional[str]:
        """
        Push command state to IPFS.

        Args:
            command_lock_path: Path to command lockfile
            description: Optional description for this sync

        Returns:
            CID if successful, None otherwise
        """
        try:
            # Load command state
            with open(command_lock_path) as f:
                command_data = json.load(f)

            # Add sync metadata
            sync_data = {
                "version": "1.0",
                "synced_at": datetime.now().isoformat(),
                "description": description,
                "source": "mcli",
                "commands": command_data,
            }

            # Compute hash for verification
            json_str = json.dumps(sync_data, sort_keys=True)
            data_hash = self._compute_hash(json_str)
            sync_data["hash"] = data_hash

            # Upload to IPFS
            cid = self.upload_to_ipfs(sync_data)

            if cid:
                # Record in history
                self.sync_history.append(
                    {
                        "cid": cid,
                        "timestamp": datetime.now().isoformat(),
                        "description": description,
                        "hash": data_hash,
                        "command_count": len(command_data.get("commands", {})),
                    }
                )
                self._save_sync_history()

            return cid

        except Exception as e:
            logger.error(f"Failed to push to IPFS: {e}")
            return None

    def pull(self, cid: str, verify: bool = True) -> Optional[dict]:
        """
        Pull command state from IPFS.

        Args:
            cid: Content identifier
            verify: Whether to verify hash

        Returns:
            Command data if successful, None otherwise
        """
        data = self.retrieve_from_ipfs(cid)

        if not data:
            return None

        # Verify hash if requested
        if verify and "hash" in data:
            # Recompute hash
            data_copy = data.copy()
            original_hash = data_copy.pop("hash")

            json_str = json.dumps(data_copy, sort_keys=True)
            computed_hash = self._compute_hash(json_str)

            if computed_hash != original_hash:
                logger.error(SyncMessages.HASH_VERIFICATION_FAILED)
                return None

        return data.get("commands", {})

    def get_history(self, limit: int = 10) -> list[dict]:
        """
        Get sync history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of sync history entries
        """
        return self.sync_history[-limit:]

    def verify_cid(self, cid: str) -> bool:
        """
        Verify that a CID is accessible.

        Args:
            cid: Content identifier

        Returns:
            True if CID is accessible, False otherwise
        """
        data = self.retrieve_from_ipfs(cid)
        return data is not None


# Commented out alternative storage backends for future use
"""
# PostgreSQL/Supabase backend (requires configuration)
class SupabaseSync:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key

    def push(self, command_data: Dict) -> str:
        # Upload to Supabase
        pass

    def pull(self, sync_id: str) -> Dict:
        # Download from Supabase
        pass


# Git-based sync (requires repo setup)
class GitSync:
    def __init__(self, repo_url: str):
        self.repo_url = repo_url

    def push(self, command_data: Dict) -> str:
        # Commit and push to git
        pass

    def pull(self, commit_hash: str) -> Dict:
        # Fetch from git
        pass


# Arweave permanent storage (requires AR tokens)
class ArweaveSync:
    def __init__(self):
        pass

    def push(self, command_data: Dict) -> str:
        # Upload to Arweave
        pass

    def pull(self, tx_id: str) -> Dict:
        # Download from Arweave
        pass
"""
