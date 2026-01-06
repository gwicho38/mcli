# MCLI - Universal Script Runner & Workflow Framework

[![codecov](https://codecov.io/gh/gwicho38/mcli/branch/main/graph/badge.svg)](https://codecov.io/gh/gwicho38/mcli)
[![Tests](https://github.com/gwicho38/mcli/actions/workflows/ci.yml/badge.svg)](https://github.com/gwicho38/mcli/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/gwicho38/mcli/blob/main/LICENSE)

**Run any script, anywhere, with intelligent tab completion. No registration required.**

MCLI is a universal script runner and workflow framework. Execute any Python, Shell, or Jupyter notebook file directly with `mcli run ./script.py` - or register scripts as versioned workflows for scheduling, daemonization, and team sharing. Your workflows live in `~/.mcli/workflows/`, are versioned via lockfile, and completely decoupled from the engine source code.

## 🎯 Core Philosophy

**Run first. Register later.** Execute any script instantly with intelligent tab completion, then optionally register it as a versioned workflow for advanced features like scheduling and sharing.

No coupling to the engine. No vendor lock-in. Just portable workflows that work.

## 🚀 Run Any Script - Zero Configuration

MCLI is now a **universal script runner** with intelligent file path completion:

```bash
# Run any script directly - no registration needed!
mcli run ./backup.py --target /data
mcli run ./deploy.sh production
mcli run ./.mcli/workflows/analysis.ipynb

# Intelligent tab completion shows all files and directories
mcli run ./<TAB>
# Shows: ./scripts/, ./.mcli/, ./backup.py, ./README.md

# Navigate hidden directories like .mcli
mcli run ./.mcli/<TAB>
# Shows: ./.mcli/workflows/, ./.mcli/commands/

# Execute notebooks directly
mcli run ./notebooks/analysis.ipynb cell-1
```

**Supported file types:**
- **Python scripts** (`.py`) - Executed with `python`
- **Shell scripts** (`.sh`, `.bash`, `.zsh`) - Executed directly (auto-made executable)
- **Jupyter notebooks** (`.ipynb`) - Loaded as command groups with cells as subcommands
- **Any executable** - Runs if executable permission is set

**Key features:**
- ✅ **Zero registration** - Run any script immediately
- ✅ **Tab completion** - Intelligent file path autocomplete with hidden directory support
- ✅ **Direct execution** - No need to import or register first
- ✅ **Still portable** - Optionally register scripts as workflows for advanced features

See [File Path Completion Guide](docs/features/FILE_PATH_COMPLETION.md) for complete documentation.

## 🚀 Visual Workflow Editing

Edit your workflow JSON files like Jupyter notebooks with our VSCode extension!

[![VSCode Extension](https://img.shields.io/badge/VSCode-Extension-blue?logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=gwicho38.mcli-framework)
[![Visual Editing](https://img.shields.io/badge/workflows-visual%20editing-brightgreen)](https://github.com/gwicho38/mcli/tree/main/vscode-extension)

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
code --install-extension vscode-extension/mcli-framework-1.0.3.vsix
```

**Learn More:**
- [Extension README](https://github.com/gwicho38/mcli/blob/main/vscode-extension/README.md) - Features and usage
- [Installation Guide](https://github.com/gwicho38/mcli/blob/main/vscode-extension/INSTALL.md) - Detailed setup
- [Workflow Notebooks Docs](https://github.com/gwicho38/mcli/blob/main/docs/workflow-notebooks.md) - Complete guide

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

# 2. Sync scripts to lockfile (auto-runs on startup)
mcli sync update -g

# 3. Run it!
mcli run -g backup
```

**Supported Languages**: Python, Bash, JavaScript, TypeScript, Ruby, Perl, Lua

**Key Features**:
- ✅ Auto-detect language from shebang or extension
- ✅ Extract metadata from `@-prefixed` comments
- ✅ Keep scripts as source of truth (JSON is auto-generated)
- ✅ File watcher for real-time sync (`MCLI_WATCH_SCRIPTS=true`)

See [Script Sync Documentation](https://github.com/gwicho38/mcli/blob/main/docs/SCRIPT_SYNC_SYSTEM.md) for details.

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

#### Method 1: Drop a Script

```bash
# Write your script directly to workflows directory
cat > ~/.mcli/workflows/my-task.py << 'EOF'
#!/usr/bin/env python
# @description: My custom workflow
# @version: 1.0.0

import click

@click.command()
@click.option('--message', default='Hello', help='Message to display')
def app(message):
    """My custom workflow"""
    click.echo(f"{message} from my workflow!")

if __name__ == "__main__":
    app()
EOF

# Run it
mcli run -g my-task --message "Hi"
```

#### Method 2: Interactive Creation

```bash
# Create workflow interactively
mcli new my-task

# Edit in your $EDITOR, then run
mcli run my-task
```

## 📦 Workflow System Features

### 1. **Create Workflows**

Multiple ways to create workflows:

```bash
# Create new workflow interactively (opens in $EDITOR)
mcli new my-workflow

# Or drop a script directly into workflows directory
cp script.py ~/.mcli/workflows/

# List all workflows
mcli list -g        # Global workflows
mcli list           # Local workflows (in git repo)
```

### 2. **Edit & Manage Workflows**

```bash
# Edit workflow in $EDITOR
mcli edit my-workflow

# Search workflows by name or description
mcli search "backup"

# Remove workflow
mcli rm my-workflow
```

### 3. **Portability**

Your workflows are just script files in `~/.mcli/workflows/`:

```bash
$ ls ~/.mcli/workflows/
backup.py
data-sync.sh
git-commit.py
commands.lock.json  # Version lockfile
```

Share workflows by copying the files or using IPFS sync (see below).

### 4. **Version Control with Lockfile**

MCLI automatically maintains a lockfile for reproducibility:

```bash
# Update lockfile with current workflow versions
mcli sync update

# Show lockfile status
mcli sync status

# Show differences between scripts and lockfile
mcli sync diff
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
git add ~/.mcli/workflows/commands.lock.json ~/.mcli/workflows/*.py ~/.mcli/workflows/*.sh
git commit -m "Update workflows"

# On another machine
git pull
mcli sync status  # Check consistency
```

### 5. **IPFS Cloud Sync (Immutable & Free)**

Share workflows globally using IPFS - zero configuration, immutable storage:

```bash
# Push your workflows to IPFS
mcli sync push -g -d "Production workflows v1.0"
# → Returns: QmXyZ123... (immutable CID)

# Anyone can pull your exact workflow state
mcli sync pull QmXyZ123...

# View sync history
mcli sync history

# Verify a CID is accessible
mcli sync verify QmXyZ123...
```

**Features:**
- ✅ **Zero config**: No accounts or API keys needed
- ✅ **Immutable**: CID guarantees content authenticity
- ✅ **Decentralized**: No single point of failure
- ✅ **Free forever**: Community-hosted IPFS gateways
- ✅ **Shareable**: Anyone can retrieve via CID

**Use Cases:**
- Share command sets with team members
- Distribute workflows to community
- Create immutable workflow snapshots
- Backup workflows to decentralized storage

**Note:** The current implementation uses public IPFS gateways which may have rate limits. For production use, consider running your own IPFS node or using a pinning service like Pinata or web3.storage.

**Migration Helper:**

Migrate your workflows to IPFS in one command:

```bash
# Migrate directory structure AND push to IPFS
mcli self migrate --to-ipfs -d "Production migration"
# → Moves commands/ to workflows/ AND pushes to IPFS

# Just push existing workflows to IPFS
mcli sync push -g -d "Production v1.0"
```

### 6. **Run Workflows Anywhere**

Workflows are just script files - run them however you want:

```bash
# Run directly with mcli
mcli run -g my-task

# Or run the script directly
python ~/.mcli/workflows/my-task.py

# Schedule with cron
crontab -e
# Add: 0 * * * * mcli run -g my-task

# Run in background with nohup
nohup mcli run -g my-task &
```

## 🎨 Real-World Workflow Examples

### Example 1: PDF Processor

```bash
# Drop your PDF processing script into workflows
cp pdf_tool.py ~/.mcli/workflows/pdf.py

# Use it
mcli run -g pdf extract ~/Documents/report.pdf
mcli run -g pdf compress ~/Documents/*.pdf --output compressed/
mcli run -g pdf split large.pdf --pages 10
```

### Example 2: Data Sync Workflow

```bash
# Create sync workflow directly in workflows directory
cat > ~/.mcli/workflows/sync.py << 'EOF'
#!/usr/bin/env python
# @description: Multi-cloud sync workflow
# @version: 1.0.0

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

if __name__ == "__main__":
    app()
EOF

# Run manually
mcli run -g sync backup ~/data remote:backup
```

### Example 3: Git Commit Helper

```bash
# Create a custom git helper
mcli new -g git-helper

# Edit it in your $EDITOR, then run it
mcli run -g git-helper
```

## 🔧 Workflow Structure

Each workflow is a native script file (Python, Bash, etc.) with metadata in comments:

```python
#!/usr/bin/env python
# @description: Does something useful
# @version: 1.0.0
# @author: you@example.com
# @tags: utility, automation

import click

@click.command()
def app():
    """My workflow command"""
    click.echo('Hello!')

if __name__ == "__main__":
    app()
```

Or as a shell script:

```bash
#!/usr/bin/env bash
# @description: Does something useful
# @version: 1.0.0
# @requires: curl, jq

echo "Hello from my workflow!"
```

## 🚀 Example Workflows

MCLI ships with example workflows in the global directory. List them with:

```bash
mcli list -g
```

Common workflow categories:
- **backup** - File and data backup scripts
- **clean** - System cleanup utilities
- **modeling** - ML training and prediction commands
- **archive** - File archiving and organization

Create your own workflows to extend the available commands.

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
- ✅ **Portable**: Native scripts, share via IPFS or git
- ✅ **Versioned**: Lockfile for reproducibility
- ✅ **Decoupled**: Zero coupling to engine source code
- ✅ **Flexible Execution**: Run directly, via cron, or as background process
- ✅ **Discoverable**: Tab completion, search, list commands

## 📚 Using MCLI as a Library

MCLI isn't just a CLI tool - it's a powerful Python library for building workflow automation systems!

```python
from mcli.lib.custom_commands import get_command_manager

# Create commands programmatically
manager = get_command_manager()
manager.save_command(
    name="backup",
    code="import click\n@click.command()...",
    description="Automated backup workflow"
)

# Discover and execute commands
from mcli.lib.discovery.command_discovery import ClickCommandDiscovery
commands = ClickCommandDiscovery().discover_all_commands()
```

**📖 Complete Documentation:**
- **[SDK Documentation](docs/SDK.md)** - Comprehensive API reference and usage guide
- **[Library Usage Example](examples/demo_library_usage.py)** - Complete working example
- **[Custom Commands Guide](docs/custom-commands.md)** - Workflow management

**Features for Library Users:**
- ✅ Command creation and discovery APIs
- ✅ Workflow scheduling and automation
- ✅ Configuration and logging utilities
- ✅ Script synchronization system
- ✅ Performance optimization tools
- ✅ Database and caching integrations
- ✅ Internal utilities (file ops, auth, Redis, LSH client, etc.)

## 📚 Advanced Features

### Shell Completion

```bash
# Install completion for your shell
mcli self completion install

# Now use tab completion
mcli run <TAB>                # Shows all workflows
mcli run pdf <TAB>            # Shows pdf subcommands
```

### Self-Management

```bash
# Check version
mcli self version

# Update MCLI to latest version
mcli self update

# View health and performance
mcli self health
mcli self performance
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

- **📚 Documentation Index**: [Complete Documentation Index](https://github.com/gwicho38/mcli/blob/main/docs/INDEX.md) - All docs organized by category
- **Installation**: See [Installation Guide](https://github.com/gwicho38/mcli/blob/main/docs/setup/INSTALL.md)
- **Workflows**: Full workflow documentation (this README)
- **Shell Completion**: See [Shell Completion Guide](https://github.com/gwicho38/mcli/blob/main/docs/features/SHELL_COMPLETION.md)
- **Testing**: See [Testing Guide](https://github.com/gwicho38/mcli/blob/main/docs/development/TESTING.md)
- **Contributing**: See [Contributing Guide](https://github.com/gwicho38/mcli/blob/main/docs/CONTRIBUTING.md)
- **Release Notes**: See [Latest Release (8.0.3)](https://github.com/gwicho38/mcli/blob/main/docs/releases/8.0.3.md)
- **Code of Conduct**: See [Code of Conduct](https://github.com/gwicho38/mcli/blob/main/docs/CODE_OF_CONDUCT.md)
- **Changelog**: See [Changelog](https://github.com/gwicho38/mcli/blob/main/docs/CHANGELOG.md)

## 🎯 Common Use Cases

### Use Case 1: Daily Automation Scripts

```bash
# Create your daily automation
mcli new -g daily-tasks  # Add your tasks in $EDITOR

# Schedule with cron
crontab -e
# Add: 0 9 * * * mcli run -g daily-tasks
```

### Use Case 2: Team Workflow Sharing

```bash
# On your machine - push workflows to IPFS
mcli sync push -g -d "Team workflows v1.0"
# → Returns: QmXyZ123... (share this CID)

# On teammate's machine
mcli sync pull QmXyZ123...
mcli sync status  # Verify workflows loaded
```

### Use Case 3: CI/CD Integration

```bash
# In your CI pipeline
- pip install mcli-framework
- mcli sync pull $WORKFLOW_CID  # Pull from IPFS
- mcli run -g build-and-test
- mcli run -g deploy --env production
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
3. Create your workflow script
4. Add it to `examples/` or document it
5. Submit PR with your workflow

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
mcli new my-first-workflow
```
