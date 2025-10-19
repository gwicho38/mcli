# Shell Command Support

MCLI now supports creating workflow commands in both **Python** and **Shell** (bash, zsh, fish, sh), providing flexibility to choose the right tool for each task.

## Overview

Shell commands are stored alongside Python commands in `~/.mcli/commands/` as JSON files, making them portable, version-controllable, and easy to share across machines.

## Features

- ✅ **Multi-Shell Support**: bash, zsh, fish, sh
- ✅ **Auto-Detection**: Automatically detects shell type from shebang or file extension
- ✅ **Argument Passing**: Pass arguments to shell scripts seamlessly
- ✅ **Environment Variables**: Access command metadata via `$MCLI_COMMAND`
- ✅ **Template Mode**: Quick command creation with pre-built templates
- ✅ **Editor Mode**: Interactive editing with your favorite editor
- ✅ **Import/Export**: Import existing shell scripts or export to `.sh` files
- ✅ **Unified Interface**: Same commands for managing Python and shell workflows

## Quick Start

### Creating a Shell Command

#### Using Template Mode (Fastest)
```bash
mcli commands add my_backup --language shell --template
```

#### Using Editor Mode (Interactive)
```bash
mcli commands add deploy_app --language shell --description "Deploy application"
```

#### Specify Shell Type
```bash
mcli commands add db_backup --language shell --shell bash
```

### Importing Existing Shell Scripts

MCLI automatically detects the language and shell type:

```bash
# Auto-detects from shebang and extension
mcli commands import my_script.sh -s

# Specify custom name and description
mcli commands import deploy.sh -s --name deploy_prod --description "Production deployment"
```

### Executing Shell Commands

Shell commands execute just like Python commands:

```bash
# No arguments
mcli workflow my_backup

# With arguments
mcli workflow deploy_app staging --force

# From any group
mcli workflow my_command arg1 arg2 arg3
```

## JSON Command Format

Shell commands are stored with the following structure:

```json
{
  "name": "git_status",
  "language": "shell",
  "shell": "bash",
  "code": "#!/usr/bin/env bash\n# Git status script\necho \"Status\"...",
  "description": "Enhanced git status",
  "group": "workflow",
  "version": "1.0",
  "created_at": "2025-10-19T03:52:27.481840Z",
  "updated_at": "2025-10-19T03:52:27.481844Z",
  "metadata": {}
}
```

## Shell Script Template

When you create a new shell command, MCLI provides this template:

```bash
#!/usr/bin/env bash
# command_name - Description
#
# This is a shell-based MCLI workflow command.
# Arguments are passed as positional parameters: $1, $2, $3, etc.
# The command name is available in: $MCLI_COMMAND

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Command logic
echo "Hello from command_name shell command!"
echo "Command: $MCLI_COMMAND"

# Example: Access arguments
if [ $# -gt 0 ]; then
    echo "Arguments: $@"
    for arg in "$@"; do
        echo "  - $arg"
    done
else
    echo "No arguments provided"
fi

# Exit successfully
exit 0
```

## Real-World Examples

### Example 1: Enhanced Git Status

```bash
#!/usr/bin/env bash
# Enhanced git status with color and branch info

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📁 Git Repository Status${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}✗ Not a git repository${NC}"
    exit 1
fi

# Show branch
BRANCH=$(git branch --show-current)
echo -e "${GREEN}Branch:${NC} $BRANCH"

# Show status
echo -e "\n${YELLOW}Status:${NC}"
git status --short

# Show last commit
echo -e "\n${YELLOW}Last commit:${NC}"
git log -1 --oneline

exit 0
```

**Create this command:**
```bash
# Save to file
cat > /tmp/git_status.sh << 'EOF'
[paste script above]
EOF

# Import into MCLI
mcli commands import /tmp/git_status.sh -s --name git_status
```

**Use it:**
```bash
mcli workflow git_status
```

### Example 2: Database Backup

```bash
#!/usr/bin/env bash
# Database backup script

set -euo pipefail

DB_NAME="${1:-mydb}"
BACKUP_DIR="${2:-$HOME/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
echo "Backing up database: $DB_NAME"
mysqldump "$DB_NAME" > "$BACKUP_FILE"

# Compress
gzip "$BACKUP_FILE"
echo "Backup complete: ${BACKUP_FILE}.gz"

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +7 -delete
echo "Cleaned up old backups"

exit 0
```

**Create and use:**
```bash
mcli commands add db_backup -l shell -t
# Edit ~/.mcli/commands/db_backup.json and replace code

mcli workflow db_backup production /backups/prod
```

### Example 3: Docker Container Manager

```bash
#!/usr/bin/env bash
# Manage Docker containers

set -euo pipefail

ACTION="${1:-list}"
CONTAINER="${2:-}"

case "$ACTION" in
    list)
        echo "Running containers:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;

    stop)
        if [ -z "$CONTAINER" ]; then
            echo "Error: Container name required"
            exit 1
        fi
        echo "Stopping container: $CONTAINER"
        docker stop "$CONTAINER"
        ;;

    restart)
        if [ -z "$CONTAINER" ]; then
            echo "Error: Container name required"
            exit 1
        fi
        echo "Restarting container: $CONTAINER"
        docker restart "$CONTAINER"
        ;;

    *)
        echo "Usage: $0 {list|stop|restart} [container_name]"
        exit 1
        ;;
esac

exit 0
```

