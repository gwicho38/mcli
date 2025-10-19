"""
Workflow command group for mcli.

All workflow commands are now loaded from portable JSON files in ~/.mcli/commands/
This provides a clean, maintainable way to manage workflow commands.

Features fuzzy finding and interactive command selection.
"""

import sys

import click

from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.fuzzy_finder import FuzzyCommandFinder
from mcli.lib.interactive_selector import (
    quick_select_best_match,
    select_command_interactive,
    select_from_suggestions,
)
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@click.group(name="workflow", invoke_without_command=True)
@click.pass_context
def workflow(ctx):
    """
    Workflow commands for automation, video processing, and daemon management.

    Interactive fuzzy finding:
        mcli workflow              # Show all commands with fuzzy finder
        mcli workflow back         # Fuzzy match commands containing 'back'
        mcli workflow gst          # Fuzzy match by acronym (e.g., git_status)

    Exact command execution:
        mcli workflow git_status   # Run exact command
        mcli workflow backup_db    # Run exact command with args
    """
    # If a subcommand was invoked, let Click handle it normally
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand - show interactive selector
    show_interactive_workflow_selector(ctx)


def get_workflow_commands():
    """Get all workflow commands from discovery system."""
    try:
        discovery = get_command_discovery()
        all_commands = discovery.get_commands(include_groups=False)

        # Filter to workflow group commands
        workflow_cmds = [
            cmd
            for cmd in all_commands
            if cmd.get("group") == "workflow" or cmd.get("full_name", "").startswith("workflow.")
        ]

        return workflow_cmds
    except Exception as e:
        logger.error(f"Failed to get workflow commands: {e}")
        return []


def handle_fuzzy_workflow(ctx, query: str):
    """
    Handle fuzzy matching for workflow commands.

    Args:
        ctx: Click context
        query: Search query
    """
    commands = get_workflow_commands()

    if not commands:
        click.echo("No workflow commands available.")
        ctx.exit(1)

    # Try quick match first (high confidence)
    best_match = quick_select_best_match(query, commands, min_score=95)

    if best_match:
        # High confidence match - execute directly
        cmd_name = best_match.get("name", "")
        explanation = FuzzyCommandFinder().get_match_explanation(query, best_match)
        click.echo(f"Running: {cmd_name} ({explanation})")

        # Execute the command
        execute_workflow_command(ctx, cmd_name, [])
        return

    # No high-confidence match - show interactive selector
    if sys.stdin.isatty() and sys.stdout.isatty():
        selected = select_command_interactive(commands, query=query, show_scores=True)

        if selected:
            cmd_name = selected.get("name", "")
            click.echo(f"\nExecuting: {cmd_name}")
            execute_workflow_command(ctx, cmd_name, [])
        else:
            click.echo("Command selection cancelled.")
            ctx.exit(0)
    else:
        # Non-interactive - show suggestions
        click.echo(f"No exact match for '{query}'.")
        click.echo("Use one of these commands:")

        finder = FuzzyCommandFinder()
        matches = finder.find_commands(query, commands)

        for cmd, score in matches[:5]:
            name = cmd.get("full_name", cmd.get("name", ""))
            desc = cmd.get("description", "")
            click.echo(f"  • {name} ({score}%) - {desc[:50]}")

        ctx.exit(1)


def show_interactive_workflow_selector(ctx):
    """Show interactive selector for all workflow commands."""
    commands = get_workflow_commands()

    if not commands:
        click.echo("No workflow commands available.")
        click.echo("Create one with: mcli commands add <name>")
        ctx.exit(1)

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        # Non-interactive - just list commands
        click.echo("Available workflow commands:")
        for cmd in commands[:20]:  # Show first 20
            name = cmd.get("full_name", cmd.get("name", ""))
            desc = cmd.get("description", "")
            click.echo(f"  • {name} - {desc[:50]}")

        if len(commands) > 20:
            click.echo(f"\n  ... and {len(commands) - 20} more")

        click.echo("\nUse: mcli workflow <command_name> to run a command")
        ctx.exit(0)

    # Interactive mode
    selected = select_command_interactive(commands, query="")

    if selected:
        cmd_name = selected.get("name", "")
        click.echo(f"\nExecuting: {cmd_name}")
        execute_workflow_command(ctx, cmd_name, [])
    else:
        click.echo("Command selection cancelled.")
        ctx.exit(0)


def execute_workflow_command(ctx, command_name: str, args: list):
    """
    Execute a workflow command.

    Args:
        ctx: Click context
        command_name: Name of command to execute
        args: Arguments to pass to command
    """
    try:
        # Get the workflow group from context
        workflow_group = ctx.command

        # Find and invoke the subcommand
        if command_name in workflow_group.commands:
            subcommand = workflow_group.commands[command_name]
            ctx.invoke(subcommand, *args)
        else:
            click.echo(f"Error: Command '{command_name}' not found in workflow group")
            ctx.exit(1)

    except Exception as e:
        logger.error(f"Failed to execute command {command_name}: {e}")
        click.echo(f"Error executing command: {e}", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    workflow()
