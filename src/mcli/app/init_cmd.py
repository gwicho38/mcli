"""
Top-level initialization and teardown commands for MCLI.
"""

import json
import shutil
import subprocess
from datetime import datetime
from typing import Any

import click
from rich.prompt import Prompt

from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger(__name__)


@click.command("init")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Initialize global workflows directory instead of local",
)
@click.option("--git", is_flag=True, help="Initialize git repository in workflows directory")
@click.option("--force", "-f", is_flag=True, help="Force initialization even if directory exists")
def init(is_global, git, force):
    """
    Initialize workflows directory structure.

    Creates the necessary directories and configuration files for managing
    custom workflows. By default, creates a local .mcli/workflows/ directory
    if in a git repository, otherwise uses ~/.mcli/workflows/.

    Examples:
        mcli init              # Initialize local workflows (if in git repo)
        mcli init --global     # Initialize global workflows
        mcli init --git        # Also initialize git repository
    """
    from mcli.lib.paths import get_git_root, get_local_mcli_dir, get_mcli_home, is_git_repository

    # Determine if we're in a git repository
    in_git_repo = is_git_repository() and not is_global
    git_root = get_git_root() if in_git_repo else None

    # Explicitly create workflows directory (not commands)
    # This bypasses the migration logic that would check for old commands/ directory
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
    if workflows_dir.exists() and not force:  # noqa: SIM102
        if lockfile_path.exists():
            console.print(
                f"[yellow]Workflows directory already initialized at:[/yellow] {workflows_dir}"
            )
            console.print("[dim]Use --force to reinitialize[/dim]")

            should_continue = Prompt.ask("Continue anyway?", choices=["y", "n"], default="n")
            if should_continue.lower() != "y":
                return 0

    # Create workflows directory
    workflows_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Created workflows directory: {workflows_dir}")

    # Create README.md
    readme_path = workflows_dir / "README.md"
    if not readme_path.exists() or force:
        "local" if in_git_repo else "global"
        scope_desc = f"for repository: {git_root.name}" if in_git_repo and git_root else "globally"

        readme_content = f"""# MCLI Custom Workflows

This directory contains custom workflow commands {scope_desc}.

## Quick Start

### Create a New Workflow

```bash
# Python workflow
mcli workflow add my-workflow

# Shell workflow
mcli workflow add my-script --language shell
```

### List Workflows

```bash
mcli workflow list --custom-only
```

### Execute a Workflow

```bash
mcli workflows my-workflow
```

### Edit a Workflow

```bash
mcli workflow edit my-workflow
```

### Export/Import Workflows

```bash
# Export all workflows
mcli workflow export workflows-backup.json

# Import workflows
mcli workflow import workflows-backup.json
```

## Directory Structure

```
{workflows_dir.name}/
├── README.md              # This file
├── commands.lock.json     # Lockfile for workflow state
└── *.json                 # Individual workflow definitions
```

## Workflow Format

Workflows are stored as JSON files with the following structure:

```json
{{
  "name": "workflow-name",
  "description": "Workflow description",
  "code": "Python or shell code",
  "language": "python",
  "group": "workflow",
  "version": "1.0",
  "created_at": "2025-10-30T...",
  "updated_at": "2025-10-30T..."
}}
```

## Scope

- **Scope**: {'Local (repository-specific)' if in_git_repo else 'Global (user-wide)'}
- **Location**: `{workflows_dir}`
{f"- **Git Repository**: `{git_root}`" if git_root else ""}

## Documentation

- [MCLI Documentation](https://github.com/gwicho38/mcli)
- [Workflow Guide](https://github.com/gwicho38/mcli/blob/main/docs/features/LOCAL_VS_GLOBAL_COMMANDS.md)

---

*Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        readme_path.write_text(readme_content)
        console.print(f"[green]✓[/green] Created README: {readme_path.name}")

    # Initialize lockfile
    if not lockfile_path.exists() or force:
        lockfile_data: dict[str, Any] = {
            "version": "1.0",
            "initialized_at": datetime.now().isoformat(),
            "scope": "local" if in_git_repo else "global",
            "commands": {},
        }

        with open(lockfile_path, "w") as f:
            json.dump(lockfile_data, f, indent=2)

        console.print(f"[green]✓[/green] Initialized lockfile: {lockfile_path.name}")

    # Create .gitignore if in workflows directory
    gitignore_path = workflows_dir / ".gitignore"
    if not gitignore_path.exists() or force:
        gitignore_content = """# Backup files
*.backup
*.bak

# Temporary files
*.tmp
*.temp

# OS files
.DS_Store
Thumbs.db

