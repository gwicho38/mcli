# MCLI Architecture Overview

**Version**: 7.19.0
**Last Updated**: 2025-11-28
**Status**: Current

---

## Executive Summary

MCLI (Modern CLI) is a high-performance, extensible command-line framework that combines:

- **Python** for command logic, AI integration, and workflow automation
- **Rust** for performance-critical operations (file watching, TF-IDF search, hashing)
- **Click** for CLI interface with lazy loading for fast startup
- **IPFS/Storacha** for decentralized storage and sync

The framework enables users to create, manage, and share command workflows with features like visual editing, shell completion, and cloud sync.

---

## System Architecture Diagram

```
                                   ┌─────────────────────────────────────┐
                                   │          User Interface             │
                                   │  (Terminal / VSCode Extension)      │
                                   └─────────────────┬───────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLI Entry Point                                     │
│                            (src/mcli/app/main.py)                               │
│                                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   LazyLoad  │  │   Config    │  │   Plugin    │  │   Custom Commands       │ │
│  │   Manager   │  │   Loader    │  │   Registry  │  │   (~/.mcli/commands)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                                     │
                    ┌────────────────────────────────┼────────────────────────────┐
                    │                                │                            │
                    ▼                                ▼                            ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────────────┐
│      Command Groups         │  │      Workflow Engine        │  │      Storage Layer          │
│                             │  │                             │  │                             │
│  ┌───────┐ ┌────────────┐  │  │  ┌───────────┐ ┌─────────┐ │  │  ┌─────────┐ ┌───────────┐  │
│  │  app  │ │  workflow  │  │  │  │  Notebook │ │  Script │ │  │  │  Local  │ │  Storacha │  │
│  └───────┘ └────────────┘  │  │  │  Executor │ │  Sync   │ │  │  │  Cache  │ │  (IPFS)   │  │
│  ┌───────┐ ┌────────────┐  │  │  └───────────┘ └─────────┘ │  │  └─────────┘ └───────────┘  │
│  │ self  │ │   public   │  │  │  ┌───────────┐ ┌─────────┐ │  │  ┌─────────────────────────┐ │
│  └───────┘ └────────────┘  │  │  │  Daemon   │ │Scheduler│ │  │  │      Encryption         │ │
│                             │  │  │  Manager  │ │         │ │  │  │    (AES-256-CBC)       │ │
│                             │  │  └───────────┘ └─────────┘ │  │  └─────────────────────────┘ │
└─────────────────────────────┘  └─────────────────────────────┘  └─────────────────────────────┘
                    │                                │                            │
                    └────────────────────────────────┼────────────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               Shared Libraries                                   │
│                              (src/mcli/lib/)                                    │
│                                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │   API    │  │    UI    │  │  Logger  │  │  Paths   │  │     Constants      │ │
│  │(OpenAI,  │  │(styling, │  │(colored  │  │(dynamic  │  │  (env vars, dirs,  │ │
│  │Anthropic)│  │ prompts) │  │ output)  │  │ paths)   │  │    messages)       │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Rust Extensions                                       │
│                           (mcli_rust/src/)                                      │
│                                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  FileWatcher   │  │   TF-IDF       │  │    Hashing     │  │   Tokenizer    │ │
│  │  (notify-rs)   │  │   Search       │  │   (SHA256)     │  │                │ │
│  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Command Discovery System

**Location**: `src/mcli/app/main.py`

The CLI uses a multi-tier command discovery system:

```
Command Sources (Priority Order):
1. Built-in commands (src/mcli/app/)
2. Self-management commands (src/mcli/self/)
3. Workflow commands (src/mcli/workflow/)
4. Public API commands (src/mcli/public/)
5. Custom user commands (~/.mcli/commands/)
6. Project-local commands (.mcli/commands/)
```

**Lazy Loading Strategy**:
- Heavy imports (torch, streamlit, etc.) are deferred using `LazyCommand` and `LazyGroup`
- Shell completion uses `create_completion_aware_lazy_group` for responsive tab-completion
- First command invocation loads dependencies, subsequent calls are fast

### 2. Workflow Engine

**Location**: `src/mcli/workflow/`

The workflow engine supports multiple execution models:

| Format | Description | Use Case |
|--------|-------------|----------|
| JSON workflows | Declarative command definitions | Simple automations |
| Script files | Shell/Python/JS scripts with metadata | Complex logic |
| Jupyter notebooks (.ipynb) | Cell-based execution | Data science workflows |
| Workflow notebooks | Custom visual workflow format | Visual editing |

**Script → JSON Sync**:
```
user_script.py  ──┐
                  │  Auto-detect language
                  ├─ Extract @metadata
                  │  Calculate SHA256 hash
                  ▼
user_script.json ──► Loaded as Click command
```

### 3. Storage Abstraction Layer

**Location**: `src/mcli/storage/`

```
┌─────────────────────────────────────────┐
│            StorageManager               │
│     (High-level API for storage)        │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
    ▼                           ▼
┌───────────────────┐  ┌───────────────────┐
│   LocalCache      │  │  StorachaBackend  │
│ (~/.mcli/storage- │  │  (IPFS via HTTP   │
│   cache/)         │  │   Bridge API)     │
└───────────────────┘  └───────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │     Encryption        │
         │    (AES-256-CBC)      │
         │  Per-record IV        │
         └───────────────────────┘
```

**Features**:
- Content-addressed storage (CIDs)
- Transparent encryption at rest
- Local caching with gateway fallback
- Offline-first with background sync

### 4. Constants System

**Location**: `src/mcli/lib/constants/`

All hardcoded strings are centralized in the constants module:

```python
from mcli.lib.constants import EnvVars, DirNames, ErrorMessages

