# Shell-Based Workflows Guide

This guide explains how to create and use shell-based workflows in MCLI, as opposed to Python-based workflows.

## Overview

MCLI supports two types of workflows:
1. **Python workflows** - Use Python code with Click decorators (default)
2. **Shell workflows** - Use bash/zsh scripts for automation

Shell workflows are ideal for:
- System administration tasks
- Git operations
- File management
- CI/CD integrations
- Docker/container operations
- Any task that's easier in bash than Python

## Shell Workflow Structure

A shell workflow JSON file has the following structure:

```json
{
  "name": "workflow_name",
  "code": "#!/usr/bin/env bash\n\n# Your shell script here\necho 'Hello from shell!'\n",
  "description": "What this workflow does",
  "group": "workflow",
  "language": "shell",
  "shell": "bash",
  "version": "1.0"
}
```

### Key Fields

- **`name`** (required): Command name (use underscores, not hyphens)
- **`code`** (required): Shell script code (use `\n` for newlines)
- **`description`** (required): Short description of what the workflow does
- **`group`** (optional): Always "workflow" for workflows
- **`language`** (required): Must be "shell" for shell-based workflows
- **`shell`** (optional): Shell type - "bash" (default), "zsh", or "sh"
- **`version`** (optional): Semantic version string

## Example 1: Simple System Check

Create `~/.mcli/workflows/system_check.json`:

```json
{
  "name": "system_check",
  "code": "#!/usr/bin/env bash\\n\\nset -euo pipefail\\n\\necho '🖥️  System Information'\\necho '━━━━━━━━━━━━━━━━━━━━'\\necho \"Hostname: $(hostname)\"\\necho \"OS: $(uname -s)\"\\necho \"Kernel: $(uname -r)\"\\necho \"Uptime: $(uptime | awk '{print $3, $4}' | sed 's/,//')\"\\necho \"\"\\necho \"💾 Disk Usage:\"\\ndf -h / | tail -1 | awk '{print \"  Used: \"$3\" / \"$2\" (\"$5\")\"}\'\\necho \"\"\\necho \"🧠 Memory:\"\\nfree -h 2>/dev/null || vm_stat | head -5\\n",
  "description": "Quick system health check",
  "group": "workflow",
  "language": "shell",
  "shell": "bash",
  "version": "1.0"
}
```

Usage:
```bash
mcli workflows system_check
```

## Example 2: Git Branch Cleanup

Create `~/.mcli/workflows/git_cleanup.json`:

```json
{
  "name": "git_cleanup",
  "code": "#!/usr/bin/env bash\\n\\nset -euo pipefail\\n\\n# Colors\\nRED='\\\\033[0;31m'\\nGREEN='\\\\033[0;32m'\\nYELLOW='\\\\033[1;33m'\\nNC='\\\\033[0m'\\n\\necho -e \"${YELLOW}🌿 Git Branch Cleanup${NC}\"\\necho '━━━━━━━━━━━━━━━━━━━━━━━━'\\n\\nif ! git rev-parse --git-dir > /dev/null 2>&1; then\\n    echo -e \"${RED}✗ Not a git repository${NC}\"\\n    exit 1\\nfi\\n\\n# Fetch and prune\\necho -e \"${GREEN}→${NC} Fetching and pruning...\"\\ngit fetch --prune\\n\\n# List merged branches (excluding main/master)\\necho -e \"\\\\n${YELLOW}Merged branches:${NC}\"\\ngit branch --merged | grep -v '\\\\*' | grep -v 'main' | grep -v 'master' || echo 'None'\\n\\n# List stale branches (older than 30 days)\\necho -e \"\\\\n${YELLOW}Stale branches (>30 days):${NC}\"\\ngit for-each-ref --sort=-committerdate refs/heads/ --format='%(refname:short) %(committerdate:relative)' | \\\\\\n    awk '$2 ~ /months?|years?/ {print $1, $2, $3}'\\n\\necho -e \"\\\\n${GREEN}✓ Analysis complete${NC}\"\\necho -e \"${YELLOW}Tip:${NC} Delete branches with: git branch -d <branch-name>\"\\n",
  "description": "Analyze and identify branches for cleanup",
  "group": "workflow",
  "language": "shell",
  "shell": "bash",
  "version": "1.0"
}
```

Usage:
```bash
mcli workflows git_cleanup
```

## Example 3: Docker Container Monitor

Create `~/.mcli/workflows/docker_status.json`:

