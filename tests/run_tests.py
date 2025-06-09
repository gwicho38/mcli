#!/usr/bin/env python3
"""
Test runner for mcli tests
"""

import os
import sys
import unittest
import argparse

def run_tests(test_pattern=None):
    """
    Run the test suite
    
    Args:
        test_pattern: Optional pattern to match test files (default: all test_*.py)
    """
    # Add parent directory to sys.path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Discover tests in the current directory
    loader = unittest.TestLoader()
    
    if test_pattern:
        test_suite = loader.discover('.', pattern=f'test_{test_pattern}.py')
    else:
        test_suite = loader.discover('.', pattern='test_*.py')
    
    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run the test suite
    result = runner.run(test_suite)
    
    # Return exit code based on test result
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run mcli tests')
    parser.add_argument('pattern', nargs='?', help='Test pattern to run (e.g., "generate_graph" to run test_generate_graph.py)')
    
    args = parser.parse_args()
    
    sys.exit(run_tests(args.pattern))