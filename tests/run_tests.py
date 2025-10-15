#!/usr/bin/env python3
"""
Test runner for mcli tests
"""

import argparse
import os
import sys
import unittest

import pytest


def run_tests(test_pattern=None):
    """
    Run the test suite

    Args:
        test_pattern: Optional pattern to match test files (default: all test_*.py)
    """
    # Add parent directory to sys.path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    # Use pytest for better test discovery and reporting
    if test_pattern:
        # Run specific test file
        test_file = f"test_{test_pattern}.py"
        if os.path.exists(test_file):
            return pytest.main([test_file, "-v"])
        else:
            print(f"Test file {test_file} not found")
            return 1
    else:
        # Run all tests
        return pytest.main([".", "-v"])


def run_cli_tests():
    """
    Run only CLI-related tests
    """
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    cli_test_files = [
        "test_webapp.py",
        "test_webapp_comprehensive.py",
        "test_file.py",
        "test_registry.py",
        "test_repo.py",
        "test_gcloud.py",
        "test_videos.py",
        "test_wakatime.py",
        "test_oi.py",
        "test_self.py",
        "test_lib.py",
        "test_auth.py",
        "test_workflow.py",
        "test_workflow_integration.py",
        "test_main_app.py",
        "test_all_cli.py",
        "test_daemon.py",
        "test_harness.py",
        "test_uv_compatibility.py",
        "test_rich.py",
    ]

    # Run CLI tests
    return pytest.main(cli_test_files + ["-v"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mcli tests")
    parser.add_argument(
        "pattern",
        nargs="?",
        help='Test pattern to run (e.g., "generate_graph" to run test_generate_graph.py)',
    )
    parser.add_argument("--cli-only", action="store_true", help="Run only CLI tests")

    args = parser.parse_args()

    if args.cli_only:
        sys.exit(run_cli_tests())
    else:
        sys.exit(run_tests(args.pattern))
