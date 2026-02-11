"""
Top-level import command for MCLI.

This module provides the ``mcli import`` command for importing external scripts
into the mcli workflow ecosystem.  It handles single files, directories,
native-language detection, wrapper generation for unsupported languages,
binary rejection, and batch operations with a Rich summary table.

Example:
    mcli import ./scripts/backup.py
    mcli import ./scripts/ --recursive --dry-run
    mcli import ./tool.rb --wrap --global
"""

import os
import shutil
import stat
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.table import Table

from mcli.app.new_cmd import (
    detect_language_from_file,
    restructure_file_as_command,
    save_script,
    validate_command_name,
)
from mcli.lib.constants import (
    ImportDefaults,
    ImportMessages,
    ScriptExtensions,
    ScriptLanguages,
    ScriptMetadataDefaults,
)
from mcli.lib.errors import InvalidCommandNameError, UnsupportedFileTypeError
from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.script_loader import ScriptLoader
from mcli.lib.ui.styling import console

logger = get_logger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1

# Result status constants
STATUS_IMPORTED = "imported"
STATUS_WRAPPED = "wrapped"
STATUS_LINKED = "linked"
STATUS_MOVED = "moved"
STATUS_SKIPPED = "skipped"
STATUS_DRY_RUN = "dry-run"


# =============================================================================
# Detection helpers
# =============================================================================


def _is_binary(file_path: Path) -> bool:
    """Return True if *file_path* looks like a binary file.

    Reads the first ``ImportDefaults.BINARY_CHECK_SIZE`` bytes and checks for
    null bytes.  ``.ipynb`` files are exempt (they are JSON).
    """
    if file_path.suffix.lower() == ScriptExtensions.IPYNB:
        return False
    try:
        with open(file_path, "rb") as fh:
            chunk = fh.read(ImportDefaults.BINARY_CHECK_SIZE)
        return b"\x00" in chunk
    except OSError:
        return True


def _is_importable(
    file_path: Path,
) -> Tuple[bool, Optional[str], Optional[bool], Optional[str]]:
    """Classify a file as importable, wrappable, or rejected.

    Returns:
        ``(ok, language_or_None, needs_wrapper, skip_reason_or_None)``
    """
    name = file_path.name

    # Hidden files
    if name.startswith("."):
        return (False, None, None, "hidden")

    # Rejected extensions
    ext_lower = file_path.suffix.lower()
    if ext_lower in ImportDefaults.REJECTED_EXTENSIONS:
        return (False, None, None, "non-script extension")

    # Size check
    try:
        size = file_path.stat().st_size
    except OSError:
        return (False, None, None, "permission denied")
    if size > ImportDefaults.MAX_FILE_SIZE:
        return (False, None, None, "too large")

    # Binary check
    if _is_binary(file_path):
        return (False, None, None, "binary")

    # Try native language detection first
    try:
        lang = detect_language_from_file(file_path)
        return (True, lang, False, None)
    except UnsupportedFileTypeError:
        pass

    # Check wrapper interpreters (by extension)
    ext_raw = file_path.suffix  # preserve case for .R
    interpreter = ImportDefaults.WRAPPER_INTERPRETERS.get(ext_raw)
    if interpreter is None:
        interpreter = ImportDefaults.WRAPPER_INTERPRETERS.get(ext_lower)
    if interpreter:
        return (True, None, True, None)

    # Check for shebang
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            first_line = fh.readline(256)
        if first_line.startswith("#!"):
            return (True, None, True, None)
    except OSError:
        return (False, None, None, "permission denied")

    # Check if executable (and has no extension)
    if not file_path.suffix:
        try:
            if os.access(file_path, os.X_OK):
                return (True, None, True, None)
        except OSError:
            pass

    return (False, None, None, "no shebang or known extension")


