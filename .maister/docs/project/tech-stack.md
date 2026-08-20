# Technology Stack

## Overview
This document describes the technology choices and rationale for **mcli** (mcli-framework), a portable CLI framework and workflow automation tool combining Python and Rust.

## Languages

### Python (3.10–3.12)
- **Usage**: ~95% of codebase
- **Rationale**: Rich CLI ecosystem (Click, Rich), fast iteration, broad library support for AI, ML, and automation. `requires-python = ">=3.10"`; CI matrix covers 3.9–3.12.
- **Key Features Used**: Type hints (mypy strict), `importlib` for lazy module loading, `asyncio`/`aiohttp` for async I/O, dataclasses/Pydantic v2 models.

### Rust (latest)
- **Usage**: Performance-critical extensions in `mcli_rust/`
- **Rationale**: Speed up hot paths (TF-IDF, file watching) without sacrificing the Python developer experience.
- **Toolchain**: `maturin` builds the Rust ↔ Python bindings; `Cargo.toml` at `mcli_rust/`.

## Frameworks

### CLI
- **Click 8.1.7 (<9.0.0)** — Decorator-driven commands/groups, the backbone of the CLI. Auto-discovery scans `src/mcli/{app,self,workflow,public}`.
- **Rich** — Colored terminal output and styling via `mcli.lib.ui`.

### Data / Validation
- **Pydantic v2 (2.0.0+)** — Settings management and data validation across models.

### Testing
- **pytest** (minversion 6.0) — Primary runner.
- **pytest-xdist** — Parallel execution (`pytest -n auto`).
- **pytest-cov** — Coverage (minimum 30%, goal 80%).
- **pytest-asyncio** — Async test support.
- **pytest-mock** — Mocking.

## Database / Storage
- **Config**: TOML files (`config.toml`, `pyproject.toml`) + environment variables (`.env`).
- **Workflows**: User-owned JSON in `~/.mcli/workflows/`, versioned by lockfile (SHA256 / IPFS CID).
- **Async SQLite**: `aiosqlite` where local persistence is needed.
- **Cache**: Redis client (optional).
- **Decentralized sync**: IPFS/IPNS (`ipfs_sync.py`, `ipns_manager.py`) + Storacha cloud backup.
- **Secrets**: Environment variables; optional `lsh-framework` integration.

## Build Tools & Package Management
- **UV** — Primary package manager (preferred over pip).
- **Makefile** — 30+ build/test/lint targets (`make wheel`, `make test`, `make lint`, …).
- **Maturin** — Rust extension builds.
- **PyPI** — Distribution as `mcli-framework`. Entry point: `mcli.app.main:main`.

## Infrastructure

### Containerization
- Docker support (`Dockerfile` present); build artifacts cached in `.build_cache/`.

### CI/CD
- **GitHub Actions** workflows: `ci.yml` (lint/test/build/scan), `test.yml` (Python 3.9–3.12 matrix), `build.yml` (multi-platform), `publish.yml` (PyPI), `security.yml` (CodeQL + bandit), `publish-self-hosted.yml`.
- **Act-first gate**: For private repos, `mcli ci preflight` runs workflows locally via `act` before push (cost optimization).
- **Runners**: Self-hosted + GitHub-hosted.

### Hosting / Distribution
- PyPI package; portable + binary executables built locally.

## Development Tools

### Linting & Formatting
- **Black** (line length 100), **isort** (black profile), **flake8**, **pylint** (optional/non-blocking).
- **lint-hardcoded-strings** — Custom pre-commit hook blocking hardcoded strings outside tests; enforces the centralized constants convention.

### Type Checking
- **mypy** (strict mode, `python_version = "3.10"`), run in pre-commit + CI.

### Security
- **bandit** (security scan), **safety** (dependency check), CodeQL in CI.

## Key Dependencies
- Core (always installed): Click, Rich, requests, tomli, Pydantic.
- Optional groups (lazy-loaded): chat (OpenAI/Anthropic/Ollama), viz/dashboard (Streamlit), video (moviepy/ffmpeg), ml (scikit-learn/MLflow), documents (pdfplumber/python-pptx).

## Version Management
- Semantic versioning (`M.m.s`), edited in `pyproject.toml`. Current: **v8.0.62**.
- Release notes per version in `docs/releases/X.Y.Z.md`; tags `vX.Y.Z` trigger PyPI publish.

---
*Last Updated*: 2026-06-26
*Auto-detected*: languages, frameworks, build tools, testing stack, linting/type/security tooling, CI/CD workflows, storage backends. *User-provided*: doc selection scope.
