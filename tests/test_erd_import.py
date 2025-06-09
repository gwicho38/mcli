#!/usr/bin/env python3
"""
Test script to check if the mcli.lib.erd module can be imported correctly.
"""
import traceback
import sys

try:
    print("Attempting to import erd...")
    from mcli.lib.erd import do_erd, generate_merged_erd_for_types
    print("Success! The erd module was imported correctly.")
    print(f"do_erd function: {do_erd}")
    print(f"generate_merged_erd_for_types function: {generate_merged_erd_for_types}")
except ImportError as e:
    print(f"Error importing mcli.lib.erd: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Now attempting to import the readiness module...")
try:
    from mcli.app.readiness.readiness import readiness, do_erd as readiness_do_erd
    print("Success! The readiness module was imported correctly.")
    print(f"readiness object: {readiness}")
    print(f"readiness do_erd function: {readiness_do_erd}")
except ImportError as e:
    print(f"Error importing mcli.app.readiness.readiness: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("All imports successful!")
sys.exit(0)