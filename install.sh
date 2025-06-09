#!/bin/bash

set -euo pipefail

# wget 'https://raw.githubusercontent.com/mcli-e/rso-cbm/refs/heads/feature/lefv/mclili/resource/mclili-20250327-arm64.tar.gz?token=GHSAT0AAAAAAC46VAZX4GFI6H53NERKF5MUZ7FQERQ' -O mclili-20250327-arm64.tar.gz
# curl -L 'https://raw.githubusercontent.com/mcli-e/rso-cbm/refs/heads/feature/lefv/mclili/resource/mclili-20250327-arm64.tar.gz?token=GHSAT0AAAAAAC46VAZX4GFI6H53NERKF5MUZ7FQERQ' -o mclili-20250327-arm64.tar.gz
# curl -L 'https://mclie-my.sharepoint.com/:u:/g/personal/luis_fernandez-de-la-vara_mcli_ai/ERd3FZkx9-xIjHdz48rz7G4BXuVu2m3W7no_wuYGsu9Vvg?e=RlxBuQ' -o mclili-20250327-arm64.tar.gz
tar -xvf *.tar.gz

APP_NAME="mclili.app"
INSTALL_BIN_DIR="/usr/local/bin"
TARGET_BINARY="mclili"
APP_PATH="$(pwd)/$APP_NAME"
BINARY_PATH="$APP_PATH/Contents/MacOS/$TARGET_BINARY"
LINK_PATH="$INSTALL_BIN_DIR/$TARGET_BINARY"

# Check if the .app exists
if [[ ! -d "$APP_PATH" ]]; then
  echo "Error: $APP_NAME not found in current directory: $APP_PATH"
  exit 1
fi

# Ensure the target binary exists
if [[ ! -f "$BINARY_PATH" ]]; then
  echo "Error: Executable binary not found at: $BINARY_PATH"
  exit 2
fi

# Ensure /usr/local/bin exists and is writable
if [[ ! -d "$INSTALL_BIN_DIR" ]]; then
  echo "Creating $INSTALL_BIN_DIR ..."
  sudo mkdir -p "$INSTALL_BIN_DIR"
fi

if [[ ! -w "$INSTALL_BIN_DIR" ]]; then
  echo "Permission denied for $INSTALL_BIN_DIR. Using sudo to install."
  USE_SUDO=true
else
  USE_SUDO=false
fi

# Make sure the binary is executable
chmod +x "$BINARY_PATH"

# Create the symlink (or copy) in /usr/local/bin
if [[ -L "$LINK_PATH" || -f "$LINK_PATH" ]]; then
  echo "Removing existing binary at $LINK_PATH"
  $USE_SUDO && sudo rm -f "$LINK_PATH" || rm -f "$LINK_PATH"
fi

echo "Installing $TARGET_BINARY to $INSTALL_BIN_DIR"

if [[ "$USE_SUDO" == true ]]; then
  sudo ln -s "$BINARY_PATH" "$LINK_PATH"
else
  ln -s "$BINARY_PATH" "$LINK_PATH"
fi

echo "✅ Installed successfully! You can now run '$TARGET_BINARY' from anywhere."
