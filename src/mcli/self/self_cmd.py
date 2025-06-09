"""
Self-management commands for mcli.
Provides utilities for maintaining and extending the CLI itself.
"""
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
import tomli
import os

try:
    import warnings
    # Suppress the warning about python-Levenshtein
    warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher")
    from fuzzywuzzy import process
except ImportError:
    process = None

from mcli.lib.logger.logger import get_logger

logger = get_logger()

# Create a Click command group instead of Typer
@click.group(name="self", help="Manage and extend the mcli application")
def self_app():
    """
    Self-management commands for mcli.
    """
    pass

console = Console()

def get_command_template(name: str, group: Optional[str] = None) -> str:
    """Generate template code for a new command."""
    
    if group:
        # Template for a command in a group using Click
        template = f'''"""
{name} command for mcli.{group}.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

# Create a Click command group
@click.group(name="{name}")
def {name}_group():
    """Description for {name} command group."""
    pass

@{name}_group.command("hello")
@click.argument("name", default="World")
def hello(name: str):
    """Example subcommand."""
    logger.info(f"Hello, {{name}}! This is the {name} command.")
    click.echo(f"Hello, {{name}}! This is the {name} command.")
'''
    else:
        # Template for a command directly under self using Click
        template = f'''"""
{name} command for mcli.self.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()

def {name}_command(name: str = "World"):
    """
    {name.capitalize()} command.
    """
    logger.info(f"Hello, {{name}}! This is the {name} command.")
    click.echo(f"Hello, {{name}}! This is the {name} command.")
'''
    
    return template

@self_app.command("search")
@click.argument("query", required=False)
@click.option("--full", "-f", is_flag=True, help="Show full command paths and descriptions")
def search(query, full):
    """
    Search for available commands using fuzzy matching.
    
    Similar to telescope in neovim, this allows quick fuzzy searching
    through all available commands in mcli.
    
    If no query is provided, lists all commands.
    """
    # Collect all commands from the application
    commands = collect_commands()
    
    # Display the commands in a table
    table = Table(title="mcli Commands")
    table.add_column("Command", style="green")
    table.add_column("Group", style="blue")
    if full:
        table.add_column("Path", style="dim")
        table.add_column("Description", style="yellow")
    
    if query:
        filtered_commands = []
        
        # Try to use fuzzywuzzy for better matching if available
        if process:
            # Extract command names for matching
            command_names = [f"{cmd['group']}.{cmd['name']}" if cmd['group'] else cmd['name'] for cmd in commands]
            matches = process.extract(query, command_names, limit=10)
            
            # Filter to matched commands
            match_indices = [command_names.index(match[0]) for match in matches if match[1] > 50]
            filtered_commands = [commands[i] for i in match_indices]
        else:
            # Fallback to simple substring matching
            filtered_commands = [
                cmd for cmd in commands 
                if query.lower() in cmd['name'].lower() or 
                (cmd['group'] and query.lower() in cmd['group'].lower())
            ]
        
        commands = filtered_commands
    
    # Sort commands by group then name
    commands.sort(key=lambda c: (c['group'] if c['group'] else '', c['name']))
    
    # Add rows to the table
    for cmd in commands:
        if full:
            table.add_row(
                cmd['name'], 
                cmd['group'] if cmd['group'] else "-", 
                cmd['path'],
                cmd['help'] if cmd['help'] else ""
            )
        else:
            table.add_row(
                cmd['name'], 
                cmd['group'] if cmd['group'] else "-"
            )
    
    console.print(table)
    
    if not commands:
        logger.info("No commands found matching the search query")
        click.echo("No commands found matching the search query")
    
    return 0

