# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCLI is a modern Python CLI framework with AI chat capabilities, ML/trading features, and extensible command architecture. The project uses UV for package management, supports multiple deployment modes (wheel, portable binary), and includes integrated dashboards for ML model training and politician trading analysis.

**Current Version:** 7.4.0
**Python Support:** 3.9-3.12
**Package Manager:** UV (preferred) / pip

## Development Commands

### Setup and Installation

```bash
# Initial setup with UV
make setup

# Install package locally (editable mode)
make install

# Install development dependencies
make install-dev

# Install from PyPI
pip install mcli-framework
```

### Testing

```bash
# Basic installation test
make test

# Run unit tests
make test-unit

# Run tests with coverage
make test-cov

# Run fast tests only (skip slow tests)
make test-fast

# Test built executable
make test-binary
```

### Building

```bash
# Build Python wheel
make wheel

# Build portable executable
make portable

# Build binary executable (directory format)
make binary

# Build everything
make build

# Validate build readiness
make validate-build
```

### Code Quality

```bash
# Run all linters (black, isort, flake8, mypy)
make lint

# Auto-format code
make format

# Type checking only
make type-check

# Security checks
make security-check

# Install and run pre-commit hooks
make pre-commit-install
make pre-commit-run
```

### Dashboard (Streamlit)

```bash
# Launch integrated dashboard (default - includes ML + LSH)
make dashboard

# Launch ML training dashboard
make dashboard-training

# Launch Supabase-focused dashboard
make dashboard-supabase

# Launch basic ML dashboard
make dashboard-basic

# Launch via CLI commands
make dashboard-cli
make dashboard-workflow
```

### Maintenance

```bash
# Clean all build artifacts
make clean

# Clean only Python cache files
make clean-pyc

# Clean build artifacts but keep venv
make clean-build

# Show debug information
make debug
```

### CI/CD

```bash
# Trigger GitHub Actions workflows
make ci-trigger-build
make ci-trigger-test

# Watch workflow runs in real-time
make ci-watch

# Show workflow status
make ci-status

# Show workflow logs
make ci-logs
make ci-logs-build
make ci-logs-test
```

## Architecture

### Core Structure

The codebase follows a modular architecture organized into several key areas:

#### 1. Application Layer (`src/mcli/app/`)
- **Entry Point:** `main.py` - Main CLI entry point with dynamic command discovery
- **Command Groups:** Each `*_cmd.py` file defines a command group (e.g., `chat_cmd.py`, `commands_cmd.py`, `visual_cmd.py`)
- **Discovery System:** Commands are dynamically discovered based on `config.toml` configuration

**Key Pattern:** Command discovery reads `config.toml` to determine which directories to scan (`app`, `self`, `workflow`, `public`). New commands placed in these directories are automatically discovered.

#### 2. Library Layer (`src/mcli/lib/`)
- **API:** Daemon client/server, decorators for API exposure
- **Auth:** Multi-cloud credential management (AWS, GCP, Azure, MCLI)
- **UI:** Styling utilities (Rich-based), visual effects
- **Services:** Redis, LSH client, data pipeline
- **Performance:** Rust bridge, uvloop configuration, optimizer
- **Discovery:** Command discovery and registration system

**Important:** The `lib/api/daemon_decorator.py` allows functions to be exposed as daemon API endpoints. The daemon system enables MCLI to run as a background service.

#### 3. Workflow Layer (`src/mcli/workflow/`)
Workflow commands for specific tasks:
- **daemon:** Background service management
- **politician_trading:** Politician trading data collection/analysis
- **model_service:** ML model serving and management
- **lsh_integration:** Locality-sensitive hashing integration
- **scheduler:** Cron/scheduled job management
- **git_commit:** Git automation
- **docker, gcloud, repo, file, sync:** Infrastructure/dev workflows

**Pattern:** Each workflow directory is a self-contained module with its own command implementation.

#### 4. ML/Trading Layer (`src/mcli/ml/`)
Complete ML pipeline for trading/prediction:
- **api:** FastAPI server with routers (predictions, backtest, portfolio, monitoring, etc.)
- **dashboard:** Streamlit dashboards (4 variants: integrated, training, supabase, basic)
- **training:** Model training pipelines
- **backtesting:** Backtest engine and performance metrics
- **monitoring:** Prometheus integration, model monitoring
- **mlops:** MLflow and DVC integration
- **data_ingestion:** Data pipeline for market data
- **features:** Feature engineering
- **predictions:** Prediction engine

