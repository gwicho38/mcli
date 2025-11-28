"""
Command Store Management - Sync ~/.mcli/commands/ to git
Similar to lsh secrets but for workflow commands
"""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import click

from mcli.lib.constants.paths import DirNames
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import error, info, success, warning

logger = get_logger()

# Default store location
DEFAULT_STORE_PATH = Path.home() / "repos" / "mcli-commands"
COMMANDS_PATH = Path.home() / DirNames.MCLI / "commands"


@click.group(name="store")
def store():
    """Manage command store - sync ~/.mcli/commands/ to git."""


@store.command(name="init")
@click.option("--path", "-p", type=click.Path(), help=f"Store path (default: {DEFAULT_STORE_PATH})")
@click.option("--remote", "-r", help="Git remote URL (optional)")
def init_store(path, remote):
    """Initialize command store with git."""
    store_path = Path(path) if path else DEFAULT_STORE_PATH

    try:
        # Create store directory
        store_path.mkdir(parents=True, exist_ok=True)

        # Initialize git if not already initialized
        git_dir = store_path / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=store_path, check=True, capture_output=True)
            success(f"Initialized git repository at {store_path}")

            # Create .gitignore
            gitignore = store_path / ".gitignore"
            gitignore.write_text("*.backup\n.DS_Store\n")

            # Create README
            readme = store_path / "README.md"
            readme.write_text(
                f"""# MCLI Commands Store

Personal workflow commands for mcli framework.

## Usage

Push commands:
```bash
mcli self store push
```

Pull commands:
```bash
mcli self store pull
```

Sync (bidirectional):
```bash
mcli self store sync
```

## Structure

All JSON command files from `~/.mcli/commands/` are stored here and version controlled.

Last updated: {datetime.now().isoformat()}
"""
            )

            # Add remote if provided
            if remote:
                subprocess.run(
                    ["git", "remote", "add", "origin", remote], cwd=store_path, check=True
                )
                success(f"Added remote: {remote}")
        else:
            info(f"Git repository already exists at {store_path}")

        # Save store path to config
        config_file = Path.home() / DirNames.MCLI / "store.conf"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(str(store_path))

        success(f"Command store initialized at {store_path}")
        info(f"Store path saved to {config_file}")

    except subprocess.CalledProcessError as e:
        error(f"Git command failed: {e}")
        logger.error(f"Git init failed: {e}")
    except Exception as e:
        error(f"Failed to initialize store: {e}")
        logger.exception(e)


@store.command(name="push")
@click.option("--message", "-m", help="Commit message")
@click.option("--all", "-a", is_flag=True, help="Push all files (including backups)")
def push_commands(message, all):
    """Push commands from ~/.mcli/commands/ to git store."""
    try:
        store_path = _get_store_path()

        # Copy commands to store
        info(f"Copying commands from {COMMANDS_PATH} to {store_path}...")

        copied_count = 0
        for item in COMMANDS_PATH.glob("*"):
            # Skip backups unless --all specified
            if not all and item.name.endswith(".backup"):
                continue

            dest = store_path / item.name
            if item.is_file():
                shutil.copy2(item, dest)
                copied_count += 1
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
                copied_count += 1

        success(f"Copied {copied_count} items to store")

        # Git add, commit, push
        subprocess.run(["git", "add", "."], cwd=store_path, check=True)

        # Check if there are changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=store_path, capture_output=True, text=True
        )

        if not result.stdout.strip():
            info("No changes to commit")
            return

        # Commit with message
        commit_msg = message or f"Update commands {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=store_path, check=True)
        success(f"Committed changes: {commit_msg}")

        # Push to remote if configured
        try:
            subprocess.run(["git", "push"], cwd=store_path, check=True, capture_output=True)
            success("Pushed to remote")
        except subprocess.CalledProcessError:
            warning("No remote configured or push failed. Commands committed locally.")

    except Exception as e:
        error(f"Failed to push commands: {e}")
        logger.exception(e)


@store.command(name="pull")
@click.option("--force", "-f", is_flag=True, help="Overwrite local commands without backup")
def pull_commands(force):
    """Pull commands from git store to ~/.mcli/commands/."""
    try:
        store_path = _get_store_path()

        # Pull from remote
        try:
            subprocess.run(["git", "pull"], cwd=store_path, check=True)
            success("Pulled latest changes from remote")
        except subprocess.CalledProcessError:
            warning("No remote configured or pull failed. Using local store.")

        # Backup existing commands if not force
        if not force and COMMANDS_PATH.exists():
            backup_dir = (
                COMMANDS_PATH.parent / f"commands_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.copytree(COMMANDS_PATH, backup_dir)
            info(f"Backed up existing commands to {backup_dir}")

        # Copy from store to commands directory
        info(f"Copying commands from {store_path} to {COMMANDS_PATH}...")

        COMMANDS_PATH.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        for item in store_path.glob("*"):
            # Skip git directory and README
            if item.name in [".git", "README.md", ".gitignore"]:
                continue

            dest = COMMANDS_PATH / item.name
            if item.is_file():
                shutil.copy2(item, dest)
                copied_count += 1
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
                copied_count += 1

        success(f"Pulled {copied_count} items from store")

    except Exception as e:
        error(f"Failed to pull commands: {e}")
        logger.exception(e)


@store.command(name="sync")
@click.option("--message", "-m", help="Commit message if pushing")
def sync_commands(message):
    """Sync commands bidirectionally (pull then push if changes)."""
    try:
        store_path = _get_store_path()

        # First pull
        info("Pulling latest changes...")
        try:
            subprocess.run(["git", "pull"], cwd=store_path, check=True, capture_output=True)
            success("Pulled from remote")
        except subprocess.CalledProcessError:
            warning("No remote or pull failed")

        # Then push local changes
        info("Pushing local changes...")

        # Copy commands
        for item in COMMANDS_PATH.glob("*"):
            if item.name.endswith(".backup"):
                continue
            dest = store_path / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)

        # Check for changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=store_path, capture_output=True, text=True
        )

        if not result.stdout.strip():
            success("Everything in sync!")
            return

        # Commit and push
        subprocess.run(["git", "add", "."], cwd=store_path, check=True)
        commit_msg = message or f"Sync commands {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=store_path, check=True)

        try:
            subprocess.run(["git", "push"], cwd=store_path, check=True, capture_output=True)
            success("Synced and pushed to remote")
        except subprocess.CalledProcessError:
            success("Synced locally (no remote configured)")

    except Exception as e:
        error(f"Sync failed: {e}")
        logger.exception(e)


