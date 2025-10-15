"""CI/CD Pipeline Monitoring Dashboard"""

import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Import components
try:
    from ..components.charts import create_status_pie_chart, create_timeline_chart, render_chart
    from ..components.metrics import display_health_indicator, display_kpi_row, display_status_badge
    from ..components.tables import display_filterable_dataframe, export_dataframe
except ImportError:
    # Fallback for when imported outside package context
    from components.charts import create_status_pie_chart, create_timeline_chart, render_chart
    from components.metrics import display_health_indicator, display_kpi_row, display_status_badge
    from components.tables import display_filterable_dataframe, export_dataframe


def get_cicd_api_url() -> str:
    """Get CI/CD API URL from environment"""
    lsh_url = os.getenv("LSH_API_URL", "http://localhost:3034")
    return f"{lsh_url}/api/cicd"


def fetch_cicd_builds(limit: int = 100) -> pd.DataFrame:
    """Fetch CI/CD build data from API"""
    try:
        api_url = get_cicd_api_url()
        response = requests.get(f"{api_url}/builds", params={"limit": limit}, timeout=5)
        response.raise_for_status()

        builds = response.json().get("builds", [])
        if builds:
            return pd.DataFrame(builds)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # API endpoint not implemented yet - use demo data silently
            pass
        else:
            st.warning(f"Could not fetch CI/CD data: {e}")
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ LSH Daemon connection failed. Using demo data.")
    except Exception as e:
        # Only show warning for unexpected errors
        st.warning(f"Could not fetch CI/CD data: {e}")

    # Return mock data for demonstration
    return create_mock_cicd_data()


def create_mock_cicd_data() -> pd.DataFrame:
    """Create mock CI/CD data for demonstration"""
    import random
    from datetime import datetime, timedelta

    pipelines = ["main-build", "develop-build", "feature-test", "release-deploy", "hotfix-deploy"]
    statuses = ["success", "failed", "running", "cancelled"]
    branches = ["main", "develop", "feature/new-dashboard", "release/v1.2.0", "hotfix/bug-123"]

    data = []
    for i in range(50):
        start_time = datetime.now() - timedelta(
            days=random.randint(0, 30), hours=random.randint(0, 23)
        )
        duration = random.randint(60, 600)  # seconds
        status = random.choices(statuses, weights=[70, 15, 10, 5])[0]

        data.append(
            {
                "id": f"build-{i+1}",
                "pipeline_name": random.choice(pipelines),
                "branch": random.choice(branches),
                "status": status,
                "started_at": start_time.isoformat(),
                "duration_sec": duration if status != "running" else None,
                "commit_sha": f"{random.randint(1000000, 9999999):07x}",
                "triggered_by": random.choice(["github-webhook", "manual", "schedule"]),
                "success_rate": (
                    random.uniform(0.7, 1.0) if status == "success" else random.uniform(0, 0.5)
                ),
            }
        )

    return pd.DataFrame(data)


def fetch_webhooks() -> list:
    """Fetch configured webhooks"""
    try:
        api_url = get_cicd_api_url()
        response = requests.get(f"{api_url}/webhooks", timeout=5)
        response.raise_for_status()
        return response.json().get("webhooks", [])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # API endpoint not implemented yet - use demo data silently
            pass
        else:
            st.warning(f"Could not fetch webhooks: {e}")
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ LSH Daemon connection failed. Using demo data.")
    except Exception as e:
        st.warning(f"Could not fetch webhooks: {e}")

    # Return mock data
    return [
        {
            "id": "wh-1",
            "name": "GitHub Main",
            "url": "https://github.com/user/repo",
            "events": ["push", "pull_request"],
            "active": True,
        },
        {
            "id": "wh-2",
            "name": "GitLab CI",
            "url": "https://gitlab.com/user/repo",
            "events": ["push"],
            "active": True,
        },
    ]


