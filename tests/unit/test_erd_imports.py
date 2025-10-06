#!/usr/bin/env python3
"""
Test script to check if the mcli.lib.erd module can be imported correctly.
"""
import pytest


def test_erd_import():
    """Test that the ERD module can be imported correctly."""
    try:
        from mcli.lib.erd import do_erd, generate_merged_erd_for_types

        assert callable(do_erd)
        assert callable(generate_merged_erd_for_types)
    except ImportError as e:
        pytest.fail(f"Failed to import mcli.lib.erd: {e}")


if __name__ == "__main__":
    test_erd_import()
    print("All imports successful!")
