# VS Code Extension - Python/JSON/Notebook Sync Strategy

## Problem Statement

We need to maintain **bidirectional consistency** between three representations of MCLI commands:

1. **Python Source Files** (`.py`) - What developers edit directly
2. **JSON Command Files** (`~/.mcli/commands/*.json`) - What mcli stores and executes
3. **VS Code Notebook View** - What the extension provides for visual editing

### Current Workflow

```
Python Script (.py)
      ↓
mcli commands import script.py -s --name mycommand
      ↓
JSON File (~/.mcli/commands/mycommand.json)
      ↓
VS Code Extension opens → Notebook View
      ↓
Edit in notebook → Save
      ↓
JSON File updated
      ❌ Python source file NOT updated
```

**The Issue:** When you edit via VS Code notebook and save, the JSON updates but the original Python source file doesn't, causing **divergence**.

## The Sync Challenge

### Scenario 1: Edit Python Source Directly
```python
# User edits /path/to/script.py
def my_function():
    print("Updated in Python")
```

**Problem:** JSON file in `~/.mcli/commands/` is now out of sync
**Expected:** JSON should auto-update or warn user

### Scenario 2: Edit via VS Code Notebook
```
User opens ~/.mcli/commands/mycommand.json
  → VS Code shows notebook view
  → User edits cells
  → Saves
  → JSON updates
```

**Problem:** Original Python source file remains unchanged
**Expected:** Python source should sync OR we accept JSON as source of truth

### Scenario 3: mcli commands edit
```bash
mcli commands edit mycommand
# Opens $EDITOR with Python code extracted from JSON
# User edits and saves
```

**Problem:** This extracts code from JSON, user edits, then re-imports
**Expected:** Workflow should be seamless

## Proposed Solutions

### Option 1: JSON as Single Source of Truth (Recommended)

**Philosophy:** The JSON file is the canonical representation. Python source files are ephemeral.

**Implementation:**
1. ✅ **Keep current VS Code extension behavior** - Edits notebook, saves to JSON
2. ✅ **mcli commands edit** - Extracts code from JSON to temp file, saves back to JSON
3. ✅ **No Python source tracking** - Original `.py` files are import artifacts only
4. ✅ **Export capability** - Add `mcli commands export mycommand --format python` to regenerate `.py` files

**Pros:**
- Simple mental model: JSON is truth
- No sync complexity
- Works with current implementation
- VS Code extension already implements this

**Cons:**
- Users can't maintain `.py` files in version control
- Lose Python-first workflow

---

### Option 2: Python Source as Single Source of Truth

**Philosophy:** Python files are primary. JSON is generated cache.

**Implementation:**
1. Store Python source file path in JSON metadata
2. Add file watcher to detect `.py` changes
3. On change, re-import: `mcli commands import script.py -s --name cmd --overwrite`
4. VS Code extension exports edited notebook back to `.py` file
5. File watcher detects change, updates JSON

**Pros:**
- Python-first workflow
- Can version control `.py` files
- Familiar for Python developers

**Cons:**
- Complex sync logic
- Potential race conditions
- File watcher overhead
- Harder to implement

---

### Option 3: Bidirectional Sync with Conflict Detection

**Philosophy:** Support both workflows, detect conflicts, let user resolve.

**Implementation:**
1. Track checksums of both Python source and JSON code
2. On edit (either side), compare checksums
3. If diverged, prompt user:
   - "Python source has changed. Update JSON?"
   - "JSON has changed. Update Python source?"
4. Add `mcli commands sync` command to reconcile

**Pros:**
- Flexible - supports both workflows
- User has control
- Detects divergence

**Cons:**
- Most complex implementation
- User friction (prompts)
- Requires careful UX design

---

## Recommended Approach: Option 1 + Enhancements

### Implementation Plan

**Phase 1: JSON as Source of Truth** ✅ (Already Done)
- VS Code extension auto-converts old JSON format
- Saves back to JSON format
- No Python source sync

**Phase 2: Enhanced Export** (Next)
Add export capabilities:
```bash
# Export command as Python script
mcli commands export mycommand --format python --output mycommand.py

# Export all commands
mcli commands export --format python --output ./commands/

# Export as notebook JSON
mcli commands export mycommand --format notebook --output mycommand.ipynb
```

**Phase 3: Metadata Tracking** (Future)
Add to JSON metadata:
```json
{
  "name": "mycommand",
  "code": "...",
  "metadata": {
    "source": "import-script",
    "original_file": "/path/to/script.py",
    "last_sync": "2025-10-28T...",
    "checksum": "sha256:..."
  }
}
```

