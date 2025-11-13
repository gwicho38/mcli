# Migration Guide: MCLI v7.x → v8.0

**Effective Date**: TBD (Planned for v8.0.0)
**Status**: Deprecation warnings in v7.14.0, Removal in v8.0.0

---

## 🎯 Overview

MCLI v8.0 refocuses the core framework on its primary mission: **command management**. ML/trading/video features are being extracted to optional workflows in the `mcli-commands` repository.

**Key Changes**:
- ❌ ML/trading/video features removed from core
- ✅ Available as optional workflows in `mcli-commands` repo
- ✅ Smaller core: ~500MB → ~20MB installation
- ✅ Fewer dependencies: 136+ → ~15-20
- ✅ Faster startup: ~500ms → ~50ms

---

## 📋 What's Changing

### Removed Entry Points

The following standalone entry points will be removed:

| Old Entry Point | New Workflow | Import From |
|----------------|--------------|-------------|
| `mcli-train` | `mcli workflows ml_train` | `mcli-commands/ml/training.json` |
| `mcli-serve` | `mcli workflows ml_serve` | `mcli-commands/ml/serving.json` |
| `mcli-backtest` | `mcli workflows ml_backtest` | `mcli-commands/trading/backtesting.json` |
| `mcli-optimize` | `mcli workflows ml_optimize` | `mcli-commands/trading/optimization.json` |
| `mcli-dashboard` | `mcli workflows ml_dashboard` | `mcli-commands/ml/dashboard.json` |

### Removed Modules

The following Python modules will be removed from core:

- `mcli.ml.*` - All ML/training/serving code
- `mcli.app.video.*` - Video processing code

These are now available as workflows.

### Dependencies Moved to Optional Extras

The following dependencies are no longer installed by default:

**ML Dependencies** (now `ml-plugin`):
- torch, torchvision, pytorch-lightning
- scikit-learn, mlflow, dvc, optuna
- streamlit, altair
- Heavy data science packages

**Trading Dependencies** (now `trading-plugin`):
- yfinance, alpha-vantage, alpaca-py
- cvxpy, PyPortfolioOpt

**Video Dependencies** (now `video-plugin`):
- opencv-python, pillow, scikit-image, scipy

---

## 🚀 Migration Steps

### Step 1: Update MCLI

```bash
# Update to v7.14.0 first (includes deprecation warnings)
pip install --upgrade mcli-framework==7.14.0

# Test your workflows with deprecation warnings
mcli-train --help  # Will show deprecation warning
```

### Step 2: Clone mcli-commands Repository

```bash
git clone https://github.com/gwicho38/mcli-commands.git
cd mcli-commands
```

### Step 3: Import Workflows You Need

```bash
# Import ML workflows
mcli workflow import ml/training.json
mcli workflow import ml/serving.json
mcli workflow import ml/dashboard.json

# Import trading workflows
mcli workflow import trading/backtesting.json
mcli workflow import trading/optimization.json

# Import video workflows
mcli workflow import video/processing.json
```

### Step 4: Install Plugin Dependencies

```bash
# Install dependencies for workflows you imported
pip install mcli-framework[ml-plugin]        # For ML workflows
pip install mcli-framework[trading-plugin]   # For trading workflows
pip install mcli-framework[video-plugin]     # For video workflows

# Or install all at once
pip install mcli-framework[ml-plugin,trading-plugin,video-plugin]
```

### Step 5: Update Your Scripts

**Before (v7.x)**:
```bash
#!/bin/bash
mcli-train model --model-type lstm --dataset data.csv
mcli-serve --model-path model.pt --port 8000
mcli-backtest --strategy momentum --symbols AAPL,GOOGL
```

**After (v8.0)**:
```bash
#!/bin/bash
mcli workflows ml_train model --model-type lstm --dataset data.csv
mcli workflows ml_serve --model-path model.pt --port 8000
mcli workflows ml_backtest --strategy momentum --symbols AAPL,GOOGL
```

### Step 6: Upgrade to v8.0

```bash
# When v8.0 is released
pip install --upgrade mcli-framework==8.0.0

# Verify workflows still work
mcli workflows ml_train --help
```

---

## 📖 Detailed Migration Examples

### Example 1: ML Training Pipeline

**Before (v7.x)**:
```bash
# Training script
#!/bin/bash
set -euo pipefail

echo "Training politician trading model..."
mcli-train politician-trading --output-dir models/

echo "Serving model..."
mcli-serve --model-path models/model.pt --port 8000
```

**After (v8.0)**:
```bash
# One-time setup: import workflows
mcli workflow import ml/training.json
mcli workflow import ml/serving.json
pip install mcli-framework[ml-plugin]

# Updated training script
#!/bin/bash
set -euo pipefail

echo "Training politician trading model..."
mcli workflows ml_train politician-trading --output-dir models/

echo "Serving model..."
mcli workflows ml_serve --model-path models/model.pt --port 8000
```

### Example 2: Trading Strategy Development

**Before (v7.x)**:
```python
#!/usr/bin/env python3
import subprocess

# Backtest
subprocess.run(["mcli-backtest",
    "--strategy", "momentum",
    "--start-date", "2023-01-01",
    "--end-date", "2024-01-01",
    "--symbols", "AAPL,GOOGL,MSFT"
])

# Optimize
subprocess.run(["mcli-optimize",
    "--symbols", "AAPL,GOOGL,MSFT",
    "--method", "max_sharpe"
])
```

