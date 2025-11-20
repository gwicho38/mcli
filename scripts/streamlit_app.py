"""
Politician Trading Tracker - Main Dashboard
Entry point for Streamlit Cloud deployment
"""

import sys
from pathlib import Path

import streamlit as st

# Configure page BEFORE any other Streamlit commands
st.set_page_config(
    page_title="Politician Trading Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/yourusername/mcli",
        "Report a bug": "https://github.com/yourusername/mcli/issues",
        "About": "# Politician Trading Tracker\nTrack, analyze, and replicate Congressional trading patterns.",
    },
)

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the overview page as main
from mcli.ml.dashboard.overview import show_overview

if __name__ == "__main__":
    show_overview()
