#!/usr/bin/env python3
"""
Simple Python executable for mcli.
This script directly imports and runs the main function from mcli.app.main.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def main():
    """Main entry point that imports and runs the Python main function."""
    try:
        # Import and call the main function from mcli.app.main
        from mcli.app.main import main as python_main
        python_main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure the mcli package is installed and available.")
        sys.exit(1)
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 