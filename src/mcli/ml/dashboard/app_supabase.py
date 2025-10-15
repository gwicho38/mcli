"""Streamlit dashboard for ML system monitoring - Supabase version"""

import asyncio
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from mcli.ml.dashboard.common import (
    get_supabase_client,
    load_environment_variables,
    setup_page_config,
)
from mcli.ml.dashboard.styles import apply_dashboard_styles

# Page config must come first
setup_page_config(page_title="MCLI ML Dashboard")

# Load environment variables
load_environment_variables()

# Apply standard dashboard styles
apply_dashboard_styles()


@st.cache_data(ttl=30)
def get_politicians_data():
    """Get politicians data from Supabase"""
    client = get_supabase_client()
    if not client:
        st.warning("No Supabase client available")
        return pd.DataFrame()

    try:
        response = client.table("politicians").select("*").execute()
        df = pd.DataFrame(response.data)
        print(f"Fetched {len(df)} politicians")  # Debug output
        return df
    except Exception as e:
        st.error(f"Error fetching politicians: {e}")
        print(f"Error fetching politicians: {e}")  # Debug output
        return pd.DataFrame()


@st.cache_data(ttl=30)
def get_disclosures_data():
    """Get trading disclosures from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        # Get recent disclosures
        response = (
            client.table("trading_disclosures")
            .select("*")
            .order("disclosure_date", desc=True)
            .limit(500)
            .execute()
        )
        df = pd.DataFrame(response.data)

        # Convert datetime columns to proper datetime format
        date_columns = ["transaction_date", "disclosure_date", "created_at", "updated_at"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="ISO8601", errors="coerce")

        return df
    except Exception as e:
        st.error(f"Error fetching disclosures: {e}")
        print(f"Error details: {e}")  # Debug output
        return pd.DataFrame()


@st.cache_data(ttl=30)
def get_predictions_data():
    """Get ML predictions from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        # Try to get predictions if table exists
        response = (
            client.table("ml_predictions")
            .select("*")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return pd.DataFrame(response.data)
    except:
        # Table might not exist yet
        return pd.DataFrame()


@st.cache_data(ttl=30)
def get_portfolios_data():
    """Get portfolio data from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        # Try to get portfolios if table exists
        response = client.table("portfolios").select("*").execute()
        return pd.DataFrame(response.data)
    except:
        # Table might not exist yet
        return pd.DataFrame()


@st.cache_data(ttl=30)
def get_jobs_data():
    """Get data pull jobs from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        response = (
            client.table("data_pull_jobs")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching jobs: {e}")
        return pd.DataFrame()


def main():
    """Main dashboard function"""

    # Title and header
    st.title("🤖 MCLI ML System Dashboard")
    st.markdown("Real-time monitoring of politician trading ML system")

    # Show connection status in sidebar
    st.sidebar.title("Navigation")

    # External Dashboard Links
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 Navigation Hub")

    st.markdown(
        '<a href="file:///Users/lefv/repos/lsh/dashboard-hub.html" target="_blank" style="text-decoration: none;">'
        '<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-weight: 600;">'
        "🚀 Dashboard Hub - View All"
        "</div></a>",
        unsafe_allow_html=True,
    )

    st.sidebar.subheader("🔗 Direct Links")

    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        st.markdown(
            '<a href="http://localhost:3034/dashboard/" target="_blank" style="text-decoration: none;">'
            '<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 8px; border-radius: 6px; text-align: center; margin-bottom: 8px;">'
            "📊 Pipeline Jobs"
            "</div></a>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<a href="http://localhost:3034/dashboard/workflow.html" target="_blank" style="text-decoration: none;">'
            '<div style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; padding: 8px; border-radius: 6px; text-align: center; margin-bottom: 8px;">'
            "🔄 Workflows"
            "</div></a>",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            '<a href="http://localhost:3033/dashboard/" target="_blank" style="text-decoration: none;">'
            '<div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 8px; border-radius: 6px; text-align: center; margin-bottom: 8px;">'
            "🏗️ CI/CD"
            "</div></a>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<a href="http://localhost:3035/api/health" target="_blank" style="text-decoration: none;">'
            '<div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 8px; border-radius: 6px; text-align: center; margin-bottom: 8px;">'
            "🔍 Monitoring"
            "</div></a>",
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")

    # Debug info
    with st.sidebar.expander("🔧 Debug Info"):
        st.write(f"URL: {os.getenv('SUPABASE_URL', 'Not set')}")
        st.write(f"Key exists: {bool(os.getenv('SUPABASE_ANON_KEY'))}")
        client = get_supabase_client()
        if client:
            st.success("✅ Connected to Supabase")
        else:
            st.error("❌ Not connected to Supabase")
    page = st.sidebar.selectbox(
        "Choose a page",
        [
            "Overview",
            "Politicians",
            "Trading Disclosures",
            "ML Predictions",
            "Data Pull Jobs",
            "System Health",
        ],
    )

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
    if auto_refresh:
        import time

        time.sleep(30)
        st.rerun()

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

    # Main content based on selected page
    if page == "Overview":
        show_overview()
    elif page == "Politicians":
        show_politicians()
    elif page == "Trading Disclosures":
        show_disclosures()
    elif page == "ML Predictions":
        show_predictions()
    elif page == "Data Pull Jobs":
        show_jobs()
    elif page == "System Health":
        show_system_health()


def show_overview():
    """Show overview dashboard"""
    st.header("System Overview")

    # Get data
    politicians = get_politicians_data()
    disclosures = get_disclosures_data()
    predictions = get_predictions_data()
    jobs = get_jobs_data()

    # Debug: Show raw data counts
    st.sidebar.write(f"Debug: {len(politicians)} politicians loaded")
    st.sidebar.write(f"Debug: {len(disclosures)} disclosures loaded")
    st.sidebar.write(f"Debug: {len(jobs)} jobs loaded")

    # Also show sample data for debugging
    if not politicians.empty:
        st.sidebar.write(
            "Sample politician:",
            politicians.iloc[0]["full_name"] if "full_name" in politicians.columns else "No name",
        )

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Politicians Tracked",
            value=len(politicians) if not politicians.empty else 0,
            delta=None,  # Simplified to avoid errors
        )

    with col2:
        st.metric(
            label="Total Disclosures",
            value=len(disclosures),
            delta=(
                f"{len(disclosures[pd.to_datetime(disclosures['disclosure_date']) > datetime.now() - timedelta(days=7)])} this week"
                if not disclosures.empty and "disclosure_date" in disclosures
                else None
            ),
        )

    with col3:
        st.metric(label="ML Predictions", value=len(predictions) if not predictions.empty else "0")

    with col4:
        successful_jobs = (
            len(jobs[jobs["status"] == "completed"]) if not jobs.empty and "status" in jobs else 0
        )
        total_jobs = len(jobs) if not jobs.empty else 0
        st.metric(
            label="Job Success Rate",
            value=f"{(successful_jobs/total_jobs*100):.1f}%" if total_jobs > 0 else "N/A",
        )

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Disclosure Types")
        if not disclosures.empty and "transaction_type" in disclosures:
            type_counts = disclosures["transaction_type"].value_counts()
            fig = px.pie(
                values=type_counts.values, names=type_counts.index, title="Transaction Types"
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})
        else:
            st.info("No disclosure data available")

    with col2:
        st.subheader("Top Traded Tickers")
        if not disclosures.empty and "ticker_symbol" in disclosures:
            ticker_counts = disclosures["ticker_symbol"].value_counts().head(10)
            fig = px.bar(
                x=ticker_counts.values,
                y=ticker_counts.index,
                orientation="h",
                title="Most Traded Stocks",
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})
        else:
            st.info("No ticker data available")