def _detect_wrapper_interpreter(file_path: Path) -> str:
    """Return the interpreter string for a non-native script.

    Falls back to reading the shebang line.
    """
    ext_raw = file_path.suffix
    ext_lower = ext_raw.lower()
    interpreter = ImportDefaults.WRAPPER_INTERPRETERS.get(ext_raw)
    if interpreter is None:
        interpreter = ImportDefaults.WRAPPER_INTERPRETERS.get(ext_lower)
    if interpreter:
        return interpreter

    # Try shebang
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            first_line = fh.readline(256).strip()
        if first_line.startswith("#!"):
            # e.g.  #!/usr/bin/env ruby  ->  ruby
            parts = first_line.lstrip("#!").strip().split()
            if parts:
                interp = parts[-1]  # last token after env
                return interp
    except OSError:
        pass

    return "bash"


# =============================================================================
# Wrapper generation
# =============================================================================


def _create_wrapper_script(
    original_path: Path,
    command_name: str,
    interpreter: str,
    group: str,
) -> str:
    """Generate a shell wrapper script that delegates to *original_path*."""
    return (
        f"#!/usr/bin/env bash\n"
        f"# @description: Wrapper for {original_path.name}\n"
        f"# @version: {ScriptMetadataDefaults.VERSION}\n"
        f"# @group: {group}\n"
        f'\nexec {interpreter} "{original_path}" "$@"\n'
    )


# =============================================================================
# Name derivation
# =============================================================================


def _derive_command_name(file_path: Path) -> str:
    """Derive a valid mcli command name from a filename stem."""
    stem = file_path.stem.lower().replace("-", "_")
    try:
        return validate_command_name(stem)
    except InvalidCommandNameError:
        # Prefix with 'cmd_' if it starts with a digit or is otherwise invalid
        prefixed = f"cmd_{stem}"
        return validate_command_name(prefixed)


def _resolve_name_conflicts(
    files: List[Tuple[Path, str, bool]],
) -> List[Tuple[Path, str, bool, str]]:
    """Resolve duplicate command names for directory imports.

    For conflicts, prefix with parent directory name:
    ``db/backup.sh`` becomes ``db_backup``.

    Returns list of ``(path, language_or_None, needs_wrapper, command_name)``.
    """
    # First pass: derive names
    entries: List[Tuple[Path, str, bool, str]] = []
    for fpath, lang, wrap in files:
        entries.append((fpath, lang, wrap, _derive_command_name(fpath)))

    # Find duplicates
    name_counts: Dict[str, int] = {}
    for _, _, _, cname in entries:
        name_counts[cname] = name_counts.get(cname, 0) + 1

    # Resolve duplicates
    resolved: List[Tuple[Path, str, bool, str]] = []
    for fpath, lang, wrap, cname in entries:
        if name_counts[cname] > 1:
            parent = fpath.parent.name.lower().replace("-", "_")
            if parent:
                new_name = f"{parent}_{cname}"
                try:
                    new_name = validate_command_name(new_name)
                except InvalidCommandNameError:
                    new_name = cname  # fall back
                resolved.append((fpath, lang, wrap, new_name))
            else:
                resolved.append((fpath, lang, wrap, cname))
        else:
            resolved.append((fpath, lang, wrap, cname))

    return resolved


# =============================================================================
# Scanning
# =============================================================================


def _scan_source(
    source: Path,
    recursive: bool,
) -> List[Tuple[Path, Optional[str], bool]]:
    """Scan *source* and return importable files.

    Returns list of ``(path, language_or_None, needs_wrapper)``.
    Skipped files are logged but not returned.
    """
    candidates: List[Tuple[Path, Optional[str], bool]] = []

    if source.is_file():
        ok, lang, wrap, reason = _is_importable(source)
        if ok:
            candidates.append((source, lang, wrap or False))
        else:
            logger.info("Skipped %s: %s", source, reason)
        return candidates

    # Directory
    iterator = source.rglob("*") if recursive else source.iterdir()
    for entry in sorted(iterator):
        if not entry.is_file():
            continue
        ok, lang, wrap, reason = _is_importable(entry)
        if ok:
            candidates.append((entry, lang, wrap or False))
        else:
            logger.info("Skipped %s: %s", entry, reason)

    return candidates


# =============================================================================
# File transfer
# =============================================================================


