# Technical Debt Policy

## TODO/FIXME Policy
This document outlines the policy for managing technical debt in the MCLI codebase.

## Categories

### 1. **BLOCKING** - Immediate Action Required
- Prevents core functionality
- Blocks user workflows
- Security vulnerabilities
- Examples: Model serving, training, backtesting stubs

### 2. **FEATURE** - Scheduled Development
- Planned feature enhancements
- Architectural improvements
- Examples: Natural language scheduling, web editor

### 3. **CLEANUP** - Technical Debt
- Code quality improvements
- Performance optimizations
- Documentation updates
- Examples: Import validation, test coverage

## TODO Format

```python
# TODO[cat]: Description
# TODO[feature]: Description  
# TODO[cleanup]: Description
# FIXME[security]: Description
```

## Tracking

### All TODOs must reference an issue:
```python
# TODO[feature]: Implement natural language parser
# See: #123
```

### Time-bound TODOs:
```python
# TODO[cleanup][2024-01-15]: Remove deprecated function
```

## Automation

- Pre-commit hooks validate TODO format
- TODO catalog automatically updated
- Monthly technical debt review
- TODOs trigger issue creation for blocking items

## Review Process

### Weekly:
- Review new TODO additions
- Update TODO catalog
- Assign to appropriate sprint

### Monthly:
- Technical debt prioritization
- Cleanup sprint planning
- Metrics review (TODO count, resolution rate)

### Quarterly:
- Architecture review
- Major cleanup planning
- Policy updates

## Metrics

Track:
- Total TODO count by category
- Average age of TODOs
- Resolution rate
- Blocking TODO count

## Enforcements

- New TODOs without issue references trigger warnings
- Blocking TODOs auto-create issues
- Outdated TODOs flagged for review
- Cleanup TODOs prioritized in sprints