def show_politicians():
    """Show politicians dashboard"""
    st.header("Politicians")

    politicians = get_politicians_data()

    if not politicians.empty:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            party_filter = st.multiselect(
                "Party",
                options=politicians["party"].dropna().unique() if "party" in politicians else [],
                default=[],
            )
        with col2:
            state_filter = st.multiselect(
                "State",
                options=politicians["state"].dropna().unique() if "state" in politicians else [],
                default=[],
            )
        with col3:
            active_only = st.checkbox("Active Only", value=True)

        # Apply filters
        filtered = politicians.copy()
        if party_filter and "party" in filtered:
            filtered = filtered[filtered["party"].isin(party_filter)]
        if state_filter and "state" in filtered:
            filtered = filtered[filtered["state"].isin(state_filter)]
        if active_only and "is_active" in filtered:
            filtered = filtered[filtered["is_active"] == True]

        # Display data
        st.dataframe(filtered, width="stretch")

        # Stats
        col1, col2 = st.columns(2)
        with col1:
            if "party" in filtered:
                party_dist = filtered["party"].value_counts()
                fig = px.pie(
                    values=party_dist.values, names=party_dist.index, title="Party Distribution"
                )
                st.plotly_chart(fig, width="stretch", config={"responsive": True})
        with col2:
            if "state" in filtered:
                state_dist = filtered["state"].value_counts().head(10)
                fig = px.bar(
                    x=state_dist.values, y=state_dist.index, orientation="h", title="Top States"
                )
                st.plotly_chart(fig, width="stretch", config={"responsive": True})
    else:
        st.warning("No politician data available")


