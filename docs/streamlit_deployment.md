# Streamlit Cloud Deployment Guide

## Dashboard Deployment Configuration

### Main File Path

When deploying to Streamlit Cloud, use this as the **Main file path**:

```
src/mcli/ml/dashboard/app_integrated.py
```

This is the integrated ML dashboard with:
- ML jobs monitoring
- LSH daemon integration
- Supabase real-time data
- Model performance tracking
- System health monitoring

## Deployment Steps

### 1. Connect Repository

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select repository: `gwicho38/mcli`
4. Branch: `main`
5. Main file path: `src/mcli/ml/dashboard/app_integrated.py`

### 2. Configure Environment Secrets

In the Streamlit Cloud dashboard, add these secrets:

```toml
# .streamlit/secrets.toml format

[secrets]
SUPABASE_URL = "https://uljsqvwkomdrlnofmlad.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjgwMjI0NCwiZXhwIjoyMDcyMzc4MjQ0fQ.4364sQbTJQd4IcxEQG6mPiOUw1iJ2bdKfV6W4oRqHvs"

# LSH Daemon API (Production - Deployed on Fly.io)
LSH_API_URL = "https://mcli-lsh-daemon.fly.dev"
```

**Or in the UI:**
- Key: `SUPABASE_URL`, Value: `https://uljsqvwkomdrlnofmlad.supabase.co`
- Key: `SUPABASE_KEY`, Value: `<your-anon-key>`
- Key: `SUPABASE_SERVICE_ROLE_KEY`, Value: `<your-service-role-key>`

### 3. Python Version

Ensure `python_version` in `.python-version` or runtime configuration:
```
3.11
```

### 4. Dependencies

The app will automatically install from `pyproject.toml`. Key dependencies:
- `streamlit>=1.50.0`
- `supabase>=2.18.1`
- `plotly>=5.17.0`
- `pandas>=2.3.1`
- `python-dotenv>=1.1.1`

## Alternative Dashboard Variants

You can deploy different dashboard variants by changing the main file path:

### Training Dashboard
```
src/mcli/ml/dashboard/app_training.py
```
Focus: ML training progress, loss curves, hyperparameters

### Supabase Dashboard
```
src/mcli/ml/dashboard/app_supabase.py
```
Focus: Supabase database monitoring

### Basic Dashboard
```
src/mcli/ml/dashboard/app.py
```
Focus: Essential ML metrics only

## Local Testing Before Deployment

Test the app locally first:

```bash
# Using Makefile
make dashboard

# Or manually
streamlit run src/mcli/ml/dashboard/app_integrated.py
```

Visit: http://localhost:8501

## Troubleshooting Streamlit Cloud

### App Won't Start

**Check logs in Streamlit Cloud dashboard:**
1. Click "Manage app"
2. View "Logs" tab
3. Look for import errors or missing dependencies

**Common issues:**
- Missing environment secrets → Add to secrets configuration
- Import errors → Check `pyproject.toml` dependencies
- Port conflicts → Streamlit Cloud handles this automatically

### Missing Data

If dashboard shows "Supabase not configured":
- Verify secrets are set correctly in Streamlit Cloud
- Check secret names match exactly: `SUPABASE_URL`, `SUPABASE_KEY`
- Restart the app after adding secrets

### Slow Performance

The dashboard caches data with TTL (time-to-live):
- Politicians data: 30 seconds
- Disclosures data: 30 seconds
- Model metrics: 30 seconds
- ML pipeline results: 60 seconds

To adjust caching, modify `@st.cache_data(ttl=X)` decorators in the source.

## App Configuration

### Streamlit Config (Optional)

Create `.streamlit/config.toml` in repo:

```toml
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
serverAddress = "localhost"

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### Requirements for Streamlit Cloud

Streamlit Cloud reads from `pyproject.toml` automatically. No separate `requirements.txt` needed.

If you prefer a standalone `requirements.txt`:

```bash
# Generate from current environment
uv pip compile pyproject.toml -o requirements.txt
```

## Dashboard Features

Once deployed, your dashboard will provide:

### Pages Available
1. **Pipeline Overview** - System metrics, data sources, LSH jobs
2. **ML Processing** - Data preprocessing, feature engineering
3. **Model Performance** - Accuracy tracking, metrics over time
4. **Predictions** - Recent predictions, ticker filtering
5. **LSH Jobs** - Daemon status, job logs
6. **System Health** - API/Redis/Database monitoring

### Controls
- 🔄 **Refresh Now** - Manual data refresh
- ☑️ **Auto-refresh** - 30-second auto-refresh
- 🚀 **Run ML Pipeline** - Execute pipeline on demand
- 📊 **Page Selection** - Navigate between views

## Monitoring Deployed App

### Streamlit Cloud Dashboard

Monitor your app at:
```
https://share.streamlit.io/app/<your-app-url>
```

Features:
- **Logs**: Real-time application logs
- **Analytics**: Usage statistics, viewer count
- **Resources**: CPU, memory usage
- **Errors**: Exception tracking

### Custom Monitoring

The dashboard includes built-in monitoring:
- **System Health** page shows component status
- **LSH Jobs** page tracks background jobs
- **Model Performance** tracks ML metrics

## Updating the Deployed App

Streamlit Cloud auto-deploys on git push to main:

```bash
# Make changes locally
git add .
git commit -m "Update dashboard"
git push origin main

# Streamlit Cloud detects and redeploys automatically
```

Force a redeploy:
1. Go to Streamlit Cloud dashboard
2. Click "Reboot app"

## Security Notes

⚠️ **Important**: Never commit secrets to git

- ✅ Use Streamlit secrets configuration
- ✅ Keep `.env` in `.gitignore`
- ✅ Use environment variables
- ❌ Don't hardcode API keys in source code
- ❌ Don't commit `.env` or secrets files

## App URL

After deployment, your app will be available at:
```
https://share.streamlit.io/<username>/<repo>/main/src/mcli/ml/dashboard/app_integrated.py
```

Or a custom URL if configured.

## Support

- **Streamlit Docs**: https://docs.streamlit.io/streamlit-community-cloud
- **Dashboard Issues**: https://github.com/gwicho38/mcli/issues
- **Local Testing**: `make dashboard`

## Example Deployment YAML (GitHub Actions)

If you want to automate deployment testing:

```yaml
# .github/workflows/streamlit-test.yml
name: Test Streamlit App

on:
  push:
    branches: [ main ]
    paths:
      - 'src/mcli/ml/dashboard/**'
      - 'pyproject.toml'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install UV
        run: pip install uv

      - name: Install dependencies
        run: uv sync

      - name: Test dashboard loads
        run: |
          timeout 30 streamlit run src/mcli/ml/dashboard/app_integrated.py --server.headless true &
          sleep 10
          curl http://localhost:8501 || exit 1
```

---

**Ready to deploy!** Use `src/mcli/ml/dashboard/app_integrated.py` as your main file path.
