# Add Centralized Constants Module and Hardcoded Strings Linter

## 🎯 Summary

This PR introduces a comprehensive system for managing constants and detecting hardcoded strings throughout the codebase. It adds a centralized constants module and a custom AST-based linter that enforces the use of constants, preventing hardcoded strings from being committed.

## 🔧 Changes Made

### 1. Centralized Constants Module (`src/mcli/lib/constants/`)

Created a well-organized constants module with 6 files covering all major constant types:

- **`env.py`** - Environment variable names (50+ variables)
  - MCLI-specific: `MCLI_TRACE_LEVEL`, `MCLI_CONFIG`, `MCLI_HOME`, etc.
  - API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ALPACA_API_KEY`, etc.
  - System variables: `SHELL`, `EDITOR`, `XDG_DATA_HOME`, etc.

- **`paths.py`** - File and directory names
  - Directory names: `.mcli`, `logs`, `config`, `workflows`, etc.
  - File names: `config.toml`, `.gitignore`, `commands.lock.json`, etc.
  - Path patterns and gitignore patterns

- **`messages.py`** - User-facing UI messages
  - Error messages with format placeholders
  - Success messages
  - Warning messages
  - Info messages
  - Prompt messages

- **`defaults.py`** - Default values and configurations
  - URLs (API endpoints, localhost defaults)
  - Editors and shells with fallback lists
  - Programming languages
  - Log levels
  - HTTP methods
  - Date formats
  - Text encodings

- **`commands.py`** - Command metadata and configuration
  - Command dictionary keys
  - Command group names
  - Configuration keys
  - Default included/excluded directories and files
  - Shell completion constants

- **`__init__.py`** - Unified exports for easy importing
- **`README.md`** - Comprehensive usage documentation

### 2. Custom Hardcoded Strings Linter (`tools/lint_hardcoded_strings.py`)

Implemented an intelligent AST-based Python linter (384 lines) that:

- **Detects** hardcoded strings that should be constants
- **Intelligently filters** to avoid false positives:
  - Skips docstrings and comments
  - Ignores very short strings (< 3 chars)
  - Ignores whitespace and punctuation
  - Skips format strings and f-strings
  - Allows constants defined in ALL_CAPS variables
  - Excludes test files, docs, scripts, tools, and constants module itself
- **Provides clear error messages** with:
  - File path and line number
  - The offending string
  - Helpful fix suggestions
  - Examples of proper usage

### 3. Development Workflow Integration

- **Pre-commit Hook** (`.pre-commit-config.yaml`)
  - Added local hook that runs automatically on every commit
  - Properly configured exclusions
  - Validates before allowing commit

- **Makefile Target**
  - Added `make lint-hardcoded-strings` command
  - Updated help text to include new linter
  - Easy to run manually or in CI/CD

### 4. Comprehensive Documentation

- **Enhanced `docs/development/LINTING.md`** (+149 lines)
  - Added to overview and quick start
  - Comprehensive "Hardcoded Strings Linter" section
  - What it checks and what it ignores
  - Step-by-step fixing violations guide
  - Constants module structure diagram
  - Usage examples (good vs bad)
  - Pre-commit integration details

- **Created `src/mcli/lib/constants/README.md`** (234 lines)
  - Complete usage guide
  - Import patterns
  - Examples for each constant type
  - How to add new constants
  - Best practices
  - Benefits explanation

- **Updated `CLAUDE.md`** (+32 lines)
  - Added to Code Quality section
  - Created "Using Constants (Required)" section
  - Added to Common Gotchas
  - Clear examples of good vs bad usage
  - Instructions for Claude Code AI assistant

## ✨ Benefits

### Code Quality Improvements

1. **Consistency** - Single source of truth for all strings across the codebase
2. **Type Safety** - IDE autocomplete and type checking for all constants
3. **Easy Maintenance** - Change once, applies everywhere (DRY principle)
4. **Prevents Typos** - Compiler catches typos in constant names
5. **Better Refactoring** - Easy to find and update all usages
6. **Reduced Bugs** - Eliminates inconsistencies from typos in hardcoded strings
7. **Internationalization Ready** - Centralized strings ready for future translation

### Developer Experience Improvements

1. **Immediate Feedback** - Pre-commit hook catches violations before commit
2. **Clear Guidance** - Error messages show exactly how to fix issues
3. **Easy to Use** - Simple import: `from mcli.lib.constants import EnvVars`
4. **Well Documented** - Multiple documentation sources with examples
5. **IDE Support** - Full autocomplete and go-to-definition support

### Security Benefits

1. **Audit Trail** - Easy to track all environment variable usage
2. **Standardization** - Consistent naming prevents security misconfigurations
3. **Code Review** - Easy to spot sensitive data in constants review

## 🧪 Testing Done

### Linter Testing

✅ Created test file with intentional hardcoded strings
✅ Verified linter correctly detects violations
✅ Tested on actual codebase files (e.g., `src/mcli/app/main.py`)
✅ Confirmed intelligent filtering avoids false positives
✅ Validated pre-commit hook integration works
✅ Tested exclusion patterns work correctly

### Constants Module Testing

✅ Verified module imports successfully
✅ Tested all constant classes are accessible
✅ Confirmed unified imports work: `from mcli.lib.constants import EnvVars`
✅ Validated no import errors or circular dependencies

### Configuration Validation

✅ Pre-commit config passes validation: `pre-commit validate-config`
✅ Python syntax validated: `python -m py_compile tools/lint_hardcoded_strings.py`
✅ Makefile target works: `make lint-hardcoded-strings`

## 📋 Usage Examples

### Using Constants

```python
# ✅ GOOD - Using constants
from mcli.lib.constants import EnvVars, DirNames, FileNames, ErrorMessages