def collect_commands() -> List[Dict[str, Any]]:
    """Collect all commands from the mcli application."""
    commands = []
    
    # Look for command modules in the mcli package
    mcli_path = Path(__file__).parent.parent
    
    # This finds command groups as directories under mcli
    for item in mcli_path.iterdir():
        if item.is_dir() and not item.name.startswith("__") and not item.name.startswith("."):
            group_name = item.name
            
            # Recursively find all Python files that might define commands
            for py_file in item.glob("**/*.py"):
                if py_file.name.startswith("__"):
                    continue
                
                # Convert file path to module path
                relative_path = py_file.relative_to(mcli_path.parent)
                module_name = ".".join(relative_path.with_suffix("").parts)
                
                try:
                    # Try to import the module
                    module = importlib.import_module(module_name)
                    
                    # Extract command and group objects
                    for name, obj in inspect.getmembers(module):
                        # Handle Click commands and groups
                        if isinstance(obj, click.Command):
                            if isinstance(obj, click.Group):
                                # Found a Click group
                                app_info = {
                                    'name': obj.name,
                                    'group': group_name,
                                    'path': module_name,
                                    'help': obj.help
                                }
                                commands.append(app_info)
                                
                                # Add subcommands if any
                                for cmd_name, cmd in obj.commands.items():
                                    commands.append({
                                        'name': cmd_name,
                                        'group': f"{group_name}.{app_info['name']}",
                                        'path': f"{module_name}.{cmd_name}",
                                        'help': cmd.help
                                    })
                            else:
                                # Found a standalone Click command
                                commands.append({
                                    'name': obj.name,
                                    'group': group_name,
                                    'path': f"{module_name}.{obj.name}",
                                    'help': obj.help
                                })
                except (ImportError, AttributeError) as e:
                    logger.debug(f"Skipping {module_name}: {e}")
    
    return commands

@self_app.command("add-command")
@click.argument("command_name", required=True)
@click.option("--group", "-g", help="Optional command group to create under")
def add_command (command_name, group):
    """
    Generate a new command template that can be used by mcli.
    
    Example:
        mcli self add my_command
        mcli self add feature_command --group features
    """
    command_name = command_name.lower().replace("-", "_")
    
    # Validate command name
    if not re.match(r'^[a-z][a-z0-9_]*$', command_name):
        logger.error(f"Invalid command name: {command_name}. Use lowercase letters, numbers, and underscores (starting with a letter).")
        click.echo(f"Invalid command name: {command_name}. Use lowercase letters, numbers, and underscores (starting with a letter).", err=True)
        return 1
    
    mcli_path = Path(__file__).parent.parent
    
    if group:
        # Creating under a specific group
        command_group = group.lower().replace("-", "_")
        
        # Validate group name
        if not re.match(r'^[a-z][a-z0-9_]*$', command_group):
            logger.error(f"Invalid group name: {command_group}. Use lowercase letters, numbers, and underscores (starting with a letter).")
            click.echo(f"Invalid group name: {command_group}. Use lowercase letters, numbers, and underscores (starting with a letter).", err=True)
            return 1
            
        # Check if group exists, create if needed
        group_path = mcli_path / command_group
        if not group_path.exists():
            # Create group directory and __init__.py
            group_path.mkdir(parents=True, exist_ok=True)
            with open(group_path / "__init__.py", "w") as f:
                f.write(f'"""\n{command_group.capitalize()} commands for mcli.\n"""')
            logger.info(f"Created new command group directory: {command_group}")
            click.echo(f"Created new command group directory: {command_group}")
        
        # Create command file
        command_file_path = group_path / f"{command_name}.py"
        if command_file_path.exists():
            logger.warning(f"Command file already exists: {command_file_path}")
            should_override = Prompt.ask("File already exists. Override?", choices=["y", "n"], default="n")
            if should_override.lower() != "y":
                logger.info("Command creation aborted.")
                click.echo("Command creation aborted.")
                return 1
                
        # Generate command file
        with open(command_file_path, "w") as f:
            f.write(get_command_template(command_name, command_group))
            
        logger.info(f"Created new command: {command_name} in group: {command_group}")
        click.echo(f"Created new command: {command_name} in group: {command_group}")
        click.echo(f"File created: {command_file_path}")
        click.echo(f"To use this command, add 'from mcli.{command_group}.{command_name} import {command_name}_group' to your main imports")
        click.echo(f"Then add '{command_name}_group to your main CLI group using app.add_command({command_name}_group)'")
        
    else:
        # Creating directly under self
        command_file_path = mcli_path / "self" / f"{command_name}.py"
        
        if command_file_path.exists():
            logger.warning(f"Command file already exists: {command_file_path}")
            should_override = Prompt.ask("File already exists. Override?", choices=["y", "n"], default="n")
            if should_override.lower() != "y":
                logger.info("Command creation aborted.")
                click.echo("Command creation aborted.")
                return 1
        
        # Generate command file
        with open(command_file_path, "w") as f:
            f.write(get_command_template(command_name))
            
        # Update self_cmd.py to import and register the new command
        with open(Path(__file__), "r") as f:
            content = f.read()
            
        # Add import statement if not exists
        import_statement = f"from mcli.self.{command_name} import {command_name}_command"
        if import_statement not in content:
            import_section_end = content.find("logger = get_logger()")
            if import_section_end != -1:
                updated_content = content[:import_section_end] + import_statement + "\n" + content[import_section_end:]
                
                # Add command registration (Click syntax)
                registration = f"@self_app.command('{command_name}')\ndef {command_name}(name=\"World\"):\n    return {command_name}_command(name)\n"
                registration_point = updated_content.rfind("def ")
                if registration_point != -1:
                    # Find the end of the last function
                    last_func_end = updated_content.find("\n\n", registration_point)
                    if last_func_end != -1:
                        updated_content = updated_content[:last_func_end + 2] + registration + updated_content[last_func_end + 2:]
                    else:
                        updated_content += "\n\n" + registration
                
                with open(Path(__file__), "w") as f:
                    f.write(updated_content)
            
        logger.info(f"Created new command: {command_name} in self module")
        click.echo(f"Created new command: {command_name} in self module")
        click.echo(f"File created: {command_file_path}")
        click.echo(f"Command has been automatically registered with self_app")
        
    return 0


