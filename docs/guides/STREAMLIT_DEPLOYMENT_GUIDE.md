# Streamlit Cloud Deployment Guide

## Quick Start: Fix IPv6 Connection Issues

### Problem
Trading dashboard and ML features fail to load on Streamlit Cloud with error:
```
connection to server at "db.*.supabase.co" failed: Cannot assign requested address
```

### Solution
Update Streamlit Cloud secrets to use EU region connection pooler.

---

## Step-by-Step Deployment

### 1. Update Streamlit Cloud Secrets

Go to your Streamlit Cloud app settings: https://politician-trading-tracker.streamlit.app/

**Settings → Secrets** and add:

```toml
# Database Connection - EU Region Pooler (IPv4)
# IMPORTANT: Replace YOUR_PROJECT_REF and YOUR_PASSWORD with actual values from Supabase Dashboard
DATABASE_URL = "postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"

# Supabase Configuration
# Get these from Supabase Dashboard → Settings → API
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_KEY = "your_anon_key_here"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key_here"

# LSH Daemon Configuration (if using)
LSH_API_URL = "your_lsh_api_url_here"
LSH_API_KEY = "your_lsh_api_key_here"

# Redis (if needed)
REDIS_HOST = "localhost"
REDIS_PORT = "6379"
REDIS_DB = "0"

# MLflow (if needed)
MLFLOW_TRACKING_URI = "http://localhost:5000"
MLFLOW_EXPERIMENT_NAME = "politician_trading"

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = "8000"
API_SECRET_KEY = "your-secret-key-change-this-in-production"

# UK Companies House API
UK_COMPANIES_HOUSE_API_KEY = "18c9e5c4-556f-40cf-943b-7057f31f8128"

# Alpaca Trading API (Paper Trading)
ALPACA_API_KEY = "PKA8W60S0UVTDHBHEPTA"
ALPACA_SECRET_KEY = "NoD8YBcuhGHWZ8QAwDvUL1QzcjrU7eDUXwrBgHJF"
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

# Environment
ENVIRONMENT = "production"
DEBUG = "false"
```

### 2. Save and Restart

1. Click **Save** in Streamlit Cloud secrets editor
2. Streamlit Cloud will automatically restart your app
3. Wait 1-2 minutes for deployment to complete

### 3. Verify Deployment

Visit your app: https://politician-trading-tracker.streamlit.app/

**Check for:**
- ✅ Trading dashboard loads without errors
- ✅ Portfolio data displays correctly
- ✅ No "Cannot assign requested address" errors in logs

**In the app logs, you should see:**
```
🔗 Using Supabase connection pooler
```
or
```
🔗 Database URL: postgresql://postgres.YOUR_PROJECT_REF:***@aws-1-eu-north-1.pooler.supabase.com:5432/postgres
```

---

## Technical Details

### Why EU Pooler?

**Testing Results:**
- ✅ EU Session pooler (port 5432): **WORKING**
- ✅ EU Transaction pooler (port 6543): **WORKING**
- ❌ US East pooler (port 5432): Connection timeout
- ❌ US West pooler (port 6543): Tenant not found
- ❌ Direct connection (db.*.supabase.co): IPv6 failure

### Connection String Format

```
postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:PORT/postgres
```

**Components:**
- `postgres.PROJECT_REF`: Username format for pooler
- `PASSWORD`: URL-encoded database password (`%23` = `#`)
- `POOLER_HOST`: `aws-1-eu-north-1.pooler.supabase.com`
- `PORT`: 5432 (session mode) or 6543 (transaction mode)

### Pooler Modes

| Mode | Port | Use Case | Connection Behavior |
|------|------|----------|-------------------|
| **Session** | 5432 | Long-running queries | Connection stays open |
| **Transaction** | 6543 | Serverless/short queries | Connection released after tx |

**Current configuration uses Session mode (5432)** for Streamlit Cloud's persistent connections.

---

## Troubleshooting

### Issue: Still getting IPv6 errors

**Check:**
1. Verify `DATABASE_URL` is set in Streamlit Cloud secrets
2. Ensure URL uses `aws-1-eu-north-1.pooler.supabase.com` (not `db.*.supabase.co`)
3. Check password is URL-encoded (`%23` for `#`)

**Fix:**
- Update secrets as shown above
- Click Save and wait for restart

### Issue: Authentication failed

**Check:**
1. Password in `DATABASE_URL` is correct (get from Supabase Dashboard → Settings → Database)
2. Service role key is set (get from Supabase Dashboard → Settings → API)
3. Project reference matches your Supabase project

**Find credentials:**
- Supabase Dashboard → Settings → Database → Connection String
- Password is shown in the connection string

### Issue: Connection timeout

**Possible causes:**
1. Using US pooler instead of EU
2. Network connectivity issues
3. Supabase project not accessible

**Fix:**
- Ensure using EU pooler: `aws-1-eu-north-1.pooler.supabase.com`
- Check Supabase project status
- Verify firewall/network settings

### Issue: Placeholder password warning

**If you see:**
```
Using Supabase connection pooler with service role key.
For better performance, set DATABASE_URL with your actual database password.
```

**This is informational only.** Connection will work, but setting the actual database password (as shown above) provides better performance.

---

## Environment Variables Reference

### Required for Database Connection

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | Primary database connection | `postgresql://postgres.YOUR_PROJECT_REF:...` |
| `SUPABASE_URL` | Supabase project URL | `https://uljsqvwkomdrlnofmlad.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role authentication | `eyJhbGci...` |

### Optional (Fallback)

If `DATABASE_URL` is not set, the system will:
1. Try `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` to construct pooler URL
2. Fall back to SQLite (development only)

---

## Monitoring

### Health Check

After deployment, check app logs for:

**Success indicators:**
```
✅ Basic query successful! Result: 1
✅ Connected to database: postgres
✅ PostgreSQL version: PostgreSQL 17.4
```

**Error indicators:**
```
❌ Connection Error: Cannot assign requested address
❌ IPv6 connectivity problem
```

### Performance Metrics

**Expected performance:**
- Connection time: < 500ms
- Query response: < 100ms
- Pool size: 5 connections
- Pool timeout: 30 seconds

---

## Rollback Plan

If issues occur after deployment:

1. **Immediate:** Revert Streamlit Cloud secrets to previous version
2. **Verify:** Check if old configuration works
3. **Debug:** Review app logs for specific error messages
4. **Contact:** Open GitHub issue with error details

---

## Production Checklist

Before deploying to production:

- [ ] Verify `DATABASE_URL` is set in Streamlit Cloud secrets
- [ ] Confirm password is URL-encoded
- [ ] Check pooler region is EU (`aws-1-eu-north-1`)
- [ ] Test connection with simple query
- [ ] Verify trading dashboard loads
- [ ] Check app logs for connection success message
- [ ] Monitor for 5-10 minutes after deployment
- [ ] Test all key features (portfolio, trading, predictions)

---

## Additional Resources

- [Supabase Connection Pooling Documentation](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)
- [IPv6 Connection Fix Guide](docs/debugging/supabase_connection_fix.md)
- [Release Notes v0.8.4](docs/releases/0.8.4.md)
- [GitHub Repository](https://github.com/gwicho38/mcli)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review [docs/debugging/supabase_connection_fix.md](docs/debugging/supabase_connection_fix.md)
3. Open GitHub issue with error logs and steps to reproduce

---

**Last Updated:** 2025-10-10
**Version:** 0.8.4
**Status:** ✅ Production Ready
