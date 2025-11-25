# File Path Completion for Workflows

**Added in version 7.19.5**

## Overview

MCLI now supports intelligent file path autocomplete when using `mcli run` (or `mcli workflows`) with local file paths. This makes it easy to discover and execute scripts directly without having to register them as workflows first.

## Features

### 1. Relative Path Completion

When you type `./`, MCLI will autocomplete files and directories in your current working directory:

```bash
mcli run ./<TAB>
# Shows all files and directories in current directory
./script.py
./my_script.sh
./subdir/
./README.md
```

### 2. Partial Filename Matching

Start typing a filename and press TAB to see matching completions:

```bash
mcli run ./test_<TAB>
# Shows only files starting with "test_"
./test_one.py
./test_two.py
./test_helpers.sh
```

### 3. Directory Navigation

Directories are shown with a trailing slash to indicate they can be navigated into:

```bash
mcli run ./scripts/<TAB>
# Shows contents of scripts directory
./scripts/backup.py
./scripts/deploy.sh
./scripts/utils/
```

### 4. Absolute Path Support

You can also use absolute paths:

```bash
mcli run /Users/name/projects/<TAB>
# Shows files in absolute path
```

### 5. Home Directory Expansion

The `~` character expands to your home directory:

```bash
mcli run ~/scripts/<TAB>
# Shows files in home directory's scripts folder
```

### 6. Hidden File Handling

Hidden files (starting with `.`) are excluded by default unless you explicitly request them:

```bash
mcli run ./<TAB>
# Shows only visible files

mcli run ./.git<TAB>
# Shows hidden files starting with .git
./.gitignore
./.github/
```

## Supported File Types

Once autocompleted, MCLI can execute various file types directly:

- **Python scripts** (`.py`) - Executed with `python`
- **Shell scripts** (`.sh`, `.bash`, `.zsh`) - Executed directly (made executable automatically)
- **Jupyter notebooks** (`.ipynb`) - Loaded as workflow command groups
- **Any executable file** - Executed if executable permission is set

## Usage Examples

### Execute a Python Script

```bash
# Autocomplete to find the script
mcli run ./scripts/backup<TAB>
# Expands to:
mcli run ./scripts/backup.py

# Add arguments after the filename
mcli run ./scripts/backup.py --target /data
```

### Execute a Shell Script

```bash
# Autocomplete shell scripts
mcli run ./deploy<TAB>
# Expands to:
mcli run ./deploy.sh

# Execute with arguments
mcli run ./deploy.sh production --verbose
```

### Load a Notebook

```bash
# Autocomplete notebooks
mcli run ./notebooks/analysis<TAB>
# Expands to:
mcli run ./notebooks/analysis.ipynb

# Then run a cell from the notebook
mcli run ./notebooks/analysis.ipynb cell-1
```

## How It Works

The file path completion is implemented in `ScopedWorkflowsGroup.shell_complete()` method in `src/mcli/workflow/workflow.py`.

**Key behaviors:**

1. **Path Detection**: Completion is triggered when the input starts with `./`, `/`, or `~`
2. **Directory Listing**: Lists all matching files/directories in the target path
3. **Filtering**: Matches only items that start with the partial filename
4. **Sorting**: Results are alphabetically sorted
5. **Type Indication**: Directories get a trailing `/` to show they're navigable

## Implementation Details

The completion logic:

1. Checks if input looks like a file path (`./`, `/`, or `~` prefix)
2. Parses the path to separate directory from partial filename
3. Expands `~` to user home directory
4. Resolves relative paths against current working directory
5. Lists directory contents and filters by partial filename
6. Returns sorted list of `CompletionItem` objects

## Testing

The feature is comprehensively tested in `tests/unit/test_workflow_file_completion.py`:

- ✅ Relative path completion (`./`)
- ✅ Partial filename matching (`./test_`)
- ✅ Absolute path completion
- ✅ Hidden file handling
- ✅ Directory trailing slashes
- ✅ Workflow command fallback (non-path completions)

Run tests:

```bash
pytest tests/unit/test_workflow_file_completion.py -v
```

## Compatibility

- **Shell Support**: Works with bash, zsh, and fish shells
- **Path Formats**: Supports relative (`./`), absolute (`/`), and home-relative (`~`) paths
- **Cross-Platform**: Works on macOS, Linux, and Windows (with appropriate shell)

## Related Commands

- `mcli workflow` - Manage workflow definitions
- `mcli commands import` - Register a script as a permanent workflow
- `mcli run` - Alias for `mcli workflows`

## See Also

- [Shell Completion Guide](../features/SHELL_COMPLETION.md) - General shell completion setup
- [Workflow Documentation](../../README.md#-workflow-system-features) - Complete workflow system guide
- [Script Sync System](../SCRIPT_SYNC_SYSTEM.md) - Auto-convert scripts to workflows
