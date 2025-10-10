# Command Consolidation - Migration Guide

## Summary

All command management functionality has been consolidated under the `mcli commands` group for better organization and discoverability.

## What Changed

### New Command Structure

All command management features are now under `mcli commands`:

```bash
mcli commands
├── list               # List all available commands
├── search             # Search commands by name, description, or tags
├── execute            # Execute a command by name
├── info               # Show detailed information about a command
├── add                # Create a new custom command
├── list-custom        # List custom commands
├── remove             # Remove a custom command
├── export             # Export custom commands to JSON
├── import             # Import custom commands from JSON
├── verify             # Verify commands match lockfile
├── update-lockfile    # Update the commands lockfile
├── edit               # Edit a command using $EDITOR
├── import-script      # Import Python script as command
└── export-script      # Export command to Python script
```

### Migration Map

Old commands in `mcli self` have been deprecated and moved:

| Old Command | New Command | Status |
|------------|-------------|--------|
| `mcli self add-command` | `mcli commands add` | Deprecated |
| `mcli self list-commands` | `mcli commands list-custom` | Deprecated |
| `mcli self remove-command` | `mcli commands remove` | Deprecated |
| `mcli self export-commands` | `mcli commands export` | Deprecated |
| `mcli self import-commands` | `mcli commands import` | Deprecated |
| `mcli self verify-commands` | `mcli commands verify` | Deprecated |
| `mcli self update-lockfile` | `mcli commands update-lockfile` | Deprecated |
| `mcli self import-script` | `mcli commands import-script` | Deprecated |
| `mcli self export-script` | `mcli commands export-script` | Deprecated |
| `mcli self edit-command` | `mcli commands edit` | Deprecated |

## Usage Examples

### Creating a new command

**Old way (deprecated):**
```bash
mcli self add-command my_command --group workflow
```

**New way:**
```bash
mcli commands add my_command --group workflow
```

### Listing custom commands

**Old way (deprecated):**
```bash
mcli self list-commands
```

**New way:**
```bash
mcli commands list-custom
```

### Editing a command

**Old way (deprecated):**
```bash
mcli self edit-command my_command
```

**New way:**
```bash
mcli commands edit my_command
```

### Importing/Exporting commands

**Old way (deprecated):**
```bash
mcli self export-commands commands.json
mcli self import-commands commands.json
```

**New way:**
```bash
mcli commands export commands.json
mcli commands import commands.json
```

## Backward Compatibility

- All old commands still work but show deprecation warnings
- Deprecated commands will be removed in a future major version
- Users are encouraged to update their scripts and workflows

## What Stayed in `mcli self`

The following commands remain in `mcli self` as they are system-level operations:

- `mcli self search` - Search for available commands
- `mcli self hello` - Test command
- `mcli self logs` - View application logs
- `mcli self performance` - Performance monitoring
- `mcli self dashboard` - Live system dashboard
- `mcli self update` - Update mcli itself
- `mcli self plugin` - Plugin management

## Benefits of Consolidation

1. **Better Organization**: All command management features are now in one place
2. **Easier Discovery**: Users can find all command-related operations under `mcli commands`
3. **Clearer Separation**: System operations (`mcli self`) vs command management (`mcli commands`)
4. **Consistent Naming**: Command names are shorter and more intuitive (e.g., `add` instead of `add-command`)

## For Developers

### Modified Files

- `src/mcli/app/commands_cmd.py` - Added all command management functions
- `src/mcli/self/self_cmd.py` - Added deprecation warnings to old commands

### Testing

All existing tests continue to pass. The old commands still work with deprecation warnings.

```bash
# Run tests
uv run pytest tests/cli/test_self_cmd.py -v
```

### Code Quality

- No breaking changes for existing users
- Graceful deprecation path with clear migration messages
- Full backward compatibility maintained

## Timeline

- **v0.1.0**: Command consolidation implemented with deprecation warnings
- **v0.2.0** (planned): Remove deprecated commands from `mcli self`

## Questions?

For questions or issues, please open a GitHub issue at https://github.com/gwicho38/mcli/issues
