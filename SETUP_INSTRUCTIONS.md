# Politician Trading Database Setup Instructions

## Step 1: Create Database Schema

1. Open your Supabase SQL editor: https://supabase.com/dashboard/project/uljsqvwkomdrlnofmlad/sql/new
2. Copy and paste the contents of: /Users/lefv/repos/mcli/politician_trading_schema.sql
3. Execute the SQL to create all tables, indexes, and triggers

## Step 2: Verify Setup

Run the following command to verify everything is working:

```bash
politician-trading setup --verify
```

## Step 3: Test Connectivity

```bash
politician-trading connectivity
```

## Step 4: Run First Collection

```bash
politician-trading test-workflow --verbose
```

## Step 5: Setup Automated Collection (Optional)

```bash
politician-trading cron-job --create
```

## Database Tables Created

- **politicians**: Stores politician information (US Congress, EU Parliament)
- **trading_disclosures**: Individual trading transactions/disclosures  
- **data_pull_jobs**: Job execution tracking and status
- **data_sources**: Data source configuration and health

## Troubleshooting

If you encounter issues:

1. Check connectivity: `politician-trading connectivity --json`
2. View logs: `politician-trading health`
3. Test workflow: `politician-trading test-workflow --verbose`
