#!/usr/bin/env python3
"""Test Supabase connection and verify tables"""

import sys
from pathlib import Path

# Add scripts directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_helper import create_supabase_client, print_table_info, verify_tables

print("=" * 60)
print("SUPABASE CONNECTION TEST")
print("=" * 60)

# Create Supabase client using helper
print(f"\n1. Creating Supabase client...")
client = create_supabase_client()

if not client:
    print("\n❌ FAILED TO CONNECT")
    print("Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set in .env")
    sys.exit(1)

print("   ✅ Client created successfully")

# Test tables
tables_to_check = ["politicians", "trading_disclosures", "lsh_jobs"]

print(f"\n2. Checking tables...")
# Use helper function to verify all tables at once
all_stats = verify_tables(client, tables_to_check)
for table_name, stats in all_stats.items():
    print_table_info(table_name, stats)

# Test specific queries
print(f"\n3. Testing specific queries...")

# Import additional helper
from utils.supabase_helper import get_table_sample

# Sample politicians
politicians_sample = get_table_sample(client, "politicians", limit=3)
if politicians_sample:
    print(f"   ✅ Politicians sample: {len(politicians_sample)} records")
    for p in politicians_sample:
        print(f"      - {p.get('first_name', '')} {p.get('last_name', '')}")
else:
    print(f"   ⚠️  Politicians table is empty or inaccessible")

# Sample trading disclosures
disclosures_sample = get_table_sample(client, "trading_disclosures", limit=3)
if disclosures_sample:
    print(f"   ✅ Trading disclosures sample: {len(disclosures_sample)} records")
    for d in disclosures_sample:
        politician = d.get("politician_name", "N/A")
        ticker = d.get("ticker_symbol", "N/A")
        amount = d.get("amount", 0)
        print(
            f"      - {politician}: {ticker} ${amount:,.0f}"
            if isinstance(amount, (int, float))
            else f"      - {politician}: {ticker}"
        )
else:
    print(f"   ⚠️  Trading disclosures table is empty or inaccessible")

print("\n" + "=" * 60)
print("CONNECTION TEST COMPLETE")
print("=" * 60)
