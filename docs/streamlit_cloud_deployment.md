# Streamlit Cloud Deployment Guide

## Overview

This guide explains how to deploy the MCLI ML Dashboard to Streamlit Cloud and ensure it's properly connected to Supabase with the politician trading data.

## Prerequisites

- Streamlit Cloud account (free at https://share.streamlit.io)
- Supabase project credentials
- GitHub repository access

## Step 1: Configure Streamlit Cloud Secrets

The dashboard requires Supabase credentials to access the seeded politician trading data.

### 1.1 Access Streamlit Cloud Settings

1. Go to https://share.streamlit.io
2. Find your app (`web-mcli`) or create a new one
3. Click on the app name
4. Click **"Settings"** (⚙️ icon in top right)
5. Click **"Secrets"** in the left sidebar

### 1.2 Add Supabase Credentials

Copy and paste the following into the Secrets editor:

```toml
# Supabase Configuration
SUPABASE_URL = "https://uljsqvwkomdrlnofmlad.supabase.co"
SUPABASE_KEY = "your_anon_key_here"

# LSH Daemon (Production)
LSH_API_URL = "https://mcli-lsh-daemon.fly.dev"
```

**Note:** The above uses the anon key which is safe for public access. For admin operations, use `SUPABASE_SERVICE_ROLE_KEY` instead.

### 1.3 Save and Restart

1. Click **"Save"**
2. The app will automatically restart and load the new secrets

## Step 2: Verify Connection

After saving the secrets, the dashboard should automatically connect to Supabase.

### 2.1 Expected Behavior

✅ **Success Indicators:**
- Dashboard loads without "Using demo trading data" message
- Pipeline Overview shows real politician data (89 politicians, 7,633 disclosures)
- Charts display actual trading data from Supabase
- "Model Training & Evaluation" page can access real data

❌ **Failure Indicators:**
- Blue info box: "🔵 Using demo trading data (Supabase unavailable)"
- Red error box: "❌ Supabase credentials not configured"
- Empty charts or demo data (Nancy Pelosi, Paul Pelosi, etc.)

### 2.2 Troubleshooting Connection Issues

If you see "Using demo trading data":

1. **Check Secrets Configuration:**
   - Go to Settings → Secrets
   - Verify `SUPABASE_URL` and `SUPABASE_KEY` are set
   - Ensure there are no extra spaces or quotes
   - Click "Save" again to force restart

2. **Check App Logs:**
   - Click "Manage app" → "Logs"
   - Look for connection errors
   - Check for "✅ Supabase connection successful" message

3. **Verify Credentials:**
   - Test credentials locally using the verification script (see below)
   - Ensure the anon key has correct permissions in Supabase

## Step 3: Verify Training Pipeline

Once connected, verify that training jobs can access the seeded data:

### 3.1 Access Model Training Page

1. Open the deployed dashboard at https://web-mcli.streamlit.app
2. In the sidebar, select **"Model Training & Evaluation"**
3. You should see:
   - Training configuration options
   - Data source showing "Supabase" (not "Demo Data")
   - Real politician trading data statistics

### 3.2 Initiate a Training Job

1. Configure training parameters:
   - Model type: Neural Network
   - Epochs: 10 (for testing)
   - Batch size: 32
   - Learning rate: 0.001

2. Click **"🚀 Start Training"**

3. Monitor progress:
   - Progress bar should show training progress
   - Real-time logs display training metrics
   - Training curves update each epoch

### 3.3 Run ML Pipeline

Alternatively, use the sidebar button:

1. Click **"🚀 Run ML Pipeline"** in the sidebar
2. This will:
   - Fetch disclosures from Supabase (7,633 records)
   - Preprocess the data
   - Extract features
   - Generate predictions

3. Check for success message: "✅ Pipeline completed!"

## Step 4: Verify Data Access

### 4.1 Check Pipeline Overview

1. Navigate to **"Pipeline Overview"** page
2. Verify the data statistics:
   - **Politicians:** 89
   - **Disclosures:** 7,633
   - **Data Source:** Supabase (not Demo)
   - **Latest Disclosure:** Should show recent Senate trading data

### 4.2 Check ML Processing

1. Navigate to **"ML Processing"** page
2. Verify:
   - Raw data shows actual Senate Stock Watcher transactions
   - Preprocessed data includes politician names from database
   - Features are generated from real trading data
   - Predictions are based on actual historical patterns

## Step 5: Maintenance

### 5.1 Update Secrets

To update secrets without downtime:

1. Go to Settings → Secrets
2. Modify the values
3. Click "Save"
4. App will restart automatically

### 5.2 Monitor Performance

- Check app logs regularly for errors
- Monitor Supabase usage in Supabase dashboard
- Review training job success rates
- Check data freshness (last disclosure date)

## Verification Script

Use this script to test the connection locally before deploying:

```bash
# Run the verification script
.venv/bin/python scripts/verify_streamlit_deployment.py
```

This will test:
- Supabase connection
- Data access (politicians, disclosures)
- Dashboard imports
- Training pipeline availability

## Common Issues

### Issue: "Using demo trading data"

**Cause:** Streamlit Cloud cannot access Supabase credentials

**Fix:**
1. Check Settings → Secrets
2. Verify SUPABASE_URL and SUPABASE_KEY are set
3. Remove any extra quotes or whitespace
4. Save and wait for restart

### Issue: "Supabase connection failed"

**Cause:** Invalid credentials or network issue

**Fix:**
1. Verify credentials in Supabase dashboard
2. Check anon key has correct permissions
3. Ensure Supabase project is active (not paused)
4. Try using SUPABASE_SERVICE_ROLE_KEY for admin access

### Issue: "No data available"

**Cause:** Database is empty or seeding failed

**Fix:**
1. Run seeding script: `python -m mcli.workflow.politician_trading.seed_database --sources all`
2. Verify data in Supabase: `SELECT COUNT(*) FROM trading_disclosures;`
3. Check job status in `data_pull_jobs` table

## Security Notes

- Never commit `.streamlit/secrets.toml` to version control (already in `.gitignore`)
- Use anon key for public Streamlit Cloud deployments
- Use service role key only for admin operations or private deployments
- Rotate keys if compromised
- Review Supabase RLS (Row Level Security) policies

## Next Steps

After successful deployment:

1. **Schedule Data Updates:**
   - Set up automated data pulls (daily/weekly)
   - Configure LSH daemon jobs for continuous ingestion

2. **Train Production Models:**
   - Use "Model Training & Evaluation" page
   - Train on full 7,633 disclosure dataset
   - Evaluate model performance metrics

3. **Monitor & Iterate:**
   - Review prediction accuracy
   - Analyze model performance over time
   - Retrain models as new data arrives

## Support

For issues or questions:
- Check app logs in Streamlit Cloud
- Review Supabase dashboard for data issues
- Consult main documentation in `/docs`
- Check GitHub issues for known problems
