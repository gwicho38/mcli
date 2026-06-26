# System Architecture

## Overview
mcli is a layered CLI application with a plugin-style command-discovery system. A Click dispatcher routes commands; heavy subsystems load lazily to keep startup fast. Shared utilities, a workflow engine, and pluggable storage backends sit behind the CLI layer.

## Architecture Pattern
**Pattern**: Layered CLI + plugin/command-discovery system.

Commands are discovered by scanning `src/mcli/{app,self,workflow,public}` (configurable via `config.toml`). Each command group is wrapped in `LazyCommand`/`LazyGroup`, which defers `importlib.import_module()` until the command is actually invoked — so heavy dependencies (torch, streamlit, moviepy) never slow down unrelated commands.

## System Structure

### app/ — CLI commands (entry point)
- **Location**: `src/mcli/app/`
- **Purpose**: Top-level commands and the dispatcher.
- **Key Files**: `main.py` (LazyCommand/LazyGroup framework, discovery), `run.py` (universal script runner), `list_cmd.py`, `search_cmd.py`, `new_cmd.py`, `edit_cmd.py`, `sync_cmd.py`.

### lib/ — shared libraries
- **Location**: `src/mcli/lib/`
- **Purpose**: Cross-cutting utilities.
- **Key Files**: `constants/` (centralized config, linter-enforced), `config/` (TOML/ENV parsing), `logger/` (structured logging, `MCLI_TRACE_LEVEL`), `ui/` (Rich styling: `success/error/warning/info`), `auth/`, `api/`, `errors.py` (McliError hierarchy).

### workflow/ — workflow engine
- **Location**: `src/mcli/workflow/`
- **Purpose**: Execute, schedule, and sync versioned workflows.
- **Key Files**: `workflow.py` (runtime executor), `scheduler/`, `daemon/`, `ci/`, `notebook/`, `sync/` (IPFS).

### self/ — self-management
- **Location**: `src/mcli/self/`
- **Purpose**: version, update, health, shell completion.

### storage/ — pluggable backends
- **Location**: `src/mcli/storage/`
- **Purpose**: File system / IPFS / Storacha / encrypted backends via a factory + base abstraction (`base.py`, `factory.py`).

## Data Flow

**Command invocation**
```
mcli <cmd>
  → main.py dispatcher (Click)
  → LazyGroup resolves + imports target module on demand
  → command executes, errors mapped to McliError subclasses
  → Rich-formatted output, exit code (0 ok / 1 error / 2 invalid)
```

**Workflow / script run**
```
mcli run <script>
  → script_loader detects language (py/sh/js/ts/rb/pl/lua)
  → metadata extracted from @-comments (@description/@version/@requires)
  → runtime prepares venv + deps
  → script executes with friendly error surface on crash
  → result logged / stored; lockfile tracks hash/CID
```

## External Integrations
- **AI**: OpenAI, Anthropic, Ollama (lazy-loaded chat).
- **Dashboards**: Streamlit.
- **Decentralized storage**: IPFS/IPNS + Storacha.
- **Datastores**: SQLite (aiosqlite), Redis (cache), Supabase (ML/trading).
- **Secrets**: lsh-framework (optional).

## Database Schema
No central relational schema. State lives in TOML/ENV config and user-owned JSON workflow definitions (`~/.mcli/workflows/`), versioned by a lockfile (SHA256 / IPFS CID). Pydantic v2 models document in-memory structures.

## Configuration
- `config.toml` — command discovery directories + tool settings.
- `pyproject.toml` — package metadata, deps, tool config.
- `.env` / `.env.example` — environment variables and secrets.
- Centralized constants in `src/mcli/lib/constants/` are the single source of truth; hardcoded strings are blocked by a pre-commit hook.

## Deployment Architecture
Distributed as a PyPI wheel (`mcli-framework`) plus portable/binary executables. Rust extensions compiled via maturin. CI builds multi-platform (macOS/Linux/Windows); private-repo CI gated locally by `act` (`mcli ci preflight`).

---
*Based on codebase analysis performed 2026-06-26*
