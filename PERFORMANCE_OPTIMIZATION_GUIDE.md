# MCLI Performance Optimization Guide

This guide helps you profile and optimize MCLI startup performance to identify bottlenecks and improve runtime speed.

## 🚀 Quick Start

Run the comprehensive profiling suite:

```bash
./profile.sh
```

This will:
1. Build wheel and binary
2. Profile startup times
3. Compare with pure Click
4. Generate optimization recommendations
5. Save detailed results

## 📊 Profiling Tools

### 1. Startup Profiling (`profile_startup.py`)

Profiles MCLI module imports and identifies bottlenecks:

```bash
python profile_startup.py
```

**Measures:**
- Import times for each module
- Memory usage during import
- Decorator creation time
- CLI creation time
- API server startup time
- Background service availability

### 2. Binary/Wheel Profiling (`profile_binary_wheel.py`)

Profiles the built binary and wheel installation:

```bash
python profile_binary_wheel.py
```

**Measures:**
- Python module import time
- Wheel installation time
- Binary execution time
- Comparison with pure Click
- Detailed timing analysis

## 🔍 Understanding the Results

### Import Time Benchmarks

| Time Range | Performance Level | Action Needed |
|------------|------------------|---------------|
| < 100ms    | Excellent        | No optimization needed |
| 100-300ms  | Good            | Monitor for regressions |
| 300-500ms  | Moderate        | Consider optimizations |
| 500-1000ms | Slow            | Optimize imports |
| > 1000ms   | Very Slow       | Major optimization required |

### Memory Usage Benchmarks

| Memory Range | Performance Level | Action Needed |
|--------------|------------------|---------------|
| < 20MB      | Excellent        | No optimization needed |
| 20-50MB     | Good            | Monitor for regressions |
| 50-100MB    | Moderate        | Consider optimizations |
| 100-200MB   | High            | Optimize memory usage |
| > 200MB     | Very High       | Major optimization required |

## 🛠️ Optimization Strategies

### 1. Lazy Loading

**Problem:** Heavy imports slow down startup
**Solution:** Import modules only when needed

```python
# Before (eager loading)
import fastapi
import uvicorn
import click

# After (lazy loading)
def get_fastapi():
    import fastapi
    return fastapi

def get_uvicorn():
    import uvicorn
    return uvicorn
```

### 2. Conditional Imports

**Problem:** Optional dependencies loaded unnecessarily
**Solution:** Import only when features are used

```python
# Before
import fastapi
import uvicorn

# After
def start_api_server():
    try:
        import fastapi
        import uvicorn
        # Use FastAPI/Uvicorn
    except ImportError:
        raise ImportError("FastAPI and Uvicorn required for API features")
```

### 3. Module Caching

**Problem:** Repeated imports slow down execution
**Solution:** Cache imported modules

```python
# Cache expensive imports
_fastapi_cache = None
_uvicorn_cache = None

def get_fastapi():
    global _fastapi_cache
    if _fastapi_cache is None:
        import fastapi
        _fastapi_cache = fastapi
    return _fastapi_cache
```

### 4. Dependency Optimization

**Problem:** Heavy dependencies increase startup time
**Solution:** Use lighter alternatives or optional dependencies

```python
# Use lighter alternatives
try:
    import orjson as json  # Faster than json
except ImportError:
    import json  # Fallback to standard json
```

### 5. Binary Optimization

**Problem:** Large binary size and slow startup
**Solution:** Optimize PyInstaller configuration

```python
# In spec file or build script
a = Analysis(
    ['main.py'],
    excludes=['matplotlib', 'numpy', 'pandas'],  # Exclude heavy libs
    hiddenimports=['mcli.lib.api.mcli_decorators'],  # Include only needed
    strip=True,  # Strip debug symbols
    upx=True,    # Compress binary
)
```

## 📈 Performance Monitoring

### Continuous Monitoring

Add performance checks to your CI/CD pipeline:

```yaml
# .github/workflows/performance.yml
name: Performance Check
on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -e .
      - name: Run performance tests
        run: |
          python profile_startup.py
          python profile_binary_wheel.py
      - name: Check performance thresholds
        run: |
          # Fail if import time > 500ms
          python -c "
          import json
          with open('profiling_results.json') as f:
              data = json.load(f)
          if data['python_module']['average'] > 500:
              exit(1)
          "
```

### Performance Regression Detection

