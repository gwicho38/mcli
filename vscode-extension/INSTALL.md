# Installing the MCLI Workflow Notebooks Extension

## Quick Install

### Option 1: Install from VSIX (Recommended)

```bash
cd /Users/lefv/repos/mcli/vscode-extension
code --install-extension mcli-workflow-notebooks-1.0.0.vsix
```

### Option 2: Build and Install from Source

```bash
cd /Users/lefv/repos/mcli/vscode-extension
npm install
npm run compile
vsce package --no-yarn
code --install-extension mcli-workflow-notebooks-1.0.0.vsix
```

## First Time Setup

1. **Reload VSCode**: After installation, reload VSCode (`Cmd+Shift+P` → "Developer: Reload Window")

2. **Open a Workflow Notebook**:
   - Navigate to any workflow JSON file (e.g., `~/.mcli/commands/*.json`)
   - Right-click the file → "Open With..." → "MCLI Workflow Notebook"

3. **Set as Default (Optional)**:
   - Right-click any `.json` workflow file
   - "Open With..." → "Configure default editor for '*.json'"
   - Select "MCLI Workflow Notebook"

## Usage

### Opening Files

The extension recognizes these file patterns:
- `**/commands/*.json`
- `**/*workflow*.json`
- `**/notebooks/*.json`

### Visual Notebook Interface

Once opened, you'll see:
- ✅ **Cell-based interface** (like Jupyter)
- ✅ **Code and Markdown cells**
- ✅ **Syntax highlighting**
- ✅ **Inline execution**
- ✅ **Output rendering**

### Keyboard Shortcuts

- `Shift+Enter`: Run cell and advance
- `Cmd+Enter`: Run cell
- `Esc`: Exit edit mode
- `Enter`: Enter edit mode
- `A`: Add cell above
- `B`: Add cell below
- `DD`: Delete cell

## Verifying Installation

```bash
# Check installed extensions
code --list-extensions | grep mcli

# Should show:
# mcli.mcli-workflow-notebooks
```

## Troubleshooting

### Extension not showing up

1. Reload window: `Cmd+Shift+P` → "Developer: Reload Window"
2. Check extension is enabled: Extensions sidebar → search "MCLI"

### Can't open notebooks

1. Ensure file matches pattern (contains "workflow" or in "commands" directory)
2. Right-click file → "Open With..." → manually select "MCLI Workflow Notebook"

### Cells not executing

1. Ensure Python 3 is installed: `python3 --version`
2. Check Output panel: View → Output → select "MCLI Workflow Notebooks"

## Uninstalling

```bash
code --uninstall-extension mcli.mcli-workflow-notebooks
```

## Next Steps

- [Extension README](./README.md)
- [MCLI Workflow Notebooks Guide](../docs/workflow-notebooks.md)
- [Create your first notebook](../docs/workflow-notebooks.md#creating-new-workflows)
