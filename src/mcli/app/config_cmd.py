"""
Configuration management commands for MCLI.

This module provides the `mcli config` command group for managing
mcli configuration, including initialization, teardown, and settings.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import click
from rich.prompt import Prompt

from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console, error, info, success, warning

logger = get_logger(__name__)


@click.group(name="config")
def config():
    """
    Configuration management for mcli.

    Manage mcli settings, initialize/teardown workflows directories,
    and configure the workflow store.

    Examples:
        mcli config init           # Initialize workflows directory
        mcli config show           # Show current configuration
        mcli config store init     # Initialize git-based command store
    """
    pass


@config.command("init")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Initialize global workflows directory instead of local",
)
@click.option("--git", is_flag=True, help="Initialize git repository in workflows directory")
@click.option("--force", "-f", is_flag=True, help="Force initialization even if directory exists")
def config_init(is_global: bool, git: bool, force: bool):
    """
    Initialize workflows directory structure.

    Creates the necessary directories and configuration files for managing
    custom workflows. By default, creates a local .mcli/workflows/ directory
    if in a git repository, otherwise uses ~/.mcli/workflows/.

    Examples:
        mcli config init              # Initialize local workflows (if in git repo)
        mcli config init --global     # Initialize global workflows
        mcli config init --git        # Also initialize git repository
    """
    from mcli.lib.paths import get_git_root, get_local_mcli_dir, get_mcli_home, is_git_repository

    # Determine if we're in a git repository
    in_git_repo = is_git_repository() and not is_global
    git_root = get_git_root() if in_git_repo else None

    # Explicitly create workflows directory
    if not is_global and in_git_repo:
        local_mcli = get_local_mcli_dir()
        if local_mcli is not None:
            workflows_dir = local_mcli / "workflows"
        else:
            workflows_dir = get_mcli_home() / "workflows"
    else:
        workflows_dir = get_mcli_home() / "workflows"

    lockfile_path = workflows_dir / "commands.lock.json"

    # Check if already initialized
    if workflows_dir.exists() and not force:
        if lockfile_path.exists():
            warning(f"Workflows directory already initialized at: {workflows_dir}")
            info("Use --force to reinitialize")

            should_continue = Prompt.ask("Continue anyway?", choices=["y", "n"], default="n")
            if should_continue.lower() != "y":
                return 0

    # Create workflows directory
    workflows_dir.mkdir(parents=True, exist_ok=True)
    success(f"Created workflows directory: {workflows_dir}")

    # Create README.md
    readme_path = workflows_dir / "README.md"
    if not readme_path.exists() or force:
        scope_desc = f"for repository: {git_root.name}" if in_git_repo and git_root else "globally"

        readme_content = f"""# MCLI Custom Workflows

This directory contains custom workflow commands {scope_desc}.

## Quick Start

### Create a New Workflow

```bash
# Python workflow
mcli new my-workflow

# Shell workflow
mcli new my-script --language shell
```

### List Workflows

```bash
mcli list
```

### Run a Workflow

```bash
mcli run my-workflow
```

## Directory Structure

