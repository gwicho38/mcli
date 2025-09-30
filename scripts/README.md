# MCLI Scripts

Utility and debugging scripts for MCLI development and operations.

## Directory Structure

### `debug/`
Debugging scripts for troubleshooting specific features:
- `debug_uk_api.py` - Debug UK API integration
- `debug_uk_api_fixed.py` - Fixed version of UK API debugging

### `utilities/`
Operational utility scripts:
- `configure_real_data.py` - Configure real data sources
- `enable_real_data.py` - Enable real data mode
- `monitor_politician_trading.py` - Monitor politician trading data
- `cron_scheduler.py` - Cron job scheduler utility

### `entrypoint.sh`
Docker entrypoint script for containerized deployments.

## Usage

Most scripts can be run directly:

```bash
python scripts/utilities/monitor_politician_trading.py
```

Some scripts may require environment variables or configuration. Check individual script documentation.
