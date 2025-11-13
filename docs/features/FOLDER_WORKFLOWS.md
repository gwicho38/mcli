# Folder-Based Workflows

Folder-based workflows provide a simple, intuitive way to organize your workflow scripts hierarchically. Just drag and drop scripts into folders, and mcli automatically creates command groups.

## Overview

The folder-based workflow system supports three types of workflows:

1. **Standalone Workflows**: Top-level scripts that become direct subcommands
2. **Folder Workflows**: Folders containing scripts, where the folder name becomes a command group
3. **Makefile Workflows**: Makefile targets automatically exposed as commands

## Quick Start

### Basic Structure

```
~/.mcli/workflows/          # Global workflows
├── deploy.sh               # mcli run -g deploy (standalone)
├── backup.py               # mcli run -g backup (standalone)
├── database/               # mcli run -g database <command> (group)
│   ├── migrate.py          # mcli run -g database migrate
│   ├── backup.sh           # mcli run -g database backup
│   └── restore.sh          # mcli run -g database restore
└── cloud/                  # mcli run -g cloud <command> (group)
    ├── deploy.py           # mcli run -g cloud deploy
    └── status.sh           # mcli run -g cloud status

.mcli/workflows/            # Local workflows (git repo only)
├── test.sh                 # mcli run test (standalone)
└── cheese/                 # mcli run cheese <command> (group)
    ├── cheddar.py          # mcli run cheese cheddar
    └── gouda.sh            # mcli run cheese gouda
```

### Local vs Global Workflows

- **Local** (`.mcli/workflows/`): Project-specific workflows, only available inside git repos
- **Global** (`~/.mcli/workflows/`): Personal workflows available everywhere

```bash
# Local workflow (requires git repo)
mcli run my-workflow

# Global workflow (anywhere)
mcli run -g my-workflow
mcli run --global my-workflow
```

## Creating Workflows

### 1. Standalone Python Workflow

Create `~/.mcli/workflows/hello.py`:

```python
#!/usr/bin/env python3
"""
Say hello to someone.
This text becomes the command help.
"""
import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"Hello, {name}!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Make it executable:
```bash
chmod +x ~/.mcli/workflows/hello.py
```

Usage:
```bash
mcli run -g hello              # Hello, World!
mcli run -g hello Alice        # Hello, Alice!
```

### 2. Standalone Shell Workflow

Create `~/.mcli/workflows/deploy.sh`:

```bash
#!/usr/bin/env bash
# Deploy application to production
# Additional help text here
set -euo pipefail

ENV=${1:-staging}
echo "Deploying to: $ENV"

