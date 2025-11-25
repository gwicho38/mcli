# MCLI Examples

This directory contains example scripts demonstrating various MCLI features and how to use mcli-framework as a Python library.

## Available Examples

### `demo_library_usage.py` ⭐ **NEW**
**Complete demonstration of using mcli-framework as a Python library.**

Shows how to:
- Create custom workflow commands programmatically
- Use command discovery and introspection
- Manage configuration and paths
- Work with the logger
- Sync scripts to JSON workflows
- Export/import commands

```bash
python examples/demo_library_usage.py
```

This is the best starting point for developers who want to build on top of mcli-framework!

### `demo_enhanced_chat.py`
Demonstrates the enhanced chat capabilities with context awareness and command suggestions.

```bash
python examples/demo_enhanced_chat.py
```

### `demo_lsh_to_mcli.py`
Shows integration between LSH (Local Semantic Hashing) and MCLI data pipeline.

```bash
python examples/demo_lsh_to_mcli.py
```

### `demo_scheduler.py`
Demonstrates the cron scheduler functionality for automated tasks.

```bash
python examples/demo_scheduler.py
```

## SDK Documentation

For comprehensive library usage documentation, see:
- **[SDK Documentation](../docs/SDK.md)** - Complete API reference and usage guide
- **[Custom Commands Guide](../docs/custom-commands.md)** - Workflow command management

## Requirements

Basic installation:
```bash
pip install mcli-framework
```

Some examples may require optional dependencies:

```bash
# For chat examples
pip install mcli-framework[chat]

# For ML/data pipeline examples
pip install mcli-framework[ml]

# All features (default in 7.x+)
pip install mcli-framework[all]
```
