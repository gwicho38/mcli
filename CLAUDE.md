# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCLI is a modern CLI framework with AI chat capabilities, command management, and extensible architecture. It combines Python and Rust for high-performance command-line operations, with features including OpenAI/Anthropic integration, workflow automation, ML/trading capabilities, and Streamlit dashboards.

## Build & Development Commands

### Setup
```bash
make setup                  # Setup UV environment with dependencies
make install-dev           # Install development dependencies
cp .env.example .env       # Configure environment variables
```

### Building
```bash
make wheel                 # Build Python wheel package
make portable              # Build portable executable
make binary                # Build binary executable (directory format)
make validate-build        # Comprehensive build validation (wheel + executable + tests)
```

### Testing
```bash
make test                  # Basic installation and functionality test
make test-unit             # Run unit tests with pytest
make test-cov              # Run tests with coverage
make test-fast             # Run fast tests only (skip slow tests)
make test-binary           # Test the built executable

# Run specific test categories
pytest tests/unit          # Unit tests only
pytest tests/cli           # CLI tests only
pytest -m "not slow"       # Skip slow tests
pytest -n auto             # Parallel testing

# Using tox for multi-environment testing
tox                        # Run tests on all Python versions (3.9-3.12)
tox -e py311-fast          # Fast tests on Python 3.11
tox -e py311-cov           # Tests with coverage on Python 3.11
tox -e py39,py310,py311,py312  # Run on specific versions
```

### Code Quality
```bash
make lint                  # Run all linting (black, isort, flake8, mypy)
make lint-pylint           # Run pylint (optional, non-blocking)
make format                # Auto-format code (black + isort)
make type-check            # Run mypy type checking
make security-check        # Run security checks (bandit, safety)
make pre-commit-run        # Run all pre-commit hooks

# Using tox for comprehensive checks
tox -e lint                # Run all linters
tox -e type                # Type checking
tox -e security            # Security checks
```

See [Linting Guide](docs/development/LINTING.md) for detailed configuration and usage

### Dashboard
```bash
make dashboard             # Launch integrated ML dashboard (default)
make dashboard-training    # ML training dashboard
make dashboard-supabase    # Supabase-focused dashboard
```

### CI/CD
```bash
make ci-trigger-build      # Trigger GitHub Actions build workflow
make ci-trigger-test       # Trigger GitHub Actions test workflow
make ci-watch              # Watch GitHub Actions runs in real-time
make ci-status             # Show GitHub Actions run status
```

### Maintenance
```bash
make clean                 # Clean all build artifacts
make clean-pyc             # Clean Python cache files only
make clean-build           # Clean build artifacts (keep venv)
```

## Architecture

### Command Discovery
- **Dynamic Loading**: Commands are discovered from `src/mcli/app/`, `src/mcli/self/`, `src/mcli/workflow/`, and `src/mcli/public/`
- **Lazy Loading**: Heavy command groups use `LazyCommand` and `LazyGroup` classes to defer imports
- **Completion-Aware**: Special wrapper `create_completion_aware_lazy_group` for shell completion support
- **Config-Driven**: `config.toml` controls which directories are scanned (default: app, self, workflow, public)

### Module Structure
```
src/mcli/
├── app/                   # Core application commands
│   ├── main.py           # Main entry point, command discovery
│   ├── chat_cmd.py       # Chat command
│   ├── commands_cmd.py   # Command management
│   ├── completion_cmd.py # Shell completion
│   ├── model_cmd.py      # Model management
│   └── video/            # Video processing commands
├── self/                  # Self-management commands (update, performance, etc.)
├── workflow/              # Workflow automation commands
│   ├── daemon/           # Daemon management
│   ├── scheduler/        # Scheduling
│   └── dashboard/        # Dashboard launch
├── lib/                   # Shared libraries
│   ├── api/              # API functionality
│   ├── ui/               # UI components (styling, rich output)
│   ├── logger/           # Logging utilities
│   ├── auth/             # Authentication
│   └── custom_commands.py # User custom commands loader
├── chat/                  # Chat system implementation
├── ml/                    # ML/Trading features
│   ├── training/         # Model training
│   ├── backtesting/      # Backtesting
│   ├── optimization/     # Portfolio optimization
│   ├── dashboard/        # ML dashboards (Streamlit)
│   └── database/         # Database interactions
└── public/               # Public API commands
```

### Key Design Patterns
1. **Lazy Loading**: Use `LazyCommand`/`LazyGroup` for heavy imports to improve startup time
2. **Click Commands**: All CLI commands use the Click framework with decorator-based definitions
3. **Rich UI**: Use `mcli.lib.ui.styling` for colored output (success, error, info, warning)
4. **Environment Config**: Heavy use of `.env` files for configuration (see `.env.example`)
5. **Rust Extensions**: Performance-critical code in `mcli_rust/` (TF-IDF, file watching, etc.)

## Important Implementation Notes

### Adding New Commands
1. Commands in `src/mcli/app/`, `src/mcli/self/`, `src/mcli/workflow/`, or `src/mcli/public/` are auto-discovered
2. Use Click decorators: `@click.command()` or `@click.group()`
3. Import UI helpers: `from mcli.lib.ui.styling import success, error, info, warning`
4. Heavy imports should use lazy loading pattern (see `main.py:_add_lazy_commands()`)

### Workflow Commands
- Workflow commands are in `src/mcli/workflow/`
- Main entry point is `workflow.py` which creates a Click group
- Subcommands are organized by domain (daemon, politician_trading, scheduler, etc.)
- Skip individual workflow submodules in discovery to avoid duplicate commands (see `main.py:109-116`)

