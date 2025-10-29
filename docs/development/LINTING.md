# Code Quality and Linting Guide

This document describes the linting and code quality tools configured for the MCLI project.

## Overview

MCLI uses multiple linting tools to maintain code quality:

- **Black** - Code formatting
- **isort** - Import sorting
- **Flake8** - Style guide enforcement
- **MyPy** - Static type checking
- **Pylint** - Code analysis (optional)
- **Bandit** - Security linting
- **Pre-commit** - Git hooks for automated checks

## Quick Start

### Running All Linters

```bash
# Run all linting tools
make lint

# Auto-format code
make format

# Run type checking only
make type-check

# Run security checks
make security-check

# Run pylint (optional)
make lint-pylint
```

### Installing Pre-commit Hooks

```bash
# Install git hooks
make pre-commit-install

# Run hooks on all files
make pre-commit-run

# Update hooks to latest versions
make pre-commit-update
```

## Tool Configuration

### Black (Code Formatting)

**Configuration:** `pyproject.toml` under `[tool.black]`

- **Line length:** 100 characters
- **Python version:** 3.9+
- **Excludes:** `.git`, `.venv`, `build`, `dist`, etc.

```bash
# Check formatting
black --check src/ tests/

# Auto-format
black src/ tests/
```

### isort (Import Sorting)

**Configuration:** `pyproject.toml` under `[tool.isort]`

- **Profile:** black (compatible with Black)
- **Line length:** 100 characters
- **Sections:** FUTURE, STDLIB, THIRDPARTY, FIRSTPARTY, LOCALFOLDER

```bash
# Check import sorting
isort --check-only src/ tests/

# Auto-sort imports
isort src/ tests/
```

### Flake8 (Style Guide Enforcement)

**Configuration:** `.flake8`

- **Line length:** 100 characters
- **Enabled plugins:**
  - pycodestyle (E, W)
  - pyflakes (F)
  - flake8-bugbear (B)
  - flake8-comprehensions (C4)
  - flake8-simplify (SIM)
  - flake8-docstrings (D)
- **Max complexity:** 10
- **Docstring convention:** Google style

```bash
# Run flake8
flake8 src/ tests/
```

#### Ignored Errors

- **E203** - Whitespace before ':' (conflicts with Black)
- **W503** - Line break before binary operator (conflicts with Black)
- **E501** - Line too long (handled by Black)
- **W504** - Line break after binary operator

#### Per-file Ignores

- Test files: Ignore docstring requirements (D100-D107)
- `__init__.py` files: Ignore module docstring (D104)
- Script files: Ignore docstring requirements

### MyPy (Static Type Checking)

**Configuration:** `pyproject.toml` under `[tool.mypy]`

- **Python version:** 3.9+
- **Strict equality:** Enabled
- **Warn on:**
  - Return any
  - Unused configs
  - Redundant casts
  - Unused ignores
  - No return
  - Unreachable code

```bash
# Run mypy
mypy src/
```

#### Module-specific Configuration

- **Tests, scripts, docs:** Errors ignored
- **Workflow modules:** Less strict on return types
- **Optional dependencies:** Missing imports ignored for `ollama`, `streamlit`, `torch`, etc.

### Pylint (Code Analysis)

**Configuration:** `.pylintrc`

- **Minimum score:** 7.0
- **Line length:** 100 characters
- **Naming conventions:** snake_case for functions/variables, PascalCase for classes

```bash
# Run pylint (may produce warnings)
pylint src/mcli/ --rcfile=.pylintrc

# Or use make target
make lint-pylint
```

#### Disabled Checks

Pylint is configured to disable checks that:
- Conflict with Black formatting
- Are overly restrictive for Click-based CLI code
- Duplicate Flake8's functionality
- Are handled by other tools

### Bandit (Security)

```bash
# Run security checks
bandit -r src/

# Or use make target
make security-check
```

### Safety (Dependency Vulnerability Scanning)

