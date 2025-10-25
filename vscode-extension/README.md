# MCLI Workflow Notebooks - VSCode Extension

Visual notebook editor for MCLI workflow JSON files using VSCode's native notebook interface.

## Features

- **Visual Cell-Based Editing**: Edit workflow JSON files with Jupyter-like cell interface
- **Cell Execution**: Run Python and Shell code cells directly in VSCode
- **Native Notebook UI**: Uses VSCode's built-in notebook interface (same as Jupyter extension)
- **JSON Format**: Files remain as `.json` with full Jupyter nbformat 4 compatibility
- **Syntax Highlighting**: Code and markdown cells with proper syntax highlighting
- **Output Rendering**: View execution results inline

## Installation

### From VSIX (Recommended)

1. Download the latest `.vsix` file from releases
2. In VSCode: `Cmd+Shift+P` → "Extensions: Install from VSIX..."
3. Select the downloaded `.vsix` file

### From Source

```bash
cd vscode-extension
npm install
npm run compile
vsce package
code --install-extension mcli-workflow-notebooks-1.0.0.vsix
```

## Usage

### Opening Workflow Notebooks

**Option 1: Right-click**
- Right-click any `.json` workflow file
- Select "Open With..."
- Choose "MCLI Workflow Notebook"

**Option 2: Command Palette**
- Open a `.json` workflow file
- `Cmd+Shift+P` → "MCLI: Open as MCLI Notebook"

**Option 3: Set as default**
- Right-click → "Open With..." → "Configure default editor for '*.json'"
- Select "MCLI Workflow Notebook"

### Editing Cells

- **Add Cell**: Click `+` button in toolbar or use keyboard shortcut
- **Edit Cell**: Click into cell and start typing
- **Run Cell**: Click ▶ button or press `Shift+Enter`
- **Delete Cell**: Click ... menu → "Delete Cell"
- **Move Cell**: Use up/down arrows in cell toolbar

### Cell Types

- **Code Cells**: Python, Shell, Bash, Zsh, Fish
- **Markdown Cells**: Documentation with GitHub Flavored Markdown

### Keyboard Shortcuts

- `Shift+Enter`: Run current cell and move to next
- `Cmd+Enter`: Run current cell
- `Esc`: Exit edit mode
- `Enter`: Enter edit mode
- `A`: Add cell above (in command mode)
- `B`: Add cell below (in command mode)
- `DD`: Delete cell (in command mode)

## File Format

Files are standard Jupyter notebooks (nbformat 4) with `.json` extension:

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "mcli": {
      "name": "workflow-name",
      "description": "Workflow description",
      "language": "python"
    }
  },
  "cells": [
    {
      "cell_type": "code",
      "source": ["print('hello')"],
      "metadata": {"language": "python"}
    }
  ]
}
```

## Requirements

- VSCode 1.85.0 or higher
- Python 3 (for Python cell execution)
- Bash/Zsh/Fish (for shell cell execution)

## Extension Settings

This extension contributes the following settings:

- `mcli.notebooks.autoSave`: Automatically save notebook changes (default: `true`)
- `mcli.notebooks.theme`: Editor theme (`light`, `dark`, `auto`)

## Known Limitations

- Cell execution runs locally (not via MCLI daemon yet)
- No variable sharing between cells currently
- Output is captured but not interactive

## Future Enhancements

- Integration with MCLI workflow execution
- Variable inspector
- Debugger support
- Interactive outputs
- Collaboration features

## Support

- [GitHub Issues](https://github.com/gwicho38/mcli/issues)
- [Documentation](https://github.com/gwicho38/mcli/blob/main/docs/workflow-notebooks.md)

## License

MIT
