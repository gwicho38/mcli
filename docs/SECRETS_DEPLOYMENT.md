# MCLI Secrets & Deployment Guide

**Generated:** 2025-10-14
**Status:** Production-Ready

## Overview

This guide documents the production environment variables and deployment process for MCLI.

## Files Created

### 1. `.env.production` - Production Environment File
- **Location:** `/Users/lefv/repos/mcli/.env.production`
- **Status:** ✅ All secrets validated
- **Total Variables:** 59
- **Critical Secrets:** 7 (all properly configured)
- **Permissions:** Set to 600 (read/write owner only)

### 2. `scripts/distribute_secrets.py` - Distribution Script
- **Location:** `/Users/lefv/repos/mcli/scripts/distribute_secrets.py`
- **Status:** ✅ Executable
- **Purpose:** Distribute secrets to various deployment targets

### 3. `ENV.md` - Original Documentation
- **Location:** `/Users/lefv/repos/mcli/docs/configuration/ENV.md`
- **Status:** ⚠️ Untracked in git (contains production secrets)
- **Note:** Should be added to .gitignore or removed

## Production Secrets Summary

### 🔒 Critical Secrets (7)

All critical secrets are properly configured with real, non-placeholder values:

1. **SUPABASE_SERVICE_ROLE_KEY** - Admin access to Supabase (219 chars)
2. **DATABASE_URL** - PostgreSQL connection string (125 chars)
3. **LSH_API_KEY** - LSH daemon authentication (48 chars)
4. **ALPACA_SECRET_KEY** - Trading API secret (40 chars)
5. **API_SECRET_KEY** - API JWT signing key (86 chars) - **NEW**
6. **SECURITY_ADMIN_PASSWORD** - Admin password (43 chars) - **NEW**
7. **UK_COMPANIES_HOUSE_API_KEY** - UK corporate data (36 chars)

### 📊 Secrets by Category

- **Database:** 5 variables (Supabase + PostgreSQL)
- **LSH Daemon:** 5 variables (fly.io deployment)
- **Trading APIs:** 4 variables (Alpaca paper trading)
- **API & Auth:** 7 variables (FastAPI security)
- **Machine Learning:** 10 variables (MLflow, PyTorch)
- **Security:** 4 variables (Authentication)
- **Monitoring:** 5 variables (Metrics & logging)

## Deployment Targets

### 1. Verify Secrets

Always verify before deploying:

```bash
python3 scripts/distribute_secrets.py --target verify --env-file .env.production
```

Expected output: `✓ All critical secrets are properly configured!`

### 2. Streamlit Cloud

Generate Streamlit secrets file:

```bash
python3 scripts/distribute_secrets.py --target streamlit --output streamlit_secrets.toml
```

**Deployment steps:**
1. Go to https://share.streamlit.io/
2. Select your app → Settings → Secrets
3. Copy contents of `streamlit_secrets.toml`
4. Paste into secrets editor
5. Save and restart app

### 3. fly.io (LSH Daemon)

Generate fly.io secrets commands:

```bash
python3 scripts/distribute_secrets.py --target flyio --app mcli-lsh-daemon
```

**Deployment steps:**
1. `fly auth login`
2. `./flyio_secrets.sh`
3. `fly secrets list -a mcli-lsh-daemon` (verify)

### 4. Remote VM/Server

Deploy via scp:

```bash
python3 scripts/distribute_secrets.py --target vm --host user@hostname --path /opt/mcli
```

**Manual deployment:**
```bash
scp .env.production user@hostname:/opt/mcli/.env
ssh user@hostname 'chmod 600 /opt/mcli/.env'
```

### 5. Docker

Generate Docker env file:

```bash
python3 scripts/distribute_secrets.py --target docker --output .env.docker
```

**Usage:**
```bash
docker run --env-file .env.docker mcli:latest
```

Or in `docker-compose.yml`:
```yaml
services:
  mcli:
    env_file:
      - .env.docker
```

### 6. Kubernetes

Generate Kubernetes secret:

```bash
python3 scripts/distribute_secrets.py --target k8s --namespace production --secret-name mcli-secrets
```

**Deployment:**
```bash
kubectl apply -f k8s_secret.yaml
```

**Usage in pod:**
```yaml
envFrom:
  - secretRef:
      name: mcli-secrets
```

## Security Best Practices

### ✅ Do's

1. **Keep .env.production secure** - Never commit to git
2. **Use secure channels** - Only transfer via scp/encrypted methods
3. **Rotate keys regularly** - Especially API_SECRET_KEY and passwords
4. **Use different keys per environment** - Dev, staging, production
5. **Monitor access** - Check Supabase/API logs regularly
6. **Backup securely** - Store encrypted backups offline

### ❌ Don'ts

1. **Never commit secrets to git** - Use .gitignore
2. **Don't share via email/Slack** - Use secure secret managers
3. **Don't reuse passwords** - Each environment should be unique
4. **Don't expose service role keys** - Only use server-side
5. **Don't log secrets** - Sanitize logs before sharing

## Generated Credentials

The following were newly generated for production:

```bash
# API JWT Signing Key (512-bit)
API_SECRET_KEY=L-WPqDUhW_yzVQcIswiF8_C479mfSfWTwvNILSc_Ok0fFIbUOfxdhBwYIiHHbkWJxawAglPQ7KjbYnUAWPPDwg

# Admin Password (256-bit)
SECURITY_ADMIN_PASSWORD=5kIBjxQxUKW6axKma2mcksXGNKZ1BfcbWFi-AwsfxnY
```

**Generation method:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"  # API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # Password
```

## Environment Configuration

### Production (.env.production)
- **ENVIRONMENT:** production
- **DEBUG:** false
- **SUPABASE_URL:** https://uljsqvwkomdrlnofmlad.supabase.co (EU North 1)
- **LSH_API_URL:** https://mcli-lsh-daemon.fly.dev
- **ALPACA_BASE_URL:** https://paper-api.alpaca.markets (paper trading)

### Development (.env)
- **ENVIRONMENT:** development
- **DEBUG:** true
- **Uses:** Placeholder values
- **Safe to commit:** Yes (no real secrets)

## Quick Reference

### Check secrets summary
```bash
python3 scripts/distribute_secrets.py --target summary --env-file .env.production
```

### View all available commands
```bash
python3 scripts/distribute_secrets.py --help
```

### Test database connection
```bash
python3 -c "from mcli.db import test_connection; test_connection()"
```

## Deployment Checklist

- [ ] Verify all secrets are valid (`--target verify`)
- [ ] Backup .env.production securely
- [ ] Add ENV.md to .gitignore
- [ ] Deploy to target platform
- [ ] Test connection/authentication
- [ ] Verify logs show no errors
- [ ] Monitor for 24 hours
- [ ] Document any issues

## Support

- **Issues:** https://github.com/lefv/mcli/issues
- **Supabase Dashboard:** https://supabase.com/dashboard/project/uljsqvwkomdrlnofmlad
- **fly.io Dashboard:** https://fly.io/apps/mcli-lsh-daemon

## Version History

- **v1.0.0** (2025-10-14): Initial production secrets configuration
  - Generated secure API_SECRET_KEY and SECURITY_ADMIN_PASSWORD
  - Created .env.production with all real values
  - Built distribution script for multiple deployment targets
  - Verified all 7 critical secrets
