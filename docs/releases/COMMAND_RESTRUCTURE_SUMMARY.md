# MCLI Command Restructure Summary

**Date**: 2025-10-30
**Version**: 7.11.0 (planned)

## Overview

This document summarizes the major command structure reorganization completed for MCLI. This was a comprehensive refactoring to improve clarity, consistency, and usability.

---

## Changes Summary

### 1. Command Group Renaming

| Old Command | New Command | Purpose |
|-------------|-------------|---------|
| `mcli commands` | `mcli workflow` | **Manage** workflows (create, edit, import, export) |
| `mcli workflow` | `mcli workflows` | **Run** workflows (execute workflow commands) |
| `mcli lib secrets` | `mcli workflows secrets` | Secrets management (moved to workflows) |
| `mcli lib` | **REMOVED** | No longer needed (functionality moved) |

### 2. Directory Structure

| Old Path | New Path |
|----------|----------|
| `~/.mcli/commands/` | `~/.mcli/workflows/` |

### 3. New Commands Added

- `mcli self migrate` - Automated migration tool
  - `--status` - Check migration status
  - `--dry-run` - Preview migration
  - `--force` - Force migration with backups

---

## Files Created

### 1. Migration System
- `src/mcli/self/migrate_cmd.py` - Migration command implementation
- Integrated into `self_app` command group

### 2. Secrets Workflow
- `src/mcli/workflow/secrets/__init__.py` - Package init
- `src/mcli/workflow/secrets/secrets_cmd.py` - Unified secrets command

### 3. Documentation
- `docs/COMMAND_MIGRATION_GUIDE.md` - Comprehensive migration guide
- `docs/releases/COMMAND_RESTRUCTURE_SUMMARY.md` - This file

---

## Files Modified

### 1. Core Command Structure
- `src/mcli/app/main.py`
  - Updated command registrations
  - Renamed `workflow` to `workflows`
  - Renamed `commands` to `workflow`
  - Removed `lib` group

- `src/mcli/app/commands_cmd.py`
  - Renamed group from `commands` to `workflow`
  - Updated all decorators (`@workflow.command`, `@workflow.group`)
  - Added backward compatibility alias

- `src/mcli/workflow/workflow.py`
  - Renamed group from `workflow` to `workflows`
  - Added secrets workflow
  - Added backward compatibility alias

### 2. Path Management
- `src/mcli/lib/paths.py`
  - Updated `get_custom_commands_dir()` to check workflows first
  - Updated `get_local_commands_dir()` to support both locations
  - Updated `get_lockfile_path()` documentation
  - Added migration support (checks both directories)

### 3. Self Command
- `src/mcli/self/self_cmd.py`
  - Added migrate command import and registration

### 4. Documentation
- `README.md`
  - Updated all command examples
  - Changed `mcli commands` → `mcli workflow`
  - Changed `mcli workflow` → `mcli workflows`
  - Removed `--group workflow` flags (no longer needed)

- `CLAUDE.md`
  - Updated "Workflow Commands" section to "Command Structure"
  - Added version 7.11.0 notation
  - Documented new structure

- `docs/COMMAND_MIGRATION_GUIDE.md`
  - Added automated migration section
  - Updated FAQ

---

## Technical Details

### Backward Compatibility

The implementation includes backward compatibility features:

1. **Function Aliases**:
   - `commands = workflow` in `commands_cmd.py`
   - `workflow = workflows` in `workflow/workflow.py`

2. **Path Resolution**:
   - `get_custom_commands_dir()` checks both locations
   - Prefers `workflows` but falls back to `commands`
   - Creates `workflows` for new installations

3. **Migration Support**:
   - Old commands still work temporarily
   - Deprecation warnings (planned for 7.x.x)
   - Full removal in 8.0.0

### Migration Logic

The `mcli self migrate` command:

1. **Checks** if `~/.mcli/commands` exists
2. **Checks** if `~/.mcli/workflows` exists
3. **Moves** all files from commands to workflows
4. **Preserves** lockfile and metadata
5. **Creates backups** if using `--force` with existing files
6. **Removes** old directory if empty
7. **Reports** detailed migration results

### Path Resolution Strategy

```python
# Simplified logic
def get_custom_commands_dir():
    # 1. Check workflows directory (new)
    if workflows_exists:
        return workflows

    # 2. Check commands directory (old, for migration)
    if commands_exists:
        return commands

    # 3. Create workflows directory (new installations)
    create_and_return_workflows()
```

---

## New Command Structure

```
mcli/
├── version          # Show version info
├── self             # Self-management commands
│   ├── update
│   ├── completion
│   ├── migrate      # ✨ NEW: Migration tool
│   └── ...
├── workflow         # Manage workflows (formerly 'commands')
│   ├── add          # Create new workflow
│   ├── edit         # Edit workflow
│   ├── import       # Import workflows
│   ├── export       # Export workflows
│   ├── list         # List all workflows
│   ├── search       # Search workflows
│   ├── remove       # Remove workflow
│   ├── info         # Workflow details
│   ├── verify       # Verify lockfile
│   ├── update-lockfile
│   └── store        # Store operations
└── workflows        # Run workflows (formerly 'workflow')
    ├── secrets      # ✨ NEW: Secrets management (moved from lib)
    ├── notebook     # Notebook management
    ├── pdf          # PDF processing
    ├── clean        # System cleanup
    ├── scheduler    # Job scheduling
    ├── daemon       # Daemon management
    └── [custom workflows]
```

