#!/usr/bin/env python3
"""
Demo script showing how to use mcli-framework as a Python library

This example demonstrates:
1. Creating custom workflow commands programmatically
2. Using internal utilities (config, logging, file operations)
3. Scheduling automated tasks
4. Working with the command manager
5. Using performance optimization features
"""

import sys
from pathlib import Path
from datetime import datetime

# Core mcli imports
from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.lib.config.config import get_config, save_config
from mcli.lib.paths import get_custom_commands_dir, is_git_repository
from mcli.lib.ui.styling import success, info, warning, error

# Advanced features
from mcli.lib.discovery.command_discovery import ClickCommandDiscovery
from mcli.workflow.script_sync import ScriptSyncSystem


def demo_command_creation():
    """Demonstrate creating custom commands programmatically"""
    print("\n" + "="*60)
    info("📝 Demo 1: Creating Custom Commands")
    print("="*60)

    # Get command manager
    manager = get_command_manager(global_mode=True)

    # Create a data processing command
    data_cmd_code = """
import click
import json
from pathlib import Path

@click.group(name='datatools')
def datatools_group():
    '''Data processing utilities'''
    pass

@datatools_group.command('validate')
@click.argument('file', type=click.Path(exists=True))
def validate_json(file):
    '''Validate JSON file format'''
    try:
        with open(file) as f:
            data = json.load(f)
        click.echo(f'✅ Valid JSON: {len(data)} items' if isinstance(data, list) else '✅ Valid JSON object')
    except json.JSONDecodeError as e:
        click.echo(f'❌ Invalid JSON: {e}', err=True)
        raise click.Abort()

@datatools_group.command('convert')
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--format', type=click.Choice(['json', 'csv']), default='json')
def convert_data(input_file, output_file, format):
    '''Convert data between formats'''
    click.echo(f'Converting {input_file} to {format}...')
    # Conversion logic would go here
    click.echo(f'✅ Saved to {output_file}')
"""

    # Save the command
    try:
        manager.save_command(
            name="datatools",
            code=data_cmd_code,
            description="Data validation and conversion utilities",
            group="utils",
            metadata={
                "author": "MCLI Demo",
                "version": "1.0.0",
                "tags": ["data", "validation", "conversion"],
                "requires": ["json", "pathlib"]
            }
        )
        success("✅ Created command: datatools")
        info("   Run with: mcli workflow datatools validate <file>")
        info("   Or: mcli workflow datatools convert <input> <output> --format json")
    except Exception as e:
        error(f"❌ Failed to create command: {e}")


def demo_command_discovery():
    """Demonstrate command discovery and introspection"""
    print("\n" + "="*60)
    info("🔍 Demo 2: Command Discovery")
    print("="*60)

    discovery = ClickCommandDiscovery()

    # Discover all commands
    try:
        commands = discovery.discover_all_commands()
        success(f"✅ Discovered {len(commands)} total commands")

        # Show some examples
        info("\n📋 Sample commands:")
        for cmd in commands[:5]:
            print(f"   • {cmd.full_name}")
            print(f"     Description: {cmd.description}")
            print(f"     Module: {cmd.module_name}")

        # Group by category
        categories = {}
        for cmd in commands:
            category = cmd.module_name.split(".")[0] if "." in cmd.module_name else "other"
            categories[category] = categories.get(category, 0) + 1

        info("\n📊 Commands by category:")
        for cat, count in sorted(categories.items()):
            print(f"   • {cat}: {count} commands")

    except Exception as e:
        error(f"❌ Discovery failed: {e}")


def demo_configuration():
    """Demonstrate configuration management"""
    print("\n" + "="*60)
    info("⚙️  Demo 3: Configuration Management")
    print("="*60)

    # Load current config
    config = get_config()
    info(f"Current configuration:")
    for key, value in list(config.items())[:5]:
        print(f"   • {key}: {value}")

    # Save custom config
    custom_config = {
        "demo_setting": True,
        "demo_timestamp": datetime.now().isoformat(),
        "demo_value": 42
    }

    try:
        save_config(custom_config)
        success("✅ Configuration saved")
    except Exception as e:
        warning(f"⚠️  Could not save config: {e}")