def _perform_transfer(
    src: Path,
    dst: Path,
    *,
    link: bool = False,
    move: bool = False,
) -> None:
    """Copy, symlink, or move *src* to *dst*."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if link:
        dst.symlink_to(src.resolve())
    elif move:
        shutil.move(str(src), str(dst))
    else:
        shutil.copy2(str(src), str(dst))


# =============================================================================
# Single-file import
# =============================================================================


def _import_single_file(
    file_path: Path,
    command_name: str,
    language: Optional[str],
    needs_wrapper: bool,
    workflows_dir: Path,
    group: str,
    version: str,
    *,
    link: bool = False,
    move: bool = False,
    force: bool = False,
    wrap: bool = True,
    dry_run: bool = False,
) -> Tuple[str, str, str]:
    """Import a single file into the workflows directory.

    Returns ``(command_name, action_label, status)``.
    """
    # Check for existing command
    if language:
        ext = ScriptExtensions.BY_LANGUAGE.get(language, ".sh")
    else:
        ext = ".sh"  # wrappers are always shell
    target = workflows_dir / f"{command_name}{ext}"

    if target.exists() and not force:
        return (command_name, "skip", STATUS_SKIPPED)

    if dry_run:
        action = (
            "wrap"
            if (needs_wrapper and wrap)
            else ("link" if link else ("move" if move else "copy"))
        )
        return (command_name, action, STATUS_DRY_RUN)

    # ---- Wrapper path ----
    if needs_wrapper and wrap:
        interpreter = _detect_wrapper_interpreter(file_path)
        wrapper_code = _create_wrapper_script(
            original_path=file_path.resolve(),
            command_name=command_name,
            interpreter=interpreter,
            group=group,
        )
        target = workflows_dir / f"{command_name}.sh"
        if target.exists() and not force:
            return (command_name, "skip", STATUS_SKIPPED)
        workflows_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(wrapper_code)
        target.chmod(target.stat().st_mode | stat.S_IXUSR)
        return (command_name, "wrap", STATUS_WRAPPED)

    # ---- Native import (copy / link / move) ----
    if link:
        _perform_transfer(file_path, target, link=True)
        return (command_name, "link", STATUS_LINKED)

    if move:
        # Read content before moving for metadata injection
        code = restructure_file_as_command(
            file_path=file_path,
            name=command_name,
            description=f"{command_name.replace('_', ' ').title()} command",
            group=group,
            version=version,
            language=language,
        )
        saved = save_script(workflows_dir, command_name, code, language)
        # Remove original after successful save
        file_path.unlink()
        return (command_name, "move", STATUS_MOVED)

    # Default: copy with metadata injection
    code = restructure_file_as_command(
        file_path=file_path,
        name=command_name,
        description=f"{command_name.replace('_', ' ').title()} command",
        group=group,
        version=version,
        language=language,
    )
    save_script(workflows_dir, command_name, code, language)
    return (command_name, "copy", STATUS_IMPORTED)


# =============================================================================
# Summary display
# =============================================================================


def _display_summary(results: List[Tuple[str, str, str]], verbose: bool) -> None:
    """Show a Rich table summarising the import results."""
    if not results:
        return

    table = Table(title=ImportMessages.SUMMARY_HEADER, show_lines=False)
    table.add_column(ImportMessages.COL_NAME, style="cyan")
    table.add_column(ImportMessages.COL_ACTION)
    table.add_column(ImportMessages.COL_STATUS)

    status_styles = {
        STATUS_IMPORTED: "green",
        STATUS_WRAPPED: "green",
        STATUS_LINKED: "green",
        STATUS_MOVED: "green",
        STATUS_SKIPPED: "yellow",
        STATUS_DRY_RUN: "dim",
    }

    for name, action, rstatus in results:
        style = status_styles.get(rstatus, "white")
        table.add_row(name, action, f"[{style}]{rstatus}[/{style}]")

    console.print(table)

    # Counters
    imported = sum(
        1
        for _, _, s in results
        if s in (STATUS_IMPORTED, STATUS_WRAPPED, STATUS_LINKED, STATUS_MOVED)
    )
    skipped = sum(1 for _, _, s in results if s == STATUS_SKIPPED)
    if imported:
        console.print(f"[green]{imported} imported[/green]", end="")
    if skipped:
        sep = ", " if imported else ""
        console.print(f"{sep}[yellow]{skipped} skipped[/yellow]", end="")
    console.print()


# =============================================================================
# Click command
# =============================================================================


@click.command("import")
@click.argument(
    "source",
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    default=False,
    help="Import to global workflows (~/.mcli/workflows/)",
)
@click.option(
    "--group",
    default=ImportDefaults.DEFAULT_GROUP,
    help=f"Metadata group for imported scripts (default: '{ImportDefaults.DEFAULT_GROUP}')",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    default=False,
    help="Preview what would be imported without making changes",
)
@click.option(
    "--link",
    is_flag=True,
    default=False,
    help="Symlink instead of copy",
)
@click.option(
    "--move",
    is_flag=True,
    default=False,
    help="Move source files (mutually exclusive with --link)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Overwrite existing commands",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    default=False,
    help="Recurse into subdirectories",
)
@click.option(
    "--wrap/--no-wrap",
    default=True,
    help="Create shell wrappers for unsupported languages (default: wrap)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show detailed per-file output",
)
def import_cmd(
    source: str,
    is_global: bool,
    group: str,
    dry_run: bool,
    link: bool,
    move: bool,
    force: bool,
    recursive: bool,
    wrap: bool,
    verbose: bool,
) -> int:
    """📥 Import external scripts into the mcli workflow ecosystem.

    SOURCE can be a single file or a directory.  Native scripts (.py, .sh, .js,
    .ts, .ipynb) are copied with metadata injected.  Unsupported languages
    (Ruby, Perl, Go, etc.) get a thin shell wrapper that delegates to the
    original.

    \b
    Examples:
        mcli import ./backup.py
        mcli import ./scripts/ --recursive --dry-run
        mcli import ./tool.rb --wrap --global
        mcli import ./deploy.sh --link
    """
    if link and move:
        raise click.UsageError("--link and --move are mutually exclusive")

    source_path = Path(source)
    workflows_dir = get_custom_commands_dir(global_mode=is_global)
    version = ScriptMetadataDefaults.VERSION

    if dry_run:
        console.print(ImportMessages.DRY_RUN_HEADER)

    # Move confirmation (unless force or dry-run)
    if move and not force and not dry_run:
        if not click.confirm(ImportMessages.MOVE_CONFIRM):
            click.echo("Cancelled.")
            return EXIT_SUCCESS

    # Scan
    candidates = _scan_source(source_path, recursive)

    if not candidates:
        console.print(ImportMessages.NO_IMPORTABLE.format(path=source_path))
        return EXIT_SUCCESS

    # Resolve names (directory import may have conflicts)
    named = _resolve_name_conflicts(candidates)

    # Import each file
    results: List[Tuple[str, str, str]] = []
    for fpath, lang, needs_wrapper, cmd_name in named:
        if verbose and not dry_run:
            console.print(ImportMessages.IMPORTING_FILE.format(path=fpath))
        try:
            result = _import_single_file(
                file_path=fpath,
                command_name=cmd_name,
                language=lang,
                needs_wrapper=needs_wrapper,
                workflows_dir=workflows_dir,
                group=group,
                version=version,
                link=link,
                move=move,
                force=force,
                wrap=wrap,
                dry_run=dry_run,
            )
            results.append(result)
        except Exception as exc:
            logger.warning("Failed to import %s: %s", fpath, exc)
            results.append((cmd_name, "error", STATUS_SKIPPED))

    # Update lockfile (unless dry-run)
    if not dry_run:
        try:
            loader = ScriptLoader(workflows_dir)
            loader.save_lockfile()
        except Exception as exc:
            logger.warning("Failed to update lockfile: %s", exc)

    _display_summary(results, verbose)
    return EXIT_SUCCESS
