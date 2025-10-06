#!/usr/bin/env python3
"""Check Supabase schema to see actual column names"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Parse secrets file
env_file = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"')

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
client = create_client(url, key)

print("=" * 60)
print("SUPABASE SCHEMA CHECK")
print("=" * 60)

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