# Environment variables
api_key = os.getenv(EnvVars.OPENAI_API_KEY)
trace_level = os.getenv(EnvVars.MCLI_TRACE_LEVEL)

# File paths
config_path = Path.home() / DirNames.MCLI / FileNames.CONFIG_TOML
workflows_dir = Path.home() / DirNames.MCLI / DirNames.WORKFLOWS

# UI messages
click.echo(ErrorMessages.COMMAND_NOT_FOUND.format(name=cmd_name))
click.echo(SuccessMessages.COMMAND_COMPLETED)
```

```python
# ❌ BAD - Hardcoded strings (will be rejected by linter)
api_key = os.getenv("OPENAI_API_KEY")
config_path = Path.home() / ".mcli" / "config.toml"
click.echo(f"Command {cmd_name} not found")
```

### Running the Linter

```bash
# Check all files in src/mcli
make lint-hardcoded-strings

# Or run directly
python tools/lint_hardcoded_strings.py --check-all

# Check specific files or directories
python tools/lint_hardcoded_strings.py src/mcli/app/main.py
python tools/lint_hardcoded_strings.py src/mcli/workflow/
```

### Linter Output Example

```
Found hardcoded strings that should be in constants module:

src/mcli/app/main.py:
  Line 27:20: Hardcoded string should be in constants module
    String: 'config.toml'
  Line 64:16: Hardcoded string should be in constants module
    String: 'Config path: '

Total: 2 violation(s) in 1 file(s)

To fix these violations:
1. Add the string to the appropriate constants file in src/mcli/lib/constants/
2. Import and use the constant instead of the hardcoded string
3. Example:
   from mcli.lib.constants import EnvVars
   api_key = os.getenv(EnvVars.OPENAI_API_KEY)  # Instead of "OPENAI_API_KEY"
```

## 🔄 Migration Guide

### For Existing Code

The constants module is ready to use immediately. Migration of existing hardcoded strings can happen gradually:

1. **New code** - Must use constants (enforced by pre-commit hook)
2. **Modified code** - When editing files, migrate hardcoded strings to constants
3. **No breaking changes** - Old code continues to work until updated

### Adding New Constants

When you need a new constant:

1. **Choose the right file:**
   - Environment variables → `env.py`
   - File/directory names → `paths.py`
   - User messages → `messages.py`
   - Default values → `defaults.py`
   - Command metadata → `commands.py`

2. **Add the constant:**
   ```python
   # In src/mcli/lib/constants/env.py
   class EnvVars:
       NEW_VAR = "NEW_VAR"
   ```

3. **Use it:**
   ```python
   from mcli.lib.constants import EnvVars
   value = os.getenv(EnvVars.NEW_VAR)
   ```

### Bypassing the Linter (if necessary)

For special cases (like test files with intentional hardcoded strings):

```bash
# Skip pre-commit hooks for a single commit
git commit --no-verify
```

**Note:** Tests, docs, scripts, and tools are already excluded by default.

## 📊 Statistics

- **Files changed:** 12
- **Lines added:** 1,389
- **Constants defined:** 100+
- **Documentation:** 500+ lines
- **Test coverage:** Comprehensive manual testing

### File Breakdown

```
src/mcli/lib/constants/
├── __init__.py         (78 lines)
├── env.py             (66 lines)
├── paths.py           (78 lines)
├── messages.py        (96 lines)
├── defaults.py        (124 lines)
├── commands.py        (129 lines)
└── README.md          (234 lines)

tools/
└── lint_hardcoded_strings.py (384 lines)

docs/development/
└── LINTING.md         (+149 lines)

Configuration:
├── .pre-commit-config.yaml (+12 lines)
├── Makefile              (+7 lines)
└── CLAUDE.md            (+32 lines)
```

## 🎬 Next Steps

After merging this PR:

1. **Install pre-commit hooks** (for team members):
   ```bash
   make pre-commit-install
   ```

2. **Run the linter** to see current state:
   ```bash
   make lint-hardcoded-strings
   ```

3. **Gradual migration** - Update files as they're modified
4. **CI/CD integration** - Consider adding to CI pipeline
5. **Team training** - Share documentation with team members

## 🔗 Related Documentation

- [Linting Guide](docs/development/LINTING.md) - Complete linting documentation
- [Constants README](src/mcli/lib/constants/README.md) - Constants usage guide
- [CLAUDE.md](CLAUDE.md) - Project guidelines for AI assistant

## ✅ Checklist

- [x] Code follows project style guidelines
- [x] Self-reviewed the code
- [x] Documentation updated
- [x] Comments added for complex logic
- [x] No new warnings generated
- [x] Tests pass (manual testing completed)
- [x] Pre-commit hooks configured
- [x] README and guides updated

## 💬 Notes

This PR establishes the foundation for better code quality and maintainability. The constants module can be expanded over time, and the linter ensures new code follows best practices from day one.

The implementation is:
- ✅ Non-breaking (existing code continues to work)
- ✅ Well-documented (multiple documentation sources)
- ✅ Tested (comprehensive manual testing)
- ✅ Extensible (easy to add new constants)
- ✅ Developer-friendly (clear error messages and examples)

---

**Branch:** `claude/audit-hardcoded-strings-linter-011CV5e4GVEvYnjYBnBp5JeB`
**Base:** `main`
**Commits:** 2
- `dd75501` - feat: add centralized constants module and hardcoded strings linter
- `930e537` - docs: update CLAUDE.md with constants module and linter information