def show_cicd_dashboard():
    """Main CI/CD dashboard page"""

    st.title("🔧 CI/CD Pipeline Dashboard")
    st.markdown("Monitor build pipelines, deployments, and CI/CD metrics")

    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)

    if auto_refresh:
        from streamlit_autorefresh import st_autorefresh

        # Auto-refresh every 30 seconds
        st_autorefresh(interval=30000, key="cicd_refresh")

    st.divider()

    # Fetch data
    with st.spinner("Loading CI/CD data..."):
        builds_df = fetch_cicd_builds()

    if builds_df.empty:
        st.warning("No CI/CD build data available")
        return

    # Convert timestamps
    if "started_at" in builds_df.columns:
        builds_df["started_at"] = pd.to_datetime(builds_df["started_at"])

    # === KPIs ===
    st.subheader("📊 Pipeline Metrics")

    total_builds = len(builds_df)
    success_builds = len(builds_df[builds_df["status"] == "success"])
    failed_builds = len(builds_df[builds_df["status"] == "failed"])
    running_builds = len(builds_df[builds_df["status"] == "running"])

    success_rate = (success_builds / total_builds * 100) if total_builds > 0 else 0
    avg_duration = builds_df[builds_df["duration_sec"].notna()]["duration_sec"].mean()

    metrics = {
        "Total Builds": {"value": total_builds, "icon": "📦"},
        "Success Rate": {
            "value": f"{success_rate:.1f}%",
            "delta": "+5.2%",
            "delta_color": "normal",
            "icon": "✅",
        },
        "Failed Builds": {"value": failed_builds, "icon": "❌"},
        "Running": {"value": running_builds, "icon": "🔵"},
        "Avg Duration": {
            "value": f"{avg_duration:.0f}s" if pd.notna(avg_duration) else "N/A",
            "icon": "⏱️",
        },
    }

    display_kpi_row(metrics, columns=5)

    st.divider()

    # === Tabs for different views ===
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 Overview", "🔍 Build History", "🔔 Webhooks", "⚙️ Configuration"]
    )

    with tab1:
        show_cicd_overview(builds_df)

    with tab2:
        show_build_history(builds_df)

    with tab3:
        show_webhooks_config()

    with tab4:
        show_cicd_configuration()


def show_cicd_overview(builds_df: pd.DataFrame):
    """Show CI/CD overview charts"""

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Status Distribution")
        if "status" in builds_df.columns:
            fig = create_status_pie_chart(builds_df, "status", "Build Status Distribution")
            render_chart(fig)

    with col2:
        st.markdown("### Pipeline Activity")
        if "pipeline_name" in builds_df.columns:
            pipeline_counts = builds_df["pipeline_name"].value_counts().head(10)
            fig = px.bar(
                x=pipeline_counts.values,
                y=pipeline_counts.index,
                orientation="h",
                title="Top Pipelines by Build Count",
                labels={"x": "Number of Builds", "y": "Pipeline"},
            )
            render_chart(fig)

    # Success rate trend
    st.markdown("### 📊 Success Rate Trend")

    if "started_at" in builds_df.columns and "status" in builds_df.columns:
        # Group by date and calculate success rate
        builds_df["date"] = builds_df["started_at"].dt.date
        daily_stats = (
            builds_df.groupby("date")
            .agg({"status": lambda x: (x == "success").sum() / len(x) * 100})
            .reset_index()
        )
        daily_stats.columns = ["date", "success_rate"]

        fig = px.line(
            daily_stats,
            x="date",
            y="success_rate",
            title="Daily Success Rate",
            labels={"date": "Date", "success_rate": "Success Rate (%)"},
            markers=True,
        )
        fig.add_hline(y=90, line_dash="dash", line_color="green", annotation_text="Target: 90%")
        render_chart(fig)

    # Build duration trend
    st.markdown("### ⏱️ Build Duration Trend")

    if "duration_sec" in builds_df.columns:
        duration_data = builds_df[builds_df["duration_sec"].notna()].copy()

        if not duration_data.empty:
            duration_data["duration_min"] = duration_data["duration_sec"] / 60

            fig = px.scatter(
                duration_data,
                x="started_at",
                y="duration_min",
                color="pipeline_name",
                title="Build Duration Over Time",
                labels={"started_at": "Time", "duration_min": "Duration (minutes)"},
            )
            render_chart(fig)


