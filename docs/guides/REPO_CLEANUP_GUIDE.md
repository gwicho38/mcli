# Repository Cleanup Command - Quick Start Guide

## What is it?

The `repo-cleanup` workflow command helps you:
1. **Organize scattered documentation** files into a clean `docs/` directory structure
2. **Clean git repository history** using BFG Repo-Cleaner to remove sensitive files or large blobs

## Quick Start

### 1. Organize Documentation

```bash
# Preview what would be organized (recommended first step)
mcli workflow repo-cleanup docs --dry-run

# Organize docs with automatic categorization
mcli workflow repo-cleanup docs --categorize

# Organize docs in a specific project
mcli workflow repo-cleanup docs --target-dir ~/repos/myproject
```

### 2. Clean Git History with BFG

```bash
# First, download BFG
brew install bfg
# Or download from: https://rtyley.github.io/bfg-repo-cleaner/

# Preview cleanup (always do this first!)
mcli workflow repo-cleanup bfg \
  --bfg-jar $(brew --prefix)/bin/bfg.jar \
  --bfg-options "--delete-files *.log" \
  --dry-run

# Execute cleanup
mcli workflow repo-cleanup bfg \
  --bfg-jar $(brew --prefix)/bin/bfg.jar \
  --bfg-options "--delete-files *.log"

# Complete the cleanup
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

### 3. Full Cleanup (Documentation + Git)

```bash
# Do everything at once
mcli workflow repo-cleanup full --categorize --dry-run
```

## Common Use Cases

### Use Case 1: Clean Up Project Documentation

**Problem**: Documentation files scattered across your repository (README.md, INSTALL.md, API.md, etc.)

**Solution**:
```bash
cd ~/repos/myproject
mcli workflow repo-cleanup docs --categorize
git add docs/
git commit -m "docs: organize documentation into docs/ directory"
git push
```

**Result**: All documentation organized into `docs/` with categories like:
```
docs/
├── guides/
│   ├── INSTALL.md
│   └── TUTORIAL.md
├── api/
│   └── API.md
├── general/
│   └── README.md
└── ...
```

### Use Case 2: Remove Sensitive Files from Git History

**Problem**: Accidentally committed credentials or API keys to git history

**Solution**:
```bash
# Backup first!
cp -r ~/repos/myproject ~/repos/myproject.backup

# Remove the sensitive files
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files '{credentials.json,*.pem,*.key}'"

# Complete cleanup
cd ~/repos/myproject
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

**Result**: Sensitive files removed from entire git history

### Use Case 3: Reduce Repository Size

**Problem**: Repository is too large due to accidentally committed build artifacts or large files

**Solution**:
```bash
# Remove files bigger than 10MB from history
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--strip-blobs-bigger-than 10M"

# Remove specific folders from history
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-folders '{node_modules,dist,build}'"
```

**Result**: Significantly reduced repository size

## Tips & Best Practices

### 1. Always Preview First
```bash
# Use --dry-run to see what would happen
mcli workflow repo-cleanup docs --dry-run
mcli workflow repo-cleanup bfg --bfg-jar ~/tools/bfg.jar --bfg-options "..." --dry-run
```

### 2. Backup Before BFG Operations
```bash
# Simple backup
cp -r ~/repos/myproject ~/repos/myproject.backup

# Or use git clone
git clone ~/repos/myproject ~/repos/myproject-backup
```

### 3. Test on a Clone First
```bash
# Create a test clone
git clone ~/repos/myproject ~/repos/myproject-test
cd ~/repos/myproject-test

# Run BFG cleanup here first
mcli workflow repo-cleanup bfg --bfg-jar ~/tools/bfg.jar --bfg-options "..."

# If successful, repeat on original
```

### 4. Coordinate Force Pushes
```bash
# Warn your team before force pushing
# After BFG cleanup, everyone needs to re-clone or reset
git push --force

# Team members should:
cd ~/repos/myproject
git fetch --all
git reset --hard origin/main
```

### 5. Use Categorization for Large Docs
```bash
# For projects with many docs
mcli workflow repo-cleanup docs --categorize

# For simple projects with few docs
mcli workflow repo-cleanup docs
```

## Supported Document Types

The command automatically detects these file types:
- Markdown (`.md`)
- Plain Text (`.txt`)
- reStructuredText (`.rst`)
- PDF (`.pdf`)
- Word (`.doc`, `.docx`)
- OpenDocument (`.odt`)
- AsciiDoc (`.adoc`)
- Org-mode (`.org`)

## Category Keywords

Documents are categorized based on filename keywords:

| Category | Example Files |
|----------|--------------|
| **guides** | `INSTALL.md`, `TUTORIAL.md`, `QUICKSTART.md` |
| **api** | `API.md`, `API_REFERENCE.md`, `endpoints.md` |
| **development** | `CONTRIBUTING.md`, `ARCHITECTURE.md`, `DEV_GUIDE.md` |
| **deployment** | `DEPLOYMENT.md`, `PRODUCTION.md`, `HOSTING.md` |
| **testing** | `TESTING.md`, `QA.md` |
| **releases** | `CHANGELOG.md`, `RELEASE_NOTES.md`, `VERSION.md` |
| **configuration** | `CONFIG.md`, `SETUP.md`, `INSTALL.md` |
| **troubleshooting** | `TROUBLESHOOTING.md`, `FAQ.md`, `DEBUG.md` |
| **examples** | `EXAMPLES.md`, `DEMO.md`, `SAMPLES.md` |
| **security** | `SECURITY.md`, `AUTH.md` |
| **general** | `README.md` (everything else) |

