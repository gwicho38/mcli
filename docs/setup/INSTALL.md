# MCLI Installation Guide

Version 8.0.7 is now available through multiple installation methods!

## 🎉 What's New in 8.0.7

Bug fixes in this release:
- **Fixed async test configuration** - All async unit tests now pass correctly
- **Fixed store command test** - Resolved mocking issue in test_init_already_exists
- **100% test pass rate** - All 774 unit tests passing

For detailed release notes, see [8.0.7 Release Notes](../releases/8.0.7.md)

## 🚀 What's New in 8.0.x

The 8.0 series brings major improvements:
- **Simplified CLI structure** - Cleaner command hierarchy
- **IPFS sync** - Decentralized workflow sharing
- **Native script support** - Edit Python/shell scripts directly
- **Lockfile management** - Version control for workflows
- **Python venv support** - `@requires` metadata for dependencies

## Installation Methods

### 1. PyPI (Recommended)

```bash
# Using uv (fastest)
uv tool install mcli-framework --force

# Using pip
pip install --upgrade mcli-framework

# Using pipx
pipx install mcli-framework --force
```

### 2. Homebrew (macOS)

```bash
# Add the tap
brew tap gwicho38/mcli

# Install
brew install mcli

# Update
brew update && brew upgrade mcli

# Uninstall
brew uninstall mcli
brew untap gwicho38/mcli
```

### 3. From GitHub (Latest Development)

```bash
# Using uv
uv tool install --force git+https://github.com/gwicho38/mcli.git

# Using pip
pip install git+https://github.com/gwicho38/mcli.git
```

## Verify Installation

```bash
# Check version (installed via uv tool)
~/.local/share/uv/tools/mcli-framework/bin/python -c "from importlib.metadata import version; print(version('mcli-framework'))"

# Test model commands
mcli model --help
mcli model list

# Test new commands
mcli model pull --help
mcli model stop --help
mcli model delete --help
```

## Self-Update

If you installed via uv tool or pip, use:

```bash
mcli self update
```

## Troubleshooting

### Version Still Shows 7.0.3

PyPI may take a few minutes to propagate. Try:

```bash
# Force reinstall from PyPI
uv tool install mcli-framework --force --reinstall

# Or install from GitHub
uv tool install --force git+https://github.com/gwicho38/mcli.git
```

### Homebrew Installation Issues

If you encounter dependency issues:

```bash
# Update Homebrew
brew update

# Reinstall
brew reinstall mcli

# Check logs if install fails
brew install mcli --verbose --debug
```

### Commands Not Showing

Clear shell hash and reinstall:

```bash
hash -r
uv tool install mcli-framework --force --reinstall
```

## Links

- **GitHub**: https://github.com/gwicho38/mcli
- **PyPI**: https://pypi.org/project/mcli-framework/
- **Homebrew Tap**: https://github.com/gwicho38/homebrew-mcli
- **Issues**: https://github.com/gwicho38/mcli/issues

## Quick Reference

### Model Management Commands

```bash
mcli model list              # List available models
mcli model download <model>  # Download a model
mcli model start             # Start model server
mcli model stop              # Stop model server
mcli model pull <model>      # Pull (download) a model
mcli model delete <model>    # Delete a model
mcli model recommend         # Get model recommendation
mcli model status            # Check server status
```

### Workflow Commands

```bash
mcli workflow --help         # List all workflows
mcli workflow scheduler      # Schedule workflows
mcli workflow daemon         # Run as daemon
mcli commands list-custom    # List custom workflows
mcli commands import-script  # Import Python script as workflow
```

### Self Management Commands

```bash
mcli self update             # Update mcli
mcli self completion install # Install shell completion
mcli self version            # Show version
```

### Other Common Commands

```bash
mcli chat                # Start AI chat
mcli workflow            # Run workflows
mcli commands            # List all commands
mcli self update         # Update mcli
```

## Development

### Install for Development

```bash
cd /path/to/mcli
uv tool install --force --editable .
```

### Build and Publish

```bash
# Build wheel
make build

# Publish to PyPI (requires PYPI_TOKEN)
make publish

# Create new release
git tag v8.0.7
git push --tags
```
