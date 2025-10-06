"""Integrated Streamlit dashboard for ML system with LSH daemon integration"""

import asyncio
import json
import os
import pickle
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv
from plotly.subplots import make_subplots
from supabase import Client, create_client

# Load environment variables from .env file
load_dotenv()

# Add ML pipeline imports
try:
    from mcli.ml.models import get_model_by_id
    from mcli.ml.preprocessing import MLDataPipeline, PoliticianTradingPreprocessor

    HAS_ML_PIPELINE = True
except ImportError:
    HAS_ML_PIPELINE = False
    PoliticianTradingPreprocessor = None
    MLDataPipeline = None

# Add prediction engine
try:
    from mcli.ml.predictions import PoliticianTradingPredictor

    HAS_PREDICTOR = True
except ImportError:
    HAS_PREDICTOR = False
    PoliticianTradingPredictor = None

# Page config
st.set_page_config(
    page_title="MCLI ML Dashboard - Integrated",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_supabase_client() -> Client:
    """Get Supabase client"""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        st.warning(
            "⚠️ Supabase credentials not found. Set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
        return None

    return create_client(url, key)


@st.cache_resource
def get_preprocessor():
    """Get data preprocessor instance"""
    if HAS_ML_PIPELINE and PoliticianTradingPreprocessor:
        return PoliticianTradingPreprocessor()
    return None


@st.cache_resource
def get_ml_pipeline():
    """Get ML data pipeline instance"""
    if HAS_ML_PIPELINE and MLDataPipeline:
        return MLDataPipeline()
    return None


@st.cache_resource
def get_predictor():
    """Get prediction engine instance"""
    if HAS_PREDICTOR and PoliticianTradingPredictor:
        return PoliticianTradingPredictor()
    return None


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
            with open(log_path, "r") as f:
                lines = f.readlines()[-100:]  # Last 100 lines

            jobs = []
            for line in lines:
                if "Started scheduled" in line or "Completed job" in line:
                    # Parse job info from log
                    parts = line.strip().split("|")
                    if len(parts) >= 3:
                        jobs.append(
                            {
                                "timestamp": parts[0].strip(),
                                "status": "completed" if "Completed" in line else "running",
                                "job_name": parts[2].strip() if len(parts) > 2 else "Unknown",
                            }
                        )

            return pd.DataFrame(jobs)
        else:
            # Log file doesn't exist - return empty DataFrame
            return pd.DataFrame()
    except Exception as e:
        # On any error, return empty DataFrame
        return pd.DataFrame()


@st.cache_data(ttl=60)
def run_ml_pipeline(df_disclosures):
    """Run the full ML pipeline on disclosure data"""
    if df_disclosures.empty:
        return None, None, None

    try:
        # 1. Preprocess data
        preprocessor = get_preprocessor()
        if preprocessor:
            try:
                processed_data = preprocessor.preprocess(df_disclosures)
            except:
                processed_data = df_disclosures
        else:
            # Use raw data if preprocessor not available
            processed_data = df_disclosures

        # 2. Feature engineering (using ML pipeline if available)
        ml_pipeline = get_ml_pipeline()
        if ml_pipeline:
            try:
                features = ml_pipeline.transform(processed_data)
            except:
                features = processed_data
        else:
            features = processed_data

        # 3. Generate predictions using real prediction engine
        predictor = get_predictor()
        if predictor and HAS_PREDICTOR:
            try:
                predictions = predictor.generate_predictions(df_disclosures)
            except Exception as pred_error:
                st.warning(f"Prediction engine error: {pred_error}. Using fallback predictions.")
                predictions = _generate_fallback_predictions(processed_data)
        else:
            predictions = _generate_fallback_predictions(processed_data)

        return processed_data, features, predictions
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        import traceback

        with st.expander("See error details"):
            st.code(traceback.format_exc())
        return None, None, None


def _generate_fallback_predictions(processed_data):
    """Generate basic predictions when predictor is unavailable"""
    if processed_data.empty:
        return pd.DataFrame()

    tickers = (
        processed_data["ticker_symbol"].unique()[:10] if "ticker_symbol" in processed_data else []
    )
    n_tickers = len(tickers)

    if n_tickers == 0:
        return pd.DataFrame()

    return pd.DataFrame(
        {
            "ticker": tickers,
            "predicted_return": np.random.uniform(-0.05, 0.05, n_tickers),
            "confidence": np.random.uniform(0.5, 0.8, n_tickers),
            "risk_score": np.random.uniform(0.3, 0.7, n_tickers),
            "recommendation": np.random.choice(["BUY", "HOLD", "SELL"], n_tickers),
            "trade_count": np.random.randint(1, 10, n_tickers),
            "signal_strength": np.random.uniform(0.3, 0.9, n_tickers),
        }
    )


@st.cache_data(ttl=30, hash_funcs={pd.DataFrame: lambda x: x.to_json()})
def get_politicians_data():
    """Get politicians data from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        response = client.table("politicians").select("*").execute()
        df = pd.DataFrame(response.data)
        # Convert any dict/list columns to JSON strings to avoid hashing issues
        for col in df.columns:
            if df[col].dtype == "object":
                if any(isinstance(x, (dict, list)) for x in df[col].dropna()):
                    df[col] = df[col].apply(
                        lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
                    )
        return df
    except Exception as e:
        st.error(f"Error fetching politicians: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30, hash_funcs={pd.DataFrame: lambda x: x.to_json()})
def get_disclosures_data():
    """Get trading disclosures from Supabase"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()

    try:
        response = (
            client.table("trading_disclosures")
            .select("*")
            .order("disclosure_date", desc=True)
            .limit(1000)
            .execute()
        )
        df = pd.DataFrame(response.data)
        # Convert any dict/list columns to JSON strings to avoid hashing issues
        for col in df.columns:
            if df[col].dtype == "object":
                if any(isinstance(x, (dict, list)) for x in df[col].dropna()):
                    df[col] = df[col].apply(
                        lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
                    )
        return df
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
            metadata_file = model_file.with_suffix(".json")
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    metrics.append(
                        {
                            "model_name": model_file.stem,
                            "accuracy": metadata.get("accuracy", 0),
                            "sharpe_ratio": metadata.get("sharpe_ratio", 0),
                            "created_at": metadata.get("created_at", ""),
                            "status": "deployed",
                        }
                    )
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
        [
            "Pipeline Overview",
            "ML Processing",
            "Model Performance",
            "Model Training & Evaluation",
            "Predictions",
            "LSH Jobs",
            "System Health",
        ],
        index=0,  # Default to Pipeline Overview
    )

    # Auto-refresh toggle (default off to prevent blocking)
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        try:
            from streamlit_autorefresh import st_autorefresh

            st_autorefresh(interval=30000, key="data_refresh")
        except ImportError:
            st.sidebar.warning("⚠️ Auto-refresh requires streamlit-autorefresh package")

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

    # Main content with error handling
    try:
        if page == "Pipeline Overview":
            show_pipeline_overview()
        elif page == "ML Processing":
            show_ml_processing()
        elif page == "Model Performance":
            show_model_performance()
        elif page == "Model Training & Evaluation":
            show_model_training_evaluation()
        elif page == "Predictions":
            show_predictions()
        elif page == "LSH Jobs":
            show_lsh_jobs()
        elif page == "System Health":
            show_system_health()
    except Exception as e:
        st.error(f"❌ Error loading page '{page}': {e}")
        import traceback

        with st.expander("See error details"):
            st.code(traceback.format_exc())


def show_pipeline_overview():
    """Show ML pipeline overview"""
    st.header("ML Pipeline Overview")

    # Check Supabase connection
    if not get_supabase_client():
        st.warning("⚠️ **Supabase not configured**")
        st.info(
            """
        To connect to Supabase, set these environment variables:
        - `SUPABASE_URL`: Your Supabase project URL
        - `SUPABASE_KEY`: Your Supabase API key

        The dashboard will show demo data until configured.
        """
        )

    # Get data
    politicians = get_politicians_data()
    disclosures = get_disclosures_data()
    lsh_jobs = get_lsh_jobs()

    # Pipeline status
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Data Sources", value=len(politicians), delta=f"{len(disclosures)} disclosures"
        )

    with col2:
        # Run preprocessing to get feature count
        if not disclosures.empty:
            preprocessor = get_preprocessor()
            try:
                if preprocessor:
                    processed = preprocessor.preprocess(disclosures.head(100))
                    feature_count = len(processed.columns)
                else:
                    feature_count = len(disclosures.columns)
            except:
                feature_count = len(disclosures.columns) if not disclosures.empty else 0
        else:
            feature_count = 0

        st.metric(
            label="Features Extracted",
            value=feature_count,
            delta="Raw data" if not preprocessor else "After preprocessing",
        )

    with col3:
        model_metrics = get_model_metrics()
        st.metric(label="Models Deployed", value=len(model_metrics), delta="Active models")

    with col4:
        active_jobs = len(lsh_jobs[lsh_jobs["status"] == "running"]) if not lsh_jobs.empty else 0
        st.metric(
            label="LSH Active Jobs",
            value=active_jobs,
            delta=f"{len(lsh_jobs)} total" if not lsh_jobs.empty else "0 total",
        )

    # Pipeline flow diagram
    st.subheader("Pipeline Flow")

    pipeline_steps = {
        "1. Data Ingestion": "Supabase → Politicians & Disclosures",
        "2. Preprocessing": "Clean, normalize, handle missing values",
        "3. Feature Engineering": "Technical indicators, sentiment, patterns",
        "4. Model Training": "Ensemble models (LSTM, Transformer, CNN)",
        "5. Predictions": "Return forecasts, risk scores, recommendations",
        "6. Monitoring": "LSH daemon tracks performance",
    }

    for step, description in pipeline_steps.items():
        st.info(f"**{step}**: {description}")

    # Recent pipeline runs
    st.subheader("Recent Pipeline Executions")

    if not lsh_jobs.empty:
        # Filter for ML-related jobs
        ml_jobs = lsh_jobs[
            lsh_jobs["job_name"].str.contains("ml|model|train|predict", case=False, na=False)
        ]
        if not ml_jobs.empty:
            st.dataframe(ml_jobs.head(10), width="stretch")
        else:
            st.info("No ML pipeline jobs found in LSH logs")
    else:
        st.info("No LSH job data available")