# Your deployment logic here
echo "✓ Deployment complete!"
```

Make it executable:
```bash
chmod +x ~/.mcli/workflows/deploy.sh
```

Usage:
```bash
mcli run -g deploy              # Deploy to staging
mcli run -g deploy production   # Deploy to production
```

### 3. Folder Workflow Group

Create a folder with multiple related scripts:

```bash
mkdir -p ~/.mcli/workflows/database
```

Create `~/.mcli/workflows/database/migrate.py`:
```python
#!/usr/bin/env python3
"""Run database migrations."""
print("Running migrations...")
# Migration logic here
```

Create `~/.mcli/workflows/database/backup.sh`:
```bash
#!/usr/bin/env bash
# Backup database to S3
echo "Creating backup..."
# Backup logic here
```

Make them executable:
```bash
chmod +x ~/.mcli/workflows/database/*.{py,sh}
```

Usage:
```bash
mcli run -g database --help     # List all database commands
mcli run -g database migrate    # Run migrations
mcli run -g database backup     # Create backup
```

## Language Detection

mcli automatically detects the script language:

### Priority Order
1. **Shebang line** (highest priority)
2. **File extension**
3. **Default to Python** (if unknown)

### Supported Languages

#### Python
```python
#!/usr/bin/env python3
# or
#!/usr/bin/env python
```
File extensions: `.py`

#### Shell Scripts
```bash
#!/usr/bin/env bash  # Bash
#!/usr/bin/env zsh   # Zsh
#!/usr/bin/env fish  # Fish
#!/usr/bin/env sh    # Generic shell
#!/bin/bash          # Also valid
```
File extensions: `.sh`

## Help Text Extraction

### Python Scripts
mcli extracts the module-level docstring:

```python
#!/usr/bin/env python3
"""
This is the command help text.

It can span multiple lines.
All text in the docstring becomes the help.
"""
import sys
# ... rest of code
```

### Shell Scripts
mcli extracts comments after the shebang:

```bash
#!/usr/bin/env bash
# This is the command help text.
# Additional lines are included.
# Blank comment lines are skipped.

set -euo pipefail
# ... rest of code
```

## Makefile Integration

Makefile targets are automatically exposed as commands under the `make` group.

### Setup

Create `.mcli/Makefile` or `Makefile` in your project:

```makefile
.PHONY: test build clean

test: ## Run unit tests
\t@pytest tests/

build: ## Build the project
\t@python -m build

clean: ## Remove build artifacts
\t@rm -rf dist/ build/
```

### Usage

```bash
mcli run make --help      # List all targets
mcli run make test        # Run tests
mcli run make build       # Build project
mcli run make clean       # Clean artifacts
```

### Makefile Help Annotations

Use `##` comments to provide descriptions:

```makefile
target: ## Description here
\t@command

# Or above the target:
# Description here
target:
\t@command
```

## Advanced Features

### Passing Arguments

All scripts receive arguments via command line:

#### Python
```python
#!/usr/bin/env python3
import sys

# Access arguments
args = sys.argv[1:]  # ['arg1', 'arg2', ...]
```

#### Shell
```bash
#!/usr/bin/env bash

# Access arguments
echo "First arg: $1"
echo "All args: $*"
```

#### Usage
```bash
mcli run -g my-script arg1 arg2 arg3
mcli run -g database migrate --dry-run --verbose
```

### Environment Variables

Scripts inherit the current environment and receive special variables:

```bash
MCLI_COMMAND=<command-name>           # Name of the command
MCLI_SCRIPT_PATH=<path-to-script>     # Full path to the script
MCLI_WORKFLOWS_DIR=<workflows-dir>    # Workflows directory path
MCLI_GLOBAL=<true|false>              # Whether running in global mode
```

### Exit Codes

Scripts should return proper exit codes:

```python
#!/usr/bin/env python3
import sys

if error_occurred:
    print("Error: Something went wrong", file=sys.stderr)
    sys.exit(1)  # Non-zero exit code

print("Success!")
sys.exit(0)  # Success
```

```bash
#!/usr/bin/env bash
set -euo pipefail  # Exit on error

if [ ! -f "config.yaml" ]; then
    echo "Error: config.yaml not found" >&2
    exit 1
fi

echo "Success!"
exit 0
```

### Special Characters and Spaces

Scripts properly handle arguments with spaces and special characters:

```bash
mcli run -g backup "/path/with spaces/file.txt"
mcli run -g deploy "user@example.com" "production"
```

## Best Practices

### 1. Use Descriptive Names

```
✅ Good:
  - deploy-production.sh
  - database-migrate.py
  - backup-to-s3.sh

❌ Bad:
  - script1.sh
  - temp.py
  - test.sh
```

### 2. Add Help Text

Always include help text via docstrings or comments:

```python
#!/usr/bin/env python3
"""
Clear and descriptive help text explaining:
- What the workflow does
- Required arguments
- Example usage
"""
```

### 3. Make Scripts Executable

```bash
chmod +x ~/.mcli/workflows/**/*.{py,sh}
```

### 4. Use Groups for Related Commands

Organize related workflows into folders:

```
database/
  - migrate.py
  - backup.sh
  - restore.sh

cloud/
  - deploy.py
  - status.sh
  - logs.sh
```

### 5. Handle Errors Gracefully

```python
#!/usr/bin/env python3
import sys

try:
    # Your code here
    pass
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
```

### 6. Use Environment-Specific Workflows

Use local workflows (`.mcli/workflows/`) for project-specific scripts:

```
.mcli/workflows/
  - test.sh           # Project-specific test runner
  - deploy.sh         # Project-specific deployment
  - database/
    - seed.py         # Seed project database
