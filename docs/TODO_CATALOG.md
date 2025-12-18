# TODO/FIXME Catalog

## Summary
- Total TODOs: 34
- Total files affected: 17
- High Priority (blocking features): 8
- Medium Priority (nice to have): 18
- Low Priority (minor improvements): 8

## High Priority TODOs (Blocking Features)

### ML Feature Implementation
1. **Model Serving** (`src/mcli/ml/serving/serve.py`)
   - Lines 23, 31, 39, 40
   - Impact: Core ML functionality blocked
   - Effort: Medium

2. **Backtesting Logic** (`src/mcli/ml/backtesting/run.py`)
   - Lines 28, 36, 45, 47
   - Impact: Trading feature blocked
   - Effort: High

3. **Model Training** (`src/mcli/ml/training/train.py`)
   - Lines 34, 46
   - Impact: Core ML functionality blocked
   - Effort: High

4. **Portfolio Optimization** (`src/mcli/ml/optimization/optimize.py`)
   - Lines 29, 42, 43
   - Impact: Trading feature blocked
   - Effort: High

### Storage Backend Implementation
5. **Supabase Backend** (`src/mcli/storage/factory.py`)
   - Lines 84-87
   - Impact: Data storage migration blocked
   - Effort: Medium

6. **SQLite Backend** (`src/mcli/storage/factory.py`)
   - Lines 91-93
   - Impact: Local fallback blocked
   - Effort: Low

### Storage Integration
7. **Dashboard Database Integration** (`src/mcli/ml/dashboard/pages/scrapers_and_logs.py`)
   - Lines 747, 753, 759
   - Impact: Data persistence blocked
   - Effort: Medium

8. **Storacha Integration** (`src/mcli/lib/constants/storage.py`)
   - Lines 146-147
   - Impact: File storage migration blocked
   - Effort: Medium

## Medium Priority TODOs (Nice to Have)

### Chat & Workflow
9. **Natural Language Scheduling** (`src/mcli/chat/chat.py`)
   - Lines 2060-2061
   - Impact: User experience improvement
   - Effort: Medium

10. **Notebook Web Editor** (`src/mcli/workflow/notebook/notebook_cmd.py`)
   - Lines 512-513
   - Impact: Editor feature enhancement
   - Effort: Medium

11. **MCLI API Validation** (`src/mcli/workflow/notebook/validator.py`)
   - Lines 182-183
   - Impact: Validation improvement
   - Effort: Low

### Azure Cloud Support
12. **Azure Credentials** (`src/mcli/lib/auth/token_util.py`)
   - Lines 236-237, 300-301
   - Impact: Multi-cloud support
   - Effort: Medium

13. **Azure UI Package Logic** (`src/mcli/lib/auth/token_util.py`)
   - Lines 898-899, 988-989
   - Impact: Azure platform compatibility
   - Effort: Low

## Low Priority TODOs (Minor Improvements)

### Testing & Development
14. **Watcher Testing** (`src/mcli/lib/watcher/watcher.py`)
   - Lines 10-11, 164-165, 173-174
   - Impact: Test coverage
   - Effort: Low

15. **Configuration Documentation** (`src/mcli/lib/config/config.py`)
   - Lines 10-11
   - Impact: Documentation completeness
   - Effort: Low

### Plugin Management
16. **Plugin Registration** (`src/mcli/self/self_cmd.py`)
   - Lines 555-556, 611-612
   - Impact: Plugin UX improvement
   - Effort: Low

### Infrastructure
17. **Dashboard Performance Tracking** (`src/mcli/ml/dashboard/pages/predictions_enhanced.py`)
   - Lines 688-689
   - Impact: Monitoring enhancement
   - Effort: Low

18. **Docker Image Pull** (`src/mcli/workflow/registry/registry.py`)
   - Lines 176-177
   - Impact: Container management
   - Effort: Low

### Code Cleanup
19. **Import Usage Validation** (`src/mcli/workflow/notebook/validator.py`)
   - Lines 253-254
   - Impact: Code quality
   - Effort: Low

## Recommended Action Plan

### Phase 1 (Sprints 1-2): Complete Blocking Features
- Implement Model Serving functionality
- Implement Backtesting logic
- Implement Model Training logic
- Implement Portfolio Optimization

### Phase 2 (Sprints 3-4): Storage & Integration
- Complete Supabase backend implementation
- Complete SQLite backend implementation
- Integrate dashboard with database
- Implement Storacha upload

### Phase 3 (Sprints 5-6): UX Enhancements
- Natural language scheduling
- Notebook web editor
- Azure cloud support
- Plugin management improvements

### Phase 4 (Ongoing): Technical Debt
- Code cleanup and documentation
- Testing improvements
- Performance optimizations