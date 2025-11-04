"""Shared utility functions for dashboard pages."""

import logging
import os
import warnings
from typing import List, Optional

import pandas as pd
import streamlit as st
from supabase import Client, create_client

# Suppress Streamlit warnings when used outside runtime context
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
warnings.filterwarnings("ignore", message=".*No runtime found.*")
warnings.filterwarnings("ignore", message=".*Session state does not function.*")
warnings.filterwarnings("ignore", message=".*to view this Streamlit app.*")

logger = logging.getLogger(__name__)


def get_supabase_client() -> Optional[Client]:
    """Get Supabase client with Streamlit Cloud secrets support."""
    # Try Streamlit secrets first (for Streamlit Cloud), then fall back to environment variables (for local dev)
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    except (AttributeError, FileNotFoundError):
        # Secrets not available, try environment variables
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not key:
        logger.warning("Supabase credentials not found")
        return None

    try:
        client = create_client(url, key)
        # Test connection with a simple query
        try:
            client.table("politicians").select("id").limit(1).execute()
            logger.info(f"✅ Supabase connection successful (URL: {url[:30]}...)")
            return client
        except Exception as conn_error:
            st.error(f"❌ Supabase connection failed: {conn_error}")
            return None
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


def get_politician_names() -> List[str]:
    """Get all politician names from database for searchable dropdown."""
    try:
        client = get_supabase_client()
        if not client:
            return ["Nancy Pelosi", "Paul Pelosi", "Dan Crenshaw", "Josh Gottheimer"]  # Fallback

        result = client.table("politicians").select("first_name, last_name").execute()
        names = [f"{row['first_name']} {row['last_name']}" for row in result.data]
        return (
            names if names else ["Nancy Pelosi", "Paul Pelosi", "Dan Crenshaw", "Josh Gottheimer"]
        )
    except Exception as e:
        logger.error(f"Failed to get politician names: {e}")
        return ["Nancy Pelosi", "Paul Pelosi", "Dan Crenshaw", "Josh Gottheimer"]


def get_disclosures_data() -> pd.DataFrame:
    """Get trading disclosures from Supabase with proper schema mapping."""
    client = get_supabase_client()
    if not client:
        st.warning("⚠️ Supabase connection not available. Configure SUPABASE_URL and SUPABASE_KEY.")
        return pd.DataFrame()  # Return empty instead of demo data

    try:
        # Get the data with politician details joined
        response = (
            client.table("trading_disclosures")
            .select("*")
            .order("disclosure_date", desc=True)
            .limit(1000)
            .execute()
        )

        if not response.data:
            st.info(
                "📊 No trading disclosures found in database. Data collection may be in progress."
            )
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        # Get politician details and join
        if not df.empty and "politician_id" in df.columns:
            politician_ids = df["politician_id"].dropna().unique()
            if len(politician_ids) > 0:
                pol_response = (
                    client.table("politicians")
                    .select("id, full_name, party, state_or_country")
                    .in_("id", list(politician_ids))
                    .execute()
                )
                politicians = {p["id"]: p for p in pol_response.data}

                # Add politician details
                df["politician_name"] = df["politician_id"].map(
                    lambda x: politicians.get(x, {}).get("full_name", "Unknown")
                )
                df["politician_party"] = df["politician_id"].map(
                    lambda x: politicians.get(x, {}).get("party", "Unknown")
                )
                df["politician_state"] = df["politician_id"].map(
                    lambda x: politicians.get(x, {}).get("state_or_country", "Unknown")
                )

                # Map column names for compatibility
                df["ticker_symbol"] = df["asset_ticker"]
                df["amount"] = df["amount_exact"].fillna(
                    (df["amount_range_min"] + df["amount_range_max"]) / 2
                )

        return df

    except Exception as e:
        st.error(f"❌ Error fetching disclosures: {e}")
        logger.error(f"Failed to fetch disclosures: {e}")
        return pd.DataFrame()


def _generate_demo_disclosures() -> pd.DataFrame:
    """Generate demo trading disclosure data for testing."""
    st.info("🔵 Using demo trading data (Supabase unavailable)")

    import random
    from datetime import datetime, timedelta

    politicians = ["Nancy Pelosi", "Paul Pelosi", "Dan Crenshaw", "Josh Gottheimer"]
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD"]
    transaction_types = ["Purchase", "Sale"]

    data = []
    for _ in range(50):
        data.append(
            {
                "politician_name": random.choice(politicians),
                "ticker_symbol": random.choice(tickers),
                "transaction_type": random.choice(transaction_types),
                "amount_min": random.randint(1000, 100000),
                "amount_max": random.randint(100000, 1000000),
                "disclosure_date": (
                    datetime.now() - timedelta(days=random.randint(1, 365))
                ).strftime("%Y-%m-%d"),
                "asset_description": f"{random.choice(tickers)} Stock",
            }
        )

    return pd.DataFrame(data)


def get_politician_trading_history(politician_name: str) -> pd.DataFrame:
    """Get trading history for a specific politician."""
    try:
        client = get_supabase_client()
        if not client:
            return pd.DataFrame()  # Return empty if no client

        # Split name into first and last
        name_parts = politician_name.split()
        if len(name_parts) < 2:
            return pd.DataFrame()

        name_parts[0]
        _last_name = " ".join(name_parts[1:])  # noqa: F841

        # Get trading disclosures for this politician
        response = (
            client.table("trading_disclosures")
            .select("*")
            .eq("politician_name", politician_name)
            .order("disclosure_date", desc=True)
            .limit(100)
            .execute()
        )

        if response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame()

    except Exception as e:
        logger.warning(f"Failed to fetch trading history for {politician_name}: {e}")
        return pd.DataFrame()
