"""
Migration commands for mcli self-management.

Handles migrations between different versions of mcli, including:
- Directory structure changes
- Configuration format changes
- Command structure changes
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import error, info, success, warning

logger = get_logger(__name__)
console = Console()


def get_migration_status() -> dict:
    """
    Check the current migration status.

    Returns:
        Dictionary with migration status information
    """
    mcli_home = Path.home() / ".mcli"
    old_commands_dir = mcli_home / "commands"
    new_workflows_dir = mcli_home / "workflows"

    status = {
        "old_dir_exists": old_commands_dir.exists(),
        "old_dir_path": str(old_commands_dir),
        "new_dir_exists": new_workflows_dir.exists(),
        "new_dir_path": str(new_workflows_dir),
        "needs_migration": False,
        "files_to_migrate": [],
        "migration_done": False,
    }

    # Check if migration is needed
    if old_commands_dir.exists():
        # Count files that need migration (excluding hidden files)
        files = [
            f for f in old_commands_dir.iterdir()
            if f.is_file() and not f.name.startswith('.')
        ]
        status["files_to_migrate"] = [f.name for f in files]
        status["needs_migration"] = len(files) > 0

    # Check if migration already done
    if new_workflows_dir.exists() and not old_commands_dir.exists():
        status["migration_done"] = True

    return status


def migrate_commands_to_workflows(dry_run: bool = False, force: bool = False) -> Tuple[bool, str]:
    """
    Migrate ~/.mcli/commands to ~/.mcli/workflows.

    Args:
        dry_run: If True, show what would be done without actually doing it
        force: If True, proceed even if workflows directory exists

    Returns:
        Tuple of (success, message)
    """
    mcli_home = Path.home() / ".mcli"
    old_dir = mcli_home / "commands"
    new_dir = mcli_home / "workflows"

    # Check if old directory exists
    if not old_dir.exists():
        return False, f"Nothing to migrate: {old_dir} does not exist"

    # Check if new directory already exists
    if new_dir.exists() and not force:
        return False, f"Target directory {new_dir} already exists. Use --force to override."

    # Get list of files to migrate
    files_to_migrate = [
        f for f in old_dir.iterdir()
        if f.is_file() and not f.name.startswith('.')
    ]

    if not files_to_migrate:
        return False, f"No files to migrate in {old_dir}"

    if dry_run:
        message = f"[DRY RUN] Would migrate {len(files_to_migrate)} files from {old_dir} to {new_dir}"
        return True, message

    try:
        # Create new directory if it doesn't exist
        new_dir.mkdir(parents=True, exist_ok=True)

        # Track migrated files
        migrated_files = []
        skipped_files = []

        # Move files
        for file_path in files_to_migrate:
            target_path = new_dir / file_path.name

            # Check if file already exists in target
            if target_path.exists():
                if force:
                    # Backup existing file
                    backup_path = target_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d%H%M%S')}")
                    shutil.move(str(target_path), str(backup_path))
                    logger.info(f"Backed up existing file to {backup_path}")
                else:
                    skipped_files.append(file_path.name)
                    continue

            # Move the file
            shutil.move(str(file_path), str(target_path))
            migrated_files.append(file_path.name)
            logger.info(f"Migrated: {file_path.name}")

        # Check if old directory is now empty (only hidden files remain)
        remaining_files = [
            f for f in old_dir.iterdir()
            if f.is_file() and not f.name.startswith('.')
        ]

        # If empty, remove old directory
        if not remaining_files:
            # Keep hidden files like .gitignore but remove directory if truly empty
            all_remaining = list(old_dir.iterdir())
            if not all_remaining:
                old_dir.rmdir()
                logger.info(f"Removed empty directory: {old_dir}")

        # Create migration report
        report_lines = [
            f"Successfully migrated {len(migrated_files)} files from {old_dir} to {new_dir}"
        ]

        if skipped_files:
            report_lines.append(f"Skipped {len(skipped_files)} files (already exist in target)")

        if remaining_files:
            report_lines.append(f"Note: {len(remaining_files)} files remain in {old_dir}")

        return True, "\n".join(report_lines)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False, f"Migration failed: {str(e)}"


@click.command(name="migrate", help="Perform system migrations for mcli")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually doing it",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force migration even if target directory exists",
)
@click.option(
    "--status",
    is_flag=True,
    help="Show migration status without performing migration",
)
def migrate_command(dry_run: bool, force: bool, status: bool):
    """
    Migrate mcli configuration and data to new structure.

    Currently handles:
    - Moving ~/.mcli/commands to ~/.mcli/workflows

    Examples:
        mcli self migrate --status       # Check migration status
        mcli self migrate --dry-run      # See what would be done
        mcli self migrate                # Perform migration
        mcli self migrate --force        # Force migration (overwrite existing)
    """

    # Get current status
    migration_status = get_migration_status()

    # If --status flag, just show status and exit
    if status:
        console.print("\n[bold cyan]Migration Status[/bold cyan]")
        console.print(f"\n[bold]Old location:[/bold] {migration_status['old_dir_path']}")
        console.print(f"  Exists: {'✓ Yes' if migration_status['old_dir_exists'] else '✗ No'}")

        console.print(f"\n[bold]New location:[/bold] {migration_status['new_dir_path']}")
        console.print(f"  Exists: {'✓ Yes' if migration_status['new_dir_exists'] else '✗ No'}")

        if migration_status['needs_migration']:
            console.print(f"\n[yellow]⚠ Migration needed[/yellow]")
            console.print(f"Files to migrate: {len(migration_status['files_to_migrate'])}")

            if migration_status['files_to_migrate']:
                table = Table(title="Files to Migrate")
                table.add_column("File Name", style="cyan")

                for filename in sorted(migration_status['files_to_migrate']):
                    table.add_row(filename)

                console.print(table)

            console.print(f"\n[dim]Run 'mcli self migrate' to perform migration[/dim]")
        elif migration_status['migration_done']:
            console.print(f"\n[green]✓ Migration already completed[/green]")
        else:
            console.print(f"\n[green]✓ No migration needed[/green]")

        return

    # Check if migration is needed
    if not migration_status['needs_migration']:
        if migration_status['migration_done']:
            info("Migration already completed")
            info(f"Workflows directory: {migration_status['new_dir_path']}")
        else:
            info("No migration needed")
        return

    # Show what will be migrated
    console.print("\n[bold cyan]Migration Plan[/bold cyan]")
    console.print(f"\nSource: [cyan]{migration_status['old_dir_path']}[/cyan]")
    console.print(f"Target: [cyan]{migration_status['new_dir_path']}[/cyan]")
    console.print(f"Files: [yellow]{len(migration_status['files_to_migrate'])}[/yellow]")

    if dry_run:
        console.print(f"\n[yellow]DRY RUN MODE - No changes will be made[/yellow]")

    # Perform migration
    success_flag, message = migrate_commands_to_workflows(dry_run=dry_run, force=force)

    if success_flag:
        if dry_run:
            info(message)
        else:
            success(message)
            console.print("\n[green]✓ Migration completed successfully[/green]")
            console.print(f"\nYour workflows are now in: [cyan]{migration_status['new_dir_path']}[/cyan]")
            console.print("\n[dim]You can now use 'mcli workflow' to manage and 'mcli workflows' to run them[/dim]")
    else:
        error(message)
        if not force and "already exists" in message:
            console.print("\n[yellow]Tip: Use --force to proceed anyway (will backup existing files)[/yellow]")


if __name__ == "__main__":
    migrate_command()