**Key Integration:** The ML system integrates with Supabase for data storage and LSH (Legal Services Hub) for job tracking.

#### 5. Chat/AI Layer (`src/mcli/chat/`)
- **chat.py:** Basic chat interface
- **enhanced_chat.py:** Advanced chat with system integration
- **command_rag.py:** Command RAG (Retrieval-Augmented Generation)
- **system_integration.py:** System command integration
- **system_controller.py:** System control interface

**Configuration:** LLM provider is configured in `config.toml`. Supports OpenAI, Anthropic, and local Ollama models. Default is lightweight local models.

#### 6. Self-Management Layer (`src/mcli/self/`)
Commands for managing MCLI itself (updates, configuration, plugins).

### Configuration System

#### Main Config (`src/mcli/config.toml`)
```toml
[paths]
included_dirs = ["app", "self", "workflow", "public"]

[llm]
provider = "local"  # or "openai", "anthropic"
model = "prajjwal1/bert-tiny"
temperature = 0.7
use_lightweight_models = true
```

#### Environment Variables (`.env`)
Key variables:
- `MCLI_ENV` - Environment (development/staging/production)
- `OPENAI_API_KEY` - For GPT models
- `ANTHROPIC_API_KEY` - For Claude
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` - Database access
- `MCLI_TRACE_LEVEL` - Debug tracing (0-3)
- `MCLI_AUTO_OPTIMIZE` - Auto-enable performance optimizations

### Testing Structure

Tests are organized by category:
- `tests/cli/` - CLI command tests
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests

**Test Markers:**
- `@pytest.mark.slow` - Slow tests (skipped with `-m "not slow"`)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.api` - API tests

### Package Entry Points

Defined in `pyproject.toml`:
```toml
[project.scripts]
mcli = "mcli.app.main:main"
mcli-train = "mcli.ml.training.train:main"
mcli-serve = "mcli.ml.serving.serve:main"
mcli-backtest = "mcli.ml.backtesting.run:main"
mcli-optimize = "mcli.ml.optimization.optimize:main"
mcli-dashboard = "mcli.ml.dashboard:main"
```

### Dependencies

**Core:** Click (CLI), Rich (UI), requests, tomli (TOML parser)
**AI:** OpenAI, Anthropic, Ollama
**Async:** FastAPI, uvicorn, uvloop, aiohttp, Redis
**ML:** PyTorch, scikit-learn, MLflow, DVC
**Trading:** yfinance, alpaca-py, PyPortfolioOpt
**Database:** Supabase, SQLAlchemy, PostgreSQL
**Dashboard:** Streamlit
**All features included by default** (GPU support optional via `mcli-framework[gpu]`)

## Development Patterns

### Adding New Commands

1. **Create command file** in appropriate directory (`app/`, `workflow/`, `self/`, or `public/`)
2. **Use Click framework:**
   ```python
   import click
   from mcli.lib.ui.styling import success, error, info

   @click.command()
   @click.option('--name', help='Your name')
   def greet(name):
       """Greet the user."""
       success(f"Hello {name}!")
   ```

3. **Commands are auto-discovered** - No manual registration needed if placed in configured directories

### Using the Logger

```python
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)
logger.info("Info message")
logger.debug("Debug message")
logger.error("Error message")
```

**Tracing:** Set `MCLI_TRACE_LEVEL=1` (function calls), `2` (line-by-line), or `3` (verbose)

### Using UI Styling

```python
from mcli.lib.ui.styling import success, error, info, warning

success("Operation completed!")
error("Something went wrong")
info("FYI: Important information")
warning("Be careful!")
```

### Exposing Functions as Daemon APIs

```python
from mcli.lib.api.daemon_decorator import daemon_route

@daemon_route(method="GET", path="/status")
def get_status():
    """Exposed as daemon API endpoint."""
    return {"status": "ok"}
```

### Working with Supabase

The project uses Supabase for:
- Politician trading data storage
- ML training data
- LSH job tracking

**Key Tables:**
- `politician_trades` - Trading transactions
- `ml_jobs` - ML training jobs
- `lsh_jobs` - Legal Services Hub jobs

**Access Pattern:**
```python
from mcli.lib.services.lsh_client import get_supabase_client

client = get_supabase_client()
result = client.table('politician_trades').select('*').execute()
```

