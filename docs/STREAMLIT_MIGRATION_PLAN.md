# Streamlit Dashboard Migration Plan

## Objective
Migrate all LSH Electron/Web dashboard features into the Streamlit application to create a single unified visualization interface.

## Current State Analysis

### ✅ Already in Streamlit (`app_integrated.py`)
1. **Pipeline Overview** - ML jobs, data sources, system metrics
2. **ML Processing** - Data preprocessing, feature engineering
3. **Model Performance** - Training metrics, accuracy tracking
4. **Model Training & Evaluation** - Interactive training, hyperparameter tuning
5. **Predictions** - Live predictions with filtering
6. **LSH Jobs** - Basic job monitoring from Fly.io daemon
7. **System Health** - Component status monitoring

### ❌ Missing from Streamlit (in LSH Dashboards)

#### From LSH Hub (hub.html)
- Dashboard launcher/hub interface
- Service status indicators
- Quick navigation between subsystems

#### From Pipeline Jobs Dashboard (index.html)
- Detailed job execution history
- Job filtering by type, status, owner
- Job retry/cancel controls
- Job execution logs viewer
- Job dependency graphs

#### From Workflow Dashboard (workflow.html)
- Workflow builder UI (drag-and-drop)
- Workflow templates
- Workflow execution triggers
- Workflow scheduling interface
- Workflow state machine visualization

#### From CI/CD Dashboard (cicd/dashboard/index.html)
- Build pipeline metrics
  - Success rate
  - Average build time
  - Failed builds count
  - Active pipelines
- Deployment tracking
- Build history timeline
- Pipeline configuration viewer
- Webhook management (GitHub/GitLab)
- Build logs viewer
- Artifact management

#### From Monitoring Dashboard (monitoring-dashboard-v2.html)
- Real-time system metrics
- CPU/Memory/Disk usage charts
- Network bandwidth monitoring
- Process list
- Log file tailing
- Alert configuration

#### Cross-cutting Features
- **WebSocket real-time updates** - Live job status changes
- **Responsive design** - Mobile-friendly layouts
- **Dark/Light theme toggle** - User preference
- **Export capabilities** - CSV/JSON data export
- **Advanced filtering** - Multi-column search/filter
- **Notifications** - Browser notifications for job completion

## Migration Plan

### Phase 1: Core Infrastructure (Priority: HIGH)
**Tasks:**
1. Add page navigation enhancement (sidebar with icons)
2. Implement WebSocket client for real-time updates
3. Add data export functionality (CSV/JSON)
4. Create reusable UI components library
5. Add theme toggle (dark/light mode)

**Estimated Time:** 2-3 hours

### Phase 2: Pipeline & Job Management (Priority: HIGH)
**Tasks:**
1. Enhanced job monitoring page
   - Job execution logs viewer
   - Job retry/cancel controls
   - Job dependency visualization
   - Advanced filtering (type, status, owner, date range)
2. Job detail view
   - Full execution logs
   - Performance metrics
   - Resource usage
   - Error stack traces

**Estimated Time:** 3-4 hours

### Phase 3: Workflow Management (Priority: MEDIUM)
**Tasks:**
1. Workflow listing page
   - Active workflows
   - Workflow templates
   - Execution history
2. Workflow builder (simplified)
   - YAML/JSON editor with validation
   - Template library
   - Schedule configuration
3. Workflow execution dashboard
   - Running workflows
   - Workflow state visualization
   - Step-by-step progress

**Estimated Time:** 4-5 hours

### Phase 4: CI/CD Integration (Priority: MEDIUM)
**Tasks:**
1. CI/CD pipeline page
   - Build metrics dashboard
   - Deployment tracking
   - Success rate charts
   - Build time trends
2. Pipeline configuration
   - Webhook management
   - Build triggers
   - Environment variables
3. Build history
   - Timeline view
   - Log viewer
   - Artifact links

**Estimated Time:** 3-4 hours