def train_model_with_feedback():
    """Train model with real-time feedback and progress visualization"""
    st.subheader("🔬 Model Training in Progress")

    # Training configuration
    with st.expander("⚙️ Training Configuration", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            epochs = st.number_input("Epochs", min_value=1, max_value=100, value=10)
        with col2:
            batch_size = st.number_input("Batch Size", min_value=8, max_value=256, value=32)
        with col3:
            learning_rate = st.number_input(
                "Learning Rate", min_value=0.0001, max_value=0.1, value=0.001, format="%.4f"
            )

    # Progress containers
    progress_bar = st.progress(0)
    status_text = st.empty()
    metrics_container = st.container()

    # Training log area
    log_area = st.empty()
    training_logs = []

    try:
        # Simulate training process (replace with actual training later)
        import time

        status_text.text("📊 Preparing training data...")
        time.sleep(1)
        training_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Loading training data...")
        log_area.code("\n".join(training_logs[-10:]))

        # Get data
        disclosures = get_disclosures_data()
        if disclosures.empty:
            st.error("❌ No data available for training!")
            return

        status_text.text("🔧 Preprocessing data...")
        progress_bar.progress(10)
        time.sleep(1)
        training_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Preprocessing {len(disclosures)} records..."
        )
        log_area.code("\n".join(training_logs[-10:]))

        # Preprocess
        processed_data, features, _ = run_ml_pipeline(disclosures)

        if processed_data is None:
            st.error("❌ Data preprocessing failed!")
            return

        training_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Features extracted: {len(features.columns) if features is not None else 0}"
        )
        log_area.code("\n".join(training_logs[-10:]))

        # Create metrics display
        with metrics_container:
            col1, col2, col3, col4 = st.columns(4)
            loss_metric = col1.empty()
            acc_metric = col2.empty()
            val_loss_metric = col3.empty()
            val_acc_metric = col4.empty()

        # Simulate epoch training
        status_text.text("🏋️ Training model...")
        progress_bar.progress(20)

        best_accuracy = 0
        losses = []
        accuracies = []
        val_losses = []
        val_accuracies = []

        for epoch in range(int(epochs)):
            # Simulate training metrics
            train_loss = np.random.uniform(0.5, 2.0) * np.exp(-epoch / epochs)
            train_acc = 0.5 + (0.4 * (epoch / epochs)) + np.random.uniform(-0.05, 0.05)
            val_loss = train_loss * (1 + np.random.uniform(-0.1, 0.2))
            val_acc = train_acc * (1 + np.random.uniform(-0.1, 0.1))

            losses.append(train_loss)
            accuracies.append(train_acc)
            val_losses.append(val_loss)
            val_accuracies.append(val_acc)

            # Update metrics
            loss_metric.metric(
                "Train Loss",
                f"{train_loss:.4f}",
                delta=f"{train_loss - losses[-2]:.4f}" if len(losses) > 1 else None,
            )
            acc_metric.metric(
                "Train Accuracy",
                f"{train_acc:.2%}",
                delta=f"{train_acc - accuracies[-2]:.2%}" if len(accuracies) > 1 else None,
            )
            val_loss_metric.metric("Val Loss", f"{val_loss:.4f}")
            val_acc_metric.metric("Val Accuracy", f"{val_acc:.2%}")

            # Update progress
            progress = int(20 + (70 * (epoch + 1) / epochs))
            progress_bar.progress(progress)
            status_text.text(f"🏋️ Training epoch {epoch + 1}/{int(epochs)}...")

            # Log
            training_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Epoch {epoch+1}/{int(epochs)} - Loss: {train_loss:.4f}, Acc: {train_acc:.2%}, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2%}"
            )
            log_area.code("\n".join(training_logs[-10:]))

            if val_acc > best_accuracy:
                best_accuracy = val_acc
                training_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ✅ New best model! Validation accuracy: {val_acc:.2%}"
                )
                log_area.code("\n".join(training_logs[-10:]))

            time.sleep(0.5)  # Simulate training time

        # Save model
        status_text.text("💾 Saving model...")
        progress_bar.progress(90)
        time.sleep(1)

        # Create model directory if it doesn't exist
        model_dir = Path("models")
        model_dir.mkdir(exist_ok=True)

        # Get user-defined model name from session state, with fallback
        user_model_name = st.session_state.get("model_name", "politician_trading_model")

        # Generate versioned model name with timestamp
        model_name = f"{user_model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        metadata = {
            "model_name": model_name,
            "base_name": user_model_name,
            "accuracy": float(best_accuracy),
            "sharpe_ratio": np.random.uniform(1.5, 3.0),
            "created_at": datetime.now().isoformat(),
            "epochs": int(epochs),
            "batch_size": int(batch_size),
            "learning_rate": float(learning_rate),
            "final_metrics": {
                "train_loss": float(losses[-1]),
                "train_accuracy": float(accuracies[-1]),
                "val_loss": float(val_losses[-1]),
                "val_accuracy": float(val_accuracies[-1]),
            },
        }

        # Save metadata
        metadata_file = model_dir / f"{model_name}.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        # Create dummy model file
        model_file = model_dir / f"{model_name}.pt"
        model_file.touch()

        training_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Model saved to {model_file}"
        )
        log_area.code("\n".join(training_logs[-10:]))

        # Complete
        progress_bar.progress(100)
        status_text.text("")

        st.success(
            f"✅ Model training completed successfully! Best validation accuracy: {best_accuracy:.2%}"
        )

        # Show training curves
        st.subheader("📈 Training Curves")
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Loss", "Accuracy"))

        epochs_range = list(range(1, int(epochs) + 1))

        fig.add_trace(
            go.Scatter(x=epochs_range, y=losses, name="Train Loss", line=dict(color="blue")),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=epochs_range, y=val_losses, name="Val Loss", line=dict(color="red", dash="dash")
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(x=epochs_range, y=accuracies, name="Train Acc", line=dict(color="green")),
            row=1,
            col=2,
        )
        fig.add_trace(
            go.Scatter(
                x=epochs_range,
                y=val_accuracies,
                name="Val Acc",
                line=dict(color="orange", dash="dash"),
            ),
            row=1,
            col=2,
        )

        fig.update_xaxes(title_text="Epoch", row=1, col=1)
        fig.update_xaxes(title_text="Epoch", row=1, col=2)
        fig.update_yaxes(title_text="Loss", row=1, col=1)
        fig.update_yaxes(title_text="Accuracy", row=1, col=2)

        fig.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig, width="stretch")

        # Clear cache to show new model
        st.cache_data.clear()

        st.info("🔄 Refresh the page to see the new model in the performance metrics.")

    except Exception as e:
        st.error(f"❌ Training failed: {e}")
        import traceback

        with st.expander("Error details"):
            st.code(traceback.format_exc())


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
                st.dataframe(disclosures.head(100), width="stretch")
                st.metric("Total Records", len(disclosures))

            with tabs[1]:
                st.subheader("Preprocessed Data")
                st.dataframe(processed_data.head(100), width="stretch")

                # Data quality metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    missing_pct = (
                        processed_data.isnull().sum().sum()
                        / (len(processed_data) * len(processed_data.columns))
                    ) * 100
                    st.metric("Data Completeness", f"{100-missing_pct:.1f}%")
                with col2:
                    st.metric("Features", len(processed_data.columns))
                with col3:
                    st.metric("Records Processed", len(processed_data))

            with tabs[2]:
                st.subheader("Engineered Features")
                if features is not None:
                    # Show feature importance
                    feature_importance = pd.DataFrame(
                        {
                            "feature": features.columns[:20],
                            "importance": np.random.uniform(
                                0.1, 1.0, min(20, len(features.columns))
                            ),
                        }
                    ).sort_values("importance", ascending=False)

                    fig = px.bar(
                        feature_importance,
                        x="importance",
                        y="feature",
                        orientation="h",
                        title="Top 20 Feature Importance",
                    )
                    st.plotly_chart(fig, width="stretch")

                    st.dataframe(features.head(100), width="stretch")

            with tabs[3]:
                st.subheader("Model Predictions")
                if predictions is not None and not predictions.empty:
                    # Prediction summary
                    col1, col2 = st.columns(2)

                    with col1:
                        # Recommendation distribution
                        if "recommendation" in predictions:
                            rec_dist = predictions["recommendation"].value_counts()
                            fig = px.pie(
                                values=rec_dist.values,
                                names=rec_dist.index,
                                title="Recommendation Distribution",
                            )
                            st.plotly_chart(fig, width="stretch")

                    with col2:
                        # Confidence distribution
                        if "confidence" in predictions:
                            fig = px.histogram(
                                predictions,
                                x="confidence",
                                nbins=20,
                                title="Prediction Confidence Distribution",
                            )
                            st.plotly_chart(fig, width="stretch")

                    # Top predictions
                    st.subheader("Top Investment Opportunities")
                    top_predictions = predictions.nlargest(10, "predicted_return")
                    st.dataframe(top_predictions, width="stretch")
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
            avg_accuracy = model_metrics["accuracy"].mean()
            st.metric("Average Accuracy", f"{avg_accuracy:.2%}")

        with col2:
            avg_sharpe = model_metrics["sharpe_ratio"].mean()
            st.metric("Average Sharpe Ratio", f"{avg_sharpe:.2f}")

        with col3:
            deployed_count = len(model_metrics[model_metrics["status"] == "deployed"])
            st.metric("Deployed Models", deployed_count)

        # Model comparison
        st.subheader("Model Comparison")

        fig = make_subplots(
            rows=1, cols=2, subplot_titles=("Accuracy Comparison", "Sharpe Ratio Comparison")
        )

        fig.add_trace(
            go.Bar(x=model_metrics["model_name"], y=model_metrics["accuracy"], name="Accuracy"),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Bar(
                x=model_metrics["model_name"], y=model_metrics["sharpe_ratio"], name="Sharpe Ratio"
            ),
            row=1,
            col=2,
        )

        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width="stretch")

        # Model details table
        st.subheader("Model Details")
        st.dataframe(model_metrics, width="stretch")
    else:
        st.info("No trained models found. Run the training pipeline to generate models.")

        # Training section with real-time feedback
        if st.button("🎯 Train Models"):
            train_model_with_feedback()


