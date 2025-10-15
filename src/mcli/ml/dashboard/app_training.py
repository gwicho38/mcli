"""Enhanced training dashboard with Bitcoin-style model comparison and analysis"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import stats

from mcli.ml.dashboard.common import setup_page_config
from mcli.ml.dashboard.styles import apply_dashboard_styles
from mcli.ml.database.models import Experiment, Model, ModelStatus
from mcli.ml.database.session import SessionLocal

# Page config - must be first
setup_page_config(page_title="MCLI Training Dashboard", page_icon="🔬")

# Apply standard dashboard styles (includes metric-card)
apply_dashboard_styles()

# Add training-specific CSS
st.markdown(
    """
<style>
    .model-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
    .best-model {
        border-left: 4px solid #28a745;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60)
def get_training_jobs():
    """Get recent training jobs and experiments"""
    db = SessionLocal()

    try:
        experiments = db.query(Experiment).order_by(Experiment.created_at.desc()).limit(50).all()

        data = []
        for exp in experiments:
            data.append(
                {
                    "name": exp.name,
                    "status": exp.status,
                    "started_at": exp.started_at,
                    "completed_at": exp.completed_at,
                    "duration_seconds": exp.duration_seconds,
                    "hyperparameters": exp.hyperparameters,
                    "train_metrics": exp.train_metrics or {},
                    "val_metrics": exp.val_metrics or {},
                    "test_metrics": exp.test_metrics or {},
                }
            )

        return pd.DataFrame(data)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_model_comparison():
    """Get model comparison data with comprehensive metrics"""
    db = SessionLocal()

    try:
        models = (
            db.query(Model)
            .filter(Model.status.in_([ModelStatus.TRAINED, ModelStatus.DEPLOYED]))
            .all()
        )

        data = []
        for model in models:
            metrics = model.metrics or {}

            # Extract metrics similar to bitcoin project
            data.append(
                {
                    "name": model.name,
                    "version": model.version,
                    "model_type": model.model_type,
                    "status": model.status.value,
                    # Training metrics
                    "train_accuracy": model.train_accuracy or 0,
                    "train_loss": model.train_loss or 0,
                    # Validation metrics
                    "val_accuracy": model.val_accuracy or 0,
                    "val_loss": model.val_loss or 0,
                    # Test metrics
                    "test_accuracy": model.test_accuracy or 0,
                    "test_loss": model.test_loss or 0,
                    # Additional metrics
                    "rmse": metrics.get("rmse", 0),
                    "mae": metrics.get("mae", 0),
                    "r2": metrics.get("r2", 0),
                    "mape": metrics.get("mape", 0),
                    # Metadata
                    "is_deployed": model.status == ModelStatus.DEPLOYED,
                    "created_at": model.created_at,
                    "updated_at": model.updated_at,
                }
            )

        return pd.DataFrame(data)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_feature_importance(model_id: str):
    """Get feature importance for a specific model"""
    db = SessionLocal()

    try:
        from sqlalchemy.dialects.postgresql import UUID

        model = db.query(Model).filter(Model.id == model_id).first()

        if model and model.feature_names:
            # Simulate feature importance (in real scenario, load from model artifacts)
            importance = np.random.dirichlet(np.ones(len(model.feature_names)))

            return pd.DataFrame(
                {"feature": model.feature_names, "importance": importance}
            ).sort_values("importance", ascending=False)

        return pd.DataFrame()
    finally:
        db.close()


def show_model_comparison():
    """Show comprehensive model comparison inspired by bitcoin project"""
    st.header("📊 Model Performance Comparison")

    models_df = get_model_comparison()

    if models_df.empty:
        st.info("No trained models available for comparison")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Models",
            value=len(models_df),
            delta=f"{len(models_df[models_df['status'] == 'deployed'])} deployed",
        )

    with col2:
        best_model = models_df.loc[models_df["test_accuracy"].idxmax()]
        st.metric(
            label="Best Test Accuracy",
            value=f"{best_model['test_accuracy']:.4f}",
            delta=best_model["name"],
        )

    with col3:
        if models_df["rmse"].max() > 0:
            best_rmse = models_df[models_df["rmse"] > 0].loc[models_df["rmse"].idxmin()]
            st.metric(label="Best RMSE", value=f"{best_rmse['rmse']:.4f}", delta=best_rmse["name"])

    with col4:
        if models_df["r2"].max() > 0:
            best_r2 = models_df.loc[models_df["r2"].idxmax()]
            st.metric(label="Best R² Score", value=f"{best_r2['r2']:.4f}", delta=best_r2["name"])

    # Model comparison table
    st.subheader("Model Performance Table")

    # Select metrics to display
    display_cols = ["name", "version", "model_type", "test_accuracy", "test_loss"]

    if models_df["rmse"].max() > 0:
        display_cols.extend(["rmse", "mae", "r2"])

    display_cols.extend(["status", "created_at"])

    # Sort by test accuracy
    sorted_df = models_df[display_cols].sort_values("test_accuracy", ascending=False)

    st.dataframe(
        sorted_df.style.highlight_max(
            subset=["test_accuracy", "r2"], color="lightgreen"
        ).highlight_min(subset=["test_loss", "rmse", "mae"], color="lightgreen"),
        width="stretch",
    )

    # Visualization section
    st.subheader("Performance Visualizations")

    col1, col2 = st.columns(2)

    with col1:
        # Accuracy comparison
        fig = px.bar(
            sorted_df.head(10),
            x="name",
            y=["train_accuracy", "val_accuracy", "test_accuracy"],
            title="Accuracy Comparison (Train/Val/Test)",
            barmode="group",
            labels={"value": "Accuracy", "variable": "Split"},
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, width="stretch", config={"responsive": True})

    with col2:
        # Loss comparison
        fig = px.bar(
            sorted_df.head(10),
            x="name",
            y=["train_loss", "val_loss", "test_loss"],
            title="Loss Comparison (Train/Val/Test)",
            barmode="group",
            labels={"value": "Loss", "variable": "Split"},
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, width="stretch", config={"responsive": True})

    # Additional metrics if available
    if models_df["rmse"].max() > 0:
        col1, col2 = st.columns(2)

        with col1:
            # RMSE vs MAE
            valid_models = models_df[(models_df["rmse"] > 0) & (models_df["mae"] > 0)]
            fig = px.scatter(
                valid_models,
                x="rmse",
                y="mae",
                size="r2",
                color="model_type",
                hover_data=["name"],
                title="RMSE vs MAE (sized by R²)",
            )
            st.plotly_chart(fig, width="stretch", config={"responsive": True})

        with col2:
            # R² score comparison
            valid_r2 = models_df[models_df["r2"] > 0].sort_values("r2", ascending=False).head(10)
            fig = px.bar(
                valid_r2,
                x="name",
                y="r2",
                title="R² Score Comparison (Higher is Better)",
                color="r2",
                color_continuous_scale="Greens",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, width="stretch", config={"responsive": True})


