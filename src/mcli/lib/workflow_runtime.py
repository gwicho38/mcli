"""Runtime helpers for executing user workflow scripts safely.

When a dynamically-loaded workflow script raises an unhandled exception at
*invoke* time (i.e. it loads fine but crashes while running), Click/Python
would dump a raw traceback at the user. That tells them little about which
script failed or what to do next.

``wrap_command_invoke`` wraps a loaded command so such crashes are rendered as
a concise, actionable message — which workflow crashed, the error, the script
location, and how to report it. The full traceback stays one env var away
(``MCLI_TRACE_LEVEL`` / ``MCLI_DEBUG``) for debugging.

Click usage errors, ``Abort`` and ``SystemExit`` are deliberately *not*
swallowed — those are normal control flow, not script crashes.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import click
from rich.console import Console

from mcli.lib.constants.defaults import URLs
from mcli.lib.constants.env import EnvVars
from mcli.lib.constants.messages import ErrorMessages, InfoMessages

# Module-level so tests can redirect it to a buffer.
_console = Console(stderr=True)


def _wants_traceback() -> bool:
    """Whether to print the full traceback (debug/trace modes)."""
    trace = os.environ.get(EnvVars.MCLI_TRACE_LEVEL, "").strip()
    if trace and trace != "0":
        return True
    debug = os.environ.get(EnvVars.MCLI_DEBUG, "").strip().lower()
    return debug in ("1", "true", "yes", "on")


def _deepest_script_line(script_path: Path, exc: BaseException) -> int | None:
    """Return the deepest line number within the user's script, if any."""
    target = str(script_path)
    line: int | None = None
    for frame, lineno in traceback.walk_tb(exc.__traceback__):
        if frame.f_code.co_filename == target:
            line = lineno
    return line


def render_script_error(name: str, script_path: str | Path, exc: BaseException) -> None:
    """Print a concise, actionable crash summary for a workflow script."""
    script_path = Path(script_path)
    line = _deepest_script_line(script_path, exc)
    location = str(script_path) if line is None else f"{script_path}:{line}"

    summary = ErrorMessages.WORKFLOW_CRASHED.format(name=name, error=f"{type(exc).__name__}: {exc}")
    _console.print(f"[bold red]✗[/bold red] {summary}", soft_wrap=True, highlight=False)
    _console.print(
        InfoMessages.WORKFLOW_CRASH_LOCATION.format(location=location),
        soft_wrap=True,
        highlight=False,
    )
    _console.print(InfoMessages.WORKFLOW_CRASH_TRACE_HINT, soft_wrap=True, highlight=False)
    _console.print(
        InfoMessages.WORKFLOW_CRASH_REPORT.format(url=URLs.GITHUB_ISSUES_MCLI),
        soft_wrap=True,
        highlight=False,
    )

    if _wants_traceback():
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)


def wrap_command_invoke(command: click.BaseCommand, script_path: str | Path):
    """Wrap a loaded command so runtime crashes render a friendly message.

    Returns the same command (mutated in place). ``None`` passes through so
    callers don't need to guard.
    """
    if command is None:
        return command

    path = Path(script_path)
    original_invoke = command.invoke

    def safe_invoke(ctx):
        try:
            return original_invoke(ctx)
        except (click.ClickException, click.Abort, SystemExit, KeyboardInterrupt):
            raise
        except Exception as exc:  # noqa: BLE001 - intentional catch-all for user scripts
            render_script_error(command.name or path.stem, path, exc)
            raise SystemExit(1) from exc

    command.invoke = safe_invoke  # type: ignore[method-assign]
    return command
