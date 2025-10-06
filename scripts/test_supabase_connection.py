#!/usr/bin/env python3
"""Test Supabase connection and verify tables"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
env_file = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
if env_file.exists():
    # Parse TOML manually for simple key=value pairs
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                os.environ[key] = value

print("="*60)
print("SUPABASE CONNECTION TEST")
print("="*60)

# Get credentials
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"\n1. Checking credentials...")
print(f"   SUPABASE_URL: {url[:30]}..." if url else "   ❌ SUPABASE_URL not set")
print(f"   SUPABASE_KEY: {'✅ Set (' + key[:20] + '...)' if key else '❌ Not set'}")

if not url or not key:
    print("\n❌ MISSING CREDENTIALS")
    print("Set SUPABASE_URL and SUPABASE_KEY in .streamlit/secrets.toml")
    sys.exit(1)

# Test connection
print(f"\n2. Testing connection to {url}...")
try:
    client: Client = create_client(url, key)
    print("   ✅ Client created successfully")
except Exception as e:
    print(f"   ❌ Failed to create client: {e}")
    sys.exit(1)

# Test tables
tables_to_check = [
    "politicians",
    "trading_disclosures",
    "lsh_jobs"
]

print(f"\n3. Checking tables...")
for table_name in tables_to_check:
    try:
        # Try to query with limit 1
        result = client.table(table_name).select("*").limit(1).execute()
        count_result = client.table(table_name).select("id", count="exact").limit(1).execute()
        total_count = count_result.count if hasattr(count_result, 'count') else "unknown"

        print(f"   ✅ {table_name:20} - {total_count} records")

        if result.data and len(result.data) > 0:
            # Show column names
            columns = list(result.data[0].keys())
            print(f"      Columns: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
    except Exception as e:
        print(f"   ❌ {table_name:20} - Error: {str(e)[:50]}")

# Test specific queries
print(f"\n4. Testing specific queries...")

try:
    # Get sample politician
    result = client.table("politicians").select("first_name, last_name").limit(5).execute()
    if result.data:
        print(f"   ✅ Politicians query: {len(result.data)} records")
        for p in result.data[:3]:
            print(f"      - {p.get('first_name', '')} {p.get('last_name', '')}")
    else:
        print(f"   ⚠️  Politicians table is empty")
except Exception as e:
    print(f"   ❌ Politicians query failed: {e}")

try:
    # Get sample disclosure
    result = client.table("trading_disclosures").select("politician_name, ticker_symbol, amount").limit(5).execute()
    if result.data:
        print(f"   ✅ Trading disclosures query: {len(result.data)} records")
        for d in result.data[:3]:
            print(f"      - {d.get('politician_name', 'N/A')}: {d.get('ticker_symbol', 'N/A')} ${d.get('amount', 0):,.0f}")
    else:
        print(f"   ⚠️  Trading disclosures table is empty")
except Exception as e:
    print(f"   ❌ Trading disclosures query failed: {e}")

print("\n" + "="*60)
print("CONNECTION TEST COMPLETE")
print("="*60)
