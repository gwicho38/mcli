"""
REPL (Read-Eval-Print Loop) for LSH secrets management.
"""

from pathlib import Path
from typing import List

import click
from prompt_toolkit import prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory

from mcli.lib.constants.paths import DirNames
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console, error, info, success, warning

from .manager import SecretsManager
from .store import SecretsStore

logger = get_logger(__name__)


class SecretsREPL:
    """Interactive REPL for secrets management."""

    def __init__(self):
        """Initialize the REPL."""
        self.manager = SecretsManager()
        self.store = SecretsStore()
        self.running = False
        self.namespace = "default"
        self.history_file = Path.home() / DirNames.MCLI / "secrets_repl_history"

        # Commands
        self.commands = {
            "set": self.cmd_set,
            "get": self.cmd_get,
            "list": self.cmd_list,
            "delete": self.cmd_delete,
            "namespace": self.cmd_namespace,
            "export": self.cmd_export,
            "import": self.cmd_import,
            "push": self.cmd_push,
            "pull": self.cmd_pull,
            "sync": self.cmd_sync,
            "status": self.cmd_status,
            "help": self.cmd_help,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
        }

        # Command completer
        self.completer = WordCompleter(list(self.commands.keys()) + ["ns"], ignore_case=True)

    def run(self):
        """Run the REPL."""
        self.running = True

        # Print welcome message
        console.print("[bold cyan]MCLI Secrets Management Shell[/bold cyan]")
        console.print("Type 'help' for available commands or 'exit' to quit.\n")

        # Create history file directory if needed
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        while self.running:
            try:
                # Build prompt
                prompt_text = f"[{self.namespace}]> "

                # Get user input
                user_input = prompt(
                    prompt_text,
                    completer=self.completer,
                    history=FileHistory(str(self.history_file)),
                    auto_suggest=AutoSuggestFromHistory(),
                ).strip()

                if not user_input:
                    continue

                # Parse command and arguments
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []

                # Handle command aliases
                if command == "ns":
                    command = "namespace"

                # Execute command
                if command in self.commands:
                    self.commands[command](args)
                else:
                    error(f"Unknown command: {command}")
                    console.print("Type 'help' for available commands.")

            except KeyboardInterrupt:
                console.print("\nUse 'exit' or 'quit' to leave the shell.")
            except EOFError:
                self.cmd_exit([])
            except Exception as e:
                error(f"Error: {e}")
                logger.exception("REPL error")

    def cmd_set(self, args: list[str]):
        """Set a secret value."""
        if len(args) < 2:
            error("Usage: set <key> <value>")
            return

        key = args[0]
        value = " ".join(args[1:])

        try:
            self.manager.set(key, value, self.namespace)
            success(f"Secret '{key}' set in namespace '{self.namespace}'")
        except Exception as e:
            error(f"Failed to set secret: {e}")

    def cmd_get(self, args: list[str]):
        """Get a secret value."""
        if len(args) != 1:
            error("Usage: get <key>")
            return

        key = args[0]
        value = self.manager.get(key, self.namespace)

        if value is not None:
            # Mask the value for security
            masked_value = (
                value[:3] + "*" * (len(value) - 6) + value[-3:]
                if len(value) > 6
                else "*" * len(value)
            )
            info(f"{key} = {masked_value}")

            if click.confirm("Show full value?", default=False):
                console.print(f"[yellow]{value}[/yellow]")
        else:
            warning(f"Secret '{key}' not found in namespace '{self.namespace}'")

    def cmd_list(self, args: list[str]):
        """List all secrets."""
        secrets = self.manager.list(self.namespace if args != ["all"] else None)

        if secrets:
            console.print("[bold]Secrets:[/bold]")
            for secret in secrets:
                console.print(f"  • {secret}")
        else:
            info("No secrets found")

    def cmd_delete(self, args: list[str]):
        """Delete a secret."""
        if len(args) != 1:
            error("Usage: delete <key>")
            return

        key = args[0]

        if click.confirm(f"Delete secret '{key}' from namespace '{self.namespace}'?"):
            if self.manager.delete(key, self.namespace):
                success(f"Secret '{key}' deleted")
            else:
                warning(f"Secret '{key}' not found")

    def cmd_namespace(self, args: list[str]):
        """Switch namespace."""
        if len(args) == 0:
            # List namespaces
            namespaces = set()
            for d in self.manager.secrets_dir.iterdir():
                if d.is_dir() and not d.name.startswith("."):
                    namespaces.add(d.name)

            console.print(f"[bold]Current namespace:[/bold] {self.namespace}")
            if namespaces:
                console.print("[bold]Available namespaces:[/bold]")
                for ns in sorted(namespaces):
                    marker = "→" if ns == self.namespace else " "
                    console.print(f"  {marker} {ns}")
        elif len(args) == 1:
            self.namespace = args[0]
            success(f"Switched to namespace '{self.namespace}'")
        else:
            error("Usage: namespace [<name>]")

    def cmd_export(self, args: list[str]):
        """Export secrets as environment variables."""
        env_vars = self.manager.export_env(self.namespace)

        if env_vars:
            if args and args[0] == "file":
                # Export to file
                filename = args[1] if len(args) > 1 else f"{self.namespace}.env"
                with open(filename, "w") as f:
                    for key, value in env_vars.items():
                        f.write(f"{key}={value}\n")
                success(f"Exported {len(env_vars)} secrets to {filename}")
            else:
                # Display export commands
                console.print("[bold]Export commands:[/bold]")
                for key, value in env_vars.items():
                    masked_value = value[:3] + "***" + value[-3:] if len(value) > 6 else "***"
                    console.print(f"export {key}={masked_value}")
        else:
            info("No secrets to export")

    def cmd_import(self, args: list[str]):
        """Import secrets from environment file."""
        if len(args) != 1:
            error("Usage: import <env-file>")
            return

        env_file = Path(args[0])
        if not env_file.exists():
            error(f"File not found: {env_file}")
            return

        count = self.manager.import_env(env_file, self.namespace)
        success(f"Imported {count} secrets from {env_file}")

    def cmd_push(self, args: list[str]):
        """Push secrets to git store."""
        message = " ".join(args) if args else None
        self.store.push(self.manager.secrets_dir, message)

    def cmd_pull(self, args: list[str]):
        """Pull secrets from git store."""
        self.store.pull(self.manager.secrets_dir)

    def cmd_sync(self, args: list[str]):
        """Sync secrets with git store."""
        message = " ".join(args) if args else None
        self.store.sync(self.manager.secrets_dir, message)

    def cmd_status(self, args: list[str]):
        """Show store status."""
        status = self.store.status()

        console.print("[bold]Secrets Store Status:[/bold]")
        console.print(f"  Initialized: {status['initialized']}")
        console.print(f"  Path: {status['store_path']}")

        if status["initialized"]:
            console.print(f"  Branch: {status['branch']}")
            console.print(f"  Commit: {status['commit']}")
            console.print(f"  Clean: {status['clean']}")

            if status["has_remote"]:
                console.print(f"  Remote: {status['remote_url']}")
            else:
                console.print("  Remote: [dim]Not configured[/dim]")

    def cmd_help(self, args: list[str]):
        """Show help information."""
        console.print("[bold]Available Commands:[/bold]\n")

        help_text = {
            "set": "Set a secret value",
            "get": "Get a secret value",
            "list": "List all secrets (use 'list all' for all namespaces)",
            "delete": "Delete a secret",
            "namespace": "Switch namespace or list namespaces (alias: ns)",
            "export": "Export secrets as environment variables",
            "import": "Import secrets from .env file",
            "push": "Push secrets to git store",
            "pull": "Pull secrets from git store",
            "sync": "Sync secrets with git store",
            "status": "Show store status",
            "help": "Show this help",
            "exit": "Exit the shell (alias: quit)",
        }

        for cmd, desc in help_text.items():
            console.print(f"  [cyan]{cmd:12}[/cyan] {desc}")

        console.print("\n[bold]Examples:[/bold]")
        console.print("  set api-key sk-1234567890")
        console.print("  get api-key")
        console.print("  namespace production")
        console.print("  export file production.env")
        console.print("  import .env.local")

    def cmd_exit(self, args: list[str]):
        """Exit the REPL."""
        self.running = False
        console.print("\nGoodbye!")


def run_repl():
    """Entry point for the REPL."""
    repl = SecretsREPL()
    repl.run()
