# MCLI Scope Migration Plan

**Goal**: Extract ML/trading/video features from core repository to mcli-commands repository, reducing core footprint while maintaining functionality through workflow JSON system.

**Date**: 2025-11-13
**Status**: Planning Phase

---

## 📊 Migration Inventory

### 1. ML/Trading Features (1.4M, ~50 files)

**Location**: `src/mcli/ml/`

**Subdirectories**:
- `dashboard/` (453K) - Streamlit ML/trading dashboards
- `features/` (91K) - Feature engineering
- `trading/` (89K) - Trading strategies
- `mlops/` (72K) - MLOps infrastructure
- `models/` (70K) - Model definitions
- `preprocessing/` (62K) - Data preprocessing
- `data_ingestion/` (54K) - Data pipelines
- `api/` (53K) - ML API endpoints
- `database/` (45K) - Database interactions
- `backtesting/` (40K) - Trading backtesting
- `optimization/` (37K) - Portfolio optimization
- `experimentation/` (36K) - ML experiments
- `tests/` (34K) - ML tests
- `monitoring/` (31K) - ML monitoring
- `auth/` (29K) - ML authentication
- `serving/` - Model serving
- `training/` - Model training
- `predictions/` - Prediction engine
- `cli/` - ML CLI
- `config/`, `configs/` - ML configuration
- `scripts/` - Utility scripts

**Entry Points** (to remove from pyproject.toml):
```toml
mcli-train = "mcli.ml.training.train:main"
mcli-serve = "mcli.ml.serving.serve:main"
mcli-backtest = "mcli.ml.backtesting.run:main"
mcli-optimize = "mcli.ml.optimization.optimize:main"
mcli-dashboard = "mcli.ml.dashboard:main"
```

**Dependencies to Remove** (~40 packages):
```python
# ML/Data Science
torch, torchvision, pytorch-lightning
scikit-learn, mlflow, dvc
optuna, PyPortfolioOpt
polars, pyarrow

# Trading
yfinance, alpha-vantage, alpaca-py
cvxpy

# Database (ML-specific)
supabase, sqlalchemy, alembic
psycopg2-binary, asyncpg

# Visualization (ML-specific)
seaborn, plotly, altair
streamlit, streamlit-autorefresh

# Document processing (ML-specific)
pandas, openpyxl

# Monitoring (ML-specific)
prometheus-client, structlog
newrelic, datadog

# Jupyter
jupyter, jupyterlab, ipykernel

# Auth (ML-specific)
python-jose, passlib
pydantic-settings, dynaconf, pandera
```

### 2. Video Processing (in app/video/)

**Location**: `src/mcli/app/video/`

**Files**:
- `video.py` - Video processing commands

**Dependencies to Remove** (~5 packages):
```python
opencv-python
pillow
scikit-image
scipy (if only used for video)
numpy (check if used elsewhere)
```

### 3. Dashboard Features (in workflow/)

**Location**: `src/mcli/workflow/dashboard/`

**Files**:
- `dashboard_cmd.py` - Dashboard launcher with politician trading integration

**Note**: This is already in workflow/ but tightly coupled to ML features (Supabase, politician trading).

### 4. Related Workflow Commands

Commands that are tightly coupled to ML features and should migrate:

**Candidates**:
- `workflow/notebook/` - Jupyter notebook operations (coupled to ML)
- Politician trading queries in dashboard

---

## 🎯 Migration Strategy

### Phase 1: Extract & Convert to Workflows

#### Step 1.1: Create Workflow JSON Files

For each major feature, create a workflow JSON file:

**Example: `mcli-train` → `ml/training.json`**
```json
{
  "name": "ml_train",
  "group": "ml",
  "description": "Train machine learning models with PyTorch/scikit-learn",
  "language": "python",
  "version": "1.0.0",
  "code": "... (copy from src/mcli/ml/training/train.py) ...",
  "metadata": {
    "requires": ["torch>=2.0.0", "scikit-learn>=1.3.0", "mlflow>=2.8.0"],
    "entry_point": "train:main",
    "category": "ml",
    "tags": ["machine-learning", "training", "pytorch"],
    "deprecated_entry_point": "mcli-train"
  },
  "created_at": "2025-11-13T10:00:00Z",
  "updated_at": "2025-11-13T10:00:00Z"
}
```

