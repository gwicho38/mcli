"""
Migration commands for mcli self-management.

Handles migrations between different versions of mcli, including:
- Directory structure changes
- Configuration format changes
- Command structure changes
"""

import json
import shutil
import stat
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mcli.lib.constants.paths import DirNames
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import error, info, success, warning

logger = get_logger(__name__)
console = Console()


def convert_json_to_script(
    json_path: Path, output_dir: Path, dry_run: bool = False
) -> tuple[bool, str, Path | None]:
    """Convert a JSON workflow definition to a native script file."""
    try:
        with open(json_path) as f:
            workflow = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Failed to read {json_path}: {e}", None

    name = workflow.get("name", json_path.stem)
    code = workflow.get("code", "")
    language = workflow.get("language", "python")
    description = workflow.get("description", "")
    version = workflow.get("version", "1.0.0")

    if not code:
        return False, f"No code found in {json_path}", None

    extension_map = {
        "python": ".py",
        "shell": ".sh",
        "bash": ".sh",
        "zsh": ".sh",
        "javascript": ".js",
        "typescript": ".ts",
    }
    ext = extension_map.get(language, ".sh")
    output_path = output_dir / f"{name}{ext}"

    if dry_run:
        return True, f"Would create {output_path}", output_path

    lines = code.split("\n")
    has_shebang = lines and lines[0].startswith("#!")

    metadata_comments = []
    if description and "@description" not in code:
        if language in ["python", "shell", "bash", "zsh"]:
            metadata_comments.append(f"# @description: {description}")
        elif language in ["javascript", "typescript"]:
            metadata_comments.append(f"// @description: {description}")

    if version and "@version" not in code:
        if language in ["python", "shell", "bash", "zsh"]:
            metadata_comments.append(f"# @version: {version}")
        elif language in ["javascript", "typescript"]:
            metadata_comments.append(f"// @version: {version}")

    if metadata_comments:
        if has_shebang:
            lines = [lines[0]] + metadata_comments + lines[1:]
        else:
            lines = metadata_comments + lines

    final_code = "\n".join(lines)

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(final_code)

        if ext == ".sh":
            output_path.chmod(
                output_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

        return True, f"Created {output_path}", output_path

    except OSError as e:
        return False, f"Failed to write {output_path}: {e}", None


def migrate_json_workflows(
    workflows_dir: Path, dry_run: bool = False, remove_json: bool = False
) -> tuple[int, int, list[str]]:
    """Find and convert all JSON workflow files to native scripts."""
    json_files = list(workflows_dir.glob("*.json"))
    json_files = [f for f in json_files if not f.name.endswith(".lock.json")]

    if not json_files:
        return 0, 0, ["No JSON workflow files found"]

    converted = 0
    failed = 0
    messages = []

    for json_file in json_files:
        try:
            with open(json_file) as f:
                data = json.load(f)

            if "code" not in data:
                messages.append(f"  ⚠ {json_file.name} (not a workflow file)")
                continue
        except json.JSONDecodeError:
            messages.append(f"  ✗ {json_file.name} (invalid JSON)")
            failed += 1
            continue

        success_flag, msg, output_path = convert_json_to_script(json_file, workflows_dir, dry_run)

        if success_flag:
            ext = output_path.suffix if output_path else ".py"
            messages.append(f"  ✓ {json_file.name} → {json_file.stem}{ext}")
            converted += 1

            if remove_json and not dry_run:
                try:
                    json_file.unlink()
                    messages.append(f"    Removed {json_file.name}")
                except OSError as e:
                    messages.append(f"    Warning: Could not remove {json_file.name}: {e}")
        else:
            messages.append(f"  ✗ {json_file.name}: {msg}")
            failed += 1

    return converted, failed, messages


def get_migration_status() -> dict:
    """
    Check the current migration status.

    Returns:
        Dictionary with migration status information
    """
    from mcli.lib.paths import get_git_root, is_git_repository

    mcli_home = Path.home() / DirNames.MCLI
    old_commands_dir = mcli_home / "commands"
    new_workflows_dir = mcli_home / "workflows"

    # Create global status dict with explicit types
    global_status: dict = {
        "old_dir_exists": old_commands_dir.exists(),
        "old_dir_path": str(old_commands_dir),
        "new_dir_exists": new_workflows_dir.exists(),
        "new_dir_path": str(new_workflows_dir),
        "needs_migration": False,
        "files_to_migrate": [],
        "migration_done": False,
    }

    status: dict = {
        "global": global_status,
        "local": None,
    }

    # Check global migration
    if old_commands_dir.exists():
        # Count files that need migration (excluding hidden files)
        files = [
            f for f in old_commands_dir.iterdir() if f.is_file() and not f.name.startswith(".")
        ]
        global_status["files_to_migrate"] = [f.name for f in files]
        global_status["needs_migration"] = len(files) > 0

    # Check if global migration already done
    if new_workflows_dir.exists() and not old_commands_dir.exists():
        global_status["migration_done"] = True

    # Check local migration (if in git repo)
    if is_git_repository():
        git_root = get_git_root()
        if git_root is not None:
            local_old = git_root / DirNames.MCLI / "commands"
            local_new = git_root / DirNames.MCLI / "workflows"

            local_status: dict = {
                "git_root": str(git_root),
                "old_dir_exists": local_old.exists(),
                "old_dir_path": str(local_old),
                "new_dir_exists": local_new.exists(),
                "new_dir_path": str(local_new),
                "needs_migration": False,
                "files_to_migrate": [],
                "migration_done": False,
            }
            status["local"] = local_status

            if local_old.exists():
                files = [
                    f for f in local_old.iterdir() if f.is_file() and not f.name.startswith(".")
                ]
                local_status["files_to_migrate"] = [f.name for f in files]
                local_status["needs_migration"] = len(files) > 0

            if local_new.exists() and not local_old.exists():
                local_status["migration_done"] = True

    return status


def migrate_directory(
    old_dir: Path, new_dir: Path, dry_run: bool = False, force: bool = False
) -> tuple[bool, str, list[str], list[str]]:
    """
    Migrate a commands directory to workflows directory.

    Args:
        old_dir: Source directory to migrate from
        new_dir: Target directory to migrate to
        dry_run: If True, show what would be done without actually doing it
        force: If True, proceed even if workflows directory exists

    Returns:
        Tuple of (success, message, migrated_files, skipped_files)
    """
    # Check if old directory exists
    if not old_dir.exists():
        return False, f"Nothing to migrate: {old_dir} does not exist", [], []

    # Check if new directory already exists
    if new_dir.exists() and not force:
        return False, f"Target directory {new_dir} already exists. Use --force to override.", [], []

    # Get list of files to migrate
    files_to_migrate = [f for f in old_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

    if not files_to_migrate:
        return False, f"No files to migrate in {old_dir}", [], []

    if dry_run:
        message = (
            f"[DRY RUN] Would migrate {len(files_to_migrate)} files from {old_dir} to {new_dir}"
        )
        return True, message, [f.name for f in files_to_migrate], []

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
                    backup_path = target_path.with_suffix(
                        f".backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
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
            f for f in old_dir.iterdir() if f.is_file() and not f.name.startswith(".")
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

        return True, "\n".join(report_lines), migrated_files, skipped_files

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False, f"Migration failed: {str(e)}", [], []


def migrate_commands_to_workflows(
    dry_run: bool = False, force: bool = False, scope: str = "all"
) -> tuple[bool, str]:
    """
    Migrate commands to workflows directories.

    Args:
        dry_run: If True, show what would be done without actually doing it
        force: If True, proceed even if workflows directory exists
        scope: "global", "local", or "all" to control migration scope

    Returns:
        Tuple of (success, message)
    """
    from mcli.lib.paths import get_git_root, is_git_repository

    results = []
    all_success = True

    # Migrate global
    if scope in ["global", "all"]:
        mcli_home = Path.home() / DirNames.MCLI
        old_dir = mcli_home / "commands"
        new_dir = mcli_home / "workflows"

        success, message, migrated, skipped = migrate_directory(old_dir, new_dir, dry_run, force)

        if old_dir.exists():
            results.append(f"[Global] {message}")
            if not success and "does not exist" not in message:
                all_success = False

    # Migrate local (if in git repo)
    if scope in ["local", "all"] and is_git_repository():
        git_root = get_git_root()
        if git_root is not None:
            old_dir = git_root / DirNames.MCLI / "commands"
            new_dir = git_root / DirNames.MCLI / "workflows"

            success, message, migrated, skipped = migrate_directory(
                old_dir, new_dir, dry_run, force
            )

            if old_dir.exists():
                results.append(f"[Local - {git_root.name}] {message}")
                if not success and "does not exist" not in message:
                    all_success = False

    if not results:
        return False, "No migrations needed"

    return all_success, "\n".join(results)


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
@click.option(
    "--scope",
    type=click.Choice(["all", "global", "local"], case_sensitive=False),
    default="all",
    help="Migration scope: all (default), global (~/.mcli), or local (.mcli in current repo)",
)
@click.option(
    "--to-ipfs",
    is_flag=True,
    help="Push workflows to IPFS after migration for decentralized backup",
)
@click.option(
    "--description",
    "-d",
    help="Description for IPFS sync (when using --to-ipfs)",
)
@click.option(
    "--json-to-scripts",
    is_flag=True,
    help="Convert legacy JSON workflow files to native scripts (.py, .sh, etc.)",
)
@click.option(
    "--remove-json",
    is_flag=True,
    help="Remove JSON files after successful conversion (use with --json-to-scripts)",
)
def migrate_command(
    dry_run: bool,
    force: bool,
    status: bool,
    scope: str,
    to_ipfs: bool,
    description: str,
    json_to_scripts: bool,
    remove_json: bool,
):
    """
    Migrate mcli configuration and data to new structure.

    Currently handles:
    - Moving ~/.mcli/commands to ~/.mcli/workflows (global)
    - Moving .mcli/commands to .mcli/workflows (local, in git repos)
    - Converting JSON workflow files to native scripts (--json-to-scripts)
    - Optionally pushing to IPFS for decentralized backup

    Examples:
        mcli self migrate --status           # Check migration status
        mcli self migrate --dry-run          # See what would be done
        mcli self migrate                    # Perform migration (both global and local)
        mcli self migrate --scope global     # Migrate only global
        mcli self migrate --scope local      # Migrate only local (current repo)
        mcli self migrate --force            # Force migration (overwrite existing)
        mcli self migrate --json-to-scripts  # Convert JSON workflows to scripts
        mcli self migrate --to-ipfs -d "Migrated workflows v1.0"  # Push to IPFS after
    """

    # Get current status
    migration_status = get_migration_status()

    # If --status flag, just show status and exit
    if status:
        console.print("\n[bold cyan]Migration Status[/bold cyan]")

        # Show global status
        global_status = migration_status["global"]
        console.print("\n[bold]Global (~/.mcli)[/bold]")
        console.print(f"  Old location: {global_status['old_dir_path']}")
        console.print(f"    Exists: {'✓ Yes' if global_status['old_dir_exists'] else '✗ No'}")
        console.print(f"  New location: {global_status['new_dir_path']}")
        console.print(f"    Exists: {'✓ Yes' if global_status['new_dir_exists'] else '✗ No'}")

        if global_status["needs_migration"]:
            console.print("  [yellow]⚠ Migration needed[/yellow]")
            console.print(f"  Files to migrate: {len(global_status['files_to_migrate'])}")
        elif global_status["migration_done"]:
            console.print("  [green]✓ Migration completed[/green]")
        else:
            console.print("  [green]✓ No migration needed[/green]")

        # Show local status if in git repo
        if migration_status["local"]:
            local_status = migration_status["local"]
            console.print(f"\n[bold]Local (current repository: {local_status['git_root']})[/bold]")
            console.print(f"  Old location: {local_status['old_dir_path']}")
            console.print(f"    Exists: {'✓ Yes' if local_status['old_dir_exists'] else '✗ No'}")
            console.print(f"  New location: {local_status['new_dir_path']}")
            console.print(f"    Exists: {'✓ Yes' if local_status['new_dir_exists'] else '✗ No'}")

            if local_status["needs_migration"]:
                console.print("  [yellow]⚠ Migration needed[/yellow]")
                console.print(f"  Files to migrate: {len(local_status['files_to_migrate'])}")
            elif local_status["migration_done"]:
                console.print("  [green]✓ Migration completed[/green]")
            else:
                console.print("  [green]✓ No migration needed[/green]")

        # Show files to migrate if any
        all_files = global_status.get("files_to_migrate", [])
        if migration_status["local"]:
            all_files.extend(migration_status["local"].get("files_to_migrate", []))

        if all_files:
            console.print("\n[bold]Files to migrate:[/bold]")
            table = Table()
            table.add_column("Location", style="cyan")
            table.add_column("File Name", style="yellow")

            for filename in sorted(global_status.get("files_to_migrate", [])):
                table.add_row("Global", filename)

            if migration_status["local"]:
                for filename in sorted(migration_status["local"].get("files_to_migrate", [])):
                    table.add_row("Local", filename)

            console.print(table)
            console.print("\n[dim]Run 'mcli self migrate' to perform migration[/dim]")

        return

    # Handle --json-to-scripts conversion
    if json_to_scripts:
        from mcli.lib.paths import get_custom_commands_dir, get_git_root, is_git_repository

        console.print("[bold cyan]Converting JSON Workflows to Native Scripts[/bold cyan]")
        if dry_run:
            console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        console.print()

        dirs_to_convert = []

        if scope in ["global", "all"]:
            global_dir = get_custom_commands_dir(global_mode=True)
            if global_dir.exists():
                dirs_to_convert.append(("Global", global_dir))

        if scope in ["local", "all"] and is_git_repository():
            git_root = get_git_root()
            if git_root:
                local_dir = get_custom_commands_dir(global_mode=False)
                if local_dir and local_dir.exists():
                    dirs_to_convert.append((f"Local ({git_root.name})", local_dir))

        if not dirs_to_convert:
            info("No workflow directories found")
            return

        total_converted = 0
        total_failed = 0

        for label, workflows_dir in dirs_to_convert:
            console.print(f"[bold]{label}:[/bold]")
            converted, failed, messages = migrate_json_workflows(
                workflows_dir, dry_run, remove_json
            )

            for msg in messages:
                console.print(msg)

            total_converted += converted
            total_failed += failed
            console.print()

        console.print("[bold]Summary:[/bold]")
        if total_converted > 0:
            console.print(f"  [green]✓ Converted: {total_converted}[/green]")
        if total_failed > 0:
            console.print(f"  [red]✗ Failed: {total_failed}[/red]")
        if total_converted == 0 and total_failed == 0:
            console.print("  No JSON workflow files found to convert")

        if total_converted > 0 and not dry_run:
            console.print()
            console.print("[dim]Run 'mcli sync update' to update the lockfile[/dim]")

        return

    # Check if migration is needed
    global_status = migration_status["global"]
    needs_any_migration = global_status["needs_migration"]
    if migration_status["local"]:
        needs_any_migration = needs_any_migration or migration_status["local"]["needs_migration"]

    if not needs_any_migration:
        info("No migration needed")
        return

    # Show what will be migrated
    console.print("\n[bold cyan]Migration Plan[/bold cyan]")

    if scope in ["global", "all"] and global_status["needs_migration"]:
        console.print("\n[bold]Global:[/bold]")
        console.print(f"  Source: [cyan]{global_status['old_dir_path']}[/cyan]")
        console.print(f"  Target: [cyan]{global_status['new_dir_path']}[/cyan]")
        console.print(f"  Files: [yellow]{len(global_status['files_to_migrate'])}[/yellow]")

    if (
        scope in ["local", "all"]
        and migration_status["local"]
        and migration_status["local"]["needs_migration"]
    ):
        console.print("\n[bold]Local:[/bold]")
        console.print(f"  Source: [cyan]{migration_status['local']['old_dir_path']}[/cyan]")
        console.print(f"  Target: [cyan]{migration_status['local']['new_dir_path']}[/cyan]")
        console.print(
            f"  Files: [yellow]{len(migration_status['local']['files_to_migrate'])}[/yellow]"
        )

    if dry_run:
        console.print("\n[yellow]DRY RUN MODE - No changes will be made[/yellow]")

    # Perform migration
    success_flag, message = migrate_commands_to_workflows(dry_run=dry_run, force=force, scope=scope)

    if success_flag:
        if dry_run:
            info(message)
        else:
            success(message)
            console.print("\n[green]✓ Migration completed successfully[/green]")
            console.print(
                "\n[dim]You can now use 'mcli workflow' to manage and 'mcli workflows' to run them[/dim]"
            )

            # Push to IPFS if requested
            if to_ipfs:
                console.print("\n[bold cyan]Pushing to IPFS...[/bold cyan]")

                try:
                    from mcli.lib.ipfs_sync import IPFSSync
                    from mcli.lib.paths import get_lockfile_path

                    ipfs = IPFSSync()

                    # Determine which lockfiles to push
                    lockfiles_to_push = []

                    if scope in ["global", "all"]:
                        global_lockfile = get_lockfile_path(global_mode=True)
                        if global_lockfile.exists():
                            lockfiles_to_push.append(("Global", global_lockfile))

                    if scope in ["local", "all"]:
                        local_lockfile = get_lockfile_path(global_mode=False)
                        if local_lockfile and local_lockfile.exists():
                            lockfiles_to_push.append(("Local", local_lockfile))

                    # Push each lockfile to IPFS
                    for location, lockfile_path in lockfiles_to_push:
                        desc = description or f"{location} workflows after migration"
                        cid = ipfs.push(lockfile_path, description=desc)

                        if cid:
                            console.print(f"\n[green]✓ {location} workflows pushed to IPFS[/green]")
                            console.print(f"  CID: [bold cyan]{cid}[/bold cyan]")
                            console.print(
                                f"  [dim]Retrieve with: mcli workflows sync pull {cid}[/dim]"
                            )
                        else:
                            console.print(
                                f"\n[yellow]⚠ Failed to push {location} workflows to IPFS[/yellow]"
                            )
                            console.print(
                                "  [dim]Note: Public IPFS gateways require authentication.[/dim]"
                            )
                            console.print(
                                "  [dim]Consider using 'mcli workflows sync push' with your own IPFS node.[/dim]"
                            )

                    if not lockfiles_to_push:
                        console.print("[yellow]⚠ No lockfiles found to push to IPFS[/yellow]")
                        console.print("  [dim]Run 'mcli workflow update-lockfile' first[/dim]")

                except ImportError as e:
                    console.print(f"[red]✗ Failed to import IPFS sync module: {e}[/red]")
                except Exception as e:
                    console.print(f"[red]✗ IPFS push failed: {e}[/red]")

    else:
        error(message)
        if not force and "already exists" in message:
            console.print(
                "\n[yellow]Tip: Use --force to proceed anyway (will backup existing files)[/yellow]"
            )


if __name__ == "__main__":
    migrate_command()
