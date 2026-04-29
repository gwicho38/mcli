"""Persistent storage for the shared workflow sync key.

The store keeps a 64-character hex secret on disk so users do not have
to ``export MCLI_SYNC_KEY=...`` in every shell. The env var still wins
when set — see :func:`mcli.lib.ipns_manager.get_sync_key`.

File: ``$MCLI_HOME/sync_key.json`` (default ``~/.mcli/sync_key.json``)
mode 0600. JSON shape: ``{"key": "<64 hex chars>"}``.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path
from typing import Optional

from mcli.lib.paths import get_mcli_home

_FILENAME = "sync_key.json"
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class SyncKeyStore:
    """Read/write the persistent sync key on disk."""

    @property
    def path(self) -> Path:
        return get_mcli_home() / _FILENAME

    def get(self) -> Optional[str]:
        path = self.path
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        key = data.get("key")
        return key if isinstance(key, str) and _HEX64.match(key) else None

    def set(self, key: str) -> None:
        if not isinstance(key, str) or not _HEX64.match(key):
            raise ValueError("sync key must be a 64-char hex string")
        self._write(key)

    def generate(self, force: bool = False) -> str:
        if self.path.exists() and not force:
            raise FileExistsError(
                f"sync key already exists at {self.path}; use force=True to overwrite"
            )
        key = secrets.token_hex(32)
        self._write(key)
        return key

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def _write(self, key: str) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write then chmod so the secret is never world-readable.
        path.write_text(json.dumps({"key": key}))
        os.chmod(path, 0o600)
