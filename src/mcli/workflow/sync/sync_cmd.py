"""Multi-cloud synchronization commands for mcli."""

import asyncio
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class MultiCloudSync:
    """Handles synchronization across GitHub, OneDrive, iCloud, and Google Drive."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()
        self.sync_config_path = self.vault_path / ".mcli_sync_config.json"
        self.sync_log_path = self.vault_path / ".mcli_sync_log.json"

        # Cloud storage paths - these will need to be configured by user
        self.cloud_paths = {"onedrive": None, "icloud": None, "googledrive": None}

        self.load_config()

    def load_config(self) -> None:
        """Load sync configuration from file."""
        if self.sync_config_path.exists():
            try:
                with open(self.sync_config_path, "r") as f:
                    config = json.load(f)
                    self.cloud_paths.update(config.get("cloud_paths", {}))
                    logger.info(f"Loaded sync config from {self.sync_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load sync config: {e}")

    def save_config(self) -> None:
        """Save sync configuration to file."""
        config = {
            "cloud_paths": self.cloud_paths,
            "vault_path": str(self.vault_path),
            "last_updated": datetime.now().isoformat(),
        }
        try:
            with open(self.sync_config_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved sync config to {self.sync_config_path}")
        except Exception as e:
            logger.error(f"Failed to save sync config: {e}")

    def log_sync_action(self, action: str, target: str, status: str, details: str = "") -> None:
        """Log sync actions for debugging and auditing."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "status": status,
            "details": details,
        }

        # Load existing log
        logs = []
        if self.sync_log_path.exists():
            try:
                with open(self.sync_log_path, "r") as f:
                    logs = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load sync log: {e}")

        # Append new entry and keep only last 100 entries
        logs.append(log_entry)
        logs = logs[-100:]

        # Save log
        try:
            with open(self.sync_log_path, "w") as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save sync log: {e}")

    def sync_to_github(self) -> bool:
        """Sync vault to GitHub repository."""
        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "status"], cwd=self.vault_path, capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log_sync_action("git_sync", "github", "error", "Not a git repository")
                return False

            # Add all changes
            subprocess.run(["git", "add", "."], cwd=self.vault_path, check=True)

            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "diff", "--staged", "--quiet"], cwd=self.vault_path, capture_output=True
            )
            if result.returncode == 0:
                self.log_sync_action("git_sync", "github", "success", "No changes to commit")
                return True

            # Commit changes
            commit_msg = f"Auto-sync vault - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.vault_path, check=True)

            # Push to remote
            subprocess.run(["git", "push"], cwd=self.vault_path, check=True)

            self.log_sync_action(
                "git_sync", "github", "success", f"Committed and pushed: {commit_msg}"
            )
            return True

        except subprocess.CalledProcessError as e:
            self.log_sync_action("git_sync", "github", "error", str(e))
            logger.error(f"Git sync failed: {e}")
            return False

    def sync_to_cloud_storage(self, cloud_name: str) -> bool:
        """Sync vault to specified cloud storage."""
        cloud_path = self.cloud_paths.get(cloud_name)
        if not cloud_path:
            self.log_sync_action("cloud_sync", cloud_name, "error", "Cloud path not configured")
            return False

        cloud_path = Path(cloud_path)
        if not cloud_path.exists():
            try:
                cloud_path.mkdir(parents=True, exist_ok=True)
                self.log_sync_action(
                    "cloud_sync", cloud_name, "info", f"Created directory: {cloud_path}"
                )
            except Exception as e:
                self.log_sync_action(
                    "cloud_sync", cloud_name, "error", f"Failed to create directory: {e}"
                )
                return False

        try:
            # Use rsync for efficient sync (macOS has rsync built-in)
            result = subprocess.run(
                [
                    "rsync",
                    "-av",
                    "--delete",
                    "--exclude=.git",
                    "--exclude=.obsidian/workspace*",
                    "--exclude=.mcli_sync_*",
                    "--exclude=__pycache__",
                    "--exclude=*.pyc",
                    f"{self.vault_path}/",
                    f"{cloud_path}/",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log_sync_action("cloud_sync", cloud_name, "success", f"Synced to {cloud_path}")
                return True
            else:
                self.log_sync_action("cloud_sync", cloud_name, "error", result.stderr)
                return False

        except Exception as e:
            self.log_sync_action("cloud_sync", cloud_name, "error", str(e))
            logger.error(f"Cloud sync to {cloud_name} failed: {e}")
            return False

    def sync_from_cloud_storage(self, cloud_name: str) -> bool:
        """Sync from cloud storage to vault."""
        cloud_path = self.cloud_paths.get(cloud_name)
        if not cloud_path or not Path(cloud_path).exists():
            self.log_sync_action("cloud_pull", cloud_name, "error", "Cloud path not found")
            return False

        try:
            # Use rsync to pull changes from cloud
            result = subprocess.run(
                [
                    "rsync",
                    "-av",
                    "--exclude=.git",
                    "--exclude=.obsidian/workspace*",
                    "--exclude=.mcli_sync_*",
                    "--exclude=__pycache__",
                    "--exclude=*.pyc",
                    f"{cloud_path}/",
                    f"{self.vault_path}/",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.log_sync_action(
                    "cloud_pull", cloud_name, "success", f"Pulled from {cloud_path}"
                )
                return True
            else:
                self.log_sync_action("cloud_pull", cloud_name, "error", result.stderr)
                return False

        except Exception as e:
            self.log_sync_action("cloud_pull", cloud_name, "error", str(e))
            logger.error(f"Cloud pull from {cloud_name} failed: {e}")
            return False

    def get_sync_status(self) -> Dict:
        """Get current sync status for all configured targets."""
        status = {
            "vault_path": str(self.vault_path),
            "last_check": datetime.now().isoformat(),
            "targets": {},
        }

        # Check git status
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                has_changes = bool(result.stdout.strip())
                status["targets"]["github"] = {
                    "configured": True,
                    "has_uncommitted_changes": has_changes,
                    "status": "dirty" if has_changes else "clean",
                }
            else:
                status["targets"]["github"] = {"configured": False, "error": "Not a git repository"}
        except Exception as e:
            status["targets"]["github"] = {"configured": False, "error": str(e)}

        # Check cloud storage paths
        for cloud_name, cloud_path in self.cloud_paths.items():
            if cloud_path:
                path_obj = Path(cloud_path)
                status["targets"][cloud_name] = {
                    "configured": True,
                    "path": cloud_path,
                    "exists": path_obj.exists(),
                    "accessible": path_obj.exists() and os.access(path_obj, os.R_OK | os.W_OK),
                }
            else:
                status["targets"][cloud_name] = {"configured": False, "path": None}

        return status


@click.group(name="sync")
def sync():
    """Multi-cloud synchronization commands for vault management."""
    pass


# Import and register test commands
try:
    from .test_cmd import test as sync_test

    sync.add_command(sync_test)
except ImportError:
    pass


@sync.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
def status(vault_path):
    """Show sync status for all configured targets."""
    syncer = MultiCloudSync(vault_path)
    status_info = syncer.get_sync_status()

    click.echo(f"📁 Vault: {status_info['vault_path']}")
    click.echo(f"🕒 Last check: {status_info['last_check']}")
    click.echo()

    for target, info in status_info["targets"].items():
        if info["configured"]:
            if target == "github":
                icon = "📚" if info["status"] == "clean" else "⚠️"
                click.echo(f"{icon} {target.title()}: {info['status']}")
                if info.get("has_uncommitted_changes"):
                    click.echo(f"   └─ Uncommitted changes present")
            else:
                icon = "☁️" if info["accessible"] else "❌"
                click.echo(
                    f"{icon} {target.title()}: {'accessible' if info['accessible'] else 'not accessible'}"
                )
                click.echo(f"   └─ Path: {info['path']}")
        else:
            click.echo(f"⚪ {target.title()}: not configured")
            if "error" in info:
                click.echo(f"   └─ Error: {info['error']}")


@sync.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
@click.option("--onedrive", help="Path to OneDrive sync folder")
@click.option("--icloud", help="Path to iCloud Drive sync folder")
@click.option("--googledrive", help="Path to Google Drive sync folder")
def configure(vault_path, onedrive, icloud, googledrive):
    """Configure cloud storage paths for synchronization."""
    syncer = MultiCloudSync(vault_path)

    if onedrive:
        syncer.cloud_paths["onedrive"] = onedrive
        click.echo(f"✅ OneDrive path set to: {onedrive}")

    if icloud:
        syncer.cloud_paths["icloud"] = icloud
        click.echo(f"✅ iCloud path set to: {icloud}")

    if googledrive:
        syncer.cloud_paths["googledrive"] = googledrive
        click.echo(f"✅ Google Drive path set to: {googledrive}")

    syncer.save_config()
    click.echo("🔧 Configuration saved!")


@sync.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
@click.option(
    "--target",
    type=click.Choice(["all", "github", "onedrive", "icloud", "googledrive"]),
    default="all",
    help="Sync target",
)
def push(vault_path, target):
    """Push vault changes to specified target(s)."""
    syncer = MultiCloudSync(vault_path)

    targets = [target] if target != "all" else ["github", "onedrive", "icloud", "googledrive"]

    results = {}

    for t in targets:
        if t == "github":
            click.echo(f"🔄 Syncing to GitHub...")
            results[t] = syncer.sync_to_github()
        else:
            if syncer.cloud_paths.get(t):
                click.echo(f"🔄 Syncing to {t.title()}...")
                results[t] = syncer.sync_to_cloud_storage(t)
            else:
                click.echo(f"⚠️ {t.title()} not configured, skipping...")
                results[t] = False

    # Show results
    click.echo("\n📊 Sync Results:")
    for target_name, success in results.items():
        icon = "✅" if success else "❌"
        click.echo(f"{icon} {target_name.title()}: {'Success' if success else 'Failed'}")


@sync.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
@click.option(
    "--target",
    type=click.Choice(["onedrive", "icloud", "googledrive"]),
    required=True,
    help="Cloud storage to pull from",
)
def pull(vault_path, target):
    """Pull changes from cloud storage to vault."""
    syncer = MultiCloudSync(vault_path)

    if not syncer.cloud_paths.get(target):
        click.echo(f"❌ {target.title()} not configured!")
        return

    click.echo(f"🔄 Pulling from {target.title()}...")
    success = syncer.sync_from_cloud_storage(target)

    if success:
        click.echo(f"✅ Successfully pulled from {target.title()}")
    else:
        click.echo(f"❌ Failed to pull from {target.title()}")


@sync.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
@click.option("--lines", default=20, help="Number of log lines to show")
def logs(vault_path, lines):
    """Show sync operation logs."""
    syncer = MultiCloudSync(vault_path)

    if not syncer.sync_log_path.exists():
        click.echo("📝 No sync logs found.")
        return

    try:
        with open(syncer.sync_log_path, "r") as f:
            logs_data = json.load(f)

        # Show last N entries
        recent_logs = logs_data[-lines:]

        click.echo(f"📝 Last {len(recent_logs)} sync operations:")
        click.echo()

        for log_entry in recent_logs:
            timestamp = log_entry.get("timestamp", "Unknown")
            action = log_entry.get("action", "Unknown")
            target = log_entry.get("target", "Unknown")
            status = log_entry.get("status", "Unknown")
            details = log_entry.get("details", "")

            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = timestamp

            # Status icon
            icon = {"success": "✅", "error": "❌", "info": "ℹ️"}.get(status, "📝")

            click.echo(f"{icon} {time_str} | {action} → {target} | {status}")
            if details:
                click.echo(f"   └─ {details}")

    except Exception as e:
        click.echo(f"❌ Failed to read logs: {e}")


if __name__ == "__main__":
    sync()