@click.group("plugin")
def plugin():
    """
    Manage plugins for mcli.

    Use one of the subcommands: add, remove, update.
    """
    logger.info("Plugin management commands loaded")
    pass

@plugin.command("add")
@click.argument("plugin_name")
@click.argument("repo_url", required=False)
def plugin_add(plugin_name, repo_url=None):
    """Add a new plugin."""
    # First, check for config path in environment variable
    logger.info(f"Adding plugin: {plugin_name} with repo URL: {repo_url}")
    config_env = os.environ.get("MCLI_CONFIG")
    config_path = None

    if config_env and Path(config_env).expanduser().exists():
        config_path = Path(config_env).expanduser()
    else:
        # Default to $HOME/.config/mcli/config.toml
        home_config = Path.home() / ".config" / "mcli" / "config.toml"
        if home_config.exists():
            config_path = home_config
        else:
            # Fallback to top-level config.toml
            top_level_config = Path(__file__).parent.parent.parent / "config.toml"
            if top_level_config.exists():
                config_path = top_level_config

    if not config_path or not config_path.exists():
        click.echo("Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root.", err=True)
        return 1

    with open(config_path, "rb") as f:
        config = tomli.load(f)

    # Example: plugins are listed under [plugins]
    plugins = config.get("plugins", {})
    if plugin_name in plugins:
        click.echo(f"Plugin '{plugin_name}' already exists in config.toml.")
        return 1

    # Determine plugin install path
    plugin_path = None
    # 1. Check config file for plugin location
    plugin_location = config.get("plugin_location")
    if plugin_location:
        plugin_path = Path(plugin_location).expanduser()
    else:
        # 2. Check env variable
        env_plugin_path = os.environ.get("MCLI_PLUGIN_PATH")
        if env_plugin_path:
            plugin_path = Path(env_plugin_path).expanduser()
        else:
            # 3. Default location
            plugin_path = Path.home() / ".config" / "mcli" / "plugins"

    plugin_path.mkdir(parents=True, exist_ok=True)

    # Download the repo if a URL is provided
    if repo_url:
        import subprocess
        dest = plugin_path / plugin_name
        if dest.exists():
            click.echo(f"Plugin directory already exists at {dest}. Aborting download.", err=True)
            return 1
        try:
            click.echo(f"Cloning {repo_url} into {dest} ...")
            subprocess.run(["git", "clone", repo_url, str(dest)], check=True)
            click.echo(f"Plugin '{plugin_name}' cloned to {dest}")
        except Exception as e:
            click.echo(f"Failed to clone repository: {e}", err=True)
            return 1
    else:
        click.echo("No repo URL provided, plugin will not be downloaded.")

    # TODO: Optionally update config.toml to register the new plugin

    return 0

