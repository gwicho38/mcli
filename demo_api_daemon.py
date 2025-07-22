#!/usr/bin/env python3
"""
Demo script for MCLI API Daemon integration.

This script demonstrates how to:
1. Start the API daemon
2. Execute commands via the daemon
3. Use the daemon decorator for automatic routing
4. Monitor daemon status

Usage:
    python demo_api_daemon.py
"""

import time
import requests
import json
from pathlib import Path

# Import MCLI daemon components
from mcli.lib.api.daemon_client import get_daemon_client, APIDaemonClient
from mcli.lib.api.daemon_decorator import daemon_command, is_daemon_available
from mcli.workflow.daemon.api_daemon import APIDaemonService

def demo_basic_daemon_usage():
    """Demo basic daemon usage"""
    print("🔧 Demo: Basic Daemon Usage")
    print("=" * 50)
    
    # Create daemon client
    client = get_daemon_client()
    
    # Check if daemon is running
    if client.is_running():
        print("✅ Daemon is running")
        
        # Get status
        status = client.status()
        print(f"📊 Status: {json.dumps(status, indent=2)}")
        
        # List commands
        commands = client.list_commands()
        print(f"📋 Available commands: {commands['total']}")
        
    else:
        print("❌ Daemon is not running")
        print("💡 Start the daemon with: python -m mcli workflow api-daemon start")

def demo_command_execution():
    """Demo command execution via daemon"""
    print("\n🚀 Demo: Command Execution via Daemon")
    print("=" * 50)
    
    client = get_daemon_client()
    
    if not client.is_running():
        print("❌ Daemon is not running. Start it first.")
        return
    
    # Example: Execute a command
    try:
        result = client.execute_command(
            command_name="hello",
            args=["--verbose"]
        )
        print(f"✅ Command executed: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"❌ Command execution failed: {e}")

def demo_decorator_usage():
    """Demo using the daemon decorator"""
    print("\n🎯 Demo: Daemon Decorator Usage")
    print("=" * 50)
    
    # Example function with daemon decorator
    @daemon_command(command_name="demo_function", timeout=30)
    def demo_function(name: str, verbose: bool = False):
        """Example function that can be executed via daemon"""
        result = f"Hello {name}!"
        if verbose:
            result += " (verbose mode)"
        return result
    
    # Execute the function
    try:
        result = demo_function("World", verbose=True)
        print(f"✅ Function result: {result}")
    except Exception as e:
        print(f"❌ Function execution failed: {e}")

def demo_daemon_lifecycle():
    """Demo daemon lifecycle management"""
    print("\n🔄 Demo: Daemon Lifecycle Management")
    print("=" * 50)
    
    client = get_daemon_client()
    
    # Check current status
    print(f"Current status: {'Running' if client.is_running() else 'Stopped'}")
    
    # Try to start daemon via HTTP
    try:
        result = client.start_daemon()
        print(f"Start result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Could not start daemon via HTTP: {e}")
    
    # Wait a moment and check status
    time.sleep(2)
    print(f"Status after start attempt: {'Running' if client.is_running() else 'Stopped'}")

def demo_configuration():
    """Demo configuration options"""
    print("\n⚙️ Demo: Configuration Options")
    print("=" * 50)
    
    # Show current config
    config_path = Path("config.toml")
    if config_path.exists():
        print("📄 Current config.toml:")
        with open(config_path, 'r') as f:
            print(f.read())
    else:
        print("❌ No config.toml found")
    
    # Show environment variables
    print("\n🌍 Environment variables:")
    env_vars = [
        "MCLI_API_DAEMON_ENABLED",
        "MCLI_API_DAEMON_HOST", 
        "MCLI_API_DAEMON_PORT",
        "MCLI_DAEMON_ROUTING"
    ]
    
    for var in env_vars:
        value = os.environ.get(var, "not set")
        print(f"  {var}: {value}")

def demo_advanced_features():
    """Demo advanced daemon features"""
    print("\n🚀 Demo: Advanced Features")
    print("=" * 50)
    
    client = get_daemon_client()
    
    if not client.is_running():
        print("❌ Daemon is not running")
        return
    
    # Health check
    try:
        health = client.health_check()
        print(f"🏥 Health check: {json.dumps(health, indent=2)}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Wait for daemon
    print("⏳ Waiting for daemon to be ready...")
    if client.wait_for_daemon(timeout=10):
        print("✅ Daemon is ready")
    else:
        print("❌ Daemon not ready within timeout")

def main():
    """Main demo function"""
    print("🎭 MCLI API Daemon Demo")
    print("=" * 60)
    print("This demo shows how to integrate the API daemon with MCLI commands.")
    print("The daemon provides persistent command execution and better resource management.")
    print()
    
    # Run demos
    demo_basic_daemon_usage()
    demo_command_execution()
    demo_decorator_usage()
    demo_daemon_lifecycle()
    demo_configuration()
    demo_advanced_features()
    
    print("\n" + "=" * 60)
    print("🎉 Demo completed!")
    print("\n💡 Next steps:")
    print("  1. Start the daemon: python -m mcli workflow api-daemon start")
    print("  2. Enable daemon routing: export MCLI_DAEMON_ROUTING=true")
    print("  3. Use @daemon_command decorator in your functions")
    print("  4. Monitor daemon: python -m mcli workflow api-daemon status")

if __name__ == "__main__":
    import os
    main() 