def demo_path_management():
    """Demonstrate path utilities"""
    print("\n" + "="*60)
    info("📁 Demo 4: Path Management")
    print("="*60)

    # Get commands directory
    global_dir = get_custom_commands_dir(global_mode=True)
    info(f"Global commands directory: {global_dir}")

    if is_git_repository():
        local_dir = get_custom_commands_dir(global_mode=False)
        info(f"Local commands directory: {local_dir}")
    else:
        warning("Not in a git repository - local commands unavailable")

    # List commands
    if global_dir.exists():
        commands = [f.stem for f in global_dir.glob("*.json") if f.stem != "commands.lock"]
        if commands:
            success(f"✅ Found {len(commands)} custom commands:")
            for cmd in commands[:10]:
                print(f"   • {cmd}")
        else:
            info("No custom commands found")


def demo_logger():
    """Demonstrate logging features"""
    print("\n" + "="*60)
    info("📋 Demo 5: Logging")
    print("="*60)

    logger = get_logger()

    # Different log levels
    logger.info("This is an info message")
    logger.debug("This is a debug message (may not show)")
    logger.warning("This is a warning message")

    try:
        # Simulate an error
        raise ValueError("Demo error for logging")
    except ValueError as e:
        logger.error(f"Caught error: {e}")

    success("✅ Logging examples completed")


def demo_script_sync():
    """Demonstrate script synchronization"""
    print("\n" + "="*60)
    info("🔄 Demo 6: Script Synchronization")
    print("="*60)

    # Create a demo script
    demo_script = """#!/usr/bin/env python3
# @description: Demo script for testing sync
# @version: 1.0.0
# @requires: click
# @tags: demo, test

import click

@click.command()
@click.argument('name', default='World')
def greet(name):
    '''Say hello to someone'''
    click.echo(f'Hello, {name}!')

if __name__ == '__main__':
    greet()
"""

    # Save demo script
    demo_dir = Path("/tmp/mcli_demo_scripts")
    demo_dir.mkdir(exist_ok=True)
    script_file = demo_dir / "demo_greet.py"
    script_file.write_text(demo_script)

    info(f"Created demo script: {script_file}")

    # Initialize sync system
    try:
        sync = ScriptSyncSystem(
            scripts_dir=demo_dir,
            commands_dir=get_custom_commands_dir(global_mode=True)
        )

        # Sync scripts
        count = sync.sync_all_scripts()
        success(f"✅ Synced {count} script(s) to JSON")

        info("The script is now available as: mcli workflow demo_greet")

    except Exception as e:
        error(f"❌ Sync failed: {e}")


def demo_command_manager_operations():
    """Demonstrate command manager CRUD operations"""
    print("\n" + "="*60)
    info("🛠️  Demo 7: Command Manager Operations")
    print("="*60)

    manager = get_command_manager(global_mode=True)

    # List all commands
    commands = manager.load_all_commands()
    info(f"Total commands: {len(commands)}")

    # Export commands
    export_path = Path("/tmp/mcli_commands_export.json")
    try:
        manager.export_commands(export_path)
        success(f"✅ Exported commands to: {export_path}")
    except Exception as e:
        error(f"❌ Export failed: {e}")

    # Verify lockfile
    try:
        is_valid, report = manager.verify_lockfile()
        if is_valid:
            success("✅ Lockfile is valid and up-to-date")
        else:
            warning(f"⚠️  Lockfile issues: {report}")
    except Exception as e:
        warning(f"⚠️  Could not verify lockfile: {e}")


def main():
    """Run all demos"""
    print("\n" + "="*70)
    print("  MCLI Framework - Library Usage Demo")
    print("  Demonstrating mcli-framework as a Python library")
    print("="*70)

    try:
        demo_path_management()
        demo_configuration()
        demo_logger()
        demo_command_discovery()
        demo_command_creation()
        demo_script_sync()
        demo_command_manager_operations()

        print("\n" + "="*70)
        success("🎉 All demos completed successfully!")
        print("="*70)

        print("\n📚 Next steps:")
        print("   • Check the created commands with: mcli workflow --help")
        print("   • Read the SDK docs: docs/SDK.md")
        print("   • Explore more examples in: examples/")
        print("   • Build your own workflows!")

    except KeyboardInterrupt:
        warning("\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        error(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
