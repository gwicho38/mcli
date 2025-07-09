#!/bin/bash

# MCLI Daemon Service Installation Script
# This script sets up the daemon service and its dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python package
python_package_exists() {
    python3 -c "import $1" >/dev/null 2>&1
}

# Function to install Python package
install_python_package() {
    local package=$1
    if ! python_package_exists "$package"; then
        print_status "Installing Python package: $package"
        pip3 install "$package"
        print_success "Installed $package"
    else
        print_status "$package is already installed"
    fi
}

# Function to check and install system dependencies
check_system_dependencies() {
    print_status "Checking system dependencies..."
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"
    
    # Check Node.js (optional)
    if command_exists node; then
        print_success "Node.js found: $(node --version)"
    else
        print_warning "Node.js not found. Node.js commands will not work."
        print_warning "Install Node.js from https://nodejs.org/"
    fi
    
    # Check Lua (optional)
    if command_exists lua; then
        print_success "Lua found: $(lua -v)"
    else
        print_warning "Lua not found. Lua commands will not work."
        print_warning "Install Lua from your package manager"
    fi
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Core dependencies
    install_python_package "click"
    install_python_package "psutil"
    install_python_package "numpy"
    install_python_package "scikit-learn"
    
    print_success "Python dependencies installed"
}

# Function to create daemon directories
create_daemon_directories() {
    print_status "Creating daemon directories..."
    
    local daemon_dir="$HOME/.local/mcli/daemon"
    mkdir -p "$daemon_dir"
    
    print_success "Created daemon directory: $daemon_dir"
}

# Function to test daemon functionality
test_daemon() {
    print_status "Testing daemon functionality..."
    
    # Test if mcli is available
    if ! command_exists mcli; then
        print_warning "MCLI not found in PATH. Make sure it's installed and available."
        return
    fi
    
    # Test daemon status
    if mcli workflow daemon status >/dev/null 2>&1; then
        print_success "Daemon commands are working"
    else
        print_warning "Daemon commands may not be working properly"
    fi
}

# Function to show usage examples
show_usage_examples() {
    echo
    echo "🎉 Installation completed!"
    echo
    echo "Quick Start Guide:"
    echo "=================="
    echo
    echo "1. Start the daemon:"
    echo "   mcli workflow daemon start"
    echo
    echo "2. Add your first command:"
    echo "   mcli workflow daemon client add-interactive"
    echo
    echo "3. List commands:"
    echo "   mcli workflow daemon client list"
    echo
    echo "4. Search commands:"
    echo "   mcli workflow daemon client search 'your query'"
    echo
    echo "5. Execute a command:"
    echo "   mcli workflow daemon client execute <command-id>"
    echo
    echo "For more information, see: src/mcli/workflow/daemon/README.md"
    echo
}

# Main installation function
main() {
    echo "🚀 MCLI Daemon Service Installation"
    echo "=================================="
    echo
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        exit 1
    fi
    
    # Check system dependencies
    check_system_dependencies
    
    # Install Python dependencies
    install_python_dependencies
    
    # Create daemon directories
    create_daemon_directories
    
    # Test daemon functionality
    test_daemon
    
    # Show usage examples
    show_usage_examples
}

# Run main function
main "$@" 