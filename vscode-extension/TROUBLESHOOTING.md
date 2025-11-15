# Troubleshooting Guide

This guide helps you solve common issues with the MCLI Framework VSCode extension.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Extension Not Working](#extension-not-working)
- [File Opening Issues](#file-opening-issues)
- [Cell Execution Issues](#cell-execution-issues)
- [Performance Issues](#performance-issues)
- [Known Limitations](#known-limitations)

---

## Installation Issues

### Extension Not Showing in Marketplace

**Problem**: Can't find "MCLI Framework" in the VSCode marketplace.

**Solutions**:
1. Make sure you're using VSCode version 1.85.0 or higher
2. Try searching for "mcli" or "workflow notebook"
3. Check if you're looking at the correct marketplace (VSCode, not Visual Studio)

**Alternative**: Install from VSIX file:
```bash
code --install-extension mcli-framework-1.0.0.vsix
```

### Installation Fails

**Problem**: Extension installation fails with an error.

**Solutions**:
1. Check your internet connection
2. Restart VSCode
3. Clear VSCode cache:
   - Close VSCode
   - Delete `~/.vscode/extensions/.obsolete` (macOS/Linux) or `%USERPROFILE%\.vscode\extensions\.obsolete` (Windows)
   - Restart VSCode and try again

---

## Extension Not Working

### Extension Not Activating

**Problem**: Extension is installed but doesn't activate.

**Check**:
1. Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
2. Type "MCLI"
3. If no MCLI commands appear, the extension isn't active

**Solutions**:
1. Check VSCode version: `Help → About`
   - Must be 1.85.0 or higher
2. Check extension status:
   - Open Extensions panel (`Cmd+Shift+X`)
   - Find "MCLI Framework"
   - If disabled, click "Enable"
3. Check for extension errors:
   - `Help → Toggle Developer Tools`
   - Look for errors in the Console
4. Reinstall the extension:
   ```bash
   code --uninstall-extension gwicho38.mcli-framework
   code --install-extension gwicho38.mcli-framework
   ```

### Commands Not Registered

**Problem**: MCLI commands don't appear in Command Palette.

**Solutions**:
1. Reload VSCode window:
   - Command Palette → "Developer: Reload Window"
2. Check that extension is enabled and activated
3. Check Developer Tools console for errors

---

## File Opening Issues

### "This JSON file is not a valid notebook format" Error

**Problem**: Getting this error when trying to open a JSON file.

**Explanation**: This extension only works with Jupyter notebook format (nbformat 4), not regular JSON or MCLI command definition files.

**Valid notebook format requires**:
```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "cells": [ /* array of cells */ ]
}
```

**Solutions**:

1. **For new workflows**: Create a proper notebook file:
   ```json
   {
     "nbformat": 4,
     "nbformat_minor": 5,
     "metadata": {
       "mcli": {
         "name": "my-workflow",
         "description": "My workflow description"
       }
     },
     "cells": [
       {
         "cell_type": "code",
         "source": ["print('hello')"],
         "metadata": {"language": "python"},
         "execution_count": null,
         "outputs": []
       }
     ]
   }
   ```

2. **For existing MCLI commands**: This extension is not for command definition files. Use:
   - Regular text editor for `.json` command definitions
   - `mcli workflow` commands for command management
   - Create new workflow notebooks in `~/.mcli/workflows/` directory

3. **Use example files**: Copy from `examples/` directory:
   ```bash
   cp examples/hello-world.json ~/.mcli/workflows/my-workflow.json
   ```

### Can't Open JSON as Notebook

**Problem**: Right-click → "Open With..." doesn't show MCLI Notebook option.

**Solutions**:
1. Make sure the file matches the pattern:
   - `**/commands/*.json`
   - `**/*workflow*.json`
   - `**/notebooks/*.json`
2. Try renaming: `my-file.json` → `my-workflow.json`
3. Manual trigger:
   - Open the JSON file in text editor
   - Command Palette → "MCLI: Open as MCLI Notebook"

### File Opens in Regular Text Editor

**Problem**: JSON file opens in text editor instead of notebook view.

**Solutions**:
1. Right-click the file → "Open With..." → "MCLI Workflow Notebook"
2. Set as default editor:
   - Right-click → "Open With..."
   - "Configure default editor for '*.json'"
   - Select "MCLI Workflow Notebook"
3. Or use selective naming (e.g., `myfile-workflow.json`) to match the pattern

---

## Cell Execution Issues

### Python Cells Not Running

**Problem**: Clicking "Run" on Python cells does nothing or shows errors.

**Check Python installation**:
```bash
python3 --version
```

**Solutions**:
1. Install Python 3:
   - macOS: `brew install python3`
   - Ubuntu: `sudo apt install python3`
   - Windows: Download from python.org
2. Make sure `python3` is in PATH
3. Try running in terminal first:
   ```bash
   python3 -c "print('hello')"
   ```

### Shell Cells Not Running

**Problem**: Shell/Bash cells don't execute.

**Solutions**:
1. Check shell availability:
   ```bash
   which bash  # or zsh, fish
   ```
2. Set correct language in cell metadata
3. Try simple command first: `echo "test"`

### Cell Execution Timeout

**Problem**: "Execution timeout" error after 30 seconds.

**Solutions**:
1. Break long-running code into smaller cells
2. Optimize your code
3. For truly long tasks, consider:
   - Running directly in terminal
   - Using MCLI daemon mode
   - Background execution patterns

### Permission Denied Errors

**Problem**: "Permission denied" when executing cells.

**Solutions**:
1. Check file permissions
2. Don't run commands that require sudo
3. Ensure Python/shell are executable:
   ```bash
   which python3
   ls -l $(which python3)
   ```

### "Command Injection" Security Error

**Problem**: Cell execution blocked for security.

**Explanation**: The extension uses secure temporary files to prevent command injection.

**If you see this**:
1. This is a bug - please report it
2. Check if your code contains unusual characters
3. Try simplifying the code

---

## Performance Issues

### Slow Extension Loading

**Problem**: Extension takes long to activate.

**Solutions**:
1. Check VSCode extensions - disable unused ones
2. Check system resources (CPU, memory)
3. Clear VSCode cache:
   ```bash
   rm -rf ~/.vscode/extensions/.obsolete
   ```

### Notebook Rendering Slow

**Problem**: Large notebooks are slow to open/edit.

**Solutions**:
1. Split large notebooks into smaller ones
2. Remove old outputs before saving:
   - Edit JSON manually to clear `outputs` arrays
3. Limit number of cells (recommend < 50 per notebook)

### High Memory Usage

**Problem**: VSCode using too much memory.

**Solutions**:
1. Close unused notebooks
2. Restart VSCode periodically
3. Clear cell outputs when not needed
4. Limit output size in cells

---

## Known Limitations

### Current Limitations

1. **Execution Environment**
   - Cells execute locally via child_process
   - No shared state between cells (each cell runs independently)
   - 30-second timeout per cell
   - 10MB output buffer limit

2. **File Format**
   - Only works with Jupyter nbformat 4
   - JSON files must have `cells` array
   - Not compatible with regular MCLI command definitions

3. **Features Not Yet Implemented**
   - Variable inspector
   - Debugger integration
   - MCLI daemon execution
   - Interactive widgets
   - Real-time collaboration

4. **Language Support**
   - Python 3 only (not Python 2)
   - Shell languages: bash, zsh, fish
   - Other languages: not yet supported

### Workarounds

**For shared state between cells**:
- Save data to files and load in next cell
- Use environment variables
- Combine cells into one

**For long-running tasks**:
- Use MCLI CLI directly: `mcli workflow run my-workflow`
- Use MCLI daemon mode
- Run in separate terminal

**For large outputs**:
- Redirect to file: `python script.py > output.txt`
- Limit output in code: `print(data[:100])`

---

## Getting Help

### Before Reporting Issues

1. Check this troubleshooting guide
2. Check the [FAQ](README.md#-faq)
3. Search existing issues: https://github.com/gwicho38/mcli/issues

### Reporting Bugs

Include in your report:
1. **VSCode version**: `Help → About`
2. **Extension version**: Check Extensions panel
3. **OS**: macOS/Linux/Windows + version
4. **Python version**: `python3 --version`
5. **Error messages**: From Developer Tools Console
6. **Steps to reproduce**: What you did before the error
7. **Sample file**: Minimal example that shows the issue

### Where to Get Help

- 🐛 **Bug Reports**: https://github.com/gwicho38/mcli/issues
- 💡 **Feature Requests**: https://github.com/gwicho38/mcli/issues/new
- 📖 **Documentation**: https://github.com/gwicho38/mcli/blob/main/README.md
- 💬 **Discussions**: https://github.com/gwicho38/mcli/discussions

---

## Additional Resources

- [Installation Guide](INSTALL.md)
- [README](README.md)
- [Examples Directory](examples/)
- [MCLI Framework Documentation](https://github.com/gwicho38/mcli)

---

**Last Updated**: November 2024
**Extension Version**: 1.0.0
