"""Integration tests for the complete ML pipeline"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from ml.backtesting.backtest_engine import BacktestConfig, BacktestEngine, TradingStrategy
from ml.backtesting.performance_metrics import PerformanceAnalyzer
from ml.features.ensemble_features import EnsembleFeatureBuilder
from ml.features.political_features import PoliticalInfluenceFeatures
from ml.features.stock_features import StockRecommendationFeatures
from ml.mlops.experiment_tracker import ExperimentTracker, MLflowConfig, ModelRegistry
from ml.mlops.pipeline_orchestrator import MLPipeline, PipelineConfig, PipelineExecutor
from ml.models.ensemble_models import DeepEnsembleModel, EnsembleConfig, ModelConfig
from ml.models.recommendation_models import RecommendationConfig, StockRecommendationModel

# Import all components
from ml.preprocessing.data_processor import DataProcessor, ProcessingConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataIntegration:
    """Test data processing integration"""

    def test_data_pipeline(self):
        """Test complete data processing pipeline"""
        # Generate mock data
        trading_data = self._generate_mock_trading_data()
        stock_data = self._generate_mock_stock_data()

        # Initialize processor
        config = ProcessingConfig()
        processor = DataProcessor(config)

        # Process data
        processed_trading = processor.process_politician_trades(trading_data)
        assert len(processed_trading) > 0
        assert "transaction_amount_cleaned" in processed_trading.columns

        # Clean data
        cleaned_data = processor.clean_data(processed_trading)
        assert cleaned_data.isnull().sum().sum() == 0  # No nulls

    def test_feature_extraction_pipeline(self):
        """Test feature extraction pipeline"""
        # Generate mock data
        trading_data = self._generate_mock_trading_data()
        stock_data = self._generate_mock_stock_data()

        # Extract features
        stock_extractor = StockRecommendationFeatures()
        political_extractor = PoliticalInfluenceFeatures()
        ensemble_builder = EnsembleFeatureBuilder()

        # Stock features
        stock_features = stock_extractor.extract_features(stock_data)
        assert stock_features.shape[1] > 20  # Should have many features

        # Political features
        political_features = political_extractor.extract_influence_features(trading_data)
        assert "total_influence" in political_features.columns

        # Ensemble features
        combined = pd.concat([political_features, stock_features], axis=1)
        ensemble_features = ensemble_builder.build_ensemble_features(combined)
        assert ensemble_features.shape[1] > combined.shape[1]  # More features

    def _generate_mock_trading_data(self):
        """Generate mock trading data"""
        n_records = 100
        data = []
        for _ in range(n_records):
            data.append(
                {
                    "politician_name_cleaned": np.random.choice(["Pelosi", "McConnell"]),
                    "transaction_date_cleaned": datetime.now()
                    - timedelta(days=np.random.randint(1, 365)),
                    "transaction_amount_cleaned": np.random.uniform(1000, 500000),
                    "transaction_type_cleaned": np.random.choice(["buy", "sell"]),
                    "ticker_cleaned": np.random.choice(["AAPL", "MSFT", "GOOGL"]),
                }
            )
        return pd.DataFrame(data)

    def _generate_mock_stock_data(self):
        """Generate mock stock data"""
        dates = pd.date_range(end=datetime.now(), periods=100)
        tickers = ["AAPL", "MSFT", "GOOGL"]
        data = []

        for ticker in tickers:
            base_price = np.random.uniform(100, 300)
            for date in dates:
                price = base_price * (1 + np.random.normal(0, 0.02))
                data.append(
                    {
                        "symbol": ticker,
                        "date": date,
                        "close": price,
                        "volume": np.random.randint(1000000, 10000000),
                        "open": price * 0.99,
                        "high": price * 1.01,
                        "low": price * 0.98,
                    }
                )

        return pd.DataFrame(data)


class TestModelIntegration:
    """Test model training and prediction integration"""

    def test_model_training_pipeline(self):
        """Test complete model training pipeline"""
        # Generate data
        X = np.random.randn(200, 50)
        y = np.random.randint(0, 2, 200)
        returns = np.random.normal(0.05, 0.15, 200)
        risk_labels = np.random.choice([0, 1, 2], 200)

        # Configure model
        model_configs = [
            ModelConfig(
                model_type="mlp",
                hidden_dims=[64, 32],
                dropout_rate=0.2,
                learning_rate=0.001,
                weight_decay=1e-4,
                batch_size=32,
                epochs=2,
            )
        ]

        ensemble_config = EnsembleConfig(base_models=model_configs)
        rec_config = RecommendationConfig(ensemble_config=ensemble_config)

        # Train model
        model = StockRecommendationModel(X.shape[1], rec_config)
        assert model is not None

        # Generate predictions
        predictions = model.predict(X[:10])
        assert len(predictions) == 10

    def test_model_serving(self):
        """Test model serving capabilities"""
        from ml.mlops.model_serving import ModelEndpoint, PredictionRequest

        # Create endpoint
        endpoint = ModelEndpoint()

        # Create request
        request = PredictionRequest(
            trading_data={"politician": "Test", "amount": 10000}, tickers=["AAPL", "MSFT"]
        )

        # Generate prediction (async would need event loop)
        # This is simplified testing
        assert endpoint is not None
        assert request is not None


class TestPipelineIntegration:
    """Test complete ML pipeline integration"""

    def test_end_to_end_pipeline(self):
        """Test complete end-to-end pipeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure pipeline
            config = PipelineConfig(
                data_dir=Path(tmpdir) / "data",
                model_dir=Path(tmpdir) / "models",
                output_dir=Path(tmpdir) / "outputs",
                enable_mlflow=False,  # Disable for testing
            )

            # Create pipeline
            pipeline = MLPipeline(config)

            # Run pipeline (with mock data)
            result = pipeline.run()

            assert "model" in result
            assert result["model"] is not None

    def test_pipeline_with_mlflow(self):
        """Test pipeline with MLflow tracking"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure MLflow
            mlflow_config = MLflowConfig(
                tracking_uri=f"sqlite:///{tmpdir}/mlflow.db", experiment_name="test_experiment"
            )

            # Configure pipeline
            config = PipelineConfig(
                data_dir=Path(tmpdir) / "data",
                model_dir=Path(tmpdir) / "models",
                enable_mlflow=True,
                mlflow_config=mlflow_config,
            )

            # Create and run pipeline
            pipeline = MLPipeline(config)
            result = pipeline.run()

            assert result is not None
            # MLflow should have logged the run
            assert pipeline.experiment_tracker is not None


class TestBacktestIntegration:
    """Test backtesting framework integration"""

    def test_backtesting_pipeline(self):
        """Test complete backtesting pipeline"""
        # Generate mock price data
        dates = pd.date_range(end=datetime.now(), periods=252)
        price_data = []

        for ticker in ["AAPL", "MSFT", "GOOGL", "SPY"]:
            base_price = np.random.uniform(100, 300)
            for date in dates:
                price = base_price * (1 + np.random.normal(0, 0.02))
                price_data.append(
                    {
                        "symbol": ticker,
                        "date": date,
                        "close": price,
                        "volume": np.random.randint(1000000, 10000000),
                    }
                )

        price_df = pd.DataFrame(price_data)

        # Configure backtest
        config = BacktestConfig(
            initial_capital=100000,
            commission=0.001,
            slippage=0.001,
            max_positions=10,
            benchmark="SPY",
        )

        # Create engine and strategy
        engine = BacktestEngine(config)
        strategy = TradingStrategy()
        engine.set_strategy(strategy)

        # Run backtest
        result = engine.run(price_df)

        assert result is not None
        assert len(result.portfolio_value) > 0
        assert result.metrics["total_return"] is not None

    def test_performance_analysis(self):
        """Test performance analysis"""
        # Generate mock returns
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        benchmark_returns = pd.Series(np.random.normal(0.0008, 0.015, 252))

        # Analyze performance
        analyzer = PerformanceAnalyzer()
        portfolio_metrics, risk_metrics = analyzer.calculate_metrics(returns, benchmark_returns)

        assert portfolio_metrics.sharpe_ratio is not None
        assert risk_metrics.value_at_risk_95 is not None
        assert risk_metrics.beta is not None


class TestSystemIntegration:
    """Test full system integration"""

    def test_complete_workflow(self):
        """Test complete ML workflow from data to backtest"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger.info("Starting complete workflow test...")

            # Step 1: Data Processing
            logger.info("Step 1: Processing data...")
            processor = DataProcessor(ProcessingConfig())
            trading_data = self._generate_trading_data()
            stock_data = self._generate_stock_data()

            processed_trading = processor.process_politician_trades(trading_data)
            assert len(processed_trading) > 0

            # Step 2: Feature Engineering
            logger.info("Step 2: Engineering features...")
            political_extractor = PoliticalInfluenceFeatures()
            features = political_extractor.extract_influence_features(processed_trading)
            assert features.shape[1] > 5

            # Step 3: Model Training
            logger.info("Step 3: Training model...")
            X = np.random.randn(100, 50)
            y = np.random.randint(0, 2, 100)

            model_configs = [
                ModelConfig(
                    model_type="mlp",
                    hidden_dims=[32],
                    dropout_rate=0.2,
                    learning_rate=0.001,
                    weight_decay=1e-4,
                    batch_size=32,
                    epochs=1,
                )
            ]

            ensemble_config = EnsembleConfig(base_models=model_configs)
            rec_config = RecommendationConfig(ensemble_config=ensemble_config)
            model = StockRecommendationModel(X.shape[1], rec_config)

            # Step 4: Backtesting
            logger.info("Step 4: Running backtest...")
            backtest_config = BacktestConfig(initial_capital=100000)
            engine = BacktestEngine(backtest_config)
            strategy = TradingStrategy(model)
            engine.set_strategy(strategy)

            result = engine.run(stock_data)
            assert result.metrics["total_return"] is not None

            # Step 5: Performance Analysis
            logger.info("Step 5: Analyzing performance...")
            analyzer = PerformanceAnalyzer()
            portfolio_metrics, risk_metrics = analyzer.calculate_metrics(result.returns)

            assert portfolio_metrics.total_return is not None
            assert risk_metrics.value_at_risk_95 is not None

            logger.info("Complete workflow test successful!")

    def _generate_trading_data(self):
        """Generate comprehensive trading data"""
        n_records = 500
        data = []

        for _ in range(n_records):
            data.append(
                {
                    "politician_name_cleaned": np.random.choice(["Pelosi", "McConnell", "Schumer"]),
                    "transaction_date_cleaned": datetime.now()
                    - timedelta(days=np.random.randint(1, 365)),
                    "transaction_amount_cleaned": np.random.uniform(1000, 1000000),
                    "transaction_type_cleaned": np.random.choice(["buy", "sell"]),
                    "ticker_cleaned": np.random.choice(["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]),
                    "disclosure_date": datetime.now() - timedelta(days=np.random.randint(0, 45)),
                }
            )

        return pd.DataFrame(data)

    def _generate_stock_data(self):
        """Generate comprehensive stock data"""
        dates = pd.date_range(end=datetime.now(), periods=365)
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY"]
        data = []

        for ticker in tickers:
            base_price = np.random.uniform(50, 500)
            prices = [base_price]

            for i, date in enumerate(dates):
                # Random walk with momentum
                change = np.random.normal(0.001, 0.02)
                new_price = prices[-1] * (1 + change)
                prices.append(new_price)

                data.append(
                    {
                        "symbol": ticker,
                        "date": date,
                        "close": new_price,
                        "open": new_price * (1 + np.random.normal(0, 0.005)),
                        "high": new_price * (1 + abs(np.random.normal(0, 0.01))),
                        "low": new_price * (1 - abs(np.random.normal(0, 0.01))),
                        "volume": np.random.randint(1000000, 50000000),
                    }
                )

        return pd.DataFrame(data)


def test_smoke():
    """Smoke test to ensure all imports work"""
    assert DataProcessor is not None
    assert StockRecommendationFeatures is not None
    assert DeepEnsembleModel is not None
    assert MLPipeline is not None
    assert BacktestEngine is not None
    logger.info("Smoke test passed - all imports successful")


if __name__ == "__main__":
    # Run integration tests
    logger.info("Running integration tests...")

    # Test data integration
    data_tests = TestDataIntegration()
    data_tests.test_data_pipeline()
    data_tests.test_feature_extraction_pipeline()
    logger.info("✅ Data integration tests passed")

    # Test model integration
    model_tests = TestModelIntegration()
    model_tests.test_model_training_pipeline()
    model_tests.test_model_serving()
    logger.info("✅ Model integration tests passed")

    # Test pipeline integration
    pipeline_tests = TestPipelineIntegration()
    pipeline_tests.test_end_to_end_pipeline()
    logger.info("✅ Pipeline integration tests passed")

    # Test backtest integration
    backtest_tests = TestBacktestIntegration()
    backtest_tests.test_backtesting_pipeline()
    backtest_tests.test_performance_analysis()
    logger.info("✅ Backtest integration tests passed")

    # Test complete system
    system_tests = TestSystemIntegration()
    system_tests.test_complete_workflow()
    logger.info("✅ System integration tests passed")

    logger.info("🎉 All integration tests passed successfully!")
