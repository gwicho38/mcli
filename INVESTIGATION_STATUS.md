# Notebook Discovery Investigation Status

**Date:** 2025-11-24
**Version:** 7.19.1 (fix completed)
**Status:** ✅ RESOLVED

## Resolution Summary

**Root Cause:** `MCLIMetadata.from_dict()` in `schema.py` was using `data["name"]` which raised KeyError for notebooks without MCLI-specific metadata.

**Fix:** Changed to `data.get("name", "unnamed")` to gracefully handle notebooks created outside of MCLI (commit: f0616a6).

**Result:** Notebooks can now be dropped into `.mcli/workflows/` and are automatically discovered and loaded.

---

# Original Investigation (for reference)

**Issue:** Jupyter notebooks in `.mcli/workflows/` were discovered by sync but not appearing in `mcli run --help`

## What's Been Done

### ✅ Completed
1. **Version 7.19.0 published to PyPI** - All CI passing
2. **Command reordering** - Commands now appear in logical order (init, new, edit, delete, self, sync, teardown, workflow, workflows)
3. **Notebook discovery fixes** - Fixed hidden directory bug in `script_sync.py`
4. **Notebook loading support** - Added `.ipynb` scanning in `custom_commands.py`
5. **Release notes created** - `docs/releases/7.19.0.md`

### 📊 Test Results
- ✅ All CLI tests passing (11/11)
- ✅ Python 3.9, 3.10, 3.11, 3.12 tests passing
- ✅ CodeQL and security scanning passed
- ✅ Black formatting compliant

## Current Issue

### Problem
The notebook `ingestion.ipynb` in `/Users/lefv/repos/politician-trading-tracker/.mcli/workflows/` is:
- ✅ Found by `mcli sync` (reports "Synced 1 script(s) to JSON")
- ✅ Loaded by command manager (reports "Loaded 2 workflow command(s)")
- ✅ Discovered by `list_commands()` (debug output shows: `[DEBUG] ADDED: ingestion`)
- ❌ **NOT appearing in `mcli run --help` output**

### Debug Output Shows
```
[DEBUG] list_commands: commands_dir=/Users/lefv/repos/politician-trading-tracker/.mcli/workflows, exists=True
[DEBUG] Found 1 notebook(s) via rglob
[DEBUG] Checking notebook: /Users/lefv/repos/politician-trading-tracker/.mcli/workflows/ingestion.ipynb
[DEBUG]   Relative parts: ('ingestion.ipynb',)
[DEBUG]   ADDED: ingestion
[DEBUG] Final notebook_commands: ['ingestion']
```

Then attempts to call `get_command(ctx, 'ingestion')` which calls `register_notebook_command_with_click()`, but this appears to fail silently or return None.

### Error During Help Generation
Logging errors appeared during help generation:
- `OSError: [Errno 28] No space left on device` (disk space issue on development machine)
- This might be masking the real error

### Notebook Content
The `ingestion.ipynb` file contains:
- Cell 0: `import click`
- Cell 1:
  ```python
  @click.command()
  def ingest(epochs, lr):
      """Train the ML model"""
      click.echo(f"Training mode...")
  ```

## Code Locations

### Relevant Files
1. **src/mcli/workflow/workflow.py** (lines 86-103)
   - `list_commands()` method discovers notebooks
   - `get_command()` method (lines 253-267) loads notebook commands

2. **src/mcli/lib/custom_commands.py** (lines 478-522)
   - `register_notebook_command_with_click()` registers notebook commands
   - Uses `NotebookCommandLoader.load_group_from_file()`

3. **src/mcli/lib/script_sync.py** (lines 431-439)
   - Fixed to not skip files in `.mcli` directories

### Key Discovery
- Notebook IS added to `notebook_commands` list (confirmed by debug output)
- The list IS returned by `list_commands()`
- BUT when Click calls `get_command(ctx, 'ingestion')` to get the command details for help display, something fails
- The failure appears to be in `register_notebook_command_with_click()` → `NotebookCommandLoader.load_group_from_file()`

## Next Steps for Investigation

1. **Check NotebookCommandLoader** - Add debug output to `src/mcli/workflow/notebook/command_loader.py`
   - Does `load_group_from_file()` successfully parse the notebook?
   - Are Click commands extracted from cells?
   - Is a command group created and returned?

2. **Test directly** - Try loading the notebook manually:
   ```python
   from mcli.workflow.notebook.command_loader import NotebookCommandLoader
   from pathlib import Path

   nb_path = Path(".mcli/workflows/ingestion.ipynb")
   group = NotebookCommandLoader.load_group_from_file(nb_path, group_name="ingestion")
   print(f"Group: {group}")
   print(f"Commands: {list(group.commands.keys()) if group else 'None'}")
   ```

3. **Check error handling** - The `register_notebook_command_with_click()` method catches exceptions:
   ```python
   except Exception as e:
       logger.error(f"Failed to register notebook {notebook_file.name}: {e}")
       return False
   ```
   Need to see what exception is being raised

4. **Verify disk space** - The "No space left on device" errors might be preventing proper operation
   ```bash
   df -h
   ```

## Files to Review on New Machine

- `src/mcli/workflow/notebook/command_loader.py` - Notebook parsing logic
- `src/mcli/workflow/notebook/__init__.py` - Package structure
- Tests in `tests/*/test_notebook_*.py` - How notebooks are supposed to work

## Commands to Run

```bash
# Check version
mcli self version

# Check if notebook appears
cd ~/repos/politician-trading-tracker
mcli run --help | grep ingestion

# Sync workflow
mcli sync

# Try to run directly
mcli run ingestion --help

# Check disk space
df -h

# Manual test in Python
cd ~/repos/politician-trading-tracker
python3 << 'EOF'
from pathlib import Path
from mcli.workflow.notebook.command_loader import NotebookCommandLoader

nb_path = Path(".mcli/workflows/ingestion.ipynb")
group = NotebookCommandLoader.load_group_from_file(nb_path, group_name="ingestion")
print(f"Group loaded: {group is not None}")
if group:
    print(f"Commands: {list(group.commands.keys())}")
else:
    print("Failed to load notebook")
EOF
```

## Hypothesis

The notebook discovery (`list_commands()`) works correctly, but when Click tries to load each command to display help text, the `NotebookCommandLoader` is failing to:
1. Parse the notebook cells
2. Extract Click commands
3. Execute setup cells (imports)
4. Create a working Click command group

This causes `get_command()` to return `None`, which makes Click silently exclude it from the help output.

## Repository State

**Branch:** main
**Latest commit:** 37370e8 (chore: Bump version to 7.19.0)
**Remote:** origin (git@github.com:gwicho38/mcli.git)
**Status:** All changes committed and pushed
