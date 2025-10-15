# Trading Schema Setup for Supabase

## Problem
The trading dashboard is showing the error:
```
relation "portfolios" does not exist
```

This is because the trading-related database tables haven't been created in Supabase yet.

## Solution

You need to execute the trading schema migration in your Supabase database.

### Step 1: Access Supabase SQL Editor

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project: `uljsqvwkomdrlnofmlad`
3. Click on **SQL Editor** in the left sidebar

### Step 2: Run the Migration

1. Click **New Query** to create a new SQL query
2. Copy the **entire contents** of the migration file:
   ```
   /Users/lefv/repos/mcli/supabase/migrations/20251010_trading_tables_schema.sql
   ```
3. Paste it into the SQL editor
4. Click **Run** (or press Cmd+Enter)

### Step 3: Verify Tables Were Created

After running the migration, verify the tables exist:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'trading_accounts',
    'portfolios',
    'positions',
    'trading_orders',
    'portfolio_performance_snapshots',
    'trading_signals'
);
```

You should see all 6 tables listed.

## What This Migration Creates

### Tables:
1. **trading_accounts** - User trading accounts with Alpaca integration
2. **portfolios** - Individual portfolios for tracking performance
3. **positions** - Stock positions within portfolios
4. **trading_orders** - Trading orders (buy/sell)
5. **portfolio_performance_snapshots** - Daily performance tracking
6. **trading_signals** - ML-generated trading signals

### Features:
- ✅ Proper foreign key relationships
- ✅ Indexes for performance
- ✅ Triggers for automatic `updated_at` timestamps
- ✅ Row Level Security (RLS) enabled with permissive policies for testing
- ✅ Support for both paper trading and live trading
- ✅ Integration with Alpaca Trading API

## After Setup

Once the migration completes successfully:

1. The trading dashboard should load without errors
2. You can create portfolios from the UI
3. You can place test/paper trades
4. Performance tracking will work

## Testing the Setup

After applying the migration, test that it works:

1. Go to: https://politician-trading-tracker.streamlit.app/trading
2. Navigate to "Portfolios" tab
3. Try creating a test portfolio
4. Verify it appears in the list

## Security Note

⚠️ **Current Configuration**: The RLS policies are set to allow anonymous access for **testing purposes**.

For production, you should:
1. Implement proper authentication
2. Update RLS policies to restrict access by user_id
3. Encrypt Alpaca API credentials

## Files Modified/Created

- ✅ `/Users/lefv/repos/mcli/supabase/migrations/20251010_trading_tables_schema.sql` - Main migration file
- ✅ `/Users/lefv/repos/mcli/TRADING_SCHEMA_SETUP.md` - This documentation

## Quick Copy-Paste Command

To copy the migration file contents to clipboard (macOS):

```bash
cat /Users/lefv/repos/mcli/supabase/migrations/20251010_trading_tables_schema.sql | pbcopy
```

Then just paste into Supabase SQL Editor and run!
