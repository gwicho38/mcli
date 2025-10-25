# Workflow Notebooks

MCLI Workflow Notebooks provide a Jupyter-compatible, cell-based format for authoring and managing workflow commands visually.

## Overview

Workflow notebooks allow you to:

- **Visual Editing**: Edit workflows in a cell-based interface (Monaco editor coming in Phase 2)
- **Documentation**: Mix code with markdown documentation
- **Modular Organization**: Split complex workflows into logical cells
- **Jupyter Compatible**: Standard notebook format that works with VSCode, JupyterLab, etc.
- **Backward Compatible**: Seamlessly convert to/from existing workflow JSON format

## Notebook Format

Notebooks use the standard Jupyter notebook format (nbformat 4) with MCLI-specific metadata:

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "mcli": {
      "name": "workflow-name",
      "description": "Workflow description",
      "group": "workflow",
      "version": "1.0",
      "language": "python"
    },
    "kernelspec": { ... },
    "language_info": { ... }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "source": ["# Documentation"]
    },
    {
      "cell_type": "code",
      "source": ["import click\n", "@click.command()\n", "..."],
      "metadata": {"language": "python"},
      "execution_count": null,
      "outputs": []
    }
  ]
}
```

## Cell Types

### Code Cells

Code cells contain executable Python or Shell code:

```json
{
  "cell_type": "code",
  "metadata": {"language": "python"},
  "source": [
    "import click\n",
    "\n",
    "@click.command()\n",
    "def hello():\n",
    "    click.echo('Hello!')\n"
  ],
  "execution_count": null,
  "outputs": []
}
```

Supported languages:
- `python` (default)
- `shell`, `bash`, `zsh`, `fish`

### Markdown Cells

Markdown cells contain documentation:

```json
{
  "cell_type": "markdown",
  "source": [
    "# Section Title\n",
    "\n",
    "This workflow does X, Y, and Z.\n",
    "\n",
    "## Usage\n",
    "..."
  ]
}
```

## CLI Commands

### Create a New Notebook

```bash
# Create a new workflow notebook
mcli workflow notebook create my-workflow

# With description and group
mcli workflow notebook create my-workflow \
  -d "My workflow description" \
  -g workflow \
  -l python
```

### Convert Between Formats

```bash
# Convert existing workflow to notebook format
mcli workflow notebook convert workflow.json --to notebook

# Convert notebook to workflow format
mcli workflow notebook convert notebook.json --to workflow -o output.json

# Create backup automatically (default)
mcli workflow notebook convert workflow.json --to notebook --backup
```

### Migrate All Workflows

```bash
# Migrate all workflows in ~/.mcli/commands to notebook format
mcli workflow notebook migrate

# Dry run to see what would be migrated
mcli workflow notebook migrate --dry-run

# Migrate specific directory
mcli workflow notebook migrate -d /path/to/workflows

# No backup (use with caution)
mcli workflow notebook migrate --no-backup
```

### Validate Notebooks

```bash
# Validate schema and syntax
mcli workflow notebook validate notebook.json

# Validate schema only
mcli workflow notebook validate notebook.json --schema

# Validate syntax only
mcli workflow notebook validate notebook.json --syntax
```

### View Notebook Info

```bash
# Display notebook information
mcli workflow notebook info notebook.json

# Output as JSON
mcli workflow notebook info notebook.json --json
```

### Edit Notebooks Visually

```bash
# Open in visual editor (Phase 2 - coming soon)
mcli workflow notebook edit notebook.json

# Use custom port
mcli workflow notebook edit notebook.json --port 9000
```

## Conversion Details

### Workflow → Notebook

When converting a workflow to notebook format:

1. Metadata is preserved in `metadata.mcli`
2. Code is intelligently split into cells based on:
   - Cell markers (`# %%`, `# <cell>`, `# CELL`)
   - Function/class definitions
   - Double blank lines
3. Description becomes a markdown cell (optional)

### Notebook → Workflow

When converting a notebook to workflow format:

1. All code cells are combined into single `code` field
2. Cells are joined with `# %%` markers for potential round-trip
3. MCLI metadata is extracted from `metadata.mcli`
4. Markdown cells are preserved but not executed

## Cell Markers

You can use cell markers in your code to explicitly define cell boundaries:

```python
# %%
import click
from pathlib import Path

# %%
@click.command()
def main():
    """Main command"""
    pass

# %%
if __name__ == "__main__":
    main()
```

Supported markers:
- `# %%` (VSCode/Jupyter style)
- `# <cell>` (explicit marker)
- `# CELL` (explicit marker)

## Validation

Notebooks can be validated for:

### Schema Validation

Checks that the notebook conforms to the Jupyter nbformat 4 schema with MCLI extensions.

```bash
mcli workflow notebook validate notebook.json --schema
```

### Syntax Validation

