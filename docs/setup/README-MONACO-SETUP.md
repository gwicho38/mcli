# Monaco Editor Support for MCLI Workflow Notebooks

## Quick Setup

Your `.json` workflow files now have **full Monaco editor IntelliSense support**!

### How It Works

1. **Keep `.json` extension** - Transparency preserved ✅
2. **JSON Schema** provides Monaco/VSCode with field definitions
3. **IntelliSense** works automatically for:
   - Field autocomplete
   - Validation
   - Hover documentation
   - Error highlighting

### Setup (One-Time)

Add to your VSCode User Settings:

```json
{
  "json.schemas": [
    {
      "fileMatch": [
        "~/.mcli/commands/*.json",
        "**/commands/*.json",
        "**/*workflow*.json"
      ],
      "url": "https://raw.githubusercontent.com/gwicho38/mcli/main/src/mcli/workflow/notebook/notebook-schema.json"
    }
  ]
}
```

### What You Get

✅ Type `"cell_type":` → Auto-suggests: `"code"`, `"markdown"`, `"raw"`
✅ Hover over fields → See documentation
✅ Invalid values → Red squiggly underlines
✅ Format Document (Shift+Alt+F) → Auto-format JSON

### No Custom Extension Needed!

This uses Monaco's **built-in JSON language support** with our schema definition. No LSP server, no custom extension - just standard JSON schema validation that Monaco already knows how to handle.

### The Format

Your `.json` files are:
- ✅ Valid Jupyter notebooks (nbformat 4)
- ✅ Monaco-compatible with schema
- ✅ Human-readable JSON
- ✅ Git-friendly
- ✅ MCLI workflow commands

### Example

```json
{
  "nbformat": 4,          // ← Monaco knows this must be 4
  "nbformat_minor": 5,
  "metadata": {
    "mcli": {
      "name": "my-workflow",  // ← Required field
      "language": "python"     // ← Enum: python|shell|bash|zsh|fish
    }
  },
  "cells": [
    {
      "cell_type": "code",  // ← Autocomplete: code|markdown|raw
      "source": ["import click\n"],
      "metadata": {"language": "python"}
    }
  ]
}
```

## Future: Visual Editor (Phase 2)

In Phase 2, we'll add `mcli workflow notebook edit file.json` which launches a Monaco-based visual editor with:
- Cell-based UI (like Jupyter)
- Live execution
- Rich output rendering

But **right now**, your `.json` files already have full Monaco IntelliSense support! 🎉
