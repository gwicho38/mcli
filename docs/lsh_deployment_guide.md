# LSH Daemon Deployment Guide

## Overview

The LSH (Long-running Service Host) daemon is a job scheduler backend that manages background tasks, data pipelines, and scheduled jobs for the mcli ML system. This guide covers deploying the LSH daemon to fly.io and integrating it with your mcli dashboard.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  mcli Dashboard │◄────────┤   LSH Daemon     │◄────────┤   Supabase DB   │
│  (Streamlit)    │  HTTP   │   (fly.io)       │  HTTP   │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │
                                     │ Manages
                                     ▼
                            ┌──────────────────┐
                            │  Scheduled Jobs  │
                            │  Data Pipelines  │
                            │  Event Streams   │
                            └──────────────────┘
```

## Deployment Options

### Option 1: Deploy LSH Daemon as Standalone fly.io App (Recommended)

This option deploys the LSH daemon as a separate fly.io application.

### Option 2: Integrate with Existing Elixir App

If you already have an Elixir app on fly.io, you can add LSH endpoints to it.

### Option 3: Local Development with ngrok

For development/testing, run LSH locally and expose via ngrok.

---

## Option 1: Standalone fly.io Deployment

### Prerequisites

1. **fly.io CLI installed**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **fly.io account**:
   ```bash
   fly auth login
   ```

3. **LSH daemon source code** (if separate repository):
   - If LSH is your Elixir app, use that repository
   - If LSH is the mcli API daemon, use the mcli repository

### Step 1: Create fly.toml Configuration

Create `fly.lsh.toml` in your repository:

```toml
# fly.lsh.toml - LSH Daemon Configuration

app = "mcli-lsh-daemon"
primary_region = "sjc"  # Change to your preferred region

[build]
  dockerfile = "Dockerfile.lsh"

[env]
  PORT = "3030"
  # Add other environment variables here

[http_service]
  internal_port = 3030
  force_https = true
  auto_stop_machines = false  # Keep daemon always running
  auto_start_machines = true
  min_machines_running = 1

  [[http_service.checks]]
    grace_period = "10s"
    interval = "30s"
    method = "GET"
    timeout = "5s"
    path = "/health"

[[services]]
  protocol = "tcp"
  internal_port = 3030

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [services.concurrency]
    type = "connections"
    hard_limit = 1000
    soft_limit = 500

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512

[metrics]
  port = 9091
  path = "/metrics"
```

### Step 2: Create Dockerfile for LSH Daemon

If using the mcli API daemon as LSH:

Create `Dockerfile.lsh`:

```dockerfile
# Dockerfile.lsh - LSH Daemon Docker Image

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install --no-cache-dir uv && \
    uv sync --frozen

# Copy source code
COPY src/mcli ./mcli

# Set Python path
ENV PYTHONPATH=/app
ENV PORT=3030

# Expose port
EXPOSE 3030

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3030/health || exit 1

# Run LSH daemon
CMD ["python", "-m", "mcli.workflow.daemon.api_daemon", "start", "--host", "0.0.0.0", "--port", "3030"]
```

If using a separate LSH/Elixir app, use your existing Dockerfile.

### Step 3: Deploy to fly.io

```bash
# Create fly.io app
fly apps create mcli-lsh-daemon

# Set secrets (environment variables)
fly secrets set \
  SUPABASE_URL="your_supabase_url" \
  SUPABASE_KEY="your_supabase_key" \
  LSH_API_KEY="your_generated_api_key" \
  -a mcli-lsh-daemon

# Deploy
fly deploy --config fly.lsh.toml -a mcli-lsh-daemon

# Check status
fly status -a mcli-lsh-daemon

# View logs
fly logs -a mcli-lsh-daemon
```

### Step 4: Configure mcli Dashboard to Use Deployed LSH

Update your environment variables for the Streamlit dashboard:

**For Streamlit Cloud:**
Add to secrets configuration:
```toml
LSH_API_URL = "https://mcli-lsh-daemon.fly.dev"
LSH_API_KEY = "your_generated_api_key"
```

**For local development:**
Create/update `.env`:
```bash
LSH_API_URL=https://mcli-lsh-daemon.fly.dev
LSH_API_KEY=your_generated_api_key
```

### Step 5: Verify Connection

Test the connection:

```bash
# Check health
curl https://mcli-lsh-daemon.fly.dev/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "MCLI API Daemon",
#   "timestamp": "2025-10-06T...",
#   "active_commands": 0
# }

