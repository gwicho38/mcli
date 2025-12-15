"""
Migration command for converting legacy JSON workflows to native scripts.

This command converts JSON workflow files to native script files (.py, .sh, etc.)
as part of the transition away from JSON-based command storage.
"""

import json
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.table import Table

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console

logger = get_logger(__name__)

# Language to extension mapping
LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "shell": ".sh",
    "javascript": ".js",
    "typescript": ".ts",
}


def extract_code_from_json(json_data: Dict) -> Tuple[str, str, str]:
    """
    Extract code and metadata from JSON command data.

    Returns:
        Tuple of (code, language, shell_type)
    """
    code = json_data.get("code", "")
    language = json_data.get("language", "python")
    shell_type = json_data.get("shell", "bash")
    return code, language, shell_type


def generate_script_with_metadata(
    code: str,
    language: str,
    json_data: Dict,
    shell_type: str = "bash",
) -> str:
    """
    Generate script content with metadata comments.

    Args:
        code: Original code from JSON
        language: Script language
        json_data: Original JSON data
        shell_type: Shell type for shell scripts

    Returns:
        Script content with metadata header
    """
    description = json_data.get("description", "")
    version = json_data.get("version", "1.0.0")
    group = json_data.get("group", "workflows")
    author = json_data.get("metadata", {}).get("author", "")

    # Determine comment prefix
    if language in ("python", "shell"):
        comment = "#"
    else:  # javascript, typescript
        comment = "//"

    # Build metadata header
    metadata_lines = []
    if description:
        metadata_lines.append(f"{comment} @description: {description}")
    metadata_lines.append(f"{comment} @version: {version}")
    if group:
        metadata_lines.append(f"{comment} @group: {group}")
    if author:
        metadata_lines.append(f"{comment} @author: {author}")
    if language == "shell":
        metadata_lines.append(f"{comment} @shell: {shell_type}")

    metadata_header = "\n".join(metadata_lines)

    # Check if code already has shebang
    if code.strip().startswith("#!"):
        # Insert metadata after shebang
        lines = code.split("\n", 1)
        if len(lines) > 1:
            return f"{lines[0]}\n{metadata_header}\n{lines[1]}"
        else:
            return f"{lines[0]}\n{metadata_header}\n"
    else:
        # Add shebang based on language
        if language == "python":
            shebang = "#!/usr/bin/env python3"
        elif language == "shell":
            shebang = f"#!/usr/bin/env {shell_type}"
        elif language in ("javascript", "typescript"):
            shebang = "#!/usr/bin/env bun"
        else:
            shebang = ""

        if shebang:
            return f"{shebang}\n{metadata_header}\n\n{code}"
        else:
            return f"{metadata_header}\n\n{code}"


def migrate_json_to_script(
    json_path: Path,
    output_dir: Path,
    backup: bool = True,
    dry_run: bool = False,
) -> Optional[Path]:
    """
    Convert a single JSON file to a native script.

    Args:
        json_path: Path to the JSON file
        output_dir: Directory to save the script
        backup: Whether to backup the JSON file
        dry_run: If True, don't actually write files

    Returns:
        Path to the created script, or None if failed
    """
    try:
        with open(json_path, "r") as f:
            json_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read JSON file {json_path}: {e}")
        return None

    name = json_data.get("name", json_path.stem)
    code, language, shell_type = extract_code_from_json(json_data)

    if not code:
        logger.warning(f"JSON file {json_path} has no code, skipping")
        return None

    # Determine output extension
    extension = LANGUAGE_EXTENSIONS.get(language, ".py")
    script_path = output_dir / f"{name}{extension}"

    if dry_run:
        logger.info(f"[DRY RUN] Would create: {script_path}")
        return script_path

    # Generate script content
    script_content = generate_script_with_metadata(code, language, json_data, shell_type)

    # Write script
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(script_path, "w") as f:
            f.write(script_content)

        # Make executable
        if language in ("python", "shell"):
            script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)

        logger.info(f"Created script: {script_path}")

        # Backup or remove JSON
        if backup:
            backup_path = json_path.with_suffix(".json.bak")
            shutil.move(json_path, backup_path)
            logger.info(f"Backed up JSON to: {backup_path}")
        else:
            json_path.unlink()
            logger.info(f"Removed JSON file: {json_path}")

        return script_path

    except Exception as e:
        logger.error(f"Failed to create script {script_path}: {e}")
        return None


def find_json_commands(commands_dir: Path) -> List[Path]:
    """
    Find all JSON command files in a directory.

    Args:
        commands_dir: Directory to search

    Returns:
        List of JSON file paths
    """
    if not commands_dir.exists():
        return []

    json_files = []
    for json_path in commands_dir.glob("*.json"):
        # Skip lockfiles and cache files
        if json_path.name in ("commands.lock.json", "workflows.lock.json", ".sync_cache.json"):
            continue
        json_files.append(json_path)

    return sorted(json_files)


@click.group(name="migrate")
def migrate():
    """Migrate legacy JSON workflows to native scripts.

    This command helps convert JSON-based workflow definitions to native
    script files (.py, .sh, .js, .ts).

    Examples:

        mcli workflow migrate status         # Show migration status

        mcli workflow migrate run --dry-run  # Preview migration

        mcli workflow migrate run            # Migrate with backup

        mcli workflow migrate run --no-backup  # Migrate without backup
    """


