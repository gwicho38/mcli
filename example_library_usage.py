#!/usr/bin/env python3
"""
Example: Using mcli as a Python Library

This script demonstrates how to use the mcli package as a library
in your own Python scripts and applications.

Note: This script should be run with the virtual environment activated:
    source .venv/bin/activate
    python example_library_usage.py
"""

import sys
import os

def main():
    """Demonstrate using mcli as a library."""
    
    print("=== MCLI Library Usage Example ===\n")
    
    # Example 1: Import and use mcli logger
    try:
        from mcli.lib.logger.logger import get_logger
        print("✅ Successfully imported mcli.lib.logger.logger")
        
        # Initialize logger
        logger = get_logger("example")
        logger.info("MCLI library is working!")
        print("✅ Logger initialized and working")
        
    except ImportError as e:
        print(f"❌ Failed to import logger: {e}")
        print("💡 Make sure to activate the virtual environment:")
        print("   source .venv/bin/activate")
        return
    
    # Example 2: Import and use filesystem functions
    try:
        from mcli.lib.fs.fs import get_user_home, get_absolute_path, ensure_directory_exists
        print("✅ Successfully imported mcli.lib.fs.fs functions")
        
        # Use filesystem functionality
        home_dir = get_user_home()
        abs_path = get_absolute_path("~/Documents")
        print(f"✅ User home: {home_dir}")
        print(f"✅ Absolute path: {abs_path}")
        
    except ImportError as e:
        print(f"❌ Failed to import filesystem functions: {e}")
    
    # Example 3: Import and use config functions
    try:
        from mcli.lib.config.config import get_config_directory, get_config_for_file
        print("✅ Successfully imported mcli.lib.config.config functions")
        
        # Use config functionality
        config_dir = get_config_directory()
        print(f"✅ Config directory: {config_dir}")
        
    except ImportError as e:
        print(f"❌ Failed to import config functions: {e}")
    
    # Example 4: Import and use shell functions
    try:
        from mcli.lib.shell.shell import shell_exec
        print("✅ Successfully imported mcli.lib.shell.shell")
        
        # Note: shell_exec is available but we won't execute it in this example
        print("✅ Shell functions available")
        
    except ImportError as e:
        print(f"❌ Failed to import shell functions: {e}")
    
    # Example 5: Import and use TOML functions
    try:
        from mcli.lib.toml.toml import read_from_toml
        print("✅ Successfully imported mcli.lib.toml.toml")
        
        print("✅ TOML functions available")
        
    except ImportError as e:
        print(f"❌ Failed to import TOML functions: {e}")
    
    # Example 6: Import and use API functions
    try:
        from mcli.lib.api.api import APIClient
        print("✅ Successfully imported mcli.lib.api.api")
        
        # Note: APIClient might not be available, let's check
        print("✅ API functions available")
        
    except ImportError as e:
        print(f"❌ Failed to import API functions: {e}")
    
    # Example 7: Import and use auth functions
    try:
        from mcli.lib.auth.auth import AuthManager
        print("✅ Successfully imported mcli.lib.auth.auth")
        
        print("✅ Auth functions available")
        
    except ImportError as e:
        print(f"❌ Failed to import auth functions: {e}")
    
    # Example 8: Import workflow functions
    try:
        from mcli.workflow.repo.repo import repo
        print("✅ Successfully imported mcli.workflow.repo.repo")
        
        print("✅ Repository workflow available")
        
    except ImportError as e:
        print(f"❌ Failed to import repo workflow: {e}")
    
    # Example 9: Import file workflow
    try:
        from mcli.workflow.file.file import file
        print("✅ Successfully imported mcli.workflow.file.file")
        
        print("✅ File workflow available")
        
    except ImportError as e:
        print(f"❌ Failed to import file workflow: {e}")
    
    print("\n=== Library Usage Complete ===")
    print("\nYou can now use mcli as a library in your Python scripts!")
    print("Example usage patterns:")
    print("- Import logger: from mcli.lib.logger.logger import get_logger")
    print("- Import filesystem: from mcli.lib.fs.fs import get_user_home, get_absolute_path")
    print("- Import config: from mcli.lib.config.config import get_config_directory")
    print("- Import shell: from mcli.lib.shell.shell import shell_exec")
    print("- Import TOML: from mcli.lib.toml.toml import read_from_toml")
    print("- Import workflows: from mcli.workflow.repo.repo import repo")
    print("\nTo use in your own scripts:")
    print("1. Activate the virtual environment: source .venv/bin/activate")
    print("2. Import mcli modules in your Python code")
    print("3. Use the functionality as shown above")
    
    print("\n=== Available Functions Summary ===")
    print("Core Library Functions:")
    print("- get_logger(name) - Get a logger instance")
    print("- get_user_home() - Get user home directory")
    print("- get_absolute_path(path) - Get absolute path")
    print("- ensure_directory_exists(dirpath) - Create directory if it doesn't exist")
    print("- get_config_directory() - Get config directory")
    print("- shell_exec(command) - Execute shell commands")
    print("- read_from_toml(file_path) - Read TOML files")

if __name__ == "__main__":
    main() 