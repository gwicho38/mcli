#!/usr/bin/env python3
"""
Test script to verify trading schema was created successfully in Supabase
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from supabase import create_client
    import streamlit as st
except ImportError:
    print("❌ Missing dependencies. Installing...")
    os.system("pip install supabase streamlit")
    from supabase import create_client
    import streamlit as st


def test_schema():
    """Test that all trading tables exist and are accessible"""

    # Get credentials from secrets
    try:
        # Try streamlit secrets first
        supabase_url = st.secrets.get("SUPABASE_URL")
        supabase_key = st.secrets.get("SUPABASE_KEY")
    except:
        # Fall back to environment
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        print("   Please set SUPABASE_URL and SUPABASE_KEY in .env or .streamlit/secrets.toml")
        return False

    print(f"🔗 Connecting to Supabase: {supabase_url}")

    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False

    # Test each table
    tables_to_test = [
        "trading_accounts",
        "portfolios",
        "positions",
        "trading_orders",
        "portfolio_performance_snapshots",
        "trading_signals"
    ]

    print("\n📊 Testing Trading Tables:")
    print("=" * 60)

    all_passed = True

    for table in tables_to_test:
        try:
            # Try to query the table (limit 0 to not fetch data, just test existence)
            result = supabase.table(table).select("*").limit(0).execute()
            print(f"✅ {table:<40} EXISTS")
        except Exception as e:
            print(f"❌ {table:<40} ERROR: {e}")
            all_passed = False

    print("=" * 60)

    # Test creating a test trading account
    print("\n🧪 Testing Write Operations:")
    print("=" * 60)

    try:
        # Create a test trading account
        test_account = {
            "account_name": "Test Account",
            "account_type": "test",
            "paper_trading": True,
            "risk_level": "moderate"
        }

        result = supabase.table("trading_accounts").insert(test_account).execute()
        account_id = result.data[0]["id"]
        print(f"✅ Created test trading_account (ID: {account_id})")

        # Create a test portfolio
        test_portfolio = {
            "trading_account_id": account_id,
            "name": "Test Portfolio",
            "description": "Auto-generated test portfolio",
            "initial_capital": 100000.00,
            "current_value": 100000.00,
            "cash_balance": 100000.00
        }

        result = supabase.table("portfolios").insert(test_portfolio).execute()
        portfolio_id = result.data[0]["id"]
        print(f"✅ Created test portfolio (ID: {portfolio_id})")

        # Clean up test data
        supabase.table("portfolios").delete().eq("id", portfolio_id).execute()
        supabase.table("trading_accounts").delete().eq("id", account_id).execute()
        print("✅ Cleaned up test data")

    except Exception as e:
        print(f"❌ Write test failed: {e}")
        all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 SUCCESS! All trading tables are working correctly!")
        print("\nYou can now use the trading dashboard at:")
        print("   https://politician-trading-tracker.streamlit.app/trading")
        return True
    else:
        print("\n❌ FAILED! Some tables are missing or not accessible")
        print("\nPlease verify the migration was run in Supabase SQL Editor:")
        print("   File: supabase/migrations/20251010_trading_tables_schema.sql")
        return False


if __name__ == "__main__":
    print("🔍 Trading Schema Verification Test")
    print("=" * 60)

    success = test_schema()

    sys.exit(0 if success else 1)
