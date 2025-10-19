# Fuzzy Finding for Workflow Commands

**Feature Version:** 7.11.0
**Status:** Active

## Overview

MCLI's fuzzy finding feature provides an intelligent, interactive command discovery system for workflow commands. Instead of requiring exact command names, users can type partial queries, acronyms, or keywords to quickly find and execute commands.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Usage Examples](#usage-examples)
- [Matching Strategies](#matching-strategies)
- [Interactive Mode](#interactive-mode)
- [Non-Interactive Mode](#non-interactive-mode)
- [Configuration](#configuration)
- [API Reference](#api-reference)

## Quick Start

### Interactive Command Selection

Simply type `mcli workflow` to launch the interactive fuzzy finder:

```bash
# Show all workflow commands with fuzzy search
mcli workflow
```

The interactive selector will display all available workflow commands with a search box. Type any query to filter commands in real-time.

### Quick Execution with High-Confidence Matches

```bash
# Type a partial command name
mcli workflow git_status      # Exact match - executes immediately
mcli workflow git             # High confidence match - executes if score >= 95%
```

## Features

### 🎯 Multi-Strategy Matching

The fuzzy finder uses multiple algorithms to find the best matches:

1. **Exact Match** (100% score) - Command name exactly matches query
2. **Prefix Match** (95% score) - Command name starts with query
3. **Fuzzy Ratio** - Overall similarity between query and command name
4. **Partial Ratio** - Substring matching within command name
5. **Token Set Ratio** - Handles word order differences
6. **Acronym Match** (85% score) - Matches first letters of words
7. **Description Match** (50% weight) - Searches command descriptions

### 🔍 Intelligent Acronym Matching

Type acronyms to find commands quickly:

- `gst` → `git_status`
- `bdb` → `backup_db`
- `dcs` → `deploy_and_check_status`

### ⚡ Smart Auto-Execution

High-confidence matches (≥95% score) execute immediately without requiring selection:

```bash
# These execute automatically
mcli workflow git_st          # Matches "git_status" with high confidence
mcli workflow backup          # Matches "backup_db" with high confidence
```

### 🎨 Rich Interactive UI

- **Fuzzy Search Box** - Type to filter commands in real-time
- **Score Display** - See match confidence scores
- **Language Badges** - Visual indicators for Python/Shell commands
- **Description Preview** - See command descriptions truncated to fit
- **Keyboard Navigation** - Arrow keys, Enter to select, Ctrl+C to cancel

## Usage Examples

### Example 1: Interactive Discovery

```bash
$ mcli workflow

# Interactive selector appears:
? Select a workflow command: (Type to search, ↑↓ to navigate, Enter to select, Ctrl+C to cancel)
  > git_status (shell) [100%] - Enhanced git status with colors
    backup_db (shell) [100%] - Backup database with timestamp
    deploy (python) [100%] - Deploy application to production
    clean (shell) [100%] - Clean system temporary files
    ... (97 more commands)

# User types "git"
? Select a workflow command: git
  > git_status (shell) [100%] - Enhanced git status with colors
    git_commit (python) [67%] - Commit changes with message template
```

### Example 2: Fuzzy Matching

```bash
$ mcli workflow back

# If no exact match, shows suggestions:
No exact match for 'back'.
Use one of these commands:
  • backup_db (95%) - Backup database with timestamp
  • rollback_deploy (78%) - Rollback last deployment
  • background_sync (72%) - Sync files in background
```

### Example 3: Acronym Matching

```bash
$ mcli workflow gst

# Matches "git_status" via acronym
Running: git_status (acronym match (gst))

On branch main
Your branch is up to date with 'origin/main'.
```

### Example 4: Non-Interactive Mode

In non-interactive environments (CI/CD, scripts):

```bash
# High-confidence matches execute automatically
mcli workflow backup > /dev/null 2>&1

# Low-confidence matches show suggestions and exit 1
mcli workflow xyz
No exact match for 'xyz'.
Use one of these commands:
  • xyz_parser (60%) - Parse XYZ format files
```

## Matching Strategies

### Exact Match (100% Score)

```python
query = "git_status"
command = "git_status"
→ Exact match! Score: 100
```

### Prefix Match (95% Score)

```python
query = "git"
command = "git_status"
→ Prefix match! Score: 95
```

### Acronym Match (85% Score)

```python
query = "gst"
command = "git_status"  # g-s-t
→ Acronym match! Score: 85
```

### Fuzzy Ratio

Uses Levenshtein distance to calculate similarity:

```python
query = "bkup"
command = "backup"
→ Fuzzy match! Score: 75
```

### Partial Ratio

Finds best substring match:

```python
query = "status"
command = "git_status"
→ Substring match! Score: 88
```

### Description Match (50% Weight)

```python
query = "database"
command = "backup_db"
description = "Backup database with timestamp"
→ Description match! Score: 45 (90 * 0.5)
```

## Interactive Mode

### Requirements

- **TTY Environment**: Requires interactive terminal (stdin/stdout must be TTY)
- **InquirerPy**: Automatically installed with MCLI

### User Interface

```
? Select a workflow command: (Type to search, ↑↓ to navigate, Enter to select, Ctrl+C to cancel)
  > git_status (shell) [100%] - Enhanced git status with colors
    backup_db (shell) [95%] - Backup database with timestamp
    deploy (python) [90%] - Deploy application to production
```

### Controls

- **Type**: Filter commands by fuzzy search
- **↑/↓**: Navigate through results
- **Enter**: Execute selected command
- **Ctrl+C/Esc**: Cancel and exit

### Features

1. **Real-time Filtering** - Results update as you type
2. **Score Display** - See match confidence (optional)
3. **Language Badges** - Python/Shell indicators
4. **Truncated Descriptions** - Descriptions limited to 60 characters
5. **Fallback to First Match** - If cancelled, suggests best match

## Non-Interactive Mode

### Automatic Detection

MCLI automatically detects non-interactive environments:

- CI/CD pipelines
- Shell scripts
- Piped input/output
- SSH without PTY allocation

### Behavior

```bash
# In non-interactive mode:
$ mcli workflow git
git_status  # If high confidence (≥80%), auto-select best match

$ mcli workflow xyz
❌ Command 'xyz' not found.
# Shows top 5 suggestions with scores
```

### Exit Codes

- `0`: Command executed successfully
- `1`: No match found or execution failed

## Configuration

### Minimum Score Threshold

Default: 60 (range: 0-100)

```python
from mcli.lib.fuzzy_finder import FuzzyCommandFinder

finder = FuzzyCommandFinder(min_score=70)  # Stricter matching
```

### Maximum Results

Default: 10

```python
finder = FuzzyCommandFinder(max_results=20)  # Show more results
```

### Quick Select Threshold

Default: 90 (for auto-execution)

```python
from mcli.lib.interactive_selector import quick_select_best_match

match = quick_select_best_match(query, commands, min_score=95)  # Stricter
```

## API Reference

### FuzzyCommandFinder

**Module:** `mcli.lib.fuzzy_finder`

#### Constructor

```python
FuzzyCommandFinder(min_score: int = 60, max_results: int = 10)
```

**Parameters:**
- `min_score`: Minimum similarity score (0-100)
- `max_results`: Maximum number of results to return

#### Methods

##### find_commands()

```python
def find_commands(
    self,
    query: str,
    commands: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], int]]
```

Find commands using fuzzy matching.

**Parameters:**
- `query`: Search query
- `commands`: List of command dictionaries

**Returns:**
- List of (command, score) tuples sorted by score descending

**Example:**

```python
from mcli.lib.fuzzy_finder import FuzzyCommandFinder

finder = FuzzyCommandFinder()
matches = finder.find_commands("git", commands)

for cmd, score in matches:
    print(f"{score}%: {cmd['name']}")
```

##### get_best_matches()

```python
def get_best_matches(
    self,
    query: str,
    commands: List[Dict[str, Any]],
    limit: Optional[int] = None
) -> List[Dict[str, Any]]
```

Get top N best matching commands.

**Returns:**
- List of command dictionaries (without scores)

##### get_single_best_match()

```python
def get_single_best_match(
    self,
    query: str,
    commands: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]
```

Get single best matching command.

**Returns:**
- Best matching command or None

##### get_match_explanation()

```python
def get_match_explanation(
    self,
    query: str,
    command: Dict[str, Any]
) -> str
```

Get human-readable explanation of why a command matched.

**Returns:**
- Explanation string (e.g., "exact match", "acronym match (gst)", "fuzzy match")

### Interactive Selector

**Module:** `mcli.lib.interactive_selector`

#### select_command_interactive()

```python
def select_command_interactive(
    commands: List[Dict[str, Any]],
    query: str = "",
    show_scores: bool = False,
    fuzzy_finder: Optional[FuzzyCommandFinder] = None
) -> Optional[Dict[str, Any]]
```

Interactive command selection with fuzzy finding.

**Parameters:**
- `commands`: List of available commands
- `query`: Initial search query (optional)
- `show_scores`: Whether to show match scores in display
- `fuzzy_finder`: Custom FuzzyCommandFinder instance (creates default if None)

**Returns:**
- Selected command dictionary or None if cancelled

**Requires:**
- Interactive TTY environment

**Example:**

```python
from mcli.lib.interactive_selector import select_command_interactive

selected = select_command_interactive(commands, query="git")
if selected:
    print(f"Selected: {selected['name']}")
```

#### select_from_suggestions()

```python
def select_from_suggestions(
    query: str,
    commands: List[Dict[str, Any]],
    fuzzy_finder: Optional[FuzzyCommandFinder] = None
) -> Optional[Dict[str, Any]]
```

Show "Did you mean?" suggestions for unknown commands.

**Parameters:**
- `query`: The unknown command that was attempted
- `commands`: List of available commands
- `fuzzy_finder`: FuzzyCommandFinder instance (default: min_score=50)

**Returns:**
- Selected command or None

**Behavior:**
- Interactive: Shows top 5 suggestions with selection prompt
- Non-interactive: Returns best match if score ≥80%

#### quick_select_best_match()

```python
def quick_select_best_match(
    query: str,
    commands: List[Dict[str, Any]],
    min_score: int = 90
) -> Optional[Dict[str, Any]]
```

Quickly select best match without interaction if score is high enough.

**Parameters:**
- `query`: Search query
- `commands`: Available commands
- `min_score`: Minimum score for auto-selection (default: 90)

**Returns:**
- Best matching command if score ≥ min_score, else None

## Integration with Workflow Commands

### Current Implementation

File: `src/mcli/workflow/workflow.py`

```python
@click.group(name="workflow", invoke_without_command=True)
@click.pass_context
def workflow(ctx):
    """Workflow commands with interactive fuzzy finding."""
    if ctx.invoked_subcommand is not None:
        return
    # No subcommand - show interactive selector
    show_interactive_workflow_selector(ctx)
```

### How It Works

1. **User types** `mcli workflow`
2. **Click invokes** workflow group with no subcommand
3. **`invoke_without_command=True`** triggers custom handler
4. **Fuzzy finder loads** all workflow commands from discovery system
5. **Interactive selector** displays commands with fuzzy search
6. **User selects** command via keyboard
7. **Command executes** with Click context

### Execution Flow

```
mcli workflow
    ↓
workflow.py:workflow()
    ↓
show_interactive_workflow_selector()
    ↓
get_workflow_commands()  # Load from discovery
    ↓
select_command_interactive()  # Show UI
    ↓
execute_workflow_command()  # Invoke via Click
```

## Best Practices

### 1. Use Short Queries

```bash
# Good
mcli workflow git
mcli workflow back
mcli workflow dep

# Less efficient
mcli workflow this is a very long query that is too specific
```

### 2. Leverage Acronyms

Create command names that form memorable acronyms:

```bash
git_status      → gst
deploy_and_test → dat
backup_database → bdb
```

### 3. Add Descriptive Metadata

Good descriptions improve fuzzy matching:

```json
{
  "name": "backup_db",
  "description": "Backup PostgreSQL database with timestamp",
  "language": "shell"
}
```

Now searches for "postgres", "database", or "backup" will all match!

### 4. Group Related Commands

Use consistent naming patterns:

```bash
git_status
git_commit
git_push
```

Query "git" will show all git-related commands together.

## Troubleshooting

### Issue: "Interactive selector requires a TTY"

**Cause:** Running in non-interactive environment

**Solutions:**
1. Use exact command name: `mcli workflow git_status`
2. Run in interactive shell
3. Allocate PTY: `ssh -t user@host mcli workflow`

### Issue: No commands appear

**Cause:** No workflow commands registered

**Solutions:**
1. Create commands: `mcli commands add my_command --group workflow`
2. Check custom commands: `ls ~/.mcli/commands/`
3. Verify discovery: `mcli commands list --custom-only`

### Issue: Poor match scores

**Cause:** Query too different from command names

**Solutions:**
1. Use shorter, more specific queries
2. Try acronyms (first letters of words)
3. Search in description by using keywords
4. Lower min_score threshold (advanced)

### Issue: Slow fuzzy matching

**Cause:** Using pure-Python fuzzywuzzy

**Solution:** Install python-Levenshtein for C speedup:

```bash
pip install python-Levenshtein
```

## Performance Considerations

### Command Loading

- Discovery happens once per invocation
- Commands cached in memory during session
- Typical load time: <100ms for 100 commands

### Fuzzy Matching

- Pure Python: ~10-20ms per command for 100 commands
- With python-Levenshtein: ~2-5ms per command
- Results sorted by score (O(n log n))

### Interactive UI

- InquirerPy renders updates: <16ms (60 FPS)
- Fuzzy search re-runs on every keystroke
- Maximum results limited to 10 for performance

## Future Enhancements

Potential future additions:

- **Command History**: Remember frequently used commands
- **Weighted Scoring**: Boost recently used commands
- **Custom Aliases**: User-defined shortcuts
- **Fuzzy Options**: Match command options/flags
- **Smart Suggestions**: ML-based command recommendation
- **Multi-Command**: Execute multiple commands in sequence
- **Command Chaining**: Pipe output between workflow commands

## Related Documentation

- [Command Management](./COMMAND_MANAGEMENT.md)
- [Workflow System](../README.md)
- [Shell Commands](./SHELL_COMMANDS.md)

## Version History

- **7.11.0** (2025-10-19) - Initial fuzzy finding implementation
  - FuzzyCommandFinder with 7 matching strategies
  - Interactive selector with InquirerPy
  - Acronym matching support
  - Auto-execution for high-confidence matches
  - Non-interactive fallback mode
