#!/usr/bin/env python3
"""
Wrapper script for mcli Cython executable.
This script imports and runs the compiled Cython extension.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def main():
    """Main entry point that imports and runs the Cython extension."""
    try:
        # Import the compiled Cython extension
        import mcli_main
        mcli_main.main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure the Cython extension is compiled and available.")
        sys.exit(1)
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 