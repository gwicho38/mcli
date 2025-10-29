# Repository Cleanup Command

## Overview

The `repo-cleanup` workflow command is a comprehensive tool for organizing repository documentation and performing advanced git cleaning operations using BFG (BFG Repo-Cleaner).

## Installation

The command is automatically available as part of the mcli-framework workflow commands. It requires:
- mcli-framework (installed)
- Python 3.7+
- Java (for BFG operations)
- BFG jar file (optional, for git cleaning)

## Features

### Documentation Organization
- Automatically finds and organizes documentation files
- Supports multiple document formats (Markdown, PDF, reStructuredText, etc.)
- Smart categorization by document type (guides, API, development, etc.)
- Preserves directory structure or categorizes by content
- Dry-run mode for previewing changes
- Customizable directory exclusions

### Git Cleaning with BFG
- Integration with BFG Repo-Cleaner for advanced git operations
- Safe dry-run mode to preview changes
- Automatic git repository validation
- Post-cleanup guidance for completing the operation

## Commands

### 1. Organize Documentation (`docs`)

Organizes documentation files into a top-level `docs/` directory.

```bash
mcli workflow repo-cleanup docs [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--target-dir` | Path | Target repository directory (defaults to current directory) |
| `--dry-run` | Flag | Show what would be done without making changes |
| `--categorize` | Flag | Categorize docs by type (guides/, api/, development/, etc.) |
| `--exclude-dirs` | String | Comma-separated list of directories to exclude (default: `node_modules,.git,venv,env,dist,build,target`) |

#### Examples

```bash
# Preview documentation organization
mcli workflow repo-cleanup docs --dry-run

# Organize docs with categorization
mcli workflow repo-cleanup docs --categorize

# Organize docs in a specific repository
mcli workflow repo-cleanup docs --target-dir ~/repos/myproject

# Exclude additional directories
mcli workflow repo-cleanup docs --exclude-dirs "node_modules,.git,venv,custom-dir"
```

#### Supported Document Types

- **Markdown** (`.md`)
- **Plain Text** (`.txt`)
- **reStructuredText** (`.rst`)
- **PDF** (`.pdf`)
- **Word Documents** (`.doc`, `.docx`)
- **OpenDocument** (`.odt`)
- **AsciiDoc** (`.adoc`)
- **Org-mode** (`.org`)

#### Document Categories

When using `--categorize`, documents are automatically sorted into categories based on filename:

| Category | Keywords |
|----------|----------|
| `guides/` | guide, tutorial, howto, getting-started, quickstart, walkthrough |
| `api/` | api, reference, endpoint, swagger, openapi |
| `development/` | dev, develop, contributing, architecture, design |
| `deployment/` | deploy, deployment, production, hosting, infrastructure |
| `testing/` | test, testing, qa, quality |
| `releases/` | release, changelog, version, history |
| `configuration/` | config, configuration, setup, install, installation |
| `troubleshooting/` | troubleshoot, debug, faq, common-issues, known-issues |
| `examples/` | example, examples, sample, demo |
| `security/` | security, auth, authentication, authorization, permissions |
| `general/` | (default for uncategorized documents) |

### 2. BFG Git Cleaning (`bfg`)

Run BFG Repo-Cleaner for advanced git repository cleaning operations.

```bash
mcli workflow repo-cleanup bfg [OPTIONS]
```

#### Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--target-dir` | Path | No | Target repository directory (defaults to current directory) |
| `--bfg-jar` | Path | **Yes** | Path to BFG jar file |
| `--bfg-options` | String | **Yes** | Options to pass to BFG |
| `--dry-run` | Flag | No | Show what would be done without executing |

#### Examples

```bash
# Preview BFG cleanup
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files *.log" \
  --dry-run

# Remove large blobs from history
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--strip-blobs-bigger-than 10M"

# Delete specific files from history
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files '{*.key,*.pem,credentials.json}'"

# Replace passwords in history
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--replace-text passwords.txt"
```

#### Important Notes

- **BFG modifies git history** - always backup your repository before running
- After BFG completes, you must run additional git commands:
  ```bash
  cd <repository>
  git reflog expire --expire=now --all
  git gc --prune=now --aggressive
  git push --force  # Required to update remote
  ```
- BFG is faster than `git filter-branch` and preserves merge commits
- Download BFG from: https://rtyley.github.io/bfg-repo-cleaner/

### 3. Full Cleanup (`full`)

Run complete cleanup: documentation organization + optional BFG git cleaning.

```bash
mcli workflow repo-cleanup full [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--target-dir` | Path | Target repository directory (defaults to current directory) |
| `--bfg-jar` | Path | Path to BFG jar file (optional) |
| `--bfg-options` | String | Options to pass to BFG |
| `--dry-run` | Flag | Show what would be done without making changes |
| `--categorize` | Flag | Categorize docs by type |

#### Examples

```bash
# Full cleanup with dry-run
mcli workflow repo-cleanup full --dry-run

# Full cleanup with categorization
mcli workflow repo-cleanup full --categorize

# Full cleanup with BFG git cleaning
mcli workflow repo-cleanup full \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files *.log" \
  --categorize
```

