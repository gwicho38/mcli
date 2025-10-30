# MCLI Command Structure Migration Guide

**Version**: 7.11.0
**Date**: 2025-10-30

## Overview

MCLI has undergone a significant command structure reorganization to improve clarity and consistency. This guide will help you migrate from the old command structure to the new one.

## Summary of Changes

### Command Group Renaming

| Old Command | New Command | Purpose |
|-------------|-------------|---------|
| `mcli commands` | `mcli workflow` | **Manage** workflows (create, edit, import, export) |
| `mcli workflow` | `mcli workflows` | **Run** workflows (execute workflow commands) |
| `mcli lib secrets` | `mcli workflows secrets` | Secrets management (moved to workflows) |

### What Was Removed

- **`mcli lib` group** - Completely removed
  - `mcli lib secrets` functionality moved to `mcli workflows secrets`

## Detailed Migration

### 1. Workflow Management Commands

These commands are for **creating, editing, and managing** your workflows.

#### OLD → NEW

```bash
# List workflows
mcli commands list-custom          → mcli workflow list
mcli commands list                 → mcli workflow list

# Create workflows
mcli commands add my-task          → mcli workflow add my-task
mcli commands import-script file.py → mcli workflow import-script file.py

# Edit workflows
mcli commands edit my-task         → mcli workflow edit my-task
mcli commands info my-task         → mcli workflow info my-task

# Search workflows
mcli commands search "pdf"         → mcli workflow search "pdf"

# Remove workflows
mcli commands remove my-task       → mcli workflow remove my-task

# Import/Export
mcli commands export workflows.json → mcli workflow export workflows.json
mcli commands import workflows.json → mcli workflow import workflows.json

# Verification
mcli commands verify               → mcli workflow verify
mcli commands update-lockfile      → mcli workflow update-lockfile

# Store operations
mcli commands store sync           → mcli workflow store sync
```

### 2. Running Workflows

These commands are for **executing** your workflows.

#### OLD → NEW

```bash
# Run built-in workflows
mcli workflow pdf extract file.pdf         → mcli workflows pdf extract file.pdf
mcli workflow clean                        → mcli workflows clean
mcli workflow scheduler add my-task        → mcli workflows scheduler add my-task
mcli workflow daemon start my-daemon       → mcli workflows daemon start my-daemon

# Run custom workflows
mcli workflow my-custom-task               → mcli workflows my-custom-task

# Help for workflows
mcli workflow --help                       → mcli workflows --help
mcli workflow pdf --help                   → mcli workflows pdf --help
```

### 3. Secrets Management

Secrets management has moved from `lib` to `workflows`.

#### OLD → NEW

```bash
# Interactive REPL
mcli lib secrets repl                      → mcli workflows secrets --repl

# Set secrets
mcli lib secrets set API_KEY abc123        → mcli workflows secrets --set API_KEY abc123

# Get secrets
mcli lib secrets get API_KEY               → mcli workflows secrets --get API_KEY
mcli lib secrets get API_KEY --show        → mcli workflows secrets --get API_KEY --show

# List secrets
mcli lib secrets list                      → mcli workflows secrets --list
mcli lib secrets list --namespace prod     → mcli workflows secrets --list --namespace prod

# Delete secrets
mcli lib secrets delete API_KEY            → mcli workflows secrets --delete API_KEY

# Export/Import
mcli lib secrets export                    → mcli workflows secrets --export
mcli lib secrets export --output .env      → mcli workflows secrets --export --output .env
mcli lib secrets import .env               → mcli workflows secrets --import-file .env

# Store operations
mcli lib secrets store init                → mcli workflows secrets --store-init
mcli lib secrets store push                → mcli workflows secrets --store-push
mcli lib secrets store pull                → mcli workflows secrets --store-pull
mcli lib secrets store sync                → mcli workflows secrets --store-sync
mcli lib secrets store status              → mcli workflows secrets --store-status
```

## Quick Reference

### New Command Structure

```
mcli
├── version                    # Show version
├── self                       # Self-management (update, completion, etc.)
├── workflow                   # Manage workflows (create, edit, import, export)
│   ├── add                    # Create new workflow
│   ├── edit                   # Edit workflow
│   ├── import                 # Import workflows
│   ├── export                 # Export workflows
│   ├── list                   # List all workflows
│   ├── search                 # Search workflows
│   ├── remove                 # Remove workflow
│   ├── info                   # Show workflow details
│   ├── verify                 # Verify lockfile
│   ├── update-lockfile        # Update lockfile
│   └── store                  # Store operations
└── workflows                  # Run workflows
    ├── secrets                # Secrets management
    ├── pdf                    # PDF processing
    ├── clean                  # System cleanup
    ├── scheduler              # Job scheduling
    ├── daemon                 # Daemon management
    ├── notebook               # Notebook management
    └── [your-custom-workflows]
```

## Backward Compatibility

For a limited time, the old commands are aliased to the new ones:

- `mcli commands` still works (alias for `mcli workflow`)
- `mcli lib secrets` will show a deprecation warning

**These aliases will be removed in version 8.0.0**

## Common Migration Patterns