- `*.py` - Python workflow scripts
- `*.sh` - Shell workflow scripts
- `commands.lock.json` - Workflow lockfile (auto-generated)
"""

        with open(readme_path, "w") as f:
            f.write(readme_content)
        success(f"Created README.md")

    # Create lockfile if it doesn't exist
    if not lockfile_path.exists() or force:
        lockfile_content = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "commands": {},
        }
        with open(lockfile_path, "w") as f:
            json.dump(lockfile_content, f, indent=2)
        success(f"Created lockfile: {lockfile_path.name}")

    # Initialize git if requested
    if git:
        import subprocess

        git_dir = workflows_dir / ".git"
        if not git_dir.exists():
            result = subprocess.run(
                ["git", "init"],
                cwd=workflows_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                success("Initialized git repository")
            else:
                error(f"Failed to initialize git: {result.stderr}")
        else:
            info("Git repository already exists")

    # Show summary
    console.print()
    scope = "local" if in_git_repo else "global"
    console.print(f"[bold]Workflows initialized ({scope}):[/bold]")
    console.print(f"  Directory: {workflows_dir}")
    console.print(f"  Lockfile: {lockfile_path}")
    console.print()
    console.print("[dim]Create your first workflow with:[/dim]")
    console.print("  mcli new my-workflow")


@config.command("teardown")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Teardown global workflows directory",
)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def config_teardown(is_global: bool, force: bool):
    """
    Remove workflows directory and configuration.

    This will delete all custom workflows and configuration.
    Use with caution - this cannot be undone!

    Examples:
        mcli config teardown           # Remove local workflows
        mcli config teardown --global  # Remove global workflows
    """
    from mcli.lib.paths import get_local_mcli_dir, get_mcli_home, is_git_repository

    # Determine directory to remove
    in_git_repo = is_git_repository() and not is_global

    if not is_global and in_git_repo:
        local_mcli = get_local_mcli_dir()
        if local_mcli is not None:
            workflows_dir = local_mcli / "workflows"
        else:
            workflows_dir = get_mcli_home() / "workflows"
    else:
        workflows_dir = get_mcli_home() / "workflows"

    if not workflows_dir.exists():
        info(f"Workflows directory does not exist: {workflows_dir}")
        return 0

    # Count items
    items = list(workflows_dir.glob("*"))
    workflow_count = len([f for f in items if f.suffix in [".py", ".sh", ".js", ".ts", ".ipynb"]])

    if not force:
        warning(f"This will delete {workflow_count} workflow(s) from: {workflows_dir}")
        should_delete = Prompt.ask("Are you sure?", choices=["y", "n"], default="n")
        if should_delete.lower() != "y":
            info("Teardown cancelled")
            return 0

    try:
        shutil.rmtree(workflows_dir)
        success(f"Removed workflows directory: {workflows_dir}")
    except Exception as e:
        error(f"Failed to remove directory: {e}")
        return 1

    return 0


@config.command("show")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Show global configuration",
)
def config_show(is_global: bool):
    """
    Show current mcli configuration.

    Displays the current configuration including paths, settings,
    and environment variables.

    Examples:
        mcli config show           # Show local configuration
        mcli config show --global  # Show global configuration
    """
    from mcli.lib.paths import (
        get_custom_commands_dir,
        get_git_root,
        get_local_mcli_dir,
        get_mcli_home,
        is_git_repository,
    )

    console.print("[bold]MCLI Configuration[/bold]")
    console.print()

    # Environment
    in_git_repo = is_git_repository()
    git_root = get_git_root() if in_git_repo else None

    console.print("[bold cyan]Environment:[/bold cyan]")
    console.print(f"  In git repository: {'Yes' if in_git_repo else 'No'}")
    if git_root:
        console.print(f"  Git root: {git_root}")
    console.print()

    # Paths
    console.print("[bold cyan]Paths:[/bold cyan]")
    console.print(f"  MCLI home: {get_mcli_home()}")

    local_mcli = get_local_mcli_dir()
    if local_mcli:
        console.print(f"  Local .mcli: {local_mcli}")

    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    console.print(f"  Workflows directory: {workflows_dir}")

    lockfile = workflows_dir / "commands.lock.json"
    console.print(f"  Lockfile: {lockfile} ({'exists' if lockfile.exists() else 'missing'})")
    console.print()

    # Stats
    if workflows_dir.exists():
        console.print("[bold cyan]Workflows:[/bold cyan]")
        py_count = len(list(workflows_dir.glob("*.py")))
        sh_count = len(list(workflows_dir.glob("*.sh")))
        js_count = len(list(workflows_dir.glob("*.js")))
        ts_count = len(list(workflows_dir.glob("*.ts")))
        nb_count = len(list(workflows_dir.glob("*.ipynb")))
        total = py_count + sh_count + js_count + ts_count + nb_count

        console.print(f"  Total: {total}")
        if py_count:
            console.print(f"  Python: {py_count}")
        if sh_count:
            console.print(f"  Shell: {sh_count}")
        if js_count:
            console.print(f"  JavaScript: {js_count}")
        if ts_count:
            console.print(f"  TypeScript: {ts_count}")
        if nb_count:
            console.print(f"  Notebooks: {nb_count}")


# ============================================================
# Store Management Subgroup
# ============================================================


@config.group(name="store")
def config_store():
    """Git-based workflow store management.

    Sync workflows with a git repository for backup and sharing.

    Examples:
        mcli config store init          # Initialize store
        mcli config store push          # Push workflows to store
        mcli config store pull          # Pull workflows from store
        mcli config store sync          # Bidirectional sync
    """
    pass


# Default store configuration
DEFAULT_STORE_PATH = Path.home() / "repos" / "mcli-commands"


def _get_store_path() -> Path:
    """Get store path from config or default."""
    config_file = Path.home() / ".mcli" / "store.conf"

    if config_file.exists():
        store_path = Path(config_file.read_text().strip())
        if store_path.exists():
            return store_path

    return DEFAULT_STORE_PATH


@config_store.command(name="init")
@click.option("--path", "-p", type=click.Path(), help=f"Store path (default: {DEFAULT_STORE_PATH})")
@click.option("--remote", "-r", help="Git remote URL (optional)")
def store_init(path, remote):
    """Initialize workflow store with git.

    Creates a git repository for storing and syncing workflow commands.
    This enables version control and sharing of your workflow scripts.

    Examples:
        mcli config store init
        mcli config store init --path ~/my-workflows
        mcli config store init --remote git@github.com:user/workflows.git
    """
    import subprocess

    store_path = Path(path) if path else DEFAULT_STORE_PATH

    try:
        store_path.mkdir(parents=True, exist_ok=True)

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
                f"""# MCLI Workflow Store

