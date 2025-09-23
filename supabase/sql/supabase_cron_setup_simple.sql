-- Simple cron job setup for Supabase Dashboard SQL Editor
-- Run this in: https://app.supabase.com/project/uljsqvwkomdrlnofmlad → SQL Editor

-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Create the cron job (every 6 hours)
SELECT cron.schedule(
    'politician-trading-collection',
    '0 */6 * * *',
    $$
    SELECT net.http_post(
        url := current_setting('SUPABASE_URL') || '/functions/v1/politician-trading-collect',
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'Authorization', 'Bearer ' || current_setting('SUPABASE_ANON_KEY')
        ),
        body := '{}'::jsonb
    ) as request_id;
    $$
);

-- Verify the cron job was created
SELECT 
    jobname,
    schedule, 
    active,
    database
FROM cron.job 
WHERE jobname = 'politician-trading-collection';

-- Check if the job will run (shows next run time)
SELECT 
    jobname,
    schedule,
    active,
    database,
    nodename
FROM cron.job;