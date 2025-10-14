"""
Completion helpers for MCLI that provide tab completion without loading heavy modules
"""

from typing import Any, Dict, List

import click
from click.shell_completion import CompletionItem

# Static completion data for lazy-loaded commands
LAZY_COMMAND_COMPLETIONS = {
    "workflow": {
        "subcommands": [
            "api-daemon",
            "daemon",
            "file",
            "politician-trading",
            "scheduler",
            "sync",
            "videos",
        ],
        "politician-trading": {
            "subcommands": [
                "connectivity",
                "cron-job",
                "data-sources",
                "disclosures",
                "health",
                "jobs",
                "monitor",
                "politicians",
                "run",
                "schema",
                "setup",
                "stats",
                "status",
                "test-workflow",
                "verify",
            ],
            "cron-job": {"options": ["--create", "--test"]},
            "setup": {
                "options": ["--create-tables", "--verify", "--generate-schema", "--output-dir"]
            },
            "run": {"options": ["--full", "--us-only", "--eu-only"]},
            "connectivity": {"options": ["--json", "--continuous", "--interval", "--duration"]},
            "health": {"options": ["--json"]},
            "monitor": {"options": ["--interval", "--count"]},
            "status": {"options": ["--json"]},
            "stats": {"options": ["--json"]},
            "test-workflow": {"options": ["--verbose", "--validate-writes"]},
            "schema": {"options": ["--show-location", "--generate", "--output-dir"]},
            "data-sources": {"options": ["--json"]},
            "jobs": {"options": ["--json", "--limit"]},
            "politicians": {
                "options": ["--json", "--limit", "--role", "--party", "--state", "--search"]
            },
            "disclosures": {
                "options": [
                    "--json",
                    "--limit",
                    "--politician",
                    "--asset",
                    "--transaction-type",
                    "--amount-min",
                    "--amount-max",
                    "--days",
                    "--details",
                ]
            },
            "verify": {"options": ["--json"]},
        },
        "scheduler": {
            "subcommands": ["add", "cancel", "list", "monitor", "remove", "start", "status", "stop"]
        },
        "daemon": {"subcommands": ["start", "stop", "status", "logs"]},
        "api-daemon": {"subcommands": ["start", "stop", "status", "logs"]},
        "videos": {"subcommands": ["remove-overlay", "extract-frames", "create-video"]},
        "sync": {"subcommands": ["status", "sync"]},
        "file": {"subcommands": ["search", "organize"]},
    },
    "chat": {"options": ["--model", "--system", "--temperature", "--max-tokens", "--stream"]},
    "model": {
        "subcommands": [
            "download",
            "list",
            "start",
            "stop",
            "pull",
            "delete",
            "recommend",
            "status",
        ]
    },
    "cron-test": {"options": ["--quick", "--cleanup", "--verbose"]},
    "visual": {"subcommands": ["demo", "spinner-test"]},
    "redis": {"subcommands": ["start", "stop", "status", "flush"]},
    "logs": {"subcommands": ["tail", "view", "clear"]},
    "completion": {
        "subcommands": ["bash", "zsh", "fish", "install", "status"],
        "install": {"options": ["--shell"]},
    },
}


def get_completion_items(cmd_path: List[str], incomplete: str = "") -> List[CompletionItem]:
    """Get completion items for a given command path without loading modules"""
    items = []

    # Navigate to the completion data for this path
    current_data = LAZY_COMMAND_COMPLETIONS

    for part in cmd_path:
        if part in current_data:
            current_data = current_data[part]
        else:
            return items  # No completion data available

    # Add subcommands
    if "subcommands" in current_data:
        for subcommand in current_data["subcommands"]:
            if subcommand.startswith(incomplete):
                items.append(CompletionItem(subcommand))

    # Add options
    if "options" in current_data:
        for option in current_data["options"]:
            if option.startswith(incomplete):
                items.append(CompletionItem(option))

    return items


class CompletionAwareLazyGroup(click.Group):
    """A Click group that provides completion without loading modules"""

    def __init__(self, name, import_path, *args, **kwargs):
        self.import_path = import_path
        self._loaded_group = None
        super().__init__(name, *args, **kwargs)

    def _load_group(self):
        """Load the actual group on first use."""
        if self._loaded_group is None:
            try:
                import importlib

                module_path, attr_name = self.import_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                self._loaded_group = getattr(module, attr_name)
            except Exception as e:
                # Return a dummy group that shows an error
                def error_callback():
                    click.echo(f"Error: Command group {self.name} is not available")

                self._loaded_group = click.Group(self.name, callback=error_callback)
        return self._loaded_group

    def invoke(self, ctx):
        """Invoke the lazily loaded group."""
        group = self._load_group()
        return group.invoke(ctx)

    def get_command(self, ctx, cmd_name):
        """Get a command from the lazily loaded group."""
        group = self._load_group()
        return group.get_command(ctx, cmd_name)

    def list_commands(self, ctx):
        """List commands from completion data first, then load if needed."""
        # Always try to get from static completion data first for workflow
        if self.name == "workflow" and self.name in LAZY_COMMAND_COMPLETIONS:
            data = LAZY_COMMAND_COMPLETIONS[self.name]
            if "subcommands" in data:
                return sorted(data["subcommands"])

        # Try to get from static completion data for other commands
        if self.name in LAZY_COMMAND_COMPLETIONS:
            data = LAZY_COMMAND_COMPLETIONS[self.name]
            if "subcommands" in data:
                return sorted(data["subcommands"])

        # Fallback to loading the actual group
        group = self._load_group()
        return group.list_commands(ctx)

    def shell_complete(self, ctx, param, incomplete):
        """Provide shell completion using static data when possible."""
        # Load the actual group to get proper completion for nested commands
        # This ensures file path completion works for subcommands
        group = self._load_group()
        if hasattr(group, "shell_complete"):
            return group.shell_complete(ctx, param, incomplete)
        return []

    def get_params(self, ctx):
        """Get parameters from the lazily loaded group."""
        group = self._load_group()
        return group.get_params(ctx)


def create_completion_aware_lazy_group(
    name: str, import_path: str, help_text: str = None
) -> CompletionAwareLazyGroup:
    """Create a completion-aware lazy group"""
    return CompletionAwareLazyGroup(name, import_path, help=help_text)
