# CLI Tests for MCLI

This directory contains comprehensive tests for all CLI groups and commands in the MCLI application.

## Test Structure

### Individual Test Files

Each CLI group has its own test file:

- `test_webapp.py` - Tests for webapp generation and management commands
- `test_file.py` - Tests for file utility commands
- `test_registry.py` - Tests for Docker registry commands
- `test_repo.py` - Tests for repository management commands
- `test_gcloud.py` - Tests for Google Cloud commands
- `test_videos.py` - Tests for video processing commands
- `test_wakatime.py` - Tests for WakaTime commands
- `test_oi.py` - Tests for OI commands
- `test_self.py` - Tests for self-management commands
- `test_lib.py` - Tests for library commands
- `test_auth.py` - Tests for authentication commands
- `test_workflow.py` - Tests for workflow group and subcommands
- `test_main_app.py` - Tests for main application commands
- `test_all_cli.py` - Comprehensive tests for all CLI groups

### Test Coverage

Each test file covers:

1. **Group Help**: Tests that each CLI group shows help information
2. **Command Help**: Tests that each command shows help information
3. **Required Arguments**: Tests that commands fail gracefully when required arguments are missing
4. **Basic Invocation**: Tests that commands can be invoked (with mocks for side effects)

## Running Tests

### Run All Tests

```bash
# From the project root
python tests/run_tests.py

# Or using pytest directly
pytest tests/ -v
```

### Run Only CLI Tests

```bash
python tests/run_tests.py --cli-only
```

### Run Specific Test File

```bash
# Run webapp tests only
python tests/run_tests.py webapp

# Run all workflow tests
python tests/run_tests.py workflow
```

### Run Specific Test Function

```bash
# Run a specific test function
pytest tests/test_webapp.py::test_webapp_group_help -v
```

## Test Dependencies

The tests require:

- `pytest` - Test framework
- `click` - CLI framework (for testing)
- All MCLI dependencies

Install test dependencies:

```bash
pip install pytest click
```

## Test Patterns

### Basic Test Structure

```python
import pytest
from click.testing import CliRunner
from src.mcli.workflow.webapp.webapp import webapp

def test_webapp_group_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['--help'])
    assert result.exit_code == 0
    assert 'Web application generation and installation commands' in result.output
```

### Testing Required Arguments

```python
def test_generate_missing_required():
    runner = CliRunner()
    result = runner.invoke(webapp, ['generate'])
    assert result.exit_code != 0
    assert 'Missing option' in result.output
```

### Testing Command Help

```python
def test_generate_help():
    runner = CliRunner()
    result = runner.invoke(webapp, ['generate', '--help'])
    assert result.exit_code == 0
    assert 'Generate a template web application' in result.output
```

## CLI Groups Tested

### Workflow Commands

- **webapp**: Generate, install, run, list, delete web applications
- **file**: OXPS to PDF conversion, file search
- **registry**: Docker registry operations (catalog, tags, search, etc.)
- **repo**: Repository analysis, worktree management, commits
- **gcloud**: Google Cloud instance management
- **videos**: Video processing and overlay removal
- **wakatime**: WakaTime integration

### Public Commands

- **oi**: Alpha tunnel creation

### Self Management

- **self**: Command search, template generation, plugin management

### Library Commands

- **lib**: Library utilities
- **auth**: Authentication management

### Main Application

- **main**: Hello, version commands

## Adding New Tests

When adding new CLI commands or groups:

1. Create a new test file: `test_<group_name>.py`
2. Import the CLI group/command
3. Test the group help
4. Test each command's help
5. Test missing required arguments
6. Add the test file to `run_cli_tests()` in `run_tests.py`

### Example for New Command

```python
import pytest
from click.testing import CliRunner
from src.mcli.new_group.new_command import new_group

def test_new_group_help():
    runner = CliRunner()
    result = runner.invoke(new_group, ['--help'])
    assert result.exit_code == 0
    assert 'New group description' in result.output

def test_new_command_help():
    runner = CliRunner()
    result = runner.invoke(new_group, ['new-command', '--help'])
    assert result.exit_code == 0
    assert 'New command description' in result.output

def test_new_command_missing_required():
    runner = CliRunner()
    result = runner.invoke(new_group, ['new-command'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.output
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

- Fast execution (no side effects)
- Isolated tests (no file system dependencies)
- Clear error messages
- Comprehensive coverage

## Troubleshooting

### Import Errors

If you get import errors, ensure:

1. You're running from the project root
2. The Python path includes the `src` directory
3. All dependencies are installed

### Test Failures

Common test failure reasons:

1. **Command signature changed**: Update test to match new command structure
2. **Help text changed**: Update assertions to match new help text
3. **Missing dependencies**: Install required packages
4. **Path issues**: Ensure correct import paths

### Running Tests in Isolation

To run tests in isolation:

```bash
# Run only one test file
pytest tests/test_webapp.py -v

# Run only one test function
pytest tests/test_webapp.py::test_webapp_group_help -v

# Run with more verbose output
pytest tests/test_webapp.py -vv
``` 