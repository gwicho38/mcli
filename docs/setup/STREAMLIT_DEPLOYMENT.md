# Streamlit Cloud Deployment Guide

Deploy the MCLI ML Dashboard to Streamlit Cloud for public access.

## Prerequisites

- GitHub account with access to the mcli repository
- Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
- Supabase project with active credentials

## Deployment Steps

### 1. Prepare Repository

The repository already includes the necessary files:

- **Dashboard App**: `src/mcli/ml/dashboard/app_supabase.py`
- **Requirements**: `streamlit_requirements.txt`
- **Secrets Template**: `.streamlit/secrets.toml` (for local testing)

### 2. Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)

2. Click "New app"

3. Configure the app:
   - **Repository**: `gwicho38/mcli`
   - **Branch**: `main`
   - **Main file path**: `src/mcli/ml/dashboard/app_supabase.py`
   - **Python version**: 3.11 (recommended)

4. Advanced settings:
   - **Requirements file**: `streamlit_requirements.txt`

### 3. Configure Secrets

In the Streamlit Cloud dashboard:

1. Click on your app
2. Go to **Settings** → **Secrets**
3. Add the following secrets:

```toml
SUPABASE_URL = "https://uljsqvwkomdrlnofmlad.supabase.co"
SUPABASE_KEY = "your_anon_key_here"
SUPABASE_ANON_KEY = "your_anon_key_here"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key_here"
```

**Important**: Replace the values with your actual Supabase credentials from `.env.production`.

### 4. Deploy

Click "Deploy" and wait for the app to build and start.

The app will be available at: `https://your-app-name.streamlit.app`

## Local Testing

Before deploying, test the dashboard locally:

```bash
# Navigate to project root
cd /path/to/mcli

# Ensure .env has Supabase credentials
cat .env | grep SUPABASE

# Launch dashboard
mcli workflow dashboard launch

# Or directly with streamlit
streamlit run src/mcli/ml/dashboard/app_supabase.py
```

## Dashboard Features

The deployed dashboard includes:

- **Overview**: System metrics and key statistics
- **Politicians**: Browse and filter politician data
- **Trading Disclosures**: View trading activity and trends
- **ML Predictions**: ML model predictions (when available)
- **Data Pull Jobs**: Monitor data collection jobs
- **System Health**: Connection status and data freshness

## Troubleshooting

### Connection Errors

If you see "Supabase credentials not found":

1. Verify secrets are configured in Streamlit Cloud
2. Check that secret names match exactly (case-sensitive)
3. Restart the app after updating secrets

### Import Errors

If modules are missing:

1. Check `streamlit_requirements.txt` includes all dependencies
2. Verify Python version matches (3.11 recommended)
3. Check Streamlit Cloud build logs for errors

### Data Not Loading

If tables are empty:

1. Verify Supabase project has data
2. Check API key permissions (should be `anon` or `service_role`)
3. Test connection using the "System Health" page

## Security Notes

- **Never commit** `.streamlit/secrets.toml` to git
- Use `.gitignore` to exclude secrets file
- Rotate API keys if exposed
- Use `SUPABASE_ANON_KEY` for public dashboards
- Use `SUPABASE_SERVICE_ROLE_KEY` only for admin dashboards

## Custom Domain

To use a custom domain:

1. Go to Streamlit Cloud app settings
2. Navigate to "Custom subdomain"
3. Enter desired subdomain: `your-custom-name`
4. URL becomes: `https://your-custom-name.streamlit.app`

## Auto-Updates

The dashboard auto-updates when you push to the main branch:

```bash
git add .
git commit -m "Update dashboard"
git push origin main
```

Streamlit Cloud will automatically rebuild and redeploy.

## Monitoring

Monitor your app:

- **Logs**: Streamlit Cloud dashboard → Logs tab
- **Analytics**: Streamlit Cloud dashboard → Analytics tab
- **Uptime**: Streamlit automatically restarts apps that crash

## Cost

Streamlit Cloud Community (Free):
- 1 app
- Unlimited viewers
- 1 GB RAM
- 1 vCPU
- Community support

For more resources, upgrade to Streamlit Cloud Team or Enterprise.

## Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Supabase Documentation](https://supabase.com/docs)
- [MCLI Dashboard Code](../../src/mcli/ml/dashboard/)