### Phase 5: System Monitoring (Priority: LOW)
**Tasks:**
1. Enhanced system health page
   - CPU/Memory/Disk real-time charts
   - Process monitoring
   - Network stats
   - Service status grid
2. Log aggregation viewer
   - Multi-source log tailing
   - Log search/filtering
   - Error highlighting
3. Alert management
   - Alert rules configuration
   - Alert history
   - Notification settings

**Estimated Time:** 3-4 hours

### Phase 6: Polish & UX (Priority: LOW)
**Tasks:**
1. Mobile responsive design
2. Keyboard shortcuts
3. Browser notifications
4. User preferences persistence
5. Tour/onboarding guide
6. Error handling improvements

**Estimated Time:** 2-3 hours

## Implementation Strategy

### Approach 1: Single Mega Dashboard (Recommended)
- Extend `app_integrated.py`
- Add new pages via sidebar navigation
- Pros: Single deployment, unified codebase
- Cons: File gets very large (consider splitting into modules)

### Approach 2: Modular Dashboard Suite
- Create separate dashboard files per domain
- Use Streamlit multipage app structure
- Pros: Better code organization, independent deployment
- Cons: More complex navigation

**Decision: Use Approach 1 with modular imports**

## Technical Architecture

### File Structure
```
src/mcli/ml/dashboard/
├── app_integrated.py          # Main app (existing)
├── components/               # New: Reusable components
│   ├── __init__.py
│   ├── charts.py            # Chart components
│   ├── tables.py            # Table components
│   ├── forms.py             # Form components
│   └── layouts.py           # Layout templates
├── pages/                   # New: Page modules
│   ├── __init__.py
│   ├── pipeline_jobs.py     # Enhanced job monitoring
│   ├── workflows.py         # Workflow management
│   ├── cicd.py              # CI/CD dashboard
│   └── monitoring.py        # System monitoring
└── utils/                   # New: Helper utilities
    ├── __init__.py
    ├── websocket_client.py  # WebSocket integration
    ├── data_export.py       # Export utilities
    └── api_clients.py       # API clients
```

### New Dependencies
```toml
# Add to pyproject.toml [project.dependencies]
python-socketio = "^5.11.0"      # WebSocket client
aiohttp = "^3.9.0"               # Async HTTP
streamlit-autorefresh = "^1.0.1" # Auto-refresh component
streamlit-ace = "^0.1.1"         # Code editor for workflows
streamlit-timeline = "^0.0.3"    # Timeline visualization
```

## Page-by-Page Feature Map

### Page 1: Pipeline Overview (Enhanced)
**Current:**
- ML job summary
- Data source stats
- LSH job count

**Add:**
- Service health grid (LSH, MCLI API, Supabase, Redis)
- Real-time job queue status
- Data pipeline flow diagram
- System alerts/notifications

### Page 2: ML Processing (Keep as-is)
- Already comprehensive

### Page 3: Model Performance (Keep as-is)
- Already comprehensive

### Page 4: Model Training (Keep as-is)
- Already comprehensive

### Page 5: Predictions (Keep as-is)
- Already comprehensive

### Page 6: Pipeline Jobs (NEW - Enhanced)
**Features:**
- Job list with advanced filtering
- Job detail modal/expander
- Job logs viewer (real-time tailing)
- Job actions (retry, cancel, trigger)
- Job dependency graph
- Job metrics (duration, success rate)

### Page 7: Workflows (NEW)
**Features:**
- Workflow list (active, scheduled, failed)
- Workflow builder (YAML editor)
- Template library
- Workflow execution history
- Schedule configuration (cron)
- Workflow state visualization

### Page 8: CI/CD (NEW)
**Features:**
- Build metrics dashboard
- Pipeline list (active, recent)
- Build history timeline
- Deployment tracker
- Webhook configuration
- Build log viewer
- Success rate trends

### Page 9: System Monitoring (NEW)
**Features:**
- CPU/Memory/Disk usage (real-time)
- Service status grid
- Process list
- Log aggregation viewer
- Alert configuration
- Network monitoring