## Important Implementation Details

### Command Discovery Mechanism
The `discover_modules()` function in `src/mcli/app/main.py` scans directories specified in `config.toml`. It:
1. Reads `[paths].included_dirs` from `config.toml`
2. Searches for Python files (excluding `__init__.py`, `setup.py`)
3. Dynamically imports modules as Click command groups
4. Registers commands with the main CLI

**To add new command groups:** Add the directory to `included_dirs` in `config.toml`

### Performance Optimization
- Uses uvloop for async performance
- Includes Rust extensions via `maturin` (see `build_rust.py`)
- Lazy imports for faster startup
- Caching via Redis (optional)

### Build System
- **UV-based:** Modern, fast dependency management
- **Multi-platform:** Supports macOS, Linux (Windows partial)
- **Caching:** Build cache in `.build_cache/` for faster rebuilds
- **Wheel naming:** Automatically sanitizes wheel names (replaces `+` with `_`)

### Database Migrations
Located in `supabase/migrations/`. Apply using:
```bash
# Run migration script
python scripts/run_migration.py
```

### Shell Completion
```bash
# Install completion for your shell
mcli completion install

# Check status
mcli completion status
```

## Common Tasks

### Running a Single Test
```bash
# Run specific test file
uv run pytest tests/cli/test_chat_cmd.py -v

# Run specific test function
uv run pytest tests/cli/test_chat_cmd.py::test_chat_help -v
```

### Debugging Import Issues
```bash
# Enable tracing
export MCLI_TRACE_LEVEL=1
mcli --help

# Check Python path
uv run python -c "import sys; print('\n'.join(sys.path))"

# Validate imports
uv run python -c "import mcli; print(mcli.__file__)"
```

### Working with ML Models
```bash
# Train model
mcli-train --config configs/model.yaml

# Run backtest
mcli-backtest --start-date 2024-01-01 --end-date 2024-12-31

# Serve model
mcli-serve --model-path models/best_model.pt --port 8000

# Launch dashboard
mcli-dashboard
# or
make dashboard
```

### Politician Trading Workflow
```bash
# Collect trading data
mcli workflow politician-trading collect

# Analyze trades
mcli workflow politician-trading analyze

# View dashboard
make dashboard-integrated
```

## CI/CD Pipeline

**GitHub Actions Workflows:**
- **build.yml** - Multi-platform builds (Ubuntu, macOS)
- **test.yml** - Multi-version testing (Python 3.9-3.12)

**Triggers:**
- Push to main branch
- Pull requests
- Manual dispatch via `make ci-trigger-*`

## Version Bumping and Publishing

```bash
# Bump version
make bump-version VERSION=7.5.0

# Publish to Test PyPI
make publish-test

# Publish to PyPI (requires PYPI_TOKEN)
make publish
```

## Project-Specific Conventions

1. **All CLI commands use Click** - No argparse or other CLI libraries
2. **Rich for output** - Use Rich for all formatted terminal output
3. **Logger over print** - Use logger instead of print statements
4. **Async-first** - Prefer async functions where I/O is involved
5. **Type hints** - Use type hints for function signatures
6. **Docstrings** - Include docstrings for public functions/classes
7. **Error handling** - Use try/except with proper logging
8. **Config over hardcoding** - Use `config.toml` or `.env` for configuration

## Troubleshooting

### "Module not found" errors
- Ensure virtual environment is activated: `source .venv/bin/activate`
- Reinstall in editable mode: `make install`
- Check `config.toml` has correct `included_dirs`

### "Command not found" after adding new command
- Verify file is in a discovered directory (`app/`, `workflow/`, etc.)
- Check `config.toml` includes the directory
- Restart shell if using shell completion

### Dashboard not loading
- Check Supabase credentials in `.env`
- Verify port is not in use: `lsof -i :8501`
- Check Streamlit logs in terminal

### Performance issues
- Enable optimizations: `export MCLI_AUTO_OPTIMIZE=true`
- Use uvloop: Already enabled by default
- Check Redis connection if using caching

## Resources

- **Repository:** https://github.com/lefv/mcli
- **PyPI:** https://pypi.org/project/mcli-framework/
- **Documentation:** https://github.com/lefv/mcli#readme
- **Issues:** https://github.com/lefv/mcli/issues
