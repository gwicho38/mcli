## Constants Usage

### Never hardcode strings — use the constants module
All user-facing strings, env-var names, file/dir paths, config keys, URLs, and default values MUST come from `src/mcli/lib/constants/` (classes `EnvVars`, `DirNames`, `FileNames`, `ErrorMessages`, `SuccessMessages`, etc.) instead of string literals. Enforced by the custom linter `tools/lint_hardcoded_strings.py`: BLOCKING at commit time (pre-commit local hook), currently NON-BLOCKING in CI (`continue-on-error`, pending refactor of existing violations). Bypass a commit only with `git commit --no-verify` when justified.
```python
# Good
from mcli.lib.constants import EnvVars, ErrorMessages
api_key = os.getenv(EnvVars.OPENAI_API_KEY)
click.echo(ErrorMessages.COMMAND_NOT_FOUND.format(name=cmd))
# Bad — rejected by linter
api_key = os.getenv("OPENAI_API_KEY")
click.echo(f"Command {cmd} not found")
```
Sources: pre-commit local hook `lint-hardcoded-strings`; `make lint-hardcoded-strings`; CLAUDE.md; constants/README.md. Confidence 95.

### Import constants from the package root only
Always import from `mcli.lib.constants` (the package `__init__`), never from individual submodules like `mcli.lib.constants.env`. This keeps the public surface stable.
```python
from mcli.lib.constants import EnvVars   # Good
from mcli.lib.constants.env import EnvVars  # Bad
```
Source: constants/README.md. Confidence 88.
