# Politician Trading Tracker Migration

## Overview

The politician trading tracker functionality has been migrated from `mcli-framework` to a standalone repository for better maintainability, focused development, and independent versioning.

**New Repository:** https://github.com/gwicho38/politician-trading-tracker

## Migration Date

October 28, 2025

## Using the New Package

### Installation

```bash
pip install politician-trading-tracker
```

### Usage

```python
# New (standalone package)
from politician_trading.workflow import PoliticianTradingWorkflow
from politician_trading.config import WorkflowConfig
```

### CLI Commands

```bash
politician-trading collect
```

## Related Issues

- Migration Issue: #97
- Cleanup Issue: #98

For more details, see the new repository.
