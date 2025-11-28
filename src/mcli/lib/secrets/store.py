"""
Git-based secrets store for synchronization across machines.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from git import GitCommandError, Repo

from mcli.lib.constants.paths import DirNames
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import error, info, success, warning

logger = get_logger(__name__)


class SecretsStore:
    """Manages git-based secrets synchronization."""

    def __init__(self, store_path: Optional[Path] = None):
        """Initialize the secrets store.

        Args:
            store_path: Path to git repository for secrets. Defaults to ~/repos/mcli-secrets
        """
        self.store_path = store_path or Path.home() / "repos" / "mcli-secrets"
        self.config_file = Path.home() / DirNames.MCLI / "secrets-store.conf"
        self.load_config()

    def load_config(self) -> None:
        """Load store configuration."""
        self.store_config = {}
        if self.config_file.exists():
            with open(self.config_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        self.store_config[key.strip()] = value.strip()

        # Override store path if configured
        if "store_path" in self.store_config:
            self.store_path = Path(self.store_config["store_path"])

    def save_config(self) -> None:
        """Save store configuration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            for key, value in self.store_config.items():
                f.write(f"{key}={value}\n")

    def init(self, remote_url: Optional[str] = None) -> None:
        """Initialize the secrets store repository.

        Args:
            remote_url: Optional git remote URL
        """
        if self.store_path.exists() and (self.store_path / ".git").exists():
            error("Store already initialized")
            return

        self.store_path.mkdir(parents=True, exist_ok=True)

        try:
            repo = Repo.init(self.store_path)

            # Create README
            readme_path = self.store_path / "README.md"
            readme_path.write_text(
                "# MCLI Secrets Store\n\n"
                "This repository stores encrypted secrets for MCLI.\n\n"
                "**WARNING**: This repository contains encrypted sensitive data.\n"
                "Ensure it is kept private and access is restricted.\n"
            )

            # Create .gitignore
            gitignore_path = self.store_path / ".gitignore"
            gitignore_path.write_text("*.key\n*.tmp\n.DS_Store\n")

            repo.index.add([readme_path.name, gitignore_path.name])
            repo.index.commit("Initial commit")

            if remote_url:
                repo.create_remote("origin", remote_url)
                self.store_config["remote_url"] = remote_url
                self.save_config()
                info(f"Remote added: {remote_url}")

            success(f"Secrets store initialized at {self.store_path}")

        except GitCommandError as e:
            error(f"Failed to initialize store: {e}")

    def push(self, secrets_dir: Path, message: Optional[str] = None) -> None:
        """Push secrets to the store.

        Args:
            secrets_dir: Directory containing encrypted secrets
            message: Commit message
        """
        if not self._check_initialized():
            return

        try:
            repo = Repo(self.store_path)

            # Copy secrets to store
            store_secrets_dir = self.store_path / "secrets"

            # Remove existing secrets
            if store_secrets_dir.exists():
                shutil.rmtree(store_secrets_dir)

            # Copy new secrets
            shutil.copytree(secrets_dir, store_secrets_dir)

            # Add to git
            repo.index.add(["secrets"])

            # Check if there are changes
            if repo.is_dirty():
                message = message or f"Update secrets from {os.uname().nodename}"
                repo.index.commit(message)

                # Push if remote exists
                if "origin" in repo.remotes:
                    info("Pushing to remote...")
                    repo.remotes.origin.push()
                    success("Secrets pushed to remote")
                else:
                    success("Secrets committed locally")
            else:
                info("No changes to push")

        except GitCommandError as e:
            error(f"Failed to push secrets: {e}")

    def pull(self, secrets_dir: Path) -> None:
        """Pull secrets from the store.

        Args:
            secrets_dir: Directory to store pulled secrets
        """
        if not self._check_initialized():
            return

        try:
            repo = Repo(self.store_path)

            # Pull from remote if exists
            if "origin" in repo.remotes:
                info("Pulling from remote...")
                repo.remotes.origin.pull()

            # Copy secrets from store
            store_secrets_dir = self.store_path / "secrets"

            if not store_secrets_dir.exists():
                warning("No secrets found in store")
                return

            # Backup existing secrets
            if secrets_dir.exists():
                backup_dir = secrets_dir.parent / f"{secrets_dir.name}.backup"
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                shutil.move(str(secrets_dir), str(backup_dir))
                info(f"Existing secrets backed up to {backup_dir}")

            # Copy secrets from store
            shutil.copytree(store_secrets_dir, secrets_dir)

            success(f"Secrets pulled to {secrets_dir}")

        except GitCommandError as e:
            error(f"Failed to pull secrets: {e}")

    def sync(self, secrets_dir: Path, message: Optional[str] = None) -> None:
        """Synchronize secrets (pull then push).

        Args:
            secrets_dir: Directory containing secrets
            message: Commit message
        """
        if not self._check_initialized():
            return

        info("Synchronizing secrets...")

        # First pull
        self.pull(secrets_dir)

        # Then push
        self.push(secrets_dir, message)

    def status(self) -> dict[str, Any]:
        """Get status of the secrets store.

        Returns:
            Status information
        """
        status = {
            "initialized": False,
            "store_path": str(self.store_path),
            "has_remote": False,
            "remote_url": None,
            "clean": True,
            "branch": None,
            "commit": None,
        }

        if not self._check_initialized(silent=True):
            return status

        try:
            repo = Repo(self.store_path)
            status["initialized"] = True
            status["clean"] = not repo.is_dirty()
            status["branch"] = repo.active_branch.name
            status["commit"] = str(repo.head.commit)[:8]

            if "origin" in repo.remotes:
                status["has_remote"] = True
                status["remote_url"] = repo.remotes.origin.url

        except Exception:
            pass

        return status

    def _check_initialized(self, silent: bool = False) -> bool:
        """Check if store is initialized.

        Args:
            silent: Don't print error message

        Returns:
            True if initialized
        """
        if not self.store_path.exists() or not (self.store_path / ".git").exists():
            if not silent:
                error("Store not initialized. Run 'mcli secrets store init' first.")
            return False
        return True
