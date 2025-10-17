# Streamlit Cloud Deployment Troubleshooting

## Issue: "Updating the app files has failed: exit status 1"

When Streamlit Cloud shows this error during deployment, it means the git pull operation failed on Streamlit's servers. This typically happens due to:

1. **Detached HEAD state** - Streamlit Cloud's git repo is not on a proper branch
2. **Uncommitted local changes** - Streamlit Cloud has uncommitted files that conflict with new commits
3. **Git repository corruption** - The .git directory on Streamlit's servers is in an inconsistent state

## Solution: Reboot the Streamlit App

### Method 1: Reboot Button (Recommended)

1. Go to **https://share.streamlit.io**
2. Find your app: **politician-trading-tracker**
3. Click the **⋮** menu (three dots) → **Settings**
4. Scroll to bottom → Click **Reboot app**
5. Wait 2-3 minutes for fresh deployment

This forces Streamlit to:
- Stop the running app
- Delete the current workspace (including git repo)
- Fresh clone from GitHub
- Install dependencies
- Restart the app

### Method 2: Change Branch (Alternative)

If reboot doesn't work:

1. Go to **Settings** → **General**
2. Change **Branch** from `main` to a different branch (e.g., `develop`)
3. Save
4. Wait for failed deployment
5. Change back to `main`
6. Save

This forces a fresh git clone.

### Method 3: Redeploy (Last Resort)

1. **Delete** the app from Streamlit Cloud
2. Click **New app**
3. Configure:
   - Repository: `gwicho38/mcli`
   - Branch: `main`
   - Main file: `src/mcli/ml/dashboard/app_supabase.py`
   - Python version: `3.11`
4. Paste secrets (see below)
5. Deploy

## Required Secrets Configuration

After reboot/redeploy, ensure secrets are configured at **Settings** → **Secrets**:

```toml
SUPABASE_URL = "https://uljsqvwkomdrlnofmlad.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjgwMjI0NCwiZXhwIjoyMDcyMzc4MjQ0fQ.4364sQbTJQd4IcxEQG6mPiOUw1iJ2bdKfV6W4oRqHvs"
```

**Important**: Secrets must be added via Streamlit Cloud UI, not committed to git.

## Expected Behavior After Fix

Once secrets are properly configured and app is rebooted, you should see:

### On Dashboard Load:
- ✅ **"Loaded N real trading disclosures from database!"** (green success message)
- No "demo data" messages
- Real politician trading data in tables/charts

### If Secrets Missing:
- ❌ **"DATABASE ERROR: No trading disclosure data available!"** (red error)
- Clear instructions showing required secrets
- UI stops rendering (st.stop())

### If Database Empty:
- ❌ **"INSUFFICIENT DATA: Found only X disclosures. Need at least 10 for ML predictions."** (red error)
- Instruction to run data collection workflows
- UI stops rendering

## Verification Steps

After reboot:

1. Visit: https://politician-trading-tracker.streamlit.app
2. Check for **"🟢 Live Data"** indicator in top-right
3. Navigate to **"🔮 Live Predictions & Recommendations"** tab
4. Should see either:
   - ✅ Success message with real data count, OR
   - ❌ Clear error message explaining configuration issue

## Common Errors and Fixes

### Error: "MediaFileHandler: Missing file"
**Cause**: Cached download files from previous session no longer exist
**Impact**: Harmless warning, doesn't affect functionality
**Fix**: Automatic on next rerun

### Error: "Plotly keyword arguments have been deprecated"
**Cause**: Plotly API changes
**Impact**: Harmless warning, doesn't affect functionality
**Fix**: Update Plotly charts to use `config` parameter (low priority)

### Error: "Session state does not function"
**Cause**: Running Streamlit scripts outside Streamlit runtime
**Impact**: None for deployed app
**Fix**: Already suppressed in code

## Related Files

- Secrets export script: `scripts/streamlit-export-secrets.sh`
- Deployment guide: `docs/setup/STREAMLIT_DEPLOYMENT.md`
- Secrets config: `.streamlit/secrets.toml` (local only, gitignored)
- Dashboard app: `src/mcli/ml/dashboard/app_supabase.py`
- Data utilities: `src/mcli/ml/dashboard/utils.py`
- Predictions page: `src/mcli/ml/dashboard/pages/predictions_enhanced.py`

## Support

If issues persist after reboot:

1. Check Streamlit Cloud logs for specific error messages
2. Verify GitHub repository is accessible at https://github.com/gwicho38/mcli
3. Confirm main branch has latest commits
4. Check Supabase dashboard for database connectivity
5. Test Supabase credentials locally with `scripts/streamlit-export-secrets.sh`

## Last Updated

2025-10-17 - Added explicit error messages for missing Supabase configuration
