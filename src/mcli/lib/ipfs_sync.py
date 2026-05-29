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
import time
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Optional

import requests

from mcli.lib.constants import FileNames, SyncMessages
from mcli.lib.ipns_manager import (
    derive_key_info,
    ensure_key_imported,
    get_repo_name,
    get_sync_key,
    publish_to_ipns,
    resolve_ipns,
)
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
    LOCAL_IPFS_CAT = "http://127.0.0.1:5001/api/v0/cat"

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
        # Set by push() to the IPNS name if (and only if) publish succeeded.
        self.last_ipns_name: Optional[str] = None

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

    def _retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
    ):
        """
        Execute a function with exponential backoff retry logic.

        Args:
            func: Callable that returns (success: bool, result: any)
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds
            backoff_factor: Multiplier for each retry

        Returns:
            Result from successful call, or None if all retries failed
        """
        last_exception = None
        delay = base_delay

        for attempt in range(max_retries + 1):
            try:
                success, result = func()
                if success:
                    return result
                # If not successful but no exception, log and retry
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s...")
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} error: {e}, retrying in {delay:.1f}s...")

            if attempt < max_retries:
                time.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)

        if last_exception:
            logger.error(f"All {max_retries + 1} attempts failed. Last error: {last_exception}")
        return None

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

    def upload_to_ipfs(self, data: dict, max_retries: int = 3) -> Optional[str]:
        """
        Upload data to IPFS and return CID.

        Tries local IPFS daemon first with retry logic, then provides guidance for alternatives.

        Args:
            data: Dictionary to upload (will be JSON serialized)
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            CID string if successful, None otherwise
        """
        # Serialize data
        json_data = json.dumps(data, indent=2, sort_keys=True)

        # Try local IPFS daemon first
        if self._check_local_ipfs():

            def attempt_upload():
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
                    return (True, cid)
                else:
                    logger.warning(
                        SyncMessages.LOCAL_IPFS_UPLOAD_FAILED.format(status=response.status_code)
                    )
                    return (False, None)

            result = self._retry_with_backoff(attempt_upload, max_retries=max_retries)
            if result:
                return result

            logger.error(f"Failed to upload to local IPFS after {max_retries + 1} attempts")

        # No local IPFS - log helpful guidance
        logger.error(
            "No local IPFS daemon available. To enable IPFS sync:\n"
            "  1. Install IPFS: brew install ipfs (or see https://docs.ipfs.tech/install/)\n"
            "  2. Initialize: ipfs init\n"
            "  3. Start daemon: ipfs daemon\n"
            "  4. Re-run this command"
        )
        return None

    def retrieve_from_ipfs(
        self, cid: str, max_retries_per_gateway: int = 2, timeout: int = 30
    ) -> Optional[dict]:
        """
        Retrieve data from IPFS by CID.

        Tries multiple gateways for redundancy with exponential backoff retry
        logic for each gateway.

        Args:
            cid: Content identifier
            max_retries_per_gateway: Max retries per gateway (default: 2)
            timeout: Request timeout in seconds (default: 30)

        Returns:
            Retrieved data dict if successful, None otherwise
        """
        # Try primary gateway first
        gateways = [self.RETRIEVE_GATEWAY] + self.ALT_GATEWAYS

        for gateway_template in gateways:
            url = gateway_template.format(cid=cid)

            def attempt_retrieve():
                logger.info(f"Retrieving from {url}")
                response = requests.get(url, timeout=timeout)

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Retrieved from IPFS: {cid}")
                    return (True, data)
                elif response.status_code == 429:
                    # Rate limited - should retry
                    logger.warning(f"Gateway {gateway_template} rate limited (429)")
                    raise requests.exceptions.RequestException("Rate limited")
                elif response.status_code >= 500:
                    # Server error - should retry
                    logger.warning(
                        f"Gateway {gateway_template} server error: {response.status_code}"
                    )
                    raise requests.exceptions.RequestException(
                        f"Server error {response.status_code}"
                    )
                else:
                    # Client error (4xx except 429) - don't retry, try next gateway
                    logger.warning(f"Gateway {gateway_template} failed: {response.status_code}")
                    return (False, None)

            result = self._retry_with_backoff(
                attempt_retrieve,
                max_retries=max_retries_per_gateway,
                base_delay=1.0,
                max_delay=10.0,
            )
            if result is not None:
                return result

        logger.error(f"Failed to retrieve from all gateways: {cid}")
        return None

    def add_file_to_ipfs(self, file_path: Path, max_retries: int = 3) -> Optional[str]:
        """Add a single file to the local IPFS daemon and return its CID.

        Used by push() to upload each workflow script body alongside the
        manifest, so consumers can reconstruct the full workflows directory
        on pull.
        """
        if not self._check_local_ipfs():
            logger.error("Cannot add file to IPFS: local daemon unavailable")
            return None

        path = Path(file_path)
        if not path.is_file():
            logger.warning(f"Skipping IPFS add — file does not exist: {path}")
            return None

        def attempt_upload():
            with open(path, "rb") as fh:
                files = {"file": (path.name, fh.read())}
            response = requests.post(self.LOCAL_IPFS_API, files=files, timeout=30)
            if response.status_code == 200:
                cid = response.json().get("Hash")
                logger.info(f"Added {path.name} to IPFS: {cid}")
                return (True, cid)
            logger.warning(f"IPFS add failed for {path.name}: {response.status_code}")
            return (False, None)

        return self._retry_with_backoff(attempt_upload, max_retries=max_retries)

    def fetch_file_from_ipfs(self, cid: str, timeout: int = 30) -> Optional[bytes]:
        """Fetch raw bytes for a CID via the local daemon, falling back to gateways.

        Used by pull_workflows() to reconstruct script files referenced by
        per-script CIDs in the manifest.
        """
        # Local daemon first
        if self._check_local_ipfs():
            try:
                response = requests.post(
                    self.LOCAL_IPFS_CAT,
                    params={"arg": cid},
                    timeout=timeout,
                )
                if response.status_code == 200:
                    return response.content
                logger.warning(f"Local daemon cat failed for {cid}: {response.status_code}")
            except Exception as e:
                logger.warning(f"Local daemon cat error for {cid}: {e}")

        # Public gateway fallback
        for gateway_template in [self.RETRIEVE_GATEWAY] + self.ALT_GATEWAYS:
            url = gateway_template.format(cid=cid)
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    return response.content
                logger.warning(
                    f"Gateway {gateway_template} returned {response.status_code} for {cid}"
                )
            except Exception as e:
                logger.warning(f"Gateway {gateway_template} error for {cid}: {e}")
        return None

    def _embed_script_cids(self, command_data: dict, workflows_dir: Path) -> dict:
        """Augment a lockfile dict in-memory with per-script IPFS CIDs.

        Reads each command's ``file`` from ``workflows_dir``, adds it to IPFS,
        and stores the resulting CID as ``script_cid`` on the entry. Bumps
        the manifest version to "2.1" to signal that script bodies are
        retrievable.
        """
        commands = command_data.get("commands", {})
        any_uploaded = False
        for name, entry in commands.items():
            script_filename = entry.get("file")
            if not script_filename:
                continue
            script_path = workflows_dir / script_filename
            if not script_path.is_file():
                logger.warning(f"Skipping '{name}' — script file missing: {script_path}")
                continue
            cid = self.add_file_to_ipfs(script_path)
            if cid:
                entry["script_cid"] = cid
                any_uploaded = True

        if any_uploaded:
            command_data["version"] = "2.1"
        return command_data

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

            # Add each workflow script to IPFS so consumers can reconstruct
            # the full workflows directory on pull. Operates on the in-memory
            # copy so the on-disk lockfile stays untouched.
            workflows_dir = Path(command_lock_path).parent
            command_data = self._embed_script_cids(command_data, workflows_dir)

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
                # Prune old entries to prevent unbounded growth
                MAX_HISTORY = 100
                if len(self.sync_history) > MAX_HISTORY:
                    self.sync_history = self.sync_history[-MAX_HISTORY:]
                self._save_sync_history()

                # Publish to IPNS if sync key is configured. Record whether the
                # publish actually succeeded so callers can report honestly
                # instead of implying IPNS resolution works when it does not.
                self.last_ipns_name = None
                sync_key = get_sync_key()
                if sync_key:
                    repo = get_repo_name()
                    key_info = derive_key_info(sync_key, repo, "global")
                    ipns_name = ensure_key_imported(key_info)
                    if ipns_name:
                        self.last_ipns_name = publish_to_ipns(cid, key_info.key_name)

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

    def pull_workflows(
        self,
        cid: str,
        workflows_dir: Path,
        verify: bool = True,
    ) -> list[Path]:
        """Pull a manifest and reconstruct the workflow script files on disk.

        Walks each command entry in the retrieved manifest, fetches its
        ``script_cid`` (if present) from IPFS, verifies the recorded
        ``content_hash``, and writes the file to ``workflows_dir``.

        Returns the list of files written. If the manifest predates per-script
        CIDs (lockfile schema < 2.1), the manifest is still pulled but no
        files are written and a warning is logged.

        Raises:
            ValueError: when a fetched script's SHA-256 does not match the
                ``content_hash`` recorded in the lockfile.
        """
        manifest = self.pull(cid, verify=verify)
        if not manifest:
            return []

        commands = manifest.get("commands", {})
        # `pull()` strips the outer envelope, so commands maps directly.
        # Some callers still get the v2.x nested shape — handle both.
        if (
            isinstance(commands, dict)
            and "commands" in commands
            and isinstance(commands["commands"], dict)
        ):
            commands = commands["commands"]

        if not commands:
            return []

        workflows_dir = Path(workflows_dir)
        workflows_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for name, entry in commands.items():
            script_filename = entry.get("file")
            script_cid = entry.get("script_cid")
            if not script_filename or not script_cid:
                logger.warning(f"Skipping '{name}': manifest predates per-script CID sync")
                continue

            payload = self.fetch_file_from_ipfs(script_cid)
            if payload is None:
                logger.error(f"Failed to fetch script for '{name}' (cid={script_cid})")
                continue

            expected_hash = entry.get("content_hash")
            if expected_hash:
                expected_value = expected_hash.split(":", 1)[-1]
                actual = hashlib.sha256(payload).hexdigest()
                if actual != expected_value:
                    raise ValueError(
                        f"hash mismatch for '{name}': expected {expected_value}, got {actual}"
                    )

            # SECURITY: `script_filename` comes from a remote, untrusted manifest.
            # Contain it inside workflows_dir so a crafted manifest cannot write
            # outside the directory via '..' segments or an absolute path.
            rel = PurePosixPath(script_filename)
            if rel.is_absolute() or any(part == ".." for part in rel.parts):
                raise ValueError(f"unsafe script path in manifest: {script_filename}")
            base = Path(workflows_dir).resolve()
            target = (base / Path(*rel.parts)).resolve()
            if base != target and base not in target.parents:
                raise ValueError(f"script path escapes workflows dir: {script_filename}")

            # Recreate group subdirectories (e.g. "demo/hello.py") on pull.
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            written.append(target)

        return written

    def resolve_latest_cid(
        self,
        scope: str = "global",
        repo_name: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve the deterministic IPNS name to a current CID.

        Returns the CID string on success, ``None`` if the sync key is
        unset, the key cannot be imported into Kubo, or IPNS resolution
        fails. Surfaces the CID so CLI callers can hand it to
        ``pull_workflows`` for script extraction.
        """
        sync_key = get_sync_key()
        if not sync_key:
            logger.warning("Sync key not configured — cannot resolve via IPNS")
            return None

        repo = repo_name or get_repo_name()
        key_info = derive_key_info(sync_key, repo, scope)

        ipns_name = ensure_key_imported(key_info)
        if not ipns_name:
            logger.error("Failed to import IPNS key into Kubo")
            return None

        cid = resolve_ipns(ipns_name)
        if not cid:
            logger.error("IPNS resolution failed — no workflows published yet?")
            return None
        return cid

    def pull_latest(
        self,
        scope: str = "global",
        repo_name: Optional[str] = None,
        verify: bool = True,
    ) -> Optional[dict]:
        """Pull the latest workflow state by resolving via IPNS.

        Requires the sync key to be configured (env var or store).
        Returns the command data dict on success, ``None`` otherwise.
        """
        cid = self.resolve_latest_cid(scope=scope, repo_name=repo_name)
        if not cid:
            return None
        return self.pull(cid, verify=verify)

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
# NOTE: This block is intentionally kept as dead code for future reference
# fmt: off
# flake8: noqa
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
# fmt: on
