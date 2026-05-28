"""Query GitHub for self-hosted runner availability via the gh CLI."""

from __future__ import annotations

import json
import subprocess


def has_online_runner(repo_slug: str) -> bool:
    """True if `repo_slug` (owner/name) has at least one online self-hosted runner."""
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{repo_slug}/actions/runners"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return False
    return any(r.get("status") == "online" for r in data.get("runners", []))