```json
{
  "name": "docker_status",
  "code": "#!/usr/bin/env bash\\n\\nset -euo pipefail\\n\\nif ! command -v docker &> /dev/null; then\\n    echo '❌ Docker not found'\\n    exit 1\\nfi\\n\\necho '🐳 Docker Status'\\necho '━━━━━━━━━━━━━━━━'\\necho ''\\n\\necho '📦 Running Containers:'\\ndocker ps --format 'table {{.Names}}\\\\t{{.Status}}\\\\t{{.Ports}}' | head -10\\n\\necho ''\\necho '💾 Disk Usage:'\\ndocker system df\\n\\necho ''\\necho '🔢 Container Stats:'\\necho \\\"  Total: $(docker ps -aq | wc -l | tr -d ' ')\\\"\\necho \\\"  Running: $(docker ps -q | wc -l | tr -d ' ')\\\"\\necho \\\"  Stopped: $(docker ps -aq -f status=exited | wc -l | tr -d ' ')\\\"\\n",
  "description": "Monitor Docker containers and usage",
  "group": "workflow",
  "language": "shell",
  "shell": "bash",
  "version": "1.0"
}
```

Usage:
```bash
mcli workflows docker_status
```

## Example 4: Backup Script with Arguments

Create `~/.mcli/workflows/backup_dir.json`:

```json
{
  "name": "backup_dir",
  "code": "#!/usr/bin/env bash\\n\\nset -euo pipefail\\n\\nSOURCE_DIR=\\\"${1:-.}\\\"\\nBACKUP_DIR=\\\"${HOME}/backups\\\"\\nTIMESTAMP=$(date +%Y%m%d_%H%M%S)\\nBACKUP_NAME=\\\"backup_${TIMESTAMP}.tar.gz\\\"\\n\\necho '💾 Backup Utility'\\necho '━━━━━━━━━━━━━━━━'\\necho \\\"Source: ${SOURCE_DIR}\\\"\\necho \\\"Target: ${BACKUP_DIR}/${BACKUP_NAME}\\\"\\necho ''\\n\\n# Create backup directory\\nmkdir -p \\\"${BACKUP_DIR}\\\"\\n\\n# Create backup\\necho '→ Creating backup...'\\ntar -czf \\\"${BACKUP_DIR}/${BACKUP_NAME}\\\" -C \\\"$(dirname \\\"${SOURCE_DIR}\\\")\\\" \\\"$(basename \\\"${SOURCE_DIR}\\\")\\\"\\n\\nBACKUP_SIZE=$(du -h \\\"${BACKUP_DIR}/${BACKUP_NAME}\\\" | cut -f1)\\necho ''\\necho \\\"✓ Backup created: ${BACKUP_NAME}\\\"\\necho \\\"  Size: ${BACKUP_SIZE}\\\"\\necho \\\"  Location: ${BACKUP_DIR}\\\"\\n",
  "description": "Backup a directory with timestamp",
  "group": "workflow",
  "language": "shell",
  "shell": "bash",
  "version": "1.0"
}
```

Usage:
```bash
mcli workflows backup_dir /path/to/directory
mcli workflows backup_dir  # Uses current directory
```

## Example 5: Network Diagnostics

Create `~/.mcli/workflows/network_check.json`:

```json
{
  "name": "network_check",
  "code": "#!/usr/bin/env bash\\n\\nset -euo pipefail\\n\\necho '🌐 Network Diagnostics'\\necho '━━━━━━━━━━━━━━━━━━━━'\\necho ''\\n\\n# Public IP\\necho '📍 Public IP:'\\ncurl -s ifconfig.me || echo 'Unable to fetch'\\necho ''\\necho ''\\n\\n# DNS Check\\necho '🔍 DNS Resolution:'\\nfor host in google.com github.com; do\\n    if host \\\"$host\\\" &>/dev/null; then\\n        echo \\\"  ✓ $host\\\"\\n    else\\n        echo \\\"  ✗ $host\\\"\\n    fi\\ndone\\necho ''\\n\\n# Ping test\\necho '📡 Connectivity:'\\nfor target in 8.8.8.8 1.1.1.1; do\\n    if ping -c 1 -W 2 \\\"$target\\\" &>/dev/null; then\\n        echo \\\"  ✓ $target reachable\\\"\\n    else\\n        echo \\\"  ✗ $target unreachable\\\"\\n    fi\\ndone\\necho ''\\n\\n# Active connections\\necho '🔌 Active Connections:'\\nnetstat -an 2>/dev/null | grep ESTABLISHED | wc -l | xargs echo '  Count:'\\n",
  "description": "Run network diagnostics and connectivity tests",
  "group": "workflow",
  "language": "shell",
  "shell": "bash",
  "version": "1.0"
}
```

Usage:
```bash
mcli workflows network_check
```

## Creating Shell Workflows

### Method 1: Using `mcli workflow add`

```bash
# Interactive mode
mcli workflow add

# Follow prompts:
# - Name: my_script
# - Language: shell
# - Shell type: bash
# - Code: (paste your script)
# - Description: What it does
```

### Method 2: Using `mcli workflow import`

```bash
# Create a shell script first
cat > /tmp/my_script.sh <<'EOF'
#!/usr/bin/env bash
echo "Hello from shell!"
EOF

# Import it
mcli workflow import /tmp/my_script.sh
```

