-- Seed Data for LSH Jobs
-- Description: Sample jobs for testing and demonstration
-- Author: LSH-MCLI Integration
-- Date: 2025-10-06

-- =============================================================================
-- Sample Jobs
-- =============================================================================

-- Job 1: Politician Trading Monitor
INSERT INTO lsh_jobs (
  job_name,
  command,
  description,
  type,
  status,
  cron_expression,
  environment,
  tags,
  priority,
  created_by
) VALUES (
  'politician-trading-monitor',
  'mcli workflow politician-trading collect --region us',
  'Monitor and collect politician trading disclosures from US sources',
  'data-pipeline',
  'active',
  '0 */4 * * *',  -- Every 4 hours
  '{"LOG_LEVEL": "info", "RETRY_COUNT": "3"}'::jsonb,
  ARRAY['trading', 'monitoring', 'data-collection'],
  10,
  'system'
) ON CONFLICT (job_name) DO NOTHING;

-- Job 2: Database Health Monitor
INSERT INTO lsh_jobs (
  job_name,
  command,
  description,
  type,
  status,
  interval_seconds,
  environment,
  tags,
  priority,
  created_by
) VALUES (
  'db-health-monitor',
  'mcli workflow database health-check',
  'Monitor database health and performance metrics',
  'system',
  'active',
  300,  -- Every 5 minutes
  '{"METRICS_ENABLED": "true"}'::jsonb,
  ARRAY['monitoring', 'database', 'health'],
  5,
  'system'
) ON CONFLICT (job_name) DO NOTHING;

-- Job 3: ML Model Training
INSERT INTO lsh_jobs (
  job_name,
  command,
  description,
  type,
  status,
  cron_expression,
  max_memory_mb,
  timeout_seconds,
  environment,
  tags,
  priority,
  created_by
) VALUES (
  'ml-model-training',
  'mcli workflow ml train --model politician-trading',
  'Train ML model for politician trading predictions',
  'ml',
  'active',
  '0 2 * * *',  -- Daily at 2 AM
  4096,
  7200,  -- 2 hours
  '{"EPOCHS": "30", "BATCH_SIZE": "32", "LEARNING_RATE": "0.001"}'::jsonb,
  ARRAY['ml', 'training', 'prediction'],
  20,
  'system'
) ON CONFLICT (job_name) DO NOTHING;

-- Job 4: System Metrics Collector
INSERT INTO lsh_jobs (
  job_name,
  command,
  description,
  type,
  status,
  interval_seconds,
  environment,
  tags,
  priority,
  created_by
) VALUES (
  'system-metrics-collector',
  'mcli workflow system collect-metrics',
  'Collect system performance and resource metrics',
  'system',
  'active',
  60,  -- Every minute
  '{"METRICS_RETENTION_DAYS": "7"}'::jsonb,
  ARRAY['monitoring', 'system', 'metrics'],
  3,
  'system'
) ON CONFLICT (job_name) DO NOTHING;

-- Job 5: Data Pipeline Sync
INSERT INTO lsh_jobs (
  job_name,
  command,
  description,
  type,
  status,
  cron_expression,
  max_retries,
  retry_delay_seconds,
  environment,
  tags,
  priority,
  created_by
) VALUES (
  'data-pipeline-sync',
  'mcli workflow data-pipeline sync --source supabase',
  'Synchronize data pipeline with external sources',
  'data-pipeline',
  'active',
  '*/15 * * * *',  -- Every 15 minutes
  3,
  120,
  '{"SYNC_MODE": "incremental", "BATCH_SIZE": "1000"}'::jsonb,
  ARRAY['data-pipeline', 'sync', 'etl'],
  15,
  'system'
) ON CONFLICT (job_name) DO NOTHING;

-- Job 6: Log Cleanup (Paused example)
INSERT INTO lsh_jobs (
  job_name,
  command,
  description,
  type,
  status,
  cron_expression,
  environment,
  tags,
  priority,
  created_by
) VALUES (
  'log-cleanup',
  'find /tmp/lsh-*.log -mtime +7 -delete',
  'Clean up old log files older than 7 days',
  'system',
  'paused',
  '0 3 * * 0',  -- Weekly on Sunday at 3 AM
  '{}'::jsonb,
  ARRAY['maintenance', 'cleanup'],
  1,
  'system'
) ON CONFLICT (job_name) DO NOTHING;

-- =============================================================================
-- Sample Job Executions
-- =============================================================================

