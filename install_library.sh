#!/bin/bash
# Install MCLI Library Script

set -e

echo "=== MCLI Library Installation ==="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the mcli project root directory"
    exit 1
fi

# Check if UV is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: UV package manager is not installed"
    echo "Please install UV first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "✅ UV found"

# Setup environment and build wheel
echo "📦 Setting up environment and building wheel..."
make setup
make wheel

# Check if wheel was built successfully
if [ ! -f "dist/mcli-"*.whl ]; then
    echo "❌ Error: Wheel file not found. Build failed."
    exit 1
fi

WHEEL_FILE=$(ls dist/mcli-*.whl | head -1)
echo "✅ Wheel built successfully: $WHEEL_FILE"

# Install the library
echo "📥 Installing mcli library..."
uv pip install "$WHEEL_FILE"

echo "✅ MCLI library installed successfully!"
echo ""
echo "You can now use mcli as a library in your Python scripts:"
echo ""
echo "Example usage:"
echo "  from mcli.lib.logger.logger import get_logger"
echo "  from mcli.lib.fs.fs import get_user_home"
echo "  from mcli.lib.config.config import get_config_directory"
echo ""
echo "Run the example:"
echo "  source .venv/bin/activate"
echo "  python example_library_usage.py"
echo ""
echo "For more information, see: LIBRARY_PACKAGING_GUIDE.md" 