#!/bin/bash
# Quick setup script for GitHub Actions self-hosted runner
# Run this on your server: lefvpc@192.168.8.239

set -e

echo "🚀 Setting up GitHub Actions Self-Hosted Runner"
echo "================================================"
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux*)
        if [ "$ARCH" = "x86_64" ]; then
            RUNNER_FILE="actions-runner-linux-x64-2.321.0.tar.gz"
            RUNNER_URL="https://github.com/actions/runner/releases/download/v2.321.0/$RUNNER_FILE"
        elif [ "$ARCH" = "aarch64" ]; then
            RUNNER_FILE="actions-runner-linux-arm64-2.321.0.tar.gz"
            RUNNER_URL="https://github.com/actions/runner/releases/download/v2.321.0/$RUNNER_FILE"
        fi
        ;;
    Darwin*)
        if [ "$ARCH" = "arm64" ]; then
            RUNNER_FILE="actions-runner-osx-arm64-2.321.0.tar.gz"
            RUNNER_URL="https://github.com/actions/runner/releases/download/v2.321.0/$RUNNER_FILE"
        else
            RUNNER_FILE="actions-runner-osx-x64-2.321.0.tar.gz"
            RUNNER_URL="https://github.com/actions/runner/releases/download/v2.321.0/$RUNNER_FILE"
        fi
        ;;
    *)
        echo "❌ Unsupported OS: $OS"
        exit 1
        ;;
esac

echo "Detected: $OS $ARCH"
echo "Using: $RUNNER_FILE"
echo ""

# Create directory
RUNNER_DIR="$HOME/actions-runner"
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

# Download if not exists
if [ ! -f "$RUNNER_FILE" ]; then
    echo "📥 Downloading GitHub Actions Runner..."
    curl -o "$RUNNER_FILE" -L "$RUNNER_URL"
else
    echo "✓ Runner already downloaded"
fi

# Extract
echo "📦 Extracting runner..."
tar xzf "./$RUNNER_FILE"

echo ""
echo "✅ GitHub Actions Runner installed successfully!"
echo ""
echo "================================================"
echo "NEXT STEPS:"
echo "================================================"
echo ""
echo "1️⃣  Get registration token (run on your LOCAL machine):"
echo "   gh api repos/gwicho38/mcli/actions/runners/registration-token --jq .token"
echo ""
echo "2️⃣  Configure the runner (run on THIS server):"
echo "   cd $RUNNER_DIR"
echo "   ./config.sh --url https://github.com/gwicho38/mcli \\"
echo "     --token <PASTE_TOKEN_HERE> \\"
echo "     --name lefvpc-runner \\"
echo "     --labels self-hosted,linux,x64 \\"
echo "     --work _work"
echo ""
echo "3️⃣  Install as service (run on THIS server):"
echo "   cd $RUNNER_DIR"
echo "   sudo ./svc.sh install"
echo "   sudo ./svc.sh start"
echo "   sudo ./svc.sh status"
echo ""
echo "4️⃣  Install dependencies:"
echo "   # UV package manager"
echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
echo ""
echo "   # Python versions (via pyenv)"
echo "   curl https://pyenv.run | bash"
echo "   pyenv install 3.9.18 3.10.13 3.11.7 3.12.1"
echo ""
echo "5️⃣  Test the runner:"
echo "   gh workflow run publish-self-hosted.yml -f publish_target=test-pypi"
echo ""
echo "📖 Full documentation: .github/SELF_HOSTED_RUNNER_SETUP.md"
echo ""
