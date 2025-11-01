# Portable Commands Guide

MCLI now supports portable, JSON-based commands that can be easily shared, edited, and migrated between installations. Commands are stored in `~/.mcli/workflows/` (or `.mcli/workflows/` for local repos) and automatically loaded on startup.

## Overview

- **Storage**: `~/.mcli/workflows/` (portable across machines) or `.mcli/workflows/` (local to git repos)
- **Format**: JSON with embedded Python code
- **Lockfile**: `~/.mcli/workflows/commands.lock.json` (npm-style tracking)
- **Auto-loading**: Commands load automatically under the `workflows` group

## Command Management

### List All Commands
```bash
mcli self list-commands
```

### Add a New Command
```bash
mcli workflow add my-command --description "My custom command"
# Creates ~/.mcli/workflows/my-command.json (or .mcli/workflows/ in git repos)
# Available as: mcli workflows my-command
```

### Remove a Command
```bash
mcli workflow remove my-command
```

## Bidirectional Conversion

### Import Python Script → JSON Command

Convert a Python script into a portable JSON command:

```bash
# Basic import
mcli workflow import-script my_script.py

# With custom name and group
mcli workflow import-script my_script.py --name custom-cmd

# Interactive mode (opens in $EDITOR for review)
mcli workflow import-script my_script.py --interactive
```

**Example Workflow:**
```python
# my_script.py
import click

@click.command()
def app():
    """My awesome command"""
    click.echo("Hello from custom command!")
```

```bash
mcli workflow import-script my_script.py --name awesome
# Now available as: mcli workflows awesome
```

### Export JSON Command → Python Script

Convert a JSON command back to a standalone Python script:

```bash
# Basic export
mcli workflow export-script redis

# Export to specific file
mcli workflow export-script redis --output my_redis.py

# Add standalone runner (for direct execution)
mcli workflow export-script redis --output redis.py --standalone
python redis.py  # Can run directly!
```

### Edit Commands In-Place

Edit a command's code using your $EDITOR:

```bash
# Uses $EDITOR (vim, code, nano, etc.)
mcli workflow edit my-command

# Specify editor
mcli workflow edit my-command --editor code
```

## Round-Trip Workflow

The most powerful feature is the ability to export, edit, and re-import commands:

```bash
# 1. Export to Python for easier editing
mcli workflow export-script redis --output redis.py --standalone

# 2. Edit with your favorite IDE/editor
code redis.py  # or vim, emacs, etc.

# 3. Test standalone (if using --standalone)
python redis.py --help

# 4. Re-import the modified version
mcli workflow import-script redis.py --name redis_v2

# 5. Or update existing
mcli workflow import-script redis.py --name redis
```

## Migrated Commands

The following commands are now portable JSON format:

### Workflow Commands
- `redis` - Redis service management
- `visual` - Visual effects and demos
- `daemon` - Daemon management
- `file` - File utilities
- `git-commit` - Git commit helpers
- `politician-trading` - Trading data
- `scheduler` - Task scheduling
- `sync` - Sync utilities
- `videos` - Video processing
- `dashboard` - ML dashboard

All stored in `~/.mcli/workflows/` (or `.mcli/workflows/` in git repos) and can be:
- Shared by copying JSON files
- Edited with `mcli workflow edit`
- Exported to Python for major changes
- Version controlled separately

## Use Cases

### 1. Quick Script Import
```bash
# Got a useful Python script? Make it an mcli workflow!
mcli workflow import-script ~/scripts/deploy.py --name deploy
mcli workflows deploy
```

### 2. Command Development
```bash
# Start with template
mcli workflow add data-processor

# Edit in your IDE
mcli workflow export-script data-processor --output dp.py
code dp.py

# Test standalone
python dp.py

# Import back when ready
mcli workflow import-script dp.py --name data-processor
```

### 3. Sharing Commands
```bash
# On machine A
mcli workflow export-script my-tool --output my-tool.py

# Share my-tool.py or the JSON directly
scp ~/.mcli/workflows/my-tool.json other-machine:~/.mcli/workflows/

# On machine B - command automatically available!
mcli workflows my-tool
```