def show_disclosures():
    """Show trading disclosures dashboard"""
    st.header("Trading Disclosures")

    disclosures = get_disclosures_data()

    if not disclosures.empty:
        # Convert dates
        if "disclosure_date" in disclosures:
            disclosures["disclosure_date"] = pd.to_datetime(disclosures["disclosure_date"])

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker_filter = st.text_input("Ticker Symbol", "").upper()
        with col2:
            transaction_types = (
                disclosures["transaction_type"].dropna().unique()
                if "transaction_type" in disclosures
                else []
            )
            transaction_filter = st.selectbox("Transaction Type", ["All"] + list(transaction_types))
        with col3:
            date_range = st.date_input(
                "Date Range",
                value=(datetime.now() - timedelta(days=30), datetime.now()),
                max_value=datetime.now(),
            )

        # Apply filters
        filtered = disclosures.copy()
        if ticker_filter and "ticker_symbol" in filtered:
            filtered = filtered[filtered["ticker_symbol"].str.contains(ticker_filter, na=False)]
        if transaction_filter != "All" and "transaction_type" in filtered:
            filtered = filtered[filtered["transaction_type"] == transaction_filter]
        if len(date_range) == 2 and "disclosure_date" in filtered:
            filtered = filtered[
                (filtered["disclosure_date"] >= pd.Timestamp(date_range[0]))
                & (filtered["disclosure_date"] <= pd.Timestamp(date_range[1]))
            ]

        # Display data
        st.dataframe(filtered, width="stretch")

        # Analysis
        if not filtered.empty:
            col1, col2 = st.columns(2)
            with col1:
                # Volume over time
                if "disclosure_date" in filtered and "amount" in filtered:
                    daily_volume = filtered.groupby(filtered["disclosure_date"].dt.date)[
                        "amount"
                    ].sum()
                    fig = px.line(
                        x=daily_volume.index,
                        y=daily_volume.values,
                        title="Trading Volume Over Time",
                    )
                    st.plotly_chart(fig, width="stretch", config={"responsive": True})

            with col2:
                # Top politicians by trading
                if "politician_name" in filtered:
                    top_traders = filtered["politician_name"].value_counts().head(10)
                    fig = px.bar(
                        x=top_traders.values,
                        y=top_traders.index,
                        orientation="h",
                        title="Most Active Traders",
                    )
                    st.plotly_chart(fig, width="stretch", config={"responsive": True})
    else:
        st.warning("No disclosure data available")


