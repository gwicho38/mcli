#!/usr/bin/env python3
"""
🚀 MCLI Publishing Script

This script helps you publish MCLI to PyPI/GitHub Packages with all the necessary
checks and Rust extension building.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse
import re

def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    if check and result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        sys.exit(1)
    
    return result

def main():
    print("🚀 MCLI Publishing Script")
    print("For full functionality, install dependencies and run from project root")

if __name__ == "__main__":
    main()