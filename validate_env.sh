#!/usr/bin/env bash
# validate_env.sh - Validates the UV development environment and Makefile commands

# Exit on any error
set -e

# Colors for pretty output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"

# Helper functions
log_step() {
  echo -e "${CYAN}==>${RESET} $1"
}

log_success() {
  echo -e "${GREEN}✓ $1${RESET}"
}

log_warning() {
  echo -e "${YELLOW}⚠ $1${RESET}"
}

log_error() {
  echo -e "${RED}✗ $1${RESET}"
}

run_command() {
  log_step "Running: $1"
  if eval "$1"; then
    log_success "Command succeeded"
    return 0
  else
    log_error "Command failed with exit code $?"
    return 1
  fi
}

validate_command() {
  command -v "$1" >/dev/null 2>&1 || { log_error "$1 is required but not installed"; return 1; }
  log_success "$1 is installed: $(command -v "$1")"
}

# Title
echo -e "${CYAN}========================================${RESET}"
echo -e "${CYAN}  MCLI Development Environment Validator${RESET}"
echo -e "${CYAN}========================================${RESET}"
echo ""

# 1. Validate required tools
log_step "Validating required tools"
validate_command "uv" || exit 1
validate_command "python" || exit 1
validate_command "make" || exit 1

# 2. Check Python version
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
MIN_PYTHON="3.9"
log_step "Checking Python version (need $MIN_PYTHON+)"
if [ "$(printf '%s\n' "$MIN_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$MIN_PYTHON" ]; then
  log_error "Python $PYTHON_VERSION detected, but mcli requires Python $MIN_PYTHON+"
  exit 1
else
  log_success "Python $PYTHON_VERSION (meets requirement)"
fi

# 3. Set up or update UV environment
log_step "Setting up UV environment"
if [ ! -d ".venv" ]; then
  run_command "uv venv" || exit 1
  log_success "Created new UV virtual environment"
else
  log_success "Using existing virtual environment"
fi

# 4. Activate virtual environment
log_step "Activating virtual environment"
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
  log_success "Virtual environment activated"
else
  log_error "Could not find .venv/bin/activate"
  exit 1
fi

# 5. Install dependencies
log_step "Installing development dependencies"
run_command "uv pip install -e ." || exit 1
run_command "uv pip install -U setuptools wheel twine build" || exit 1

# 6. Test Makefile targets
echo ""
log_step "Testing Makefile targets"

# 6.1 Check clean target
run_command "make clean" || { log_error "make clean failed"; exit 1; }

# 6.2 Check setup target
run_command "make setup" || { log_error "make setup failed"; exit 1; }

# 6.3 Try building wheel
log_step "Testing wheel build (this may take a minute)"
if run_command "make darwin"; then
  log_success "Wheel build successful"
else
  log_error "Wheel build failed"
  exit 1
fi

# 7. Create .envrc backup preserving sensitive data and add new content
log_step "Setting up direnv configuration"
if [ -f ".envrc" ]; then
  cp .envrc .envrc.bak
  log_success "Created backup of existing .envrc at .envrc.bak"
fi

cat > .envrc << 'EOF'
#!/usr/bin/env bash
# .envrc - direnv configuration for mcli development with UV

# Exit on error
set -e

echo "🔧 Setting up mcli development environment..."

# Create or update UV virtual environment
if [ ! -d ".venv" ]; then
  echo "📦 Creating new UV virtual environment..."
  uv venv
else
  echo "📦 Using existing virtual environment..."
fi

# Add .venv/bin to PATH
PATH_add .venv/bin

# Install development dependencies if needed
if [ ! -f ".venv/.initialized" ]; then
  echo "📥 Installing dependencies..."
  uv pip install -e .
  uv pip install -U setuptools wheel twine build
  touch .venv/.initialized
fi

# Export environment variables needed for build
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
export UV_NATIVE_TLS=1
export MCLI_DEV=1

# Validate Python version is compatible
python_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
min_python="3.9"

if [ "$(printf '%s\n' "$min_python" "$python_version" | sort -V | head -n1)" != "$min_python" ]; then
  echo "❌ Error: Python $python_version detected, but mcli requires Python $min_python+"
  echo "💡 Consider using pyenv or asdf to install a compatible Python version"
  return 1
fi

# Print environment info
echo "✅ Development environment initialized:"
echo "   • Python: $(python --version)"
echo "   • UV: $(uv --version)"
echo "   • Virtual env: $(pwd)/.venv"
echo "   • Run 'make help' to see available build commands"

# Load any extra local configuration if it exists (not tracked in git)
[ -f .envrc.local ] && source_env .envrc.local
EOF

# Restore any environment variables from backup
if [ -f ".envrc.bak" ]; then
  grep "^export " .envrc.bak >> .envrc
  log_success "Restored environment variables from backup"
fi

# Add trailing message to .envrc
echo 'echo "🚀 Ready to develop!"' >> .envrc

chmod +x .envrc
log_success "Created .envrc file"

# 8. Final status
echo ""
echo -e "${GREEN}========================================${RESET}"
echo -e "${GREEN}  Environment setup and validation complete${RESET}"
echo -e "${GREEN}========================================${RESET}"
echo ""
echo -e "To use this environment:"
echo -e "1. Install direnv if not already installed:"
echo -e "   ${CYAN}brew install direnv${RESET} (macOS) or ${CYAN}apt install direnv${RESET} (Linux)"
echo -e "2. Add direnv hook to your shell (.bashrc, .zshrc, etc.):"
echo -e "   ${CYAN}eval \"\$(direnv hook bash)\"${RESET} or ${CYAN}eval \"\$(direnv hook zsh)\"${RESET}"
echo -e "3. Allow direnv to load the environment:"
echo -e "   ${CYAN}direnv allow${RESET}"
echo -e "4. Enter the directory again to trigger direnv"
echo ""
echo -e "Run ${CYAN}make help${RESET} to see all available build commands"