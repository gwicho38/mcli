#!/bin/bash
# build.sh - Updated for UV compatibility

set -e

# Ensure UV environment is active
uv venv --update
uv pip install -U nuitka

# Build with Nuitka
LDFLAGS="-L/opt/homebrew/opt/gettext/lib -lintl" python -m nuitka src/mcli/app/main.py --standalone --follow-imports --lto=no --macos-create-app-bundle --macos-signed-app-name="mclili" --plugin-enable=multiprocessing --output-dir=dist --macos-app-name="mclili" --output-filename="mclili"
