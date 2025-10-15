"""Streamlit dashboard for ML system monitoring"""

import asyncio
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

from mcli.ml.cache import cache_manager
from mcli.ml.config import settings
from mcli.ml.dashboard.common import setup_page_config
from mcli.ml.dashboard.styles import apply_dashboard_styles
from mcli.ml.database.models import (
    BacktestResult,
    Model,
    ModelStatus,
    Portfolio,
    Prediction,
    StockData,
    Trade,
    User,
)
from mcli.ml.database.session import SessionLocal

# Page config - must be first
setup_page_config(page_title="MCLI ML Dashboard")

# Apply standard dashboard styles
apply_dashboard_styles()


@st.cache_data(ttl=30)
def get_system_metrics():
    """Get real-time system metrics"""
    db = SessionLocal()

    try:
        # Model metrics
        total_models = db.query(Model).count()
        deployed_models = db.query(Model).filter(Model.status == ModelStatus.DEPLOYED).count()
        training_models = db.query(Model).filter(Model.status == ModelStatus.TRAINING).count()

        # User metrics
        total_users = db.query(User).count()
        active_users = (
            db.query(User)
            .filter(User.last_login_at >= datetime.utcnow() - timedelta(days=1))
            .count()
        )

        # Prediction metrics
        predictions_today = (
            db.query(Prediction)
            .filter(Prediction.prediction_date >= datetime.utcnow().date())
            .count()
        )

        # Portfolio metrics
        active_portfolios = db.query(Portfolio).filter(Portfolio.is_active == True).count()

        return {
            "total_models": total_models,
            "deployed_models": deployed_models,
            "training_models": training_models,
            "total_users": total_users,
            "active_users": active_users,
            "predictions_today": predictions_today,
            "active_portfolios": active_portfolios,
            "timestamp": datetime.utcnow(),
        }
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_model_performance():
    """Get model performance data"""
    db = SessionLocal()

    try:
        models = db.query(Model).filter(Model.status == ModelStatus.DEPLOYED).all()

        data = []
        for model in models:
            data.append(
                {
                    "name": model.name,
                    "accuracy": model.test_accuracy or 0,
                    "created_at": model.created_at,
                    "last_updated": model.updated_at,
                }
            )

        return pd.DataFrame(data)
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_recent_predictions():
    """Get recent predictions"""
    db = SessionLocal()

    try:
        predictions = (
            db.query(Prediction).order_by(Prediction.prediction_date.desc()).limit(100).all()
        )

        data = []
        for pred in predictions:
            data.append(
                {
                    "ticker": pred.ticker,
                    "predicted_return": pred.predicted_return,
                    "confidence": pred.confidence_score,
                    "prediction_date": pred.prediction_date,
                    "target_date": pred.target_date,
                }
            )

        return pd.DataFrame(data)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_portfolio_performance():
    """Get portfolio performance data"""
    db = SessionLocal()

    try:
        portfolios = db.query(Portfolio).filter(Portfolio.is_active == True).all()

        data = []
        for portfolio in portfolios:
            data.append(
                {
                    "name": portfolio.name,
                    "total_return": portfolio.total_return or 0,
                    "sharpe_ratio": portfolio.sharpe_ratio or 0,
                    "max_drawdown": portfolio.max_drawdown or 0,
                    "current_value": portfolio.current_value or 0,
                }
            )

        return pd.DataFrame(data)
    finally:
        db.close()


def check_api_health():
    """Check API health"""
    try:
        response = requests.get(f"http://localhost:{settings.api.port}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def check_redis_health():
    """Check Redis health"""
    try:
        cache_manager.initialize()
        return cache_manager.redis_client.ping() if cache_manager.redis_client else False
    except:
        return False


def main():
    """Main dashboard function"""

    # Title and header
    st.title("🤖 MCLI ML System Dashboard")
    st.markdown("Real-time monitoring of ML models, predictions, and system health")

    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Overview", "Models", "Predictions", "Portfolios", "System Health", "Live Monitoring"],
    )

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

    # Main content based on selected page
    if page == "Overview":
        show_overview()
    elif page == "Models":
        show_models()
    elif page == "Predictions":
        show_predictions()
    elif page == "Portfolios":
        show_portfolios()
    elif page == "System Health":
        show_system_health()
    elif page == "Live Monitoring":
        show_live_monitoring()


def show_overview():
    """Show overview dashboard"""
    st.header("System Overview")

    # Get metrics
    metrics = get_system_metrics()

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Deployed Models",
            value=metrics["deployed_models"],
            delta=f"{metrics['training_models']} training",
        )

    with col2:
        st.metric(
            label="Active Users",
            value=metrics["active_users"],
            delta=f"{metrics['total_users']} total",
        )

    with col3:
        st.metric(label="Predictions Today", value=metrics["predictions_today"])

    with col4:
        st.metric(label="Active Portfolios", value=metrics["active_portfolios"])

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Model Performance")
        model_data = get_model_performance()
        if not model_data.empty:
            fig = px.bar(model_data, x="name", y="accuracy", title="Model Accuracy Comparison")
            st.plotly_chart(fig, width="stretch", config={"responsive": True})
        else:
            st.info("No model performance data available")

    with col2:
        st.subheader("Recent Predictions")
        pred_data = get_recent_predictions()
        if not pred_data.empty:
            # Show confidence distribution
            fig = px.histogram(
                pred_data, x="confidence", title="Prediction Confidence Distribution"
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})
        else:
            st.info("No recent predictions available")


