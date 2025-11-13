# MCLI - Portable Workflow Framework

[![codecov](https://codecov.io/gh/gwicho38/mcli/branch/main/graph/badge.svg)](https://codecov.io/gh/gwicho38/mcli)
[![Tests](https://github.com/gwicho38/mcli/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/gwicho38/mcli/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Transform any script into a versioned, portable, schedulable workflow command.**

MCLI is a modular CLI framework that lets you write scripts once and run them anywhere - as interactive commands, scheduled jobs, or background daemons. Your workflows live in `~/.mcli/workflows/`, are versioned via lockfile, and completely decoupled from the engine source code.

## 🎯 Core Philosophy

Write a script. Store it. Version it. Run it anywhere. Schedule it. Share it.

No coupling to the engine. No vendor lock-in. Just portable workflows that work.

## 🚀 Visual Workflow Editing

Edit your workflow JSON files like Jupyter notebooks with our VSCode extension!

[![VSCode Extension](https://img.shields.io/badge/VSCode-Extension-blue?logo=visualstudiocode)](vscode-extension/)
[![Visual Editing](https://img.shields.io/badge/workflows-visual%20editing-brightgreen)](vscode-extension/)

**Features:**
- 📝 Cell-based editing (Jupyter-like interface)
- ⚡ Live code execution (Python, Shell, Bash, Zsh, Fish)
- 🎯 Monaco editor with IntelliSense
- 📊 Rich markdown documentation cells
- 💾 Files stay as `.json` (git-friendly)

**Quick Install:**
```bash
# From VSCode Marketplace (pending publication)
code --install-extension gwicho38.mcli-framework

# Or install from VSIX
code --install-extension vscode-extension/mcli-framework-2.0.0.vsix
```

**Learn More:**
- [Extension README](vscode-extension/README.md) - Features and usage
- [Visual Editing Guide](README-VISUAL-EDITING.md) - Quick start
- [Installation Guide](vscode-extension/INSTALL.md) - Detailed setup
- [Workflow Notebooks Docs](docs/workflow-notebooks.md) - Complete guide

## ⚡ Quick Start

### Installation

```bash
# Install from PyPI
pip install mcli-framework

# Or with UV (recommended)
uv pip install mcli-framework
```

### Drop & Run: Simplest Way to Add Commands

MCLI automatically converts any script into a workflow command:

```bash
# 1. Create a script with metadata comments
cat > ~/.mcli/commands/backup.sh <<'EOF'
#!/usr/bin/env bash
# @description: Backup files to S3
# @version: 1.0.0
# @requires: aws-cli

aws s3 sync /data/ s3://my-bucket/backup/
EOF

# 2. Sync scripts to JSON (auto-runs on startup)
mcli workflows sync all

# 3. Run it!
mcli workflows backup
```

**Supported Languages**: Python, Bash, JavaScript, TypeScript, Ruby, Perl, Lua

**Key Features**:
- ✅ Auto-detect language from shebang or extension
- ✅ Extract metadata from `@-prefixed` comments
- ✅ Keep scripts as source of truth (JSON is auto-generated)
- ✅ File watcher for real-time sync (`MCLI_WATCH_SCRIPTS=true`)

See [Script Sync Documentation](docs/SCRIPT_SYNC_SYSTEM.md) for details.

### Initialize Workflows Directory

```bash
# Initialize workflows in current git repository
mcli init

# Or initialize global workflows
mcli init --global

# Initialize with git repository for workflows
mcli init --git
```

This creates a `.mcli/workflows/` directory (local to your repo) or `~/.mcli/workflows/` (global) with:
- README.md with usage instructions
- commands.lock.json for version tracking
- .gitignore for backup files

### Create Your First Workflow

#### Method 1: From a Python Script

```bash
# Write your script
cat > my_task.py << 'EOF'
import click

@click.command()
@click.option('--message', default='Hello', help='Message to display')
def app(message):
    """My custom workflow"""
    click.echo(f"{message} from my workflow!")
EOF

# Import as workflow
mcli workflow import-script my_task.py --name my-task

# Run it
mcli workflowss my-task --message "Hi"
```

#### Method 2: Interactive Creation

```bash
# Create workflow interactively
mcli workflow add my-task

# Edit in your $EDITOR, then run
mcli workflowss my-task
```

## 📦 Workflow System Features

### 1. **Create Workflows**

Multiple ways to create workflows:

```bash
# Import from existing Python script
mcli workflow import-script script.py --name my-workflow
# Create new workflow interactively
mcli workflow add my-workflow --group workflow --description "Does something useful"

# List all workflows
mcli workflow list-custom
```

### 2. **Edit & Manage Workflows**

```bash
# Edit workflow in $EDITOR
mcli workflow edit my-workflow

# Show workflow details
mcli workflow info my-workflow

# Search workflows
mcli workflow search "pdf"

# Remove workflow
mcli workflow remove my-workflow
```

### 3. **Export & Import (Portability)**

Share workflows across machines or with your team:

```bash
# Export all workflows to JSON
mcli workflow export my-workflows.json

# Import on another machine
mcli workflow import my-workflows.json

# Export single workflow to Python script
mcli workflow export-script my-workflow --output my_workflow.py
```

Your workflows are just JSON files in `~/.mcli/workflows/`:

```bash
$ ls ~/.mcli/workflows/
pdf-processor.json
data-sync.json
git-commit.json
commands.lock.json  # Version lockfile
```

### 4. **Version Control with Lockfile**

MCLI automatically maintains a lockfile for reproducibility:

```bash
# Update lockfile with current workflow versions
mcli workflow update-lockfile

# Verify workflows match lockfile
mcli workflow verify
```

Example `commands.lock.json`:

```json
{
  "version": "1.0",
  "generated_at": "2025-10-17T10:30:00Z",
  "commands": {
    "pdf-processor": {
      "name": "pdf-processor",
      "description": "Intelligent PDF processor",
      "group": "workflow",
      "version": "1.2",
      "updated_at": "2025-10-15T14:30:00Z"
    }
  }
}
```

**Version control your workflows:**

```bash
# Add lockfile to git
git add ~/.mcli/workflows/commands.lock.json ~/.mcli/workflows/*.json
git commit -m "Update workflows"

# On another machine
git pull
mcli workflow verify  # Ensures consistency
```

### 5. **Run as Daemon or Scheduled Task**

Workflows aren't coupled to the engine - run them however you want:

#### As a Daemon:

```bash
# Start workflow as background daemon
mcli workflows daemon start my-task-daemon --workflow my-task

# Check daemon status
mcli workflows daemon status

# Stop daemon
mcli workflows daemon stop my-task-daemon
```

#### As Scheduled Task:

```bash
# Schedule workflow to run every hour
mcli workflows scheduler add \
  --name hourly-sync \
  --schedule "0 * * * *" \
  --workflow my-task

# List scheduled workflows
mcli workflows scheduler list

# View logs
mcli workflows scheduler logs hourly-sync
```

## 🎨 Real-World Workflow Examples

### Example 1: PDF Processor

```bash
# Create PDF processing workflow
mcli workflow import-script pdf_tool.py --name pdf
# Use it
mcli workflows pdf extract ~/Documents/report.pdf
mcli workflows pdf compress ~/Documents/*.pdf --output compressed/
mcli workflows pdf split large.pdf --pages 10
```

### Example 2: Data Sync Workflow

```bash
# Create sync workflow
cat > sync.py << 'EOF'
import click
import subprocess

@click.group()
def app():
    """Multi-cloud sync workflow"""
    pass

@app.command()
@click.argument('source')
@click.argument('dest')
def backup(source, dest):
    """Backup data to cloud"""
    subprocess.run(['rclone', 'sync', source, dest])
    click.echo(f"Synced {source} to {dest}")

@app.command()
def status():
    """Check sync status"""
    click.echo("Checking sync status...")
EOF

mcli workflow import-script sync.py --name sync
# Run manually
mcli workflows sync backup ~/data remote:backup

# Or schedule it
mcli workflows scheduler add \
  --name nightly-backup \
  --schedule "0 2 * * *" \
  --workflow "sync backup ~/data remote:backup"
```

### Example 3: Git Commit Helper

```bash
# Already included as built-in workflow
mcli workflows git-commit

# Or create your own variant
mcli workflow export-script git-commit --output my_git_helper.py
# Edit my_git_helper.py to customize
mcli workflow import-script my_git_helper.py --name my-git```

## 🔧 Workflow Structure

Each workflow is a JSON file with this structure:

```json
{
  "name": "my-workflow",
  "group": "workflow",
  "description": "Does something useful",
  "version": "1.0",
  "metadata": {
    "author": "you@example.com",
    "tags": ["utility", "automation"]
  },
  "code": "import click\n\n@click.command()\ndef app():\n    click.echo('Hello!')",
  "updated_at": "2025-10-17T10:00:00Z"
}
```

## 🚀 Built-in Workflows

MCLI comes with powerful built-in workflows:

```bash
mcli workflows --help
```

Available workflows:
- **pdf** - Intelligent PDF processing (extract, compress, split, merge)
- **clean** - Enhanced Mac system cleaner
- **emulator** - Android/iOS emulator management
- **git-commit** - AI-powered commit message generation
- **scheduler** - Cron-like job scheduling
- **daemon** - Process management and daemonization
- **redis** - Redis cache management
- **videos** - Video processing and overlay removal
- **sync** - Multi-cloud synchronization
- **politician-trading** - Now available as standalone package: [politician-trading-tracker](https://github.com/gwicho38/politician-trading-tracker)

## 💡 Why MCLI?

### The Problem

You write scripts. They work. Then:
- ❌ Can't remember where you saved them
- ❌ Hard to share with team members
- ❌ No version control or change tracking
- ❌ Coupling to specific runners or frameworks
- ❌ No easy way to schedule or daemonize

### The MCLI Solution

- ✅ **Centralized Storage**: All workflows in `~/.mcli/workflows/`
- ✅ **Portable**: Export/import as JSON, share anywhere
- ✅ **Versioned**: Lockfile for reproducibility
- ✅ **Decoupled**: Zero coupling to engine source code
- ✅ **Flexible Execution**: Run interactively, scheduled, or as daemon
- ✅ **Discoverable**: Tab completion, search, info commands

## 📚 Advanced Features

### Shell Completion

```bash
# Install completion for your shell
mcli self completion install

# Now use tab completion
mcli workflows <TAB>          # Shows all workflows
mcli workflows pdf <TAB>      # Shows pdf subcommands
```

### AI Chat Integration

```bash
# Chat with AI about your workflows
mcli chat

# Configure AI providers
export OPENAI_API_KEY=your-key
export ANTHROPIC_API_KEY=your-key
```

### Self-Update

```bash
# Update MCLI to latest version
mcli self update

# Check version
mcli version
```

## 🛠️ Development

### For Development or Customization

```bash
# Clone repository
git clone https://github.com/gwicho38/mcli.git
cd mcli

# Setup with UV
uv venv
uv pip install -e ".[dev]"

# Run tests
make test

# Build wheel
make wheel
```

## 📖 Documentation

- **📚 Documentation Index**: [Complete Documentation Index](docs/INDEX.md) - All docs organized by category
- **Installation**: See [Installation Guide](docs/setup/INSTALL.md)
- **Workflows**: Full workflow documentation (this README)
- **Shell Completion**: See [Shell Completion Guide](docs/features/SHELL_COMPLETION.md)
- **Testing**: See [Testing Guide](docs/development/TESTING.md)
- **Contributing**: See [Contributing Guide](CONTRIBUTING.md)
- **Release Notes**: See [Latest Release (7.10.2)](docs/releases/7.10.2.md)

## 🎯 Common Use Cases

### Use Case 1: Daily Automation Scripts

```bash
# Create your daily automation
mcli workflow add daily-tasks# Add your tasks in $EDITOR
mcli workflows scheduler add --name daily --schedule "0 9 * * *" --workflow daily-tasks
```

### Use Case 2: Team Workflow Sharing

```bash
# On your machine
mcli workflow export team-workflows.json

# Share file with team
# On teammate's machine
mcli workflow import team-workflows.json
mcli workflow verify  # Ensure consistency
```

### Use Case 3: CI/CD Integration

```bash
# In your CI pipeline
- pip install mcli-framework
- mcli workflow import ci-workflows.json
- mcli workflows build-and-test
- mcli workflows deploy --env production
```

## 📦 Dependencies

### Core (Always Installed)
- **click**: CLI framework
- **rich**: Beautiful terminal output
- **requests**: HTTP client
- **python-dotenv**: Environment management

### Optional Features

All features are included by default as of v7.0.0. For specialized needs:

```bash
# GPU support (CUDA required)
pip install "mcli-framework[gpu]"

# Development tools
pip install "mcli-framework[dev]"
```

## 🤝 Contributing

We welcome contributions! Especially workflow examples.

1. Fork the repository
2. Create feature branch: `git checkout -b feature/awesome-workflow`
3. Create your workflow
4. Export it: `mcli workflow export my-workflow.json`
5. Submit PR with workflow JSON

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Built with [Click](https://click.palletsprojects.com/)
- Styled with [Rich](https://github.com/Textualize/rich)
- Managed with [UV](https://docs.astral.sh/uv/)

---

**Start transforming your scripts into portable workflows today:**

```bash
pip install mcli-framework
mcli workflow add my-first-workflow```