### Method 3: Manual JSON Creation

1. Create the JSON file:
```bash
cat > ~/.mcli/workflows/my_workflow.json <<'EOF'
{
  "name": "my_workflow",
  "code": "#!/usr/bin/env bash\n\necho 'Hello World!'\n",
  "description": "My custom workflow",
  "group": "workflow",
  "language": "shell",
  "shell": "bash",
  "version": "1.0"
}
EOF
```

2. Update the lockfile:
```bash
mcli lock update -g
```

## Tips for Shell Workflows

### 1. **Use `set -euo pipefail`**
Always include error handling at the top:
```bash
#!/usr/bin/env bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures
```

### 2. **Handle Arguments**
Shell workflows can accept arguments:
```bash
#!/usr/bin/env bash
set -euo pipefail

ARG1="${1:-default_value}"
ARG2="${2:-}"

if [ -z "$ARG2" ]; then
    echo "Usage: $0 <arg1> <arg2>"
    exit 1
fi
```

### 3. **Use Colors for Output**
Make output readable with colors:
```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Success!${NC}"
echo -e "${RED}Error!${NC}"
```

### 4. **Escape Special Characters in JSON**
When writing code in JSON:
- Use `\\n` for newlines
- Use `\\\\` for single backslash
- Use `\\\"` for quotes inside the code string

### 5. **Test Shell Scripts Before Converting**
Test your script independently first:
```bash
bash /tmp/my_script.sh
# If it works, then convert to workflow
```

### 6. **Add Comments and Documentation**
```bash
#!/usr/bin/env bash
# Purpose: What this script does
# Usage: script_name [args]
# Author: Your name
# Date: 2025-01-01

set -euo pipefail
```

## Common Use Cases

### System Administration
- Log rotation and cleanup
- Service health checks
- Security audits
- Backup automation

### Development
- Build automation
- Test execution
- Code formatting
- Git operations

### DevOps
- Container management
- Deployment scripts
- Environment setup
- CI/CD integration

### Monitoring
- Resource usage tracking
- Alert generation
- Performance metrics
- Status dashboards

## Verification

After creating a shell workflow, verify it:

```bash
# List all workflows
mcli workflows

# Check if your workflow appears
mcli workflows | grep your_workflow_name

# Verify code validity
mcli lock verify -g --code

# Test execution
mcli workflows your_workflow_name
```

## Troubleshooting

### Workflow doesn't appear in `mcli workflows` list

1. Check the JSON syntax:
```bash
python3 -m json.tool ~/.mcli/workflows/your_workflow.json
```

2. Verify the language field:
```json
"language": "shell"  // Must be "shell", not "bash"
```

3. Update the lockfile:
```bash
mcli lock update -g
```

4. Validate with code check:
```bash
mcli lock verify -g --code
```

### Script fails to execute

1. Test the shell script independently:
```bash
# Extract code from JSON and test
python3 -c "import json; print(json.load(open('~/.mcli/workflows/your_workflow.json'))['code'])" | bash
```

2. Check for syntax errors:
```bash
bash -n your_script.sh
```

3. Add debugging:
```bash
#!/usr/bin/env bash
set -euxo pipefail  # Add 'x' for debug output
```

## Comparison: Shell vs Python Workflows

| Aspect | Shell Workflows | Python Workflows |
|--------|----------------|------------------|
| **Best For** | System tasks, quick scripts | Complex logic, data processing |
| **Syntax** | Bash/shell commands | Python + Click decorators |
| **Dependencies** | System commands | Python packages |
| **Arguments** | Positional args `$1, $2` | Click options/arguments |
| **Error Handling** | Exit codes, set -e | Try/except blocks |
| **Portability** | Varies by shell | Python version dependent |
| **Learning Curve** | Low for sysadmins | Low for Python devs |

## Advanced: Converting Python to Shell

If you have a Python workflow and want to convert it to shell:

```python
# Python workflow
import click

@click.command()
@click.option('--name', default='World')
def hello(name):
    click.echo(f'Hello {name}!')
```

Equivalent shell workflow:
```bash
#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-World}"
echo "Hello ${NAME}!"
```

## Next Steps

- Read [Workflow Management Guide](./WORKFLOW_MANAGEMENT.md)
- Learn about [Custom Commands](./CUSTOM_COMMANDS.md)
- Explore [Lockfile System](./LOCKFILE.md)
- Check out existing workflows: `ls ~/.mcli/workflows/`

## Resources

- [Advanced Bash Scripting Guide](https://tldp.org/LDP/abs/html/)
- [ShellCheck](https://www.shellcheck.net/) - Shell script linter
- [Bash Best Practices](https://bertvv.github.io/cheat-sheets/Bash.html)

---

**Last Updated:** 2025-11-01