-- Get job IDs for sample executions
DO $$
DECLARE
  job_id_trading UUID;
  job_id_health UUID;
  job_id_ml UUID;
  job_id_metrics UUID;
BEGIN
  -- Get job IDs
  SELECT id INTO job_id_trading FROM lsh_jobs WHERE job_name = 'politician-trading-monitor';
  SELECT id INTO job_id_health FROM lsh_jobs WHERE job_name = 'db-health-monitor';
  SELECT id INTO job_id_ml FROM lsh_jobs WHERE job_name = 'ml-model-training';
  SELECT id INTO job_id_metrics FROM lsh_jobs WHERE job_name = 'system-metrics-collector';

  -- Trading monitor - successful execution
  INSERT INTO lsh_job_executions (
    job_id,
    execution_id,
    status,
    started_at,
    completed_at,
    exit_code,
    stdout,
    stderr,
    max_memory_mb,
    avg_cpu_percent,
    tags,
    triggered_by
  ) VALUES (
    job_id_trading,
    'exec-' || gen_random_uuid()::text,
    'completed',
    NOW() - INTERVAL '1 hour',
    NOW() - INTERVAL '55 minutes',
    0,
    'Successfully collected 142 trading disclosures',
    '',
    256.5,
    15.3,
    ARRAY['trading', 'success'],
    'scheduler'
  ) ON CONFLICT DO NOTHING;

  -- Health monitor - recent successful
  INSERT INTO lsh_job_executions (
    job_id,
    execution_id,
    status,
    started_at,
    completed_at,
    exit_code,
    stdout,
    max_memory_mb,
    avg_cpu_percent,
    tags,
    triggered_by
  ) VALUES (
    job_id_health,
    'exec-' || gen_random_uuid()::text,
    'completed',
    NOW() - INTERVAL '5 minutes',
    NOW() - INTERVAL '4 minutes',
    0,
    'All health checks passed',
    128.2,
    8.1,
    ARRAY['health', 'success'],
    'scheduler'
  ) ON CONFLICT DO NOTHING;

  -- ML training - long running completed
  INSERT INTO lsh_job_executions (
    job_id,
    execution_id,
    status,
    started_at,
    completed_at,
    exit_code,
    stdout,
    max_memory_mb,
    avg_cpu_percent,
    tags,
    triggered_by
  ) VALUES (
    job_id_ml,
    'exec-' || gen_random_uuid()::text,
    'completed',
    NOW() - INTERVAL '12 hours',
    NOW() - INTERVAL '10 hours 15 minutes',
    0,
    E'Training completed\nFinal accuracy: 0.8805\nFinal loss: 0.4951',
    3072.8,
    85.2,
    ARRAY['ml', 'training', 'success'],
    'scheduler'
  ) ON CONFLICT DO NOTHING;

  -- Metrics collector - currently running
  INSERT INTO lsh_job_executions (
    job_id,
    execution_id,
    status,
    started_at,
    stdout,
    max_memory_mb,
    avg_cpu_percent,
    tags,
    triggered_by
  ) VALUES (
    job_id_metrics,
    'exec-' || gen_random_uuid()::text,
    'running',
    NOW() - INTERVAL '30 seconds',
    'Collecting metrics...',
    64.1,
    5.2,
    ARRAY['metrics', 'running'],
    'scheduler'
  ) ON CONFLICT DO NOTHING;

  -- Health monitor - failed execution example
  INSERT INTO lsh_job_executions (
    job_id,
    execution_id,
    status,
    started_at,
    completed_at,
    exit_code,
    stdout,
    stderr,
    error_type,
    error_message,
    max_memory_mb,
    avg_cpu_percent,
    tags,
    triggered_by
  ) VALUES (
    job_id_health,
    'exec-' || gen_random_uuid()::text,
    'failed',
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '2 hours' + INTERVAL '10 seconds',
    1,
    'Starting health checks...',
    'Connection timeout to database',
    'DatabaseError',
    'Failed to connect to database: connection timeout after 5s',
    96.4,
    12.1,
    ARRAY['health', 'failed'],
    'scheduler'
  ) ON CONFLICT DO NOTHING;

END $$;

-- Update next_run times for active jobs
UPDATE lsh_jobs
SET next_run = NOW() + INTERVAL '5 minutes'
WHERE status = 'active' AND (cron_expression IS NOT NULL OR interval_seconds IS NOT NULL);

-- Seed data complete
