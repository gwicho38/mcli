#!/usr/bin/env python3
"""
Verification Script for Streamlit Cloud Deployment

This script verifies that the Streamlit dashboard can successfully:
1. Connect to Supabase
2. Fetch politician trading data
3. Load ML pipeline components
4. Initialize training capabilities

Run this locally before deploying to Streamlit Cloud to catch issues early.

Usage:
    python scripts/verify_streamlit_deployment.py
    # or with virtual environment:
    .venv/bin/python scripts/verify_streamlit_deployment.py
"""

import os
import sys
from pathlib import Path

# Add scripts and src directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.supabase_helper import create_supabase_client


def verify_environment():
    """Verify environment variables and secrets are configured"""
    print("\n" + "=" * 80)
    print("STEP 1: Verifying Environment Configuration")
    print("=" * 80)

    # Check for secrets.toml
    secrets_file = Path(".streamlit/secrets.toml")
    if secrets_file.exists():
        print(f"✅ Found secrets file: {secrets_file}")

        # Try to load secrets
        try:
            import tomli

            with open(secrets_file, "rb") as f:
                secrets = tomli.load(f)
                print(f"✅ Secrets loaded successfully")

                # Check required keys
                required_keys = ["SUPABASE_URL", "SUPABASE_KEY"]
                missing_keys = [k for k in required_keys if k not in secrets]

                if missing_keys:
                    print(f"❌ Missing required secrets: {missing_keys}")
                    return False
                else:
                    print(f"✅ All required secrets present: {required_keys}")

                # Validate URLs
                if not secrets["SUPABASE_URL"].startswith("https://"):
                    print(f"⚠️  Warning: SUPABASE_URL should start with https://")

        except ImportError:
            print("⚠️  Warning: tomli not installed, cannot validate secrets.toml")
            print("   Install with: pip install tomli")
    else:
        print(f"⚠️  Secrets file not found at {secrets_file}")
        print("   Checking environment variables instead...")

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if url and key:
            print(f"✅ Found environment variables")
        else:
            print(f"❌ Missing environment variables")
            print(f"   SUPABASE_URL: {'✅' if url else '❌'}")
            print(f"   SUPABASE_KEY: {'✅' if key else '❌'}")
            return False

    return True