@migrate.command("status")
@click.option("--global", "-g", "is_global", is_flag=True, help="Check global workflows")
def migration_status(is_global):
    """Show migration status - JSON files that can be migrated."""
    workflows_dir = get_custom_commands_dir(global_mode=is_global)

    json_files = find_json_commands(workflows_dir)

    if not json_files:
        scope = "global" if is_global else "local"
        console.print(f"[green]No legacy JSON files found in {scope} directory.[/green]")
        console.print(f"[dim]Directory: {workflows_dir}[/dim]")
        return 0

    table = Table(title="JSON Files Available for Migration")
    table.add_column("Name", style="cyan")
    table.add_column("Language", style="blue")
    table.add_column("Group", style="green")
    table.add_column("Description", style="dim")

    for json_path in json_files:
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            table.add_row(
                data.get("name", json_path.stem),
                data.get("language", "python"),
                data.get("group", "-"),
                (
                    (data.get("description", "")[:50] + "...")
                    if len(data.get("description", "")) > 50
                    else data.get("description", "-")
                ),
            )
        except Exception:
            table.add_row(json_path.stem, "?", "?", "Failed to read")

    console.print(table)
    console.print(f"\n[dim]Found {len(json_files)} JSON file(s) to migrate[/dim]")
    console.print("[dim]Run 'mcli workflow migrate run' to migrate[/dim]")


@migrate.command("run")
@click.option("--global", "-g", "is_global", is_flag=True, help="Migrate global workflows")
@click.option("--backup/--no-backup", default=True, help="Backup JSON files (default: backup)")
@click.option("--dry-run", is_flag=True, help="Preview migration without making changes")
@click.argument("name", required=False)
def run_migration(is_global, backup, dry_run, name):
    """
    Migrate JSON workflows to native scripts.

    If NAME is provided, migrates only that workflow.
    Otherwise migrates all JSON workflows.

    Examples:

        mcli workflow migrate run                    # Migrate all

        mcli workflow migrate run my_workflow        # Migrate specific

        mcli workflow migrate run --dry-run          # Preview only

        mcli workflow migrate run --no-backup        # Don't keep JSON backup
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)

    if name:
        # Migrate specific file
        json_path = workflows_dir / f"{name}.json"
        if not json_path.exists():
            console.print(f"[red]JSON file not found: {json_path}[/red]")
            return 1

        json_files = [json_path]
    else:
        # Migrate all
        json_files = find_json_commands(workflows_dir)

    if not json_files:
        scope = "global" if is_global else "local"
        console.print(f"[green]No JSON files to migrate in {scope} directory.[/green]")
        return 0

    if dry_run:
        console.print("[yellow]DRY RUN - No files will be modified[/yellow]\n")

    migrated = []
    failed = []

    for json_path in json_files:
        result = migrate_json_to_script(
            json_path,
            workflows_dir,
            backup=backup,
            dry_run=dry_run,
        )
        if result:
            migrated.append(result)
        else:
            failed.append(json_path)

    # Summary
    console.print("")
    if migrated:
        console.print(f"[green]Migrated {len(migrated)} workflow(s):[/green]")
        for path in migrated:
            console.print(f"  - {path.name}")

    if failed:
        console.print(f"\n[red]Failed to migrate {len(failed)} workflow(s):[/red]")
        for path in failed:
            console.print(f"  - {path.name}")

    # Update lockfile
    if migrated and not dry_run:
        try:
            loader = ScriptLoader(workflows_dir)
            loader.save_lockfile()
            console.print("\n[dim]Updated lockfile[/dim]")
        except Exception as e:
            logger.warning(f"Failed to update lockfile: {e}")

    if dry_run:
        console.print(
            "\n[yellow]DRY RUN complete. Run without --dry-run to apply changes.[/yellow]"
        )

    return 0 if not failed else 1


@migrate.command("restore")
@click.option("--global", "-g", "is_global", is_flag=True, help="Restore global workflows")
@click.argument("name", required=False)
def restore_backup(is_global, name):
    """
    Restore JSON files from backup.

    If NAME is provided, restores only that workflow.
    Otherwise restores all backed up JSON files.
    """
    workflows_dir = get_custom_commands_dir(global_mode=is_global)

    if name:
        backup_path = workflows_dir / f"{name}.json.bak"
        if not backup_path.exists():
            console.print(f"[red]Backup not found: {backup_path}[/red]")
            return 1
        backups = [backup_path]
    else:
        backups = list(workflows_dir.glob("*.json.bak"))

    if not backups:
        console.print("[yellow]No backup files found.[/yellow]")
        return 0

    restored = []
    for backup_path in backups:
        json_path = backup_path.with_suffix("")  # Remove .bak
        try:
            shutil.move(backup_path, json_path)
            restored.append(json_path)
            console.print(f"[green]Restored: {json_path.name}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to restore {backup_path.name}: {e}[/red]")

    if restored:
        console.print(f"\n[green]Restored {len(restored)} JSON file(s)[/green]")

    return 0
