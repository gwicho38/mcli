## Python Tooling

### Format with Black, line length 100
Python code MUST be Black-formatted with `line-length = 100`. CI runs `black --check --diff src/` as a BLOCKING step; pre-commit runs psf/black 24.8.0 `--line-length=100` on every commit; `.editorconfig` pins `[*.py] max_line_length=100`. Confidence 95.

### Sort imports with isort (black profile)
Imports MUST be sorted with isort using `profile = "black"`, `line_length = 100`. CI runs `isort --check-only --diff src/` (blocking); enforced on every commit. Confidence 95.

### Lint with flake8 + plugins
Every commit runs flake8 (max-line-length 100, `--extend-ignore=E203,W503`) with flake8-docstrings (Google convention), flake8-bugbear, flake8-comprehensions, flake8-simplify. Note: the repo-level `.flake8`/`setup.cfg` deliberately restrict standalone runs to critical errors (F821,F841,E711,E712,E721,E902,E999) at max-line 120; the pre-commit hook is the stricter gate. Confidence 85.

### Type-check with mypy (gradual, strict on core)
mypy targets `python_version = "3.10"` with `ignore_missing_imports = true`. Default is lenient (`disallow_untyped_defs = false`), but core modules have per-module overrides enabling `disallow_untyped_defs = true` and `strict_optional = true`. mypy is NON-BLOCKING in CI (gradual adoption) but runs at commit time (excludes tests/docs/scripts). New core code should be fully typed. Confidence 84.

### Security-scan with bandit
bandit scans `src/` recursively (pre-commit + `tox -e security`); CI fails only on HIGH severity, with a curated skip list of CLI false positives (B101,B102,B104,B108,B113,…). Confidence 85.

### Use the standard pre-commit hook suite
Install hooks with `make pre-commit-install`. On every commit they run: Black, isort, flake8(+plugins), mypy, bandit, the hardcoded-strings linter, plus file-hygiene (trailing-whitespace, end-of-file-fixer, LF endings, check yaml/json/toml, max-added-file 500kb, debug-statements), pyupgrade `--py39-plus`, prettier (yaml, excl `.github/`), and shellcheck (`-e SC1091`). pylint is advisory only (`|| true`, fail-under 7.0). Confidence 85.

### Target Python 3.10+ (test 3.10–3.12)
`requires-python = ">=3.10"` is the source of truth; CI test matrix runs 3.10, 3.11, 3.12; recommended runtime 3.11. NOTE: some legacy `tox.ini`/docs references to 3.9 are stale and should not be relied on. Confidence 82.
