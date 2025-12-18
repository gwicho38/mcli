# Test Coverage Improvement Plan

## Current Status
- **Current Coverage**: 9.48% (3,723 statements, 4426 covered)
- **Previous Threshold**: 30%
- **New Threshold**: 25% (realistic intermediate goal)
- **Target Coverage**: 80% (long-term goal)

## High-Impact Areas for Coverage Improvement

### 1. Core CLI Commands (Priority: HIGH)
**Files**: `src/mcli/app/`
- `commands_cmd.py`: 896 statements, 0% coverage
- `main.py`: 263 statements, 12% coverage
- `new_cmd.py`: 256 statements, 16% coverage
- `init_cmd.py`: 152 statements, 0% coverage

**Impact**: Core functionality affects all users

### 2. Chat System (Priority: HIGH)
**Files**: `src/mcli/chat/`
- `chat.py`: 1,243 statements, 5% coverage
- `system_controller.py`: 409 statements, 8% coverage
- `system_integration.py`: 426 statements, 5% coverage

**Impact**: AI features and daemon integration

### 3. ML Dashboard (Priority: MEDIUM)
**Files**: `src/mcli/ml/dashboard/`
- `app_integrated.py`: 1,272 statements, 0% coverage
- `pages/scrapers_and_logs.py`: 449 statements, 0% coverage
- `pages/predictions_enhanced.py`: 389 statements, 0% coverage

**Impact**: ML/Trading visualization features

### 4. Storage & Auth (Priority: MEDIUM)
**Files**: `src/mcli/lib/` modules
- `auth/token_util.py`: 519 statements, 0% coverage
- `custom_commands.py`: 295 statements, 9% coverage
- `api/mcli_decorators.py`: 220 statements, 32% coverage

**Impact**: Authentication and extensibility

## Implementation Strategy

### Phase 1: Core CLI Coverage (Target: 18%)
1. **Commands Module Tests**:
   - Test command discovery and execution
   - Test command import/export functionality
   - Test store management (git operations)
   - Test script import workflows

2. **Main Module Tests**:
   - Test CLI initialization and configuration
   - Test command loading and lazy loading
   - Test error handling and exit codes
   - Test shell completion functionality

### Phase 2: Chat System Coverage (Target: 15%)
1. **Chat Functionality Tests**:
   - Test chat message processing
   - Test daemon communication
   - Test AI provider integration
   - Test error handling and fallbacks

2. **System Controller Tests**:
   - Test system operations
   - Test cache management
   - Test file operations
   - Test process management

### Phase 3: Integration Coverage (Target: 20%)
1. **API Integration Tests**:
   - Test daemon client functionality
   - Test API endpoints
   - Test authentication flows
   - Test error handling

2. **ML Integration Tests**:
   - Test ML module loading
   - Test configuration management
   - Test dashboard components
   - Test data ingestion

## Specific Test Implementation Plan

### Week 1-2: Core CLI Tests
```python
# tests/cli/test_commands_cmd.py
def test_command_discovery():
    # Test basic command discovery

def test_command_store_operations():
    # Test git init, add, commit, push

def test_script_import():
    # Test importing Python, bash, JS scripts
```

### Week 3-4: Chat Tests
```python
# tests/chat/test_chat.py
def test_chat_basic_flow():
    # Test basic chat interaction

def test_daemon_communication():
    # Test daemon client operations
```

### Week 5-6: Integration Tests
```python
# tests/integration/test_cli_daemon.py
def test_cli_with_daemon():
    # Test CLI-daemon integration

def test_end_to_end_workflow():
    # Test complete user workflows
```

## Coverage Monitoring

### Weekly Metrics
- Track overall coverage percentage
- Monitor coverage by module
- Identify coverage gaps and regressions
- Report progress toward targets

### Success Criteria
- **Phase 1**: Reach 18% coverage (core CLI)
- **Phase 2**: Reach 25% coverage (new threshold)
- **Phase 3**: Reach 35% coverage (comprehensive)
- **Long-term**: Reach 80% coverage (goal)

## Tools & Automation

### Coverage Reports
- Continuous coverage reporting in CI
- Automated coverage badge updates
- Coverage trend visualization
- Module-specific coverage tracking

### Quality Gates
- Coverage thresholds in pull requests
- Automated coverage regression detection
- Coverage requirements for new features

This plan provides a structured approach to systematically improve test coverage while focusing on high-impact functionality."