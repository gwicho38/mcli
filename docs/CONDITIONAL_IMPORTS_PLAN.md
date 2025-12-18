# Conditional Imports Implementation Plan

## Current Performance Issues
- **Startup time**: 2-3 seconds for basic commands
- **Memory usage**: High due to importing all ML libraries
- **Import analysis**: Heavy libraries loaded even for `mcli --help`

## Heavy Import Chains Identified

### 1. ML Dependencies
```python
# Currently in src/mcli/app/main.py (always loaded)
import torch  # 300MB+
import torchvision  # 100MB+
import tensorflow  # 200MB+
import scikit-learn  # 50MB+
import mlflow  # 40MB+
```

### 2. Dashboard Dependencies
```python
# Currently in CLI modules
import streamlit  # 50MB+
import plotly  # 30MB+
import matplotlib  # 40MB+
```

### 3. Trading Dependencies
```python
# Currently loaded for basic commands
import pandas  # 50MB+
import numpy  # 50MB+
import yfinance  # 20MB+
```

## Implementation Strategy

### Phase 1: Core Commands Optimization (Immediate)

#### 1.1 Feature Detection
```python
# src/mcli/lib/feature_detection.py
def has_ml_features():
    """Check if user is actually using ML features"""
    return (
        os.getenv("MCLI_ENABLE_ML", "").lower() == "true" or
        check_for_ml_imports()
    )

def has_dashboard_features():
    return (
        os.getenv("MCLI_ENABLE_DASHBOARD", "").lower() == "true" or
        check_for_dashboard_imports()
    )
```

#### 1.2 Lazy Loading Wrapper
```python
# src/mcli/lib/lazy_imports.py
class LazyLoader:
    def __init__(self, module_name: str, fallback=None):
        self.module_name = module_name
        self._module = None
        self._fallback = fallback
    
    def __getattr__(self, name):
        if self._module is None:
            try:
                self._module = importlib.import_module(self.module_name)
            except ImportError:
                if self._fallback:
                    return self._fallback
                raise
        return getattr(self._module, name)

# Usage
torch = LazyLoader("torch", fallback=MockTorch())
streamlit = LazyLoader("streamlit", fallback=MockStreamlit())
```

#### 1.3 Command Entry Point Optimization
```python
# src/mcli/app/main.py (optimized)
def load_core_imports():
    """Only load essential imports"""
    import click, rich, requests, tomli, python_dotenv
    return True

def load_conditional_imports():
    """Load imports based on feature usage"""
    # Only load ML if actually needed
    if os.getenv("MCLI_ENABLE_ML"):
        import torch, mlflow, scikit_learn
    
    # Only load dashboard if needed
    if os.getenv("MCLI_ENABLE_DASHBOARD"):
        import streamlit, plotly
    
    # Only load trading if needed  
    if os.getenv("MCLI_ENABLE_TRADING"):
        import pandas, yfinance
    
    return True

def main():
    load_core_imports()
    
    # Check if we need extra features for this command
    if requires_features(sys.argv):
        load_conditional_imports()
    
    # Rest of main...
```

### Phase 2: Progressive Loading (Week 2)

#### 2.1 Import Profiling
```python
# src/mcli/lib/import_profiler.py
class ImportProfiler:
    def profile_import(self, module_name: str):
        start = time.time()
        mem_before = psutil.Process().memory_info().rss
        module = importlib.import_module(module_name)
        mem_after = psutil.Process().memory_info().rss
        
        return {
            'module': module_name,
            'import_time': time.time() - start,
            'memory_delta': mem_after - mem_before
        }
```

#### 2.2 Startup Time Measurement
```python
# src/mcli/lib/startup_timer.py
def time_startup():
    start = time.time()
    # ... initialization ...
    end = time.time()
    logger.info(f"Startup completed in {end - start:.2f}s")
```

### Phase 3: Advanced Optimization (Week 3)

#### 3.1 Module Caching
```python
# Cache imported modules for faster subsequent loads
IMPORT_CACHE = {}

def cached_import(module_name: str):
    if module_name not in IMPORT_CACHE:
        IMPORT_CACHE[module_name] = importlib.import_module(module_name)
    return IMPORT_CACHE[module_name]
```

#### 3.2 Selective Import Unloading
```python
# For long-running processes
def unload_heavy_modules():
    modules_to_unload = ['torch', 'tensorflow', 'streamlit']
    for module_name in modules_to_unload:
        if module_name in sys.modules:
            del sys.modules[module_name]
```

## Implementation Files

### New Files to Create
1. `src/mcli/lib/feature_detection.py`
2. `src/mcli/lib/lazy_imports.py`
3. `src/mcli/lib/import_profiler.py`
4. `src/mcli/lib/startup_timer.py`
5. `src/mcli/lib/performance_config.py`

### Files to Modify
1. `src/mcli/app/main.py` - Add conditional loading
2. `src/mcli/app/commands_cmd.py` - Optimize command loading
3. `src/mcli/chat/` - Add lazy loading for AI features
4. `src/mcli/workflow/` - Optimize workflow loading

## Expected Performance Gains

### Startup Time
- **Current**: 2-3 seconds
- **After Phase 1**: 0.8-1.2 seconds
- **After Phase 2**: 0.5-0.8 seconds
- **After Phase 3**: 0.3-0.5 seconds

### Memory Usage
- **Current**: 400-500MB for basic commands
- **After Phase 1**: 100-200MB for basic commands
- **After Phase 2**: 80-150MB for basic commands
- **After Phase 3**: 50-100MB for basic commands

## Testing Strategy

### Performance Benchmarks
```python
def benchmark_startup():
    # Test 10 startup cycles
    times = []
    for i in range(10):
        start = time.time()
        subprocess.run(['python', '-m', 'mcli', '--help'])
        end = time.time()
        times.append(end - start)
    
    print(f"Average startup time: {statistics.mean(times):.2f}s")
```

### Feature Functionality Tests
```python
def test_lazy_loading():
    # Test that all features still work
    test_ml_features()
    test_dashboard_features()
    test_trading_features()
```

## Configuration Options

### Environment Variables
```bash
# Enable only what you need
export MCLI_ENABLE_ML=false
export MCLI_ENABLE_DASHBOARD=false  
export MCLI_ENABLE_TRADING=false
export MCLI_STARTUP_PROFILE=true
```

### Config File Options
```toml
# ~/.mcli/config.toml
[performance]
lazy_loading = true
profile_startup = false
preload_modules = ["click", "rich", "requests"]
```

## User Experience

### Error Messages
```python
# When feature is needed but not loaded
try:
    import torch
except ImportError as e:
    click.echo(f"ML features require extra installation: pip install mcli[ml]")
    sys.exit(1)
```

### Installation Commands
```bash
# Auto-detect and install missing features
mcli install-features  # Analyze usage and suggest extras
mcli install-ml      # Install ML features
mcli install-dashboard # Install dashboard features
```

This plan provides a structured approach to dramatically improve startup performance while maintaining full functionality when needed."