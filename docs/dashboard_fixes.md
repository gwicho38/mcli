# Dashboard Fixes - October 2025

## Issues Fixed

### 1. **White Screen / Blank Page** ✅
**Problem**: Dashboard showed empty white screen with navigation not working

**Root Cause**: The auto-refresh logic was using `time.sleep(30)` which blocked the entire Streamlit app, preventing any content from rendering.

**Fix**:
- Changed auto-refresh to use `streamlit-autorefresh` component (non-blocking)
- Set auto-refresh default to `False` (off) to prevent initial blocking
- Added fallback handling if `streamlit-autorefresh` isn't installed

### 2. **Navigation Not Working** ✅
**Problem**: Sidebar navigation dropdown didn't properly switch pages

**Root Cause**: App was blocked by sleep call before page routing logic could execute

**Fix**:
- Fixed auto-refresh blocking issue
- Added explicit `index=0` to default to "Pipeline Overview" page
- Added comprehensive error handling for page loading

### 3. **Missing Data / No Supabase Connection** ✅
**Problem**: No data displayed, silent failures

**Root Cause**: Supabase credentials not configured, causing empty DataFrames

**Fix**:
- Added clear warning message when Supabase isn't configured
- Added instructions for setting environment variables
- Functions now gracefully return empty DataFrames instead of crashing
- Dashboard shows demo/mock data when real data unavailable

### 4. **Import Errors** ✅
**Problem**: `ModuleNotFoundError: No module named 'mcli.ml.preprocessing.data_preprocessor'`

**Root Cause**: Non-existent modules referenced in imports

**Fix**:
- Updated imports to use actual available classes:
  - `PoliticianTradingPreprocessor` instead of `DataPreprocessor`
  - `MLDataPipeline` instead of `FeatureEngineering`
- Added graceful fallback when ML pipeline modules aren't available

## How to Use

### 1. Restart the Dashboard

If you have the dashboard running, stop it (Ctrl+C) and restart:

```bash
make dashboard
```

Or manually:
```bash
.venv/bin/python -m streamlit run src/mcli/ml/dashboard/app_integrated.py \
    --server.port 8501 \
    --server.address localhost
```

### 2. Configure Supabase (Optional)

To see real data instead of demo data, set environment variables:

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-api-key"
```

Then restart the dashboard.

### 3. Navigate the Dashboard

The dashboard now has 6 pages accessible via the sidebar dropdown:

1. **Pipeline Overview** (default) - System metrics, data sources, LSH jobs
2. **ML Processing** - Data preprocessing and feature engineering
3. **Model Performance** - Model metrics and accuracy tracking
4. **Predictions** - Recent predictions and analysis
5. **LSH Jobs** - LSH daemon job status and logs
6. **System Health** - API, Redis, Database health checks

### 4. Use Controls

**Sidebar Controls:**
- 📊 **Page Selection**: Dropdown to switch between pages
- ☑️ **Auto-refresh**: Enable 30-second auto-refresh (requires `streamlit-autorefresh`)
- 🔄 **Refresh Now**: Manual refresh button
- 🚀 **Run ML Pipeline**: Execute the full ML pipeline on demand

## Known Limitations

1. **Auto-refresh**: Requires `streamlit-autorefresh` package
   - If not installed, auto-refresh won't work
   - Shows warning in sidebar when enabled without package

2. **Demo Data**: Without Supabase configuration:
   - Shows mock/random data for metrics
   - LSH jobs read from local log file if available
   - Models read from local `models/` directory if available

3. **ML Pipeline**: Some features require:
   - Trained models in `models/` directory
   - Proper Supabase schema (politicians, trading_disclosures tables)

## Testing

Verify the fixes work:

```bash
# 1. Test dashboard launches
make dashboard

# 2. Check navigation works
# - Select different pages from dropdown
# - Verify content loads for each page

# 3. Test controls
# - Click "Refresh Now" button
# - Toggle auto-refresh (if streamlit-autorefresh installed)
# - Click "Run ML Pipeline" button
```

## Updated Files

1. `src/mcli/ml/dashboard/app_integrated.py`:
   - Fixed auto-refresh logic (non-blocking)
   - Added error handling for page loading
   - Added Supabase configuration warnings
   - Fixed imports to use available modules
   - Added fallback for missing components

2. `Makefile`:
   - Added dashboard targets (already done)

3. `pyproject.toml`:
   - Removed problematic `mcli[chat,...]` dependency (already done)

## Quick Reference

```bash
# Launch dashboard
make dashboard

# Alternative ports
make dashboard-training     # Port 8502
make dashboard-supabase     # Port 8503
make dashboard-basic        # Port 8504

# With Supabase
export SUPABASE_URL="..."
export SUPABASE_KEY="..."
make dashboard
```

## Screenshots Expected

After fixes, you should see:

1. **Title**: "🤖 MCLI ML System Dashboard - Integrated"
2. **Subtitle**: "Real-time ML pipeline monitoring with LSH daemon integration"
3. **Sidebar**: Navigation dropdown, controls, buttons
4. **Main Content**:
   - Warning about Supabase if not configured
   - 4-column metrics dashboard
   - Charts and visualizations
   - Pipeline flow diagram

If you still see a white screen, check browser console for JavaScript errors or file an issue with error details.
