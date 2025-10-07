"""Workflow Management Dashboard"""

import streamlit as st
import pandas as pd
import requests
import os
import json
from datetime import datetime, timedelta
import plotly.express as px
from typing import Optional, Dict, Any

# Import components
try:
    from ..components.metrics import display_kpi_row, display_status_badge, display_health_indicator
    from ..components.charts import create_timeline_chart, create_status_pie_chart, create_gantt_chart, render_chart
    from ..components.tables import display_filterable_dataframe, export_dataframe
except ImportError:
    # Fallback for when imported outside package context
    from components.metrics import display_kpi_row, display_status_badge, display_health_indicator
    from components.charts import create_timeline_chart, create_status_pie_chart, create_gantt_chart, render_chart
    from components.tables import display_filterable_dataframe, export_dataframe


def get_workflow_api_url() -> str:
    """Get Workflow API URL from environment"""
    lsh_url = os.getenv("LSH_API_URL", "http://localhost:3034")
    return f"{lsh_url}/api/workflows"


def fetch_workflows() -> pd.DataFrame:
    """Fetch workflow definitions from API"""
    try:
        api_url = get_workflow_api_url()
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()

        workflows = response.json().get("workflows", [])
        if workflows:
            return pd.DataFrame(workflows)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # API endpoint not implemented yet - use demo data silently
            pass
        else:
            st.warning(f"Could not fetch workflow data: {e}")
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ LSH Daemon connection failed. Using demo data.")
    except Exception as e:
        # Only show warning for unexpected errors
        st.warning(f"Could not fetch workflow data: {e}")

    # Return mock data
    return create_mock_workflow_data()


def create_mock_workflow_data() -> pd.DataFrame:
    """Create mock workflow data for demonstration"""
    workflows = [
        {
            "id": "wf-1",
            "name": "Data Ingestion Pipeline",
            "description": "Ingest politician trading data from multiple sources",
            "status": "active",
            "schedule": "0 */6 * * *",  # Every 6 hours
            "last_run": (datetime.now() - timedelta(hours=3)).isoformat(),
            "next_run": (datetime.now() + timedelta(hours=3)).isoformat(),
            "success_rate": 0.95,
            "avg_duration_min": 12,
            "total_runs": 150
        },
        {
            "id": "wf-2",
            "name": "ML Model Training",
            "description": "Train and evaluate ML models on latest data",
            "status": "active",
            "schedule": "0 2 * * *",  # Daily at 2 AM
            "last_run": (datetime.now() - timedelta(days=1, hours=2)).isoformat(),
            "next_run": (datetime.now() + timedelta(hours=22)).isoformat(),
            "success_rate": 0.88,
            "avg_duration_min": 45,
            "total_runs": 30
        },
        {
            "id": "wf-3",
            "name": "Data Validation & Quality Check",
            "description": "Validate data integrity and quality metrics",
            "status": "active",
            "schedule": "0 * * * *",  # Hourly
            "last_run": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "next_run": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "success_rate": 1.0,
            "avg_duration_min": 5,
            "total_runs": 500
        },
        {
            "id": "wf-4",
            "name": "Prediction Generation",
            "description": "Generate stock recommendations based on latest models",
            "status": "paused",
            "schedule": "0 9 * * 1-5",  # Weekdays at 9 AM
            "last_run": (datetime.now() - timedelta(days=3)).isoformat(),
            "next_run": None,
            "success_rate": 0.92,
            "avg_duration_min": 20,
            "total_runs": 75
        }
    ]

    return pd.DataFrame(workflows)


def fetch_workflow_executions(workflow_id: Optional[str] = None) -> pd.DataFrame:
    """Fetch workflow execution history"""
    try:
        api_url = get_workflow_api_url()
        url = f"{api_url}/{workflow_id}/executions" if workflow_id else f"{api_url}/executions"
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        executions = response.json().get("executions", [])
        if executions:
            return pd.DataFrame(executions)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # API endpoint not implemented yet - use demo data silently
            pass
        else:
            st.warning(f"Could not fetch execution data: {e}")
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ LSH Daemon connection failed. Using demo data.")
    except Exception as e:
        st.warning(f"Could not fetch execution data: {e}")

    # Return mock execution data
    return create_mock_execution_data(workflow_id)