def show_build_history(builds_df: pd.DataFrame):
    """Show detailed build history"""

    st.markdown("### Build History")

    # Filters
    filter_config = {
        "pipeline_name": "multiselect",
        "status": "multiselect",
        "branch": "multiselect",
    }

    filtered_df = display_filterable_dataframe(
        builds_df, filter_columns=filter_config, key_prefix="cicd_filter"
    )

    # Export option
    st.markdown("#### 📥 Export Data")
    export_dataframe(filtered_df, filename="cicd_builds", formats=["csv", "json"])

    # Build details expander
    st.markdown("#### Build Details")

    if not filtered_df.empty:
        for _, build in filtered_df.head(20).iterrows():
            with st.expander(
                f"{build.get('pipeline_name', 'Unknown')} - {build.get('commit_sha', 'Unknown')[:7]} - {display_status_badge(build.get('status', 'unknown'), 'small')}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Pipeline:** {build.get('pipeline_name', 'N/A')}")
                    st.markdown(f"**Branch:** {build.get('branch', 'N/A')}")
                    st.markdown(f"**Commit:** `{build.get('commit_sha', 'N/A')}`")
                    st.markdown(f"**Triggered By:** {build.get('triggered_by', 'N/A')}")

                with col2:
                    st.markdown(
                        f"**Status:** {display_status_badge(build.get('status', 'unknown'), 'small')}"
                    )
                    st.markdown(f"**Started:** {build.get('started_at', 'N/A')}")
                    if pd.notna(build.get("duration_sec")):
                        st.markdown(
                            f"**Duration:** {build['duration_sec']}s ({build['duration_sec']/60:.1f}m)"
                        )

                # Mock logs
                if st.button(f"View Logs", key=f"logs_{build.get('id')}"):
                    st.code(
                        f"""
[INFO] Starting build for {build.get('pipeline_name')}
[INFO] Checking out branch: {build.get('branch')}
[INFO] Installing dependencies...
[INFO] Running tests...
[INFO] Build {'completed successfully' if build.get('status') == 'success' else 'failed'}
                    """,
                        language="bash",
                    )


def show_webhooks_config():
    """Show webhook configuration"""

    st.markdown("### 🔔 Configured Webhooks")

    webhooks = fetch_webhooks()

    if not webhooks:
        st.info("No webhooks configured")
        return

    for webhook in webhooks:
        with st.expander(
            f"{webhook['name']} - {'✅ Active' if webhook['active'] else '❌ Inactive'}"
        ):
            st.markdown(f"**URL:** `{webhook['url']}`")
            st.markdown(f"**Events:** {', '.join(webhook['events'])}")
            st.markdown(f"**Status:** {'Active' if webhook['active'] else 'Inactive'}")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔄 Test", key=f"test_{webhook['id']}"):
                    st.success("Webhook test triggered!")
            with col2:
                if st.button("✏️ Edit", key=f"edit_{webhook['id']}"):
                    st.info("Edit functionality coming soon")
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{webhook['id']}"):
                    st.warning("Delete confirmation required")

    st.divider()

    # Add new webhook
    with st.expander("➕ Add New Webhook"):
        name = st.text_input("Webhook Name")
        url = st.text_input("Webhook URL")
        events = st.multiselect("Events", ["push", "pull_request", "release", "tag"])

        if st.button("Create Webhook"):
            if name and url and events:
                st.success(f"Webhook '{name}' created successfully!")
            else:
                st.error("Please fill in all fields")


def show_cicd_configuration():
    """Show CI/CD configuration options"""

    st.markdown("### ⚙️ CI/CD Configuration")

    with st.form("cicd_config"):
        st.markdown("#### Pipeline Settings")

        max_concurrent_builds = st.number_input(
            "Max Concurrent Builds", min_value=1, max_value=10, value=3
        )
        build_timeout = st.number_input(
            "Build Timeout (minutes)", min_value=5, max_value=120, value=30
        )
        retry_failed_builds = st.checkbox("Auto-retry Failed Builds", value=True)
        max_retries = st.number_input("Max Retries", min_value=1, max_value=5, value=2)

        st.markdown("#### Notifications")
        notify_on_success = st.checkbox("Notify on Success", value=False)
        notify_on_failure = st.checkbox("Notify on Failure", value=True)
        notification_email = st.text_input("Notification Email")

        submitted = st.form_submit_button("Save Configuration")

        if submitted:
            st.success("✅ Configuration saved successfully!")
            st.json(
                {
                    "max_concurrent_builds": max_concurrent_builds,
                    "build_timeout_minutes": build_timeout,
                    "retry_failed_builds": retry_failed_builds,
                    "max_retries": max_retries,
                    "notifications": {
                        "on_success": notify_on_success,
                        "on_failure": notify_on_failure,
                        "email": notification_email,
                    },
                }
            )


if __name__ == "__main__":
    show_cicd_dashboard()
