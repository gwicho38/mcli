"""
Standalone Gravity Anomaly Visualization App
Entry point for Streamlit deployment
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the app
from mcli.ml.dashboard.pages.gravity_viz import main

if __name__ == "__main__":
    main()