## Language Comparison

### When to Use Shell

- **System administration tasks**: File operations, backups, deployments
- **Simple scripts**: Quick automation without complex logic
- **External tool orchestration**: Chaining Unix utilities
- **Git operations**: Wrapping git commands
- **Environment setup**: PATH modifications, exports

### When to Use Python

- **Complex logic**: Algorithms, data processing, API interactions
- **Error handling**: Need robust exception handling
- **Data manipulation**: JSON, CSV, database operations
- **Cross-platform**: Need Windows compatibility
- **MCLI integration**: Need access to MCLI APIs and libraries

## Tips and Best Practices

### 1. Use Strict Error Handling
Always include at the top of your shell scripts:
```bash
set -euo pipefail
```

### 2. Provide Help Messages
```bash
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 [options]"
    echo "  -h, --help    Show this help"
    exit 0
fi
```

### 3. Validate Input
```bash
if [ $# -lt 1 ]; then
    echo "Error: Missing required argument"
    exit 1
fi
```

### 4. Use Descriptive Variable Names
```bash
# Good
BACKUP_DIR="/var/backups"
DB_NAME="production"

# Bad
dir="/var/backups"
d="production"
```

### 5. Add Comments
```bash
# Clean up temporary files older than 7 days
find /tmp -name "*.tmp" -mtime +7 -delete
```

## Advanced Features

### Accessing Command Metadata

The `$MCLI_COMMAND` environment variable contains the command name:

```bash
echo "Running command: $MCLI_COMMAND"
LOG_FILE="/var/log/${MCLI_COMMAND}.log"
```

### Exit Codes

MCLI respects shell exit codes:

```bash
# Success
exit 0

# Failure
if [ ! -f "$REQUIRED_FILE" ]; then
    echo "Error: Required file not found"
    exit 1
fi
```

### Combining with Python Commands

You can mix shell and Python commands in your workflow:

```bash
# Shell command to prepare data
mcli workflow prepare_data

# Python command to process
mcli workflow analyze_results

# Shell command to deploy
mcli workflow deploy_to_prod
```

## Listing and Managing Shell Commands

### View All Custom Commands
```bash
mcli commands list --custom-only
```

### Search for Shell Commands
```bash
mcli commands search backup
```

### View Command Details
```bash
mcli commands info git_status
```

### Edit a Shell Command
```bash
mcli commands edit git_status
```

### Remove a Shell Command
```bash
mcli commands remove old_backup --yes
```

### Export to Shell Script
```bash
mcli commands export git_status -s -o ~/scripts/git-status.sh
```

## Sharing Shell Commands

### Export for Sharing
```bash
# Export single command
mcli commands export git_status -s -o git-status.sh

# Export all commands
mcli commands export my-commands.json
```

### Import Shared Commands
```bash
# Import shell script
mcli commands import git-status.sh -s

# Import JSON collection
mcli commands import shared-commands.json
```

### Git-Based Workflow
```bash
# Store in git repository
cp ~/.mcli/commands/git_status.json ~/my-mcli-commands/
cd ~/my-mcli-commands
git add .
git commit -m "Add git status command"
git push

# On another machine
git pull
cp git_status.json ~/.mcli/commands/
```

## Troubleshooting

### Command Not Found After Creation
Restart MCLI or reload commands:
```bash
# Restart terminal or
source ~/.bashrc  # or ~/.zshrc
```

### Permission Denied
MCLI automatically makes scripts executable. If you get permission errors:
```bash
chmod +x ~/.mcli/commands/*.sh
```

### Shell Not Available
If using a specific shell (zsh, fish), ensure it's installed:
```bash
which zsh
which fish
which bash
```

### Shebang Not Working
Ensure the shebang path is correct:
```bash
#!/usr/bin/env bash    # ✓ Portable
#!/bin/bash            # ✓ Specific
#!/usr/local/bin/bash  # ✗ Non-portable
```

## Migration Guide

### Converting Existing Shell Scripts

1. **Save your script**
   ```bash
   cp ~/scripts/backup.sh /tmp/backup.sh
   ```

2. **Import to MCLI**
   ```bash
   mcli commands import /tmp/backup.sh -s --name backup
   ```

3. **Test execution**
   ```bash
   mcli workflow backup --help
   ```

4. **Remove old script** (optional)
   ```bash
   rm ~/scripts/backup.sh
   ```

### Converting Python Commands to Shell

If a Python command is just calling shell commands:

```python
# Before (Python)
import subprocess
subprocess.run(["git", "status"])
subprocess.run(["git", "log", "-1"])
```

```bash
# After (Shell)
#!/usr/bin/env bash
git status
git log -1
```

Convert:
```bash
mcli commands export old_command -s -o /tmp/temp.py
# Rewrite as shell script
mcli commands add new_command -l shell
# Paste shell version
```

## Version History

- **v7.10.0** - Initial shell command support
  - Multi-shell support (bash, zsh, fish, sh)
  - Auto-detection from shebang and file extension
  - Template and editor modes
  - Import/export functionality
  - Unified command management interface
