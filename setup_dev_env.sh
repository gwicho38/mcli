#!/usr/bin/env bash
# setup_dev_env.sh - Comprehensive script to set up mcli development environment
# Optimized to only run necessary steps

# Colors for pretty output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"
CHECKMARK="✓"
CROSSMARK="✗"

# Function to check if a command exists
command_exists() {
  command -v "$1" &> /dev/null
}

# Welcome message
echo -e "${CYAN}==========================================${RESET}"
echo -e "${CYAN}mcli Development Environment Setup Script${RESET}"
echo -e "${CYAN}==========================================${RESET}"
echo ""
echo -e "This script will install all necessary tools for mcli development."
echo -e "Each step will be checked first to avoid unnecessary operations."
echo ""

# Step 1: Check and install Homebrew if needed
if ! command_exists brew; then
  echo -e "${YELLOW}Installing Homebrew package manager...${RESET}"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  
  # Add brew to path for the current session
  if [[ $(uname -m) == "arm64" ]]; then
    # For Apple Silicon Macs
    eval "$(/opt/homebrew/bin/brew shellenv)"
  else
    # For Intel Macs
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  
  echo -e "${GREEN}${CHECKMARK} Homebrew installed${RESET}"
else
  echo -e "${GREEN}${CHECKMARK} Homebrew already installed${RESET}"
fi

# Step 2: Update Homebrew if it hasn't been updated recently
# Check when Homebrew was last updated
BREW_LAST_UPDATE=$(stat -f %m $(brew --prefix)/Homebrew/.git/FETCH_HEAD 2>/dev/null || echo 0)
CURRENT_TIME=$(date +%s)
ONE_DAY=86400

if (( CURRENT_TIME - BREW_LAST_UPDATE > ONE_DAY )); then
  echo -e "${CYAN}Updating Homebrew (last updated > 24h ago)...${RESET}"
  brew update
  echo -e "${GREEN}${CHECKMARK} Homebrew updated${RESET}"
else
  echo -e "${GREEN}${CHECKMARK} Homebrew was recently updated (< 24h), skipping update${RESET}"
fi

# Step 3: Install required packages only if they don't exist
PACKAGES=(
  "make"
  "python@3.9"
  "coreutils"
  "uv"
  "pyenv"
  "git"
  "graphviz"
)

for pkg in "${PACKAGES[@]}"; do
  if brew list "$pkg" &>/dev/null; then
    echo -e "${GREEN}${CHECKMARK} $pkg already installed${RESET}"
  else
    echo -e "${YELLOW}Installing $pkg...${RESET}"
    brew install "$pkg"
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}${CHECKMARK} $pkg installed successfully${RESET}"
    else
      echo -e "${RED}${CROSSMARK} Failed to install $pkg${RESET}"
    fi
  fi
done

# Step 4: Add GNU tools to PATH if not already there
if ! grep -q "coreutils.*gnubin" ~/.zshrc; then
  echo -e "${CYAN}Adding GNU tools to PATH in ~/.zshrc...${RESET}"
  echo 'export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"' >> ~/.zshrc
  echo -e "${GREEN}${CHECKMARK} Added GNU tools to PATH${RESET}"
  echo -e "${YELLOW}Note: Run 'source ~/.zshrc' to update your current shell${RESET}"
else
  echo -e "${GREEN}${CHECKMARK} GNU tools already in PATH${RESET}"
fi

# Step 5: Setup Python 3.9 with pyenv if needed
if command_exists pyenv; then
  if ! pyenv versions | grep -q "3.9"; then
    echo -e "${YELLOW}Installing Python 3.9 with pyenv...${RESET}"
    pyenv install 3.9 -s  # -s for skip if already installed
    echo -e "${GREEN}${CHECKMARK} Python 3.9 installed via pyenv${RESET}"
  else
    echo -e "${GREEN}${CHECKMARK} Python 3.9 already available via pyenv${RESET}"
  fi
fi

# Step 6: Setup project with UV only if needed
cd "$(dirname "$0")"  # Make sure we're in the project root

# Check if we already have a valid virtual environment
if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
  # Check if key dependencies are installed
  if .venv/bin/python -c "import mcli" &>/dev/null; then
    echo -e "${GREEN}${CHECKMARK} Virtual environment already set up with project dependencies${RESET}"
  else
    echo -e "${YELLOW}Virtual environment exists but project not installed. Setting up project...${RESET}"
    make setup
    echo -e "${GREEN}${CHECKMARK} Project dependencies installed${RESET}"
  fi
else
  echo -e "${YELLOW}Setting up project virtual environment and dependencies...${RESET}"
  make clean-all setup
  echo -e "${GREEN}${CHECKMARK} Project environment created and dependencies installed${RESET}"
fi

# Step 7: Check for timeout command and add to PATH for current session if needed
if ! command_exists timeout; then
  echo -e "${YELLOW}Adding GNU coreutils to current PATH temporarily...${RESET}"
  export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
  
  if command_exists timeout; then
    echo -e "${GREEN}${CHECKMARK} The 'timeout' command is now available in this session${RESET}"
    echo -e "${YELLOW}Remember to run 'source ~/.zshrc' in new terminals${RESET}"
  else
    echo -e "${RED}${CROSSMARK} The 'timeout' command is still not available. Check coreutils installation.${RESET}"
  fi
else
  echo -e "${GREEN}${CHECKMARK} The 'timeout' command is available${RESET}"
fi

# Final message
echo ""
echo -e "${CYAN}==========================================${RESET}"
echo -e "${GREEN}Development environment setup complete!${RESET}"
echo -e "${CYAN}==========================================${RESET}"
echo ""
echo -e "To activate the virtual environment, run:"
echo -e "${YELLOW}source .venv/bin/activate${RESET}"
echo ""
echo -e "To run the full test suite:"
echo -e "${YELLOW}./test_makefile_full.sh${RESET}"
echo ""
echo -e "To build the project:"
echo -e "${YELLOW}make darwin${RESET}"
echo ""
echo -e "${CYAN}App Signing Notes:${RESET}"
echo -e "The Makefile has been updated to use minimal code signing (--macos-sign-identity=- for Nuitka"
echo -e "and --codesign-identity=- for PyInstaller) which fixes the 'invalid signature' errors."
echo -e "This allows the app to be built successfully even with markdown and other non-code files."
echo -e "If you need properly signed apps for distribution, replace the '-' with a valid"
echo -e "signing identity in the Makefile."
echo ""
echo -e "Happy coding! 🚀"