# Environment variables
api_key = os.getenv(EnvVars.OPENAI_API_KEY)

# Directory names
config_path = Path.home() / DirNames.MCLI / FileNames.CONFIG_TOML

# User-facing messages
click.echo(ErrorMessages.COMMAND_NOT_FOUND.format(name=cmd_name))
```

**Constant Categories**:
- `EnvVars` - Environment variable names
- `DirNames`, `FileNames` - Paths and filenames
- `ErrorMessages`, `SuccessMessages` - UI messages
- `URLs`, `Editors`, `Shells` - Default values
- `StorageEnvVars`, `StoragePaths` - Storage configuration

---

## Command Group Structure

```
mcli
├── chat                    # AI chat with OpenAI/Anthropic
├── commands               # Command management
│   └── (list|add|edit|remove|import|export|verify)
├── model                   # AI model management
├── workflow               # Single workflow management
│   └── (add|edit|info|list|remove|verify|update-lockfile)
├── workflows (alias: run)  # Run workflows
│   ├── sync               # Script-to-JSON sync
│   │   └── (all|one|status|cleanup|watch|push|pull)
│   ├── storage            # Storacha/IPFS storage
│   │   └── (status|login|setup|upload|download|list)
│   ├── daemon             # Background daemon
│   ├── scheduler          # Cron-like scheduling
│   └── <custom>           # User-defined workflows
├── self                    # Self-management
│   ├── update             # Update MCLI
│   ├── completion         # Shell completion
│   └── perf               # Performance diagnostics
└── <custom>                # User custom commands
```

---

## Data Flow

### Command Execution Flow

```
User Input: mcli workflow run my-script
                │
                ▼
        ┌───────────────────┐
        │  CLI Entry Point  │
        │    (main.py)      │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │  Command Router   │  Check built-in → workflow → custom
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │  Lazy Load Group  │  Load only required imports
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │  Execute Command  │  Run with Click context
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │  Output Formatter │  Rich/styled terminal output
        └───────────────────┘
```

### Script Sync Flow

```
Script File Modified
        │
        ▼
┌───────────────────┐
│   File Watcher    │  (Rust-based or watchdog)
│   (debounced)     │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  ScriptSyncMgr    │
│  - Detect lang    │
│  - Extract @meta  │
│  - Calc SHA256    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Generate JSON    │  Only if hash changed
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Cache Refresh    │  Update sync cache
└───────────────────┘
```

---

## Extension Points

### Adding Custom Commands

**Option 1: Script-based** (recommended for simple commands)
```bash
# Create script with metadata
cat > ~/.mcli/commands/utils/backup.sh << 'EOF'
#!/usr/bin/env bash
# @description: Backup files to S3
# @version: 1.0.0
# @requires: aws-cli

aws s3 sync . s3://my-bucket/
EOF

# Sync to JSON
mcli workflows sync all

# Command is now available
mcli utils backup
```

**Option 2: Python module** (for complex logic)
```python
# ~/.mcli/commands/custom/my_command.py
import click
from mcli.lib.ui.styling import success

@click.command()
@click.option('--name', '-n', required=True)
def my_command(name):
    """My custom command description."""
    success(f"Hello, {name}!")
```

### Extending Storage Backends

```python
# Implement EncryptedStorageBackend interface
from mcli.storage.backends.base import EncryptedStorageBackend

class MyBackend(EncryptedStorageBackend):
    async def connect(self) -> bool: ...
    async def store(self, key: str, data: bytes, metadata: dict) -> str: ...
    async def retrieve(self, key: str) -> Optional[bytes]: ...
    async def delete(self, key: str) -> bool: ...
```

---

## Performance Considerations

### Startup Time Optimization

| Technique | Implementation | Impact |
|-----------|----------------|--------|
| Lazy imports | `LazyCommand`/`LazyGroup` | -500ms typical |
| Rust extensions | File watching, hashing | -50% I/O time |
| Import caching | `MCLI_CACHE_IMPORTS=1` | -100ms subsequent |
| Config caching | `.mcli_cache/config.pickle` | -20ms |

### Memory Usage

- Base footprint: ~50MB
- With ML dependencies: ~500MB
- Dashboard mode: ~1GB

---

## Security Model

### Data Protection

1. **Secrets**: Use `lsh-framework` for secret management (external dependency)
2. **Encryption**: AES-256-CBC with per-record IV for storage
3. **Key Derivation**: PBKDF2 with SHA256
4. **Environment**: Sensitive env vars never logged

### IPFS/Storacha Integration

- UCAN tokens for delegated authorization
- CIDs provide content authenticity
- Local cache avoids network for private data

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [STORAGE_ABSTRACTION.md](STORAGE_ABSTRACTION.md) | Storacha/IPFS storage details |
| [FASTAPI_MIGRATION.md](FASTAPI_MIGRATION.md) | API migration planning |
| [SCRIPT_SYNC_SYSTEM.md](../SCRIPT_SYNC_SYSTEM.md) | Script sync deep dive |
| [TESTING.md](../development/TESTING.md) | Test architecture |
| [LINTING.md](../development/LINTING.md) | Code quality tools |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 7.19.0 | 2025-11-28 | Added storage abstraction, Storacha integration |
| 7.14.0 | 2025-11-15 | Script sync v2, workflow notebooks |
| 7.11.0 | 2025-10-30 | Command restructure, lazy loading |
| 7.0.0 | 2025-09-01 | Initial architecture documentation |
