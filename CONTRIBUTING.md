# Contributing to MCLI

Thank you for your interest in contributing to MCLI! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Development Workflow](#development-workflow)
- [Code of Conduct](#code-of-conduct)

## Getting Started

### Prerequisites

- Python 3.9 or higher
- [UV](https://docs.astral.sh/uv/) (recommended) or pip
- Git
- A GitHub account

### First Time Setup

1. **Fork the repository** on GitHub
2. **Clone your fork locally:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcli.git
   cd mcli
   ```

3. **Set up the development environment:**
   ```bash
   # Setup environment
   make setup

   # Or manually with UV
   uv venv
   uv pip install -e ".[dev]"

   # Configure environment variables
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Install pre-commit hooks:**
   ```bash
   make pre-commit-install
   ```

5. **Verify your setup:**
   ```bash
   make test
   make lint
   ```

## Development Setup

### Environment Configuration

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure required variables in `.env`:**
   ```bash
   # Required for AI chat functionality
   OPENAI_API_KEY=your-openai-api-key-here
   ANTHROPIC_API_KEY=your-anthropic-api-key-here

   # Required for politician trading features (if developing those)
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key-here
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key-here

   # Development settings
   MCLI_TRACE_LEVEL=1
   MCLI_DEBUG=true
   ```

### Available Make Commands

```bash
# Setup and Installation
make setup                  # Setup UV environment
make install-dev           # Install development dependencies

# Code Quality
make lint                   # Run all linting tools
make format                 # Auto-format code
make type-check            # Run mypy type checking
make security-check        # Run security checks
make pre-commit-run        # Run pre-commit hooks

# Testing
make test                   # Basic installation test
make test-unit             # Run unit tests
make test-cov              # Run tests with coverage
make test-cov-report       # Generate coverage report
make test-fast             # Run fast tests only

# Maintenance
make clean                 # Clean all build artifacts
make clean-pyc             # Clean Python cache files
```

## Code Style Guidelines

### Python Code Style

We use several tools to maintain consistent code style:

- **Black** for code formatting (line length: 100)
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **bandit** for security checks

### Formatting Rules

1. **Line length:** Maximum 100 characters
2. **Imports:** Use isort with black profile
3. **Type hints:** Required for public functions and methods
4. **Docstrings:** Use Google style docstrings

### Example Code Style

```python
from typing import List, Optional

import click
from rich.console import Console

from mcli.lib.ui.styling import success, error


def process_items(
    items: List[str],
    filter_empty: bool = True,
    console: Optional[Console] = None
) -> List[str]:
    """Process a list of items with optional filtering.

    Args:
        items: List of string items to process
        filter_empty: Whether to filter out empty strings
        console: Optional console for output

    Returns:
        Processed list of items

    Raises:
        ValueError: If items list is None
    """
    if items is None:
        raise ValueError("Items list cannot be None")

    if filter_empty:
        items = [item for item in items if item.strip()]

    return items
```

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality:

```bash
# Install hooks (one time setup)
make pre-commit-install

# Run hooks manually on all files
make pre-commit-run

# Update hooks
make pre-commit-update
```

## Testing Requirements

### Test Coverage

- **Minimum coverage:** 80%
- **Test types:** Unit tests, integration tests, CLI tests
- **Test files:** Place in `tests/` directory with `test_*.py` naming

### Running Tests

```bash
# Run all tests
make test-unit

# Run with coverage
make test-cov

# Run fast tests only (skip slow tests)
make test-fast

# Generate and view coverage report
make test-cov-report
```

### Writing Tests

1. **Use pytest** for all tests
2. **Mark slow tests** with `@pytest.mark.slow`
3. **Use fixtures** for common setup
4. **Test both success and error cases**

Example test:

```python
import pytest
from mcli.lib.ui.styling import success

def test_success_message():
    """Test success message formatting."""
    result = success("Test message")
    assert "Test message" in result
    assert "[green]" in result

@pytest.mark.slow
def test_integration_feature():
    """Test integration with external service."""
    # Slow integration test
    pass
```

## Pull Request Process

### Before Submitting

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

3. **Run quality checks:**
   ```bash
   make lint
   make test-cov
   make security-check
   ```

4. **Update documentation** if needed

### PR Requirements

- [ ] **All tests pass:** `make test-cov`
- [ ] **Code is linted:** `make lint`
- [ ] **Security checks pass:** `make security-check`
- [ ] **Coverage maintained:** At least 80% coverage
- [ ] **Documentation updated:** For new features
- [ ] **Commit messages follow convention:** See [Commit Messages](#commit-messages)

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(chat): add support for streaming responses
fix(cli): resolve argument parsing issue
docs(readme): update installation instructions
test(auth): add tests for token validation
```

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Coverage maintained

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

## Issue Reporting

### Bug Reports

Use the bug report template and include:

- **Environment details:** OS, Python version, MCLI version
- **Steps to reproduce:** Clear, numbered steps
- **Expected behavior:** What should happen
- **Actual behavior:** What actually happens
- **Error messages:** Full error logs
- **Additional context:** Screenshots, config files

### Feature Requests

Use the feature request template and include:

- **Problem description:** What problem does this solve?
- **Proposed solution:** How should it work?
- **Alternatives considered:** Other approaches you've thought about
- **Additional context:** Mockups, examples, use cases

## Development Workflow

### Branching Strategy

- `main`: Production-ready code
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation changes
- `chore/*`: Maintenance tasks

### Local Development

1. **Start with latest main:**
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create feature branch:**
   ```bash
   git checkout -b feature/new-feature
   ```

3. **Develop with quality checks:**
   ```bash
   # Make changes
   make format  # Auto-format code
   make lint    # Check code quality
   make test    # Run tests
   ```

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/new-feature
   ```

5. **Create pull request** on GitHub

### Release Process

1. Version bumping is handled by maintainers
2. Releases are automated through GitHub Actions
3. Changelog is maintained automatically

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code.

## Getting Help

- **GitHub Issues:** For bugs and feature requests
- **GitHub Discussions:** For questions and general discussion
- **Documentation:** Check the [README](README.md) and docs/

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Project documentation

Thank you for contributing to MCLI! 🚀