@store.command(name="list")
@click.option("--store", "-s", is_flag=True, help="List store instead of local")
def list_commands(store):
    """List all commands."""
    try:
        if store:
            store_path = _get_store_path()
            path = store_path
            title = f"Commands in store ({store_path})"
        else:
            path = COMMANDS_PATH
            title = f"Local commands ({COMMANDS_PATH})"

        click.echo(f"\n{title}:\n")

        if not path.exists():
            warning(f"Directory does not exist: {path}")
            return

        items = sorted(path.glob("*"))
        if not items:
            info("No commands found")
            return

        for item in items:
            if item.name in [".git", ".gitignore", "README.md"]:
                continue

            if item.is_file():
                size = item.stat().st_size / 1024
                modified = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                click.echo(f"  📄 {item.name:<40} {size:>8.1f} KB  {modified}")
            elif item.is_dir():
                count = len(list(item.glob("*")))
                click.echo(f"  📁 {item.name:<40} {count:>3} files")

        click.echo()

    except Exception as e:
        error(f"Failed to list commands: {e}")
        logger.exception(e)


@store.command(name="status")
def store_status():
    """Show git status of command store."""
    try:
        store_path = _get_store_path()

        click.echo(f"\n📦 Store: {store_path}\n")

        # Git status
        result = subprocess.run(
            ["git", "status", "--short", "--branch"], cwd=store_path, capture_output=True, text=True
        )

        if result.stdout:
            click.echo(result.stdout)

        # Show remote
        result = subprocess.run(
            ["git", "remote", "-v"], cwd=store_path, capture_output=True, text=True
        )

        if result.stdout:
            click.echo("\n🌐 Remotes:")
            click.echo(result.stdout)
        else:
            info("\nNo remote configured")

        click.echo()

    except Exception as e:
        error(f"Failed to get status: {e}")
        logger.exception(e)


@store.command(name="show")
@click.argument("command_name")
@click.option("--store", "-s", is_flag=True, help="Show from store instead of local")
def show_command(command_name, store):
    """Show command file contents."""
    try:
        if store:
            store_path = _get_store_path()
            path = store_path / command_name
        else:
            path = COMMANDS_PATH / command_name

        if not path.exists():
            error(f"Command not found: {command_name}")
            return

        if path.is_file():
            click.echo(f"\n📄 {path}:\n")
            click.echo(path.read_text())
        else:
            info(f"{command_name} is a directory")
            for item in sorted(path.glob("*")):
                click.echo(f"  {item.name}")

        click.echo()

    except Exception as e:
        error(f"Failed to show command: {e}")
        logger.exception(e)


@store.command(name="config")
@click.option("--remote", "-r", help="Set git remote URL")
@click.option("--path", "-p", type=click.Path(), help="Change store path")
def configure_store(remote, path):
    """Configure store settings."""
    try:
        store_path = _get_store_path()

        if path:
            new_path = Path(path).expanduser().resolve()
            config_file = Path.home() / DirNames.MCLI / "store.conf"
            config_file.write_text(str(new_path))
            success(f"Store path updated to: {new_path}")
            return

        if remote:
            # Check if remote exists
            result = subprocess.run(
                ["git", "remote"], cwd=store_path, capture_output=True, text=True
            )

            if "origin" in result.stdout:
                subprocess.run(
                    ["git", "remote", "set-url", "origin", remote], cwd=store_path, check=True
                )
                success(f"Updated remote URL: {remote}")
            else:
                subprocess.run(
                    ["git", "remote", "add", "origin", remote], cwd=store_path, check=True
                )
                success(f"Added remote URL: {remote}")

    except Exception as e:
        error(f"Configuration failed: {e}")
        logger.exception(e)


def _get_store_path() -> Path:
    """Get store path from config or default."""
    config_file = Path.home() / DirNames.MCLI / "store.conf"

    if config_file.exists():
        store_path = Path(config_file.read_text().strip())
        if store_path.exists():
            return store_path

    # Use default
    return DEFAULT_STORE_PATH


if __name__ == "__main__":
    store()
