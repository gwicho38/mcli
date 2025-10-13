#!/usr/bin/env python3
"""Check Supabase schema to see actual column names"""

import sys
from pathlib import Path

# Add scripts directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_helper import create_supabase_client

print("=" * 60)
print("SUPABASE SCHEMA CHECK")
print("=" * 60)

# Create Supabase client using helper
client = create_supabase_client()
if not client:
    print("Failed to connect to Supabase")
    print("Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set in .env")
    sys.exit(1)

# Check trading_disclosures schema
print("\n1. trading_disclosures columns:")
result = client.table("trading_disclosures").select("*").limit(1).execute()
if result.data:
    columns = list(result.data[0].keys())
    for col in sorted(columns):
        value = result.data[0][col]
        print(f"   - {col:30} = {str(value)[:50]}")
else:
    print("   ⚠️  Table is empty")

# Check politicians schema
print("\n2. politicians columns:")
result = client.table("politicians").select("*").limit(1).execute()
if result.data:
    columns = list(result.data[0].keys())
    for col in sorted(columns):
        value = result.data[0][col]
        print(f"   - {col:30} = {str(value)[:50]}")
else:
    print("   ⚠️  Table is empty")

# Try to get disclosures with politician name via JOIN
print("\n3. Testing JOIN query (disclosures with politician info):")
try:
    result = client.table("trading_disclosures").select(
        "*, politicians(first_name, last_name)"
    ).limit(3).execute()

    if result.data:
        print(f"   ✅ JOIN successful: {len(result.data)} records")
        for record in result.data:
            pol = record.get('politicians', {})
            if pol:
                name = f"{pol.get('first_name', '')} {pol.get('last_name', '')}"
            else:
                name = "No politician linked"
            ticker = record.get('ticker_symbol', 'N/A')
            amount = record.get('amount', 0)
            print(f"      - {name}: {ticker} ${amount:,.0f}")
    else:
        print("   ⚠️  No data returned")
except Exception as e:
    print(f"   ❌ JOIN failed: {e}")

print("\n" + "=" * 60)
