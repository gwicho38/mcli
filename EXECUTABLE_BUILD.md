# Building Executables from Wheel Output

This guide explains how to create standalone executables from the mcli wheel package using PyInstaller.

## Overview

The mcli project now supports creating portable executables from the wheel output. This allows you to:

1. Build a Python wheel package
2. Create a standalone executable that includes all dependencies
3. Distribute the executable without requiring Python installation

## Prerequisites

- Python 3.9 or higher
- UV package manager
- PyInstaller (automatically installed via Makefile)

## Quick Start

### 1. Build the Wheel

```bash
# Clean any previous builds
make clean

# Setup the environment and build wheel
make setup
make wheel
```

### 2. Create Executable

```bash
# Build portable executable (single file)
make portable

# Or build binary executable (directory format)
make binary
```

### 3. Test the Executable

```bash
# Test the built executable
make test-binary
```

### 4. Install System-Wide (Optional)

```bash
# Install portable executable to system
make install-portable
```

## Available Makefile Targets

### Core Build Targets

- `make wheel` - Build Python wheel package
- `make portable` - Build portable executable (onefile)
- `make binary` - Build binary executable (onedir)
- `make test-binary` - Test the built executable

### Installation Targets

- `make install-portable` - Install portable executable to system
- `make install-binary` - Install binary executable to system

### Utility Targets

- `make clean` - Clean all build artifacts
- `make setup` - Setup UV environment
- `make debug` - Show debug information

## Executable Types

### Portable Executable (Recommended)

- **Format**: Single file
- **Target**: `make portable`
- **Output**: `bin/mcli`
- **Advantages**: 
  - Easy to distribute
  - Self-contained
  - No additional files needed

### Binary Executable

- **Format**: Directory with executable + dependencies
- **Target**: `make binary`
- **Output**: `bin/mcli/mcli`
- **Advantages**:
  - Faster startup
  - Easier to debug
  - Smaller individual file size

## File Structure

After building, you'll find:

```
mcli/
├── dist/                    # Wheel files
│   └── mcli-*.whl
├── bin/                     # Executables
│   └── mcli                # Portable executable
├── build/                   # PyInstaller build files
└── mcli.spec               # PyInstaller spec file
```

## Testing

### Test the Executable

```bash
# Test basic functionality
make test-binary

# Manual testing
./bin/mcli --help
./bin/mcli --version
```

### Test Installation

```bash
# Install to system
make install-portable

# Test system installation
mcli --help
```

## Troubleshooting

### Common Issues

1. **PyInstaller not found**
   ```bash
   make install-pyinstaller
   ```

2. **Missing dependencies**
   ```bash
   make clean
   make setup
   make portable
   ```

3. **Permission denied**
   ```bash
   chmod +x bin/mcli
   ```

4. **Executable too large**
   - Use `make binary` instead of `make portable`
   - Check for unnecessary imports in the spec file

### Debug Information

```bash
# Show debug information
make debug

# Check PyInstaller spec file
cat mcli.spec
```

## Advanced Configuration

### Custom PyInstaller Options

Edit the `mcli.spec` file to customize:

- Hidden imports
- Data files
- Excluded modules
- Icon files
- Code signing

### Platform-Specific Builds

The build system automatically detects your platform:

- **macOS**: ARM64 or x86_64
- **Linux**: x86_64
- **Windows**: AMD64

### Cross-Platform Building

For cross-platform builds, use Docker or virtual machines with the target platform.

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Build Executable
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env
      - run: make setup
      - run: make wheel
      - run: make portable
      - run: make test-binary
      - uses: actions/upload-artifact@v3
        with:
          name: mcli-executable
          path: bin/mcli
```

## Performance Considerations

### Executable Size

- **Portable**: ~50-100MB (includes Python runtime)
- **Binary**: ~20-50MB (shared runtime)

### Startup Time

- **Portable**: Slower startup (extracts to temp directory)
- **Binary**: Faster startup (direct execution)

### Memory Usage

Both formats use similar memory usage during execution.

## Security Considerations

### Code Signing (macOS)

```bash
# Sign the executable
codesign --force --deep --sign "Developer ID Application: Your Name" bin/mcli
```

### Verification

```bash
# Verify signature
codesign -dv bin/mcli
```

## Distribution

### Portable Distribution

1. Build the executable: `make portable`
2. Distribute `bin/mcli` file
3. Users can run directly: `./mcli`

### System Installation

1. Build: `make portable`
2. Install: `make install-portable`
3. Users can run: `mcli`

### Package Managers

Consider creating platform-specific packages:

- **macOS**: Homebrew formula
- **Linux**: DEB/RPM packages
- **Windows**: MSI installer

## Examples

### Complete Build Process

```bash
# Full build and test
make clean
make setup
make wheel
make portable
make test-binary
make install-portable
```

### Development Workflow

```bash
# Quick test build
make clean && make portable && make test-binary
```

### Production Build

```bash
# Clean production build
make clean
make setup
make wheel
make portable
# Test thoroughly before distribution
make test-binary
```

## Support

For issues with executable builds:

1. Check the debug output: `make debug`
2. Review PyInstaller logs in `build/` directory
3. Test with a minimal example first
4. Check PyInstaller documentation for advanced options

## Related Documentation

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [Makefile Targets](Makefile#available-targets) 