**Workflow Structure in mcli-commands**:
```
mcli-commands/
├── ml/
│   ├── training.json          # mcli workflows ml_train
│   ├── serving.json           # mcli workflows ml_serve
│   ├── backtesting.json       # mcli workflows ml_backtest
│   ├── optimization.json      # mcli workflows ml_optimize
│   └── dashboard.json         # mcli workflows ml_dashboard
├── video/
│   └── processing.json        # mcli workflows video_processing
└── trading/
    ├── politician_data.json   # mcli workflows politician_data
    └── portfolio_viz.json     # mcli workflows portfolio_viz
```

#### Step 1.2: Create Multi-File Workflows

For complex features, support multi-file structure:

```
mcli-commands/
└── ml/
    ├── training/
    │   ├── __main__.py        # Entry point
    │   ├── train_model.py
    │   ├── data_loader.py
    │   ├── requirements.txt   # Per-workflow dependencies
    │   └── README.md
    └── training.json          # Metadata wrapper
```

`training.json`:
```json
{
  "name": "ml_train",
  "group": "ml",
  "description": "Train ML models",
  "language": "python",
  "type": "multi-file",
  "entry_point": "training/__main__.py",
  "metadata": {
    "requires_file": "training/requirements.txt"
  }
}
```

### Phase 2: Update Core MCLI

#### Step 2.1: Remove ML/Video Modules

```bash
# Remove directories
rm -rf src/mcli/ml/
rm -rf src/mcli/app/video/
```

#### Step 2.2: Update pyproject.toml

**Remove entry points**:
```toml
# DELETE these lines
mcli-train = "mcli.ml.training.train:main"
mcli-serve = "mcli.ml.serving.serve:main"
mcli-backtest = "mcli.ml.backtesting.run:main"
mcli-optimize = "mcli.ml.optimization.optimize:main"
mcli-dashboard = "mcli.ml.dashboard:main"
```

**Remove dependencies**:
```toml
# KEEP these (core dependencies)
dependencies = [
  "click>=8.1.7,<9.0.0",
  "rich>=14.0.0",
  "requests>=2.31.0,<3.0.0",
  "tomli>=2.2.1",
  "python-dotenv>=1.1.1",
  "watchdog>=3.0.0,<4.0.0",
  "tqdm>=4.66.1,<5.0.0",
  "humanize>=4.9.0,<5.0.0",
  "psutil>=5.9.0,<6.0.0",
  "inquirerpy>=0.3.4,<0.4.0",
  "gitpython>=3.1.40,<4.0.0",
  "prompt-toolkit>=3.0.0,<4.0.0",
  "aiohttp>=3.9.0",
  "httpx>=0.28.1",
  "websockets>=12.0",
  "beautifulsoup4>=4.13.5",
  "fuzzywuzzy>=0.18.0",
  "redis>=5.0.0",  # Keep if used for daemon/workflow features
]

# REMOVE all ML/trading/video specific packages
# - torch, torchvision, pytorch-lightning
# - scikit-learn, mlflow, dvc, optuna
# - yfinance, alpha-vantage, alpaca-py, cvxpy
# - supabase, sqlalchemy, alembic, psycopg2-binary
# - opencv-python, pillow, scikit-image, scipy
# - streamlit, altair, streamlit-autorefresh
# - matplotlib, seaborn, plotly
# - pandas, openpyxl
# - jupyter, jupyterlab, ipykernel
# - prometheus-client, newrelic, datadog
# - kafka-python
```

**Create optional plugin dependencies**:
```toml
[project.optional-dependencies]
# ML plugin dependencies (user installs separately)
ml-plugin = [
  "torch>=2.0.0",
  "scikit-learn>=1.3.0",
  "mlflow>=2.8.0",
  "pytorch-lightning>=2.0.0",
  # ... other ML deps
]

# Video plugin dependencies
video-plugin = [
  "opencv-python>=4.11.0.86",
  "pillow>=11.2.1",
  "scikit-image>=0.24.0",
]

# Trading plugin dependencies
trading-plugin = [
  "yfinance>=0.2.18",
  "alpha-vantage>=2.3.1",
  "alpaca-py==0.43.2",
  "cvxpy>=1.4.0",
]
```