**After (v8.0)**:
```python
#!/usr/bin/env python3
# One-time setup (run once):
# mcli workflow import trading/backtesting.json
# mcli workflow import trading/optimization.json
# pip install mcli-framework[trading-plugin]

import subprocess

# Backtest
subprocess.run(["mcli", "workflows", "ml_backtest",
    "--strategy", "momentum",
    "--start-date", "2023-01-01",
    "--end-date", "2024-01-01",
    "--symbols", "AAPL,GOOGL,MSFT"
])

# Optimize
subprocess.run(["mcli", "workflows", "ml_optimize",
    "--symbols", "AAPL,GOOGL,MSFT",
    "--method", "max_sharpe"
])
```

### Example 3: Video Processing Pipeline

**Before (v7.x)**:
```bash
# Process videos
for video in *.mp4; do
    python -m mcli.app.video.video analyze "$video"
done
```

**After (v8.0)**:
```bash
# One-time setup:
# mcli workflow import video/processing.json
# pip install mcli-framework[video-plugin]

# Process videos
for video in *.mp4; do
    mcli workflows video_process analyze "$video" --fps --frames --resolution
done
```

---

## 🔍 Testing Your Migration

### Verify Workflows Are Imported

```bash
mcli workflow list
# Should show: ml_train, ml_serve, ml_backtest, ml_optimize, ml_dashboard, video_process
```

### Verify Dependencies Are Installed

```bash
# Check if ML dependencies are available
python -c "import torch; import sklearn; import mlflow; print('ML plugin OK')"

# Check if trading dependencies are available
python -c "import yfinance; import cvxpy; print('Trading plugin OK')"

# Check if video dependencies are available
python -c "import cv2; import PIL; print('Video plugin OK')"
```

### Test Workflows

```bash
# Test ML training
mcli workflows ml_train --help

# Test trading backtesting
mcli workflows ml_backtest --help

# Test video processing
mcli workflows video_process --help
```

---

## ⚠️ Deprecation Timeline

### v7.14.0 (Deprecation Warnings)
- ✅ All old entry points still work
- ⚠️ Deprecation warnings shown when using old entry points
- ✅ New workflow system available
- ✅ Migration tools provided

**Example Warning**:
```
DeprecationWarning: mcli-train is deprecated and will be removed in v8.0.0.
Use 'mcli workflows ml_train' instead.
See migration guide: https://github.com/gwicho38/mcli/docs/MIGRATION_GUIDE_V8.md
```

### v7.15.0 - v7.99.0 (Grace Period)
- ⚠️ Continued deprecation warnings
- ✅ Both old and new methods work
- 📚 Updated documentation

### v8.0.0 (Breaking Changes)
- ❌ Old entry points removed
- ❌ ML/trading/video modules removed from core
- ✅ Workflows-only approach
- ✅ Smaller, faster core

---

## 🆘 Troubleshooting

### "Command not found: mcli-train"

**After upgrading to v8.0**, the old entry points no longer exist.

**Solution**:
```bash
# Import the workflow
mcli workflow import ml/training.json
pip install mcli-framework[ml-plugin]

# Use the workflow
mcli workflows ml_train --help
```

### "ModuleNotFoundError: No module named 'mcli.ml'"

The ML modules were removed from core.

**Solution**:
```bash
# Import workflows and install plugin
mcli workflow import ml/training.json
pip install mcli-framework[ml-plugin]
```

### "ImportError: cannot import name 'train_model'"

ML code is no longer in the core package.

**Solution**:
The code is now embedded in the workflow JSON. Import the workflow and it will work.

### Workflows Not Loading

```bash
# Check if workflows are imported
mcli workflow list

# If missing, import them
mcli workflow import ml/training.json

# Verify lockfile
mcli lock verify
mcli lock update
```

---

## 📦 For Package Maintainers

If you depend on mcli-framework in your package:

### Update Dependencies

**Before**:
```toml
[project]
dependencies = [
    "mcli-framework>=7.0.0",
]
```

**After**:
```toml
[project]
dependencies = [
    "mcli-framework>=8.0.0",
]

[project.optional-dependencies]
ml = [
    "mcli-framework[ml-plugin]>=8.0.0",
]
trading = [
    "mcli-framework[trading-plugin]>=8.0.0",
]
```

### Update Import Paths

**Before**:
```python
from mcli.ml.training import train_model
from mcli.ml.serving import start_server
```

**After**:
```python
# Import workflows instead
# The code is embedded in workflow JSON files
# Use subprocess to call workflows:
import subprocess

subprocess.run(["mcli", "workflows", "ml_train", ...])
subprocess.run(["mcli", "workflows", "ml_serve", ...])
```

---

## 🎁 Benefits After Migration

### Smaller Installation
- **Before**: ~500MB with all features
- **After**: ~20MB core + plugins you need

### Faster Startup
- **Before**: ~500ms (loading ML libraries)
- **After**: ~50ms (core only)

### Cleaner Dependencies
- **Before**: 136+ packages always installed
- **After**: ~15-20 core packages + opt-in plugins

### More Flexibility
- Install only what you need
- Update ML workflows independently
- Share workflows across team

---

## 📚 Additional Resources

- **mcli-commands Repository**: https://github.com/gwicho38/mcli-commands
- **Workflow Guide**: `docs/SCRIPT_SYNC_SYSTEM.md`
- **Plugin Documentation**: `docs/PLUGIN_SYSTEM.md`
- **Migration Script**: `scripts/migrate_features.py`

---

## 🤝 Support

If you encounter issues during migration:

1. Check this guide first
2. Search existing issues: https://github.com/gwicho38/mcli/issues
3. Ask on discussions: https://github.com/gwicho38/mcli/discussions
4. File a bug report: https://github.com/gwicho38/mcli/issues/new

---

**Last Updated**: 2025-11-13
**For MCLI**: v8.0.0
**Status**: Draft (Deprecation starts in v7.14.0)
