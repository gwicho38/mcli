"""Unit tests for training dashboard functionality"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.orm import Session

from mcli.ml.database.models import Experiment, Model, ModelStatus


class TestTrainingDashboard:
    """Test suite for training dashboard functions"""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def sample_models(self):
        """Create sample model data"""
        models = []

        # Bitcoin-style model comparison data
        model_configs = [
            {
                "name": "Random Forest",
                "type": "random_forest",
                "test_rmse": 150.5,
                "test_mae": 120.3,
                "test_r2": 0.85,
                "mape": 5.5,
            },
            {
                "name": "Gradient Boosting",
                "type": "gradient_boosting",
                "test_rmse": 155.2,
                "test_mae": 125.8,
                "test_r2": 0.83,
                "mape": 6.2,
            },
            {
                "name": "Linear Regression",
                "type": "linear_regression",
                "test_rmse": 180.0,
                "test_mae": 145.0,
                "test_r2": 0.75,
                "mape": 8.5,
            },
            {
                "name": "Ridge Regression",
                "type": "ridge",
                "test_rmse": 175.5,
                "test_mae": 140.2,
                "test_r2": 0.78,
                "mape": 7.8,
            },
            {
                "name": "Lasso Regression",
                "type": "lasso",
                "test_rmse": 178.0,
                "test_mae": 142.5,
                "test_r2": 0.76,
                "mape": 8.1,
            },
        ]

        for i, config in enumerate(model_configs):
            model = Mock(spec=Model)
            model.id = f"model-{i}"
            model.name = config["name"]
            model.version = "1.0.0"
            model.model_type = config["type"]
            model.status = ModelStatus.DEPLOYED if i < 2 else ModelStatus.TRAINED

            model.train_accuracy = 0.90 + np.random.uniform(-0.05, 0.05)
            model.val_accuracy = 0.88 + np.random.uniform(-0.05, 0.05)
            model.test_accuracy = 0.85 + np.random.uniform(-0.05, 0.05)

            model.train_loss = 0.15 + np.random.uniform(-0.05, 0.05)
            model.val_loss = 0.18 + np.random.uniform(-0.05, 0.05)
            model.test_loss = 0.20 + np.random.uniform(-0.05, 0.05)

            # Bitcoin-style metrics
            model.test_rmse = config["test_rmse"]
            model.test_mae = config["test_mae"]
            model.test_r2 = config["test_r2"]

            model.metrics = {
                "rmse": config["test_rmse"],
                "mae": config["test_mae"],
                "r2": config["test_r2"],
                "mape": config["mape"],
            }

            # Feature names
            model.feature_names = [
                "lag_1",
                "lag_7",
                "lag_30",
                "ma_7",
                "ma_14",
                "ma_30",
                "volatility_7",
                "volatility_14",
                "price_change_1",
                "price_change_7",
            ]

            model.created_at = datetime.utcnow() - timedelta(days=i)
            model.updated_at = datetime.utcnow()

            models.append(model)

        return models

    @pytest.fixture
    def sample_experiments(self):
        """Create sample experiment data"""
        experiments = []

        for i in range(10):
            exp = Mock(spec=Experiment)
            exp.id = f"exp-{i}"
            exp.name = f"Experiment {i}"
            exp.status = "completed" if i < 7 else ("running" if i < 9 else "failed")
            exp.started_at = datetime.utcnow() - timedelta(hours=i * 2)
            exp.completed_at = (
                datetime.utcnow() - timedelta(hours=i * 2 - 1)
                if exp.status == "completed"
                else None
            )
            exp.duration_seconds = 3600 if exp.status == "completed" else None

            exp.hyperparameters = {"learning_rate": 0.01, "n_estimators": 100, "max_depth": 10}

            exp.train_metrics = {"loss": 0.15, "accuracy": 0.90}
            exp.val_metrics = {"loss": 0.18, "accuracy": 0.88}
            exp.test_metrics = {"loss": 0.20, "accuracy": 0.85}

            experiments.append(exp)

        return experiments

    def test_model_comparison_metrics(self, sample_models):
        """Test model comparison metrics calculation"""
        # Convert to DataFrame as the dashboard would
        df = pd.DataFrame(
            [
                {
                    "name": m.name,
                    "test_rmse": m.test_rmse,
                    "test_mae": m.test_mae,
                    "test_r2": m.test_r2,
                    "mape": m.metrics["mape"],
                }
                for m in sample_models
            ]
        )

        # Test ranking by RMSE
        sorted_by_rmse = df.sort_values("test_rmse")
        assert sorted_by_rmse.iloc[0]["name"] == "Random Forest"
        assert sorted_by_rmse.iloc[0]["test_rmse"] < 155

        # Test ranking by R²
        sorted_by_r2 = df.sort_values("test_r2", ascending=False)
        assert sorted_by_r2.iloc[0]["test_r2"] > 0.8

        # Test ranking by MAE
        sorted_by_mae = df.sort_values("test_mae")
        assert sorted_by_mae.iloc[0]["test_mae"] < 125

    def test_model_performance_aggregation(self, sample_models):
        """Test aggregation of model performance"""
        metrics = {
            "total_models": len(sample_models),
            "deployed_models": sum(1 for m in sample_models if m.status == ModelStatus.DEPLOYED),
            "avg_rmse": np.mean([m.test_rmse for m in sample_models]),
            "avg_r2": np.mean([m.test_r2 for m in sample_models]),
        }

        assert metrics["total_models"] == 5
        assert metrics["deployed_models"] == 2
        assert 150 < metrics["avg_rmse"] < 180
        assert 0.75 < metrics["avg_r2"] < 0.85

    def test_feature_importance_calculation(self, sample_models):
        """Test feature importance extraction and ranking"""
        model = sample_models[0]

        # Simulate feature importance
        importance = np.random.dirichlet(np.ones(len(model.feature_names)))
        feature_df = pd.DataFrame(
            {"feature": model.feature_names, "importance": importance}
        ).sort_values("importance", ascending=False)

        # Test that importances sum to 1
        assert np.isclose(feature_df["importance"].sum(), 1.0)

        # Test top features
        top_5 = feature_df.head(5)
        assert len(top_5) == 5
        assert all(top_5["importance"] > 0)

    def test_residuals_analysis(self):
        """Test residual analysis calculations"""
        # Generate sample predictions and actuals
        np.random.seed(42)
        n = 500

        actual = np.random.normal(100, 20, n)
        predicted = actual + np.random.normal(0, 5, n)
        residuals = actual - predicted

        # Test residual statistics
        mean_residual = np.mean(residuals)
        std_residual = np.std(residuals)
        max_abs_residual = np.max(np.abs(residuals))

        assert abs(mean_residual) < 1  # Should be close to 0
        assert std_residual > 0
        assert max_abs_residual > std_residual

        # Test normality (using simple statistics)
        from scipy import stats

        _, p_value = stats.normaltest(residuals)
        # With random data, should generally pass normality test
        assert 0 <= p_value <= 1

    def test_cross_validation_metrics(self):
        """Test cross-validation metrics calculation"""
        # Simulate CV scores
        cv_scores = [0.80, 0.82, 0.78, 0.85, 0.79]

        cv_mean = np.mean(cv_scores)
        cv_std = np.std(cv_scores)

        assert 0.75 < cv_mean < 0.85
        assert cv_std < 0.05

        # Test that std is reasonable (not too high)
        assert cv_std / cv_mean < 0.1  # Coefficient of variation < 10%

    def test_training_duration_analysis(self, sample_experiments):
        """Test training duration analysis"""
        completed = [exp for exp in sample_experiments if exp.status == "completed"]

        durations = [exp.duration_seconds for exp in completed]
        avg_duration = np.mean(durations)
        max_duration = np.max(durations)
        min_duration = np.min(durations)

        assert all(d > 0 for d in durations)
        assert min_duration <= avg_duration <= max_duration

    def test_model_comparison_ranking(self, sample_models):
        """Test ranking models by multiple metrics"""
        df = pd.DataFrame(
            [
                {
                    "name": m.name,
                    "test_rmse": m.test_rmse,
                    "test_mae": m.test_mae,
                    "test_r2": m.test_r2,
                }
                for m in sample_models
            ]
        )

        # Rank by RMSE (lower is better)
        df["rank_rmse"] = df["test_rmse"].rank()

        # Rank by R² (higher is better)
        df["rank_r2"] = df["test_r2"].rank(ascending=False)

        # Composite rank
        df["composite_rank"] = (df["rank_rmse"] + df["rank_r2"]) / 2

        best_overall = df.loc[df["composite_rank"].idxmin()]

        # Random Forest should be among the best
        assert best_overall["test_r2"] > 0.8
        assert best_overall["test_rmse"] < 160

    def test_feature_categorization(self):
        """Test feature categorization (lag, MA, volatility, etc.)"""
        features = [
            "lag_1",
            "lag_7",
            "lag_30",
            "ma_7",
            "ma_14",
            "sma_30",
            "ema_20",
            "volatility_7",
            "volatility_14",
            "std_30",
            "price_change_1",
            "pct_change_7",
            "rsi_14",
            "macd",
            "bollinger_upper",
        ]

        categories = {
            "Lag Features": [f for f in features if "lag" in f.lower()],
            "Moving Averages": [
                f for f in features if any(x in f.lower() for x in ["ma", "sma", "ema"])
            ],
            "Volatility": [
                f for f in features if any(x in f.lower() for x in ["volatility", "std"])
            ],
            "Price Changes": [f for f in features if "change" in f.lower() or "pct" in f.lower()],
            "Technical": [
                f for f in features if any(x in f.lower() for x in ["rsi", "macd", "bollinger"])
            ],
        }

        assert len(categories["Lag Features"]) == 3
        assert len(categories["Moving Averages"]) == 4
        assert len(categories["Volatility"]) == 3
        assert len(categories["Price Changes"]) == 2
        assert len(categories["Technical"]) == 3

    def test_mape_calculation(self):
        """Test Mean Absolute Percentage Error calculation"""
        actual = np.array([100, 200, 150, 300, 250])
        predicted = np.array([105, 195, 160, 295, 245])

        mape = np.mean(np.abs((actual - predicted) / actual)) * 100

        assert 0 <= mape <= 100
        assert mape < 10  # Should be reasonably low for good predictions

    def test_error_metrics_comparison(self):
        """Test that RMSE >= MAE for any predictions"""
        # This is a mathematical property: RMSE is always >= MAE

        errors = np.array([5, 3, 8, 2, 10])

        mae = np.mean(np.abs(errors))
        rmse = np.sqrt(np.mean(errors**2))

        assert rmse >= mae

    def test_r2_score_properties(self):
        """Test R² score properties"""
        # Perfect predictions
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1, 2, 3, 4, 5])

        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot)

        assert np.isclose(r2, 1.0)

        # Random predictions
        y_pred_random = np.array([2, 3, 1, 5, 4])
        ss_res_random = np.sum((y_true - y_pred_random) ** 2)
        r2_random = 1 - (ss_res_random / ss_tot)

        assert r2_random < 1.0

    def test_experiment_status_distribution(self, sample_experiments):
        """Test experiment status distribution"""
        status_counts = {}
        for exp in sample_experiments:
            status_counts[exp.status] = status_counts.get(exp.status, 0) + 1

        assert status_counts["completed"] == 7
        assert status_counts["running"] == 2
        assert status_counts["failed"] == 1
        assert sum(status_counts.values()) == 10


class TestModelVersioning:
    """Test model versioning functionality"""

    def test_version_comparison(self):
        """Test semantic version comparison"""
        versions = ["1.0.0", "1.1.0", "1.0.1", "2.0.0", "1.2.0"]

        # Parse and sort versions
        parsed = [tuple(map(int, v.split("."))) for v in versions]
        sorted_versions = sorted(parsed)

        assert sorted_versions[0] == (1, 0, 0)
        assert sorted_versions[-1] == (2, 0, 0)

    def test_model_deployment_tracking(self):
        """Test tracking which models are deployed"""
        models = [
            {"name": "model-a", "version": "1.0.0", "deployed": True},
            {"name": "model-a", "version": "1.1.0", "deployed": False},
            {"name": "model-b", "version": "1.0.0", "deployed": True},
        ]

        deployed = [m for m in models if m["deployed"]]
        assert len(deployed) == 2

        # Test that only one version of each model is deployed
        deployed_names = [m["name"] for m in deployed]
        assert len(deployed_names) == len(set(deployed_names))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
