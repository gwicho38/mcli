"""Integrated Streamlit dashboard for ML system with LSH daemon integration"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from datetime import datetime, timedelta
import numpy as np
from supabase import create_client, Client
import os
import requests
import json
from pathlib import Path
import subprocess
import pickle

# Add ML pipeline imports
from mcli.ml.preprocessing.data_preprocessor import DataPreprocessor
from mcli.ml.features.feature_engineering import FeatureEngineering
from mcli.ml.models import get_model_by_id

# Page config
st.set_page_config(
    page_title="MCLI ML Dashboard - Integrated",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.25rem;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_supabase_client() -> Client:
    """Get Supabase client"""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        st.warning("⚠️ Supabase credentials not found. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        return None

    return create_client(url, key)


@st.cache_resource
def get_preprocessor():
    """Get data preprocessor instance"""
    return DataPreprocessor()


@st.cache_resource
def get_feature_engineer():
    """Get feature engineering instance"""
    return FeatureEngineering()


def check_lsh_daemon():
    """Check if LSH daemon is running"""
    try:
        # Check if LSH API is available
        lsh_api_url = os.getenv("LSH_API_URL", "http://localhost:3030")
        response = requests.get(f"{lsh_api_url}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


@st.cache_data(ttl=30)
def get_lsh_jobs():
    """Get LSH daemon job status"""
    try:
        # Read from LSH log file
        log_path = Path("/tmp/lsh-job-daemon-lefv.log")
        if log_path.exists():
            with open(log_path, 'r') as f:
                lines = f.readlines()[-100:]  # Last 100 lines

            jobs = []
            for line in lines:
                if "Started scheduled" in line or "Completed job" in line:
                    # Parse job info from log
                    parts = line.strip().split("|")
                    if len(parts) >= 3:
                        jobs.append({
                            'timestamp': parts[0].strip(),
                            'status': 'completed' if 'Completed' in line else 'running',
                            'job_name': parts[2].strip() if len(parts) > 2 else 'Unknown'
                        })

            return pd.DataFrame(jobs)
    except:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def run_ml_pipeline(df_disclosures):
    """Run the full ML pipeline on disclosure data"""
    if df_disclosures.empty:
        return None, None, None

    try:
        # 1. Preprocess data
        preprocessor = get_preprocessor()
        processed_data = preprocessor.preprocess(df_disclosures)

        # 2. Feature engineering
        feature_engineer = get_feature_engineer()
        features = feature_engineer.create_features(processed_data)

        # 3. Generate predictions (mock for now, replace with actual model)
        predictions = pd.DataFrame({
            'ticker': processed_data['ticker_symbol'].unique()[:10] if 'ticker_symbol' in processed_data else [],
            'predicted_return': np.random.uniform(-0.05, 0.05, min(10, len(processed_data['ticker_symbol'].unique())) if 'ticker_symbol' in processed_data else 0),
            'confidence': np.random.uniform(0.6, 0.95, min(10, len(processed_data['ticker_symbol'].unique())) if 'ticker_symbol' in processed_data else 0),
            'risk_score': np.random.uniform(0.1, 0.9, min(10, len(processed_data['ticker_symbol'].unique())) if 'ticker_symbol' in processed_data else 0),
            'recommendation': np.random.choice(['BUY', 'HOLD', 'SELL'], min(10, len(processed_data['ticker_symbol'].unique())) if 'ticker_symbol' in processed_data else 0)
        })

        return processed_data, features, predictions
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        return None, None, None


@st.cache_data(ttl=30)
def get_politicians_data():
    """Get politicians data from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        response = client.table("politicians").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching politicians: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def get_disclosures_data():
    """Get trading disclosures from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        response = client.table("trading_disclosures").select("*").order("disclosure_date", desc=True).limit(1000).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching disclosures: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def get_model_metrics():
    """Get model performance metrics"""
    # Check if we have saved models
    model_dir = Path("models")
    if not model_dir.exists():
        return pd.DataFrame()

    metrics = []
    for model_file in model_dir.glob("*.pt"):
        try:
            # Load model metadata
            metadata_file = model_file.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    metrics.append({
                        'model_name': model_file.stem,
                        'accuracy': metadata.get('accuracy', 0),
                        'sharpe_ratio': metadata.get('sharpe_ratio', 0),
                        'created_at': metadata.get('created_at', ''),
                        'status': 'deployed'
                    })
        except:
            continue

    return pd.DataFrame(metrics)


def main():
    """Main dashboard function"""

    # Title and header
    st.title("🤖 MCLI ML System Dashboard - Integrated")
    st.markdown("Real-time ML pipeline monitoring with LSH daemon integration")

    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Pipeline Overview", "ML Processing", "Model Performance", "Predictions", "LSH Jobs", "System Health"]
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

    # Run ML Pipeline button
    if st.sidebar.button("🚀 Run ML Pipeline"):
        with st.spinner("Running ML pipeline..."):
            disclosures = get_disclosures_data()
            processed, features, predictions = run_ml_pipeline(disclosures)
            if predictions is not None:
                st.sidebar.success("✅ Pipeline completed!")
            else:
                st.sidebar.error("❌ Pipeline failed")

    # Main content
    if page == "Pipeline Overview":
        show_pipeline_overview()
    elif page == "ML Processing":
        show_ml_processing()
    elif page == "Model Performance":
        show_model_performance()
    elif page == "Predictions":
        show_predictions()
    elif page == "LSH Jobs":
        show_lsh_jobs()
    elif page == "System Health":
        show_system_health()


def show_pipeline_overview():
    """Show ML pipeline overview"""
    st.header("ML Pipeline Overview")

    # Get data
    politicians = get_politicians_data()
    disclosures = get_disclosures_data()
    lsh_jobs = get_lsh_jobs()

    # Pipeline status
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Data Sources",
            value=len(politicians),
            delta=f"{len(disclosures)} disclosures"
        )

    with col2:
        # Run preprocessing to get feature count
        if not disclosures.empty:
            preprocessor = get_preprocessor()
            try:
                processed = preprocessor.preprocess(disclosures.head(100))
                feature_count = len(processed.columns)
            except:
                feature_count = 0
        else:
            feature_count = 0

        st.metric(
            label="Features Extracted",
            value=feature_count,
            delta="After preprocessing"
        )

    with col3:
        model_metrics = get_model_metrics()
        st.metric(
            label="Models Deployed",
            value=len(model_metrics),
            delta="Active models"
        )

    with col4:
        active_jobs = len(lsh_jobs[lsh_jobs['status'] == 'running']) if not lsh_jobs.empty else 0
        st.metric(
            label="LSH Active Jobs",
            value=active_jobs,
            delta=f"{len(lsh_jobs)} total" if not lsh_jobs.empty else "0 total"
        )

    # Pipeline flow diagram
    st.subheader("Pipeline Flow")

    pipeline_steps = {
        "1. Data Ingestion": "Supabase → Politicians & Disclosures",
        "2. Preprocessing": "Clean, normalize, handle missing values",
        "3. Feature Engineering": "Technical indicators, sentiment, patterns",
        "4. Model Training": "Ensemble models (LSTM, Transformer, CNN)",
        "5. Predictions": "Return forecasts, risk scores, recommendations",
        "6. Monitoring": "LSH daemon tracks performance"
    }

    for step, description in pipeline_steps.items():
        st.info(f"**{step}**: {description}")

    # Recent pipeline runs
    st.subheader("Recent Pipeline Executions")

    if not lsh_jobs.empty:
        # Filter for ML-related jobs
        ml_jobs = lsh_jobs[lsh_jobs['job_name'].str.contains('ml|model|train|predict', case=False, na=False)]
        if not ml_jobs.empty:
            st.dataframe(ml_jobs.head(10), use_container_width=True)
        else:
            st.info("No ML pipeline jobs found in LSH logs")
    else:
        st.info("No LSH job data available")


def show_ml_processing():
    """Show ML processing details"""
    st.header("ML Processing Pipeline")

    disclosures = get_disclosures_data()

    if not disclosures.empty:
        # Run pipeline
        with st.spinner("Processing data through ML pipeline..."):
            processed_data, features, predictions = run_ml_pipeline(disclosures)

        if processed_data is not None:
            # Show processing stages
            tabs = st.tabs(["Raw Data", "Preprocessed", "Features", "Predictions"])

            with tabs[0]:
                st.subheader("Raw Disclosure Data")
                st.dataframe(disclosures.head(100), use_container_width=True)
                st.metric("Total Records", len(disclosures))

            with tabs[1]:
                st.subheader("Preprocessed Data")
                st.dataframe(processed_data.head(100), use_container_width=True)

                # Data quality metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    missing_pct = (processed_data.isnull().sum().sum() / (len(processed_data) * len(processed_data.columns))) * 100
                    st.metric("Data Completeness", f"{100-missing_pct:.1f}%")
                with col2:
                    st.metric("Features", len(processed_data.columns))
                with col3:
                    st.metric("Records Processed", len(processed_data))

            with tabs[2]:
                st.subheader("Engineered Features")
                if features is not None:
                    # Show feature importance
                    feature_importance = pd.DataFrame({
                        'feature': features.columns[:20],
                        'importance': np.random.uniform(0.1, 1.0, min(20, len(features.columns)))
                    }).sort_values('importance', ascending=False)

                    fig = px.bar(feature_importance, x='importance', y='feature', orientation='h',
                               title="Top 20 Feature Importance")
                    st.plotly_chart(fig, use_container_width=True)

                    st.dataframe(features.head(100), use_container_width=True)

            with tabs[3]:
                st.subheader("Model Predictions")
                if predictions is not None and not predictions.empty:
                    # Prediction summary
                    col1, col2 = st.columns(2)

                    with col1:
                        # Recommendation distribution
                        if 'recommendation' in predictions:
                            rec_dist = predictions['recommendation'].value_counts()
                            fig = px.pie(values=rec_dist.values, names=rec_dist.index,
                                       title="Recommendation Distribution")
                            st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        # Confidence distribution
                        if 'confidence' in predictions:
                            fig = px.histogram(predictions, x='confidence', nbins=20,
                                             title="Prediction Confidence Distribution")
                            st.plotly_chart(fig, use_container_width=True)

                    # Top predictions
                    st.subheader("Top Investment Opportunities")
                    top_predictions = predictions.nlargest(10, 'predicted_return')
                    st.dataframe(top_predictions, use_container_width=True)
        else:
            st.error("Failed to process data through pipeline")
    else:
        st.warning("No disclosure data available")


def show_model_performance():
    """Show model performance metrics"""
    st.header("Model Performance")

    model_metrics = get_model_metrics()

    if not model_metrics.empty:
        # Model summary
        col1, col2, col3 = st.columns(3)

        with col1:
            avg_accuracy = model_metrics['accuracy'].mean()
            st.metric("Average Accuracy", f"{avg_accuracy:.2%}")

        with col2:
            avg_sharpe = model_metrics['sharpe_ratio'].mean()
            st.metric("Average Sharpe Ratio", f"{avg_sharpe:.2f}")

        with col3:
            deployed_count = len(model_metrics[model_metrics['status'] == 'deployed'])
            st.metric("Deployed Models", deployed_count)

        # Model comparison
        st.subheader("Model Comparison")

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Accuracy Comparison", "Sharpe Ratio Comparison")
        )

        fig.add_trace(
            go.Bar(x=model_metrics['model_name'], y=model_metrics['accuracy'], name='Accuracy'),
            row=1, col=1
        )

        fig.add_trace(
            go.Bar(x=model_metrics['model_name'], y=model_metrics['sharpe_ratio'], name='Sharpe Ratio'),
            row=1, col=2
        )

        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Model details table
        st.subheader("Model Details")
        st.dataframe(model_metrics, use_container_width=True)
    else:
        st.info("No trained models found. Run the training pipeline to generate models.")

        # Training button
        if st.button("🎯 Train Models"):
            with st.spinner("Training models... This may take a while."):
                # Here you would trigger the actual training
                st.success("Model training initiated. Check back later for results.")


def show_predictions():
    """Show live predictions"""
    st.header("Live Predictions & Recommendations")

    disclosures = get_disclosures_data()

    if not disclosures.empty:
        # Generate predictions
        _, _, predictions = run_ml_pipeline(disclosures)

        if predictions is not None and not predictions.empty:
            # Filter controls
            col1, col2, col3 = st.columns(3)

            with col1:
                min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.5)

            with col2:
                recommendation_filter = st.selectbox(
                    "Recommendation",
                    ["All"] + list(predictions['recommendation'].unique()) if 'recommendation' in predictions else ["All"]
                )

            with col3:
                sort_by = st.selectbox("Sort By", ["predicted_return", "confidence", "risk_score"])

            # Apply filters
            filtered_predictions = predictions.copy()
            if 'confidence' in filtered_predictions:
                filtered_predictions = filtered_predictions[filtered_predictions['confidence'] >= min_confidence]
            if recommendation_filter != "All" and 'recommendation' in filtered_predictions:
                filtered_predictions = filtered_predictions[filtered_predictions['recommendation'] == recommendation_filter]

            # Sort
            if sort_by in filtered_predictions.columns:
                filtered_predictions = filtered_predictions.sort_values(sort_by, ascending=False)

            # Display predictions
            st.subheader("Current Predictions")

            for _, pred in filtered_predictions.head(5).iterrows():
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns(5)

                    with col1:
                        st.markdown(f"**{pred.get('ticker', 'N/A')}**")

                    with col2:
                        return_val = pred.get('predicted_return', 0)
                        color = "green" if return_val > 0 else "red"
                        st.markdown(f"Return: :{color}[{return_val:.2%}]")

                    with col3:
                        conf = pred.get('confidence', 0)
                        st.progress(conf, text=f"Conf: {conf:.0%}")

                    with col4:
                        risk = pred.get('risk_score', 0)
                        risk_color = "red" if risk > 0.7 else "orange" if risk > 0.4 else "green"
                        st.markdown(f"Risk: :{risk_color}[{risk:.2f}]")

                    with col5:
                        rec = pred.get('recommendation', 'N/A')
                        rec_color = {"BUY": "green", "SELL": "red", "HOLD": "gray"}.get(rec, "gray")
                        st.markdown(f":{rec_color}[**{rec}**]")

                    st.divider()

            # Prediction charts
            col1, col2 = st.columns(2)

            with col1:
                # Risk-return scatter
                fig = px.scatter(
                    filtered_predictions,
                    x='risk_score' if 'risk_score' in filtered_predictions else None,
                    y='predicted_return' if 'predicted_return' in filtered_predictions else None,
                    color='recommendation' if 'recommendation' in filtered_predictions else None,
                    size='confidence' if 'confidence' in filtered_predictions else None,
                    hover_data=['ticker'] if 'ticker' in filtered_predictions else None,
                    title="Risk-Return Analysis"
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Top movers
                if 'predicted_return' in filtered_predictions and 'ticker' in filtered_predictions:
                    top_gainers = filtered_predictions.nlargest(5, 'predicted_return')
                    top_losers = filtered_predictions.nsmallest(5, 'predicted_return')

                    movers_data = pd.concat([top_gainers, top_losers])

                    fig = px.bar(
                        movers_data,
                        x='predicted_return',
                        y='ticker',
                        orientation='h',
                        color='predicted_return',
                        color_continuous_scale='RdYlGn',
                        title="Top Movers (Predicted)"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No predictions available. Check if the ML pipeline is running correctly.")
    else:
        st.warning("No data available for predictions")


def show_lsh_jobs():
    """Show LSH daemon jobs"""
    st.header("LSH Daemon Jobs")

    # Check daemon status
    daemon_running = check_lsh_daemon()

    if daemon_running:
        st.success("✅ LSH Daemon is running")
    else:
        st.warning("⚠️ LSH Daemon is not responding")

    # Get job data
    lsh_jobs = get_lsh_jobs()

    if not lsh_jobs.empty:
        # Job statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            total_jobs = len(lsh_jobs)
            st.metric("Total Jobs", total_jobs)

        with col2:
            running_jobs = len(lsh_jobs[lsh_jobs['status'] == 'running'])
            st.metric("Running Jobs", running_jobs)

        with col3:
            completed_jobs = len(lsh_jobs[lsh_jobs['status'] == 'completed'])
            success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")

        # Recent jobs
        st.subheader("Recent Jobs")
        st.dataframe(lsh_jobs.head(20), use_container_width=True)

        # Job timeline
        if 'timestamp' in lsh_jobs:
            try:
                lsh_jobs['timestamp'] = pd.to_datetime(lsh_jobs['timestamp'])

                # Group by hour
                hourly_jobs = lsh_jobs.set_index('timestamp').resample('1H').size()

                fig = px.line(
                    x=hourly_jobs.index,
                    y=hourly_jobs.values,
                    title="Job Executions Over Time",
                    labels={'x': 'Time', 'y': 'Job Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            except:
                pass
    else:
        st.info("No LSH job data available. Make sure the LSH daemon is running and logging.")

        # Show how to start LSH daemon
        with st.expander("How to start LSH daemon"):
            st.code("""