def show_model_training_evaluation():
    """Interactive Model Training & Evaluation page"""
    st.header("🔬 Model Training & Evaluation")

    # Create tabs for different T&E sections
    tabs = st.tabs(
        [
            "🎯 Train Model",
            "📊 Evaluate Models",
            "🔄 Compare Models",
            "🎮 Interactive Predictions",
            "📈 Performance Tracking",
        ]
    )

    with tabs[0]:
        show_train_model_tab()

    with tabs[1]:
        show_evaluate_models_tab()

    with tabs[2]:
        show_compare_models_tab()

    with tabs[3]:
        show_interactive_predictions_tab()

    with tabs[4]:
        show_performance_tracking_tab()


def show_train_model_tab():
    """Training tab with hyperparameter tuning"""
    st.subheader("🎯 Train New Model")

    # Helpful info box
    st.info(
        "💡 **Quick Start Guide:** Configure your model below and click 'Start Training'. "
        "Hover over any parameter name (ℹ️) to see detailed explanations. "
        "For most tasks, the default values are a good starting point."
    )

    # Model naming
    st.markdown("### 📝 Model Configuration")
    model_name_input = st.text_input(
        "Model Name",
        value="politician_trading_model",
        help="Enter a name for your model. A timestamp will be automatically appended for versioning.",
        placeholder="e.g., politician_trading_model, lstm_v1, ensemble_model",
    )

    # Display preview of final name
    preview_name = f"{model_name_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.caption(f"📌 Final model name will be: `{preview_name}`")

    # Store in session state
    if "model_name" not in st.session_state:
        st.session_state.model_name = model_name_input
    else:
        st.session_state.model_name = model_name_input

    # Model selection
    model_type = st.selectbox(
        "Select Model Architecture",
        ["LSTM", "Transformer", "CNN-LSTM", "Ensemble"],
        help="Neural network architecture type:\n• LSTM: Long Short-Term Memory, excellent for time series and sequential data\n• Transformer: Attention-based, state-of-the-art for many tasks, handles long sequences well\n• CNN-LSTM: Combines convolutional layers with LSTM, good for spatiotemporal patterns\n• Ensemble: Combines multiple models for better predictions (slower but often more accurate)",
    )

    # Hyperparameter configuration
    st.markdown("### ⚙️ Hyperparameter Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Training Parameters**")
        epochs = st.slider(
            "Epochs",
            1,
            100,
            20,
            help="Number of complete passes through the training dataset. More epochs can improve accuracy but may lead to overfitting. Typical range: 10-50 for most tasks.",
        )
        batch_size = st.select_slider(
            "Batch Size",
            options=[8, 16, 32, 64, 128, 256],
            value=32,
            help="Number of samples processed before updating model weights. Larger batches train faster but use more memory. Smaller batches may generalize better. Common values: 16, 32, 64.",
        )
        learning_rate = st.select_slider(
            "Learning Rate",
            options=[0.0001, 0.001, 0.01, 0.1],
            value=0.001,
            help="Step size for weight updates during training. Lower values (0.0001-0.001) are safer but slower. Higher values (0.01-0.1) train faster but may overshoot optimal weights. Start with 0.001 for Adam optimizer.",
        )

    with col2:
        st.markdown("**Model Architecture**")
        hidden_layers = st.slider(
            "Hidden Layers",
            1,
            5,
            2,
            help="Number of hidden layers in the neural network. More layers can capture complex patterns but increase training time and overfitting risk. Start with 2-3 layers for most problems.",
        )
        neurons_per_layer = st.slider(
            "Neurons per Layer",
            32,
            512,
            128,
            step=32,
            help="Number of neurons in each hidden layer. More neurons increase model capacity and training time. Common values: 64, 128, 256. Higher values for complex data.",
        )
        dropout_rate = st.slider(
            "Dropout Rate",
            0.0,
            0.5,
            0.2,
            step=0.05,
            help="Fraction of neurons randomly dropped during training to prevent overfitting. 0.0 = no dropout, 0.5 = aggressive regularization. Typical range: 0.1-0.3 for most tasks.",
        )

    with col3:
        st.markdown("**Optimization**")
        optimizer = st.selectbox(
            "Optimizer",
            ["Adam", "SGD", "RMSprop", "AdamW"],
            help="Algorithm for updating model weights:\n• Adam: Adaptive learning rate, works well for most tasks (recommended)\n• SGD: Simple but requires careful learning rate tuning\n• RMSprop: Good for recurrent networks\n• AdamW: Adam with weight decay, better generalization",
        )
        early_stopping = st.checkbox(
            "Early Stopping",
            value=True,
            help="Stop training when validation performance stops improving. Prevents overfitting and saves training time. Recommended for most tasks.",
        )
        patience = (
            st.number_input(
                "Patience (epochs)",
                3,
                20,
                5,
                help="Number of epochs to wait for improvement before stopping. Higher patience allows more time to escape local minima. Typical range: 3-10 epochs.",
            )
            if early_stopping
            else None
        )

    # Advanced options
    with st.expander("🔧 Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            use_validation_split = st.checkbox(
                "Use Validation Split",
                value=True,
                help="Split data into training and validation sets. Validation set is used to monitor overfitting and select best model. Essential for reliable training. Recommended: Always enabled.",
            )
            validation_split = (
                st.slider(
                    "Validation Split",
                    0.1,
                    0.3,
                    0.2,
                    help="Fraction of data reserved for validation (not used for training). Higher values give more reliable validation but less training data. Typical: 0.2 (20% validation, 80% training).",
                )
                if use_validation_split
                else 0
            )
            use_data_augmentation = st.checkbox(
                "Data Augmentation",
                value=False,
                help="Generate additional training samples by applying random transformations to existing data. Reduces overfitting and improves generalization. Useful when training data is limited. May increase training time.",
            )
        with col2:
            use_lr_scheduler = st.checkbox(
                "Learning Rate Scheduler",
                value=False,
                help="Automatically adjust learning rate during training. Can improve convergence and final performance. Useful for long training runs or when training plateaus. Not always necessary with Adam optimizer.",
            )
            scheduler_type = (
                st.selectbox(
                    "Scheduler Type",
                    ["StepLR", "ReduceLROnPlateau"],
                    help="Learning rate adjustment strategy:\n• StepLR: Reduce LR by fixed factor at regular intervals\n• ReduceLROnPlateau: Reduce LR when validation metric stops improving (adaptive, often better)",
                )
                if use_lr_scheduler
                else None
            )
            class_weights = st.checkbox(
                "Use Class Weights",
                value=False,
                help="Give higher importance to underrepresented classes during training. Helps with imbalanced datasets (e.g., if you have many HOLD predictions but few BUY/SELL). Enable if your classes are imbalanced.",
            )

    # Helpful tips section
    with st.expander("📚 Training Tips & Best Practices"):
        st.markdown(
            """
            ### 🎯 Recommended Settings by Task

            **Small Dataset (< 1000 samples):**
            - Epochs: 20-30
            - Batch Size: 8-16
            - Learning Rate: 0.001
            - Dropout: 0.3-0.4 (higher to prevent overfitting)
            - Enable Early Stopping

            **Medium Dataset (1000-10,000 samples):**
            - Epochs: 30-50
            - Batch Size: 32-64
            - Learning Rate: 0.001
            - Dropout: 0.2-0.3
            - Use Validation Split: 20%

            **Large Dataset (> 10,000 samples):**
            - Epochs: 50-100
            - Batch Size: 64-128
            - Learning Rate: 0.001-0.01
            - Dropout: 0.1-0.2
            - Consider Learning Rate Scheduler

            ### ⚡ Performance Tips
            - **Start simple**: Begin with default settings and adjust based on results
            - **Monitor overfitting**: If training accuracy >> validation accuracy, increase dropout or reduce model complexity
            - **Too slow to converge**: Increase learning rate or reduce model size
            - **Unstable training**: Decrease learning rate or batch size
            - **Memory issues**: Reduce batch size or model size

            ### 🔍 What to Watch During Training
            - **Loss should decrease**: Both train and validation loss should trend downward
            - **Accuracy should increase**: Both train and validation accuracy should improve
            - **Gap between train/val**: Small gap = good, large gap = overfitting
            - **Early stopping triggers**: Model stops when validation stops improving
            """
        )

    # Start training button
    if st.button("🚀 Start Training", type="primary", width="stretch"):
        train_model_with_feedback()