def verify_supabase_connection():
    """Verify connection to Supabase"""
    print("\n" + "=" * 80)
    print("STEP 2: Verifying Supabase Connection")
    print("=" * 80)

    try:
        # Create Supabase client using helper
        client = create_supabase_client()
        if not client:
            print("❌ Supabase credentials not configured")
            return False

        print("✅ Supabase client created")

        # Test connection with politicians table
        print("Testing politicians table...")
        politicians = client.table("politicians").select("*", count="exact").execute()
        print(f"✅ Politicians table accessible: {politicians.count} records")

        # Test disclosures table
        print("Testing trading_disclosures table...")
        disclosures = (
            client.table("trading_disclosures").select("*", count="exact").limit(10).execute()
        )
        print(f"✅ Disclosures table accessible: {disclosures.count} total records")

        if disclosures.data:
            print(f"✅ Sample disclosure retrieved successfully")
            sample = disclosures.data[0]
            print(f"   - ID: {sample.get('id', 'N/A')[:20]}...")
            print(f"   - Asset: {sample.get('asset_name', 'N/A')[:50]}")
            print(f"   - Date: {sample.get('transaction_date', 'N/A')[:10]}")

        # Check data pull jobs
        print("Testing data_pull_jobs table...")
        jobs = (
            client.table("data_pull_jobs")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if jobs.data:
            print(f"✅ Data pull jobs accessible: {len(jobs.data)} records")
            latest_job = jobs.data[0]
            print(f"   - Latest job: {latest_job.get('job_type', 'N/A')}")
            print(f"   - Status: {latest_job.get('status', 'N/A')}")
            print(f"   - Records found: {latest_job.get('records_found', 'N/A')}")
        else:
            print(f"⚠️  No data pull jobs found (database may be empty)")

        return True

    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        import traceback

        print(traceback.format_exc())
        return False


def verify_dashboard_imports():
    """Verify dashboard can be imported"""
    print("\n" + "=" * 80)
    print("STEP 3: Verifying Dashboard Imports")
    print("=" * 80)

    try:
        # Test streamlit import
        import streamlit as st

        print("✅ Streamlit imported successfully")
        print(f"   Version: {st.__version__}")

        # Test dashboard imports
        from mcli.ml.dashboard import app_integrated

        print("✅ Dashboard module imported")

        # Test Supabase client function
        # Note: We can't actually run st.cache_resource outside Streamlit
        print("✅ Dashboard imports complete")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("   Make sure all dependencies are installed:")
        print("   pip install streamlit pandas plotly supabase")
        return False


def verify_ml_pipeline():
    """Verify ML pipeline components are available"""
    print("\n" + "=" * 80)
    print("STEP 4: Verifying ML Pipeline Components")
    print("=" * 80)

    try:
        # Test ML imports
        from mcli.ml.preprocessing import MLDataPipeline, PoliticianTradingPreprocessor

        print("✅ Preprocessing modules imported")

        from mcli.ml.models import get_model_by_id

        print("✅ Model modules imported")

        try:
            from mcli.ml.predictions import PoliticianTradingPredictor

            print("✅ Prediction engine imported")
        except ImportError:
            print("⚠️  Prediction engine not available (optional)")

        return True

    except ImportError as e:
        print(f"⚠️  ML pipeline import warning: {e}")
        print("   Training may work with reduced functionality")
        return True  # Not critical for basic dashboard


def verify_data_flow():
    """Verify end-to-end data flow"""
    print("\n" + "=" * 80)
    print("STEP 5: Verifying End-to-End Data Flow")
    print("=" * 80)

    try:
        import pandas as pd

        # Create Supabase client using helper
        client = create_supabase_client()
        if not client:
            print("❌ Supabase credentials not configured")
            return False

        # Fetch disclosures
        print("Fetching disclosures...")
        response = client.table("trading_disclosures").select("*").limit(100).execute()
        df = pd.DataFrame(response.data)
        print(f"✅ Fetched {len(df)} disclosures")

        # Test datetime parsing
        print("Testing datetime parsing...")
        date_columns = ["transaction_date", "disclosure_date", "created_at", "updated_at"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="ISO8601", errors="coerce")
                print(f"   ✅ {col}: {df[col].dtype}")

        print("✅ Data flow verification complete")

        # Show sample data
        if not df.empty:
            print("\nSample data preview:")
            print(f"   Columns: {list(df.columns[:5])}...")
            print(f"   First row asset: {df.iloc[0].get('asset_name', 'N/A')[:50]}")
            print(
                f"   Date range: {df['transaction_date'].min()} to {df['transaction_date'].max()}"
            )

        return True

    except Exception as e:
        print(f"❌ Data flow verification failed: {e}")
        import traceback

        print(traceback.format_exc())
        return False


def main():
    """Run all verification checks"""
    print("\n" + "=" * 80)
    print("STREAMLIT CLOUD DEPLOYMENT VERIFICATION")
    print("=" * 80)
    print("\nThis script verifies that your local environment is correctly")
    print("configured to deploy the MCLI ML Dashboard to Streamlit Cloud.")
    print("\n" + "=" * 80)

    results = {
        "Environment Configuration": verify_environment(),
        "Supabase Connection": verify_supabase_connection(),
        "Dashboard Imports": verify_dashboard_imports(),
        "ML Pipeline Components": verify_ml_pipeline(),
        "End-to-End Data Flow": verify_data_flow(),
    }

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")

    print("\n" + "=" * 80)

    if all(results.values()):
        print("🎉 All checks passed! Ready for Streamlit Cloud deployment.")
        print("\nNext steps:")
        print("1. Configure secrets in Streamlit Cloud (Settings → Secrets)")
        print("2. Copy contents of .streamlit/secrets.toml to Streamlit Cloud")
        print("3. Deploy and verify at https://web-mcli.streamlit.app")
        print("4. Check for 'Using demo trading data' message (should NOT appear)")
        print("\nSee docs/streamlit_cloud_deployment.md for detailed instructions.")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above before deploying.")
        print("\nCommon fixes:")
        print("- Ensure .streamlit/secrets.toml exists with SUPABASE_URL and SUPABASE_KEY")
        print("- Run: pip install streamlit pandas plotly supabase tomli")
        print("- Verify Supabase credentials are correct")
        return 1


if __name__ == "__main__":
    sys.exit(main())
