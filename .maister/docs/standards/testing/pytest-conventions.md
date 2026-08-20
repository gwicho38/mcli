## Pytest Conventions

### Mark tests with registered markers; --strict-markers is on
Tests MUST use registered pytest markers; unknown markers fail (`--strict-markers`, `--strict-config`). Registered: `slow`, `integration`, `unit`, `api`, `cli`, `asyncio` (plus dependency markers `requires_redis`/`requires_ollama`/`requires_supabase`/`requires_mlflow`, `performance`, `e2e`). Slow tests must be `@pytest.mark.slow` so `-m "not slow"` can skip them; tests needing external services must carry the matching marker. Confidence 90.

### Organize tests by category under tests/
`testpaths = ["tests"]`, organized into category subdirectories: `unit/`, `cli/`, `integration/`, `e2e/`, `performance/`. Discovery: files `test_*.py`, classes `Test*`, functions `test_*`; `asyncio_mode = "auto"`. One test file per module (`test_module_name.py`). Confidence 88.

### Centralize reusable fixtures in tests/fixtures/
Shared fixtures live in domain-split modules under `tests/fixtures/` (cli_fixtures.py, command_fixtures.py, db_fixtures.py, model_fixtures.py, …) and are exposed globally via a single root `conftest.py`. Confidence 75.

### Test CLI commands with Click CliRunner
Exercise CLI commands through Click's `CliRunner` (invoke + assert on `result.exit_code`/`result.output`) rather than subprocess, isolating command logic.
```python
runner = CliRunner()
result = runner.invoke(cmd, ["arg"])
assert result.exit_code == 0
```
Confidence 72.

### Isolate external dependencies with unittest.mock
Unit tests must be fast (<1s), isolated, and deterministic. Mock external services (filesystem, network, subprocess, DB, Redis, OpenAI) with `unittest.mock` (`patch`, `MagicMock`). Confidence 75.

### Minimum coverage gate: 50% (goal 80%)
The enforced gate is `--cov-fail-under=50` with branch coverage on `src/mcli` (`pyproject.toml [tool.coverage.report] fail_under = 50.0`); CI runs `pytest --cov=src/mcli`. 80% is the aspirational/PR target; core modules (`mcli/self/`, `mcli/app/model_cmd.py`) aim for 95%. NOTE: stale references to 30% in CLAUDE.md/tox.ini predate the 50% gate — 50% is authoritative. Confidence 85.
