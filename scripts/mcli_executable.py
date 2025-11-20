#!/usr/bin/env python3
"""
MCLI Executable Entry Point

This file serves as the main entry point for the MCLI executable.
It's used by the build system to create standalone executables.
"""

import sys


def main():
    """Main entry point for MCLI executable."""
    try:
        # Import and run the main MCLI application
        from mcli.app.main import main as mcli_main
        
        # Run the main application
        mcli_main()
    except ImportError as e:
        print(f"Error: Failed to import MCLI modules: {e}", file=sys.stderr)
        print("Please ensure MCLI is properly installed.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()