@plugin.command("remove")
@click.argument("plugin_name")
def plugin_remove(plugin_name):
    """Remove an existing plugin."""
    # Determine plugin install path as in plugin_add
    logger.info(f"Removing plugin: {plugin_name}")
    config_env = os.environ.get("MCLI_CONFIG")
    config_path = None

    if config_env and Path(config_env).expanduser().exists():
        config_path = Path(config_env).expanduser()
    else:
        home_config = Path.home() / ".config" / "mcli" / "config.toml"
        if home_config.exists():
            config_path = home_config
        else:
            top_level_config = Path(__file__).parent.parent.parent / "config.toml"
            if top_level_config.exists():
                config_path = top_level_config

    if not config_path or not config_path.exists():
        click.echo("Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root.", err=True)
        return 1

    with open(config_path, "rb") as f:
        config = tomli.load(f)

    plugin_location = config.get("plugin_location")
    if plugin_location:
        plugin_path = Path(plugin_location).expanduser()
    else:
        env_plugin_path = os.environ.get("MCLI_PLUGIN_PATH")
        if env_plugin_path:
            plugin_path = Path(env_plugin_path).expanduser()
        else:
            plugin_path = Path.home() / ".config" / "mcli" / "plugins"

    dest = plugin_path / plugin_name
    if not dest.exists():
        click.echo(f"Plugin directory does not exist at {dest}. Nothing to remove.", err=True)
        return 1

    import shutil
    try:
        shutil.rmtree(dest)
        click.echo(f"Plugin '{plugin_name}' removed from {dest}")
    except Exception as e:
        click.echo(f"Failed to remove plugin: {e}", err=True)
        return 1

    # TODO: Optionally update config.toml to unregister the plugin

    return 0

@plugin.command("update")
@click.argument("plugin_name")
def plugin_update(plugin_name):
    """Update an existing plugin (git pull on default branch)."""
    """Update an existing plugin by pulling the latest changes from its repository."""
    # Determine plugin install path as in plugin_add
    config_env = os.environ.get("MCLI_CONFIG")
    config_path = None

    if config_env and Path(config_env).expanduser().exists():
        config_path = Path(config_env).expanduser()
    else:
        home_config = Path.home() / ".config" / "mcli" / "config.toml"
        if home_config.exists():
            config_path = home_config
        else:
            top_level_config = Path(__file__).parent.parent.parent / "config.toml"
            if top_level_config.exists():
                config_path = top_level_config

    if not config_path or not config_path.exists():
        click.echo("Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root.", err=True)
        return 1

    with open(config_path, "rb") as f:
        config = tomli.load(f)

    plugin_location = config.get("plugin_location")
    if plugin_location:
        plugin_path = Path(plugin_location).expanduser()
    else:
        env_plugin_path = os.environ.get("MCLI_PLUGIN_PATH")
        if env_plugin_path:
            plugin_path = Path(env_plugin_path).expanduser()
        else:
            plugin_path = Path.home() / ".config" / "mcli" / "plugins"

    dest = plugin_path / plugin_name
    if not dest.exists():
        click.echo(f"Plugin directory does not exist at {dest}. Cannot update.", err=True)
        return 1

    import subprocess
    try:
        click.echo(f"Updating plugin '{plugin_name}' in {dest} ...")
        subprocess.run(["git", "-C", str(dest), "pull"], check=True)
        click.echo(f"Plugin '{plugin_name}' updated (git pull).")
    except Exception as e:
        click.echo(f"Failed to update plugin: {e}", err=True)
        return 1

    return 0

# Register the plugin group with self_app
self_app.add_command(plugin)

# This part is important to make the command available to the CLI
if __name__ == "__main__":
    self_app()