### Testing Requirements
- Current minimum coverage: 30% (configured in `pyproject.toml`, goal: 80%)
- Tests in `tests/` organized by category: unit, cli, integration, e2e, performance
- Use pytest markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.cli`, `@pytest.mark.unit`
- Additional markers: `@pytest.mark.performance`, `@pytest.mark.requires_redis`, etc.
- All fixtures in `tests/fixtures/` are globally available
- Integration tests requiring external services are skipped by default (use markers)
- Test suite status: 834 passing, 0 failing, 271 skipped (100% pass rate)
- See [Testing Guide](docs/development/TESTING.md) for comprehensive testing documentation

### Environment Variables
Key variables from `.env`:
- `MCLI_ENV`: Environment (development/staging/production)
- `DEBUG`: Debug mode toggle
- `MCLI_TRACE_LEVEL`: Runtime tracing (0=off, 1=basic, 2=detailed, 3=verbose)
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: For chat features
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`: For database features
- `MCLI_AUTO_OPTIMIZE`: Performance optimization toggle

### ML/Trading Features
- Politician trading workflows in `src/mcli/workflow/politician_trading/`
- Scrapers for US states, California, EU, UK, corporate registries
- Supabase integration for data storage
- MLflow tracking for experiments
- Streamlit dashboards for visualization

### Build System Details
- **UV**: Fast Python package manager (preferred over pip)
- **Wheel**: Standard Python package format
- **Portable Executable**: Single-file Python executable
- **Cache System**: Build cache in `.build_cache/` for faster rebuilds
- **Multi-Platform**: Supports macOS (arm64/x86_64), Ubuntu, Windows

### Shell Completion
- Install with: `mcli self completion install`
- Auto-detects bash/zsh/fish
- Completion scripts in `src/mcli/self/completion_cmd.py`
- Lazy groups need special wrapper for completion support

### Pre-commit Hooks
- Black: Code formatting (line length: 100)
- isort: Import sorting (black profile)
- flake8: Linting
- mypy: Type checking
- bandit: Security scanning
- Install hooks: `make pre-commit-install`

## CI/CD Pipeline

### GitHub Actions Workflows
- **ci.yml**: Main CI pipeline (lint, test, build, security scan)
- **build.yml**: Multi-platform builds
- **test.yml**: Multi-version Python testing (3.9-3.12)
- **ml-pipeline.yml**: ML workflow testing
- **publish.yml**: PyPI publishing
- **security.yml**: Security scanning

### CI Test Matrix
- OS: Ubuntu, macOS
- Python: 3.9, 3.10, 3.11, 3.12
- Rust extensions tested on all platforms

## Common Gotchas

1. **Import Order**: Use isort with black profile (see `pyproject.toml`)
2. **Lazy Loading**: Heavy imports (torch, streamlit, etc.) must be lazy-loaded
3. **Workflow Discovery**: Individual workflow submodules are skipped to avoid duplicate commands
4. **Version Bumping**: Edit `pyproject.toml` version field directly
5. **Rust Extensions**: Run `maturin develop` in `mcli_rust/` for local development
6. **Test Markers**: Mark slow tests with `@pytest.mark.slow` to allow skipping
7. **Integration Tests**: Mark tests requiring external services (Redis, Ollama, Supabase) with appropriate markers
8. **Test Environment**: Set `MCLI_INCLUDE_TEST_COMMANDS=1` when testing custom command loading
9. **Environment Setup**: Always copy `.env.example` to `.env` before development
10. **Multi-Environment Testing**: Use `tox` to test across Python 3.9-3.12

## Python Version Support

- **Minimum**: Python 3.9
- **Tested**: 3.9, 3.10, 3.11, 3.12
- **Recommended**: 3.11 (best performance)

## Dependencies Management

- **Core**: Click, Rich, requests, tomli (always installed)
- **Optional Groups**: chat, async-extras, video, documents, viz, database, ml, gpu, monitoring, streaming, dashboard, web
- **Development**: pytest, black, isort, mypy, ruff, pylint, pre-commit (in `[dev]` extra)
- **All dependencies** now included by default (as of v7.0.0), optional groups are for legacy compatibility
- **Testing**: pytest-asyncio, pytest-cov, pytest-mock, pytest-xdist for parallel testing
- **Security**: bandit, safety for security scanning
- **Multi-Environment**: tox for testing across Python versions

## Performance Considerations

- Startup time optimization via lazy loading (see `LazyCommand`/`LazyGroup`)
- Runtime tracing available with `MCLI_TRACE_LEVEL` for debugging
- Rust extensions for performance-critical paths
- Build caching in `.build_cache/` to speed up rebuilds
- Parallel testing with `pytest -n auto`

## Release Process

1. Update version in `pyproject.toml`
2. Run `make validate-build` to ensure everything works
3. Run full test suite: `make test-cov` or `tox`
4. Create release notes in `docs/releases/X.Y.Z.md` following the format in previous releases
5. Update `docs/setup/INSTALL.md` with new version number
6. Update `docs/INDEX.md` if needed
7. Tag release: `git tag vX.Y.Z`
8. Push tags: `git push origin vX.Y.Z`
9. GitHub Actions will automatically build and publish

**Release Notes Template**: See [docs/releases/7.10.2.md](docs/releases/7.10.2.md) for the expected format

## Entry Points

Defined in `pyproject.toml [project.scripts]`:
- `mcli`: Main CLI (`mcli.app.main:main`)
- `mcli-train`: ML training (`mcli.ml.training.train:main`)
- `mcli-serve`: ML serving (`mcli.ml.serving.serve:main`)
- `mcli-backtest`: Backtesting (`mcli.ml.backtesting.run:main`)
- `mcli-optimize`: Portfolio optimization (`mcli.ml.optimization.optimize:main`)
- `mcli-dashboard`: Dashboard launcher (`mcli.ml.dashboard:main`)
