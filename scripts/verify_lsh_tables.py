#!/usr/bin/env python3
"""
Verify LSH tables in Supabase
"""
import sys
from pathlib import Path

# Add scripts directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_helper import (
    create_supabase_client,
    get_table_sample,
    verify_table,
)

def verify_tables():
    """Verify LSH tables and data in Supabase"""

    print("=" * 70)
    print("LSH SUPABASE TABLES VERIFICATION")
    print("=" * 70)

    # Create Supabase client using helper
    supabase = create_supabase_client()
    if not supabase:
        print("Failed to connect to Supabase")
        sys.exit(1)

    print("✅ Connected to Supabase")
    print()

    # Check lsh_jobs table
    print("1. Checking lsh_jobs table...")
    stats = verify_table(supabase, "lsh_jobs")
    if stats['exists']:
        print(f"   ✓ Found {stats['count']} jobs")
        sample = get_table_sample(supabase, "lsh_jobs", limit=3)
        if sample:
            print("\n   Sample jobs:")
            for job in sample:
                print(f"     - {job['job_name']} ({job['type']}, {job['status']})")
    else:
        print(f"   ✗ Error: {stats['error']}")

    print()

    # Check lsh_job_executions table
    print("2. Checking lsh_job_executions table...")
    stats = verify_table(supabase, "lsh_job_executions")
    if stats['exists']:
        print(f"   ✓ Found {stats['count']} job executions")
        sample = get_table_sample(supabase, "lsh_job_executions", limit=3)
        if sample:
            print("\n   Sample executions:")
            for exec in sample:
                print(f"     - {exec['execution_id']}: {exec['status']}")
    else:
        print(f"   ✗ Error: {stats['error']}")

    print()

    # Check lsh_job_stats view
    print("3. Checking lsh_job_stats view...")
    stats = verify_table(supabase, "lsh_job_stats")
    if stats['exists']:
        print(f"   ✓ Found statistics for {stats['count']} jobs")
        sample = get_table_sample(supabase, "lsh_job_stats", limit=5)
        if sample:
            print("\n   Job Statistics:")
            for stat in sample:
                success_rate = stat.get('success_rate_percent', 0) or 0
                print(f"     - {stat['job_name']}: {stat['total_executions']} total, {success_rate:.1f}% success")
    else:
        print(f"   ✗ Error: {stats['error']}")

    print()

    # Check lsh_recent_executions view
    print("4. Checking lsh_recent_executions view...")
    stats = verify_table(supabase, "lsh_recent_executions")
    if stats['exists']:
        print(f"   ✓ Found {stats['count']} recent executions")
        sample = get_table_sample(supabase, "lsh_recent_executions", limit=5)
        if sample:
            print("\n   Recent Executions:")
            for exec in sample:
                duration = exec.get('duration_ms', 0) or 0
                print(f"     - {exec['job_name']}: {exec['status']} ({duration}ms)")
    else:
        print(f"   ✗ Error: {stats['error']}")

    print()
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    verify_tables()