### 4. Interactive Editing
```bash
# Quick in-editor changes
mcli workflow edit redis
# Opens in $EDITOR, validates syntax, saves automatically

# Or export → edit → reimport for bigger changes
mcli workflow export-script redis --output redis.py
vim redis.py
mcli workflow import-script redis.py --name redis
```

## File Structure

```
~/.mcli/
└── workflows/
    ├── commands.lock.json       # Lockfile (auto-generated)
    ├── redis.json               # Redis command
    ├── visual.json              # Visual effects
    ├── my-custom.json           # Your custom commands
    └── ...                      # More commands

# Or for local repos:
.mcli/
└── workflows/
    ├── commands.lock.json
    ├── my-workflow.json
    └── ...
```

### JSON Format
```json
{
  "name": "redis",
  "group": "workflow",
  "description": "Redis service management commands",
  "version": "1.0",
  "code": "import click\n\n@click.group(name=\"redis\")\ndef app():\n    pass",
  "metadata": {
    "source": "import-script",
    "imported_at": "2025-10-08T23:26:30"
  },
  "created_at": "2025-10-08T23:26:30",
  "updated_at": "2025-10-08T23:26:30"
}
```

## Best Practices

1. **Use descriptive names**: `data-processor` not `dp`
2. **Add docstrings**: Helps with `--help` output
3. **Test before importing**: Use `--standalone` for testing
4. **Version your commands**: Export to git repo for history
5. **Share via JSON**: More portable than Python scripts
6. **Use interactive mode**: Review before importing unknown scripts

## Tips

- **$EDITOR support**: Set `export EDITOR=code` (or vim, nano, etc.)
- **Syntax validation**: Edit validates before saving
- **Lockfile sync**: Run `mcli workflow verify` to check
- **Auto-reload**: Commands load on next mcli startup
- **Standalone testing**: Use `--standalone` flag for direct Python execution

## Troubleshooting

### Command not showing up
```bash
# Verify it's in the directory
ls ~/.mcli/workflows/  # or .mcli/workflows/ in git repos

# Check lockfile
mcli workflow verify

# Reload mcli
# (just restart or run a new mcli instance)
```

### Syntax errors
```bash
# Edit command will validate
mcli workflow edit my-cmd
# If it has errors, it will warn you

# Or export and check manually
mcli workflow export-script my-cmd --output test.py
python -m py_compile test.py
```

### Import failures
```bash
# Use interactive mode to review first
mcli workflow import-script script.py --interactive
# This opens in $EDITOR before saving
```

## Examples

### Convert Existing Script
```python
# awesome_tool.py
#!/usr/bin/env python3
import click

@click.group()
def cli():
    """Awesome CLI tool"""
    pass

@cli.command()
def deploy():
    """Deploy the application"""
    click.echo("Deploying...")

@cli.command()
def status():
    """Check status"""
    click.echo("Status: OK")

if __name__ == '__main__':
    cli()
```

```bash
# Import it
mcli workflow import-script awesome_tool.py --name awesome

# Now use it
mcli workflows awesome deploy
mcli workflows awesome status
```

### Create Portable Toolkit
```bash
# Export all your commands
for cmd in redis visual dashboard; do
    mcli workflow export-script $cmd --output ~/mcli-toolkit/$cmd.py
done

# Share the directory
tar -czf mcli-toolkit.tar.gz ~/mcli-toolkit/

# On another machine
tar -xzf mcli-toolkit.tar.gz
for script in ~/mcli-toolkit/*.py; do
    mcli workflow import-script $script
done
```

## Advanced: Command Templates

### Group Command Template
```python
import click

@click.group(name="mygroup")
def app():
    """My command group"""
    pass

@app.command()
def subcommand():
    """A subcommand"""
    click.echo("Hello from subcommand!")
```

### Async Command Template
```python
import click
import asyncio

@click.command()
def app():
    """Async command"""
    async def run():
        # Your async code here
        pass

    asyncio.run(run())
```

### Command with Options
```python
import click

@click.command()
@click.option('--name', '-n', default='World', help='Name to greet')
@click.option('--count', '-c', default=1, help='Number of greetings')
def app(name, count):
    """Greet someone"""
    for _ in range(count):
        click.echo(f'Hello {name}!')
```

---

**See also:**
- [Custom Commands Documentation](./custom-commands.md)
- [MCLI Architecture](../README.md#architecture)
