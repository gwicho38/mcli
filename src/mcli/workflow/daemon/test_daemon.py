#!/usr/bin/env python3
"""
Test script for the MCLI Daemon Service.

This script demonstrates the daemon functionality by creating and executing
example commands in different programming languages.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path


def create_test_scripts():
    """Create test scripts for different languages"""
    scripts = {}

    # Python script
    python_script = '''#!/usr/bin/env python3
import sys
import json

def process_data(input_data):
    """Process input data and return result"""
    try:
        data = json.loads(input_data)
        result = {
            "processed": True,
            "count": len(data),
            "sum": sum(data) if isinstance(data, list) else 0,
            "timestamp": time.time()
        }
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    import time
    input_data = sys.argv[1] if len(sys.argv) > 1 else '[1, 2, 3, 4, 5]'
    result = process_data(input_data)
    print(result)
'''
    scripts["python"] = python_script

    # Node.js script
    node_script = """#!/usr/bin/env node
const fs = require('fs');

function processFile(filename) {
    try {
        const content = fs.readFileSync(filename, 'utf8');
        const lines = content.split('\\n').filter(line => line.trim());
        const result = {
            filename: filename,
            lineCount: lines.length,
            wordCount: content.split('\\s+').filter(word => word.trim()).length,
            timestamp: new Date().toISOString()
        };
        console.log(JSON.stringify(result, null, 2));
    } catch (error) {
        console.error(JSON.stringify({error: error.message}));
    }
}

const filename = process.argv[2] || __filename;
processFile(filename);
"""
    scripts["node"] = node_script

    # Shell script
    shell_script = """#!/bin/bash

# Simple system info script
echo "=== System Information ==="
echo "Hostname: $(hostname)"
echo "OS: $(uname -s)"
echo "Architecture: $(uname -m)"
echo "Uptime: $(uptime)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Disk Usage: $(df -h / | tail -1 | awk '{print $5}')"
echo "=== End ==="
"""
    scripts["shell"] = shell_script

    return scripts


def test_daemon_functionality():
    """Test the daemon functionality"""
    print("🧪 Testing MCLI Daemon Service")
    print("=" * 50)

    # Create test scripts
    scripts = create_test_scripts()

    # Create temporary directory for test scripts
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Write test scripts
        script_files = {}
        for lang, script in scripts.items():
            if lang == "python":
                filename = temp_path / "test_script.py"
            elif lang == "node":
                filename = temp_path / "test_script.js"
            elif lang == "shell":
                filename = temp_path / "test_script.sh"

            with open(filename, "w") as f:
                f.write(script)

            # Make shell script executable
            if lang == "shell":
                os.chmod(filename, 0o755)

            script_files[lang] = filename

        print("✅ Test scripts created")

        # Test daemon commands
        try:
            # Test daemon status
            print("\n📊 Testing daemon status...")
            result = subprocess.run(
                ["mcli", "workflow", "daemon", "status"], capture_output=True, text=True
            )
            print(f"Status: {result.stdout.strip()}")

            # Test adding commands
            print("\n➕ Testing command addition...")
            for lang, script_file in script_files.items():
                print(f"Adding {lang} command...")
                result = subprocess.run(
                    [
                        "mcli",
                        "workflow",
                        "daemon",
                        "client",
                        "add-file",
                        f"test-{lang}",
                        str(script_file),
                        "--description",
                        f"Test {lang} script",
                        "--language",
                        lang,
                        "--group",
                        "test",
                        "--tags",
                        f"test,{lang},demo",
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print(f"✅ {lang} command added successfully")
                else:
                    print(f"❌ Failed to add {lang} command: {result.stderr}")

            # Test listing commands
            print("\n📋 Testing command listing...")
            result = subprocess.run(
                ["mcli", "workflow", "daemon", "client", "list"], capture_output=True, text=True
            )
            print(result.stdout)

            # Test searching commands
            print("\n🔍 Testing command search...")
            result = subprocess.run(
                ["mcli", "workflow", "daemon", "client", "search", "test"],
                capture_output=True,
                text=True,
            )
            print(result.stdout)

            # Test command execution (if we can get command IDs)
            print("\n⚡ Testing command execution...")
            # Note: In a real scenario, you'd get the command ID from the add command output
            # For this test, we'll just show the command structure
            print("Command execution would be tested with:")
            print("mcli workflow daemon client execute <command-id> [args...]")

        except Exception as e:
            print(f"❌ Error during testing: {e}")

    print("\n✅ Daemon functionality test completed!")


def show_usage_examples():
    """Show usage examples"""
    print("\n📚 Usage Examples")
    print("=" * 50)

    examples = [
        {
            "title": "Start the daemon",
            "command": "mcli workflow daemon start",
            "description": "Start the background daemon service",
        },
        {
            "title": "Add a Python command",
            "command": "mcli workflow daemon client add-file my-script script.py --language python --group utils",
            "description": "Add a Python script as a command",
        },
        {
            "title": "Add command interactively",
            "command": "mcli workflow daemon client add-interactive",
            "description": "Interactive command creation with prompts",
        },
        {
            "title": "Search for commands",
            "command": "mcli workflow daemon client search 'data processing'",
            "description": "Search for commands by name, description, or tags",
        },
        {
            "title": "Execute a command",
            "command": "mcli workflow daemon client execute <command-id> arg1 arg2",
            "description": "Execute a stored command with arguments",
        },
        {
            "title": "List all commands",
            "command": "mcli workflow daemon client list",
            "description": "List all stored commands",
        },
        {
            "title": "Show command details",
            "command": "mcli workflow daemon client show <command-id>",
            "description": "Show detailed information about a command",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}")
        print(f"   Command: {example['command']}")
        print(f"   Description: {example['description']}")


def main():
    """Main test function"""
    print("🚀 MCLI Daemon Service Test Suite")
    print("=" * 60)

    # Check if mcli is available
    try:
        result = subprocess.run(["mcli", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ MCLI not found or not working properly")
            return
    except FileNotFoundError:
        print("❌ MCLI command not found in PATH")
        return

    print("✅ MCLI is available")

    # Show usage examples
    show_usage_examples()

    # Ask if user wants to run tests
    print("\n" + "=" * 60)
    response = input("Would you like to run the daemon functionality tests? (y/n): ")

    if response.lower() in ["y", "yes"]:
        test_daemon_functionality()
    else:
        print("Skipping tests. You can run them manually using the examples above.")

    print("\n🎉 Test suite completed!")
    print("\nFor more information, see: src/mcli/workflow/daemon/README.md")


if __name__ == "__main__":
    main()
