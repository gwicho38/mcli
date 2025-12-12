# MCLI Secrets Management Guide

## Overview

MCLI uses the **LSH Secrets Manager** to securely store and sync environment variables across machines. All secrets are encrypted and stored in Supabase, eliminating the need to manually copy `.env` files or commit them to git.

## 🔐 Available Environments

| Environment | Description | Variables |
|-------------|-------------|-----------|
| `mcli-prod` | Production environment variables | 25 vars |
| `mcli-streamlit-prod` | Streamlit dashboard secrets | 14 vars |
| `mcli-dev` | Development environment (optional) | - |

## 🚀 Quick Start

### New Machine Setup (One-Time)

```bash
# 1. Install LSH (if not already installed)
npm install -g gwicho38-lsh

# 2. Create LSH config directory
mkdir -p ~/.lsh-config

# 3. Add LSH credentials
cat > ~/.lsh-config/.env <<EOF
SUPABASE_URL=https://uljsqvwkomdrlnofmlad.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI
LSH_SECRETS_KEY=fdc6fca3488483b15315e9512083c26de2e973671f3211cb6015bb86ba09fe02
EOF

# 4. Set proper permissions
chmod 600 ~/.lsh-config/.env
```

### Pull Secrets for MCLI

```bash
# Navigate to MCLI project
cd ~/repos/mcli

# Pull main environment variables
/home/lefvpc/repos/lsh/lsh secrets pull --env mcli-prod

# Pull Streamlit dashboard secrets
/home/lefvpc/repos/lsh/lsh secrets pull --file .streamlit/secrets.toml --env mcli-streamlit-prod
```

## 📋 Common Operations

### List All Environments

```bash
/home/lefvpc/repos/lsh/lsh secrets list
```

### View Secrets (Masked)

```bash
# View production secrets
/home/lefvpc/repos/lsh/lsh secrets show --env mcli-prod

# View Streamlit secrets
/home/lefvpc/repos/lsh/lsh secrets show --env mcli-streamlit-prod
```

### Push Updated Secrets

After modifying local `.env` files:

```bash
# Push main .env
/home/lefvpc/repos/lsh/lsh secrets push --env mcli-prod

# Push Streamlit secrets
/home/lefvpc/repos/lsh/lsh secrets push --file .streamlit/secrets.toml --env mcli-streamlit-prod
```

## 🔑 Environment Variables Reference

### Core Configuration (`mcli-prod`)

```bash
# Application Environment
ENVIRONMENT=production
MCLI_ENV=production
DEBUG=false

# Supabase Database
SUPABASE_URL=https://uljsqvwkomdrlnofmlad.supabase.co
SUPABASE_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
DATABASE_URL=postgresql://...

# LSH Daemon
LSH_API_URL=https://mcli-lsh-daemon.fly.dev
LSH_API_KEY=<api-key>

# Trading APIs
ALPACA_API_KEY=<paper-trading-key>
ALPACA_SECRET_KEY=<paper-trading-secret>
ALPACA_BASE_URL=https://paper-api.alpaca.markets
UK_COMPANIES_HOUSE_API_KEY=<api-key>

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=politician_trading

# API Server
API_HOST=0.0.0.0
API_PORT=8001
API_SECRET_KEY=<generate-secure-key>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Streamlit Secrets (`mcli-streamlit-prod`)

```toml
# UK Companies House API
UK_COMPANIES_HOUSE_API_KEY = "..."

# Alpaca Trading API
ALPACA_API_KEY = "..."
ALPACA_SECRET_KEY = "..."
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

# Supabase
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
SUPABASE_SERVICE_ROLE_KEY = "..."

# LSH Daemon
LSH_API_URL = "..."
LSH_API_KEY = "..."

# MLflow
MLFLOW_TRACKING_URI = "..."
MLFLOW_EXPERIMENT_NAME = "politician_trading"

# Environment
ENVIRONMENT = "production"
DEBUG = "false"

# Database
DATABASE_URL = "postgresql://..."
```

## 🛡️ Security Best Practices

### ✅ DO

- **Always use LSH secrets manager** for storing credentials
- **Keep LSH credentials in `~/.lsh-config/.env`** with `chmod 600`
- **Add all `.env` files to `.gitignore`**
- **Rotate credentials regularly** (quarterly recommended)
- **Use separate environments** for dev/staging/prod
- **Enable 2FA on Supabase** (recommended)

### ❌ DON'T

- **Never commit `.env` files** to git
- **Never share credentials** via chat/email/Slack
- **Never hardcode secrets** in code
- **Never use production credentials** in development
- **Never push to git without checking** for secrets first

## 🧹 Git History Cleanup (If Secrets Were Committed)

If secrets were accidentally committed to git, follow these steps:

### 1. Push Secrets to LSH Manager First

```bash
cd ~/repos/mcli

