#!/bin/bash

# Webapp command wrapper
# This script provides a convenient way to run webapp commands

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

# Function to show usage
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  generate --url <URL> --name <NAME> [--icon <ICON>] [--output-dir <DIR>] [--install]"
    echo "    Generate a new web application from template"
    echo ""
    echo "  install <app-dir>"
    echo "    Install a generated web application"
    echo ""
    echo "  run <app-dir>"
    echo "    Run a generated web application in development mode"
    echo ""
    echo "  list [--verbose]"
    echo "    List all generated web applications"
    echo ""
    echo "  delete <app-name> [--force]"
    echo "    Delete a generated web application"
    echo ""
    echo "Examples:"
    echo "  $0 generate --url https://app.example.com --name 'My App' --install"
    echo "  $0 install ~/.local/mcli/webapps/my_app"
    echo "  $0 run ~/.local/mcli/webapps/my_app"
    echo "  $0 list --verbose"
    echo "  $0 delete my_app --force"
}

# Check if command is provided
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# Run the Python command
cd "$PROJECT_ROOT"
python -m src.mcli.workflow.webapp.webapp "$@" 