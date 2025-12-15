#!/usr/bin/env bash
# @description: Example shell workflow command
# @version: 1.0.0
# @group: examples
# @author: MCLI Team
# @tags: example, demo, shell, bash
# @shell: bash

# Example shell workflow command for mcli.
#
# This demonstrates how to create a shell-based mcli command.
# The script will be automatically discovered and available as:
#     mcli run example_shell
#
# Arguments are passed as positional parameters: $1, $2, $3, etc.
# The command name is available in: $MCLI_COMMAND

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Default values
NAME="${1:-World}"
GREETING="${2:-Hello}"
VERBOSE="${VERBOSE:-false}"

# Helper function for verbose logging
log_debug() {
    if [ "$VERBOSE" = "true" ]; then
        echo "[DEBUG] $*" >&2
    fi
}

# Main logic
main() {
    log_debug "name=$NAME, greeting=$GREETING"
    log_debug "MCLI_COMMAND=$MCLI_COMMAND"

    local message="${GREETING}, ${NAME}!"
    echo "$message"

    log_debug "Message length: ${#message}"
}

# Show usage if help requested
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: mcli run example_shell [NAME] [GREETING]"
    echo ""
    echo "An example shell workflow command."
    echo ""
    echo "Arguments:"
    echo "  NAME      Name to greet (default: World)"
    echo "  GREETING  Greeting to use (default: Hello)"
    echo ""
    echo "Environment:"
    echo "  VERBOSE=true  Enable debug output"
    exit 0
fi

# Run main
main

exit 0
