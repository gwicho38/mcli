# Complete Deployment Guide: MCLI + LSH Daemon + Streamlit

This guide covers the full deployment of the MCLI ecosystem with LSH daemon on Fly.io and Streamlit dashboard on Streamlit Cloud.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Production Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌───────────────────┐        │
│  │  Streamlit Cloud │◄────────┤   Supabase DB     │        │
│  │  (Dashboard)     │         │  (Politicians &   │        │
│  │                  │         │   Disclosures)    │        │
│  └────────┬─────────┘         └───────────────────┘        │
│           │                                                  │
│           │ HTTPS                                            │
│           ▼                                                  │
│  ┌──────────────────┐                                       │
│  │   Fly.io         │                                       │
│  │  LSH Daemon      │◄─────── Job Scheduler & API          │
│  │  (mcli-lsh-      │         - ML Training Jobs            │
│  │   daemon.fly.dev)│         - Data Pipeline Jobs          │
│  └──────────────────┘         - Monitoring Jobs             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- ✅ Fly.io account (https://fly.io)
- ✅ Streamlit Cloud account (https://share.streamlit.io)
- ✅ GitHub repository with your code
- ✅ Supabase project (for database)

## Part 1: LSH Daemon Deployment (✅ COMPLETED)

The LSH daemon is already deployed and running!

### Current Status
- **URL**: https://mcli-lsh-daemon.fly.dev
- **Status**: ✅ Healthy
- **Version**: 0.5.2
- **Region**: San Jose (sjc)

### Verify LSH Daemon

```bash
# Check health
curl https://mcli-lsh-daemon.fly.dev/health

# Check API status
curl https://mcli-lsh-daemon.fly.dev/api/status

# View jobs
curl https://mcli-lsh-daemon.fly.dev/api/jobs
```

### LSH Daemon Management

```bash
# View logs
fly logs -a mcli-lsh-daemon

# Check status
fly status -a mcli-lsh-daemon

# Scale resources (if needed)
fly scale memory 1024 -a mcli-lsh-daemon

# Redeploy (if code changes)
cd /Users/lefv/repos/lsh
fly deploy -a mcli-lsh-daemon
```

### Environment Secrets (Already Configured)

The LSH daemon has these secrets set:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `LSH_API_KEY`

To update secrets:
```bash
fly secrets set KEY=value -a mcli-lsh-daemon
```

## Part 2: Streamlit Dashboard Deployment

### Step 1: Prepare Repository

The repository is ready with:
- ✅ `.streamlit/config.toml` - Streamlit configuration
- ✅ `.streamlit/secrets.toml` - Secrets template (for reference)
- ✅ Updated deployment docs pointing to production LSH daemon

### Step 2: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit: https://share.streamlit.io
   - Sign in with GitHub

2. **Create New App**
   - Click "New app"
   - Repository: `gwicho38/mcli` (or your fork)
   - Branch: `main`
   - Main file path: `src/mcli/ml/dashboard/app_integrated.py`

3. **Configure Secrets**

   Click "Advanced settings" → "Secrets" and add:

   ```toml
   SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
   SUPABASE_KEY = "your_anon_key_here"
   SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key_here"
   LSH_API_URL = "https://mcli-lsh-daemon.fly.dev"
   ```

4. **Deploy**
   - Click "Deploy!"
   - Wait for build to complete (2-5 minutes)
   - Your app will be at: `https://web-mcli.streamlit.app` (or auto-generated URL)

### Step 3: Verify Deployment

Once deployed, check:

1. **Dashboard loads** - Should show "MCLI ML System Dashboard"
2. **Supabase connection** - "Pipeline Overview" should show data
3. **LSH daemon integration** - "LSH Jobs" page should show jobs
4. **System Health** - All components should be green

### Troubleshooting Streamlit Deployment

**App won't start:**
- Check logs in Streamlit Cloud dashboard
- Verify all secrets are set correctly
- Check Python version compatibility

**No data showing:**
- Verify Supabase credentials in secrets
- Check LSH_API_URL is correct
- Restart app from Streamlit Cloud dashboard

**LSH jobs not showing:**
- Verify LSH_API_URL: `https://mcli-lsh-daemon.fly.dev`
- Check LSH daemon is running: `fly status -a mcli-lsh-daemon`
- Test API manually: `curl https://mcli-lsh-daemon.fly.dev/api/jobs`

## Part 3: Testing End-to-End Integration

### Local Testing (Optional)

Test locally before deploying:

```bash
# Set environment variables
export LSH_API_URL=https://mcli-lsh-daemon.fly.dev
export SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
export SUPABASE_KEY=<your-anon-key>

# Run dashboard locally
cd /Users/lefv/repos/mcli
streamlit run src/mcli/ml/dashboard/app_integrated.py
```

Visit http://localhost:8501 and verify:
- ✅ Dashboard loads
- ✅ Data from Supabase appears
- ✅ LSH jobs are visible
- ✅ No errors in console

### Production Testing

After Streamlit deployment:

1. **Navigate to Dashboard Pages:**
   - Pipeline Overview
   - ML Processing
   - Model Performance
   - Predictions
   - LSH Jobs
   - System Health

2. **Verify LSH Integration:**
   - Go to "LSH Jobs" page
   - Should see jobs from https://mcli-lsh-daemon.fly.dev
   - Check "System Health" → LSH Daemon should be "✅ Running"

3. **Test Predictions:**
   - Go to "Model Training & Evaluation" → "Interactive Predictions"
   - Enter test data
   - Generate prediction
   - Should return results with confidence scores

## Part 4: Updating Deployments

### Update LSH Daemon

```bash
cd /Users/lefv/repos/lsh

# Make changes to code
# ...

# Deploy updates
fly deploy -a mcli-lsh-daemon

# Verify
fly logs -a mcli-lsh-daemon
curl https://mcli-lsh-daemon.fly.dev/health
```

### Update Streamlit Dashboard

Streamlit Cloud auto-deploys on git push:

```bash
cd /Users/lefv/repos/mcli

# Make changes to dashboard
# src/mcli/ml/dashboard/app_integrated.py

# Commit and push
git add .
git commit -m "Update dashboard"
git push origin main

# Streamlit Cloud will auto-deploy in 1-2 minutes
```

To force redeploy:
1. Go to Streamlit Cloud dashboard
2. Click "Reboot app"

## Part 5: Monitoring & Maintenance

### LSH Daemon Monitoring

```bash
# Real-time logs
fly logs -a mcli-lsh-daemon --follow

# Resource usage
fly status -a mcli-lsh-daemon

# Dashboard
fly dashboard -a mcli-lsh-daemon
```

### Streamlit Dashboard Monitoring

1. Go to https://share.streamlit.io
2. Select your app
3. View:
   - Logs
   - Analytics (viewers, usage)
   - Resources (CPU, memory)
   - Errors

### Health Checks

Set up periodic health checks:

```bash
# LSH Daemon
curl https://mcli-lsh-daemon.fly.dev/health

# Streamlit Dashboard
curl https://web-mcli.streamlit.app/_stcore/health
```

## Part 6: Cost Optimization

### Fly.io (LSH Daemon)

Current config (512MB RAM, 1 CPU):
- ~$1.94/month (if running 24/7)
- Free tier available: 3 shared-cpu VMs

To reduce costs:
```toml
# fly.toml
[[vm]]
  memory_mb = 256  # Minimum
  cpus = 1

[http_service]
  auto_stop_machines = true   # Auto-sleep when idle
  min_machines_running = 0
```

### Streamlit Cloud

- Free tier: 1 app, unlimited viewers
- Community plan: Free forever
- No credit card required

## URLs & Resources

### Production URLs
- **LSH Daemon**: https://mcli-lsh-daemon.fly.dev
- **Dashboard**: https://web-mcli.streamlit.app (or your custom URL)
- **Supabase**: https://YOUR_PROJECT_REF.supabase.co

### Dashboards
- **Fly.io**: https://fly.io/dashboard
- **Streamlit Cloud**: https://share.streamlit.io
- **Supabase**: https://supabase.com/dashboard

### API Endpoints
- LSH Health: `https://mcli-lsh-daemon.fly.dev/health`
- LSH Status: `https://mcli-lsh-daemon.fly.dev/api/status`
- LSH Jobs: `https://mcli-lsh-daemon.fly.dev/api/jobs`

## Next Steps

1. ✅ LSH daemon deployed on Fly.io
2. ⏳ Deploy Streamlit dashboard to Streamlit Cloud
3. ⏳ Configure custom domain (optional)
4. ⏳ Set up monitoring alerts
5. ⏳ Enable HTTPS/SSL (automatic on both platforms)

## Support

- **LSH Daemon Issues**: Check `fly logs -a mcli-lsh-daemon`
- **Dashboard Issues**: Check Streamlit Cloud logs
- **Integration Issues**: Verify `LSH_API_URL` in Streamlit secrets
- **Documentation**: See `/docs/streamlit_deployment.md`

---

**Deployment Status**: LSH Daemon ✅ | Streamlit Dashboard ⏳

Last Updated: 2025-10-06