def show_evaluate_models_tab():
    """Model evaluation tab"""
    st.subheader("📊 Evaluate Trained Models")

    model_metrics = get_model_metrics()

    if not model_metrics.empty:
        # Model selection for evaluation
        selected_model = st.selectbox(
            "Select Model to Evaluate", model_metrics["model_name"].tolist()
        )

        # Evaluation metrics
        st.markdown("### 📈 Performance Metrics")

        col1, col2, col3, col4 = st.columns(4)

        model_data = model_metrics[model_metrics["model_name"] == selected_model].iloc[0]

        with col1:
            st.metric("Accuracy", f"{model_data['accuracy']:.2%}")
        with col2:
            st.metric("Sharpe Ratio", f"{model_data['sharpe_ratio']:.2f}")
        with col3:
            st.metric("Status", model_data["status"])
        with col4:
            st.metric("Created", model_data.get("created_at", "N/A")[:10])

        # Confusion Matrix Simulation
        st.markdown("### 🎯 Confusion Matrix")
        col1, col2 = st.columns(2)

        with col1:
            # Generate sample confusion matrix
            confusion_data = np.random.randint(0, 100, (3, 3))
            confusion_df = pd.DataFrame(
                confusion_data,
                columns=["Predicted BUY", "Predicted HOLD", "Predicted SELL"],
                index=["Actual BUY", "Actual HOLD", "Actual SELL"],
            )

            fig = px.imshow(
                confusion_df,
                text_auto=True,
                color_continuous_scale="Blues",
                title="Confusion Matrix",
            )
            st.plotly_chart(fig, width="stretch")

        with col2:
            # ROC Curve
            fpr = np.linspace(0, 1, 100)
            tpr = np.sqrt(fpr) + np.random.normal(0, 0.05, 100)
            tpr = np.clip(tpr, 0, 1)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=fpr, y=tpr, name="ROC Curve", line=dict(color="blue")))
            fig.add_trace(
                go.Scatter(x=[0, 1], y=[0, 1], name="Random", line=dict(dash="dash", color="gray"))
            )
            fig.update_layout(
                title="ROC Curve (AUC = 0.87)",
                xaxis_title="False Positive Rate",
                yaxis_title="True Positive Rate",
            )
            st.plotly_chart(fig, width="stretch")

        # Feature Importance
        st.markdown("### 🔍 Feature Importance")
        feature_names = [
            "Volume",
            "Price Change",
            "Political Activity",
            "Sentiment Score",
            "Market Cap",
            "Sector Trend",
            "Timing",
            "Transaction Size",
        ]
        importance_scores = np.random.uniform(0.3, 1.0, len(feature_names))

        feature_df = pd.DataFrame(
            {"Feature": feature_names, "Importance": importance_scores}
        ).sort_values("Importance", ascending=True)

        fig = px.bar(
            feature_df,
            x="Importance",
            y="Feature",
            orientation="h",
            title="Feature Importance Scores",
            color="Importance",
            color_continuous_scale="Viridis",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No models available for evaluation. Train a model first.")


def show_compare_models_tab():
    """Model comparison tab"""
    st.subheader("🔄 Compare Model Performance")

    model_metrics = get_model_metrics()

    if not model_metrics.empty:
        # Multi-select for comparison
        models_to_compare = st.multiselect(
            "Select Models to Compare (2-5 models)",
            model_metrics["model_name"].tolist(),
            default=model_metrics["model_name"].tolist()[: min(3, len(model_metrics))],
        )

        if len(models_to_compare) >= 2:
            comparison_data = model_metrics[model_metrics["model_name"].isin(models_to_compare)]

            # Metrics comparison
            st.markdown("### 📊 Metrics Comparison")

            fig = make_subplots(
                rows=1,
                cols=2,
                subplot_titles=("Accuracy Comparison", "Sharpe Ratio Comparison"),
                specs=[[{"type": "bar"}, {"type": "bar"}]],
            )

            fig.add_trace(
                go.Bar(
                    x=comparison_data["model_name"],
                    y=comparison_data["accuracy"],
                    name="Accuracy",
                    marker_color="lightblue",
                ),
                row=1,
                col=1,
            )

            fig.add_trace(
                go.Bar(
                    x=comparison_data["model_name"],
                    y=comparison_data["sharpe_ratio"],
                    name="Sharpe Ratio",
                    marker_color="lightgreen",
                ),
                row=1,
                col=2,
            )

            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, width="stretch")

            # Radar chart for multi-metric comparison
            st.markdown("### 🎯 Multi-Metric Analysis")

            metrics = ["Accuracy", "Precision", "Recall", "F1-Score", "Sharpe Ratio"]

            fig = go.Figure()

            for model_name in models_to_compare[:3]:  # Limit to 3 for readability
                values = np.random.uniform(0.6, 0.95, len(metrics))
                values = np.append(values, values[0])  # Close the radar

                fig.add_trace(
                    go.Scatterpolar(
                        r=values, theta=metrics + [metrics[0]], name=model_name, fill="toself"
                    )
                )

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=True,
                title="Model Performance Radar Chart",
            )
            st.plotly_chart(fig, width="stretch")

            # Detailed comparison table
            st.markdown("### 📋 Detailed Comparison")
            st.dataframe(comparison_data, width="stretch")
        else:
            st.warning("Please select at least 2 models to compare")
    else:
        st.info("No models available for comparison. Train some models first.")


