# Dashboard Makefile Usage

## Quick Start

Launch the integrated ML dashboard with LSH integration:

```bash
make dashboard
```

This will start the dashboard at http://localhost:8501

## Available Dashboard Targets

### 1. **Integrated Dashboard** (Default)
```bash
make dashboard                # Default - launches integrated dashboard
make dashboard-integrated     # Same as above, explicit name
```
- **Port**: 8501
- **Features**: ML jobs monitoring + LSH daemon integration
- **File**: `src/mcli/ml/dashboard/app_integrated.py`

### 2. **Training Dashboard**
```bash
make dashboard-training
```
- **Port**: 8502
- **Features**: ML training-focused monitoring
- **File**: `src/mcli/ml/dashboard/app_training.py`

### 3. **Supabase Dashboard**
```bash
make dashboard-supabase
```
- **Port**: 8503
- **Features**: Supabase-focused monitoring
- **File**: `src/mcli/ml/dashboard/app_supabase.py`

### 4. **Basic Dashboard**
```bash
make dashboard-basic
```
- **Port**: 8504
- **Features**: Basic ML monitoring
- **File**: `src/mcli/ml/dashboard/app.py`

### 5. **CLI Commands**
```bash
make dashboard-cli           # Uses mcli-dashboard CLI
make dashboard-workflow      # Uses mcli workflow dashboard launch
```

## Features by Dashboard Type

### Integrated Dashboard (Recommended)
- ✅ ML training job monitoring
- ✅ LSH daemon integration
- ✅ Real-time predictions
- ✅ Model performance metrics
- ✅ Portfolio analytics
- ✅ System health checks
- ✅ Live monitoring with auto-refresh

### Training Dashboard
- ✅ Training progress tracking
- ✅ Loss/accuracy curves
- ✅ Hyperparameter monitoring
- ✅ Resource utilization

### Supabase Dashboard
- ✅ Database monitoring
- ✅ Supabase-specific metrics
- ✅ Query performance

### Basic Dashboard
- ✅ Essential ML metrics
- ✅ Lightweight interface

## Troubleshooting

### Dashboard won't start
```bash
# Ensure dependencies are installed
make setup

# Check if streamlit is available
.venv/bin/python -c "import streamlit; print(streamlit.__version__)"
```

### Port already in use
Each dashboard variant uses a different port, so you can run multiple dashboards simultaneously:
- Port 8501: Integrated
- Port 8502: Training
- Port 8503: Supabase
- Port 8504: Basic

### Dependency issues
If you encounter dependency resolution errors:
```bash
# Regenerate lock file
uv lock

# Re-setup environment
make clean
make setup
```

## Environment Variables

The dashboards use these environment variables (if available):
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase API key
- `REDIS_URL`: Redis connection URL

## Implementation Details

All dashboard targets:
1. Run the `setup` target first to ensure environment is ready
2. Use the virtual environment Python (`$(VENV_PYTHON)`)
3. Launch streamlit with appropriate configuration
4. Disable usage statistics collection
5. Bind to localhost by default

## See Also

- [DASHBOARD.md](../DASHBOARD.md) - Full dashboard documentation
- [Makefile](../Makefile) - Complete build system reference