## Customization

### Exclude Directories
```bash
# Default exclusions
mcli workflow repo-cleanup docs --exclude-dirs "node_modules,.git,venv,env,dist,build,target"

# Add more exclusions
mcli workflow repo-cleanup docs --exclude-dirs "node_modules,.git,vendor,tmp"
```

### BFG Options

Common BFG operations:

```bash
# Delete specific files
--bfg-options "--delete-files 'filename.ext'"

# Delete files by pattern
--bfg-options "--delete-files '{*.log,*.tmp}'"

# Delete folders
--bfg-options "--delete-folders 'folder-name'"

# Strip large blobs
--bfg-options "--strip-blobs-bigger-than 100M"

# Replace text/passwords
--bfg-options "--replace-text passwords.txt"
```

## Troubleshooting

### "Command not found"
```bash
# Check if installed
mcli commands list | grep repo-cleanup

# Check file exists
ls -la ~/.mcli/commands/repo-cleanup.json

# Reinstall mcli if needed
cd ~/repos/mcli && uv tool install -e .
```

### "No documentation files found"
```bash
# Check what docs exist
find . -name "*.md" -o -name "*.txt"

# Try with minimal exclusions
mcli workflow repo-cleanup docs --exclude-dirs ".git"
```

### "Java not found" (for BFG)
```bash
# Install Java
brew install openjdk

# Verify installation
java -version

# Install BFG
brew install bfg
```

### "Git history corrupted" (after BFG)
```bash
# Restore from backup
rm -rf ~/repos/myproject
cp -r ~/repos/myproject.backup ~/repos/myproject

# Or reset from remote
git fetch --all
git reset --hard origin/main
```

## Getting Help

```bash
# Command help
mcli workflow repo-cleanup --help
mcli workflow repo-cleanup docs --help
mcli workflow repo-cleanup bfg --help
mcli workflow repo-cleanup full --help

# Full documentation
cat ~/repos/mcli/docs/features/REPO_CLEANUP.md

# File issues
gh issue create --repo ~/repos/mcli
```

## Examples Gallery

### Example 1: Simple Documentation Organization
```bash
$ cd ~/repos/myproject
$ mcli workflow repo-cleanup docs --dry-run

📚 Organizing documentation in: /Users/user/repos/myproject
🚫 Excluding: node_modules, .git, venv, env, dist, build, target
🔍 [DRY RUN] Preview mode - no changes will be made

📄 Found 5 documentation file(s):
  • README.md
  • INSTALL.md
  • API.md
  • CONTRIBUTING.md
  • CHANGELOG.md

📁 [DRY RUN] Would create: docs/

🔄 [DRY RUN] Would move:
  README.md → docs/README.md
  INSTALL.md → docs/INSTALL.md
  API.md → docs/API.md
  CONTRIBUTING.md → docs/CONTRIBUTING.md
  CHANGELOG.md → docs/CHANGELOG.md

✅ [DRY RUN] Would move 5 file(s).
```

### Example 2: Categorized Documentation
```bash
$ mcli workflow repo-cleanup docs --categorize

📚 Organizing documentation in: /Users/user/repos/myproject
🚫 Excluding: node_modules, .git, venv, env, dist, build, target

📄 Found 5 documentation file(s):
  • README.md
  • INSTALL.md
  • API.md
  • CONTRIBUTING.md
  • CHANGELOG.md

📁 Created: docs/

📦 Moving files:
  ✅ README.md → docs/general/README.md
  ✅ INSTALL.md → docs/configuration/INSTALL.md
  ✅ API.md → docs/api/API.md
  ✅ CONTRIBUTING.md → docs/development/CONTRIBUTING.md
  ✅ CHANGELOG.md → docs/releases/CHANGELOG.md

✅ Documentation organization complete. Moved 5 file(s).
```

### Example 3: BFG Cleanup Preview
```bash
$ mcli workflow repo-cleanup bfg \
    --bfg-jar ~/tools/bfg.jar \
    --bfg-options "--delete-files credentials.json" \
    --dry-run

🔧 BFG Repository Cleaning

📦 Repository: /Users/user/repos/myproject
🔨 BFG jar: /Users/user/tools/bfg.jar
⚙️  Options: --delete-files credentials.json

🔍 [DRY RUN] Would execute:
  java -jar /Users/user/tools/bfg.jar --delete-files credentials.json /Users/user/repos/myproject

⚠️  Note: BFG modifies git history. Always backup before running!
```

## Next Steps

1. **Try it out**: Start with `--dry-run` on a test repository
2. **Read the docs**: Check out `/repos/mcli/docs/features/REPO_CLEANUP.md`
3. **Report issues**: File issues at `https://github.com/[username]/mcli/issues`
4. **Improve it**: Contribute enhancements to the mcli repository

---

*Created: 2025-10-29 | Version: 1.0.0*