```bash
# Check for vulnerable dependencies
safety check

# Or use make target
make security-check
```

## Pre-commit Hooks

The project uses pre-commit hooks to automatically run linters before each commit.

### Installation

```bash
make pre-commit-install
```

### Configuration

**File:** `.pre-commit-config.yaml`

Hooks run on every commit:
1. Black formatting
2. isort import sorting
3. Flake8 linting
4. MyPy type checking

### Manual Execution

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Update hooks
pre-commit autoupdate
```

## IDE Integration

### VS Code

Install these extensions:
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Black Formatter** (ms-python.black-formatter)
- **isort** (ms-python.isort)
- **Flake8** (ms-python.flake8)
- **Mypy Type Checker** (ms-python.mypy-type-checker)

Configure in `.vscode/settings.json`:

```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.pylintEnabled": false,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. Go to **Settings → Tools → Black**
2. Enable "On save"
3. Go to **Settings → Editor → Inspections**
4. Enable flake8, mypy, and other linters

## CI/CD Integration

All linting checks run automatically in GitHub Actions:

```yaml
# .github/workflows/ci.yml
- name: Check code formatting with Black
  run: black --check --diff src/

- name: Check import sorting with isort
  run: isort --check-only --diff src/

- name: Type checking with mypy
  run: mypy src/ --ignore-missing-imports
```

## Common Issues and Solutions

### Black and Flake8 Conflicts

**Problem:** Flake8 complains about formatting that Black enforces.

**Solution:** The `.flake8` config already ignores conflicting errors (E203, W503, E501, W504).

### Import Sorting Issues

**Problem:** isort and Black disagree on import formatting.

**Solution:** Use `profile = "black"` in isort config (already configured).

### MyPy Missing Imports

**Problem:** MyPy can't find third-party libraries.

**Solution:** Add to mypy overrides in `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["your_module.*"]
ignore_missing_imports = true
```

### Pylint Too Strict

**Problem:** Pylint produces too many warnings.

**Solution:** Pylint is optional. Use `make lint-pylint` only when needed. Main linting uses Flake8.

### Pre-commit Hooks Too Slow

**Problem:** Hooks take too long to run.

**Solution:**

```bash
# Skip hooks for a single commit
git commit --no-verify

# Or disable specific hooks in .pre-commit-config.yaml
```

## Best Practices

### Before Committing

1. **Format code:** `make format`
2. **Run linters:** `make lint`
3. **Fix issues:** Address any errors or warnings
4. **Commit:** Pre-commit hooks will run automatically

### During Development

1. **Use IDE integration** for real-time feedback
2. **Run `make format`** periodically
3. **Check types** with `make type-check` before pushing

### Before Pull Requests

1. **Run all checks:** `make lint && make type-check && make security-check`
2. **Ensure tests pass:** `make test`
3. **Check coverage:** `make test-cov`
4. **Review changes:** `git diff`

## Configuration Files Reference

- **`.flake8`** - Flake8 configuration
- **`.pylintrc`** - Pylint configuration
- **`pyproject.toml`** - Black, isort, mypy, pytest, coverage configuration
- **`.pre-commit-config.yaml`** - Pre-commit hooks

## Customization

### Adding New Ignore Rules

**Flake8:**
```ini
# .flake8
ignore =
    E203,
    YOUR_NEW_CODE
```

**MyPy:**
```toml
# pyproject.toml
[[tool.mypy.overrides]]
module = ["your_module.*"]
ignore_errors = true
```

**Pylint:**
```ini
# .pylintrc
disable=
    your-check-name,
```

### Adjusting Line Length

To change from 100 to a different length, update:
- `pyproject.toml` → `[tool.black]` → `line-length`
- `pyproject.toml` → `[tool.isort]` → `line_length`
- `.flake8` → `max-line-length`
- `.pylintrc` → `[FORMAT]` → `max-line-length`

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pylint Documentation](https://pylint.pycqa.org/)
- [Pre-commit Documentation](https://pre-commit.com/)
