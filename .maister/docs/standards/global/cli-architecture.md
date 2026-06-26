## CLI Architecture

### Define commands with Click decorators in *_cmd.py modules
All CLI surface uses Click decorator definitions (`@click.command()` / `@click.group()` with `@click.option` / `@click.argument`). Command modules follow the `*_cmd.py` naming convention and are auto-discovered from `src/mcli/{app,self,workflow,public}`. Evidence: 59 files declare Click decorators, 30 use `*_cmd.py`, 365 `@click.option`. Confidence 92.

### Lazy-load heavy command groups
Heavy command groups and heavy third-party imports (torch, streamlit, moviepy, etc.) MUST defer importing via the `LazyCommand`/`LazyGroup` pattern, registered through `_add_lazy_commands()` (and `create_completion_aware_lazy_group` for completion support) in `src/mcli/app/main.py`. This keeps CLI startup fast and preserves shell completion. Do not import heavy deps at module top level in command modules. Confidence 90.

### Route user output through Rich UI styling helpers
User-facing status output goes through `mcli.lib.ui.styling` helpers (`success`, `error`, `warning`, `info`) and the shared `console`, not raw `print`, to keep colored output consistent.
```python
from mcli.lib.ui.styling import success, error, info, warning
```
Confidence 85.

### Use a per-module logger via get_logger(__name__)
Modules that log obtain a module-scoped logger from the project factory rather than stdlib logging directly. Near-universal form (92/109 logging files):
```python
from mcli.lib.logger.logger import get_logger
logger = get_logger(__name__)
```
Confidence 85.

### Raise typed exceptions from the McliError hierarchy
Prefer the custom exception hierarchy in `src/mcli/lib/errors.py` (`McliError` base → `CommandError`, `ScriptError`, `ValidationError`, `ConfigurationError`, and specific subclasses like `CommandNotFoundError`, `UnsupportedLanguageError`) over generic `ValueError`/`RuntimeError`, so callers can handle errors precisely and the CLI can map them to friendly messages + exit codes. NOTE: aspirational — currently low adoption (~3 files import the hierarchy; generic raises still dominate). New code should use typed exceptions. Confidence 62.

### Python naming conventions
snake_case module filenames (with `*_cmd.py` for command modules), PascalCase classes (e.g. `McliError`, `LazyGroup`), UPPER_SNAKE constant values grouped under `mcli.lib.constants`. Confidence 80.