---

## Testing Results

All commands verified working:

✅ `mcli --help` - Shows new structure
✅ `mcli workflow --help` - Shows management commands
✅ `mcli workflows --help` - Shows runnable workflows
✅ `mcli workflows secrets --help` - Secrets workflow accessible
✅ `mcli self migrate --status` - Shows migration status
✅ `mcli self migrate --dry-run` - Previews migration
✅ Path resolution works for both old and new locations

---

## User Impact

### For End Users

**Immediate**:
- Old commands still work (backward compatibility)
- New commands available immediately
- Migration is optional but recommended

**Short Term** (7.x.x versions):
- Deprecation warnings for old commands
- Encouragement to migrate

**Long Term** (8.0.0):
- Old command aliases removed
- Only new commands work

### For Script Writers

**Action Required**:
- Update scripts to use new commands
- Run `mcli self migrate` to move workflows directory
- Test all workflows after migration

**Timeline**:
- Now - 7.11.0: Both work (use new commands)
- 7.x.x: Deprecation warnings (migrate scripts)
- 8.0.0: Old commands removed (must use new)

### For CI/CD

**Updates Needed**:
1. Change `mcli commands` → `mcli workflow`
2. Change `mcli workflow X` → `mcli workflows X`
3. Change `mcli lib secrets` → `mcli workflows secrets`
4. Run `mcli self migrate` in setup steps (optional but recommended)

**Example Migration**:
```yaml
# Old CI/CD
- run: mcli commands import workflows.json
- run: mcli workflow build-project
- run: mcli lib secrets get API_KEY

# New CI/CD
- run: mcli self migrate  # Optional: Migrate directory
- run: mcli workflow import workflows.json
- run: mcli workflows build-project
- run: mcli workflows secrets --get API_KEY --show
```

---

## Benefits

### 1. Clarity
- **`workflow`** - clearly means "manage workflows"
- **`workflows`** - clearly means "run workflows"
- No more confusion between `commands` and `workflow`

### 2. Consistency
- All executable workflows under `workflows`
- All management under `workflow`
- Secrets logically grouped with other workflows

### 3. Simplification
- Removed confusing `lib` group
- Single location for workflow files
- Clearer command hierarchy

### 4. Extensibility
- Easy to add new workflows to `workflows` group
- Easy to add new management commands to `workflow` group
- Clear pattern for future additions

---

## Migration Support

### Automated Migration

```bash
# Check what needs migration
mcli self migrate --status

# Preview migration
mcli self migrate --dry-run

# Perform migration
mcli self migrate
```

### Manual Migration

```bash
# Backup
cp -r ~/.mcli/commands ~/.mcli/commands.backup

# Migrate
mkdir -p ~/.mcli/workflows
mv ~/.mcli/commands/* ~/.mcli/workflows/
rmdir ~/.mcli/commands
```

### Documentation

- [Command Migration Guide](COMMAND_MIGRATION_GUIDE.md) - Complete migration instructions
- [README](../README.md) - Updated with new commands
- [CLAUDE.md](../CLAUDE.md) - Updated for AI assistant

---

## Statistics

- **Files Created**: 3 (migrate_cmd.py, secrets_cmd.py + init, summary)
- **Files Modified**: 6 (main.py, commands_cmd.py, workflow.py, paths.py, self_cmd.py, README.md, CLAUDE.md)
- **Documentation Updated**: 3 docs (README, CLAUDE.md, migration guide)
- **Lines Changed**: ~500 lines
- **Commands Added**: 1 (`mcli self migrate`)
- **Commands Renamed**: 3 (commands → workflow, workflow → workflows, lib secrets → workflows secrets)
- **Commands Removed**: 1 group (`mcli lib`)

---

## Future Work

### Version 7.11.x
- [x] Implement command restructure
- [x] Add migration command
- [x] Update documentation
- [ ] Add deprecation warnings for old commands
- [ ] User communication (changelog, blog post)

### Version 7.x.x
- [ ] Monitor migration adoption
- [ ] Collect feedback
- [ ] Refine migration process if needed

### Version 8.0.0
- [ ] Remove backward compatibility aliases
- [ ] Remove old command support
- [ ] Clean up migration code
- [ ] Final documentation update

---

## Rollback Plan

If issues arise, rollback is straightforward:

1. **Revert code changes** - All changes are in tracked files
2. **Restore directory** - `mv ~/.mcli/workflows ~/.mcli/commands`
3. **Use git** - `git revert <commit>` for all related commits

---

## Related Issues

- User request: Clarify command structure
- User request: Move secrets to workflows
- User request: Remove confusing lib group

---

## Contact

For questions or issues:
- **GitHub Issues**: [mcli/issues](https://github.com/gwicho38/mcli/issues)
- **Documentation**: [docs/INDEX.md](INDEX.md)
- **Migration Guide**: [COMMAND_MIGRATION_GUIDE.md](COMMAND_MIGRATION_GUIDE.md)

---

**Last Updated**: 2025-10-30
**Version**: 7.11.0
**Status**: Complete
