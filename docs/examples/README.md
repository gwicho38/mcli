# MCLI Workflow Examples

This directory contains example workflow scripts demonstrating the various languages
supported by `mcli new`.

## Supported Languages

| Language | Extension | Runtime | Example File |
|----------|-----------|---------|--------------|
| Python | `.py` | python3 | `workflows/example_python.py` |
| Shell | `.sh`, `.bash` | bash/zsh/fish | `workflows/example_shell.sh` |
| JavaScript | `.js` | bun | `workflows/example_javascript.js` |
| TypeScript | `.ts` | bun | `workflows/example_typescript.ts` |
| Jupyter | `.ipynb` | papermill | N/A |

## Metadata Format

All scripts use `@-prefixed` comments for metadata:

```python
# @description: Brief description of the command
# @version: 1.0.0
# @group: category
# @author: Your Name
# @tags: tag1, tag2, tag3
# @requires: dependency1, dependency2
# @shell: bash  # Only for shell scripts
```

For JavaScript/TypeScript, use `//` comments:

```javascript
// @description: Brief description of the command
// @version: 1.0.0
// @group: category
```

For Jupyter notebooks, metadata is stored in the notebook's JSON structure:

```json
{
  "metadata": {
    "mcli": {
      "description": "Brief description",
      "version": "1.0.0",
      "group": "category"
    }
  }
}
```

## Creating New Commands

### From Scratch

```bash
# Interactive mode (opens editor)
mcli new my_command -l python

# Template mode (no editor)
mcli new my_command -l python -t

# With custom options
mcli new backup_db -l shell -d "Backup database" --group utils
```

### From Existing File

```bash
# Import and restructure an existing script
mcli new --file ./my_existing_script.py

# With custom name and group
mcli new custom_name --file ./script.sh --group utilities

# Import globally
mcli new --file ./script.py -g
```

## Running Commands

Once created, commands are available via:

```bash
# Run a workflow command
mcli run example_python

# With arguments
mcli run example_python "Alice" --greeting "Hi"

# Run from global scope
mcli run -g example_python
```

## Directory Structure

```
docs/examples/
├── README.md           # This file
└── workflows/
    ├── example_python.py
    ├── example_shell.sh
    ├── example_javascript.js
    └── example_typescript.ts
```

## Best Practices

1. **Always include metadata**: Description, version, and group at minimum
2. **Use descriptive names**: Command names should indicate what they do
3. **Handle errors gracefully**: Use `set -euo pipefail` in shell, try/catch in others
4. **Support `--help`**: Provide usage information for complex commands
5. **Use environment variables**: For configuration that varies between environments
6. **Keep dependencies minimal**: Prefer standard library when possible
