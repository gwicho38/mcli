# Custom Commands Guide

MCLI now supports **portable custom commands** that are automatically loaded at startup and persist across updates. This feature is similar to npm's package.json/package-lock.json system, allowing you to define, share, and manage custom CLI utilities.

## Overview

Custom commands are stored as JSON files in `~/.mcli/commands/` and are automatically loaded when MCLI starts. **All user-created commands are automatically nested under the `workflow` group**, making them organized and easy to manage.

This makes them:

- **Portable**: Copy your `~/.mcli/commands/` directory to another machine and your commands work immediately
- **Persistent**: Commands survive `mcli self update` since they're stored outside the package directory
- **Versioned**: Each command has version tracking and a lockfile for state management
- **Shareable**: Export/import commands as JSON for easy distribution
- **Organized**: All custom commands live under `mcli workflow` by default

## Quick Start

### Creating a Custom Workflow Command

```bash
# Create a workflow command (defaults to workflow group)
mcli self add-command hello_world -d "My hello world command"

# Run it
mcli workflow hello_world hello

# Create a command with description
mcli self add-command my_tool -d "My custom utility"

# Create a command in a different group
mcli self add-command analytics --group data
```

### Viewing Custom Commands

```bash
# List all custom commands
mcli self list-commands

# Output example:
# ┏━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┓
# ┃ Name      ┃ Group ┃ Description   ┃ Version ┃ Updated    ┃
# ┡━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
# │ hello     │ -     │ Custom cmd    │ 1.0     │ 2025-01-15 │
# └───────────┴───────┴───────────────┴─────────┴────────────┘
```

### Removing Custom Commands

```bash
# Remove a command (with confirmation)
mcli self remove-command hello_world

# Skip confirmation
mcli self remove-command hello_world -y
```

## Command Storage

### Directory Structure

```
~/.mcli/
└── commands/
    ├── hello_world.json      # Command definition
    ├── my_tool.json          # Another command
    └── commands.lock.json    # Lockfile (auto-generated)
```

### Command JSON Format

Each command is stored as a JSON file with the following structure:

```json
{
  "name": "hello_world",
  "code": "import click\n\n@click.command()\ndef hello():\n    click.echo('Hello, World!')",
  "description": "A simple hello world command",
  "group": null,
  "version": "1.0",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "metadata": {}
}
```

## Lockfile Management

The `commands.lock.json` file tracks all installed commands and their metadata, similar to npm's package-lock.json.

### Lockfile Format

```json
{
  "version": "1.0",
  "generated_at": "2025-01-15T10:30:00Z",
  "commands": {
    "hello_world": {
      "name": "hello_world",
      "description": "A simple hello world command",
      "group": null,
      "version": "1.0",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  }
}
```

### Lockfile Commands

```bash
# Verify lockfile matches current commands
mcli self verify-commands

# Update lockfile (usually automatic)
mcli self update-lockfile
```

## Import/Export

### Exporting Commands

Export all your custom commands to a single JSON file for backup or sharing:

```bash
# Export to default file (commands-export.json)
mcli self export-commands

# Export to specific file
mcli self export-commands my-commands.json
```

### Importing Commands

Import commands from a JSON file:

```bash
# Import commands (skip existing)
mcli self import-commands my-commands.json

# Import and overwrite existing commands
mcli self import-commands my-commands.json --overwrite
```

### Example Export Format

```json
[
  {
    "name": "hello_world",
    "code": "import click\n...",
    "description": "Hello world command",
    "group": null,
    "version": "1.0",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z",
    "metadata": {}
  },
  {
    "name": "analytics",
    "code": "import click\n...",
    "description": "Data analytics command",
    "group": "data",
    "version": "1.0",
    "created_at": "2025-01-15T11:00:00Z",
    "updated_at": "2025-01-15T11:00:00Z",
    "metadata": {}
  }
]
```

## Sharing Commands Across Machines

### Method 1: Copy Directory

Simply copy your `~/.mcli/commands/` directory to another machine:

```bash
# On source machine
tar -czf mcli-commands.tar.gz ~/.mcli/commands/

# On target machine
tar -xzf mcli-commands.tar.gz -C ~/
```

### Method 2: Export/Import

```bash
# On source machine
mcli self export-commands my-commands.json

# Copy my-commands.json to target machine, then:
mcli self import-commands my-commands.json
```

## Command Development

### Command Template

When you run `mcli self add-command`, MCLI generates a template based on whether you specify a group:

#### Standalone Command Template

```python
"""
my_command command for mcli.self.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

def my_command_command(name: str = "World"):
    """
    My_command command.
    """
    logger.info(f"Hello, {name}! This is the my_command command.")
    click.echo(f"Hello, {name}! This is the my_command command.")
```

#### Group Command Template

```python
"""
my_command command for mcli.my_group.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

@click.group(name="my_command")
def my_command_group():
    """Description for my_command command group."""
    pass

@my_command_group.command("hello")
@click.argument("name", default="World")
def hello(name: str):
    """Example subcommand."""
    logger.info(f"Hello, {name}! This is the my_command command.")
    click.echo(f"Hello, {name}! This is the my_command command.")
```

### Editing Commands

You can directly edit command JSON files in `~/.mcli/commands/`:

```bash
# Edit a command
vim ~/.mcli/commands/hello_world.json

# After editing, update the lockfile
mcli self update-lockfile
```

## Auto-Loading

Custom commands are automatically loaded when MCLI starts. The loading happens in `mcli/app/main.py` during the `_add_lazy_commands` function.

### Loading Process

