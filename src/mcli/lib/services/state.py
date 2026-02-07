"""Service state persistence for mcli.

Stores per-service state as JSON files in ~/.mcli/services/state/<name>.json.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_services_state_dir

logger = get_logger(__name__)


@dataclass
class ServiceState:
    """Persistent state for a managed service."""

    name: str
    status: str = "stopped"  # stopped | running | failed | unknown
    pid: Optional[int] = None
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    restart_count: int = 0
    last_health_check: Optional[str] = None
    health_status: Optional[str] = None  # healthy | unhealthy | unknown
    config: Optional[dict] = field(default_factory=dict)


def _state_path(name: str) -> Path:
    """Get the state file path for a service."""
    return get_services_state_dir() / f"{name}.json"


def load_state(name: str) -> Optional[ServiceState]:
    """Load service state from disk."""
    path = _state_path(name)
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return ServiceState(**data)
    except Exception as e:
        logger.error(f"Failed to load state for {name}: {e}")
        return None


def save_state(state: ServiceState) -> bool:
    """Save service state to disk."""
    path = _state_path(state.name)
    try:
        with open(path, "w") as f:
            json.dump(asdict(state), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save state for {state.name}: {e}")
        return False


def remove_state(name: str) -> bool:
    """Remove service state from disk."""
    path = _state_path(name)
    try:
        if path.exists():
            path.unlink()
        return True
    except Exception as e:
        logger.error(f"Failed to remove state for {name}: {e}")
        return False


def list_states() -> List[ServiceState]:
    """List all persisted service states."""
    states = []
    state_dir = get_services_state_dir()
    for path in sorted(state_dir.glob("*.json")):
        state = load_state(path.stem)
        if state:
            states.append(state)
    return states
