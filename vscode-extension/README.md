# 🚀 MCLI Workflow Notebooks

> ✨ Transform your workflow JSON files into beautiful, interactive notebooks!

[![Visual Editing](https://img.shields.io/badge/workflows-visual%20editing-brightgreen)](https://github.com/gwicho38/mcli)
[![Jupyter Compatible](https://img.shields.io/badge/jupyter-nbformat%204-orange)](https://jupyter.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)

## 🎯 What Is This?

Ever wish you could edit your workflow JSON files like Jupyter notebooks? Now you can! This extension brings the magic of cell-based editing to your MCLI workflow files.

### ✨ The Magic

```
Your workflow.json file
        ↓
📝 Edit with cell-based interface
        ↓
⚡ Run code and see output
        ↓
💾 Saves back to .json automatically
```

**Files stay as `.json`** - Visual editing is just a superpower! 🦸

## 🎬 Quick Demo

### Before (Plain JSON)
```json
{
  "nbformat": 4,
  "cells": [
    {"cell_type": "code", "source": ["print('hello')"]}
  ]
}
```

### After (Visual Interface)
```
┌─────────────────────────────────────┐
│ 📝 Markdown Cell                    │
│ # My Awesome Workflow               │
│ Does cool automation stuff!         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 🐍 Python Cell            ▶️ Run    │
│ print('hello world!')               │
│                                     │
│ 💬 Output:                          │
│ hello world!                        │
└─────────────────────────────────────┘

         [➕ Add Cell]
```

## 🚀 Features

### 🎨 Visual Cell-Based Editing
- **Add cells** with one click
- **Move cells** up/down easily
- **Delete cells** when you don't need them
- **Organize** your code logically

### ⚡ Live Execution
- **Run cells** with `Shift+Enter`
- **See output** inline immediately
- **Debug** with full error messages
- **Execute** Python, Shell, Bash, Zsh, Fish

### 🎯 Monaco Editor
- **IntelliSense** - Smart code completion
- **Syntax highlighting** - Beautiful code
- **Hover docs** - Instant documentation
- **Go to definition** - Navigate your code

### 📝 Rich Documentation
- **Markdown cells** - Write beautiful docs
- **Headers** - Organize sections
- **Lists, code blocks, links** - Full markdown support
- **Mix code & docs** - Keep everything together

### 💾 Git-Friendly
- **JSON format** - Clean, readable diffs
- **Version control** - Track changes easily
- **Collaboration** - Share with your team
- **Transparency** - No hidden binary format

## 📦 Installation

### From VSCode Marketplace (Recommended)

1. Open VSCode
2. Go to Extensions (`Cmd+Shift+X`)
3. Search for **"MCLI Workflow Notebooks"**
4. Click **Install**

### From VSIX File

```bash
# Download the .vsix file
# Then install:
code --install-extension mcli-workflow-notebooks-1.0.0.vsix
```

## 🎮 Usage

### Opening Notebooks

**Method 1: Right-click**
1. Right-click any `.json` workflow file
2. Select **"Open With..."**
3. Choose **"MCLI Workflow Notebook"**

**Method 2: Set as default**
1. Right-click → **"Open With..."**
2. **"Configure default editor for '*.json'"**
3. Select **"MCLI Workflow Notebook"**

### Creating New Notebooks

```bash
# Using MCLI CLI
mcli workflow notebook create my-awesome-workflow

# Open in visual editor
code ~/.mcli/commands/my-awesome-workflow.json
```

### Editing Cells

- **Add Cell**: Click `➕` button or press `B` (in command mode)
- **Edit Cell**: Click into cell and start typing
- **Run Cell**: Click `▶️` or press `Shift+Enter`
- **Delete Cell**: Press `DD` (in command mode)
- **Move Cell**: Use ↑↓ buttons

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| 🏃 Run cell and advance | `Shift+Enter` |
| ▶️ Run cell | `Cmd+Enter` |
| ➕ Add cell above | `A` (command mode) |
| ➕ Add cell below | `B` (command mode) |
| 🗑️ Delete cell | `DD` (command mode) |
| ✏️ Enter edit mode | `Enter` |
| 🚪 Exit edit mode | `Esc` |

## 🎨 Cell Types

### Code Cells

Support multiple languages:
- 🐍 **Python** - Full Python 3 support
- 🐚 **Shell** - Bash, Zsh, Fish scripts
- 📜 **Any language** via interpreters

### Markdown Cells

Rich text documentation:
- Headers, lists, links
- Code blocks with syntax highlighting
- Images, tables, and more
- GitHub Flavored Markdown

## 💡 Examples

### Example 1: Data Processing Workflow

```python
# Cell 1: Import libraries
import pandas as pd
import numpy as np

# Cell 2: Load data
df = pd.read_csv('data.csv')
print(f"Loaded {len(df)} rows")

# Cell 3: Process
df['new_column'] = df['old_column'] * 2
print(df.head())
```

### Example 2: DevOps Automation

```bash
# Cell 1: Check status
kubectl get pods

# Cell 2: Deploy
helm upgrade myapp ./chart

# Cell 3: Verify
curl https://myapp.com/health
```

## 🛠️ Requirements

- **VSCode** 1.85.0 or higher
- **Python 3** (for Python cell execution)
- **Bash/Zsh/Fish** (for shell cell execution)
- **MCLI** (optional, for workflow management)

## ⚙️ Extension Settings

This extension contributes the following settings:

- `mcli.notebooks.autoSave` - Auto-save changes (default: `true`)
- `mcli.notebooks.theme` - Editor theme (`light`, `dark`, `auto`)

## 📚 Documentation

- 📖 [Complete User Guide](https://github.com/gwicho38/mcli/blob/main/docs/workflow-notebooks.md)
- 🚀 [Quick Start](https://github.com/gwicho38/mcli/blob/main/README-VISUAL-EDITING.md)
- 💻 [Installation Guide](https://github.com/gwicho38/mcli/blob/main/vscode-extension/INSTALL.md)
- 🔧 [Technical Details](https://github.com/gwicho38/mcli/blob/main/docs/releases/PHASE-2-COMPLETE.md)

## 🤝 Contributing

Found a bug? Have a feature request? Want to contribute?

- 🐛 [Report Issues](https://github.com/gwicho38/mcli/issues)
- 💡 [Request Features](https://github.com/gwicho38/mcli/issues/new)
- 🔧 [Contribute Code](https://github.com/gwicho38/mcli/pulls)

## 📝 File Format

Files are standard Jupyter notebooks (nbformat 4) with `.json` extension:

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "mcli": {
      "name": "workflow-name",
      "description": "What this workflow does",
      "language": "python"
    }
  },
  "cells": [
    {
      "cell_type": "code",
      "source": ["print('Hello!')"],
      "metadata": {"language": "python"},
      "outputs": []
    }
  ]
}
```

## 🎯 Use Cases

### 📊 Data Science
- Process data with pandas
- Run analysis workflows
- Document findings inline

### 🚀 DevOps
- Automate deployments
- Run kubectl commands
- Document procedures

### 🔬 Research
- Reproducible experiments
- Document methodology
- Share workflows

### 🎓 Learning
- Interactive tutorials
- Code examples with docs
- Step-by-step guides

## ❓ FAQ

**Q: Will this change my JSON files?**
A: No! Files remain as `.json`. The extension just provides a visual interface.

**Q: Is this compatible with Jupyter?**
A: Yes! Uses standard Jupyter nbformat 4.

**Q: Can I edit files without the extension?**
A: Absolutely! They're just JSON - edit with any editor.

**Q: Does execution run locally?**
A: Yes, currently runs Python/Shell locally (MCLI daemon integration coming).

## 🗺️ Roadmap

### ✅ Phase 1 & 2 (Complete)
- Visual editing
- Cell execution
- Monaco integration
- Production ready

### 🔮 Phase 3 (Coming Soon)
- Variable inspector
- Debugger integration
- MCLI daemon execution
- Interactive outputs

### 🌟 Phase 4 (Future)
- Collaboration features
- Notebook templates
- Advanced visualizations
- Plugin system

## 📄 License

MIT License - see [LICENSE.txt](LICENSE.txt)

## 🙏 Acknowledgments

- Built with [VSCode Extension API](https://code.visualstudio.com/api)
- Uses [Jupyter nbformat 4](https://jupyter.org/)
- Inspired by [C3 AI Extension](https://marketplace.visualstudio.com/items?itemName=C3ai.c3-ai-dx-v8)
- Part of the [MCLI Framework](https://github.com/gwicho38/mcli)

---

**Made with ❤️ for workflow automation enthusiasts**

**Enjoy your new visual superpowers! 🚀✨**

[⭐ Star us on GitHub](https://github.com/gwicho38/mcli) | [📖 Read the docs](https://github.com/gwicho38/mcli/blob/main/docs/workflow-notebooks.md) | [🐛 Report a bug](https://github.com/gwicho38/mcli/issues)