```

## Migration from JSON Commands

If you have existing JSON commands, you can migrate to folder workflows:

### Before (JSON)
```json
{
  "name": "deploy",
  "group": "workflows",
  "language": "shell",
  "code": "#!/bin/bash\\necho 'Deploying...'"
}
```

### After (Folder Workflow)
1. Create `~/.mcli/workflows/deploy.sh`
2. Add the script content
3. Make it executable: `chmod +x deploy.sh`
4. Remove the JSON command: `mcli rm -g deploy`

The folder workflow approach is simpler and more maintainable.

## Troubleshooting

### Workflow Not Showing Up

1. **Check file permissions**: Scripts must be executable
   ```bash
   chmod +x ~/.mcli/workflows/my-script.py
   ```

2. **Check file extension**: Use `.py` for Python, `.sh` for shell
   ```bash
   mv script script.py  # Add extension
   ```

3. **Check location**: Local workflows only work in git repos
   ```bash
   git status  # Must be in a git repo for local workflows
   ```

4. **Refresh command list**:
   ```bash
   mcli run --help           # List local workflows
   mcli run -g --help        # List global workflows
   ```

### Script Not Executing

1. **Check shebang**: First line must be a valid shebang
   ```python
   #!/usr/bin/env python3  # ✅ Correct
   #! /usr/bin/python       # ❌ Space after #!
   ```

2. **Check syntax**: Verify script runs standalone
   ```bash
   python3 ~/.mcli/workflows/my-script.py  # Test directly
   bash ~/.mcli/workflows/my-script.sh     # Test directly
   ```

3. **Check exit code**: Scripts must exit properly
   ```python
   sys.exit(0)  # Explicit exit
   ```

### Help Text Not Showing

1. **Python**: Ensure docstring is at module level
   ```python
   #!/usr/bin/env python3
   """This appears as help."""  # ✅ Module level
   import sys

   def main():
       """This does NOT appear."""  # ❌ Function level
   ```

2. **Shell**: Comments must be after shebang
   ```bash
   #!/usr/bin/env bash
   # This appears as help  # ✅ After shebang

   set -euo pipefail
   # This does NOT appear  # ❌ After code
   ```

## Examples

### Example 1: Image Converter

A global workflow that resizes images (already included!):

```bash
# Convert all PNGs on Desktop to 1024x500
mcli run -g image-convert 1024 500

# Convert specific image
mcli run -g image-convert 1024 x 500 --input ~/photo.jpg

# Convert with glob pattern
mcli run -g image-convert 1024x500 --input "*.png"

# Use fill mode (crop to fit)
mcli run -g image-convert 1024 500 --mode fill
```

### Example 2: Project Test Suite

Local workflows for a project:

```
.mcli/workflows/
├── test.sh              # Run all tests
├── test-unit.sh         # Run unit tests only
└── coverage.sh          # Generate coverage report
```

Usage:
```bash
cd my-project
mcli run test            # Run all tests
mcli run test-unit       # Unit tests only
mcli run coverage        # Coverage report
```

### Example 3: Multi-Service Deployment

Folder workflow for microservices:

```
~/.mcli/workflows/deploy/
├── api.sh               # Deploy API service
├── web.sh               # Deploy web frontend
├── worker.sh            # Deploy background workers
└── all.sh               # Deploy all services
```

Usage:
```bash
mcli run -g deploy --help        # List all deployment commands
mcli run -g deploy api staging   # Deploy API to staging
mcli run -g deploy all production # Deploy all to production
```

### Example 4: Database Management

Comprehensive database workflow group:

```
~/.mcli/workflows/database/
├── migrate.py           # Run migrations
├── rollback.py          # Rollback last migration
├── seed.py              # Seed database
├── backup.sh            # Create backup
├── restore.sh           # Restore from backup
└── console.sh           # Open database console
```

Usage:
```bash
mcli run -g database migrate     # Run migrations
mcli run -g database backup      # Create backup
mcli run -g database restore latest.dump  # Restore backup
```

## See Also

- [Commands Guide](./COMMANDS.md) - Full command reference
- [JSON Commands](./JSON_COMMANDS.md) - Legacy JSON command format
- [Testing Guide](../testing/TESTING.md) - Testing workflows
- [Setup Guide](../setup/INSTALL.md) - Installation and setup
