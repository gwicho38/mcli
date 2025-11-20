"""
Shared Supabase utilities for MCLI scripts.

This module provides common Supabase client creation and table verification
functionality to avoid duplication across scripts.
"""

import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client


def create_supabase_client() -> Optional[Client]:
    """
    Create Supabase client from environment variables.

    Loads credentials from .env file and creates a Supabase client.

    Returns:
        Client: Supabase client instance
        None: If credentials are missing

    Environment Variables:
        SUPABASE_URL: Supabase project URL
        SUPABASE_SERVICE_ROLE_KEY: Service role key (or SUPABASE_KEY)

    Example:
        from mcli.scripts.utils.supabase_helper import create_supabase_client

        client = create_supabase_client()
        if client:
            data = client.table('politicians').select('*').execute()
    """
    # Load environment variables
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not url:
        print("❌ SUPABASE_URL not found in environment variables")
        return None

    if not key:
        print("❌ SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) not found in environment variables")
        return None

    try:
        client = create_client(url, key)
        return client
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {e}")
        return None


def verify_table(client: Client, table_name: str) -> dict[str, any]:
    """
    Verify that a table exists and return basic statistics.

    Args:
        client: Supabase client instance
        table_name: Name of the table to verify

    Returns:
        dict: Table statistics including count, exists status
            {
                'exists': bool,
                'count': int,
                'error': str (if any)
            }

    Example:
        stats = verify_table(client, 'politicians')
        if stats['exists']:
            print(f"Table has {stats['count']} rows")
    """
    try:
        # Try to select count from table
        result = client.table(table_name).select("*", count="exact").limit(1).execute()

        return {
            "exists": True,
            "count": result.count if hasattr(result, "count") else len(result.data),
            "error": None,
        }
    except Exception as e:
        return {"exists": False, "count": 0, "error": str(e)}


def print_table_info(table_name: str, stats: dict[str, any]):
    """
    Pretty print table information.

    Args:
        table_name: Name of the table
        stats: Statistics dictionary from verify_table()

    Example:
        stats = verify_table(client, 'politicians')
        print_table_info('politicians', stats)
    """
    if stats["exists"]:
        print(f"   ✅ {table_name:30s} - {stats['count']:,} rows")
    else:
        print(f"   ❌ {table_name:30s} - Error: {stats['error']}")


def verify_tables(client: Client, table_names: list[str]) -> dict[str, dict]:
    """
    Verify multiple tables and return statistics for all.

    Args:
        client: Supabase client instance
        table_names: List of table names to verify

    Returns:
        dict: Dictionary mapping table names to their stats

    Example:
        tables = ['politicians', 'politician_trades', 'ml_jobs']
        all_stats = verify_tables(client, tables)

        for table, stats in all_stats.items():
            print_table_info(table, stats)
    """
    results = {}

    for table_name in table_names:
        results[table_name] = verify_table(client, table_name)

    return results


def get_table_sample(client: Client, table_name: str, limit: int = 5) -> Optional[list[dict]]:
    """
    Get a sample of rows from a table.

    Args:
        client: Supabase client instance
        table_name: Name of the table
        limit: Number of rows to retrieve (default: 5)

    Returns:
        list: List of row dictionaries
        None: If error occurs

    Example:
        sample = get_table_sample(client, 'politicians', limit=3)
        if sample:
            for row in sample:
                print(row)
    """
    try:
        result = client.table(table_name).select("*").limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"❌ Error fetching sample from {table_name}: {e}")
        return None
