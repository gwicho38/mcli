#!/usr/bin/env python3
"""Test that dashboard can fetch and map Supabase data correctly"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Parse secrets
env_file = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"')

# Mock streamlit to prevent import errors
class MockStreamlit:
    def error(self, msg): print(f"ERROR: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def info(self, msg): print(f"INFO: {msg}")
    def expander(self, title): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def code(self, msg): print(f"  {msg}")

sys.modules['streamlit'] = MockStreamlit()

from supabase import create_client
import pandas as pd

print("="*60)
print("DASHBOARD DATA MAPPING TEST")
print("="*60)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
client = create_client(url, key)

print("\n1. Fetching raw data with JOIN...")
response = (
    client.table("trading_disclosures")
    .select("*, politicians(first_name, last_name, full_name, party, state_or_country)")
    .limit(5)
    .execute()
)

df = pd.DataFrame(response.data)
print(f"   ✅ Fetched {len(df)} records")

print("\n2. Mapping politician info...")
if 'politicians' in df.columns:
    df['politician_name'] = df['politicians'].apply(
        lambda x: x.get('full_name', '') if isinstance(x, dict) else ''
    )
    print(f"   ✅ Extracted politician_name")
    print(f"      Sample: {df['politician_name'].iloc[0] if len(df) > 0 else 'N/A'}")

print("\n3. Mapping ticker_symbol...")
if 'asset_ticker' in df.columns:
    df['ticker_symbol'] = df['asset_ticker']
elif 'asset_name' in df.columns:
    df['ticker_symbol'] = df['asset_name'].str.split().str[0]
print(f"   ✅ Mapped ticker_symbol")
print(f"      Sample: {df['ticker_symbol'].iloc[0] if len(df) > 0 else 'N/A'}")

print("\n4. Calculating amount from range...")
if 'amount_range_min' in df.columns and 'amount_range_max' in df.columns:
    df['amount'] = (
        df['amount_range_min'].fillna(0) + df['amount_range_max'].fillna(0)
    ) / 2
    print(f"   ✅ Calculated amount (midpoint of range)")
    sample_amount = df['amount'].iloc[0] if len(df) > 0 else 0
    print(f"      Sample: ${sample_amount:,.2f}")

print("\n5. Final dashboard-compatible columns:")
expected_cols = ['politician_name', 'ticker_symbol', 'amount', 'transaction_type', 'disclosure_date']
for col in expected_cols:
    if col in df.columns:
        sample = df[col].iloc[0] if len(df) > 0 else 'N/A'
        print(f"   ✅ {col:20} = {sample}")
    else:
        print(f"   ❌ {col:20} MISSING")

print("\n6. Sample records:")
if len(df) > 0:
    for idx, row in df.head(3).iterrows():
        pol_name = row.get('politician_name', 'N/A')
        ticker = row.get('ticker_symbol', 'N/A')
        amount = row.get('amount', 0)
        trans_type = row.get('transaction_type', 'N/A')
        print(f"   - {pol_name:25} {ticker:8} ${amount:>10,.0f}  ({trans_type})")

print("\n" + "="*60)
print("DATA MAPPING TEST COMPLETE")
print("="*60)