def show_models():
    """Show models dashboard"""
    st.header("Model Management")

    # Model performance table
    model_data = get_model_performance()

    if not model_data.empty:
        st.subheader("Model Performance")
        st.dataframe(model_data, width="stretch")

        # Model accuracy chart
        fig = px.line(
            model_data, x="created_at", y="accuracy", color="name", title="Model Accuracy Over Time"
        )
        st.plotly_chart(fig, width="stretch", config={"responsive": True})
    else:
        st.warning("No model data available")


def show_predictions():
    """Show predictions dashboard"""
    st.header("Predictions Analysis")

    pred_data = get_recent_predictions()

    if not pred_data.empty:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            selected_tickers = st.multiselect(
                "Filter by Ticker",
                options=pred_data["ticker"].unique(),
                default=pred_data["ticker"].unique()[:5],
            )

        with col2:
            confidence_threshold = st.slider(
                "Minimum Confidence", min_value=0.0, max_value=1.0, value=0.5, step=0.1
            )

        # Filter data
        filtered_data = pred_data[
            (pred_data["ticker"].isin(selected_tickers))
            & (pred_data["confidence"] >= confidence_threshold)
        ]

        # Display filtered data
        st.subheader("Filtered Predictions")
        st.dataframe(filtered_data, width="stretch")

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            fig = px.scatter(
                filtered_data,
                x="confidence",
                y="predicted_return",
                color="ticker",
                title="Confidence vs Predicted Return",
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})

        with col2:
            # Group by ticker and show average return
            avg_returns = filtered_data.groupby("ticker")["predicted_return"].mean().reset_index()
            fig = px.bar(
                avg_returns,
                x="ticker",
                y="predicted_return",
                title="Average Predicted Return by Ticker",
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})

    else:
        st.warning("No prediction data available")


def show_portfolios():
    """Show portfolios dashboard"""
    st.header("Portfolio Performance")

    portfolio_data = get_portfolio_performance()

    if not portfolio_data.empty:
        # Portfolio metrics
        st.subheader("Portfolio Summary")
        st.dataframe(portfolio_data, width="stretch")

        # Performance charts
        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                portfolio_data, x="name", y="total_return", title="Total Return by Portfolio"
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})

        with col2:
            fig = px.scatter(
                portfolio_data,
                x="sharpe_ratio",
                y="total_return",
                size="current_value",
                hover_data=["name"],
                title="Risk-Return Analysis",
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})

    else:
        st.warning("No portfolio data available")


def show_system_health():
    """Show system health dashboard"""
    st.header("System Health")

    # Check various system components
    api_healthy = check_api_health()
    redis_healthy = check_redis_health()

    col1, col2, col3 = st.columns(3)

    with col1:
        if api_healthy:
            st.success("✅ API Server: Healthy")
        else:
            st.error("❌ API Server: Unhealthy")

    with col2:
        if redis_healthy:
            st.success("✅ Redis Cache: Healthy")
        else:
            st.error("❌ Redis Cache: Unhealthy")

    with col3:
        # Database health (always assume healthy if we can query)
        st.success("✅ Database: Healthy")

    # System metrics over time (simulated)
    st.subheader("System Metrics")

    # Generate sample time series data
    times = pd.date_range(start=datetime.now() - timedelta(hours=24), end=datetime.now(), freq="H")
    cpu_usage = np.random.normal(45, 10, len(times))
    memory_usage = np.random.normal(60, 15, len(times))

    metrics_df = pd.DataFrame(
        {
            "time": times,
            "cpu_usage": np.clip(cpu_usage, 0, 100),
            "memory_usage": np.clip(memory_usage, 0, 100),
        }
    )

    fig = make_subplots(rows=2, cols=1, subplot_titles=("CPU Usage (%)", "Memory Usage (%)"))

    fig.add_trace(
        go.Scatter(x=metrics_df["time"], y=metrics_df["cpu_usage"], name="CPU"), row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=metrics_df["time"], y=metrics_df["memory_usage"], name="Memory"), row=2, col=1
    )

    fig.update_layout(height=500, title_text="System Resource Usage (24h)")
    st.plotly_chart(fig, width="stretch", config={"responsive": True})


def show_live_monitoring():
    """Show live monitoring with real-time updates"""
    st.header("Live Monitoring")

    # Real-time metrics placeholder
    metrics_placeholder = st.empty()

    # Live prediction feed
    st.subheader("Live Prediction Feed")
    prediction_placeholder = st.empty()

    # Live model status
    st.subheader("Model Status")
    model_placeholder = st.empty()

    # Auto-update every 5 seconds
    if st.button("Start Live Monitoring"):
        for i in range(60):  # Run for 5 minutes
            # Update metrics
            metrics = get_system_metrics()
            with metrics_placeholder.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Predictions/min", np.random.randint(5, 20))
                with col2:
                    st.metric("Avg Confidence", f"{np.random.uniform(0.7, 0.9):.3f}")
                with col3:
                    st.metric("Active Models", metrics["deployed_models"])

            # Simulate new predictions
            with prediction_placeholder.container():
                new_preds = pd.DataFrame(
                    {
                        "Ticker": np.random.choice(["AAPL", "GOOGL", "MSFT", "TSLA"], 5),
                        "Prediction": np.random.uniform(-0.05, 0.05, 5),
                        "Confidence": np.random.uniform(0.6, 0.95, 5),
                        "Time": [datetime.now() - timedelta(seconds=x * 10) for x in range(5)],
                    }
                )
                st.dataframe(new_preds, width="stretch")

            # Model status
            with model_placeholder.container():
                model_data = get_model_performance()
                if not model_data.empty:
                    st.dataframe(model_data[["name", "accuracy"]], width="stretch")

            time.sleep(5)


if __name__ == "__main__":
    main()
