# MCLI - Portable Workflow Framework

**Transform any script into a versioned, portable, schedulable workflow command.**

MCLI is a modular CLI framework that lets you write scripts once and run them anywhere - as interactive commands, scheduled jobs, or background daemons. Your workflows live in `~/.mcli/commands/`, are versioned via lockfile, and completely decoupled from the engine source code.

## 🎯 Core Philosophy

Write a script. Store it. Version it. Run it anywhere. Schedule it. Share it.

No coupling to the engine. No vendor lock-in. Just portable workflows that work.

## ⚡ Quick Start

### Installation

```bash
# Install from PyPI
pip install mcli-framework

# Or with UV (recommended)
uv pip install mcli-framework
```

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
mcli commands import-script my_task.py --name my-task --group workflow

# Run it
mcli workflow my-task --message "Hi"
```

#### Method 2: Interactive Creation

```bash
# Create workflow interactively
mcli commands add my-task --group workflow

# Edit in your $EDITOR, then run
mcli workflow my-task
```

## 📦 Workflow System Features

### 1. **Create Workflows**

Multiple ways to create workflows:

```bash
# Import from existing Python script
mcli commands import-script script.py --name my-workflow --group workflow

# Create new workflow interactively
mcli commands add my-workflow --group workflow --description "Does something useful"

# List all workflows
mcli commands list-custom
```

### 2. **Edit & Manage Workflows**

```bash
# Edit workflow in $EDITOR
mcli commands edit my-workflow

# Show workflow details
mcli commands info my-workflow

# Search workflows
mcli commands search "pdf"

# Remove workflow
mcli commands remove my-workflow
```

### 3. **Export & Import (Portability)**

Share workflows across machines or with your team:

```bash
# Export all workflows to JSON
mcli commands export my-workflows.json

# Import on another machine
mcli commands import my-workflows.json

# Export single workflow to Python script
mcli commands export-script my-workflow --output my_workflow.py
```

Your workflows are just JSON files in `~/.mcli/commands/`:

```bash
$ ls ~/.mcli/commands/
pdf-processor.json
data-sync.json
git-commit.json
commands.lock.json  # Version lockfile
```

### 4. **Version Control with Lockfile**

MCLI automatically maintains a lockfile for reproducibility:

```bash
# Update lockfile with current workflow versions
mcli commands update-lockfile

# Verify workflows match lockfile
mcli commands verify
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
git add ~/.mcli/commands/commands.lock.json ~/.mcli/commands/*.json
git commit -m "Update workflows"

# On another machine
git pull
mcli commands verify  # Ensures consistency
```

### 5. **Run as Daemon or Scheduled Task**

Workflows aren't coupled to the engine - run them however you want:

#### As a Daemon:

```bash
# Start workflow as background daemon
mcli workflow daemon start my-task-daemon --workflow my-task

# Check daemon status
mcli workflow daemon status

# Stop daemon
mcli workflow daemon stop my-task-daemon
```

#### As Scheduled Task:

```bash
# Schedule workflow to run every hour
mcli workflow scheduler add \
  --name hourly-sync \
  --schedule "0 * * * *" \
  --workflow my-task

# List scheduled workflows
mcli workflow scheduler list

# View logs
mcli workflow scheduler logs hourly-sync
```

## 🎨 Real-World Workflow Examples

### Example 1: PDF Processor

```bash
# Create PDF processing workflow
mcli commands import-script pdf_tool.py --name pdf --group workflow

# Use it
mcli workflow pdf extract ~/Documents/report.pdf
mcli workflow pdf compress ~/Documents/*.pdf --output compressed/
mcli workflow pdf split large.pdf --pages 10
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

mcli commands import-script sync.py --name sync --group workflow

# Run manually
mcli workflow sync backup ~/data remote:backup

# Or schedule it
mcli workflow scheduler add \
  --name nightly-backup \
  --schedule "0 2 * * *" \
  --workflow "sync backup ~/data remote:backup"
```

### Example 3: Git Commit Helper

```bash
# Already included as built-in workflow
mcli workflow git-commit

# Or create your own variant
mcli commands export-script git-commit --output my_git_helper.py
# Edit my_git_helper.py to customize
mcli commands import-script my_git_helper.py --name my-git --group workflow
```

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
mcli workflow --help
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
- **politician-trading** - Financial data collection (specialized)

## 💡 Why MCLI?

### The Problem

You write scripts. They work. Then:
- ❌ Can't remember where you saved them
- ❌ Hard to share with team members
- ❌ No version control or change tracking
- ❌ Coupling to specific runners or frameworks
- ❌ No easy way to schedule or daemonize

### The MCLI Solution

- ✅ **Centralized Storage**: All workflows in `~/.mcli/commands/`
- ✅ **Portable**: Export/import as JSON, share anywhere
- ✅ **Versioned**: Lockfile for reproducibility
- ✅ **Decoupled**: Zero coupling to engine source code
- ✅ **Flexible Execution**: Run interactively, scheduled, or as daemon
- ✅ **Discoverable**: Tab completion, search, info commands

## 📚 Advanced Features

### Shell Completion

```bash
# Install completion for your shell
mcli completion install

# Now use tab completion
mcli workflow <TAB>          # Shows all workflows
mcli workflow pdf <TAB>      # Shows pdf subcommands
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

- **Installation**: See [Installation Guide](docs/setup/INSTALLATION.md)
- **Workflows**: Full workflow documentation (this README)
- **Shell Completion**: See [Shell Completion Guide](docs/features/SHELL_COMPLETION.md)
- **Contributing**: See [Contributing Guide](CONTRIBUTING.md)

## 🎯 Common Use Cases

### Use Case 1: Daily Automation Scripts

```bash
# Create your daily automation
mcli commands add daily-tasks --group workflow
# Add your tasks in $EDITOR
mcli workflow scheduler add --name daily --schedule "0 9 * * *" --workflow daily-tasks
```

### Use Case 2: Team Workflow Sharing

```bash
# On your machine
mcli commands export team-workflows.json

# Share file with team
# On teammate's machine
mcli commands import team-workflows.json
mcli commands verify  # Ensure consistency
```

### Use Case 3: CI/CD Integration

```bash
# In your CI pipeline
- pip install mcli-framework
- mcli commands import ci-workflows.json
- mcli workflow build-and-test
- mcli workflow deploy --env production
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
4. Export it: `mcli commands export my-workflow.json`
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
mcli commands add my-first-workflow --group workflow
```
