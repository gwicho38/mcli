-- Migration: LSH Jobs and Job Executions Schema
-- Description: Creates tables for LSH daemon job management and execution tracking
-- Author: LSH-MCLI Integration
-- Date: 2025-10-06

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Table: lsh_jobs
-- Description: Stores job definitions, configurations, and scheduling information
-- =============================================================================
CREATE TABLE IF NOT EXISTS lsh_jobs (
  -- Primary identification
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name TEXT NOT NULL UNIQUE,
  command TEXT NOT NULL,
  description TEXT,

  -- Job type and status
  type TEXT CHECK (type IN ('shell', 'system', 'scheduled', 'service', 'ml', 'data-pipeline')) DEFAULT 'shell',
  status TEXT CHECK (status IN ('active', 'paused', 'disabled', 'archived')) DEFAULT 'active',

  -- Scheduling configuration
  cron_expression TEXT,
  interval_seconds INTEGER,
  next_run TIMESTAMPTZ,
  last_run TIMESTAMPTZ,

  -- Execution configuration
  environment JSONB DEFAULT '{}'::jsonb,
  working_directory TEXT,
  max_memory_mb INTEGER,
  max_cpu_percent INTEGER,
  timeout_seconds INTEGER DEFAULT 3600,

  -- Retry configuration
  max_retries INTEGER DEFAULT 0,
  retry_delay_seconds INTEGER DEFAULT 60,

  -- Metadata and organization
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  priority INTEGER DEFAULT 0,
  created_by TEXT DEFAULT 'system',

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Constraints
  CONSTRAINT valid_schedule CHECK (
    (cron_expression IS NOT NULL AND interval_seconds IS NULL) OR
    (cron_expression IS NULL AND interval_seconds IS NOT NULL) OR
    (cron_expression IS NULL AND interval_seconds IS NULL)
  )
);

-- Indexes for lsh_jobs
CREATE INDEX IF NOT EXISTS idx_lsh_jobs_status ON lsh_jobs(status);
CREATE INDEX IF NOT EXISTS idx_lsh_jobs_type ON lsh_jobs(type);
CREATE INDEX IF NOT EXISTS idx_lsh_jobs_next_run ON lsh_jobs(next_run) WHERE next_run IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_lsh_jobs_tags ON lsh_jobs USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_lsh_jobs_created_at ON lsh_jobs(created_at DESC);

-- =============================================================================
-- Table: lsh_job_executions
-- Description: Tracks all job execution attempts with detailed metrics
-- =============================================================================
CREATE TABLE IF NOT EXISTS lsh_job_executions (
  -- Primary identification
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES lsh_jobs(id) ON DELETE CASCADE,
  execution_id TEXT NOT NULL,

  -- Execution status
  status TEXT CHECK (status IN ('queued', 'running', 'completed', 'failed', 'killed', 'timeout')) DEFAULT 'queued',
  exit_code INTEGER,
  signal TEXT,

  -- Process information
  pid INTEGER,
  ppid INTEGER,
  hostname TEXT,

  -- Timing information
  queued_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  duration_ms INTEGER,

  -- Output and logs (consider object storage for large logs)
  stdout TEXT,
  stderr TEXT,
  output_size_bytes INTEGER DEFAULT 0,
  log_file_path TEXT,

  -- Resource usage metrics
  max_memory_mb REAL,
  avg_cpu_percent REAL,
  disk_io_mb REAL,

  -- Execution context
  environment JSONB DEFAULT '{}'::jsonb,
  working_directory TEXT,
  triggered_by TEXT DEFAULT 'scheduler',

  -- Retry information
  retry_count INTEGER DEFAULT 0,
  parent_execution_id UUID REFERENCES lsh_job_executions(id),

  -- Error details
  error_type TEXT,
  error_message TEXT,
  stack_trace TEXT,

  -- Metadata
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  metadata JSONB DEFAULT '{}'::jsonb,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Constraints
  UNIQUE(job_id, execution_id)
);