## Usage Workflows

### Workflow 1: Organize Existing Documentation

Perfect for cleaning up a repository with scattered documentation files.

```bash
# 1. Preview what would be organized
mcli workflow repo-cleanup docs --dry-run

# 2. Review the output and decide on categorization
mcli workflow repo-cleanup docs --dry-run --categorize

# 3. Execute the organization
mcli workflow repo-cleanup docs --categorize

# 4. Commit the changes
git add docs/
git commit -m "docs: organize documentation into docs/ directory"
```

### Workflow 2: Clean Git History

Remove sensitive files or large blobs from git history.

```bash
# 1. Backup your repository
cp -r ~/repos/myproject ~/repos/myproject.backup

# 2. Preview BFG cleanup
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files credentials.json" \
  --dry-run

# 3. Execute BFG cleanup
mcli workflow repo-cleanup bfg \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files credentials.json"

# 4. Complete the cleanup
cd ~/repos/myproject
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Force push to update remote
git push --force
```

### Workflow 3: Complete Repository Cleanup

Organize docs and clean git history in one operation.

```bash
# 1. Backup repository
cp -r ~/repos/myproject ~/repos/myproject.backup

# 2. Preview full cleanup
mcli workflow repo-cleanup full \
  --dry-run \
  --categorize \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files *.log"

# 3. Execute full cleanup
mcli workflow repo-cleanup full \
  --categorize \
  --bfg-jar ~/tools/bfg.jar \
  --bfg-options "--delete-files *.log"

# 4. Complete git cleanup
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Commit and push
git add docs/
git commit -m "docs: organize documentation and clean git history"
git push --force
```

## Configuration

### Customizing Exclusions

You can customize which directories are excluded during documentation scanning:

```bash
# Default exclusions
mcli workflow repo-cleanup docs --exclude-dirs "node_modules,.git,venv,env,dist,build,target"

# Add custom exclusions
mcli workflow repo-cleanup docs --exclude-dirs "node_modules,.git,vendor,tmp,cache"
```

### BFG Configuration

BFG supports many options. Here are common use cases:

```bash
# Remove files by name
--delete-files "filename.ext"

# Remove files by pattern
--delete-files "{*.log,*.tmp,*.cache}"

# Remove folders
--delete-folders "folder-name"

# Strip blobs bigger than X
--strip-blobs-bigger-than 100M

# Replace text/passwords
--replace-text passwords.txt

# Strip blobs with specific IDs
--strip-blobs-with-ids blob-ids.txt
```

## Troubleshooting

### Command Not Found

If `mcli workflow repo-cleanup` is not recognized:

```bash
# Check if command is registered
mcli commands list | grep repo-cleanup

# Verify the JSON file exists
ls -la ~/.mcli/commands/repo-cleanup.json

# Reinstall mcli if needed
cd ~/repos/mcli
uv tool install -e .
```

### No Documentation Found

If the command reports no documentation files:

```bash
# Check what files exist
find . -name "*.md" -o -name "*.txt" -o -name "*.pdf"

# Verify exclusions aren't too broad
mcli workflow repo-cleanup docs --dry-run --exclude-dirs ".git"
```

### BFG Java Not Found

If you get a "Java not found" error:

```bash
# Install Java via Homebrew
brew install openjdk

# Verify Java installation
java -version

# Get BFG jar file
brew install bfg
# Or download from: https://rtyley.github.io/bfg-repo-cleaner/
```

### Git History Issues After BFG

If you have issues after running BFG:

```bash
# Restore from backup
rm -rf ~/repos/myproject
cp -r ~/repos/myproject.backup ~/repos/myproject

# Always test on a clone first
git clone ~/repos/myproject ~/repos/myproject-test
cd ~/repos/myproject-test
# Run BFG cleanup here first
```

## Best Practices

1. **Always use `--dry-run` first** to preview changes before executing
2. **Backup repositories** before running BFG operations
3. **Use categorization** for better documentation organization
4. **Review exclusions** to ensure important directories aren't skipped
5. **Complete git cleanup** after BFG by running the suggested commands
6. **Test on a clone** before running BFG on production repositories
7. **Document changes** in commit messages when reorganizing docs
8. **Coordinate with team** before force-pushing after BFG cleanup

## Contributing

To report issues or suggest improvements:

```bash
# File an issue in the mcli repository
gh issue create --repo ~/repos/mcli --title "repo-cleanup: [issue description]"

# Or manually create an issue at:
# https://github.com/[username]/mcli/issues
```

## Version History

### v1.0.0 (2025-10-29)
- Initial release
- Documentation organization with categorization
- BFG jar integration
- Dry-run mode support
- Multi-format document support
- Customizable exclusions

## License

This command is part of the mcli-framework project and follows the same license.

## See Also

- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [mcli-framework Documentation](../README.md)
- [Workflow Commands Guide](../guides/WORKFLOW_COMMANDS.md)
