-- Create cron job for politician trading data collection
-- This runs every 6 hours to collect fresh data from all sources

-- Enable pg_cron extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule the politician trading collection job
SELECT cron.schedule(
    'politician-trading-collection',
    '0 */6 * * *',  -- Every 6 hours at minute 0
    $$
    SELECT net.http_post(
        url := current_setting('SUPABASE_URL') || '/functions/v1/politician-trading-collect',
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'Authorization', 'Bearer ' || current_setting('SUPABASE_SERVICE_ROLE_KEY')
        ),
        body := '{}'::jsonb
    ) as request_id;
    $$
);

-- View scheduled cron jobs
SELECT 
    jobid,
    schedule, 
    command,
    nodename,
    nodeport,
    database,
    username,
    active,
    jobname
FROM cron.job 
WHERE jobname = 'politician-trading-collection';

-- View cron job run history (last 10 runs)
SELECT 
    runid,
    jobid,
    database,
    username,
    command,
    status,
    return_message,
    start_time,
    end_time
FROM cron.job_run_details 
WHERE jobid IN (
    SELECT jobid FROM cron.job WHERE jobname = 'politician-trading-collection'
)
ORDER BY start_time DESC 
LIMIT 10;

-- To unschedule the job (if needed):
-- SELECT cron.unschedule('politician-trading-collection');

-- Manual test of the HTTP call using environment variables
-- SELECT net.http_post(
--     url := current_setting('SUPABASE_URL') || '/functions/v1/politician-trading-collect',
--     headers := jsonb_build_object(
--         'Content-Type', 'application/json',
--         'Authorization', 'Bearer ' || current_setting('SUPABASE_SERVICE_ROLE_KEY')
--     ),
--     body := '{}'::jsonb
-- ) as test_response;