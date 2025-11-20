#!/usr/bin/env python3
"""Test that dashboard can fetch and map Supabase data correctly"""

import sys
from pathlib import Path

# Add scripts directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent))


# Mock streamlit to prevent import errors
class MockStreamlit:
    def error(self, msg):
        print(f"ERROR: {msg}")

    def warning(self, msg):
        print(f"WARNING: {msg}")

    def info(self, msg):
        print(f"INFO: {msg}")

    def expander(self, title):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def code(self, msg):
        print(f"  {msg}")


sys.modules["streamlit"] = MockStreamlit()

import pandas as pd
from utils.supabase_helper import create_supabase_client

print("=" * 60)
print("DASHBOARD DATA MAPPING TEST")
print("=" * 60)

# Create Supabase client using helper
client = create_supabase_client()
if not client:
    print("Failed to connect to Supabase")
    sys.exit(1)

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
if "politicians" in df.columns:
    df["politician_name"] = df["politicians"].apply(
        lambda x: x.get("full_name", "") if isinstance(x, dict) else ""
    )
    print(f"   ✅ Extracted politician_name")
    print(f"      Sample: {df['politician_name'].iloc[0] if len(df) > 0 else 'N/A'}")

print("\n3. Mapping ticker_symbol...")
if "asset_ticker" in df.columns:
    df["ticker_symbol"] = df["asset_ticker"]
elif "asset_name" in df.columns:
    df["ticker_symbol"] = df["asset_name"].str.split().str[0]
print(f"   ✅ Mapped ticker_symbol")
print(f"      Sample: {df['ticker_symbol'].iloc[0] if len(df) > 0 else 'N/A'}")

print("\n4. Calculating amount from range...")
if "amount_range_min" in df.columns and "amount_range_max" in df.columns:
    df["amount"] = (df["amount_range_min"].fillna(0) + df["amount_range_max"].fillna(0)) / 2
    print(f"   ✅ Calculated amount (midpoint of range)")
    sample_amount = df["amount"].iloc[0] if len(df) > 0 else 0
    print(f"      Sample: ${sample_amount:,.2f}")

print("\n5. Final dashboard-compatible columns:")
expected_cols = [
    "politician_name",
    "ticker_symbol",
    "amount",
    "transaction_type",
    "disclosure_date",
]
for col in expected_cols:
    if col in df.columns:
        sample = df[col].iloc[0] if len(df) > 0 else "N/A"
        print(f"   ✅ {col:20} = {sample}")
    else:
        print(f"   ❌ {col:20} MISSING")

print("\n6. Sample records:")
if len(df) > 0:
    for idx, row in df.head(3).iterrows():
        pol_name = row.get("politician_name", "N/A")
        ticker = row.get("ticker_symbol", "N/A")
        amount = row.get("amount", 0)
        trans_type = row.get("transaction_type", "N/A")
        print(f"   - {pol_name:25} {ticker:8} ${amount:>10,.0f}  ({trans_type})")

print("\n" + "=" * 60)
print("DATA MAPPING TEST COMPLETE")
print("=" * 60)