Validates code syntax in all code cells:
- **Python**: Uses `ast.parse()` to check syntax
- **Shell**: Uses `bash -n` for syntax checking

```bash
mcli workflow notebook validate notebook.json --syntax
```

## Examples

### Example 1: Simple Command Notebook

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "mcli": {
      "name": "hello",
      "description": "Simple hello command"
    }
  },
  "cells": [
    {
      "cell_type": "code",
      "source": [
        "import click\n",
        "\n",
        "@click.command()\n",
        "@click.option('--name', default='World')\n",
        "def hello(name):\n",
        "    click.echo(f'Hello, {name}!')\n"
      ]
    }
  ]
}
```

### Example 2: Multi-Cell Workflow

See [`examples/notebooks/example-workflow.json`](../examples/notebooks/example-workflow.json) for a complete example demonstrating:

- Markdown documentation cells
- Multiple code cells
- Command group with subcommands
- File processing logic

## Best Practices

1. **Use Markdown Cells**: Document your workflows with markdown cells
2. **Logical Cell Division**: Split code into logical units (imports, helpers, commands)
3. **Cell Markers**: Use `# %%` markers in legacy workflows for better conversion
4. **Validation**: Always validate notebooks after manual editing
5. **Version Control**: Notebook JSON is git-friendly with pretty formatting

## Roadmap

### Phase 1: Foundation (Complete)
- ✅ Notebook schema design
- ✅ Bidirectional converter
- ✅ CLI commands
- ✅ Validation system
- ✅ Unit tests

### Phase 2: Visual Editor (Planned)
- ⏳ Monaco editor integration
- ⏳ Web-based UI
- ⏳ Live editing with file sync
- ⏳ Syntax highlighting and IntelliSense

### Phase 3: Execution (Planned)
- ⏳ Cell execution engine
- ⏳ Output capture and display
- ⏳ Variable sharing between cells
- ⏳ Interactive debugging

### Phase 4: Advanced Features (Planned)
- ⏳ Export to standalone scripts
- ⏳ Export to HTML/PDF
- ⏳ Notebook templates
- ⏳ Git diff integration

## Troubleshooting

### Conversion Issues

**Problem**: Conversion fails with "Invalid JSON"
- **Solution**: Validate the source JSON with `python -m json.tool file.json`

**Problem**: Code not split into cells correctly
- **Solution**: Add `# %%` markers to explicitly define cell boundaries

### Validation Issues

**Problem**: Syntax validation fails but code works
- **Solution**: Check for platform-specific shell commands; validation uses bash

**Problem**: Schema validation fails
- **Solution**: Ensure all required fields are present (name, nbformat, etc.)

## Related Documentation

- [Custom Commands](./custom-commands.md)
- [Workflow System](../README.md#workflow-commands)
- [Jupyter Notebook Format](https://nbformat.readthedocs.io/)

## Feedback

Found a bug or have a feature request? File an issue:
- [GitHub Issues](https://github.com/gwicho38/mcli/issues)
- Label: `workflow`, `enhancement`

## VSCode Monaco Editor Support

### Getting IntelliSense for Workflow Notebooks

To enable IntelliSense, autocomplete, and validation in VSCode for your workflow notebook JSON files:

**Option 1: Automatic (within mcli repo)**
- Files in `examples/notebooks/` and `~/.mcli/commands/` automatically get schema support
- No configuration needed if working in the mcli repository

**Option 2: User Settings (for editing workflow files anywhere)**

Add this to your VSCode User Settings (`Cmd+Shift+P` → "Preferences: Open User Settings (JSON)"):

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

**Option 3: Workspace Settings**

For project-specific configuration, create `.vscode/settings.json`:

```json
{
  "json.schemas": [
    {
      "fileMatch": ["*.json"],
      "url": "./path/to/notebook-schema.json"
    }
  ]
}
```

### What You Get

With schema validation enabled in Monaco/VSCode:

✅ **Autocomplete**: Field suggestions as you type
✅ **Validation**: Real-time error highlighting
✅ **Hover docs**: Descriptions for each field
✅ **IntelliSense**: Smart suggestions based on context
✅ **Enum values**: Dropdowns for `cell_type`, `language`, etc.

### Example Editing Experience

When editing a workflow notebook in VSCode with schema support:

1. **Start typing `"cell_type": `** → Monaco suggests: `"code"`, `"markdown"`, `"raw"`
2. **Hover over `"nbformat"`** → Shows: "Jupyter notebook format version (always 4)"
3. **Add invalid field** → Red squiggly underline with error message
4. **Type `"metadata": { "mcli": {`** → Auto-suggests required `name` field

### Monaco Editor JSON Formatting

The schema also enables Monaco's built-in JSON formatting:
- Right-click → "Format Document" (or `Shift+Alt+F`)
- Automatic indentation and structure validation
- Preserves comments in JSONC files

