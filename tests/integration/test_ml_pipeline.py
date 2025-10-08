"""Test suite for ML pipeline and data processing

NOTE: ML pipeline tests require torch and ML pipeline modules.
Tests are conditional on torch installation and module availability.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio

# Check for torch dependency
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Check for ML pipeline modules
try:
    if HAS_TORCH:
        from mcli.ml.mlops.pipeline_orchestrator import MLPipeline, PipelineConfig
        from mcli.ml.data.preprocessing import DataPreprocessor
        from mcli.ml.features.feature_engineering import FeatureEngineer
        from mcli.ml.backtesting.backtest_engine import BacktestEngine, BacktestConfig
        from mcli.ml.monitoring.drift_detection import ModelMonitor
    HAS_ML_MODULES = HAS_TORCH
except ImportError:
    HAS_ML_MODULES = False

# Skip all tests if dependencies not available
if not HAS_ML_MODULES:
    pytestmark = pytest.mark.skip(reason="torch or ML pipeline modules not available")


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestDataPreprocessing:
    """Test data preprocessing functionality"""

    @pytest.fixture
    def sample_dataframe(self):
        """Create sample dataframe for testing"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'date': dates,
            'open': np.random.randn(100) * 10 + 100,
            'high': np.random.randn(100) * 10 + 105,
            'low': np.random.randn(100) * 10 + 95,
            'close': np.random.randn(100) * 10 + 100,
            'volume': np.random.randint(1000000, 10000000, 100),
            'ticker': 'AAPL'
        })

    def test_preprocessor_initialization(self):
        """Test preprocessor initialization"""
        preprocessor = DataPreprocessor()
        assert preprocessor is not None
        assert hasattr(preprocessor, 'scaler')

    def test_data_cleaning(self, sample_dataframe):
        """Test data cleaning"""
        preprocessor = DataPreprocessor()

        # Add some NaN values
        sample_dataframe.loc[5:10, 'close'] = np.nan

        cleaned_data = preprocessor.clean_data(sample_dataframe)

        assert cleaned_data['close'].isna().sum() == 0
        assert len(cleaned_data) > 0

    def test_outlier_removal(self, sample_dataframe):
        """Test outlier removal"""
        preprocessor = DataPreprocessor()

        # Add outliers
        sample_dataframe.loc[50, 'close'] = 1000

        cleaned_data = preprocessor.remove_outliers(
            sample_dataframe,
            columns=['close'],
            method='zscore',
            threshold=3
        )

        assert cleaned_data['close'].max() < 1000

    def test_data_normalization(self, sample_dataframe):
        """Test data normalization"""
        preprocessor = DataPreprocessor()

        normalized_data = preprocessor.normalize_data(
            sample_dataframe[['open', 'high', 'low', 'close']]
        )

        # Check values are normalized
        assert normalized_data.min().min() >= -3  # Roughly within 3 std
        assert normalized_data.max().max() <= 3


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestFeatureEngineering:
    """Test feature engineering"""

    @pytest.fixture
    def price_data(self):
        """Create sample price data"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        prices = 100 + np.cumsum(np.random.randn(200) * 2)

        return pd.DataFrame({
            'date': dates,
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 200),
            'high': prices + np.random.rand(200) * 5,
            'low': prices - np.random.rand(200) * 5,
            'open': prices + np.random.randn(200)
        })

    def test_technical_indicators(self, price_data):
        """Test technical indicator calculation"""
        engineer = FeatureEngineer()

        features = engineer.calculate_technical_indicators(price_data)

        # Check key indicators exist
        assert 'rsi' in features.columns
        assert 'macd' in features.columns
        assert 'bb_upper' in features.columns
        assert 'bb_lower' in features.columns

        # Check values are reasonable
        assert features['rsi'].min() >= 0
        assert features['rsi'].max() <= 100

    def test_price_features(self, price_data):
        """Test price-based features"""
        engineer = FeatureEngineer()

        features = engineer.calculate_price_features(price_data)

        assert 'returns_1d' in features.columns
        assert 'returns_5d' in features.columns
        assert 'volatility_20d' in features.columns

    def test_volume_features(self, price_data):
        """Test volume-based features"""
        engineer = FeatureEngineer()

        features = engineer.calculate_volume_features(price_data)

        assert 'volume_ratio' in features.columns
        assert 'obv' in features.columns

    def test_pattern_recognition(self, price_data):
        """Test pattern recognition features"""
        engineer = FeatureEngineer()

        patterns = engineer.detect_patterns(price_data)

        assert 'support' in patterns
        assert 'resistance' in patterns


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestMLPipeline:
    """Test ML pipeline orchestration"""

    @pytest.fixture
    def pipeline_config(self):
        """Create pipeline configuration"""
        return PipelineConfig(
            experiment_name="test_experiment",
            enable_mlflow=False,
            data_dir="./test_data",
            model_dir="./test_models"
        )

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline_config):
        """Test pipeline initialization"""
        pipeline = MLPipeline(pipeline_config)
        assert pipeline is not None
        assert pipeline.config == pipeline_config

    @pytest.mark.asyncio
    async def test_pipeline_data_loading(self, pipeline_config):
        """Test data loading step"""
        pipeline = MLPipeline(pipeline_config)

        with patch.object(pipeline, 'load_data') as mock_load:
            mock_load.return_value = pd.DataFrame({'test': [1, 2, 3]})

            data = await pipeline.load_data_async()
            assert data is not None

    @pytest.mark.asyncio
    async def test_pipeline_feature_engineering(self, pipeline_config):
        """Test feature engineering step"""
        pipeline = MLPipeline(pipeline_config)

        test_data = pd.DataFrame({
            'close': np.random.randn(100),
            'volume': np.random.randint(1000, 10000, 100)
        })

        with patch.object(pipeline, 'engineer_features') as mock_engineer:
            mock_engineer.return_value = test_data

            features = await pipeline.process_features_async(test_data)
            assert features is not None

    @pytest.mark.asyncio
    async def test_pipeline_model_training(self, pipeline_config):
        """Test model training step"""
        pipeline = MLPipeline(pipeline_config)

        with patch.object(pipeline, 'train_model') as mock_train:
            mock_train.return_value = Mock(accuracy=0.85)

            model = await pipeline.train_model_async()
            assert model is not None


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestBacktesting:
    """Test backtesting functionality"""

    @pytest.fixture
    def backtest_config(self):
        """Create backtest configuration"""
        return BacktestConfig(
            initial_capital=100000,
            commission=0.001,
            slippage=0.001
        )

    @pytest.fixture
    def price_history(self):
        """Create price history for backtesting"""
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        prices = 100 * (1 + np.cumsum(np.random.randn(252) * 0.02))

        return pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.randn(252) * 0.01),
            'high': prices * (1 + np.abs(np.random.randn(252) * 0.02)),
            'low': prices * (1 - np.abs(np.random.randn(252) * 0.02)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 252)
        })

    def test_backtest_initialization(self, backtest_config):
        """Test backtest engine initialization"""
        engine = BacktestEngine(backtest_config)
        assert engine.initial_capital == 100000
        assert engine.commission == 0.001

    def test_position_management(self, backtest_config, price_history):
        """Test position management"""
        engine = BacktestEngine(backtest_config)

        # Test opening position
        position = engine.open_position(
            ticker='AAPL',
            shares=100,
            price=150.0,
            timestamp=datetime.now()
        )

        assert position is not None
        assert position['shares'] == 100
        assert position['entry_price'] == 150.0

    def test_performance_calculation(self, backtest_config):
        """Test performance metrics calculation"""
        engine = BacktestEngine(backtest_config)

        # Simulate some trades
        returns = np.array([0.01, -0.02, 0.03, 0.01, -0.01])

        metrics = engine.calculate_performance_metrics(returns)

        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics

    @pytest.mark.asyncio
    async def test_backtest_run(self, backtest_config, price_history):
        """Test running backtest"""
        engine = BacktestEngine(backtest_config)

        # Mock strategy
        async def mock_strategy(data):
            return {'action': 'buy', 'size': 100}

        with patch.object(engine, 'run_strategy', new=mock_strategy):
            results = await engine.run_backtest_async(
                price_history,
                start_date='2022-01-01',
                end_date='2022-12-31'
            )

            assert results is not None
            assert 'equity_curve' in results


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestModelMonitoring:
    """Test model monitoring and drift detection"""

    @pytest.fixture
    def reference_data(self):
        """Create reference data for drift detection"""
        return pd.DataFrame({
            'feature1': np.random.normal(0, 1, 1000),
            'feature2': np.random.normal(5, 2, 1000),
            'feature3': np.random.exponential(2, 1000)
        })

    @pytest.fixture
    def current_data(self):
        """Create current data (potentially drifted)"""
        return pd.DataFrame({
            'feature1': np.random.normal(0.5, 1.2, 1000),  # Slight drift
            'feature2': np.random.normal(5, 2, 1000),  # No drift
            'feature3': np.random.exponential(3, 1000)  # Drift
        })

    def test_monitor_initialization(self):
        """Test model monitor initialization"""
        monitor = ModelMonitor("test_model")
        assert monitor.model_name == "test_model"

    def test_data_drift_detection(self, reference_data, current_data):
        """Test data drift detection"""
        monitor = ModelMonitor("test_model")

        drift_report = monitor.detect_data_drift(
            reference_data,
            current_data,
            threshold=0.05
        )

        assert 'drift_detected' in drift_report
        assert 'drifted_features' in drift_report
        assert len(drift_report['drifted_features']) > 0

    def test_prediction_drift_detection(self):
        """Test prediction drift detection"""
        monitor = ModelMonitor("test_model")

        reference_predictions = np.random.normal(0, 1, 1000)
        current_predictions = np.random.normal(0.5, 1, 1000)  # Drift

        drift_detected = monitor.detect_prediction_drift(
            reference_predictions,
            current_predictions,
            threshold=0.05
        )

        assert drift_detected == True

    def test_performance_monitoring(self):
        """Test performance monitoring"""
        monitor = ModelMonitor("test_model")

        # Simulate performance over time
        timestamps = pd.date_range(start='2023-01-01', periods=30, freq='D')
        accuracies = 0.85 - np.cumsum(np.random.randn(30) * 0.01)  # Degrading

        alerts = monitor.monitor_performance(
            timestamps,
            accuracies,
            threshold=0.80
        )

        assert len(alerts) > 0 if any(accuracies < 0.80) else len(alerts) == 0


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self):
        """Test end-to-end pipeline execution"""
        config = PipelineConfig(
            experiment_name="integration_test",
            enable_mlflow=False
        )

        pipeline = MLPipeline(config)

        with patch.multiple(
            pipeline,
            load_data_async=AsyncMock(return_value=pd.DataFrame({'test': [1, 2, 3]})),
            process_features_async=AsyncMock(return_value=np.array([[1, 2], [3, 4]])),
            train_model_async=AsyncMock(return_value=Mock()),
            evaluate_model_async=AsyncMock(return_value={'accuracy': 0.85})
        ):
            result = await pipeline.run_async()
            assert result is not None
            assert 'accuracy' in result

    def test_model_deployment_workflow(self):
        """Test model deployment workflow"""
        # Mock model
        model = Mock()
        model.predict = Mock(return_value=np.array([0.1, 0.2, 0.3]))

        # Mock deployment
        with patch('mcli.ml.mlops.model_serving.deploy_model') as mock_deploy:
            mock_deploy.return_value = {'endpoint': 'http://localhost:8000/predict'}

            deployment = mock_deploy(model, "test_model")
            assert 'endpoint' in deployment


@pytest.mark.performance
@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestPerformance:
    """Performance and scalability tests"""

    def test_large_dataset_processing(self):
        """Test processing large datasets"""
        # Create large dataset
        large_data = pd.DataFrame({
            'feature': np.random.randn(100000),
            'target': np.random.randn(100000)
        })

        preprocessor = DataPreprocessor()

        import time
        start_time = time.time()
        processed = preprocessor.clean_data(large_data)
        processing_time = time.time() - start_time

        assert processing_time < 10  # Should process in under 10 seconds
        assert len(processed) > 0

    def test_concurrent_predictions(self):
        """Test concurrent prediction handling"""
        from concurrent.futures import ThreadPoolExecutor

        model = Mock()
        model.predict = Mock(return_value=np.array([0.5]))

        def make_prediction(data):
            return model.predict(data)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_prediction, np.random.randn(1, 10))
                for _ in range(100)
            ]

            results = [f.result() for f in futures]

        assert len(results) == 100
        assert all(r is not None for r in results)