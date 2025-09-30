# MCLI Examples

This directory contains example scripts demonstrating various MCLI features.

## Available Examples

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

## Requirements

Some examples may require optional dependencies:

```bash
# For chat examples
pip install mcli[chat]

# For ML/data pipeline examples
pip install mcli[ml]
```