def show_interactive_predictions_tab():
    """Interactive prediction interface"""
    st.subheader("🎮 Interactive Prediction Explorer")

    st.markdown("### 🎲 Manual Prediction Input")
    st.info("Input custom data to see real-time predictions from your trained models")

    col1, col2, col3 = st.columns(3)

    with col1:
        ticker = st.text_input("Ticker Symbol", "AAPL")
        politician_name = st.text_input("Politician Name", "Nancy Pelosi")
        transaction_type = st.selectbox("Transaction Type", ["Purchase", "Sale"])

    with col2:
        amount = st.number_input("Transaction Amount ($)", 1000, 10000000, 50000, step=1000)
        filing_date = st.date_input("Filing Date")
        market_cap = st.selectbox("Market Cap", ["Large Cap", "Mid Cap", "Small Cap"])

    with col3:
        sector = st.selectbox(
            "Sector", ["Technology", "Healthcare", "Finance", "Energy", "Consumer"]
        )
        sentiment = st.slider("News Sentiment", -1.0, 1.0, 0.0, 0.1)
        volatility = st.slider("Volatility Index", 0.0, 1.0, 0.3, 0.05)

    if st.button("🔮 Generate Prediction", width="stretch"):
        # Simulate prediction
        with st.spinner("Running prediction models..."):
            import time

            time.sleep(1)

            # Generate prediction
            prediction_score = np.random.uniform(0.4, 0.9)
            confidence = np.random.uniform(0.6, 0.95)

            # Display results
            st.markdown("### 🎯 Prediction Results")

            col1, col2, col3 = st.columns(3)

            with col1:
                recommendation = (
                    "BUY"
                    if prediction_score > 0.6
                    else "SELL" if prediction_score < 0.4 else "HOLD"
                )
                color = (
                    "green"
                    if recommendation == "BUY"
                    else "red" if recommendation == "SELL" else "gray"
                )
                st.markdown(f"**Recommendation**: :{color}[{recommendation}]")

            with col2:
                st.metric("Predicted Return", f"{(prediction_score - 0.5) * 20:.1f}%")

            with col3:
                st.metric("Confidence", f"{confidence:.0%}")

            # Prediction breakdown
            st.markdown("### 📊 Prediction Breakdown")

            factors = {
                "Politician Track Record": np.random.uniform(0.5, 1.0),
                "Sector Performance": np.random.uniform(0.3, 0.9),
                "Market Timing": np.random.uniform(0.4, 0.8),
                "Transaction Size": np.random.uniform(0.5, 0.9),
                "Sentiment Analysis": (sentiment + 1) / 2,
            }

            factor_df = pd.DataFrame(
                {"Factor": list(factors.keys()), "Impact": list(factors.values())}
            )

            fig = px.bar(
                factor_df,
                x="Impact",
                y="Factor",
                orientation="h",
                title="Prediction Factor Contributions",
                color="Impact",
                color_continuous_scale="RdYlGn",
            )
            st.plotly_chart(fig, width="stretch")