**Phase 4: Optional Sync** (Future)
Add opt-in sync for users who want Python source:
```bash
# Enable Python source sync for a command
mcli commands link mycommand --source mycommand.py

# Auto-sync when Python file changes
mcli commands watch
```

---

## User Workflows

### Workflow A: JSON-First (Current, Recommended)

1. Create command from script:
   ```bash
   mcli commands import script.py -s --name mycmd
   ```

2. Edit visually in VS Code:
   - Open `~/.mcli/commands/mycmd.json` in VS Code
   - Edit with notebook interface
   - Save (updates JSON)

3. Execute:
   ```bash
   mcli workflow mycmd
   ```

4. Export to Python if needed:
   ```bash
   mcli commands export mycmd --format python -o mycmd.py
   ```

**Mental Model:** JSON is the source of truth. Python files are exports.

---

### Workflow B: Python-First (Future, Requires Sync)

1. Create Python file:
   ```python
   # mycmd.py
   import click

   @click.command()
   def app():
       print("Hello")
   ```

2. Link to mcli:
   ```bash
   mcli commands link mycmd --source mycmd.py --watch
   ```

3. Edit Python file directly → Auto-syncs to JSON

4. OR edit in VS Code notebook → Auto-syncs back to Python

5. Execute:
   ```bash
   mcli workflow mycmd
   ```

**Mental Model:** Python is source of truth. JSON is generated cache.

---

## Current State (v2.0.0)

✅ **Implemented:**
- VS Code extension auto-converts old JSON format to notebook
- Saves notebook edits back to JSON
- Preserves metadata

❌ **Not Implemented:**
- Python source file sync
- Conflict detection
- Export to Python functionality

---

## Recommendations

### For v2.0 (Current)

**Accept:** JSON as single source of truth
**Document:** Users should treat JSON files as primary
**Workflow:** Import → Edit in VS Code → Execute
**Export:** Future enhancement

### For v2.1 (Next Release)

**Add:** Export functionality
```bash
mcli commands export <name> --format python|notebook|shell
```

**Update:** Documentation to clarify workflows

### For v3.0 (Future)

**Add:** Optional Python source sync
**Add:** File watchers
**Add:** Conflict resolution UI

---

## FAQs

**Q: Can I edit the Python source file after importing?**
A: Not currently. The JSON is the source of truth. Edit via `mcli commands edit` or VS Code extension.

**Q: How do I version control my commands?**
A: Version control the JSON files in `~/.mcli/commands/`. You can export to Python for reference.

**Q: What if I want to maintain Python files?**
A: Wait for v2.1 export functionality or v3.0 sync features. Or manually manage:
   ```bash
   # Extract code
   jq -r '.code' ~/.mcli/commands/mycmd.json > mycmd.py

   # Edit mycmd.py

   # Re-import
   mcli commands import mycmd.py -s --name mycmd --overwrite
   ```

**Q: Why not sync automatically?**
A: Sync adds complexity, race conditions, and overhead. For now, we optimize for simplicity. JSON as single source is clearer.

---

## Implementation Notes

### VS Code Extension (Already Implemented)

File: `vscode-extension/src/notebookSerializer.ts`

```typescript
// Deserialize: JSON → Notebook
async deserializeNotebook() {
  // Auto-converts old format if needed
  if (!raw.cells && raw.code) {
    raw = this.convertMcliCommandToNotebook(raw);
  }
  // Returns notebook data for VS Code
}

// Serialize: Notebook → JSON
async serializeNotebook() {
  // Saves back to JSON format
  if (metadata.original_format === 'mcli_command') {
    return this.serializeAsMcliCommand(data, cells);
  }
  // Returns JSON bytes
}
```

**Result:** Round-trip JSON → Notebook → JSON works perfectly.

### Missing: Python Source Sync

Would require:
1. File watcher on original Python source
2. Checksum comparison
3. Re-import on change
4. Conflict detection

**Decision:** Defer to v3.0 to keep v2.0 simple and stable.

---

## Conclusion

**For v2.0:** JSON is source of truth. This is simple, stable, and working.

**For users who need Python files:** Use export functionality (coming in v2.1) or manual extraction.

**For full sync:** Wait for v3.0 or contribute to mcli framework.

The current approach (JSON as source of truth) is the right choice for stability and simplicity. We can add Python source sync later as an opt-in feature without breaking existing workflows.
