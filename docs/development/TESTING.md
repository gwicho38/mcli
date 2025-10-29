# Testing Guide

This document describes the testing infrastructure and practices for the MCLI project.

## Test Infrastructure Status

**Current State (2025-10-29):**
- ✅ 1,129 tests collected successfully
- ✅ 847 tests passing (75%)
- ✅ Comprehensive fixture system in place
- ✅ Test markers configured
- ✅ Pytest configuration complete
- ⚠️ 135 tests failing (mostly integration tests requiring external services)
- ⚠️ 126 tests skipped (missing optional dependencies)

## Quick Start

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run only fast tests (skip slow tests)
make test-fast

# Run specific test markers
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests
pytest -m "cli"             # CLI tests only
```

### Test Organization

```
tests/
├── conftest.py           # Global pytest configuration and fixtures
├── fixtures/             # Shared test fixtures
│   ├── cli_fixtures.py
│   ├── chat_fixtures.py
│   ├── data_fixtures.py
│   ├── db_fixtures.py
│   └── model_fixtures.py
├── unit/                 # Unit tests (fast, isolated)
├── integration/          # Integration tests (external services)
├── cli/                  # CLI command tests
├── e2e/                  # End-to-end tests
└── performance/          # Performance benchmarks
```

## Test Markers

Tests can be marked with these markers (defined in `pytest.ini`):

### Standard Markers

- **`@pytest.mark.unit`** - Fast, isolated unit tests
- **`@pytest.mark.integration`** - Integration tests with external systems
- **`@pytest.mark.cli`** - CLI command tests
- **`@pytest.mark.e2e`** - End-to-end workflow tests
- **`@pytest.mark.slow`** - Slow-running tests
- **`@pytest.mark.api`** - API tests
- **`@pytest.mark.performance`** - Performance benchmarks

### Dependency Markers

- **`@pytest.mark.requires_redis`** - Requires Redis server
- **`@pytest.mark.requires_ollama`** - Requires Ollama
- **`@pytest.mark.requires_supabase`** - Requires Supabase
- **`@pytest.mark.requires_mlflow`** - Requires MLflow
- **`@pytest.mark.requires_network`** - Requires network access

### Example Usage

```python
import pytest

@pytest.mark.unit
def test_basic_function():
    """Fast unit test."""
    assert 1 + 1 == 2

@pytest.mark.integration
@pytest.mark.requires_redis
def test_redis_connection():
    """Integration test requiring Redis."""
    # Test code here

@pytest.mark.slow
@pytest.mark.integration
def test_full_workflow():
    """Slow integration test."""
    # Test code here
```

## Fixtures

### Global Fixtures (in conftest.py)

All these fixtures are automatically available in any test:

#### Environment Fixtures

```python
def test_with_mock_env(mock_env):
    """Use clean test environment."""
    assert mock_env["MCLI_ENV"] == "test"
```

#### Mock Service Fixtures

```python
def test_with_openai(mock_openai):
    """Test with mocked OpenAI."""
    response = mock_openai.chat.completions.create(...)

def test_with_ollama(mock_ollama):
    """Test with mocked Ollama."""
    response = mock_ollama.generate(...)

def test_with_redis(mock_redis):
    """Test with mocked Redis."""
    assert mock_redis.ping() is True

def test_with_supabase(mock_supabase):
    """Test with mocked Supabase."""
    data = mock_supabase.table("test").select("*").execute()
```

#### Configuration Fixtures

```python
def test_with_temp_config(temp_config_file):
    """Test with temporary config file."""
    # temp_config_file is a Path to a temporary config.toml
```

### Fixture Categories (in tests/fixtures/)

**CLI Fixtures** (`cli_fixtures.py`)
- `cli_runner` - ClickTestingCliRunner for CLI tests
- `isolated_filesystem` - Temporary filesystem
- `mock_click_context` - Mock Click context

**Chat Fixtures** (`chat_fixtures.py`)
- `mock_chat_session` - Mock chat session
- `mock_chat_history` - Mock chat history
- `sample_messages` - Sample chat messages

**Data Fixtures** (`data_fixtures.py`)
- `sample_stock_data` - Sample stock/trading data
- `sample_portfolio` - Sample portfolio
- `sample_predictions` - Sample ML predictions

**Database Fixtures** (`db_fixtures.py`)
- `db_session` - Database session
- `test_db` - Test database
- `clean_db` - Clean database state

**Model Fixtures** (`model_fixtures.py`)
- `mock_model` - Mock ML model
- `sample_model_data` - Sample training data

## Writing Tests

### Unit Tests

Unit tests should be:
- Fast (< 1 second each)
- Isolated (no external dependencies)
- Deterministic (same result every time)

```python
# tests/unit/test_example.py
import pytest
from mcli.lib.some_module import some_function

@pytest.mark.unit
def test_some_function():
    """Test some_function with valid input."""
    result = some_function("input")
    assert result == "expected"

@pytest.mark.unit
def test_some_function_with_invalid_input():
    """Test some_function with invalid input."""
    with pytest.raises(ValueError):
        some_function(None)
```

### Integration Tests

Integration tests may:
- Take longer to run
- Require external services
- Be marked with `@pytest.mark.slow`

```python
# tests/integration/test_example.py
import pytest

@pytest.mark.integration
@pytest.mark.requires_redis
def test_redis_integration(mock_redis):
    """Test Redis integration."""
    # Use mock_redis fixture or real Redis if available
    assert mock_redis.ping() is True
