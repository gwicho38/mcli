# Optional Dependencies Handling Guide

This guide explains how to gracefully handle optional dependencies in the MCLI codebase.

## Overview

MCLI provides utilities to handle optional dependencies gracefully, preventing import errors and providing clear error messages when features are unavailable.

## Why Use Optional Dependency Handling?

1. **Better User Experience**: Users get clear error messages instead of cryptic import errors
2. **Graceful Degradation**: Features can fall back to alternatives when dependencies are missing
3. **Reduced Startup Time**: Heavy dependencies are only imported when needed
4. **Flexible Installation**: Users can install only the dependencies they need

## Usage Patterns

### Pattern 1: Simple Optional Import

Use `optional_import()` for simple cases where you want to check if a module is available:

```python
from mcli.lib.optional_deps import optional_import

# Try to import ollama
ollama, OLLAMA_AVAILABLE = optional_import("ollama")

def use_ollama():
    if not OLLAMA_AVAILABLE:
        print("Ollama not available. Install with: pip install ollama")
        return

    # Use ollama safely
    client = ollama.Client()
    # ...
```

### Pattern 2: Require Dependency with Clear Error

Use `require_dependency()` when a feature absolutely needs a dependency:

```python
from mcli.lib.optional_deps import require_dependency

def launch_dashboard():
    # Will raise ImportError with clear message if streamlit not available
    streamlit = require_dependency("streamlit", "dashboard")

    streamlit.set_page_config(...)
    # ...
```

### Pattern 3: Function-Level Requirements

Use the `@requires` decorator to mark functions that need specific dependencies:

```python
from mcli.lib.optional_deps import requires

@requires("torch", "transformers")
def train_model():
    import torch
    import transformers

    # Training code here
    # ...
```

If a user tries to call `train_model()` without torch or transformers installed, they'll get:

```
ImportError: Function 'train_model' requires missing dependencies: torch, transformers
Install them with: pip install torch transformers
```

### Pattern 4: OptionalDependency Class

Use the `OptionalDependency` class for more control:

```python
from mcli.lib.optional_deps import OptionalDependency

# Create optional dependency handler
ollama = OptionalDependency("ollama")

if ollama.available:
    # Use the module
    client = ollama.Client()
else:
    # Fallback behavior
    print(f"Ollama not available: {ollama.error}")
```

## Best Practices

### 1. Check Availability Early

Check for optional dependencies at the start of functions:

```python
def ai_commit_message(changes):
    if not OLLAMA_AVAILABLE:
        logger.warning("Ollama not installed, using fallback")
        return fallback_commit_message(changes)

    # Use ollama
    response = ollama.generate(...)
    return response
```

### 2. Provide Helpful Error Messages

Include installation instructions in error messages:

```python
if not TORCH_AVAILABLE:
    raise ImportError(
        "PyTorch is required for ML training features.\n"
        "Install with: pip install torch\n"
        "Or install the ML extras: pip install mcli-framework[ml]"
    )
```

### 3. Use Graceful Degradation

Provide alternatives when possible:

```python
if PLOTLY_AVAILABLE:
    # Use interactive plotly charts
    fig = plotly.graph_objects.Figure(...)
else:
    # Fall back to matplotlib
    logger.info("Plotly not available, using matplotlib")
    fig, ax = plt.subplots()
    ax.plot(...)
```

### 4. Document Optional Features

In docstrings, clearly indicate when a feature requires optional dependencies:

```python
def train_transformer_model(data):
    """
    Train a transformer model on the provided data.

    Requires:
        - torch: pip install torch
        - transformers: pip install transformers

    Or install all ML dependencies:
        pip install mcli-framework[ml]
    """
    # Implementation
```

## Migration Guide

### Migrating Existing Code

**Before:**
```python
import ollama  # Fails if not installed

def use_ollama():
    client = ollama.Client()
    # ...
```

**After:**
```python
from mcli.lib.optional_deps import optional_import

ollama, OLLAMA_AVAILABLE = optional_import("ollama")

def use_ollama():
    if not OLLAMA_AVAILABLE:
        raise ImportError("Ollama required. Install with: pip install ollama")

    client = ollama.Client()
    # ...
```

### Common Optional Dependencies

The following dependencies are pre-registered:

- `ollama` - Local LLM inference
- `streamlit` - Dashboard framework
- `torch` - Deep learning
- `transformers` - Transformer models
- `mlflow` - ML experiment tracking
- `plotly` - Interactive charts
- `pandas` - Data manipulation
- `numpy` - Numerical computing

## Testing with Optional Dependencies

When writing tests, you can check dependency availability:

```python
import pytest
from mcli.lib.optional_deps import optional_import

ollama, OLLAMA_AVAILABLE = optional_import("ollama")

@pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="Requires ollama")
def test_ollama_integration():
    # Test code that uses ollama
    pass
```

## Examples from Codebase

### Example 1: AI Service with Fallback

```python
# src/mcli/workflow/git_commit/ai_service.py
from mcli.lib.optional_deps import optional_import

ollama, OLLAMA_AVAILABLE = optional_import("ollama")

class GitCommitAIService:
    def generate_commit_message(self, changes, diff_content):
        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama not available, using fallback")
            return self._generate_fallback_message(changes)

        # Use AI-powered generation
        response = ollama.generate(...)
        return response
```

### Example 2: Dashboard with Required Dependencies

```python
# src/mcli/ml/dashboard/app.py
from mcli.lib.optional_deps import requires

@requires("streamlit", "plotly", install_all_hint="pip install mcli-framework[dashboard]")
def launch_dashboard():
    import streamlit as st
    import plotly.graph_objects as go

    st.set_page_config(...)
    # Dashboard code
```

### Example 3: ML Training with Multiple Dependencies

```python
# src/mcli/ml/training/train_model.py
from mcli.lib.optional_deps import check_dependencies, requires

def check_ml_environment():
    """Check which ML dependencies are available."""
    deps = check_dependencies("torch", "transformers", "mlflow", "tensorboard")

    for name, available in deps.items():
        status = "✓" if available else "✗"
        print(f"{status} {name}")

    return all(deps.values())

@requires("torch", "transformers", install_all_hint="pip install mcli-framework[ml]")
def train_model(config):
    # Training code
    pass
```

## FAQ

### Q: Should every import be optional?

No. Core dependencies that are always installed (like `click`, `rich`, `requests`) don't need optional handling. Only use this for truly optional features.

### Q: What about standard library modules?

Standard library modules (like `os`, `sys`, `json`) are always available and don't need optional handling.

### Q: Can I use this with submodule imports?

Yes! You can access submodules through the OptionalDependency:

```python
dep = OptionalDependency("sklearn")
if dep.available:
    linear_model = dep.linear_model  # Access sklearn.linear_model
```

### Q: What if a dependency has a different import name?

Use the `import_name` parameter:

```python
# Package is "Pillow" but import is "PIL"
pil, PIL_AVAILABLE = optional_import("pillow", import_name="PIL")
```

## See Also

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guidelines
- [Optional Dependencies API Reference](../api/optional_deps.md)
- Issue #41: Implement graceful handling of optional dependencies