#### Step 2.3: Update Documentation

**Update CLAUDE.md**:
- Remove ML/trading sections
- Add section on workflow plugins
- Update architecture diagram

**Update README.md**:
- Focus on core command manager features
- Add "Plugins" section for ML/trading/video

### Phase 3: Implement Script → JSON Sync System

#### Design Philosophy

The JSON layer serves as:
1. **Metadata store** - Description, version, dependencies
2. **Execution wrapper** - How to run the script
3. **Cache layer** - Avoid re-parsing scripts on every startup

#### Architecture

```
User's Script (source of truth)
    ↓
Auto-generate JSON (if missing)
    ↓
Keep JSON in sync with script (file watching)
    ↓
Load from JSON (fast startup)
```

#### Implementation

**Location**: `src/mcli/lib/script_sync.py`

```python
"""Script → JSON synchronization system."""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

class ScriptSyncManager:
    """Manages synchronization between raw scripts and JSON workflow definitions."""

    def __init__(self, commands_dir: Path):
        self.commands_dir = commands_dir
        self.sync_cache = commands_dir / ".sync_cache.json"

    def detect_language(self, script_path: Path) -> str:
        """Detect script language from extension or shebang."""
        # Check shebang first
        with open(script_path, 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#!'):
                if 'python' in first_line:
                    return 'python'
                elif 'bash' in first_line or 'sh' in first_line:
                    return 'shell'
                elif 'node' in first_line:
                    return 'javascript'
                # Add more...

        # Fallback to extension
        ext_map = {
            '.py': 'python',
            '.sh': 'shell',
            '.bash': 'shell',
            '.zsh': 'shell',
            '.fish': 'shell',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.rb': 'ruby',
            '.pl': 'perl',
        }
        return ext_map.get(script_path.suffix, 'unknown')

    def extract_metadata(self, script_path: Path, language: str) -> Dict:
        """Extract metadata from script comments."""
        metadata = {
            'description': '',
            'version': '1.0.0',
            'author': '',
            'requires': [],
            'tags': [],
        }

        comment_prefix = '#' if language in ['python', 'shell', 'ruby', 'perl'] else '//'

        with open(script_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith(comment_prefix):
                    continue

                # Remove comment prefix
                line = line[len(comment_prefix):].strip()

                # Parse @-prefixed metadata
                if line.startswith('@'):
                    if ':' in line:
                        key, value = line[1:].split(':', 1)
                        key = key.strip()
                        value = value.strip()

                        if key in ['requires', 'tags']:
                            metadata[key] = [v.strip() for v in value.split(',')]
                        else:
                            metadata[key] = value

        return metadata

    def calculate_hash(self, script_path: Path) -> str:
        """Calculate SHA256 hash of script file."""
        with open(script_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def needs_sync(self, script_path: Path, json_path: Path) -> bool:
        """Check if JSON needs to be regenerated."""
        if not json_path.exists():
            return True

        # Compare modification times
        if script_path.stat().st_mtime > json_path.stat().st_mtime:
            return True

        # Compare hashes (more reliable)
        script_hash = self.calculate_hash(script_path)

        try:
            with open(json_path, 'r') as f:
                json_data = json.load(f)
                cached_hash = json_data.get('metadata', {}).get('source_hash', '')
                return script_hash != cached_hash
        except:
            return True

    def generate_json(self, script_path: Path, group: Optional[str] = None) -> Path:
        """Generate JSON workflow from script file."""
        language = self.detect_language(script_path)
        metadata = self.extract_metadata(script_path, language)
        script_hash = self.calculate_hash(script_path)

        # Read script code
        with open(script_path, 'r') as f:
            code = f.read()

        # Determine group from directory structure
        if group is None:
            relative = script_path.relative_to(self.commands_dir)
            if len(relative.parts) > 1:
                group = relative.parts[0]
            else:
                group = None

        # Generate JSON
        json_data = {
            "name": script_path.stem,
            "group": group,
            "description": metadata.get('description', f"{script_path.stem} command"),
            "language": language,
            "version": metadata.get('version', '1.0.0'),
            "code": code,
            "metadata": {
                "source_file": str(script_path.relative_to(self.commands_dir)),
                "source_hash": script_hash,
                "author": metadata.get('author', ''),
                "requires": metadata.get('requires', []),
                "tags": metadata.get('tags', []),
                "auto_generated": True,
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        # Shell-specific metadata
        if language == 'shell':
            json_data["shell"] = metadata.get('shell', 'bash')

        # Save JSON
        json_path = script_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)

        return json_path

    def sync_all(self):
        """Sync all scripts in commands directory."""
        synced = []

        for script_path in self.commands_dir.rglob('*'):
            # Skip non-script files
            if script_path.suffix not in ['.py', '.sh', '.bash', '.zsh', '.fish', '.js', '.ts', '.rb', '.pl']:
                continue

            # Skip JSON files
            if script_path.suffix == '.json':
                continue

            # Skip if already has JSON and up-to-date
            json_path = script_path.with_suffix('.json')
            if not self.needs_sync(script_path, json_path):
                continue

            # Generate/update JSON
            self.generate_json(script_path)
            synced.append(script_path)

        return synced
```