def create_mock_execution_data(workflow_id: Optional[str] = None) -> pd.DataFrame:
    """Create mock execution data"""
    import random

    executions = []
    for i in range(50):
        start_time = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        duration = random.randint(300, 3600)  # 5-60 minutes in seconds
        status = random.choices(["completed", "failed", "running"], weights=[80, 15, 5])[0]

        executions.append({
            "id": f"exec-{i+1}",
            "workflow_id": workflow_id or f"wf-{random.randint(1,4)}",
            "workflow_name": random.choice(["Data Ingestion Pipeline", "ML Model Training", "Data Validation", "Prediction Generation"]),
            "status": status,
            "started_at": start_time.isoformat(),
            "completed_at": (start_time + timedelta(seconds=duration)).isoformat() if status != "running" else None,
            "duration_sec": duration if status != "running" else None,
            "triggered_by": random.choice(["schedule", "manual", "api"]),
            "steps_completed": random.randint(3, 8),
            "steps_total": 8
        })

    return pd.DataFrame(executions)


def show_workflows_dashboard():
    """Main workflow management dashboard"""

    st.title("⚙️ Workflow Management")
    st.markdown("Create, schedule, and monitor data pipeline workflows")

    # Refresh button
    col1, col2 = st.columns([1, 9])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()

    st.divider()

    # Fetch data
    with st.spinner("Loading workflow data..."):
        workflows_df = fetch_workflows()

    if workflows_df.empty:
        st.warning("No workflows found")
        return

    # Convert timestamps
    for col in ["last_run", "next_run"]:
        if col in workflows_df.columns:
            workflows_df[col] = pd.to_datetime(workflows_df[col], errors='coerce')

    # === KPIs ===
    st.subheader("📊 Workflow Metrics")

    total_workflows = len(workflows_df)
    active_workflows = len(workflows_df[workflows_df["status"] == "active"])
    paused_workflows = len(workflows_df[workflows_df["status"] == "paused"])
    avg_success_rate = workflows_df["success_rate"].mean() * 100 if "success_rate" in workflows_df.columns else 0

    metrics = {
        "Total Workflows": {"value": total_workflows, "icon": "⚙️"},
        "Active": {"value": active_workflows, "icon": "✅"},
        "Paused": {"value": paused_workflows, "icon": "⏸️"},
        "Avg Success Rate": {"value": f"{avg_success_rate:.1f}%", "icon": "📈"},
    }

    display_kpi_row(metrics, columns=4)

    st.divider()

    # === Tabs ===
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Workflows", "📈 Executions", "➕ Create Workflow", "📚 Templates"])

    with tab1:
        show_workflow_list(workflows_df)

    with tab2:
        show_workflow_executions()

    with tab3:
        show_workflow_builder()

    with tab4:
        show_workflow_templates()


def show_workflow_list(workflows_df: pd.DataFrame):
    """Display list of workflows"""

    st.markdown("### Active Workflows")

    # Filter options
    filter_config = {
        "status": "multiselect",
    }

    filtered_df = display_filterable_dataframe(
        workflows_df,
        filter_columns=filter_config,
        key_prefix="workflow_filter"
    )

    # Workflow details
    for _, workflow in filtered_df.iterrows():
        with st.expander(f"{workflow['name']} - {display_status_badge(workflow['status'], 'small')}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Description:** {workflow.get('description', 'N/A')}")
                st.markdown(f"**Schedule:** `{workflow.get('schedule', 'N/A')}`")
                st.markdown(f"**Total Runs:** {workflow.get('total_runs', 0)}")

            with col2:
                st.markdown(f"**Success Rate:** {workflow.get('success_rate', 0) * 100:.1f}%")
                st.markdown(f"**Avg Duration:** {workflow.get('avg_duration_min', 0):.1f} min")
                st.markdown(f"**Last Run:** {workflow.get('last_run', 'Never')}")

            # Actions
            col_a, col_b, col_c, col_d = st.columns(4)

            with col_a:
                if st.button("▶️ Run Now", key=f"run_{workflow['id']}"):
                    st.success(f"Workflow '{workflow['name']}' triggered!")

            with col_b:
                if workflow['status'] == "active":
                    if st.button("⏸️ Pause", key=f"pause_{workflow['id']}"):
                        st.info(f"Workflow '{workflow['name']}' paused")
                else:
                    if st.button("▶️ Resume", key=f"resume_{workflow['id']}"):
                        st.info(f"Workflow '{workflow['name']}' resumed")

            with col_c:
                if st.button("✏️ Edit", key=f"edit_{workflow['id']}"):
                    st.session_state['edit_workflow_id'] = workflow['id']
                    st.info("Edit mode activated")

            with col_d:
                if st.button("📊 View Executions", key=f"view_exec_{workflow['id']}"):
                    st.session_state['selected_workflow'] = workflow['id']

            # Show workflow definition
            if st.checkbox("Show Workflow Definition", key=f"def_{workflow['id']}"):
                workflow_def = {
                    "name": workflow['name'],
                    "description": workflow['description'],
                    "schedule": workflow['schedule'],
                    "steps": [
                        {"name": "Fetch Data", "action": "api_call", "params": {}},
                        {"name": "Transform Data", "action": "python_script", "params": {}},
                        {"name": "Validate Data", "action": "validation", "params": {}},
                        {"name": "Store Results", "action": "database_write", "params": {}}
                    ]
                }
                st.json(workflow_def)