1. MCLI starts up
2. Custom command manager scans `~/.mcli/commands/`
3. Each `.json` file (except lockfile) is loaded
4. Commands are dynamically registered with Click
5. Commands become available immediately

### Troubleshooting

If commands don't load:

```bash
# Check MCLI logs for errors
mcli self logs -n 100 | grep -i "custom command"

# Verify commands directory exists
ls -la ~/.mcli/commands/

# Verify lockfile is valid
mcli self verify-commands
```

## Best Practices

### 1. Use Descriptive Names

```bash
# Good
mcli self add-command analyze_logs -d "Parse and analyze log files"

# Less descriptive
mcli self add-command logs
```

### 2. Organize with Groups

```bash
# Group related commands
mcli self add-command stats --group analytics
mcli self add-command report --group analytics
mcli self add-command viz --group analytics
```

### 3. Export Regularly

```bash
# Backup your commands weekly
mcli self export-commands ~/backups/mcli-commands-$(date +%Y%m%d).json
```

### 4. Version Control

Consider tracking your commands export in git:

```bash
# Add to your dotfiles repo
mcli self export-commands ~/dotfiles/mcli-commands.json
cd ~/dotfiles
git add mcli-commands.json
git commit -m "Update MCLI custom commands"
```

### 5. Keep Lockfile in Sync

The lockfile is automatically updated when you add/remove commands, but you can manually sync if needed:

```bash
# Verify state
mcli self verify-commands

# Update if needed
mcli self update-lockfile
```

## Advanced Usage

### Programmatic Access

You can use the custom command manager in your Python code:

```python
from mcli.lib.custom_commands import get_command_manager

# Get manager instance
manager = get_command_manager()

# List all commands
commands = manager.load_all_commands()

# Save a new command
manager.save_command(
    name="my_cmd",
    code="import click\n...",
    description="My command",
)

# Export commands
manager.export_commands(Path("~/export.json"))
```

### Custom Metadata

You can add custom metadata to commands:

```python
manager.save_command(
    name="my_cmd",
    code="...",
    description="My command",
    metadata={
        "author": "John Doe",
        "tags": ["utility", "data"],
        "requires": ["pandas", "numpy"]
    }
)
```

## Migrating Workflow Commands to JSON

MCLI now provides a tool to extract existing workflow commands as JSON templates:

```bash
# Extract all workflow commands to JSON
mcli self extract-workflow-commands

# Extract to specific file
mcli self extract-workflow-commands -o my-workflows.json

# Import the extracted commands
mcli self import-commands workflow-commands.json

# Customize the code in ~/.mcli/commands/<command>.json
```

This creates portable templates for all workflow commands that you can customize and share.

## Migration from Old System

If you have commands in the old system (stored in source tree), you can migrate them:

1. Use `mcli self extract-workflow-commands` to export workflow commands
2. Use `mcli self add-command` to create new portable versions
3. Copy the code from old command files to new JSON files
4. Update the lockfile: `mcli self update-lockfile`
5. Verify: `mcli self verify-commands`

## Troubleshooting

### Command Not Loading

**Issue**: Custom command doesn't appear after creation

**Solutions**:
1. Check if file exists: `ls ~/.mcli/commands/`
2. Verify JSON is valid: `cat ~/.mcli/commands/YOUR_CMD.json | python -m json.tool`
3. Check logs: `mcli self logs -n 50 | grep custom`
4. Restart MCLI or start a new shell session

### Import Conflicts

**Issue**: Import fails with existing command

**Solutions**:
```bash
# Use --overwrite flag
mcli self import-commands file.json --overwrite

# Or remove existing first
mcli self remove-command existing_cmd -y
mcli self import-commands file.json
```

### Lockfile Out of Sync

**Issue**: `verify-commands` shows discrepancies

**Solutions**:
```bash
# Update lockfile
mcli self update-lockfile

# Or regenerate from scratch
rm ~/.mcli/commands/commands.lock.json
mcli self update-lockfile
```

## API Reference

### CLI Commands

- `mcli self add-command NAME [-g GROUP] [-d DESCRIPTION]` - Create a new command (defaults to workflow group)
- `mcli self list-commands` - List all custom commands
- `mcli self remove-command NAME [-y]` - Remove a command
- `mcli self export-commands [FILE]` - Export commands to JSON
- `mcli self import-commands FILE [--overwrite]` - Import commands from JSON
- `mcli self extract-workflow-commands [-o FILE]` - Extract workflow commands as JSON templates
- `mcli self verify-commands` - Verify lockfile state
- `mcli self update-lockfile` - Update the lockfile

### Python API

```python
from mcli.lib.custom_commands import (
    CustomCommandManager,
    get_command_manager,
    load_custom_commands
)

# Get singleton manager
manager = get_command_manager()

# Manager methods
manager.save_command(name, code, description, group, metadata)
manager.load_command(command_file)
manager.load_all_commands()
manager.delete_command(name)
manager.generate_lockfile()
manager.update_lockfile()
manager.load_lockfile()
manager.verify_lockfile()
manager.export_commands(export_path)
manager.import_commands(import_path, overwrite)
```

## Future Enhancements

Planned features:

- Command dependencies (one command requiring another)
- Remote command repositories (like npm registry)
- Command versioning and upgrade tracking
- Built-in command marketplace
- Command testing framework
- Auto-generated documentation

## Support

For issues or questions:

1. Check logs: `mcli self logs`
2. Verify installation: `mcli self verify-commands`
3. Report issues on GitHub: https://github.com/gwicho38/mcli/issues