#### File Watcher Integration

**Location**: `src/mcli/lib/script_watcher.py`

```python
"""File watcher for script → JSON sync."""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class ScriptFileHandler(FileSystemEventHandler):
    """Watch for script file changes and trigger sync."""

    def __init__(self, sync_manager):
        self.sync_manager = sync_manager

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix in ['.py', '.sh', '.bash', '.zsh', '.fish', '.js', '.ts']:
            self.sync_manager.generate_json(path)

    def on_modified(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix in ['.py', '.sh', '.bash', '.zsh', '.fish', '.js', '.ts']:
            json_path = path.with_suffix('.json')
            if self.sync_manager.needs_sync(path, json_path):
                self.sync_manager.generate_json(path)

    def on_deleted(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix in ['.py', '.sh', '.bash', '.zsh', '.fish', '.js', '.ts']:
            # Delete corresponding JSON
            json_path = path.with_suffix('.json')
            json_path.unlink(missing_ok=True)

def start_watcher(commands_dir: Path, sync_manager):
    """Start file watcher for commands directory."""
    event_handler = ScriptFileHandler(sync_manager)
    observer = Observer()
    observer.schedule(event_handler, str(commands_dir), recursive=True)
    observer.start()
    return observer
```

#### Usage in main.py

```python
from mcli.lib.script_sync import ScriptSyncManager
from mcli.lib.script_watcher import start_watcher

def create_app():
    cli = click.Group(...)

    # Get commands directory
    commands_dir = get_custom_commands_dir()

    # Sync scripts → JSON on startup
    sync_manager = ScriptSyncManager(commands_dir)
    synced = sync_manager.sync_all()
    if synced:
        logger.info(f"Synced {len(synced)} scripts to JSON")

    # Start file watcher (optional, for development)
    if os.getenv('MCLI_WATCH_SCRIPTS', 'false').lower() == 'true':
        start_watcher(commands_dir, sync_manager)

    # Load commands from JSON (as before)
    load_custom_commands(cli)

    return cli
```

### Phase 4: Migration Execution

#### Step 4.1: Create mcli-commands Repository Structure

```bash
mcli-commands/
├── README.md                  # Overview of available workflows
├── ml/
│   ├── README.md
│   ├── training.json
│   ├── serving.json
│   ├── backtesting.json
│   ├── optimization.json
│   └── dashboard.json
├── video/
│   ├── README.md
│   └── processing.json
├── trading/
│   ├── README.md
│   ├── politician_data.json
│   └── portfolio_viz.json
└── .github/
    └── workflows/
        └── validate.yml       # Validate JSON schemas
```

#### Step 4.2: Extract Code

For each feature:

1. **Extract entry point code** to JSON `code` field
2. **Extract dependencies** to JSON `metadata.requires`
3. **Create README** explaining usage
4. **Test workflow** before migration

Example for `mcli-train`:

```bash
# 1. Read current code
cat src/mcli/ml/training/train.py

# 2. Create JSON workflow
cat > mcli-commands/ml/training.json <<'EOF'
{
  "name": "ml_train",
  "group": "ml",
  "description": "Train machine learning models",
  "language": "python",
  "version": "1.0.0",
  "code": "... (paste code here) ...",
  "metadata": {
    "requires": [
      "torch>=2.0.0",
      "scikit-learn>=1.3.0",
      "mlflow>=2.8.0"
    ],
    "deprecated_entry_point": "mcli-train",
    "install_hint": "pip install torch scikit-learn mlflow"
  }
}
EOF

# 3. Test
mcli workflow import mcli-commands/ml/training.json
mcli workflows ml_train --help
```

#### Step 4.3: Update Core Repository

```bash
# Remove ML module
git rm -r src/mcli/ml/

# Remove video module
git rm -r src/mcli/app/video/

# Update pyproject.toml (manual edit)
vim pyproject.toml
# - Remove entry points
# - Remove dependencies
# - Add optional plugin dependencies

# Update documentation
vim CLAUDE.md
vim README.md

# Commit changes
git add -A
git commit -m "refactor: extract ML/trading/video features to mcli-commands

- Remove src/mcli/ml/ (1.4M, 50 files)
- Remove src/mcli/app/video/
- Remove 40+ ML/trading/video dependencies
- Remove entry points: mcli-train, mcli-serve, mcli-backtest, etc.
- Update documentation to reflect plugin architecture
- Core installation size reduced from ~500MB to ~20MB

Features are now available as workflows in mcli-commands repo.
Users can install plugin dependencies optionally:
  pip install mcli-framework[ml-plugin]
  pip install mcli-framework[video-plugin]
  pip install mcli-framework[trading-plugin]

See: https://github.com/gwicho38/mcli-commands"
```

---

## 📈 Success Metrics

### Before Migration

| Metric | Value |
|--------|-------|
| Total files | 210 |
| Lines of code | 80,314 |
| Dependencies | 136+ |
| Install size | ~500MB |
| Core vs peripheral | 50/50 split |

### After Migration (Target)

| Metric | Value |
|--------|-------|
| Total files | ~160 (-50) |
| Lines of code | ~60,000 (-20K) |
| Dependencies | ~15-20 (-115) |
| Install size | ~10-20MB (-480MB) |
| Core vs peripheral | 100% core |

### Installation Time

- **Before**: 5-10 minutes (PyTorch, etc.)
- **After**: 10-30 seconds (core only)

### Startup Time

- **Before**: ~500ms (loading ML modules)
- **After**: ~50ms (no ML imports)

---

## 🔄 Backward Compatibility

### Migration Guide for Users

**If using ML features**:

```bash
# Old way (deprecated)
mcli-train --config config.yaml

# New way (workflow)
# 1. Import workflow from mcli-commands
mcli workflow import https://github.com/gwicho38/mcli-commands/ml/training.json

# 2. Install dependencies
pip install torch scikit-learn mlflow

# 3. Run workflow
mcli workflows ml_train --config config.yaml
```

### Deprecation Timeline

- **v7.13.0**: ML/video features still in core (current)
- **v7.14.0**: Mark features as deprecated, warn users
- **v8.0.0**: Remove features, require migration to workflows

### Deprecation Warnings

Add to affected commands:

```python
import warnings

def main():
    warnings.warn(
        "mcli-train is deprecated and will be removed in v8.0.0. "
        "Use 'mcli workflows ml_train' instead. "
        "See: https://github.com/gwicho38/mcli-commands",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing code
```

---

## 📝 Next Steps

1. ✅ Review and approve this migration plan
2. ⏳ Implement script → JSON sync system
3. ⏳ Create mcli-commands repository
4. ⏳ Extract ML features to workflows
5. ⏳ Extract video features to workflows
6. ⏳ Update pyproject.toml dependencies
7. ⏳ Update documentation
8. ⏳ Test migration with real workflows
9. ⏳ Release v7.14.0 with deprecation warnings
10. ⏳ Release v8.0.0 with features removed

---

## 🤝 Review & Feedback

**Questions to Address**:

1. Should we support multi-file workflows immediately or start with single-file?
2. What should happen to the standalone entry points (mcli-train, etc.)? Keep as thin wrappers?
3. Should plugin dependencies be auto-installed when importing workflows that need them?
4. How do we handle workflow updates from mcli-commands repo?
5. Should we create a workflow marketplace/registry?

**Reviewers**: @gwicho38

**Status**: Awaiting approval
