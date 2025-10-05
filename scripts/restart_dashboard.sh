#!/bin/bash
# Restart the MCLI ML Dashboard
# This script cleanly stops and restarts the dashboard

set -e

echo "🛑 Stopping any running Streamlit processes..."
pkill -f "streamlit run" 2>/dev/null || true
sleep 2

echo "🧹 Clearing Streamlit cache..."
rm -rf ~/.streamlit/cache 2>/dev/null || true

echo "🚀 Starting ML Dashboard..."
echo ""
echo "Dashboard will be available at: http://localhost:8501"
echo "Press Ctrl+C to stop"
echo ""

cd /Users/lefv/repos/mcli
.venv/bin/python -m streamlit run src/mcli/ml/dashboard/app_integrated.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.gatherUsageStats false
