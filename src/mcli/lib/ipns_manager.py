"""IPNS key management for deterministic workflow sync.

Provides helpers to derive stable IPNS key identities from a shared
secret, import them into the local Kubo node, and publish/resolve
CIDs via IPNS names.
"""

import base64
import hashlib
import hmac
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from mcli.lib.constants import EnvVars, IpfsDefaults
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

# PKCS#8 DER prefix for a bare ED25519 private key (32-byte seed)
# RFC 8410: OID 1.3.101.112 (id-EdDSA / Ed25519)
ED25519_PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class IPNSKeyInfo:
    """Deterministically derived IPNS key identity."""

    key_name: str  # e.g. "mcli-3c3080bd2a8c73b0"
    seed: bytes  # 32-byte ed25519 seed


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------


def derive_key_info(sync_key: str, repo_name: str, scope: str) -> IPNSKeyInfo:
    """Derive a stable IPNSKeyInfo from *sync_key*, *repo_name*, and *scope*.

    The derivation is deterministic: the same inputs always produce the same
    key_name and seed, so all team members sharing the same sync key converge
    on the same IPNS identity.
    """
    context = f"{IpfsDefaults.IPNS_KEY_DERIVATION_CONTEXT}:{repo_name}:{scope}"
    seed = hmac.new(sync_key.encode(), context.encode(), hashlib.sha256).digest()
    key_name = IpfsDefaults.IPNS_KEY_PREFIX + hashlib.sha256(seed).hexdigest()[:16]
    return IPNSKeyInfo(key_name=key_name, seed=seed)


# ---------------------------------------------------------------------------
# PEM encoding
# ---------------------------------------------------------------------------


def build_pem_from_seed(seed: bytes) -> str:
    """Encode *seed* as a PKCS#8 PEM private key string.

    The resulting PEM can be passed directly to ``/key/import`` on a Kubo node
    using the ``pem-pkcs8-cleartext`` format.
    """
    der = ED25519_PKCS8_PREFIX + seed
    b64 = base64.b64encode(der).decode("ascii")
    # Wrap at 64 characters per line
    wrapped = "\n".join(b64[i : i + 64] for i in range(0, len(b64), 64))
    return f"-----BEGIN PRIVATE KEY-----\n{wrapped}\n-----END PRIVATE KEY-----\n"


# ---------------------------------------------------------------------------
# Kubo API helpers
# ---------------------------------------------------------------------------


def ensure_key_imported(key_info: IPNSKeyInfo) -> Optional[str]:
    """Ensure *key_info* is present in the local Kubo node, importing if needed.

    Returns the IPNS key Id (peer ID string) on success, or None on failure.
    """
    kubo_url = IpfsDefaults.KUBO_API_URL
    try:
        resp = requests.post(f"{kubo_url}/key/list", timeout=5)
        resp.raise_for_status()
        keys = resp.json().get("Keys", [])
        for k in keys:
            if k.get("Name") == key_info.key_name:
                logger.debug("IPNS key already imported: %s", key_info.key_name)
                return k["Id"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to list Kubo keys: %s", exc)
        return None

    # Key not found — import it
    logger.info("Importing IPNS key: %s", key_info.key_name)
    pem = build_pem_from_seed(key_info.seed)
    try:
        resp = requests.post(
            f"{kubo_url}/key/import",
            params={"arg": key_info.key_name, "format": "pem-pkcs8-cleartext"},
            files={"file": ("key.pem", pem.encode(), "application/octet-stream")},
            timeout=5,
        )
        resp.raise_for_status()
        key_id = resp.json()["Id"]
        logger.info("Imported IPNS key %s → %s", key_info.key_name, key_id)
        return key_id
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to import IPNS key %s: %s", key_info.key_name, exc)
        return None


def publish_to_ipns(cid: str, key_name: str) -> Optional[str]:
    """Publish *cid* to IPNS using *key_name*.

    Returns the IPNS name string on success, or None on failure.
    """
    kubo_url = IpfsDefaults.KUBO_API_URL
    try:
        resp = requests.post(
            f"{kubo_url}/name/publish",
            params={
                "arg": f"/ipfs/{cid}",
                "key": key_name,
                "offline": "false",
                "allow-offline": "false",
                "lifetime": IpfsDefaults.IPNS_LIFETIME,
                "resolve": "false",
            },
            timeout=IpfsDefaults.IPNS_PUBLISH_TIMEOUT,
        )
        resp.raise_for_status()
        name = resp.json()["Name"]
        logger.info("Published %s → IPNS %s", cid, name)
        return name
    except Exception as exc:  # noqa: BLE001
        logger.warning("IPNS publish failed: %s", exc)
        return None


def resolve_ipns(ipns_name: str) -> Optional[str]:
    """Resolve *ipns_name* to a CID.

    Returns the CID (without the ``/ipfs/`` prefix) on success, or None on
    failure.
    """
    kubo_url = IpfsDefaults.KUBO_API_URL
    try:
        resp = requests.post(
            f"{kubo_url}/name/resolve",
            params={"arg": ipns_name, "nocache": "true"},
            timeout=IpfsDefaults.IPNS_RESOLVE_TIMEOUT,
        )
        resp.raise_for_status()
        path = resp.json()["Path"]
        cid = path.removeprefix("/ipfs/")
        logger.debug("Resolved IPNS %s → %s", ipns_name, cid)
        return cid
    except Exception as exc:  # noqa: BLE001
        logger.warning("IPNS resolve failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Environment / repo helpers
# ---------------------------------------------------------------------------


def get_sync_key() -> Optional[str]:
    """Return the MCLI_SYNC_KEY environment variable, or None if unset."""
    return os.environ.get(EnvVars.MCLI_SYNC_KEY) or None


def get_repo_name() -> str:
    """Return the repository name inferred from git remote, or cwd name.

    Tries ``git remote -v`` first and parses the first fetch URL.  Falls back
    to ``Path.cwd().name`` if git is unavailable or returns no remotes.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.splitlines():
                if "(fetch)" in line:
                    # Format: "origin\thttps://host/user/repo.git (fetch)"
                    url_part = line.split("\t", 1)[1].split(" ")[0]
                    repo = url_part.rstrip("/").split("/")[-1]
                    if repo.endswith(".git"):
                        repo = repo[:-4]
                    return repo
    except Exception as exc:  # noqa: BLE001
        logger.debug("git remote -v failed: %s", exc)

    return Path.cwd().name
