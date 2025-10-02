# MCLI Framework Testing Guide

Comprehensive testing documentation for mcli-framework.

## 📁 Test Organization

```
tests/
├── unit/              # Unit tests - fast, isolated
├── integration/       # Integration tests - components working together
├── cli/               # CLI command tests
├── e2e/               # End-to-end workflow tests
├── performance/       # Benchmark and performance tests
├── property/          # Property-based tests (Hypothesis)
├── fixtures/          # Shared test fixtures
└── conftest.py        # Global pytest configuration
```

## 🚀 Quick Start

```bash
# Run all tests
pytest

# Run specific category
pytest tests/unit
pytest tests/cli

# Run with coverage
pytest --cov=src/mcli --cov-report=html

# Run fast tests only
pytest -m "not slow"

# Run in parallel
pytest -n auto
```

## 📚 Full Documentation

For complete testing guide, see [Testing Strategy Document](TEST_CATEGORIZATION.md)

## ✨ Key Features

- **Organized Structure**: Tests categorized by scope and purpose
- **Shared Fixtures**: Reusable components in `fixtures/`
- **Multiple Markers**: unit, integration, cli, e2e, slow, api
- **Coverage Tracking**: 80%+ target with detailed reports
- **CI Integration**: Automated testing on push and PR

## 📊 Coverage Goals

| Module | Target | Priority |
|--------|--------|----------|
| mcli/self/ | 95% | Critical |
| mcli/app/model_cmd.py | 95% | Critical |
| mcli/lib/ | 90% | High |
| mcli/chat/ | 85% | High |

## 🔧 Available Fixtures

All fixtures from `tests/fixtures/` are globally available:

- **model_fixtures**: Model server mocks, PyPI responses
- **chat_fixtures**: OpenAI, Anthropic, Ollama mocks
- **cli_fixtures**: CliRunner, config files, env vars
- **data_fixtures**: JSON, CSV, log data generators
- **db_fixtures**: Database mocks and SQLite DBs

## 💡 Best Practices

✅ Write tests for all new features  
✅ Test both success and failure paths  
✅ Use descriptive test names  
✅ Keep tests independent  
✅ Mock external dependencies  

❌ Don't test implementation details  
❌ Don't skip tests for "simple" code  
❌ Don't ignore flaky tests  

## 🏃 Common Commands

```bash
# Coverage report
pytest --cov=src/mcli --cov-report=term-missing

# Specific test file
pytest tests/cli/test_self_cmd.py

# Specific test function
pytest tests/cli/test_self_cmd.py::test_update_help

# With markers
pytest -m integration
pytest -m "cli and not slow"

# Generate HTML report
pytest --cov=src/mcli --cov-report=html
open htmlcov/index.html
```

## 📖 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [Coverage.py](https://coverage.readthedocs.io/)