Create a script to detect performance regressions:

```python
# check_performance.py
import json
import sys

def check_performance_thresholds():
    with open('profiling_results.json') as f:
        data = json.load(f)
    
    failures = []
    
    # Check import time
    if data['python_module']['average'] > 500:
        failures.append(f"Import time too high: {data['python_module']['average']:.2f}ms")
    
    # Check binary startup
    if data['binary']['help_command']['average'] > 1000:
        failures.append(f"Binary startup too slow: {data['binary']['help_command']['average']:.2f}ms")
    
    # Check overhead vs Click
    if data['comparison']['mcli']['average'] - data['comparison']['click']['average'] > 200:
        failures.append("MCLI overhead too high vs Click")
    
    if failures:
        print("❌ Performance regressions detected:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("✅ Performance within acceptable thresholds")

if __name__ == "__main__":
    check_performance_thresholds()
```

## 🎯 Common Bottlenecks and Solutions

### 1. Heavy Dependencies

**Symptoms:**
- Slow import times (>500ms)
- High memory usage (>100MB)

**Solutions:**
- Use optional dependencies
- Implement lazy loading
- Consider lighter alternatives

### 2. Inefficient Decorators

**Symptoms:**
- Slow decorator creation (>1000μs)
- High overhead vs Click

**Solutions:**
- Optimize decorator logic
- Cache expensive operations
- Use simpler implementations

### 3. Binary Size Issues

**Symptoms:**
- Large binary size (>50MB)
- Slow binary startup (>1000ms)

**Solutions:**
- Exclude unnecessary modules
- Use UPX compression
- Strip debug symbols

### 4. Memory Leaks

**Symptoms:**
- Increasing memory usage over time
- High peak memory usage

**Solutions:**
- Fix circular references
- Properly close resources
- Use weak references where appropriate

## 📋 Optimization Checklist

### Before Optimization
- [ ] Run comprehensive profiling
- [ ] Identify specific bottlenecks
- [ ] Set performance targets
- [ ] Establish baseline metrics

### During Optimization
- [ ] Implement lazy loading for heavy modules
- [ ] Optimize import statements
- [ ] Use conditional imports
- [ ] Cache expensive operations
- [ ] Minimize binary size

### After Optimization
- [ ] Re-run profiling
- [ ] Compare with baseline
- [ ] Check for regressions
- [ ] Update documentation
- [ ] Set up monitoring

## 🔧 Advanced Profiling

### Using cProfile for Detailed Analysis

```bash
python -m cProfile -o profile.stats profile_startup.py
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"
```

### Using memory_profiler

```bash
pip install memory_profiler
python -m memory_profiler profile_startup.py
```

### Using py-spy for Real-time Profiling

```bash
pip install py-spy
py-spy top -- python profile_startup.py
```

## 📊 Performance Metrics Dashboard

Create a simple dashboard to track performance over time:

```python
# performance_dashboard.py
import json
import matplotlib.pyplot as plt
from datetime import datetime

def create_performance_dashboard():
    with open('profiling_results.json') as f:
        data = json.load(f)
    
    metrics = {
        'Import Time (ms)': data['python_module']['average'],
        'Binary Startup (ms)': data['binary']['help_command']['average'],
        'Wheel Install (ms)': data['wheel']['install_time'],
        'Click Overhead (ms)': data['comparison']['mcli']['average'] - data['comparison']['click']['average']
    }
    
    # Create visualization
    plt.figure(figsize=(10, 6))
    plt.bar(metrics.keys(), metrics.values())
    plt.title('MCLI Performance Metrics')
    plt.ylabel('Time (ms)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('performance_dashboard.png')
    plt.close()

if __name__ == "__main__":
    create_performance_dashboard()
```

## 🎉 Success Metrics

Your optimization is successful when:

- ✅ Import time < 300ms
- ✅ Binary startup < 500ms
- ✅ Memory usage < 50MB
- ✅ Overhead vs Click < 200ms
- ✅ No performance regressions in CI/CD

## 📚 Additional Resources

- [Python Performance Profiling Guide](https://docs.python.org/3/library/profile.html)
- [PyInstaller Optimization](https://pyinstaller.readthedocs.io/en/stable/usage.html)
- [Click Performance Best Practices](https://click.palletsprojects.com/en/8.1.x/)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/tutorial/deployment/)

Remember: **Profile first, optimize second, measure third!** 