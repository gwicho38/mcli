"""
Log streaming and management commands
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from mcli.lib.paths import get_logs_dir

console = Console()


@click.group(name="logs")
def logs_group():
    """Stream and manage MCLI log files"""
    pass


@logs_group.command(name="location")
def show_location():
    """Show the location of the logs directory"""
    logs_dir = get_logs_dir()
    console.print(f"📁 [cyan]Logs directory:[/cyan] {logs_dir}")
    console.print(f"   [dim]Set MCLI_HOME environment variable to change location[/dim]")

    # Show if directory exists and has files
    if logs_dir.exists():
        log_files = list(logs_dir.glob("mcli*.log"))
        if log_files:
            console.print(f"   [green]✓ {len(log_files)} log file(s) found[/green]")
        else:
            console.print(f"   [yellow]⚠ Directory exists but no log files yet[/yellow]")
    else:
        console.print(f"   [yellow]⚠ Directory will be created on first use[/yellow]")


@logs_group.command(name="stream")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["main", "trace", "system", "all"]),
    default="main",
    help="Type of logs to stream (default: main)",
)
@click.option(
    "--lines", "-n", type=int, default=50, help="Number of initial lines to show (default: 50)"
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    default=True,
    help="Follow log output in real-time (default: enabled)",
)
def stream_logs(type: str, lines: int, follow: bool):
    """Stream MCLI log files in real-time

    Shows log output with syntax highlighting and real-time updates.
    Similar to 'tail -f' but with enhanced formatting for MCLI logs.
    """
    logs_dir = get_logs_dir()

    # Get today's log files
    today = datetime.now().strftime("%Y%m%d")

    log_files = {
        "main": logs_dir / f"mcli_{today}.log",
        "trace": logs_dir / f"mcli_trace_{today}.log",
        "system": logs_dir / f"mcli_system_{today}.log",
    }

    # Filter to existing files
    existing_files = {k: v for k, v in log_files.items() if v.exists()}

    if not existing_files:
        console.print(f"❌ No log files found for today ({today})", style="red")
        _list_available_logs(logs_dir)
        return

    # Determine which files to stream
    if type == "all":
        files_to_stream = list(existing_files.values())
    else:
        if type not in existing_files:
            console.print(f"❌ {type} log file not found for today", style="red")
            console.print(f"Available logs: {', '.join(existing_files.keys())}", style="yellow")
            return
        files_to_stream = [existing_files[type]]

    # Start streaming
    try:
        if len(files_to_stream) == 1:
            _stream_single_file(files_to_stream[0], lines, follow)
        else:
            _stream_multiple_files(files_to_stream, lines, follow)
    except KeyboardInterrupt:
        console.print("\n👋 Log streaming stopped", style="cyan")


@logs_group.command(name="list")
@click.option("--date", "-d", help="Show logs for specific date (YYYYMMDD format)")
def list_logs(date: Optional[str]):
    """List available log files"""
    logs_dir = get_logs_dir()
    _list_available_logs(logs_dir, date)


@logs_group.command(name="tail")
@click.argument("log_type", type=click.Choice(["main", "trace", "system"]))
@click.option("--lines", "-n", type=int, default=20, help="Number of lines to show (default: 20)")
@click.option("--date", "-d", help="Date for log file (YYYYMMDD format, default: today)")
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output in real-time (like tail -f)",
)
def tail_logs(log_type: str, lines: int, date: Optional[str], follow: bool):
    """Show the last N lines of a specific log file

    By default, shows the last N lines and exits. Use --follow/-f to
    continuously monitor the log file for new entries (similar to tail -f).
    """
    logs_dir = get_logs_dir()

    # Note: get_logs_dir() creates the directory automatically

    # Use provided date or default to today
    log_date = date or datetime.now().strftime("%Y%m%d")

    # Map log types to file patterns
    log_files = {
        "main": f"mcli_{log_date}.log",
        "trace": f"mcli_trace_{log_date}.log",
        "system": f"mcli_system_{log_date}.log",
    }

    log_file = logs_dir / log_files[log_type]

    if not log_file.exists():
        console.print(f"❌ Log file not found: {log_file}", style="red")
        _list_available_logs(logs_dir, log_date)
        return

    try:
        if follow:
            # Follow mode: continuously stream new lines
            console.print(f"\n📡 **Following {log_file.name}** (last {lines} lines)", style="cyan")
            console.print("Press Ctrl+C to stop\n")

            # Use tail -f for real-time following
            cmd = ["tail", f"-n{lines}", "-f", str(log_file)]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            try:
                for line in iter(process.stdout.readline, ""):
                    if line:
                        formatted_line = _format_log_line(line.rstrip())
                        console.print(formatted_line)
            except KeyboardInterrupt:
                process.terminate()
                console.print("\n👋 Log following stopped", style="cyan")
        else:
            # Standard mode: just show last N lines
            # Read last N lines
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            # Display with formatting
            console.print(
                f"\n📋 **Last {len(tail_lines)} lines from {log_file.name}**\n", style="cyan"
            )

            for line in tail_lines:
                formatted_line = _format_log_line(line.rstrip())
                console.print(formatted_line)

    except Exception as e:
        console.print(f"❌ Error reading log file: {e}", style="red")


@logs_group.command(name="grep")
@click.argument("pattern")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["main", "trace", "system", "all"]),
    default="all",
    help="Type of logs to search (default: all)",
)
@click.option("--date", "-d", help="Date for log files (YYYYMMDD format, default: today)")
@click.option(
    "--context", "-C", type=int, default=3, help="Lines of context around matches (default: 3)"
)
def grep_logs(pattern: str, type: str, date: Optional[str], context: int):
    """Search for patterns in log files"""
    logs_dir = get_logs_dir()

    # Use provided date or default to today
    log_date = date or datetime.now().strftime("%Y%m%d")

    # Get log files to search
    log_files = {
        "main": logs_dir / f"mcli_{log_date}.log",
        "trace": logs_dir / f"mcli_trace_{log_date}.log",
        "system": logs_dir / f"mcli_system_{log_date}.log",
    }

    files_to_search = []
    if type == "all":
        files_to_search = [f for f in log_files.values() if f.exists()]
    else:
        if log_files[type].exists():
            files_to_search = [log_files[type]]

    if not files_to_search:
        console.print(f"❌ No log files found for {log_date}", style="red")
        return

    # Search each file
    total_matches = 0
    for log_file in files_to_search:
        matches = _search_log_file(log_file, pattern, context)
        if matches:
            console.print(f"\n📁 **{log_file.name}** ({len(matches)} matches)", style="cyan")
            for match in matches:
                console.print(match)
            total_matches += len(matches)

    if total_matches == 0:
        console.print(f"❌ No matches found for pattern: {pattern}", style="yellow")
    else:
        console.print(f"\n✅ Found {total_matches} total matches", style="green")


@logs_group.command(name="clear")
@click.option("--older-than", type=int, help="Clear logs older than N days")
@click.option("--confirm", "-y", is_flag=True, help="Skip confirmation prompt")
def clear_logs(older_than: Optional[int], confirm: bool):
    """Clear old log files"""
    logs_dir = get_logs_dir()

    # Find log files
    log_files = list(logs_dir.glob("mcli*.log"))

    if not log_files:
        console.print("ℹ️  No log files to clear", style="blue")
        return

    # Filter by age if specified
    if older_than:
        import time

        cutoff_time = time.time() - (older_than * 24 * 60 * 60)  # Convert days to seconds
        log_files = [f for f in log_files if f.stat().st_mtime < cutoff_time]

        if not log_files:
            console.print(f"ℹ️  No log files older than {older_than} days", style="blue")
            return

    # Show what will be deleted
    console.print(f"📋 **Log files to clear:**", style="yellow")
    total_size = 0
    for log_file in log_files:
        size = log_file.stat().st_size
        total_size += size
        console.print(f"   • {log_file.name} ({_format_file_size(size)})")

    console.print(f"\n📊 **Total size:** {_format_file_size(total_size)}", style="cyan")

    # Confirm deletion
    if not confirm:
        if not click.confirm(f"\nDelete {len(log_files)} log files?"):
            console.print("❌ Operation cancelled", style="yellow")
            return

    # Delete files
    deleted_count = 0
    for log_file in log_files:
        try:
            log_file.unlink()
            deleted_count += 1
        except Exception as e:
            console.print(f"❌ Failed to delete {log_file.name}: {e}", style="red")

    console.print(
        f"✅ Deleted {deleted_count} log files ({_format_file_size(total_size)} freed)",
        style="green",
    )


def _stream_single_file(log_file: Path, lines: int, follow: bool):
    """Stream a single log file"""
    console.print(f"📡 **Streaming {log_file.name}**", style="cyan")
    console.print("Press Ctrl+C to stop\n")

    if follow:
        # Use tail -f for real-time following
        cmd = ["tail", f"-{lines}", "-f", str(log_file)]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            for line in iter(process.stdout.readline, ""):
                if line:
                    formatted_line = _format_log_line(line.rstrip())
                    console.print(formatted_line)
        except KeyboardInterrupt:
            process.terminate()
    else:
        # Just show last N lines
        with open(log_file, "r") as f:
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        for line in tail_lines:
            formatted_line = _format_log_line(line.rstrip())
            console.print(formatted_line)


def _stream_multiple_files(log_files: list, lines: int, follow: bool):
    """Stream multiple log files simultaneously"""
    console.print(f"📡 **Streaming {len(log_files)} log files**", style="cyan")
    for log_file in log_files:
        console.print(f"   • {log_file.name}")
    console.print("Press Ctrl+C to stop\n")

    # Use multitail or custom implementation
    # For simplicity, we'll cycle through files
    try:
        while True:
            for log_file in log_files:
                if log_file.exists():
                    # Show recent lines from each file
                    with open(log_file, "r") as f:
                        all_lines = f.readlines()
                        recent_lines = all_lines[-5:] if len(all_lines) > 5 else all_lines

                    if recent_lines:
                        console.print(f"\n--- {log_file.name} ---", style="blue")
                        for line in recent_lines:
                            formatted_line = _format_log_line(line.rstrip())
                            console.print(formatted_line)

            if follow:
                time.sleep(2)  # Update every 2 seconds
            else:
                break

    except KeyboardInterrupt:
        pass


def _format_log_line(line: str) -> Text:
    """Format a log line with syntax highlighting"""
    text = Text()

    # Color-code by log level
    if "ERROR" in line:
        text.append(line, style="red")
    elif "WARNING" in line or "WARN" in line:
        text.append(line, style="yellow")
    elif "INFO" in line:
        text.append(line, style="green")
    elif "DEBUG" in line:
        text.append(line, style="dim blue")
    else:
        text.append(line, style="white")

    return text


def _list_available_logs(logs_dir: Path, date_filter: Optional[str] = None):
    """List available log files"""
    log_files = sorted(logs_dir.glob("mcli*.log"))

    if not log_files:
        console.print("ℹ️  No log files found", style="blue")
        return

    # Filter by date if specified
    if date_filter:
        log_files = [f for f in log_files if date_filter in f.name]
        if not log_files:
            console.print(f"ℹ️  No log files found for date: {date_filter}", style="blue")
            return

    console.print("📋 **Available log files:**", style="cyan")

    for log_file in log_files:
        size = log_file.stat().st_size
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        console.print(
            f"   • {log_file.name} ({_format_file_size(size)}, {mtime.strftime('%Y-%m-%d %H:%M')})"
        )


def _search_log_file(log_file: Path, pattern: str, context: int) -> list:
    """Search for pattern in log file with context"""
    matches = []

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if pattern.lower() in line.lower():
                # Get context lines
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)

                context_lines = []
                for j in range(start, end):
                    prefix = ">>> " if j == i else "    "
                    style = "bright_yellow" if j == i else "dim"
                    context_lines.append(f"{prefix}{lines[j].rstrip()}")

                matches.append("\n".join(context_lines) + "\n")

    except Exception as e:
        console.print(f"❌ Error searching {log_file.name}: {e}", style="red")

    return matches


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


# Register with main CLI
def register_logs_commands(cli):
    """Register logs commands with the main CLI"""
    cli.add_command(logs_group)