### Pattern 1: Daily Workflow Management

#### Old Way
```bash
# Create workflow
mcli commands add daily-backup

# Run workflow
mcli workflow daily-backup

# Edit workflow
mcli commands edit daily-backup
```

#### New Way
```bash
# Create workflow
mcli workflow add daily-backup

# Run workflow
mcli workflows daily-backup

# Edit workflow
mcli workflow edit daily-backup
```

### Pattern 2: Secrets in CI/CD

#### Old Way
```bash
# In CI/CD pipeline
mcli lib secrets import production.env
mcli lib secrets get API_KEY --show > api_key.txt
```

#### New Way
```bash
# In CI/CD pipeline
mcli workflows secrets --import-file production.env
mcli workflows secrets --get API_KEY --show > api_key.txt
```

### Pattern 3: Workflow Sharing

#### Old Way
```bash
# Export on machine A
mcli commands export my-workflows.json

# Import on machine B
mcli commands import my-workflows.json

# Run the workflow
mcli workflow my-task
```

#### New Way
```bash
# Export on machine A
mcli workflow export my-workflows.json

# Import on machine B
mcli workflow import my-workflows.json

# Run the workflow
mcli workflows my-task
```

## Benefits of New Structure

1. **Clearer Separation**: `workflow` for management, `workflows` for execution
2. **Consistency**: All workflow-related commands under `workflows`
3. **Simplified**: Removed confusing `lib` group
4. **Intuitive**: Command names match their purpose

## FAQ

### Q: Why was this changed?

**A**: The old structure had several issues:
- `commands` was confusing (everything is a command)
- `workflow` vs `commands` distinction was unclear
- `lib` group was a catch-all that didn't fit the pattern

The new structure makes it clear:
- `mcli workflow` = manage workflows
- `mcli workflows` = run workflows

### Q: Will my scripts break?

**A**: In the short term, no. We provide backward compatibility aliases. However, you should migrate your scripts to the new commands before version 8.0.0.

### Q: What about ~/.mcli/commands/?

**A**: The directory has been renamed to `~/.mcli/workflows/`. Use `mcli self migrate` to automatically move your workflows from the old location to the new one. The system will check both locations for backward compatibility.

### Q: Can I use both old and new commands?

**A**: Yes, during the transition period (versions 7.11.x - 7.x.x). But we recommend migrating to the new structure immediately.

### Q: How do I find all my scripts using old commands?

**A**:
```bash
# Search for old command patterns
grep -r "mcli commands" /path/to/scripts/
grep -r "mcli workflow " /path/to/scripts/  # Note the space after workflow
grep -r "mcli lib secrets" /path/to/scripts/
```

## Automated Migration

### Using `mcli self migrate`

MCLI now includes an automated migration command to help you transition smoothly:

```bash
# Check migration status
mcli self migrate --status

# Preview what will be migrated (dry run)
mcli self migrate --dry-run

# Perform the migration
mcli self migrate

# Force migration (overwrite existing files)
mcli self migrate --force
```

**What it does:**
- Moves all files from `~/.mcli/commands/` to `~/.mcli/workflows/`
- Preserves the lockfile (`commands.lock.json`)
- Creates backups of any existing files if using `--force`
- Shows detailed progress and results

**After migration:**
- Your workflows remain in `~/.mcli/workflows/`
- All commands continue to work as before
- Path references are automatically updated

## Manual Migration Steps

If you prefer to migrate manually or need more control:

```bash
# 1. Backup your current commands
cp -r ~/.mcli/commands ~/.mcli/commands.backup

# 2. Create workflows directory
mkdir -p ~/.mcli/workflows

# 3. Move files
mv ~/.mcli/commands/* ~/.mcli/workflows/

# 4. Verify
ls ~/.mcli/workflows/

# 5. Remove old directory (optional)
rmdir ~/.mcli/commands
```

## Migration Checklist

### Automated (Recommended)
- [ ] Run `mcli self migrate --status` to check what needs migration
- [ ] Run `mcli self migrate` to perform migration
- [ ] Verify workflows still work: `mcli workflow list`
- [ ] Test running a workflow: `mcli workflows <your-workflow>`

### Manual Updates
- [ ] Update all `mcli commands` → `mcli workflow`
- [ ] Update all `mcli workflow <name>` → `mcli workflows <name>`
- [ ] Update all `mcli lib secrets` → `mcli workflows secrets`
- [ ] Test your workflows with new commands
- [ ] Update CI/CD pipelines
- [ ] Update documentation
- [ ] Update shell scripts
- [ ] Update aliases in ~/.bashrc or ~/.zshrc
- [ ] Update team documentation

## Need Help?

- **Documentation**: [docs/INDEX.md](INDEX.md)
- **Issues**: [GitHub Issues](https://github.com/gwicho38/mcli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gwicho38/mcli/discussions)

## Timeline

- **Version 7.11.0**: New command structure introduced, old commands work with aliases
- **Version 7.x.x**: Deprecation warnings for old commands
- **Version 8.0.0**: Old command aliases removed

---

**Last Updated**: 2025-10-30
**Version**: 7.11.0