# Save secrets before cleanup
/home/lefvpc/repos/lsh/lsh secrets push --env mcli-prod
/home/lefvpc/repos/lsh/lsh secrets push --file .streamlit/secrets.toml --env mcli-streamlit-prod
```

### 2. Add to .gitignore

```bash
# Add secrets files to .gitignore
cat >> .gitignore <<EOF
# Environment files - NEVER commit
.env
.env.local
.env.*.local
.env.production
.env.backup
.streamlit/secrets.toml
EOF
```

### 3. Remove from Git Tracking

```bash
# Remove from staging (keeps local file)
git rm --cached .env
git rm --cached .streamlit/secrets.toml
```

### 4. Clean Git History with BFG

```bash
# Create backup first
cd /path/to/parent/directory
tar -czf mcli-backup-$(date +%Y%m%d).tar.gz mcli/.git

# Use BFG Repo Cleaner to purge from history
cd ~/repos/mcli
java -jar ~/repos/lsh/bfg-1.14.0.jar --delete-files secrets.toml .

# Clean up git references
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### 5. Commit and Force Push

```bash
# Commit the .gitignore changes
git add .gitignore
git commit -m "security: Remove secrets from version control and git history"

# Force push cleaned history
git push --force origin main
```

### 6. Rotate All Credentials

After cleaning git history, rotate these credentials:

- Supabase service role key
- API keys (Alpaca, Companies House, etc.)
- LSH API key
- API secret keys
- Database passwords

## 🔄 Credential Rotation Checklist

When rotating credentials:

1. **Generate new credentials** in respective services
2. **Update local `.env` files** with new values
3. **Push to LSH secrets manager**
   ```bash
   /home/lefvpc/repos/lsh/lsh secrets push --env mcli-prod
   ```
4. **Update on all machines**
   ```bash
   /home/lefvpc/repos/lsh/lsh secrets pull --env mcli-prod
   ```
5. **Update in production deployments** (Fly.io, Streamlit Cloud, etc.)
6. **Revoke old credentials** in respective services
7. **Test all services** to ensure everything works

## 📤 Deployment Workflows

### Local Development

```bash
# Pull latest secrets
/home/lefvpc/repos/lsh/lsh secrets pull --env mcli-prod

# Start development
python -m mcli.app.streamlit_app
```

### Streamlit Cloud Deployment

Streamlit Cloud uses the secrets UI, not `.env` files:

1. Go to Streamlit Cloud → App Settings → Secrets
2. Copy contents from:
   ```bash
   /home/lefvpc/repos/lsh/lsh secrets show --env mcli-streamlit-prod
   ```
3. Paste into Streamlit Secrets UI (unmasked values)
4. Save and redeploy

### Fly.io Deployment (LSH Daemon)

```bash
# Set secrets on Fly.io
fly secrets set LSH_API_KEY=xxx -a mcli-lsh-daemon
fly secrets set SUPABASE_URL=xxx -a mcli-lsh-daemon
fly secrets set SUPABASE_SERVICE_ROLE_KEY=xxx -a mcli-lsh-daemon
```

## 🚨 Troubleshooting

### "No secrets found for environment"

```bash
# Check available environments
/home/lefvpc/repos/lsh/lsh secrets list

# Push if missing
/home/lefvpc/repos/lsh/lsh secrets push --env mcli-prod
```

### "Decryption failed"

Wrong encryption key! Verify `LSH_SECRETS_KEY` matches:

```bash
cat ~/.lsh-config/.env | grep LSH_SECRETS_KEY
```

### "File not found" when pulling

Use absolute path:

```bash
/home/lefvpc/repos/lsh/lsh secrets pull --file /absolute/path/.env --env mcli-prod
```

### Secrets out of sync between machines

```bash
# On source machine (with latest secrets)
/home/lefvpc/repos/lsh/lsh secrets push --env mcli-prod

# On target machine
/home/lefvpc/repos/lsh/lsh secrets pull --env mcli-prod
```

## 📚 Additional Resources

- **LSH Secrets Quick Reference**: `~/repos/lsh/SECRETS_QUICK_REFERENCE.md`
- **LSH Secrets Guide**: `~/repos/lsh/SECRETS_GUIDE.md`
- **LSH Secrets Cheatsheet**: `~/repos/lsh/SECRETS_CHEATSHEET.txt`
- **Supabase Dashboard**: https://supabase.com/dashboard
- **LSH Daemon (Fly.io)**: https://mcli-lsh-daemon.fly.dev

## 🎯 Summary

**Key Commands:**

```bash
# Pull secrets (daily use)
/home/lefvpc/repos/lsh/lsh secrets pull --env mcli-prod

# Push secrets (after updates)
/home/lefvpc/repos/lsh/lsh secrets push --env mcli-prod

# List environments
/home/lefvpc/repos/lsh/lsh secrets list

# View secrets (masked)
/home/lefvpc/repos/lsh/lsh secrets show --env mcli-prod
```

**Remember:**
- ✅ Never commit `.env` files
- ✅ Always use LSH secrets manager
- ✅ Keep credentials secure
- ✅ Rotate regularly
- ✅ Use separate dev/prod environments

---

**Last Updated:** October 2025
**Secrets Secured:** ✓ mcli-prod (25 vars) | ✓ mcli-streamlit-prod (14 vars)