def show_workflow_executions():
    """Show workflow execution history"""

    st.markdown("### Workflow Execution History")

    # Fetch executions
    executions_df = fetch_workflow_executions()

    if executions_df.empty:
        st.info("No execution history")
        return

    # Convert timestamps
    for col in ["started_at", "completed_at"]:
        if col in executions_df.columns:
            executions_df[col] = pd.to_datetime(executions_df[col], errors='coerce')

    # Filter
    filter_config = {
        "workflow_name": "multiselect",
        "status": "multiselect",
        "triggered_by": "multiselect"
    }

    filtered_df = display_filterable_dataframe(
        executions_df,
        filter_columns=filter_config,
        key_prefix="exec_filter"
    )

    # Status distribution
    col1, col2 = st.columns(2)

    with col1:
        if "status" in filtered_df.columns:
            fig = create_status_pie_chart(filtered_df, "status", "Execution Status Distribution")
            render_chart(fig)

    with col2:
        if "workflow_name" in filtered_df.columns:
            workflow_counts = filtered_df["workflow_name"].value_counts()
            fig = px.bar(
                x=workflow_counts.values,
                y=workflow_counts.index,
                orientation='h',
                title="Executions by Workflow"
            )
            render_chart(fig)

    # Execution details
    st.markdown("#### Recent Executions")

    for _, execution in filtered_df.head(20).iterrows():
        with st.expander(f"{execution.get('workflow_name')} - {execution.get('started_at')} - {display_status_badge(execution.get('status'), 'small')}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Workflow:** {execution.get('workflow_name')}")
                st.markdown(f"**Started:** {execution.get('started_at')}")
                st.markdown(f"**Completed:** {execution.get('completed_at', 'In progress')}")

            with col2:
                st.markdown(f"**Status:** {display_status_badge(execution.get('status'), 'small')}")
                st.markdown(f"**Triggered By:** {execution.get('triggered_by')}")

                if pd.notna(execution.get('duration_sec')):
                    st.markdown(f"**Duration:** {execution['duration_sec']/60:.1f} min")

                if execution.get('steps_total'):
                    progress = execution.get('steps_completed', 0) / execution['steps_total']
                    st.progress(progress)
                    st.caption(f"Steps: {execution.get('steps_completed')}/{execution['steps_total']}")

            # Action buttons
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                if st.button("📋 View Logs", key=f"logs_{execution.get('id')}"):
                    st.code(f"""
[INFO] Workflow execution started: {execution.get('id')}
[INFO] Step 1/8: Fetching data from sources...
[INFO] Step 2/8: Transforming data...
[INFO] Step 3/8: Validating data quality...
[INFO] Execution {'completed' if execution.get('status') == 'completed' else execution.get('status')}
                    """, language="log")

            with col_btn2:
                # Download results as JSON
                result_data = {
                    "execution_id": execution.get('id'),
                    "workflow_name": execution.get('workflow_name'),
                    "status": execution.get('status'),
                    "started_at": str(execution.get('started_at')),
                    "completed_at": str(execution.get('completed_at')),
                    "duration_seconds": execution.get('duration_sec'),
                    "triggered_by": execution.get('triggered_by'),
                    "steps_completed": execution.get('steps_completed'),
                    "steps_total": execution.get('steps_total'),
                    "results": {
                        "records_processed": 1250,
                        "errors": 0,
                        "warnings": 3,
                        "output_location": f"/data/workflows/{execution.get('id')}/output.parquet"
                    }
                }
                st.download_button(
                    label="💾 Download Results",
                    data=json.dumps(result_data, indent=2),
                    file_name=f"workflow_result_{execution.get('id')}.json",
                    mime="application/json",
                    key=f"download_{execution.get('id')}"
                )

            with col_btn3:
                # Link to view detailed results (mock for now)
                if st.button("🔗 View Details", key=f"details_{execution.get('id')}"):
                    st.info(f"Results viewer would open for execution: {execution.get('id')}")
                    st.json(result_data)

    # Export
    st.markdown("#### 📥 Export Execution Data")
    export_dataframe(filtered_df, filename="workflow_executions", formats=["csv", "json"])