# From mcli CLI
mcli lsh-status --url https://mcli-lsh-daemon.fly.dev
```

---

## Option 2: Integrate with Existing Elixir App

If you already have an Elixir Phoenix app on fly.io:

### Step 1: Add LSH API Endpoints to Your Elixir App

Add these routes to your Phoenix router:

```elixir
# lib/your_app_web/router.ex

scope "/api", YourAppWeb do
  pipe_through :api

  # LSH API endpoints
  get "/health", LSHController, :health
  get "/status", LSHController, :status
  get "/jobs", LSHController, :list_jobs
  post "/jobs", LSHController, :create_job
  post "/jobs/:id/trigger", LSHController, :trigger_job
  get "/events", LSHController, :stream_events  # Server-Sent Events
end
```

### Step 2: Implement LSH Controller

```elixir
# lib/your_app_web/controllers/lsh_controller.ex

defmodule YourAppWeb.LSHController do
  use YourAppWeb, :controller

  def health(conn, _params) do
    json(conn, %{
      status: "healthy",
      service: "LSH Daemon",
      timestamp: DateTime.utc_now(),
      uptime: System.monotonic_time(:second)
    })
  end

  def status(conn, _params) do
    json(conn, %{
      running: true,
      pid: System.get_pid(),
      uptime: System.monotonic_time(:second),
      memoryUsage: %{
        heapUsed: :erlang.memory(:total)
      }
    })
  end

  def list_jobs(conn, params) do
    # Implement job listing logic
    jobs = YourApp.Jobs.list_jobs(params)
    json(conn, jobs)
  end

  def create_job(conn, params) do
    # Implement job creation logic
    case YourApp.Jobs.create_job(params) do
      {:ok, job} -> json(conn, job)
      {:error, reason} ->
        conn
        |> put_status(400)
        |> json(%{error: reason})
    end
  end

  def stream_events(conn, _params) do
    # Server-Sent Events implementation
    conn
    |> put_resp_content_type("text/event-stream")
    |> send_chunked(200)
    |> stream_events_loop()
  end

  defp stream_events_loop(conn) do
    # Implement SSE streaming
    # Send events as they occur
  end
end
```

### Step 3: Update fly.toml

Ensure your existing app exposes the necessary ports:

```toml
[env]
  LSH_ENABLED = "true"
  PORT = "3030"  # or your existing port

[http_service]
  internal_port = 3030  # match your Phoenix app port

  [[http_service.checks]]
    path = "/api/health"
```

### Step 4: Deploy Update

```bash
fly deploy -a your-existing-app
```

### Step 5: Configure mcli

```bash
# Set LSH URL to your existing app
export LSH_API_URL=https://your-existing-app.fly.dev/api
```

---

## Option 3: Local Development with ngrok

For development and testing:

### Step 1: Run LSH Daemon Locally

```bash
# Start the API daemon
python -m mcli.workflow.daemon.api_daemon start --port 3030

# Or using mcli CLI
mcli workflow api-daemon start --port 3030
```

### Step 2: Expose with ngrok

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Expose port 3030
ngrok http 3030

# Copy the forwarding URL (e.g., https://abc123.ngrok.io)
```

### Step 3: Configure mcli Dashboard

```bash
# Use the ngrok URL
export LSH_API_URL=https://abc123.ngrok.io
```

**Note:** ngrok URLs change on restart unless you have a paid account with reserved domains.

---

## API Endpoints Reference

The LSH daemon must implement these endpoints:

### Health & Status

```bash
GET /health
Response: { "status": "healthy", "service": "LSH Daemon", "timestamp": "..." }

GET /status
Response: { "running": true, "pid": 12345, "uptime": 3600, "memoryUsage": {...} }
```

### Job Management

```bash
GET /jobs?status=running
Response: [{ "id": "job-1", "name": "...", "status": "running", ... }]

POST /jobs
Body: { "name": "...", "command": "...", "schedule": {...} }
Response: { "id": "job-1", "status": "created" }

POST /jobs/:id/trigger
Response: { "status": "triggered" }

POST /jobs/:id/start
Response: { "status": "started" }

POST /jobs/:id/stop
Response: { "status": "stopped" }
```

### Event Streaming

```bash
GET /events
Content-Type: text/event-stream
Response: Server-Sent Events stream
```

---

## Environment Variables

Configure these environment variables for the LSH daemon:

```bash
# Required
PORT=3030
LSH_API_KEY=your_secure_api_key_here

# Supabase integration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional
LSH_LOG_LEVEL=info
LSH_MAX_CONCURRENT_JOBS=10
LSH_JOB_TIMEOUT=300
```

---

## Security

### API Key Generation

Generate a secure API key:

```bash
# Generate random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### CORS Configuration

If your dashboard is on a different domain, configure CORS:

**Python (FastAPI):**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-dashboard.streamlit.app",
        "http://localhost:8501"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Elixir (Phoenix):**
```elixir
# In endpoint.ex
plug Corsica,
  origins: [
    "https://your-dashboard.streamlit.app",
    "http://localhost:8501"
  ],
  allow_methods: ["GET", "POST", "PUT", "DELETE"],
  allow_headers: ["Authorization", "Content-Type"]
```

---

## Monitoring & Troubleshooting

### Check LSH Daemon Status

```bash
# Via fly.io CLI
fly status -a mcli-lsh-daemon
fly logs -a mcli-lsh-daemon

# Via HTTP API
curl https://mcli-lsh-daemon.fly.dev/health
curl https://mcli-lsh-daemon.fly.dev/status

# Via mcli CLI
mcli lsh-status
```

### Common Issues

#### Dashboard shows "LSH Daemon Not Reachable"

**Cause:** Dashboard cannot connect to LSH daemon

**Solutions:**
1. Verify LSH_API_URL is set correctly
2. Check LSH daemon is running: `fly status -a mcli-lsh-daemon`
3. Test endpoint directly: `curl https://your-lsh-url.fly.dev/health`
4. Check CORS configuration if dashboard is on different domain
5. Verify API key if authentication is enabled

#### Jobs Not Executing

**Cause:** LSH daemon not processing job queue

**Solutions:**
1. Check daemon logs: `fly logs -a mcli-lsh-daemon`
2. Verify Supabase connection
3. Check job status: `mcli lsh-jobs`
4. Increase timeout settings

#### Connection Timeout

**Cause:** Network/firewall issues

**Solutions:**
1. Verify fly.io app is in correct region
2. Check HTTP service configuration in fly.toml
3. Test from different network
4. Check fly.io status page

---

## Testing the Deployment

### Automated Health Check

Create `scripts/test_lsh_deployment.sh`:

```bash
#!/bin/bash

LSH_URL=${LSH_API_URL:-"http://localhost:3030"}

echo "Testing LSH Daemon at $LSH_URL"

# Test health endpoint
echo "1. Testing /health endpoint..."
curl -f "$LSH_URL/health" || { echo "❌ Health check failed"; exit 1; }
echo "✅ Health check passed"

# Test status endpoint
echo "2. Testing /status endpoint..."
curl -f "$LSH_URL/status" || { echo "❌ Status check failed"; exit 1; }
echo "✅ Status check passed"

# Test jobs endpoint
echo "3. Testing /jobs endpoint..."
curl -f "$LSH_URL/jobs" || { echo "❌ Jobs endpoint failed"; exit 1; }
echo "✅ Jobs endpoint passed"

echo "🎉 All tests passed!"
```

Make executable and run:

```bash
chmod +x scripts/test_lsh_deployment.sh
./scripts/test_lsh_deployment.sh
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale to multiple machines
fly scale count 2 -a mcli-lsh-daemon

# Scale by region
fly scale count 1 --region sjc -a mcli-lsh-daemon
fly scale count 1 --region iad -a mcli-lsh-daemon
```

### Vertical Scaling

```bash
# Increase memory
fly scale memory 1024 -a mcli-lsh-daemon

# Increase CPU
fly scale vm shared-cpu-2x -a mcli-lsh-daemon
```

---

## Cost Optimization

### Auto-stop Machines

For development environments, allow auto-stop:

```toml
[http_service]
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
```

### Resource Limits

Use minimal resources for light workloads:

```toml
[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256  # Minimum
```

---

## Next Steps

1. **Deploy LSH daemon** using Option 1, 2, or 3
2. **Configure mcli dashboard** with LSH_API_URL
3. **Test connection** using health checks
4. **Create scheduled jobs** for data pipelines
5. **Monitor performance** via fly.io dashboard

## Support

- **fly.io docs**: https://fly.io/docs
- **mcli issues**: https://github.com/gwicho38/mcli/issues
- **LSH integration examples**: `examples/demo_lsh_to_mcli.py`

---

**Ready to deploy!** Choose your deployment option and follow the steps above.