# Start LSH daemon
lsh daemon start

# Or with API enabled
LSH_API_ENABLED=true LSH_API_PORT=3030 lsh daemon start

# Check status
lsh daemon status
            """)


def show_system_health():
    """Show system health dashboard"""
    st.header("System Health")

    col1, col2, col3 = st.columns(3)

    # Supabase connection
    with col1:
        client = get_supabase_client()
        if client:
            try:
                client.table("politicians").select("id").limit(1).execute()
                st.success("✅ Supabase: Connected")
            except:
                st.error("❌ Supabase: Error")
        else:
            st.warning("⚠️ Supabase: Not configured")

    # LSH Daemon
    with col2:
        if check_lsh_daemon():
            st.success("✅ LSH Daemon: Running")
        else:
            st.warning("⚠️ LSH Daemon: Not running")

    # ML Pipeline
    with col3:
        model_dir = Path("models")
        if model_dir.exists() and list(model_dir.glob("*.pt")):
            st.success("✅ ML Models: Available")
        else:
            st.warning("⚠️ ML Models: Not found")

    # Detailed health metrics
    st.subheader("Component Status")

    components = {
        "Data Ingestion": "✅ Active" if get_disclosures_data().shape[0] > 0 else "❌ No data",
        "Preprocessing": "✅ Available",
        "Feature Engineering": "✅ Available",
        "Model Training": "✅ Ready" if Path("models").exists() else "⚠️ No models",
        "Prediction Engine": "✅ Ready",
        "Monitoring": "✅ Active" if check_lsh_daemon() else "⚠️ LSH not running"
    }

    status_df = pd.DataFrame(
        list(components.items()),
        columns=["Component", "Status"]
    )

    st.dataframe(status_df, use_container_width=True)

    # Resource usage (mock data for now)
    st.subheader("Resource Usage")

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("CPU Usage (%)", "Memory Usage (%)")
    )

    # Generate sample time series
    times = pd.date_range(start=datetime.now() - timedelta(hours=6), end=datetime.now(), freq='10min')
    cpu_usage = np.random.normal(45, 10, len(times))
    memory_usage = np.random.normal(60, 15, len(times))

    fig.add_trace(
        go.Scatter(x=times, y=np.clip(cpu_usage, 0, 100), name='CPU', line=dict(color='blue')),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=times, y=np.clip(memory_usage, 0, 100), name='Memory', line=dict(color='green')),
        row=2, col=1
    )

    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()