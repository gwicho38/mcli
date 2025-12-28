"""
Workspace registry for mcli.

Tracks registered workflow locations across multiple repositories,
enabling `mcli list` to show all workflows from all registered workspaces.

The registry is stored in ~/.mcli/workspaces.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_git_root, get_mcli_home, is_git_repository
from mcli.lib.script_loader import ScriptLoader

logger = get_logger(__name__)


def get_registry_path() -> Path:
    """Get the path to the workspaces registry file."""
    return get_mcli_home() / "workspaces.json"


def load_registry() -> Dict[str, Any]:
    """
    Load the workspace registry from disk.

    Returns:
        Dictionary with registry data, or empty structure if not found
    """
    registry_path = get_registry_path()

    if not registry_path.exists():
        return {"version": "1.0", "workspaces": {}}

    try:
        with open(registry_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load workspace registry: {e}")
        return {"version": "1.0", "workspaces": {}}


def save_registry(registry: Dict[str, Any]) -> bool:
    """
    Save the workspace registry to disk.

    Args:
        registry: Registry data to save

    Returns:
        True if successful, False otherwise
    """
    registry_path = get_registry_path()

    try:
        registry["updated_at"] = datetime.utcnow().isoformat() + "Z"
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save workspace registry: {e}")
        return False


def get_workspace_name(workspace_path: Path) -> str:
    """
    Get a friendly name for a workspace.

    Args:
        workspace_path: Path to the workspace root (git root or directory)

    Returns:
        Friendly name (typically the directory name)
    """
    return workspace_path.name


def register_workspace(
    workspace_path: Optional[Path] = None, name: Optional[str] = None
) -> Optional[str]:
    """
    Register a workspace in the registry.

    Args:
        workspace_path: Path to workspace root (defaults to current git root)
        name: Optional custom name for the workspace

    Returns:
        Workspace ID (path string) if successful, None otherwise
    """
    # Determine workspace path
    if workspace_path is None:
        if is_git_repository():
            workspace_path = get_git_root()
        else:
            workspace_path = Path.cwd()

    if workspace_path is None:
        logger.error("Could not determine workspace path")
        return None

    workspace_path = workspace_path.resolve()

    # Check if workflows directory exists
    workflows_dir = workspace_path / ".mcli" / "workflows"
    if not workflows_dir.exists():
        # Also check for legacy commands directory
        legacy_dir = workspace_path / ".mcli" / "commands"
        if not legacy_dir.exists():
            logger.warning(f"No workflows found at {workspace_path}")
            logger.info("Initialize with: mcli init")
            return None

    # Load registry
    registry = load_registry()

    # Use path as ID
    workspace_id = str(workspace_path)

    # Create workspace entry
    workspace_name = name or get_workspace_name(workspace_path)
    registry["workspaces"][workspace_id] = {
        "name": workspace_name,
        "path": str(workspace_path),
        "added_at": datetime.utcnow().isoformat() + "Z",
    }

    if save_registry(registry):
        logger.info(f"Registered workspace: {workspace_name} ({workspace_path})")
        return workspace_id

    return None


def unregister_workspace(workspace_path: Optional[Path] = None) -> bool:
    """
    Remove a workspace from the registry.

    Args:
        workspace_path: Path to workspace root (defaults to current git root)

    Returns:
        True if successful, False otherwise
    """
    # Determine workspace path
    if workspace_path is None:
        if is_git_repository():
            workspace_path = get_git_root()
        else:
            workspace_path = Path.cwd()

    if workspace_path is None:
        logger.error("Could not determine workspace path")
        return False

    workspace_path = workspace_path.resolve()
    workspace_id = str(workspace_path)

    # Load registry
    registry = load_registry()

    if workspace_id not in registry["workspaces"]:
        logger.warning(f"Workspace not registered: {workspace_path}")
        return False

    # Remove workspace
    del registry["workspaces"][workspace_id]

    if save_registry(registry):
        logger.info(f"Unregistered workspace: {workspace_path}")
        return True

    return False


def list_registered_workspaces() -> List[Dict[str, Any]]:
    """
    List all registered workspaces.

    Returns:
        List of workspace dictionaries with name, path, and status
    """
    registry = load_registry()
    workspaces = []

    for workspace_id, workspace_data in registry.get("workspaces", {}).items():
        workspace_path = Path(workspace_data["path"])

        # Check if workspace still exists
        workflows_dir = workspace_path / ".mcli" / "workflows"
        legacy_dir = workspace_path / ".mcli" / "commands"
        exists = workflows_dir.exists() or legacy_dir.exists()

        workspaces.append(
            {
                "id": workspace_id,
                "name": workspace_data.get("name", workspace_path.name),
                "path": str(workspace_path),
                "exists": exists,
                "added_at": workspace_data.get("added_at"),
            }
        )

    return workspaces


def get_all_workflows() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all workflows from all registered workspaces.

    Returns:
        Dictionary mapping workspace name to list of workflow info
    """
    registry = load_registry()
    all_workflows: Dict[str, List[Dict[str, Any]]] = {}

    # Always include global workflows
    global_workflows_dir = get_mcli_home() / "workflows"
    if global_workflows_dir.exists():
        loader = ScriptLoader(global_workflows_dir)
        scripts = loader.discover_scripts()

        workflows = []
        for script_path in scripts:
            try:
                info = loader.get_script_info(script_path)
                info["name"] = script_path.stem
                info["path"] = str(script_path)
                workflows.append(info)
            except Exception as e:
                logger.debug(f"Failed to get info for {script_path}: {e}")

        if workflows:
            all_workflows["global (~/.mcli/workflows)"] = workflows

    # Get workflows from registered workspaces
    for _workspace_id, workspace_data in registry.get("workspaces", {}).items():
        workspace_path = Path(workspace_data["path"])
        workspace_name = workspace_data.get("name", workspace_path.name)

        # Determine workflows directory
        workflows_dir = workspace_path / ".mcli" / "workflows"
        if not workflows_dir.exists():
            workflows_dir = workspace_path / ".mcli" / "commands"

        if not workflows_dir.exists():
            continue

        loader = ScriptLoader(workflows_dir)
        scripts = loader.discover_scripts()

        workflows = []
        for script_path in scripts:
            try:
                info = loader.get_script_info(script_path)
                info["name"] = script_path.stem
                info["path"] = str(script_path)
                workflows.append(info)
            except Exception as e:
                logger.debug(f"Failed to get info for {script_path}: {e}")

        if workflows:
            all_workflows[f"{workspace_name} ({workspace_path})"] = workflows

    return all_workflows


def auto_register_current() -> Optional[str]:
    """
    Auto-register the current workspace if it has workflows and isn't registered.

    Returns:
        Workspace ID if registered, None otherwise
    """
    if not is_git_repository():
        return None

    git_root = get_git_root()
    if git_root is None:
        return None

    # Check if already registered
    registry = load_registry()
    workspace_id = str(git_root.resolve())

    if workspace_id in registry.get("workspaces", {}):
        return workspace_id

    # Check if has workflows
    workflows_dir = git_root / ".mcli" / "workflows"
    legacy_dir = git_root / ".mcli" / "commands"

    if workflows_dir.exists() or legacy_dir.exists():
        return register_workspace(git_root)

    return None