def show_predictions():
    """Show ML predictions dashboard"""
    st.header("ML Predictions")

    predictions = get_predictions_data()

    if not predictions.empty:
        st.dataframe(predictions, width="stretch")

        # Add prediction analysis charts if we have data
        if "confidence" in predictions:
            fig = px.histogram(
                predictions, x="confidence", title="Prediction Confidence Distribution"
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})
    else:
        st.info(
            "No ML predictions available yet. The ML pipeline will generate predictions once sufficient data is collected."
        )


def show_jobs():
    """Show data pull jobs dashboard"""
    st.header("Data Pull Jobs")

    jobs = get_jobs_data()

    if not jobs.empty:
        # Status overview
        col1, col2, col3 = st.columns(3)

        status_counts = jobs["status"].value_counts() if "status" in jobs else pd.Series()

        with col1:
            st.metric("Completed", status_counts.get("completed", 0))
        with col2:
            st.metric("Running", status_counts.get("running", 0))
        with col3:
            st.metric("Failed", status_counts.get("failed", 0))

        # Jobs table
        st.dataframe(jobs, width="stretch")

        # Success rate over time
        if "created_at" in jobs:
            jobs["created_at"] = pd.to_datetime(jobs["created_at"])
            jobs["date"] = jobs["created_at"].dt.date

            daily_stats = jobs.groupby(["date", "status"]).size().unstack(fill_value=0)
            fig = go.Figure()

            for status in daily_stats.columns:
                fig.add_trace(
                    go.Scatter(
                        x=daily_stats.index,
                        y=daily_stats[status],
                        mode="lines+markers",
                        name=status,
                        stackgroup="one",
                    )
                )

            fig.update_layout(title="Job Status Over Time", xaxis_title="Date", yaxis_title="Count")
            st.plotly_chart(fig, width="stretch", config={"responsive": True})
    else:
        st.warning("No job data available")


def show_system_health():
    """Show system health dashboard"""
    st.header("System Health")

    client = get_supabase_client()

    # Check Supabase connection
    col1, col2, col3 = st.columns(3)

    with col1:
        if client:
            try:
                # Try a simple query to test connection
                client.table("politicians").select("id").limit(1).execute()
                st.success("✅ Supabase: Connected")
            except:
                st.error("❌ Supabase: Connection Error")
        else:
            st.warning("⚠️ Supabase: Not Configured")

    with col2:
        # Check data freshness
        disclosures = get_disclosures_data()
        if not disclosures.empty and "created_at" in disclosures:
            latest = pd.to_datetime(disclosures["created_at"]).max()
            hours_ago = (datetime.now() - latest).total_seconds() / 3600
            if hours_ago < 24:
                st.success(f"✅ Data: Fresh ({hours_ago:.1f}h old)")
            else:
                st.warning(f"⚠️ Data: Stale ({hours_ago:.1f}h old)")
        else:
            st.info("ℹ️ Data: No data yet")

    with col3:
        # Check job health
        jobs = get_jobs_data()
        if not jobs.empty and "status" in jobs:
            recent_jobs = jobs.head(10)
            success_rate = (recent_jobs["status"] == "completed").mean() * 100
            if success_rate > 80:
                st.success(f"✅ Jobs: {success_rate:.0f}% success")
            elif success_rate > 50:
                st.warning(f"⚠️ Jobs: {success_rate:.0f}% success")
            else:
                st.error(f"❌ Jobs: {success_rate:.0f}% success")
        else:
            st.info("ℹ️ Jobs: No jobs yet")

    # Data statistics
    st.subheader("Data Statistics")

    politicians = get_politicians_data()
    disclosures = get_disclosures_data()
    predictions = get_predictions_data()

    stats_data = {
        "Entity": ["Politicians", "Disclosures", "Predictions", "Data Jobs"],
        "Count": [
            len(politicians),
            len(disclosures),
            len(predictions),
            len(jobs) if not jobs.empty else 0,
        ],
    }

    stats_df = pd.DataFrame(stats_data)

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(stats_df, width="stretch")

    with col2:
        fig = px.bar(stats_df, x="Entity", y="Count", title="Database Records")
        st.plotly_chart(fig, width="stretch", config={"responsive": True})


if __name__ == "__main__":
    main()
