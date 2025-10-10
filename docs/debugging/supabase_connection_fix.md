# Supabase Database Connection Debugging Guide

## Problem: IPv6 Connection Failure

### Error Message
```
psycopg2.OperationalError: connection to server at "db.uljsqvwkomdrlnofmlad.supabase.co" (2a05:d016:571:a402:8455:5460:1249:d73), port 5432 failed: Cannot assign requested address
Is the server running on that host and accepting TCP/IP connections?
```

### Root Causes

1. **IPv6 Connectivity Issues**
   - Streamlit Cloud (and some hosting platforms) have limited or no IPv6 support
   - Direct Supabase database connections (`db.*.supabase.co`) may resolve to IPv6 addresses
   - The error shows an IPv6 address: `2a05:d016:571:a402:8455:5460:1249:d73`

2. **Placeholder Password**
   - DATABASE_URL contains `your_password` instead of actual credentials
   - Code detects this and automatically falls back to connection pooler

## Solution

### Implemented Fixes

1. **Automatic Pooler Detection** (`session.py`)
   - When `your_password` placeholder is detected, code automatically uses Supabase connection pooler
   - Connection pooler uses IPv4-only endpoints
   - Service role key is used for authentication

2. **Multi-Region Pooler Fallback**
   - Tries multiple pooler endpoints for better reliability:
     - `aws-0-us-east-1.pooler.supabase.com:5432` (Session mode)
     - `aws-0-us-west-1.pooler.supabase.com:6543` (Transaction mode)
   - Tests each connection before using it

3. **Enhanced Error Messages**
   - Detects IPv6-related errors
   - Provides actionable guidance to users
   - Suggests using connection pooler instead of direct connection

4. **Connection Pool Configuration**
   - Smaller pool size (5) for Streamlit Cloud
   - Connection timeout: 10 seconds
   - Statement timeout: 30 seconds
   - Pre-ping enabled to verify connections

### Configuration Options

#### Option 1: Use Connection Pooler (Recommended for Streamlit Cloud)

**Important:** Connection pooler requires actual database password, not service role key.

Set in Streamlit Cloud Secrets or `.env`:

```bash
# Use connection pooler URL directly with database password
DATABASE_URL=postgresql://postgres.PROJECT_REF:YOUR_DATABASE_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres

# Where:
# - PROJECT_REF: Your Supabase project reference (e.g., uljsqvwkomdrlnofmlad)
# - YOUR_DATABASE_PASSWORD: Your actual database password from Supabase Dashboard
```

To find your database password:
1. Go to Supabase Dashboard → Settings → Database
2. Look for "Connection string" section
3. Copy the password from the connection string

**Note:** Service role key authentication with pooler is not yet fully supported by this implementation.

#### Option 2: Direct Connection with Real Password

If you have the database password:

```bash
DATABASE_URL=postgresql://postgres:YOUR_ACTUAL_PASSWORD@db.uljsqvwkomdrlnofmlad.supabase.co:5432/postgres
```

**Note:** This may still fail on Streamlit Cloud due to IPv6 issues.

#### Option 3: Use Pooler URL Directly

Manually specify the pooler URL:

```bash
DATABASE_URL=postgresql://postgres.uljsqvwkomdrlnofmlad:YOUR_SERVICE_ROLE_KEY@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### Where to Find Credentials

1. **Service Role Key**:
   - Supabase Dashboard → Settings → API → Service Role Key (secret)

2. **Database Password**:
   - Supabase Dashboard → Settings → Database → Connection String
   - Look for "Connection string" section
   - Password is shown in the connection string

3. **Project Reference**:
   - From your Supabase URL: `https://PROJECT_REF.supabase.co`
   - In the example: `uljsqvwkomdrlnofmlad` is the project reference

## Testing the Fix

### Local Testing

```bash
# Test connection with pooler
python -c "
import os
os.environ['SUPABASE_URL'] = 'https://uljsqvwkomdrlnofmlad.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'your_service_role_key'
from mcli.ml.database.session import engine
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('Connection successful!')
"
```

### Streamlit Cloud Testing

1. Deploy with the fixes
2. Check logs for connection messages:
   - ✅ `Successfully connected via pooler: aws-0-us-east-1.pooler.supabase.com`
   - ⚠️ `Using Supabase connection pooler with service role key`

3. Verify trading dashboard loads without errors

## Connection Pooler Modes

Supabase offers two pooler modes:

### Session Mode (Port 5432)
- Connection remains open between client and database
- Better for: Long-running queries, transactions
- URL: `aws-0-us-east-1.pooler.supabase.com:5432`

### Transaction Mode (Port 6543)
- Connection released after each transaction
- Better for: Serverless, short queries
- URL: `aws-0-us-west-1.pooler.supabase.com:6543`

Our implementation tries Session mode first, then Transaction mode as fallback.

## Troubleshooting

### Still getting IPv6 errors?

1. Verify SUPABASE_SERVICE_ROLE_KEY is set correctly
2. Check Streamlit Cloud logs for connection attempt messages
3. Ensure DATABASE_URL contains `your_password` (or remove DATABASE_URL entirely)

### Connection timeout errors?

1. Try different pooler region (edit `session.py` pooler_urls list)
2. Increase `connect_timeout` in session.py connect_args
3. Check Supabase project status

### Authentication failed?

1. Verify service role key is correct and not expired
2. Check project reference matches your Supabase URL
3. Ensure service role key has necessary permissions

## Additional Resources

- [Supabase Connection Pooling Docs](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)
- [IPv4 vs IPv6 Connectivity](https://www.cloudflare.com/learning/network-layer/what-is-ipv6/)
- [SQLAlchemy Connection Issues](https://docs.sqlalchemy.org/en/20/core/pooling.html)

## Related Files

- `/src/mcli/ml/database/session.py` - Connection management
- `/src/mcli/ml/dashboard/pages/trading.py` - Trading dashboard (uses get_session)
- `/src/mcli/ml/dashboard/pages/test_portfolio.py` - Test portfolio (uses get_session)
- `/.env` - Local environment configuration
- Streamlit Cloud Secrets - Production configuration