Personal workflow commands for mcli framework.

## Usage

Push workflows:
```bash
mcli config store push
```

Pull workflows:
```bash
mcli config store pull
```

Sync (bidirectional):
```bash
mcli config store sync
```

Last updated: {datetime.now().isoformat()}
"""
            )

            if remote:
                subprocess.run(
                    ["git", "remote", "add", "origin", remote], cwd=store_path, check=True
                )
                success(f"Added remote: {remote}")
        else:
            info(f"Git repository already exists at {store_path}")

        # Save store path to config
        config_file = Path.home() / ".mcli" / "store.conf"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(str(store_path))

        success(f"Workflow store initialized at {store_path}")

    except subprocess.CalledProcessError as e:
        error(f"Git command failed: {e}")
    except Exception as e:
        error(f"Failed to initialize store: {e}")


@config_store.command(name="push")
@click.option("--message", "-m", help="Commit message")
def store_push(message):
    """Push workflow changes to git remote.

    Copies workflows to the store directory, commits changes,
    and pushes to the remote repository.

    Examples:
        mcli config store push
        mcli config store push -m "Added new backup workflow"
    """
    import subprocess

    from mcli.lib.paths import get_custom_commands_dir

    store_path = _get_store_path()
    if not store_path.exists():
        error(f"Store not initialized. Run 'mcli config store init' first.")
        return

    try:
        # Copy workflows to store
        workflows_dir = get_custom_commands_dir(global_mode=True)
        if workflows_dir.exists():
            for script in workflows_dir.glob("*"):
                if script.suffix in [".py", ".sh", ".js", ".ts", ".ipynb", ".json"]:
                    shutil.copy2(script, store_path / script.name)

        # Git add and commit
        subprocess.run(["git", "add", "."], cwd=store_path, check=True, capture_output=True)

        # Check if there are changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=store_path,
            capture_output=True,
        )

        if result.returncode == 0:
            info("No changes to commit.")
            return

        commit_msg = message or f"Update workflows: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=store_path,
            check=True,
            capture_output=True,
        )
        success("Changes committed.")

        # Push to remote
        try:
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=store_path,
                check=True,
                capture_output=True,
            )
            success("Pushed to remote.")
        except subprocess.CalledProcessError:
            warning("Could not push to remote. You may need to set up a remote first.")

    except Exception as e:
        error(f"Push failed: {e}")


@config_store.command(name="pull")
def store_pull():
    """Pull workflow updates from git remote.

    Pulls changes from the remote repository and copies
    workflows to your local workflows directory.

    Examples:
        mcli config store pull
    """
    import subprocess

    from mcli.lib.paths import get_custom_commands_dir

    store_path = _get_store_path()
    if not store_path.exists():
        error(f"Store not initialized. Run 'mcli config store init' first.")
        return

    try:
        # Pull from remote
        try:
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=store_path,
                check=True,
                capture_output=True,
            )
            success("Pulled from remote.")
        except subprocess.CalledProcessError:
            warning("Could not pull from remote.")

        # Copy workflows from store
        workflows_dir = get_custom_commands_dir(global_mode=True)
        workflows_dir.mkdir(parents=True, exist_ok=True)

        for script in store_path.glob("*"):
            if script.suffix in [".py", ".sh", ".js", ".ts", ".ipynb", ".json"]:
                shutil.copy2(script, workflows_dir / script.name)

        success(f"Workflows copied to {workflows_dir}")

    except Exception as e:
        error(f"Pull failed: {e}")


@config_store.command(name="status")
def store_status():
    """Show store status and pending changes.

    Displays git status of the workflow store,
    including uncommitted and unpushed changes.

    Examples:
        mcli config store status
    """
    import subprocess

    store_path = _get_store_path()
    if not store_path.exists():
        error(f"Store not initialized. Run 'mcli config store init' first.")
        return

    console.print(f"[bold]Store path:[/bold] {store_path}")

    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=store_path,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            console.print("\n[bold]Pending changes:[/bold]")
            console.print(result.stdout)
        else:
            success("No pending changes.")

    except Exception as e:
        error(f"Could not get status: {e}")