def show_residual_analysis():
    """Show residual analysis for model predictions"""
    st.header("📈 Residual Analysis")

    models_df = get_model_comparison()

    if models_df.empty:
        st.info("No models available for analysis")
        return

    # Model selector
    model_options = models_df["name"].unique()
    selected_model = st.selectbox("Select Model for Analysis", model_options)

    # Generate simulated residuals (in real scenario, load actual predictions)
    np.random.seed(42)
    n_predictions = 500

    # Simulate predictions with realistic error patterns
    actual = np.random.normal(100, 20, n_predictions)
    predicted = actual + np.random.normal(0, 5, n_predictions)
    residuals = actual - predicted

    # Create tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Residuals Over Time", "Distribution", "Q-Q Plot", "Residuals vs Predicted"]
    )

    with tab1:
        st.subheader("Residuals Over Time")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                y=residuals,
                mode="lines+markers",
                name="Residuals",
                line=dict(color="blue", width=1),
            )
        )
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        fig.update_layout(
            xaxis_title="Prediction Index", yaxis_title="Residuals", hovermode="x unified"
        )
        st.plotly_chart(fig, width="stretch", config={"responsive": True})

        # Statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mean Residual", f"{np.mean(residuals):.4f}")
        with col2:
            st.metric("Std Residual", f"{np.std(residuals):.4f}")
        with col3:
            st.metric("Max Abs Residual", f"{np.max(np.abs(residuals)):.4f}")

    with tab2:
        st.subheader("Residual Distribution")
        fig = go.Figure()
        fig.add_trace(
            go.Histogram(x=residuals, nbinsx=50, name="Residuals", marker_color="lightblue")
        )

        # Add normal distribution overlay
        x_range = np.linspace(residuals.min(), residuals.max(), 100)
        y_norm = stats.norm.pdf(x_range, np.mean(residuals), np.std(residuals))
        y_norm_scaled = y_norm * len(residuals) * (residuals.max() - residuals.min()) / 50

        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=y_norm_scaled,
                mode="lines",
                name="Normal Distribution",
                line=dict(color="red", width=2),
            )
        )

        fig.update_layout(xaxis_title="Residuals", yaxis_title="Frequency", showlegend=True)
        st.plotly_chart(fig, width="stretch", config={"responsive": True})

        # Normality tests
        _, p_value = stats.normaltest(residuals)
        if p_value > 0.05:
            st.success(f"✅ Residuals appear normally distributed (p-value: {p_value:.4f})")
        else:
            st.warning(f"⚠️ Residuals may not be normally distributed (p-value: {p_value:.4f})")

    with tab3:
        st.subheader("Q-Q Plot")

        # Calculate theoretical quantiles
        (osm, osr), (slope, intercept, r) = stats.probplot(residuals, dist="norm")

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=osm,
                y=osr,
                mode="markers",
                name="Sample Quantiles",
                marker=dict(color="blue", size=5),
            )
        )

        # Add reference line
        fig.add_trace(
            go.Scatter(
                x=osm,
                y=slope * osm + intercept,
                mode="lines",
                name="Theoretical Line",
                line=dict(color="red", width=2, dash="dash"),
            )
        )

        fig.update_layout(
            xaxis_title="Theoretical Quantiles",
            yaxis_title="Sample Quantiles",
            title="Q-Q Plot (Normal Distribution)",
        )
        st.plotly_chart(fig, width="stretch", config={"responsive": True})

        st.info(f"Correlation with normal distribution: {r:.4f}")

    with tab4:
        st.subheader("Residuals vs Predicted Values")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=predicted,
                y=residuals,
                mode="markers",
                marker=dict(
                    color=np.abs(residuals),
                    colorscale="Reds",
                    showscale=True,
                    colorbar=dict(title="Abs Residual"),
                ),
            )
        )
        fig.add_hline(y=0, line_dash="dash", line_color="black")
        fig.update_layout(
            xaxis_title="Predicted Values",
            yaxis_title="Residuals",
            title="Residuals vs Predicted (looking for patterns)",
        )
        st.plotly_chart(fig, width="stretch", config={"responsive": True})

        st.info(
            "💡 Ideally, residuals should be randomly scattered around zero with no clear patterns."
        )


