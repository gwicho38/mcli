# ML Dashboard

Real-time monitoring dashboard for the MCLI ML system.

## Quick Start

1. **Install dashboard dependencies:**
   ```bash
   cd /Users/lefv/repos/mcli
   uv sync --extra dashboard
   ```

2. **Launch the dashboard:**
   ```bash
   uv run mcli-dashboard
   ```

   The dashboard will start on http://localhost:8501

3. **Custom configuration:**
   ```bash
   # Custom port and host
   uv run mcli-dashboard --port 8502 --host 0.0.0.0

   # Debug mode
   uv run mcli-dashboard --debug
   ```

## Features

The dashboard provides real-time monitoring of:

- **System Overview**: Key metrics, deployed models, active users, predictions
- **Model Management**: Model performance, accuracy tracking over time
- **Predictions Analysis**: Recent predictions with filtering capabilities
- **Portfolio Performance**: Portfolio metrics and risk-return analysis
- **System Health**: API server, Redis cache, database status
- **Live Monitoring**: Real-time feeds with auto-refresh

## Dashboard Pages

### Overview
- Deployed models count
- Active users metrics
- Daily predictions count
- Active portfolios
- Model accuracy comparison charts
- Prediction confidence distribution

### Models
- Model performance table
- Accuracy trends over time
- Model status tracking

### Predictions
- Recent predictions with filtering
- Ticker-based filtering
- Confidence threshold controls
- Scatter plots and analysis

### Portfolios
- Portfolio summary table
- Return performance charts
- Risk-return scatter plots
- Sharpe ratio analysis

### System Health
- Component health checks (API, Redis, Database)
- System resource usage charts
- 24-hour metrics history

### Live Monitoring
- Real-time prediction feed
- Live model status updates
- Automatic refresh every 5 seconds
- Interactive start/stop controls

## Configuration

The dashboard automatically connects to your ML system using the configuration in `mcli.ml.config.settings`.

Key settings:
- Database connection
- Redis cache
- API endpoints
- Model directories

## Troubleshooting

**Dashboard won't start:**
- Check that dependencies are installed: `uv sync --extra dashboard`
- Verify database connection is working
- Check logs for specific errors

**No data showing:**
- Ensure ML system is running and has generated data
- Check database contains models and predictions
- Verify connection settings

**Performance issues:**
- Reduce auto-refresh frequency in app settings
- Filter data to smaller time ranges
- Check system resources

## Development

To modify the dashboard:

1. Edit `/Users/lefv/repos/mcli/src/mcli/ml/dashboard/app.py`
2. Add new pages or components
3. Test with `uv run mcli-dashboard`

The dashboard uses Streamlit for the UI framework and Plotly for interactive charts.