```

### CLI Tests

```python
# tests/cli/test_example.py
import pytest
from click.testing import CliRunner
from mcli.app.main import cli

@pytest.mark.cli
def test_cli_command():
    """Test CLI command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['version'])

    assert result.exit_code == 0
    assert 'mcli' in result.output.lower()
```

### Parametrized Tests

```python
@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input, expected):
    """Test uppercase conversion."""
    assert input.upper() == expected
```

## Test Isolation

### Mocking External Services

Always mock external services in unit tests:

```python
from unittest.mock import patch, MagicMock

@pytest.mark.unit
def test_with_mocked_api():
    """Test with mocked API call."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "test"}

        # Your test code here
        result = call_external_api()

        assert result == {"data": "test"}
        mock_get.assert_called_once()
```

### Using Optional Dependencies

For tests requiring optional dependencies:

```python
import pytest
from mcli.lib.optional_deps import optional_import

ollama, OLLAMA_AVAILABLE = optional_import("ollama")

@pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="Requires ollama")
@pytest.mark.integration
def test_ollama_integration():
    """Test Ollama integration (skipped if not available)."""
    # Test code using ollama
```

### Temporary Files and Directories

```python
import pytest
from pathlib import Path

@pytest.mark.unit
def test_with_temp_files(tmp_path):
    """Test using temporary directory."""
    # tmp_path is a pathlib.Path to a temporary directory
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    assert test_file.read_text() == "test content"
```

## Coverage

### Running Coverage

```bash
# Run tests with coverage
make test-cov

# Generate HTML report
make test-cov-report

# View coverage report
open htmlcov/index.html
```

### Coverage Configuration

Configuration in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/mcli"]
omit = ["*/tests/*", "*/__pycache__/*", "*/venv/*"]
branch = true

[tool.coverage.report]
fail_under = 30.0
show_missing = true
precision = 2
```

### Coverage Goals

- **Current:** ~8-10% (baseline)
- **Target:** 30% (milestone, see issue #68)
- **Core modules:** 95% coverage required
  - `mcli/self/`
  - `mcli/app/model_cmd.py`

## Common Testing Patterns

### Testing Click Commands

```python
from click.testing import CliRunner
from mcli.app.main import cli

def test_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['command', '--option', 'value'])

    assert result.exit_code == 0
    assert 'expected output' in result.output
```

### Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result == expected
```

### Testing Exceptions

```python
def test_exception():
    """Test that function raises expected exception."""
    with pytest.raises(ValueError, match="expected error message"):
        function_that_raises()
```

### Testing File Operations

```python
def test_file_operations(tmp_path):
    """Test file read/write operations."""
    test_file = tmp_path / "test.json"

    # Write
    write_json(test_file, {"key": "value"})

    # Read
    data = read_json(test_file)
    assert data == {"key": "value"}
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:
- Every push to main/develop
- Every pull request
- Manual trigger via workflow_dispatch

```yaml
# .github/workflows/ci.yml
- name: Run Python tests with coverage
  run: |
    pytest tests/ -v --tb=short --cov=src/mcli --cov-report=xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
```

## Troubleshooting

### Import Errors

**Problem:** Tests can't import modules from `src/mcli`

**Solution:** The `conftest.py` adds `src/` to the Python path. Ensure you're running pytest from the project root:

```bash
# From project root
pytest tests/

# Not from tests/ directory
```

### Fixture Not Found

**Problem:** Pytest can't find a fixture

**Solution:** Check that fixtures are:
1. Defined in `conftest.py` or a fixture file
2. Imported in `pytest_plugins` list
3. Named correctly (no typos)

### Slow Tests

**Problem:** Test suite takes too long

**Solution:** Use markers to skip slow tests during development:

```bash
# Skip slow tests
pytest -m "not slow"

# Run only fast unit tests
pytest -m unit
```

### External Service Tests Failing

**Problem:** Tests requiring Redis/Ollama/etc. are failing

**Solution:** Either:
1. Install and run the required service
2. Skip those tests: `pytest -m "not requires_redis"`
3. Use mocks (recommended for unit tests)

### Coverage Too Low

**Problem:** Coverage below threshold

**Solution:**
1. Add tests for uncovered code
2. Review exclusions in `pyproject.toml`
3. Check test markers (some tests may be skipped)

## Best Practices

### Test Organization

1. **One test file per module:** `test_module_name.py` for `module_name.py`
2. **Group related tests:** Use test classes for related tests
3. **Clear test names:** Use descriptive names that explain what's being tested
4. **One assertion per test:** Keep tests focused

### Test Writing

1. **Arrange-Act-Assert pattern:**
   ```python
   def test_function():
       # Arrange - set up test data
       input_data = "test"

       # Act - call the function
       result = function(input_data)

       # Assert - verify the result
       assert result == expected
   ```

2. **Use fixtures for setup:** Don't repeat setup code
3. **Mock external dependencies:** Keep tests fast and reliable
4. **Test edge cases:** Don't just test the happy path
5. **Use parametrize for variations:** Reduce code duplication

### Documentation

1. **Docstrings on all tests:** Explain what's being tested
2. **Mark tests appropriately:** Use pytest markers
3. **Comment complex setup:** Explain non-obvious test setup

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Click Testing](https://click.palletsprojects.com/en/8.1.x/testing/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Mocking with unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
