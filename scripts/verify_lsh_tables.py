#!/usr/bin/env python3
"""
Verify LSH tables in Supabase
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client, Client

def verify_tables():
    """Verify LSH tables and data in Supabase"""

    # Get Supabase credentials
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    # Create Supabase client
    supabase: Client = create_client(url, key)

    print("=" * 70)
    print("LSH SUPABASE TABLES VERIFICATION")
    print("=" * 70)
    print(f"Supabase URL: {url}")
    print()

    # Check lsh_jobs table
    print("1. Checking lsh_jobs table...")
    try:
        jobs = supabase.table("lsh_jobs").select("*").execute()
        print(f"   ✓ Found {len(jobs.data)} jobs")

        if jobs.data:
            print("\n   Sample jobs:")
            for job in jobs.data[:3]:
                print(f"     - {job['job_name']} ({job['type']}, {job['status']})")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")

    print()

    # Check lsh_job_executions table
    print("2. Checking lsh_job_executions table...")
    try:
        executions = supabase.table("lsh_job_executions").select("*").execute()
        print(f"   ✓ Found {len(executions.data)} job executions")

        if executions.data:
            print("\n   Sample executions:")
            for exec in executions.data[:3]:
                print(f"     - {exec['execution_id']}: {exec['status']}")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")

    print()

    # Check lsh_job_stats view
    print("3. Checking lsh_job_stats view...")
    try:
        stats = supabase.table("lsh_job_stats").select("*").execute()
        print(f"   ✓ Found statistics for {len(stats.data)} jobs")

        if stats.data:
            print("\n   Job Statistics:")
            for stat in stats.data:
                success_rate = stat.get('success_rate_percent', 0) or 0
                print(f"     - {stat['job_name']}: {stat['total_executions']} total, {success_rate:.1f}% success")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")

    print()

    # Check lsh_recent_executions view
    print("4. Checking lsh_recent_executions view...")
    try:
        recent = supabase.table("lsh_recent_executions").select("*").limit(5).execute()
        print(f"   ✓ Found {len(recent.data)} recent executions")

        if recent.data:
            print("\n   Recent Executions:")
            for exec in recent.data:
                duration = exec.get('duration_ms', 0) or 0
                print(f"     - {exec['job_name']}: {exec['status']} ({duration}ms)")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")

    print()
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    verify_tables()