# Editor files
*.swp
*.swo
*~
.vscode/
.idea/
"""
        gitignore_path.write_text(gitignore_content)
        console.print("[green]✓[/green] Created .gitignore")

    # Initialize git if requested
    if git and not (workflows_dir / ".git").exists():
        try:
            subprocess.run(["git", "init"], cwd=workflows_dir, check=True, capture_output=True)
            console.print("[green]✓[/green] Initialized git repository in workflows directory")

            # Create initial commit
            subprocess.run(["git", "add", "."], cwd=workflows_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit: Initialize workflows directory"],
                cwd=workflows_dir,
                check=True,
                capture_output=True,
            )
            console.print("[green]✓[/green] Created initial commit")

        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]⚠[/yellow] Git initialization failed: {e}")
        except FileNotFoundError:
            console.print("[yellow]⚠[/yellow] Git not found. Skipping git initialization.")

    # Summary
    from rich.table import Table

    console.print()
    console.print("[bold green]Workflows directory initialized successfully![/bold green]")
    console.print()

    # Display summary table
    table = Table(title="Initialization Summary", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Scope", "Local (repository-specific)" if in_git_repo else "Global (user-wide)")
    table.add_row("Location", str(workflows_dir))
    if git_root:
        table.add_row("Git Repository", str(git_root))
    table.add_row("Lockfile", str(lockfile_path))
    table.add_row("Git Initialized", "Yes" if git and (workflows_dir / ".git").exists() else "No")

    console.print(table)
    console.print()

    # Next steps
    console.print("[bold]Next Steps:[/bold]")
    console.print("  1. Create a workflow:  [cyan]mcli workflow add my-workflow[/cyan]")
    console.print("  2. List workflows:     [cyan]mcli workflow list --custom-only[/cyan]")
    console.print("  3. Execute workflow:   [cyan]mcli workflows my-workflow[/cyan]")
    console.print(f"  4. View README:        [cyan]cat {workflows_dir}/README.md[/cyan]")
    console.print()

    if in_git_repo:
        console.print(
            "[dim]Tip: Workflows are local to this repository. Use --global for user-wide workflows.[/dim]"
        )
    else:
        console.print(
            "[dim]Tip: Use workflows in any git repository, or create local ones with 'mcli init' inside repos.[/dim]"
        )

    return 0


@click.command("teardown")
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Teardown global workflows directory instead of local",
)
@click.option("--force", "-f", is_flag=True, help="Skip all confirmation prompts")
def teardown(is_global, force):
    """
    Remove all local MCLI artifacts.

    This command deletes the workflows directory and all associated files.
    By default, operates on local workflows (if in git repo), use --global for
    global workflows.

    For safety, you must type the name of the current directory to confirm.

    Examples:
        mcli teardown              # Remove local workflows (requires confirmation)
        mcli teardown --global     # Remove global workflows (requires confirmation)
        mcli teardown --force      # Skip confirmations (dangerous!)
    """
    from mcli.lib.paths import get_git_root, get_local_mcli_dir, get_mcli_home, is_git_repository

    # Determine which directory to teardown
    in_git_repo = is_git_repository() and not is_global
    git_root = get_git_root() if in_git_repo else None

    if not is_global and in_git_repo:
        local_mcli = get_local_mcli_dir()
        if local_mcli is not None:
            workflows_dir = local_mcli / "workflows"
        else:
            workflows_dir = get_mcli_home() / "workflows"
        scope = "local"
        scope_display = git_root.name if git_root else "current repository"
    else:
        workflows_dir = get_mcli_home() / "workflows"
        scope = "global"
        scope_display = "global (~/.mcli)"

    # Check if workflows directory exists
    if not workflows_dir.exists():
        console.print(f"[yellow]No workflows directory found at:[/yellow] {workflows_dir}")
        console.print("[dim]Nothing to teardown.[/dim]")
        return 0

    # Display what will be removed
    console.print(f"[bold red]⚠ WARNING: This will delete all {scope} MCLI artifacts[/bold red]")
    console.print()
    console.print(f"[bold]Scope:[/bold] {scope_display}")
    console.print(f"[bold]Directory:[/bold] {workflows_dir}")

    # Count files
    try:
        file_count = sum(1 for _ in workflows_dir.rglob("*") if _.is_file())
        console.print(f"[bold]Files to delete:[/bold] {file_count}")
    except Exception:
        console.print("[bold]Files to delete:[/bold] unknown")

    console.print()

    # Safety confirmation
    if not force:
        console.print("[yellow]This action cannot be undone![/yellow]")
        console.print()

        if in_git_repo and git_root:
            # For local repos, require typing the repo name
            expected_name = git_root.name
            console.print(
                f"[bold]To confirm, type the repository name:[/bold] [cyan]{expected_name}[/cyan]"
            )
        else:
            # For global, require typing "global"
            expected_name = "global"
            console.print(f"[bold]To confirm, type:[/bold] [cyan]{expected_name}[/cyan]")

        confirmation = Prompt.ask("Confirmation")

        if confirmation != expected_name:
            console.print("[red]Confirmation failed. Teardown cancelled.[/red]")
            return 1

    # Perform teardown
    try:
        console.print()
        console.print("[yellow]Removing workflows directory...[/yellow]")

        shutil.rmtree(workflows_dir)

        console.print(f"[green]✓[/green] Removed: {workflows_dir}")

        # Also remove parent .mcli directory if empty (local only)
        if not is_global and in_git_repo:
            try:
                parent_dir = workflows_dir.parent
                if parent_dir.exists() and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    console.print(f"[green]✓[/green] Removed empty directory: {parent_dir}")
            except OSError:
                pass  # Directory not empty, that's fine

        console.print()
        console.print("[bold green]Teardown complete![/bold green]")

        if in_git_repo:
            console.print(
                "[dim]Local workflows removed. Global workflows (if any) are still available.[/dim]"
            )
        else:
            console.print(
                "[dim]Global workflows removed. Local workflows (if any) are still available.[/dim]"
            )

        return 0

    except Exception as e:
        console.print(f"[red]Error during teardown: {e}[/red]")
        logger.exception(e)
        return 1
