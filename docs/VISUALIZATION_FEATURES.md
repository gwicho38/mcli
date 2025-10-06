# Visualization & Dashboard Features

This document catalogs all visualization, dashboard, and web-based features across the MCLI and LSH codebases.

## Table of Contents
- [Overview](#overview)
- [LSH Visualization Features](#lsh-visualization-features)
- [MCLI Visualization Features](#mcli-visualization-features)
- [Integration Points](#integration-points)
- [How to Use](#how-to-use)

---

## Overview

The MCLI and LSH ecosystem provides multiple visualization interfaces:

1. **Electron Desktop App** (LSH) - Native desktop dashboard application
2. **Web Dashboards** (LSH) - HTML-based monitoring interfaces
3. **Streamlit Dashboards** (MCLI) - Interactive ML dashboards
4. **REST APIs** (MCLI + LSH) - FastAPI and Express servers
5. **WebSocket Real-time** (LSH) - Live job updates

---

## LSH Visualization Features

### 1. Electron Desktop Application

**Location**: `/Users/lefv/repos/lsh/src/electron/`

**What it is**: A native desktop application built with Electron that provides a unified dashboard for monitoring LSH pipelines.

**Features**:
- **Multi-page dashboard** with navigation bar
- **Pipeline Jobs Dashboard** - Monitor running jobs
- **Workflow Builder** - Visual workflow creation
- **ML Dashboard** - ML pipeline monitoring
- **CI/CD Dashboard** - CI/CD pipeline tracking
- **System Health** - Component health monitoring
- **Real-time updates** via WebSocket

**Files**:
```
src/electron/
├── main.cjs          # Electron main process (window management)
└── preload.cjs       # Security/context isolation layer
```

**How to Run**:
```bash
cd /Users/lefv/repos/lsh

# Development mode
npm run electron-dev

# Production mode
npm run dashboard
# or
npm run app
# or
npm run electron
```

**Window Configuration**:
- Size: 1400x1000 (min: 1200x800)
- Loads: `http://localhost:3034/hub`
- Auto-starts pipeline service on port 3034

**Navigation Menu**:
- Dashboard Hub → `http://localhost:3034/hub`
- Pipeline Jobs → `http://localhost:3034/dashboard/`
- Workflows → `http://localhost:3034/dashboard/workflow.html`
- ML Dashboard → `http://localhost:3034/ml/dashboard`
- CI/CD Dashboard → `http://localhost:3034/cicd/dashboard`
- System Health → `http://localhost:3034/health/all`

### 2. Web-Based Pipeline Service

**Location**: `/Users/lefv/repos/lsh/src/pipeline/pipeline-service.ts`

**What it is**: An Express.js server that provides web dashboards and REST APIs for pipeline management.

**Features**:
- **Express web server** on port 3034
- **WebSocket support** for real-time updates (Socket.IO)
- **REST API** for job management
- **HTML dashboards** served statically
- **Proxy to Streamlit** for ML dashboards
- **MCLI bridge** for cross-system integration

**Dashboard Pages**:
```
src/pipeline/dashboard/
├── hub.html           # Main dashboard hub
├── index.html         # Pipeline jobs overview
├── job-detail.html    # Individual job details
├── workflow.html      # Workflow management
├── workflow.js        # Workflow logic
└── workflow-builder.js # Visual workflow builder
```

**API Endpoints**:
```typescript
GET  /api/jobs              # List all jobs
GET  /api/jobs/:id          # Get job details
POST /api/jobs              # Create new job
POST /api/jobs/:id/trigger  # Trigger job execution
GET  /api/workflows         # List workflows
GET  /api/health            # Health check
```

**WebSocket Events**:
```typescript
'job-status-update'    # Real-time job status changes
'pipeline-event'       # Pipeline events
'workflow-update'      # Workflow state changes
```

**How to Run**:
```bash
cd /Users/lefv/repos/lsh

# Via npm script
npm run start:pipeline

# Direct node execution
node dist/pipeline/pipeline-service.js
```

### 3. Monitoring Dashboards (HTML)

**Location**: `/Users/lefv/repos/lsh/`

**Files**:
- `monitoring-dashboard.html` (16 KB) - Basic monitoring dashboard
- `monitoring-dashboard-v2.html` (46 KB) - Enhanced monitoring dashboard

**Features**:
- **Dark theme** with gradient backgrounds
- **Real-time metrics** display
- **Status indicators** with animations
- **Metric cards** with hover effects
- **Responsive grid layout**
- **Self-contained** (no external dependencies)

**How to Use**:
```bash
# Open directly in browser
open /Users/lefv/repos/lsh/monitoring-dashboard-v2.html

# Or serve via HTTP
python3 -m http.server 8080
# Then visit: http://localhost:8080/monitoring-dashboard-v2.html
```

### 4. CI/CD Dashboard

**Location**: `/Users/lefv/repos/lsh/src/cicd/dashboard/`

**Features**:
- **Build pipeline tracking**
- **Deployment monitoring**
- **Analytics dashboard**
- **Admin interface**

**Files**:
```
src/cicd/dashboard/
├── index.html          # Main CI/CD dashboard
├── analytics.html      # Analytics view
└── admin.html          # Admin panel
```

### 5. LSH Daemon API

**Location**: `/Users/lefv/repos/lsh/src/daemon/api-server.ts`

**Deployed URL**: `https://mcli-lsh-daemon.fly.dev`

**API Endpoints**:
```bash
# Health check
GET /health
{
  "status": "healthy",
  "service": "LSH Daemon",
  "timestamp": "2025-10-06T21:51:20.697Z",
  "uptime": 4197.75,
  "version": "0.5.2"
}

# Daemon status
GET /api/status
{
  "running": true,
  "pid": 642,
  "uptime": 4275.73,
  "memoryUsage": { ... },
  "version": "0.5.2"
}

# Job registry
GET /api/jobs
{
  "jobs": [
    {
      "job_name": "ml-model-training",
      "status": "completed",
      "last_run": "2025-10-06T05:18:48.853418+00:00",
      "duration_ms": 6300000,
      "job_type": "ml",
      "cron_expression": "0 2 * * *",
      "tags": ["ml", "training", "prediction"]
    },
    ...
  ]
}
```

---

## MCLI Visualization Features

### 1. Streamlit Dashboards

**Location**: `/Users/lefv/repos/mcli/src/mcli/ml/dashboard/`

#### A. Integrated Dashboard (Primary)

**File**: `app_integrated.py` (2,390 lines)

**Features**:
- **7 major pages**:
  1. Pipeline Overview - System metrics, data sources, LSH jobs
  2. ML Processing - Data preprocessing, feature engineering
  3. Model Performance - Accuracy tracking, metrics
  4. Model Training & Evaluation - Interactive training interface
  5. Predictions - Live predictions with filtering
  6. LSH Jobs - Daemon status and job logs
  7. System Health - Component monitoring

- **Interactive Model Training**:
  - Hyperparameter tuning UI
  - Real-time training progress
  - Loss/accuracy curves visualization
  - Early stopping controls
  - Model comparison tools

- **Politician Trading Analysis**:
  - Searchable politician dropdown (from database)
  - Trading history visualization
  - Transaction type distribution
  - Timeline analysis
  - Interactive prediction generator

- **LSH Integration**:
  - Live job monitoring from Fly.io daemon
  - Job execution timeline
  - Status tracking
  - Real-time health checks

**Run Command**:
```bash
cd /Users/lefv/repos/mcli

# Via Makefile (recommended)
make dashboard

# Direct command
.venv/bin/streamlit run src/mcli/ml/dashboard/app_integrated.py --server.port 8501
```

**Deployed URL**:
- Streamlit Cloud: `https://web-mcli.streamlit.app` (when deployed)
- Local: `http://localhost:8501`

#### B. Training Dashboard

**File**: `app_training.py`

**Focus**: ML model training workflows
- Training progress tracking
- Loss curve visualization
- Hyperparameter history
- Model versioning

**Run Command**:
```bash
make dashboard-training
# Runs on http://localhost:8502
```

#### C. Supabase Dashboard

**File**: `app_supabase.py`

**Focus**: Database monitoring
- Politician data overview
- Trading disclosures tracking
- Data quality metrics
- Real-time database stats

**Run Command**:
```bash
make dashboard-supabase
# Runs on http://localhost:8503
```

#### D. Basic Dashboard

**File**: `app.py`

**Focus**: Essential ML metrics only
- Lightweight alternative
- Core predictions
- Model status
- Quick insights

### 2. FastAPI ML System

**Location**: `/Users/lefv/repos/mcli/src/mcli/ml/api/`

**What it is**: Production-grade REST API for ML model serving and management.

**Main App**: `app.py`
- **Framework**: FastAPI + Uvicorn
- **Features**: CORS, rate limiting, sessions, error handling
- **Auto-docs**: `/docs` (Swagger UI), `/redoc` (ReDoc)
- **WebSocket**: Real-time prediction updates

**Routers** (9 modules):
```python
/api/auth          # Authentication & authorization
/api/models        # Model management (list, load, deploy)
/api/predictions   # Generate predictions
/api/trades        # Trading recommendations
/api/portfolio     # Portfolio management
/api/backtest      # Backtesting engine
/api/data          # Data ingestion
/api/monitoring    # System monitoring
/api/admin         # Admin operations
/websocket         # Real-time updates
```

**How to Run**:
```bash
cd /Users/lefv/repos/mcli

# Development mode
uvicorn mcli.ml.api.app:app --reload --port 8000

# Production mode
uvicorn mcli.ml.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

**API Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### 3. Model Serving API

**Location**: `/Users/lefv/repos/mcli/src/mcli/ml/mlops/model_serving.py`

**What it is**: Dedicated FastAPI server for serving trained ML models.

**Features**:
- **RESTful endpoints** for predictions
- **Batch prediction** support
- **Model versioning** and hot-swapping
- **Feature extraction** pipeline
- **Caching** for performance
- **Health checks** and metrics

**Endpoints**:
```python
POST /predict             # Single prediction
POST /predict/batch       # Batch predictions
GET  /health             # Service health
GET  /metrics            # Model metrics
GET  /models             # List loaded models
POST /models/load        # Load new model
POST /models/reload      # Reload current model
```

**Request Example**:
```json
{
  "trading_data": {
    "politician": "Nancy Pelosi",
    "transaction_type": "Purchase",
    "amount": 500000
  },
  "tickers": ["AAPL", "NVDA", "MSFT"],
  "features": {
    "sentiment": 0.8,
    "volatility": 0.3
  }
}
```

**Response Example**:
```json
{
  "recommendations": [
    {
      "ticker": "NVDA",
      "recommendation": "BUY",
      "predicted_return": 0.15,
      "confidence": 0.87,
      "risk_score": 0.42
    }
  ],
  "timestamp": "2025-10-07T00:00:00Z",
  "model_version": "1.0.0",
  "processing_time_ms": 125.3
}
```

### 4. Dashboard CLI Commands

**Location**: `/Users/lefv/repos/mcli/src/mcli/workflow/dashboard/dashboard_cmd.py`

**What it is**: CLI wrapper for launching dashboards.

**Commands**:
```bash
# Launch integrated dashboard
mcli dashboard launch

# Launch specific variant
mcli dashboard launch --variant training
mcli dashboard launch --variant supabase
mcli dashboard launch --variant basic

# Status check
mcli dashboard status

# Stop dashboard
mcli dashboard stop
```

---

## Integration Points

### 1. LSH ↔ MCLI Integration

**How they connect**:

```
┌─────────────────┐         HTTP/WS        ┌─────────────────┐
│   LSH Electron  │◄──────────────────────►│  LSH Pipeline   │
│   Desktop App   │                        │  Service :3034  │
└─────────────────┘                        └────────┬────────┘
                                                    │
                                                    │ Proxy
                                                    ▼
┌─────────────────┐         HTTP           ┌─────────────────┐
│   MCLI FastAPI  │◄──────────────────────►│ Streamlit       │
│   API :8000     │                        │ Dashboard :8501 │
└────────┬────────┘                        └─────────────────┘
         │
         │ REST API
         ▼
┌─────────────────┐         HTTP           ┌─────────────────┐
│ LSH Daemon API  │◄──────────────────────►│  Supabase DB    │
│ fly.dev:443     │                        │  (PostgreSQL)   │
└─────────────────┘                        └─────────────────┘
```

**Data Flow**:
1. LSH Daemon (Fly.io) stores job metadata in Supabase
2. MCLI Streamlit dashboards query Supabase for data
3. MCLI Streamlit dashboards call LSH Daemon API for live job status
4. LSH Pipeline Service proxies requests to MCLI APIs
5. Electron app displays unified view of all systems

### 2. Streamlit Integration with LSH

**Configuration**:
```toml
# .streamlit/secrets.toml
LSH_API_URL = "https://mcli-lsh-daemon.fly.dev"
SUPABASE_URL = "https://uljsqvwkomdrlnofmlad.supabase.co"
SUPABASE_KEY = "<anon-key>"
```

**Code Example** (`app_integrated.py`):
```python
def check_lsh_daemon():
    """Check if LSH daemon is running"""
    lsh_api_url = os.getenv("LSH_API_URL", "http://localhost:3030")
    response = requests.get(f"{lsh_api_url}/health", timeout=2)
    return response.status_code == 200

def get_lsh_jobs():
    """Get LSH daemon job status from API"""
    lsh_api_url = os.getenv("LSH_API_URL", "http://localhost:3030")
    response = requests.get(f"{lsh_api_url}/api/jobs", timeout=5)
    return pd.DataFrame(response.json()["jobs"])
```

---

## How to Use

### Scenario 1: Local Development (All Services)

**Terminal 1 - LSH Daemon**:
```bash
cd /Users/lefv/repos/lsh
npm run start:pipeline
# Runs on http://localhost:3034
```

**Terminal 2 - MCLI API**:
```bash
cd /Users/lefv/repos/mcli
.venv/bin/uvicorn mcli.ml.api.app:app --reload --port 8000
# Runs on http://localhost:8000
```

**Terminal 3 - MCLI Dashboard**:
```bash
cd /Users/lefv/repos/mcli
make dashboard
# Runs on http://localhost:8501
```

**Terminal 4 - LSH Electron App**:
```bash
cd /Users/lefv/repos/lsh
npm run electron-dev
# Opens desktop window
```

### Scenario 2: Production (Cloud Deployment)

**LSH Daemon**:
```bash
# Already deployed on Fly.io
https://mcli-lsh-daemon.fly.dev
```

**MCLI Dashboard**:
```bash
# Deploy to Streamlit Cloud
# Set secrets in Streamlit Cloud UI:
# - LSH_API_URL = https://mcli-lsh-daemon.fly.dev
# - SUPABASE_URL = https://uljsqvwkomdrlnofmlad.supabase.co
# - SUPABASE_KEY = <anon-key>

# Access at:
https://web-mcli.streamlit.app
```

**MCLI API**:
```bash
# Deploy to cloud provider (Railway, Fly.io, etc.)
# Or run locally and expose via ngrok
```

### Scenario 3: Quick Monitoring (Standalone)

**Option A - HTML Dashboard (No Dependencies)**:
```bash
cd /Users/lefv/repos/lsh
open monitoring-dashboard-v2.html
```

**Option B - Electron App Only**:
```bash
cd /Users/lefv/repos/lsh
npm run app
# Includes pipeline service automatically
```

**Option C - Streamlit Only**:
```bash
cd /Users/lefv/repos/mcli
make dashboard
# Connects to deployed LSH daemon
```

---

## Quick Reference

### Ports Used

| Service | Port | URL |
|---------|------|-----|
| LSH Pipeline Service | 3034 | http://localhost:3034 |
| MCLI FastAPI | 8000 | http://localhost:8000 |
| MCLI Streamlit (Integrated) | 8501 | http://localhost:8501 |
| MCLI Streamlit (Training) | 8502 | http://localhost:8502 |
| MCLI Streamlit (Supabase) | 8503 | http://localhost:8503 |
| Model Serving API | 9090 | http://localhost:9090 |

### Production URLs

| Service | URL |
|---------|-----|
| LSH Daemon API | https://mcli-lsh-daemon.fly.dev |
| MCLI Dashboard | https://web-mcli.streamlit.app |
| Supabase Database | https://uljsqvwkomdrlnofmlad.supabase.co |

### Key Files

**LSH**:
- Electron: `src/electron/main.cjs`
- Pipeline Service: `src/pipeline/pipeline-service.ts`
- Daemon API: `src/daemon/api-server.ts`
- HTML Dashboards: `monitoring-dashboard-v2.html`

**MCLI**:
- Main Dashboard: `src/mcli/ml/dashboard/app_integrated.py`
- FastAPI: `src/mcli/ml/api/app.py`
- Model Serving: `src/mcli/ml/mlops/model_serving.py`
- Makefile: `Makefile` (dashboard targets)

---

## Summary

The MCLI/LSH ecosystem provides comprehensive visualization through:

✅ **Desktop Application** - Electron-based unified dashboard
✅ **Web Dashboards** - HTML + Express pipeline monitoring
✅ **Interactive ML** - Streamlit dashboards with 7 major pages
✅ **REST APIs** - FastAPI for ML serving, Express for pipeline management
✅ **Real-time Updates** - WebSocket integration
✅ **Cloud Deployment** - Fly.io (LSH), Streamlit Cloud (MCLI)
✅ **Database Integration** - Supabase for persistence
✅ **Cross-platform** - macOS, Linux, Windows (Electron)

All visualization features are production-ready and actively maintained.