def show_feature_importance():
    """Show feature importance analysis"""
    st.header("🔍 Feature Importance Analysis")

    models_df = get_model_comparison()

    if models_df.empty:
        st.info("No models available for analysis")
        return

    # Model selector
    model_options = models_df["name"].unique()
    selected_model = st.selectbox("Select Model", model_options, key="feature_imp_model")

    # Get model details
    db = SessionLocal()
    try:
        model = db.query(Model).filter(Model.name == selected_model).first()

        if model and model.feature_names:
            # Generate simulated feature importance
            importance = np.random.dirichlet(np.ones(len(model.feature_names)))
            feature_df = pd.DataFrame(
                {"feature": model.feature_names, "importance": importance}
            ).sort_values("importance", ascending=False)

            # Top N features
            top_n = st.slider("Number of top features to show", 5, min(50, len(feature_df)), 20)
            top_features = feature_df.head(top_n)

            # Visualization
            fig = px.bar(
                top_features,
                y="feature",
                x="importance",
                orientation="h",
                title=f"Top {top_n} Most Important Features - {selected_model}",
                color="importance",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(height=600, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch", config={"responsive": True})

            # Feature importance table
            st.subheader("Feature Importance Table")
            st.dataframe(feature_df.head(top_n), width="stretch")

            # Feature categories (similar to bitcoin project)
            st.subheader("Feature Categories")

            # Categorize features
            categories = {
                "Lag Features": [f for f in feature_df["feature"] if "lag" in f.lower()],
                "Moving Averages": [
                    f
                    for f in feature_df["feature"]
                    if "ma" in f.lower() or "sma" in f.lower() or "ema" in f.lower()
                ],
                "Volatility": [
                    f
                    for f in feature_df["feature"]
                    if "volatility" in f.lower() or "std" in f.lower()
                ],
                "Price Changes": [
                    f for f in feature_df["feature"] if "change" in f.lower() or "pct" in f.lower()
                ],
                "Technical": [
                    f
                    for f in feature_df["feature"]
                    if any(x in f.lower() for x in ["rsi", "macd", "bollinger"])
                ],
                "Other": [],
            }

            # Assign uncategorized features
            all_categorized = set()
            for cat_features in categories.values():
                all_categorized.update(cat_features)

            categories["Other"] = [f for f in feature_df["feature"] if f not in all_categorized]

            # Calculate importance by category
            category_importance = {}
            for cat, features in categories.items():
                if features:
                    cat_imp = feature_df[feature_df["feature"].isin(features)]["importance"].sum()
                    category_importance[cat] = cat_imp

            if category_importance:
                cat_df = pd.DataFrame(
                    {
                        "Category": list(category_importance.keys()),
                        "Total Importance": list(category_importance.values()),
                    }
                ).sort_values("Total Importance", ascending=False)

                fig = px.pie(
                    cat_df,
                    values="Total Importance",
                    names="Category",
                    title="Feature Importance by Category",
                )
                st.plotly_chart(fig, width="stretch", config={"responsive": True})
        else:
            st.warning("No feature information available for this model")
    finally:
        db.close()


def show_training_history():
    """Show training history and experiments"""
    st.header("📚 Training History")

    jobs_df = get_training_jobs()

    if jobs_df.empty:
        st.info("No training jobs available")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Experiments", len(jobs_df))

    with col2:
        completed = len(jobs_df[jobs_df["status"] == "completed"])
        st.metric("Completed", completed)

    with col3:
        running = len(jobs_df[jobs_df["status"] == "running"])
        st.metric("Running", running)

    with col4:
        failed = len(jobs_df[jobs_df["status"] == "failed"])
        st.metric("Failed", failed)

    # Training jobs table
    st.subheader("Recent Training Jobs")

    display_df = jobs_df[["name", "status", "started_at", "duration_seconds"]].copy()
    display_df["duration_minutes"] = display_df["duration_seconds"] / 60

    st.dataframe(display_df, width="stretch")

    # Training duration distribution
    if not jobs_df["duration_seconds"].isna().all():
        valid_durations = jobs_df[jobs_df["duration_seconds"].notna()]

        fig = px.histogram(
            valid_durations,
            x="duration_seconds",
            nbins=30,
            title="Training Duration Distribution",
            labels={"duration_seconds": "Duration (seconds)"},
        )
        st.plotly_chart(fig, width="stretch", config={"responsive": True})


def main():
    """Main dashboard function"""
    st.title("🔬 ML Training Dashboard")
    st.markdown("Comprehensive model training analysis and comparison")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a view",
        ["Model Comparison", "Residual Analysis", "Feature Importance", "Training History"],
    )

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (60s)", value=True)
    if auto_refresh:
        import time

        time.sleep(60)
        st.rerun()

    # Manual refresh
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

    # Route to appropriate page
    if page == "Model Comparison":
        show_model_comparison()
    elif page == "Residual Analysis":
        show_residual_analysis()
    elif page == "Feature Importance":
        show_feature_importance()
    elif page == "Training History":
        show_training_history()


if __name__ == "__main__":
    main()
