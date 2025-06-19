#!/usr/bin/env python3
"""
PyInstaller entry point for mcli.
This script imports and calls the main function from mcli.app.main
which is the same entry point used by the Python wheel installation.
"""

if __name__ == "__main__":
    from mcli.app.main import main
    main()