### Page 10: LSH Jobs (Enhanced)
**Current:**
- Basic job listing
- Status counts

**Add:**
- Real-time updates via WebSocket
- Job type filtering
- Execution timeline chart
- Failure analysis
- Job trigger interface

### Page 11: System Health (Enhanced)
**Current:**
- Component status
- Resource usage mockups

**Add:**
- Real data from LSH daemon API
- Historical trends
- Alert history
- Service dependency map

## API Integration Requirements

### LSH Daemon API Extensions Needed
```typescript
// Add these endpoints to LSH daemon

GET  /api/jobs/:id/logs          // Stream job logs
POST /api/jobs/:id/retry         // Retry failed job
POST /api/jobs/:id/cancel        // Cancel running job

GET  /api/workflows              // List workflows
POST /api/workflows              // Create workflow
GET  /api/workflows/:id          // Get workflow details
POST /api/workflows/:id/trigger  // Trigger workflow

GET  /api/cicd/builds            // Build history
GET  /api/cicd/builds/:id/logs   // Build logs
POST /api/cicd/webhooks          // Configure webhooks

GET  /api/monitoring/metrics     // System metrics
GET  /api/monitoring/logs        // Aggregated logs
GET  /api/monitoring/alerts      // Alert history

WS   /ws/jobs                    // Job status updates
WS   /ws/metrics                 // Real-time metrics
```

### Supabase Schema Extensions
```sql
-- Add tables for CI/CD tracking
CREATE TABLE cicd_builds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    commit_sha TEXT,
    branch TEXT,
    logs_url TEXT,
    artifacts JSONB
);

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    definition JSONB NOT NULL,
    schedule TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    status TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_log JSONB
);
```

## Testing Strategy

### Unit Tests
- Component rendering tests
- API client tests
- Data transformation tests

### Integration Tests
- LSH daemon integration
- Supabase queries
- WebSocket connectivity

### E2E Tests
- Page navigation
- Job triggering workflow
- Export functionality

## Rollout Plan

### Week 1: Infrastructure (Phase 1)
- Set up modular structure
- Add WebSocket client
- Implement data export

### Week 2: Core Features (Phase 2-3)
- Enhanced job monitoring
- Workflow management

### Week 3: Advanced Features (Phase 4-5)
- CI/CD integration
- System monitoring

### Week 4: Polish (Phase 6)
- UX improvements
- Testing
- Documentation

## Success Metrics

1. **Feature Parity**: 100% of LSH dashboard features in Streamlit
2. **Performance**: Page load < 2s, real-time updates < 500ms latency
3. **Usability**: User can accomplish all tasks without leaving Streamlit
4. **Reliability**: 99.9% uptime, error rate < 0.1%

## Migration Checklist

- [ ] Phase 1: Infrastructure
  - [ ] Modular file structure
  - [ ] WebSocket client
  - [ ] Data export
  - [ ] Theme toggle
  - [ ] UI component library

- [ ] Phase 2: Pipeline Jobs
  - [ ] Job logs viewer
  - [ ] Job controls (retry, cancel)
  - [ ] Advanced filtering
  - [ ] Job dependency graph

- [ ] Phase 3: Workflows
  - [ ] Workflow listing
  - [ ] Workflow editor
  - [ ] Execution tracking

- [ ] Phase 4: CI/CD
  - [ ] Build dashboard
  - [ ] Webhook management
  - [ ] Build logs

- [ ] Phase 5: Monitoring
  - [ ] System metrics
  - [ ] Log viewer
  - [ ] Alert management

- [ ] Phase 6: Polish
  - [ ] Mobile responsive
  - [ ] Keyboard shortcuts
  - [ ] Notifications
  - [ ] Documentation

## Next Steps

1. Review and approve migration plan
2. Set up development environment with new dependencies
3. Create modular file structure
4. Begin Phase 1 implementation
5. Iterative deployment to Streamlit Cloud

---

**Status**: Draft - Awaiting Approval
**Owner**: Development Team
**Timeline**: 4 weeks estimated
**Priority**: HIGH
