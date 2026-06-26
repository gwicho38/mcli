# Documentation Index

**IMPORTANT**: Read this file at the beginning of any development task to understand available documentation and standards.

## Quick Reference

### Project Documentation
Project-level documentation covering vision, goals, architecture, and technology choices.

### Technical Standards
Coding standards, conventions, and best practices organized by domain.

---

## Project Documentation

Located in `.maister/docs/project/`

### Vision (`project/vision.md`)
mcli as a portable, version-controlled CLI framework — "Run first. Register later." Covers current state (v8.0.62, ~13 months, 883+ commits), the script-to-command purpose, and 6–12 month goals: orphaned-code removal (issue #209), dependency consolidation, raising coverage from 30% toward 50%+, and expanded docs.

### Roadmap (`project/roadmap.md`)
Prioritized plan from v8.0.62: high-priority orphaned-code removal (~4.8K LOC) and dependency consolidation; medium-priority coverage uplift and ADR/tutorial documentation; technical debt around dead auto-discovery scan paths and config-precedence simplification; plus future scalability/feature ideas.

### Tech Stack (`project/tech-stack.md`)
Python 3.10–3.12 (~95%) + Rust (`mcli_rust/` via maturin); Click 8.x CLI, Rich UI, Pydantic v2; pytest/xdist/cov/asyncio testing; TOML/ENV config with JSON workflows synced over IPFS/Storacha; UV + Makefile builds; Black/isort/flake8/mypy-strict/bandit tooling; GitHub Actions with act-first local gate.

### Architecture (`project/architecture.md`)
Layered CLI + plugin command-discovery: a Click dispatcher (`main.py`) lazily resolves `LazyCommand`/`LazyGroup` modules scanned from `src/mcli/{app,self,workflow,public}`. Documents the lib/workflow/self/storage layers, command and `mcli run` data flows, McliError handling, external integrations, and PyPI/binary deployment.

---

## Technical Standards

### Global Standards

Located in `.maister/docs/standards/global/`

#### CLI Architecture (`standards/global/cli-architecture.md`)
Click-decorator commands in `*_cmd.py` modules auto-discovered from `app/self/workflow/public`, lazy-loaded heavy groups via `LazyCommand`/`LazyGroup` + `_add_lazy_commands()`, Rich `styling` output helpers, per-module `get_logger(__name__)`, the (aspirational) `McliError` typed-exception hierarchy, and snake_case/PascalCase/UPPER_SNAKE naming.

#### Coding Style (`standards/global/coding-style.md`)
Naming consistency, automatic formatting, descriptive names, focused functions, uniform indentation, no dead code, no backward compatibility unless required, and DRY (Don't Repeat Yourself).

#### Commenting (`standards/global/commenting.md`)
Let code speak for itself, comment sparingly (explain why not what), and avoid change/history comments.

#### Constants Usage (`standards/global/constants-usage.md`)
Never hardcode strings — pull env-var names, paths, config keys, URLs, and messages from `src/mcli/lib/constants/` (`EnvVars`, `DirNames`, `FileNames`, `ErrorMessages`, …); enforced by the `tools/lint_hardcoded_strings.py` pre-commit hook (blocking locally, non-blocking in CI); import from the `mcli.lib.constants` package root only.

#### Development Conventions (`standards/global/conventions.md`)
Predictable structure, up-to-date documentation, clean version control, environment variables, minimal dependencies, consistent reviews, testing standards, feature flags, changelog updates, and building only what's needed.

#### Error Handling (`standards/global/error-handling.md`)
Clear user messages, fail fast, typed exceptions, centralized handling, graceful degradation, retry with backoff, and resource cleanup.

#### Git & Release Workflow (`standards/global/git-workflow.md`)
Conventional commit/PR titles (`type(scope): description`), `pyproject.toml` version bump within the PR, a regression test per bug fix, per-version release notes at `docs/releases/X.Y.Z.md`, `make lint/test-cov/security-check` PR gates off `feature/*` branches, never declaring done until CI is green, and isolated git worktrees for concurrent agents.

#### Minimal Implementation (`standards/global/minimal-implementation.md`)
Build only what you need, clear purpose, delete exploration artifacts, no future stubs, no speculative abstractions, review before commit, and treat unused code as debt.

#### Python Tooling (`standards/global/python-tooling.md`)
Black (line-length 100) and isort (black profile) blocking in CI; flake8 + plugins, mypy (gradual, strict on core modules), and bandit at commit time; the standard pre-commit hook suite via `make pre-commit-install`; target Python 3.10+ (test 3.10–3.12, 3.9 refs are stale).

#### Security & CI Gates (`standards/global/security-ci.md`)
Self-hosted act-first CI (`ci.yml`/`test.yml` on self-hosted runners, gated by `mcli ci preflight`), bandit blocking on HIGH severity, TruffleHog verified-only secret scanning, weekly CodeQL `+security-and-quality`, dependency-review failing on moderate+, and never committing secrets (use `.env`/env vars).

#### Validation (`standards/global/validation.md`)
Server-side validation always, client-side for feedback, validate early, specific errors, allowlists over blocklists, type and format checks, input sanitization, business rules, and consistent enforcement.

### Frontend Standards

Located in `.maister/docs/standards/frontend/`

#### Accessibility (`standards/frontend/accessibility.md`)
Semantic HTML, keyboard navigation, color contrast, alt text and labels, screen reader testing, ARIA when needed, heading structure, and focus management.

#### Components (`standards/frontend/components.md`)
Single responsibility, reusability, composability, clear interface, encapsulation, consistent naming, local state, minimal props, and documentation.

#### CSS (`standards/frontend/css.md`)
Consistent methodology, work with the framework, design tokens, minimize custom CSS, and production optimization.

#### Responsive Design (`standards/frontend/responsive.md`)
Mobile-first, standard breakpoints, fluid layouts, relative units, cross-device testing, touch-friendly targets, mobile performance, readable typography, and content priority.

### Backend Standards

Located in `.maister/docs/standards/backend/`

#### API Design (`standards/backend/api.md`)
RESTful principles, consistent naming, versioning, plural nouns, limited nesting, query parameters, proper status codes, and rate limit headers.

#### Database Migrations (`standards/backend/migrations.md`)
Reversible migrations, small and focused changes, zero-downtime awareness, separate schema and data, careful indexing, descriptive names, and version control.

#### Models (`standards/backend/models.md`)
Clear naming, timestamps, database constraints, appropriate types, index foreign keys, multi-layer validation, clear relationships, and practical normalization.

#### Database Queries (`standards/backend/queries.md`)
Parameterized queries, avoid N+1, select only needed columns, index strategic columns, transactions, query timeouts, and cache expensive queries.

#### Rust Extensions (`standards/backend/rust-extensions.md`)
Performance-critical code (TF-IDF, file watching) lives in `mcli_rust/` as a PyO3 extension module (cdylib, Rust edition 2021, pyo3 0.22 with `extension-module`; deps tokio/notify/serde/rayon/regex), built locally with `maturin develop`.

### Testing Standards

Located in `.maister/docs/standards/testing/`

#### Pytest Conventions (`standards/testing/pytest-conventions.md`)
Registered markers under `--strict-markers` (`slow`, `unit`, `cli`, `integration`, `requires_*`, …), tests organized by category under `tests/`, reusable fixtures centralized in `tests/fixtures/` via root `conftest.py`, Click `CliRunner` for CLI tests, `unittest.mock` isolation of external deps, and a 50% coverage gate (`--cov-fail-under=50`, goal 80%).

#### Test Writing (`standards/testing/test-writing.md`)
Test behavior not implementation, clear names, mock external dependencies, fast execution, risk-based testing, balance coverage and velocity, critical path focus, and appropriate depth.

---

## How to Use This Documentation

1. **Start Here**: Always read this INDEX.md first to understand what documentation exists
2. **Project Context**: Read relevant project documentation before starting work
3. **Standards**: Reference appropriate standards when writing code
4. **Keep Updated**: Update documentation when making significant changes
5. **Customize**: Adapt all documentation to your project's specific needs

## Updating Documentation

- Project documentation should be updated when goals, tech stack, or architecture changes
- Technical standards should be updated when team conventions evolve
- Always update INDEX.md when adding, removing, or significantly changing documentation
