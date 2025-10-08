"""Test suite for ML models

NOTE: ML model tests require torch and model modules.
Tests are conditional on torch installation.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Check for torch dependency
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Check for model modules
try:
    if HAS_TORCH:
        from mcli.ml.models.base_models import BaseStockModel, MLPBaseModel, ResNetModel
        from mcli.ml.models.ensemble_models import (
            AttentionStockPredictor,
            TransformerStockModel,
            LSTMStockPredictor,
            DeepEnsembleModel
        )
        from mcli.ml.models.recommendation_models import StockRecommendationModel
    HAS_MODELS = HAS_TORCH
except ImportError:
    HAS_MODELS = False

# Skip all tests if torch or models not available
if not HAS_MODELS:
    pytestmark = pytest.mark.skip(reason="torch or ML model modules not available")


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestBaseModels:
    """Test base model abstractions"""

    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing"""
        batch_size = 32
        input_dim = 100
        sequence_length = 30

        return {
            'X': torch.randn(batch_size, input_dim),
            'X_seq': torch.randn(batch_size, sequence_length, input_dim),
            'y': torch.randn(batch_size, 1),
            'y_multi': torch.randn(batch_size, 3)
        }

    def test_mlp_base_model(self, sample_data):
        """Test MLP base model"""
        model = MLPBaseModel(
            input_dim=100,
            hidden_dims=[64, 32],
            output_dim=1
        )

        # Test forward pass
        output = model(sample_data['X'])
        assert output.shape == (32, 1)

        # Test with different output dimensions
        model_multi = MLPBaseModel(
            input_dim=100,
            hidden_dims=[64, 32],
            output_dim=3
        )
        output_multi = model_multi(sample_data['X'])
        assert output_multi.shape == (32, 3)

    def test_resnet_model(self, sample_data):
        """Test ResNet model"""
        model = ResNetModel(
            input_dim=100,
            hidden_dims=[64, 64],
            output_dim=1
        )

        output = model(sample_data['X'])
        assert output.shape == (32, 1)

        # Verify residual connections work
        assert model.layers is not None

    def test_model_metrics_calculation(self):
        """Test metrics calculation"""
        model = MLPBaseModel(input_dim=10, hidden_dims=[5], output_dim=1)

        y_true = np.array([1.0, 2.0, 3.0, 4.0])
        y_pred = np.array([1.1, 2.1, 2.9, 3.8])

        metrics = model.calculate_metrics(y_true, y_pred)

        assert 'mae' in metrics
        assert 'rmse' in metrics
        assert 'r2' in metrics
        assert metrics['mae'] > 0


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestEnsembleModels:
    """Test ensemble and advanced models"""

    @pytest.fixture
    def sequence_data(self):
        """Generate sequence data for testing"""
        batch_size = 16
        sequence_length = 30
        input_dim = 50

        return torch.randn(batch_size, sequence_length, input_dim)

    def test_attention_model(self, sequence_data):
        """Test attention-based model"""
        model = AttentionStockPredictor(
            input_dim=50,
            hidden_dim=64,
            num_heads=4
        )

        output = model(sequence_data)
        assert output.shape == (16, 1)

    def test_transformer_model(self, sequence_data):
        """Test transformer model"""
        model = TransformerStockModel(
            input_dim=50,
            hidden_dim=64,
            num_heads=4,
            num_layers=2
        )

        output = model(sequence_data)
        assert output.shape == (16, 1)

    def test_lstm_model(self, sequence_data):
        """Test LSTM model"""
        model = LSTMStockPredictor(
            input_dim=50,
            hidden_dim=64,
            num_layers=2
        )

        output = model(sequence_data)
        assert output.shape == (16, 1)

    def test_deep_ensemble(self, sequence_data):
        """Test deep ensemble model"""
        models = [
            AttentionStockPredictor(50, 32, 2),
            LSTMStockPredictor(50, 32, 1),
        ]

        ensemble = DeepEnsembleModel(
            models=models,
            weights=[0.5, 0.5],
            voting_method='weighted_average'
        )

        output = ensemble(sequence_data)
        assert output.shape == (16, 1)

        # Test confidence calculation
        confidence = ensemble.get_prediction_confidence(sequence_data)
        assert confidence.shape == (16, 1)
        assert torch.all(confidence >= 0) and torch.all(confidence <= 1)


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestRecommendationModel:
    """Test stock recommendation model"""

    @pytest.fixture
    def mock_data(self):
        """Create mock data for testing"""
        batch_size = 10
        input_dim = 100

        return {
            'X': torch.randn(batch_size, input_dim),
            'tickers': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'FB',
                       'TSLA', 'NVDA', 'JPM', 'JNJ', 'V'],
            'market_data': {
                'market_cap': torch.randn(batch_size),
                'pe_ratio': torch.randn(batch_size),
                'volume': torch.randn(batch_size)
            }
        }

    def test_recommendation_generation(self, mock_data):
        """Test generating recommendations"""
        model = StockRecommendationModel(
            input_dim=100,
            hidden_dims=[64, 32]
        )

        # Set to eval mode to avoid dropout randomness
        model.eval()

        recommendations = model.generate_recommendations(
            mock_data['X'],
            mock_data['tickers'],
            mock_data['market_data']
        )

        assert len(recommendations) > 0
        assert all(hasattr(r, 'ticker') for r in recommendations)
        assert all(hasattr(r, 'action') for r in recommendations)
        assert all(hasattr(r, 'confidence') for r in recommendations)

    def test_multi_task_learning(self, mock_data):
        """Test multi-task learning outputs"""
        model = StockRecommendationModel(
            input_dim=100,
            hidden_dims=[64, 32],
            use_multi_task=True
        )

        returns, risks, confidence = model.forward_multi_task(mock_data['X'])

        assert returns.shape == (10, 1)
        assert risks.shape == (10, 1)
        assert confidence.shape == (10, 1)

    def test_portfolio_optimization(self, mock_data):
        """Test portfolio optimization integration"""
        model = StockRecommendationModel(
            input_dim=100,
            hidden_dims=[64, 32]
        )

        model.eval()

        # Mock optimizer
        with patch('mcli.ml.models.recommendation_models.AdvancedPortfolioOptimizer') as mock_optimizer:
            mock_instance = mock_optimizer.return_value
            mock_instance.optimize.return_value = np.array([0.2, 0.2, 0.2, 0.2, 0.2])

            portfolio = model.optimize_portfolio(
                mock_data['X'][:5],
                mock_data['tickers'][:5]
            )

            assert portfolio is not None
            assert 'weights' in portfolio
            assert len(portfolio['weights']) == 5


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestModelTraining:
    """Test model training functionality"""

    @pytest.fixture
    def training_setup(self):
        """Setup for training tests"""
        model = MLPBaseModel(
            input_dim=10,
            hidden_dims=[8, 4],
            output_dim=1
        )

        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = torch.nn.MSELoss()

        return model, optimizer, criterion

    def test_training_step(self, training_setup):
        """Test single training step"""
        model, optimizer, criterion = training_setup

        # Generate batch
        X = torch.randn(16, 10)
        y = torch.randn(16, 1)

        # Training step
        model.train()
        optimizer.zero_grad()

        output = model(X)
        loss = criterion(output, y)

        loss.backward()
        optimizer.step()

        assert loss.item() > 0

    def test_model_save_load(self, training_setup, tmp_path):
        """Test model saving and loading"""
        model, _, _ = training_setup

        # Save model
        save_path = tmp_path / "test_model.pt"
        torch.save(model.state_dict(), save_path)

        # Load model
        new_model = MLPBaseModel(
            input_dim=10,
            hidden_dims=[8, 4],
            output_dim=1
        )
        new_model.load_state_dict(torch.load(save_path))

        # Verify weights are same
        for p1, p2 in zip(model.parameters(), new_model.parameters()):
            assert torch.allclose(p1, p2)


