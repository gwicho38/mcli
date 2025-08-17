import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

# Import the daemon classes
from .commands import Command, CommandDatabase, CommandExecutor


@click.group()
def client():
    """Client CLI for daemon commands."""
    pass


class DaemonClient:
    """Client interface for interacting with the daemon service"""

    def __init__(self, timeout: int = 30):
        self.db = CommandDatabase()
        self.executor = CommandExecutor()
        self.timeout = timeout  # Default timeout for operations
        self._validate_connection()

    def _validate_connection(self):
        """Verify connection to the daemon service"""
        try:
            self.db.get_all_commands()  # Simple query to test connection
        except Exception as e:
            raise ConnectionError(f"Failed to connect to daemon: {str(e)}") from e

    def add_command_from_file(
        self,
        name: str,
        file_path: str,
        description: Optional[str] = None,
        language: str = "python",
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Add a command from a file"""
        # Read the file
        with open(file_path, "r") as f:
            code = f.read()

        # Detect language from file extension if not specified
        if language == "auto":
            ext = Path(file_path).suffix.lower()
            language_map = {
                ".py": "python",
                ".js": "node",
                ".lua": "lua",
                ".sh": "shell",
                ".bash": "shell",
            }
            language = language_map.get(ext, "python")

        # Create command
        command = Command(
            id=str(uuid.uuid4()),
            name=name,
            description=description or f"Command from {file_path}",
            code=code,
            language=language,
            group=group,
            tags=tags or [],
        )

        # Add to database
        return self.db.add_command(command)

    def add_command_from_stdin(
        self,
        name: str,
        description: Optional[str] = None,
        language: str = "python",
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Add a command from stdin"""
        click.echo("Enter your code (Ctrl+D when done):")

        # Read from stdin
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass

        code = "\n".join(lines)

        if not code.strip():
            raise ValueError("No code provided")

        # Create command
        command = Command(
            id=str(uuid.uuid4()),
            name=name,
            description=description or f"Command from stdin",
            code=code,
            language=language,
            group=group,
            tags=tags or [],
        )

        # Add to database
        return self.db.add_command(command)

    def add_command_interactive(self) -> Optional[str]:
        """Interactive command creation"""
        # Get command name
        name = click.prompt("Command name", type=str)

        # Check if name already exists
        existing = self.db.search_commands(name, limit=1)
        if existing and existing[0].name == name:
            if not click.confirm(f"Command '{name}' already exists. Overwrite?"):
                return None

        # Get description
        description = click.prompt("Description (optional)", type=str, default="")

        # Get language
        language = click.prompt(
            "Language", type=click.Choice(["python", "node", "lua", "shell"]), default="python"
        )

        # Get group
        group = click.prompt("Group (optional)", type=str, default="")
        if not group:
            group = None

        # Get tags
        tags_input = click.prompt("Tags (comma-separated, optional)", type=str, default="")
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

        # Get code source
        source = click.prompt(
            "Code source", type=click.Choice(["file", "stdin", "paste"]), default="paste"
        )

        if source == "file":
            file_path = click.prompt("File path", type=click.Path(exists=True))
            return self.add_command_from_file(name, file_path, description, language, group, tags)
        elif source == "stdin":
            return self.add_command_from_stdin(name, description, language, group, tags)
        else:  # paste
            click.echo("Paste your code below (Ctrl+D when done):")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass

            code = "\n".join(lines)

            if not code.strip():
                raise ValueError("No code provided")

            # Create command
            command = Command(
                id=str(uuid.uuid4()),
                name=name,
                description=description or f"Command from paste",
                code=code,
                language=language,
                group=group,
                tags=tags,
            )

            # Add to database
            return self.db.add_command(command)

    def execute_command(self, command_id: str, args: List[str] = None) -> Dict[str, Any]:
        """Execute a command"""
        command = self.db.get_command(command_id)
        if not command:
            raise ValueError(f"Command '{command_id}' not found")

        # Execute
        result = self.executor.execute_command(command, args or [])

        # Record execution
        self.db.record_execution(
            command_id=command_id,
            status=result["status"],
            output=result.get("output", ""),
            error=result.get("error", ""),
            execution_time_ms=result.get("execution_time_ms", 0),
        )

        return result

    def search_commands(self, query: str, limit: int = 10) -> List[Command]:
        """Search for commands"""
        return self.db.search_commands(query, limit)

    def find_similar_commands(self, query: str, limit: int = 5) -> List[tuple]:
        """Find similar commands using cosine similarity"""
        return self.db.find_similar_commands(query, limit)

    def get_all_commands(self) -> List[Command]:
        """Get all commands"""
        return self.db.get_all_commands()

    def get_command(self, command_id: str) -> Optional[Command]:
        """Get a command by ID"""
        return self.db.get_command(command_id)

    def update_command(self, command: Command) -> bool:
        """Update a command"""
        return self.db.update_command(command)

    def delete_command(self, command_id: str) -> bool:
        """Delete a command"""
        return self.db.delete_command(command_id)


# CLI Commands - these will be subcommands under the daemon group
@client.command()
@click.argument("name")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--description", help="Command description")
@click.option(
    "--language",
    type=click.Choice(["python", "node", "lua", "shell", "auto"]),
    default="auto",
    help="Programming language",
)
@click.option("--group", help="Command group")
@click.option("--tags", help="Comma-separated tags")
def add_file(name: str, file_path: str, description: str, language: str, group: str, tags: str):
    """Add a command from a file"""
    client = DaemonClient()

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

    try:
        command_id = client.add_command_from_file(
            name=name,
            file_path=file_path,
            description=description,
            language=language,
            group=group,
            tags=tag_list,
        )
        click.echo(f"✅ Command '{name}' added with ID: {command_id}")
    except Exception as e:
        click.echo(f"❌ Error adding command: {e}", err=True)


@client.command()
@click.argument("name")
@click.option("--description", help="Command description")
@click.option(
    "--language",
    type=click.Choice(["python", "node", "lua", "shell"]),
    default="python",
    help="Programming language",
)
@click.option("--group", help="Command group")
@click.option("--tags", help="Comma-separated tags")
def add_stdin(name: str, description: str, language: str, group: str, tags: str):
    """Add a command from stdin"""
    client = DaemonClient()

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

    try:
        command_id = client.add_command_from_stdin(
            name=name, description=description, language=language, group=group, tags=tag_list
        )
        click.echo(f"✅ Command '{name}' added with ID: {command_id}")
    except Exception as e:
        click.echo(f"❌ Error adding command: {e}", err=True)


@client.command()
def add_interactive():
    """Add a command interactively"""
    client = DaemonClient()

    try:
        command_id = client.add_command_interactive()
        if command_id:
            click.echo(f"✅ Command added with ID: {command_id}")
        else:
            click.echo("Command creation cancelled")
    except Exception as e:
        click.echo(f"❌ Error adding command: {e}", err=True)


@client.command()
@click.argument("command_id")
@click.argument("args", nargs=-1)
def execute(command_id: str, args: List[str]):
    """Execute a command"""
    client = DaemonClient()

    try:
        result = client.execute_command(command_id, list(args))

        if result["success"]:
            click.echo("✅ Command executed successfully")
            if result["output"]:
                click.echo("Output:")
                click.echo(result["output"])
        else:
            click.echo("❌ Command execution failed")
            if result["error"]:
                click.echo(f"Error: {result['error']}")

        click.echo(f"Execution time: {result.get('execution_time_ms', 0)}ms")

    except Exception as e:
        click.echo(f"❌ Error executing command: {e}", err=True)


@client.command()
@click.argument("query")
@click.option("--limit", default=10, help="Maximum number of results")
@click.option("--similar", is_flag=True, help="Use similarity search")
def search(query: str, limit: int, similar: bool):
    """Search for commands"""
    client = DaemonClient()

    try:
        if similar:
            results = client.find_similar_commands(query, limit)
            if results:
                click.echo(f"Found {len(results)} similar command(s):")
                for cmd, similarity in results:
                    click.echo(f"  {cmd.name} ({cmd.language}) - {cmd.description}")
                    click.echo(f"    Similarity: {similarity:.3f}")
                    if cmd.tags:
                        click.echo(f"    Tags: {', '.join(cmd.tags)}")
                    click.echo()
            else:
                click.echo("No similar commands found")
        else:
            commands = client.search_commands(query, limit)
            if commands:
                click.echo(f"Found {len(commands)} command(s):")
                for cmd in commands:
                    click.echo(f"  {cmd.name} ({cmd.language}) - {cmd.description}")
                    if cmd.tags:
                        click.echo(f"    Tags: {', '.join(cmd.tags)}")
                    click.echo()
            else:
                click.echo("No commands found")

    except Exception as e:
        click.echo(f"❌ Error searching commands: {e}", err=True)


@client.command()
@click.option("--group", help="Filter by group")
@click.option("--language", help="Filter by language")
def list(group: str, language: str):
    """List all commands"""
    client = DaemonClient()

    try:
        commands = client.get_all_commands()

        # Apply filters
        if group:
            commands = [cmd for cmd in commands if cmd.group == group]
        if language:
            commands = [cmd for cmd in commands if cmd.language == language]

        if not commands:
            click.echo("No commands found")
            return

        click.echo(f"Found {len(commands)} command(s):")
        for cmd in commands:
            click.echo(f"  {cmd.name} ({cmd.language}) - {cmd.description}")
            if cmd.group:
                click.echo(f"    Group: {cmd.group}")
            if cmd.tags:
                click.echo(f"    Tags: {', '.join(cmd.tags)}")
            click.echo(f"    Executed {cmd.execution_count} times")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing commands: {e}", err=True)


@client.command()
@click.argument("command_id")
def show(command_id: str):
    """Show command details"""
    client = DaemonClient()

    try:
        command = client.get_command(command_id)
        if not command:
            click.echo(f"Command '{command_id}' not found")
            return

        click.echo(f"Command: {command.name}")
        click.echo(f"ID: {command.id}")
        click.echo(f"Description: {command.description}")
        click.echo(f"Language: {command.language}")
        if command.group:
            click.echo(f"Group: {command.group}")
        if command.tags:
            click.echo(f"Tags: {', '.join(command.tags)}")
        click.echo(f"Created: {command.created_at}")
        click.echo(f"Updated: {command.updated_at}")
        click.echo(f"Executed: {command.execution_count} times")
        if command.last_executed:
            click.echo(f"Last executed: {command.last_executed}")
        click.echo()
        click.echo("Code:")
        click.echo("=" * 50)
        click.echo(command.code)
        click.echo("=" * 50)

    except Exception as e:
        click.echo(f"❌ Error showing command: {e}", err=True)


@client.command()
@click.argument("command_id")
def delete(command_id: str):
    """Delete a command"""
    client = DaemonClient()

    try:
        command = client.get_command(command_id)
        if not command:
            click.echo(f"Command '{command_id}' not found")
            return

        if click.confirm(f"Are you sure you want to delete command '{command.name}'?"):
            if client.delete_command(command_id):
                click.echo(f"✅ Command '{command.name}' deleted")
            else:
                click.echo(f"❌ Error deleting command '{command.name}'")
        else:
            click.echo("Deletion cancelled")

    except Exception as e:
        click.echo(f"❌ Error deleting command: {e}", err=True)


@client.command()
@click.argument("command_id")
@click.option("--name", help="New name")
@click.option("--description", help="New description")
@click.option("--group", help="New group")
@click.option("--tags", help="New tags (comma-separated)")
def edit(command_id: str, name: str, description: str, group: str, tags: str):
    """Edit a command"""
    client = DaemonClient()

    try:
        command = client.get_command(command_id)
        if not command:
            click.echo(f"Command '{command_id}' not found")
            return

        # Update fields if provided
        if name:
            command.name = name
        if description:
            command.description = description
        if group:
            command.group = group
        if tags:
            command.tags = [tag.strip() for tag in tags.split(",")]

        command.updated_at = datetime.now()

        if client.update_command(command):
            click.echo(f"✅ Command '{command.name}' updated")
        else:
            click.echo(f"❌ Error updating command '{command.name}'")

    except Exception as e:
        click.echo(f"❌ Error editing command: {e}", err=True)


@client.command()
def groups():
    """List all command groups"""
    client = DaemonClient()

    try:
        commands = client.get_all_commands()
        groups = {}

        for cmd in commands:
            group = cmd.group or "ungrouped"
            if group not in groups:
                groups[group] = []
            groups[group].append(cmd)

        if not groups:
            click.echo("No groups found")
            return

        click.echo("Command groups:")
        for group_name, group_commands in groups.items():
            click.echo(f"  {group_name} ({len(group_commands)} commands)")
            for cmd in group_commands:
                click.echo(f"    - {cmd.name} ({cmd.language})")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing groups: {e}", err=True)


if __name__ == "__main__":
    client()
