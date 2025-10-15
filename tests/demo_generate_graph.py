#!/usr/bin/env python3
"""
Demonstration script for testing the modified do_erd function.

This script creates a mock realGraph.json file and patches the modified_do_erd
function to use this mock file instead of the real one.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add parent directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, project_root)

# Import the test harness
from test_harness import SAMPLE_GRAPH_DATA, create_mock_graph_json

# Import the modules to test
from mcli.app.main import generate_graph


def demo_generate_graph_with_mock_data():
    """Demonstrate the generate_graph functionality with mock data"""
    print("Creating mock realGraph.json file...")
    mock_file_path = create_mock_graph_json()

    print(f"Mock data created at: {mock_file_path}")

    # Create a function that patches the file path to use our mock file
    def mock_join(*args, **kwargs):
        # Always return the mock file path, regardless of the arguments
        return mock_file_path

    # Patch the os.path.join function to return our mock file path
    with patch("os.path.join", side_effect=mock_join):
        print("\nRunning modified_do_erd with max_depth=2...")
        result = generate_graph.modified_do_erd(max_depth=2)

        if result:
            dot_file, png_file = result
            print(f"\nGenerated files:")
            print(f"DOT file: {dot_file}")
            print(f"PNG file: {png_file}")

            # Check if the files exist in the project root
            dot_path = os.path.join(project_root, dot_file)
            png_path = os.path.join(project_root, png_file)

            if os.path.exists(dot_path) and os.path.exists(png_path):
                print("\nFiles successfully created!")
            else:
                print("\nWarning: Expected files not found at the expected location.")
        else:
            print("\nNo result returned from modified_do_erd.")

    print("\nCleaning up mock file...")
    os.remove(mock_file_path)
    print("Done!")


def run_tests():
    """Run unit tests for the generate_graph module"""
    loader = unittest.TestLoader()
    suite = loader.discover(script_dir, pattern="test_generate_graph.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    # Check if running in test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sys.exit(run_tests())
    else:
        demo_generate_graph_with_mock_data()