-- Indexes for lsh_job_executions
CREATE INDEX IF NOT EXISTS idx_lsh_job_executions_job_id ON lsh_job_executions(job_id);
CREATE INDEX IF NOT EXISTS idx_lsh_job_executions_status ON lsh_job_executions(status);
CREATE INDEX IF NOT EXISTS idx_lsh_job_executions_started_at ON lsh_job_executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_lsh_job_executions_completed_at ON lsh_job_executions(completed_at DESC) WHERE completed_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_lsh_job_executions_execution_id ON lsh_job_executions(execution_id);

-- =============================================================================
-- Functions and Triggers
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for lsh_jobs updated_at
DROP TRIGGER IF EXISTS update_lsh_jobs_updated_at ON lsh_jobs;
CREATE TRIGGER update_lsh_jobs_updated_at
  BEFORE UPDATE ON lsh_jobs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Trigger for lsh_job_executions updated_at
DROP TRIGGER IF EXISTS update_lsh_job_executions_updated_at ON lsh_job_executions;
CREATE TRIGGER update_lsh_job_executions_updated_at
  BEFORE UPDATE ON lsh_job_executions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate execution duration
CREATE OR REPLACE FUNCTION calculate_execution_duration()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
    NEW.duration_ms = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER * 1000;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate duration
DROP TRIGGER IF EXISTS calculate_lsh_execution_duration ON lsh_job_executions;
CREATE TRIGGER calculate_lsh_execution_duration
  BEFORE INSERT OR UPDATE ON lsh_job_executions
  FOR EACH ROW
  EXECUTE FUNCTION calculate_execution_duration();

-- =============================================================================
-- Views for common queries
-- =============================================================================

-- View: Job execution statistics
CREATE OR REPLACE VIEW lsh_job_stats AS
SELECT
  j.id,
  j.job_name,
  j.type,
  j.status,
  COUNT(e.id) AS total_executions,
  COUNT(CASE WHEN e.status = 'completed' THEN 1 END) AS successful_executions,
  COUNT(CASE WHEN e.status = 'failed' THEN 1 END) AS failed_executions,
  COUNT(CASE WHEN e.status = 'running' THEN 1 END) AS running_executions,
  ROUND(
    (COUNT(CASE WHEN e.status = 'completed' THEN 1 END)::NUMERIC /
     NULLIF(COUNT(CASE WHEN e.status IN ('completed', 'failed') THEN 1 END), 0)) * 100,
    2
  ) AS success_rate_percent,
  AVG(e.duration_ms) AS avg_duration_ms,
  MIN(e.duration_ms) AS min_duration_ms,
  MAX(e.duration_ms) AS max_duration_ms,
  MAX(e.completed_at) AS last_execution_at,
  AVG(e.max_memory_mb) AS avg_memory_mb,
  MAX(e.max_memory_mb) AS max_memory_mb
FROM lsh_jobs j
LEFT JOIN lsh_job_executions e ON j.id = e.job_id
GROUP BY j.id, j.job_name, j.type, j.status;

-- View: Recent job executions (last 100)
CREATE OR REPLACE VIEW lsh_recent_executions AS
SELECT
  e.id,
  e.job_id,
  j.job_name,
  e.execution_id,
  e.status,
  e.started_at,
  e.completed_at,
  e.duration_ms,
  e.exit_code,
  e.error_message,
  e.triggered_by,
  e.retry_count
FROM lsh_job_executions e
JOIN lsh_jobs j ON e.job_id = j.id
ORDER BY e.started_at DESC
LIMIT 100;

-- =============================================================================
-- Row Level Security (RLS)
-- =============================================================================

-- Enable RLS on tables
ALTER TABLE lsh_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE lsh_job_executions ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all operations for authenticated users (adjust as needed)
CREATE POLICY "Allow all for authenticated users" ON lsh_jobs
  FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow all for authenticated users" ON lsh_job_executions
  FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- =============================================================================
-- Comments for documentation
-- =============================================================================

COMMENT ON TABLE lsh_jobs IS 'LSH daemon job definitions and configurations';
COMMENT ON TABLE lsh_job_executions IS 'LSH job execution history and metrics';
COMMENT ON VIEW lsh_job_stats IS 'Aggregated statistics for all jobs';
COMMENT ON VIEW lsh_recent_executions IS 'Recent 100 job executions for monitoring';

-- Migration complete