@pytest.mark.skipif(not HAS_TORCH, reason="torch module not installed")
class TestModelValidation:
    """Test model validation and evaluation"""

    def test_prediction_bounds(self):
        """Test that predictions are within reasonable bounds"""
        model = StockRecommendationModel(
            input_dim=50,
            hidden_dims=[32, 16]
        )

        model.eval()
        X = torch.randn(10, 50)

        with torch.no_grad():
            predictions = model(X)

        # Check predictions are finite
        assert torch.all(torch.isfinite(predictions))

    def test_ensemble_consistency(self):
        """Test ensemble predictions are consistent"""
        models = [
            MLPBaseModel(50, [32], 1),
            MLPBaseModel(50, [32], 1)
        ]

        ensemble = DeepEnsembleModel(
            models=models,
            weights=[0.5, 0.5],
            voting_method='weighted_average'
        )

        X = torch.randn(5, 50)

        # Get multiple predictions
        ensemble.eval()
        with torch.no_grad():
            pred1 = ensemble(X)
            pred2 = ensemble(X)

        # Should be deterministic in eval mode
        assert torch.allclose(pred1, pred2)


@pytest.mark.parametrize("input_dim,hidden_dims,output_dim", [
    (10, [8, 4], 1),
    (50, [32, 16, 8], 3),
    (100, [64], 1),
])
def test_model_architectures(input_dim, hidden_dims, output_dim):
    """Parameterized test for different architectures"""
    model = MLPBaseModel(
        input_dim=input_dim,
        hidden_dims=hidden_dims,
        output_dim=output_dim
    )

    X = torch.randn(8, input_dim)
    output = model(X)

    assert output.shape == (8, output_dim)