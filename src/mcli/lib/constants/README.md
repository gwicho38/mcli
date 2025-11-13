# Constants Module

This module provides centralized constants for the entire MCLI application. Using constants instead of hardcoded strings helps maintain consistency, reduce typos, and make the codebase easier to maintain and refactor.

## Structure

```
src/mcli/lib/constants/
├── __init__.py         # Main exports - import from here
├── env.py             # Environment variable names (EnvVars)
├── paths.py           # File and directory names (DirNames, FileNames, PathPatterns)
├── messages.py        # UI messages (ErrorMessages, SuccessMessages, WarningMessages, InfoMessages)
├── defaults.py        # Default values (URLs, Editors, Shells, Languages, LogLevels, etc.)
└── commands.py        # Command metadata (CommandKeys, CommandGroups, ConfigKeys)
```

## Usage

### Basic Import

Always import from the main module, not from individual files:

```python
# ✅ Good
from mcli.lib.constants import EnvVars, DirNames, ErrorMessages

# ❌ Bad
from mcli.lib.constants.env import EnvVars
```

### Environment Variables

```python
from mcli.lib.constants import EnvVars
import os

# Get environment variables
api_key = os.getenv(EnvVars.OPENAI_API_KEY)
trace_level = os.getenv(EnvVars.MCLI_TRACE_LEVEL)
config_path = os.getenv(EnvVars.MCLI_CONFIG)

# Check environment
if EnvVars.CI in os.environ:
    print("Running in CI environment")
```

### File and Directory Paths

```python
from mcli.lib.constants import DirNames, FileNames
from pathlib import Path

# Build paths
config_dir = Path.home() / DirNames.CONFIG_DIR / DirNames.MCLI
config_file = config_dir / FileNames.CONFIG_TOML
commands_dir = Path.home() / DirNames.MCLI / DirNames.COMMANDS

# Check for git directory
if (repo_path / DirNames.GIT).exists():
    print("Git repository found")
```

### UI Messages

```python
from mcli.lib.constants import ErrorMessages, SuccessMessages, WarningMessages, InfoMessages
import click

# Success messages
click.echo(SuccessMessages.COMMAND_COMPLETED)
click.echo(SuccessMessages.SAVED_TO.format(path=output_path))

# Error messages
if not command_found:
    click.echo(ErrorMessages.COMMAND_NOT_FOUND.format(name=cmd_name))

# Warning messages
if file_exists:
    click.echo(WarningMessages.ALREADY_EXISTS.format(item=filename))

# Info messages
click.echo(InfoMessages.LOADING.format(item="configuration"))
```

### Default Values

```python
from mcli.lib.constants import URLs, Editors, Shells, LogLevels
import os

# URLs
api_url = os.getenv("API_URL", URLs.LSH_API_DEFAULT)
ollama_url = URLs.OLLAMA_DEFAULT

# Editor selection
editor = os.getenv("EDITOR")
if not editor:
    for editor in Editors.FALLBACK_LIST:
        if shutil.which(editor):
            break
    else:
        editor = Editors.DEFAULT

# Shell detection
shell = os.getenv("SHELL", Shells.DEFAULT_PATH)

# Logging
logger.setLevel(LogLevels.INFO)
```

### Command Metadata

```python
from mcli.lib.constants import CommandKeys, CommandGroups, ConfigKeys

# Command dictionary
command_data = {
    CommandKeys.NAME: "my-command",
    CommandKeys.CODE: "echo 'Hello'",
    CommandKeys.DESCRIPTION: "A test command",
    CommandKeys.GROUP: CommandGroups.CUSTOM,
    CommandKeys.LANGUAGE: "shell",
}

# Config access
config = {
    ConfigKeys.PATHS: {
        ConfigKeys.INCLUDED_DIRS: ["app", "workflow"],
    }
}
```

## Adding New Constants

When you need to add a new constant:

1. **Choose the right module:**
   - Environment variables → `env.py`
   - File/directory names → `paths.py`
   - User-facing messages → `messages.py`
   - Default values/configs → `defaults.py`
   - Command-related → `commands.py`

2. **Add to the appropriate class:**
   ```python
   # In env.py
   class EnvVars:
       # ... existing constants
       NEW_ENV_VAR = "NEW_ENV_VAR"
   ```

3. **Export from `__init__.py`** (if adding a new class):
   ```python
   from .env import EnvVars, NewClass

   __all__ = [
       "EnvVars",
       "NewClass",
       # ... other exports
   ]
   ```

4. **Use it in your code:**
   ```python
   from mcli.lib.constants import EnvVars

   value = os.getenv(EnvVars.NEW_ENV_VAR)
   ```

## Linting

A custom linter (`tools/lint_hardcoded_strings.py`) automatically detects hardcoded strings that should be constants:

```bash
# Check all files
make lint-hardcoded-strings

# Or run directly
python tools/lint_hardcoded_strings.py --check-all
```

The linter runs automatically as a pre-commit hook, so hardcoded strings will be caught before they're committed.

## Best Practices

1. **Always use constants** for:
   - Environment variable names
   - File and directory names
   - Configuration keys
   - User-facing messages
   - URLs and endpoints
   - Default values

2. **Keep constants organized:**
   - Group related constants together
   - Use descriptive names in ALL_CAPS
   - Add docstrings for complex constants

3. **Don't hardcode strings** in:
   - Error messages
   - Success/warning/info messages
   - Environment variable lookups
   - Path construction
   - Configuration access

4. **Format strings with `.format()`:**
   ```python
   # ✅ Good
   ErrorMessages.COMMAND_NOT_FOUND.format(name=cmd_name)

   # ❌ Bad
   f"Command {cmd_name} not found"
   ```

## Benefits

- **Consistency:** Same strings used everywhere
- **Type Safety:** IDE autocomplete and type checking
- **Easy Updates:** Change once, applies everywhere
- **Better Testing:** Mock constants easily
- **No Typos:** Compiler catches mistakes
- **Refactoring:** Easy to find all usages
- **Internationalization:** Centralized strings ready for translation

## Examples from the Codebase

See these files for examples of proper constants usage:
- `src/mcli/lib/paths.py` - Uses DirNames and FileNames
- `src/mcli/app/commands_cmd.py` - Will be updated to use constants
- `src/mcli/self/self_cmd.py` - Will be updated to use constants

## Questions?

See the [Linting Guide](../../../docs/development/LINTING.md) for more information about the hardcoded strings linter and code quality standards.
