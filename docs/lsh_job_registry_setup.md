# LSH Job Registry Setup Guide

## Overview
This guide covers setting up the LSH job registry with Supabase persistent storage for issue #70.

## Progress Status

### ✅ Completed
1. **Database Schema Design**
   - Created `lsh_jobs` table schema
   - Created `lsh_job_executions` table schema
   - Added indexes for performance
   - Created views for statistics (`lsh_job_stats`, `lsh_recent_executions`)
   - Added Row Level Security policies

2. **Migration Files Created**
   - `supabase/migrations/20251006_lsh_jobs_schema.sql` - Main schema
   - `supabase/sql/lsh_seed_data.sql` - Sample data for testing

3. **Scripts Created**
   - `scripts/run_migration.py` - Migration runner
   - `scripts/verify_lsh_tables.py` - Table verification

### ⚠️ Pending Manual Step

**The migration needs to be run manually in the Supabase SQL Editor:**

1. Go to Supabase Dashboard: https://app.supabase.com/project/uljsqvwkomdrlnofmlad
2. Navigate to SQL Editor
3. Copy and paste the contents of `supabase/migrations/20251006_lsh_jobs_schema.sql`
4. Execute the SQL
5. Copy and paste the contents of `supabase/sql/lsh_seed_data.sql`
6. Execute the SQL
7. Verify tables were created using the verification script:
   ```bash
   SUPABASE_URL="https://uljsqvwkomdrlnofmlad.supabase.co" \
   SUPABASE_SERVICE_ROLE_KEY="..." \
   .venv/bin/python scripts/verify_lsh_tables.py
   ```

## Database Schema

### lsh_jobs Table
```sql
- id (UUID, primary key)
- job_name (TEXT, unique)
- command (TEXT)
- description (TEXT)
- type (TEXT: shell, system, scheduled, service, ml, data-pipeline)
- status (TEXT: active, paused, disabled, archived)
- cron_expression (TEXT, nullable)
- interval_seconds (INTEGER, nullable)
- environment (JSONB)
- tags (TEXT[])
- created_at, updated_at (TIMESTAMPTZ)
```

### lsh_job_executions Table
```sql
- id (UUID, primary key)
- job_id (UUID, foreign key)
- execution_id (TEXT)
- status (TEXT: queued, running, completed, failed, killed, timeout)
- started_at, completed_at (TIMESTAMPTZ)
- duration_ms (INTEGER, auto-calculated)
- stdout, stderr (TEXT)
- max_memory_mb, avg_cpu_percent (REAL)
- error_message, stack_trace (TEXT)
- created_at, updated_at (TIMESTAMPTZ)
```

## Next Steps

### 1. Verify Migration (Manual)
Run the SQL files in Supabase dashboard as described above.

### 2. Update LSH Simple API Server
Update `/Users/lefv/repos/lsh/src/simple-api-server.ts` to fetch real job data from Supabase instead of returning sample data.

### 3. Update MCLI Dashboard
The dashboard at `src/mcli/ml/dashboard/app_integrated.py` already fetches from the API, so it will automatically show real data once the API is updated.

### 4. Update Integration Tests
Update `tests/integration/test_e2e_dashboard_lsh_supabase.py` to verify real job data.

## Testing

### Verify Tables
```bash
.venv/bin/python scripts/verify_lsh_tables.py
```

### Query Sample Data
```python
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Get all jobs
jobs = supabase.table("lsh_jobs").select("*").execute()
print(f"Found {len(jobs.data)} jobs")

# Get job statistics
stats = supabase.table("lsh_job_stats").select("*").execute()
for stat in stats.data:
    print(f"{stat['job_name']}: {stat['total_executions']} executions, {stat['success_rate_percent']}% success")
```

## Files Created

- ✅ `supabase/migrations/20251006_lsh_jobs_schema.sql`
- ✅ `supabase/sql/lsh_seed_data.sql`
- ✅ `scripts/run_migration.py`
- ✅ `scripts/verify_lsh_tables.py`
- ✅ `docs/lsh_job_registry_setup.md` (this file)

## Related GitHub Issue

Issue #70: Setup LSH Daemon Job Registry with Persistent Storage
https://github.com/gwicho38/mcli/issues/70