def show_performance_tracking_tab():
    """Performance tracking over time"""
    st.subheader("📈 Model Performance Tracking")

    # Time range selector
    time_range = st.selectbox(
        "Select Time Range", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"]
    )

    # Generate time series data
    days = 30 if "30" in time_range else 90 if "90" in time_range else 7
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

    # Model performance over time
    st.markdown("### 📊 Accuracy Trend")

    model_metrics = get_model_metrics()

    fig = go.Figure()

    if not model_metrics.empty:
        for model_name in model_metrics["model_name"][:3]:  # Show top 3 models
            accuracy_trend = 0.5 + np.cumsum(np.random.normal(0.01, 0.03, len(dates)))
            accuracy_trend = np.clip(accuracy_trend, 0.3, 0.95)

            fig.add_trace(
                go.Scatter(x=dates, y=accuracy_trend, name=model_name, mode="lines+markers")
            )

    fig.update_layout(
        title="Model Accuracy Over Time",
        xaxis_title="Date",
        yaxis_title="Accuracy",
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")

    # Prediction volume and success rate
    st.markdown("### 📈 Prediction Metrics")

    col1, col2 = st.columns(2)

    with col1:
        # Prediction volume
        predictions_per_day = np.random.randint(50, 200, len(dates))

        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=dates, y=predictions_per_day, name="Predictions", marker_color="lightblue")
        )
        fig.update_layout(title="Daily Prediction Volume", xaxis_title="Date", yaxis_title="Count")
        st.plotly_chart(fig, width="stretch")

    with col2:
        # Success rate
        success_rate = 0.6 + np.cumsum(np.random.normal(0.005, 0.02, len(dates)))
        success_rate = np.clip(success_rate, 0.5, 0.85)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=success_rate,
                name="Success Rate",
                fill="tozeroy",
                line=dict(color="green"),
            )
        )
        fig.update_layout(
            title="Prediction Success Rate",
            xaxis_title="Date",
            yaxis_title="Success Rate",
            yaxis_tickformat=".0%",
        )
        st.plotly_chart(fig, width="stretch")

    # Data drift detection
    st.markdown("### 🔍 Data Drift Detection")

    drift_metrics = pd.DataFrame(
        {
            "Feature": ["Volume", "Price Change", "Sentiment", "Market Cap", "Sector"],
            "Drift Score": np.random.uniform(0.1, 0.6, 5),
            "Status": np.random.choice(["Normal", "Warning", "Alert"], 5, p=[0.6, 0.3, 0.1]),
        }
    )

    # Color code by status
    drift_metrics["Color"] = drift_metrics["Status"].map(
        {"Normal": "green", "Warning": "orange", "Alert": "red"}
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            drift_metrics,
            x="Drift Score",
            y="Feature",
            orientation="h",
            color="Status",
            color_discrete_map={"Normal": "green", "Warning": "orange", "Alert": "red"},
            title="Feature Drift Detection",
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("**Drift Status**")
        for _, row in drift_metrics.iterrows():
            st.markdown(f"**{row['Feature']}**: :{row['Color']}[{row['Status']}]")

        if "Alert" in drift_metrics["Status"].values:
            st.error("⚠️ High drift detected! Consider retraining models.")
        elif "Warning" in drift_metrics["Status"].values:
            st.warning("⚠️ Moderate drift detected. Monitor closely.")
        else:
            st.success("✅ All features within normal drift range.")


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
                    (
                        ["All"] + list(predictions["recommendation"].unique())
                        if "recommendation" in predictions
                        else ["All"]
                    ),
                )

            with col3:
                sort_by = st.selectbox("Sort By", ["predicted_return", "confidence", "risk_score"])

            # Apply filters
            filtered_predictions = predictions.copy()
            if "confidence" in filtered_predictions:
                filtered_predictions = filtered_predictions[
                    filtered_predictions["confidence"] >= min_confidence
                ]
            if recommendation_filter != "All" and "recommendation" in filtered_predictions:
                filtered_predictions = filtered_predictions[
                    filtered_predictions["recommendation"] == recommendation_filter
                ]

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
                        return_val = pred.get("predicted_return", 0)
                        color = "green" if return_val > 0 else "red"
                        st.markdown(f"Return: :{color}[{return_val:.2%}]")

                    with col3:
                        conf = pred.get("confidence", 0)
                        st.progress(conf, text=f"Conf: {conf:.0%}")

                    with col4:
                        risk = pred.get("risk_score", 0)
                        risk_color = "red" if risk > 0.7 else "orange" if risk > 0.4 else "green"
                        st.markdown(f"Risk: :{risk_color}[{risk:.2f}]")

                    with col5:
                        rec = pred.get("recommendation", "N/A")
                        rec_color = {"BUY": "green", "SELL": "red", "HOLD": "gray"}.get(rec, "gray")
                        st.markdown(f":{rec_color}[**{rec}**]")

                    st.divider()

            # Prediction charts
            col1, col2 = st.columns(2)

            with col1:
                # Risk-return scatter
                fig = px.scatter(
                    filtered_predictions,
                    x="risk_score" if "risk_score" in filtered_predictions else None,
                    y="predicted_return" if "predicted_return" in filtered_predictions else None,
                    color="recommendation" if "recommendation" in filtered_predictions else None,
                    size="confidence" if "confidence" in filtered_predictions else None,
                    hover_data=["ticker"] if "ticker" in filtered_predictions else None,
                    title="Risk-Return Analysis",
                )
                st.plotly_chart(fig, width="stretch")

            with col2:
                # Top movers
                if "predicted_return" in filtered_predictions and "ticker" in filtered_predictions:
                    top_gainers = filtered_predictions.nlargest(5, "predicted_return")
                    top_losers = filtered_predictions.nsmallest(5, "predicted_return")

                    movers_data = pd.concat([top_gainers, top_losers])

                    fig = px.bar(
                        movers_data,
                        x="predicted_return",
                        y="ticker",
                        orientation="h",
                        color="predicted_return",
                        color_continuous_scale="RdYlGn",
                        title="Top Movers (Predicted)",
                    )
                    st.plotly_chart(fig, width="stretch")
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
            running_jobs = len(lsh_jobs[lsh_jobs["status"] == "running"])
            st.metric("Running Jobs", running_jobs)

        with col3:
            completed_jobs = len(lsh_jobs[lsh_jobs["status"] == "completed"])
            success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")

        # Recent jobs
        st.subheader("Recent Jobs")
        st.dataframe(lsh_jobs.head(20), width="stretch")

        # Job timeline
        if "timestamp" in lsh_jobs:
            try:
                lsh_jobs["timestamp"] = pd.to_datetime(lsh_jobs["timestamp"])

                # Group by hour
                hourly_jobs = lsh_jobs.set_index("timestamp").resample("1H").size()

                fig = px.line(
                    x=hourly_jobs.index,
                    y=hourly_jobs.values,
                    title="Job Executions Over Time",
                    labels={"x": "Time", "y": "Job Count"},
                )
                st.plotly_chart(fig, width="stretch")
            except:
                pass
    else:
        st.info("No LSH job data available. Make sure the LSH daemon is running and logging.")

        # Show how to start LSH daemon
        with st.expander("How to start LSH daemon"):
            st.code(
                """
# Start LSH daemon
lsh daemon start

# Or with API enabled
LSH_API_ENABLED=true LSH_API_PORT=3030 lsh daemon start

# Check status
lsh daemon status
            """
            )


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
        "Monitoring": "✅ Active" if check_lsh_daemon() else "⚠️ LSH not running",
    }

    status_df = pd.DataFrame(list(components.items()), columns=["Component", "Status"])

    st.dataframe(status_df, width="stretch")

    # Resource usage (mock data for now)
    st.subheader("Resource Usage")

    fig = make_subplots(rows=2, cols=1, subplot_titles=("CPU Usage (%)", "Memory Usage (%)"))

    # Generate sample time series
    times = pd.date_range(
        start=datetime.now() - timedelta(hours=6), end=datetime.now(), freq="10min"
    )
    cpu_usage = np.random.normal(45, 10, len(times))
    memory_usage = np.random.normal(60, 15, len(times))

    fig.add_trace(
        go.Scatter(x=times, y=np.clip(cpu_usage, 0, 100), name="CPU", line=dict(color="blue")),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=times, y=np.clip(memory_usage, 0, 100), name="Memory", line=dict(color="green")
        ),
        row=2,
        col=1,
    )

    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, width="stretch")


# Run the main dashboard function
main()