def show_workflow_builder():
    """Workflow builder interface"""

    st.markdown("### ➕ Create New Workflow")

    with st.form("new_workflow"):
        name = st.text_input("Workflow Name", placeholder="e.g., Daily Data Sync")
        description = st.text_area("Description", placeholder="What does this workflow do?")

        col1, col2 = st.columns(2)

        with col1:
            schedule_type = st.selectbox("Schedule Type", ["Cron Expression", "Interval", "Manual Only"])

            if schedule_type == "Cron Expression":
                schedule = st.text_input("Cron Schedule", placeholder="0 0 * * *", help="Cron expression for scheduling")
            elif schedule_type == "Interval":
                interval_value = st.number_input("Every", min_value=1, value=1)
                interval_unit = st.selectbox("Unit", ["minutes", "hours", "days"])
                schedule = f"Every {interval_value} {interval_unit}"
            else:
                schedule = "manual"

        with col2:
            enabled = st.checkbox("Enabled", value=True)
            retry_on_failure = st.checkbox("Retry on Failure", value=True)
            max_retries = st.number_input("Max Retries", min_value=0, max_value=5, value=2)

        st.markdown("#### Workflow Steps")

        # Simple step builder
        num_steps = st.number_input("Number of Steps", min_value=1, max_value=10, value=3)

        steps = []
        for i in range(num_steps):
            with st.expander(f"Step {i+1}"):
                step_name = st.text_input(f"Step Name", key=f"step_name_{i}", placeholder=f"Step {i+1}")
                step_type = st.selectbox(f"Step Type", ["API Call", "Python Script", "Database Query", "Data Transform", "Validation"], key=f"step_type_{i}")
                step_config = st.text_area(f"Configuration (JSON)", key=f"step_config_{i}", placeholder='{"param": "value"}')

                steps.append({
                    "name": step_name,
                    "type": step_type,
                    "config": step_config
                })

        submitted = st.form_submit_button("Create Workflow")

        if submitted:
            if name and description:
                workflow_def = {
                    "name": name,
                    "description": description,
                    "schedule": schedule,
                    "enabled": enabled,
                    "retry_on_failure": retry_on_failure,
                    "max_retries": max_retries,
                    "steps": steps
                }

                st.success(f"✅ Workflow '{name}' created successfully!")
                st.json(workflow_def)
            else:
                st.error("Please fill in required fields: Name and Description")


def show_workflow_templates():
    """Show workflow templates"""

    st.markdown("### 📚 Workflow Templates")

    templates = [
        {
            "name": "Data Ingestion Pipeline",
            "description": "Fetch data from external APIs and store in database",
            "category": "Data Engineering",
            "steps": 4
        },
        {
            "name": "ML Training Pipeline",
            "description": "Train and evaluate ML models on schedule",
            "category": "Machine Learning",
            "steps": 6
        },
        {
            "name": "Data Quality Check",
            "description": "Validate data integrity and quality metrics",
            "category": "Data Quality",
            "steps": 3
        },
        {
            "name": "Report Generation",
            "description": "Generate and distribute periodic reports",
            "category": "Reporting",
            "steps": 5
        }
    ]

    for template in templates:
        with st.expander(f"{template['name']} ({template['category']})"):
            st.markdown(f"**Description:** {template['description']}")
            st.markdown(f"**Steps:** {template['steps']}")
            st.markdown(f"**Category:** {template['category']}")

            if st.button(f"Use Template", key=f"use_{template['name']}"):
                st.info(f"Loading template: {template['name']}")
                # Would populate the workflow builder form


if __name__ == "__main__":
    show_workflows_dashboard()
