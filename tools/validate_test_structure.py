#!/usr/bin/env python3
"""
Validate test directory structure and prevent artifact accumulation.
"""

import os
import sys
from pathlib import Path

def validate_test_directory():
    """Check for common test directory issues."""
    test_dir = Path("tests")
    issues = []
    
    # Check for Python cache
    cache_dirs = list(test_dir.rglob("__pycache__"))
    if cache_dirs:
        issues.append(f"Found {len(cache_dirs)} __pycache__ directories")
    
    # Check for compiled files
    compiled_files = list(test_dir.rglob("*.pyc")) + list(test_dir.rglob("*.pyo"))
    if compiled_files:
        issues.append(f"Found {len(compiled_files)} compiled Python files")
    
    # Check for pytest cache
    pytest_cache = test_dir / ".pytest_cache"
    if pytest_cache.exists():
        issues.append("Found pytest cache directory")
    
    # Check for coverage artifacts
    coverage_files = list(test_dir.rglob(".coverage")) + list(test_dir.rglob("htmlcov"))
    if coverage_files:
        issues.append(f"Found {len(coverage_files)} coverage artifacts")
    
    # Check file count (should be reasonable)
    python_files = list(test_dir.rglob("*.py"))
    if len(python_files) > 200:
        issues.append(f"High number of Python test files: {len(python_files)}")
    
    return issues

if __name__ == "__main__":
    issues = validate_test_directory()
    if issues:
        print("❌ Test directory validation issues:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✅ Test directory validation passed")
        sys.exit(0)