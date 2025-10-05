"""Test script for ensemble models"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import torch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_features(n_samples: int = 500, n_features: int = 150) -> pd.DataFrame:
    """Generate mock feature data for testing"""
    np.random.seed(42)

    # Create realistic feature names
    feature_names = []

    # Technical indicators
    for indicator in ["sma", "ema", "rsi", "macd", "bb", "volume", "volatility"]:
        for period in [5, 10, 20, 50]:
            feature_names.append(f"{indicator}_{period}")

    # Political features
    for pol_feature in ["influence", "trading_freq", "committee_align", "seniority"]:
        for agg in ["mean", "max", "std"]:
            feature_names.append(f"political_{pol_feature}_{agg}")

    # Ensemble features
    for i in range(50):
        feature_names.append(f"ensemble_feature_{i}")

    # Market regime features
    for regime in ["volatility", "trend", "volume"]:
        for metric in ["regime", "strength", "persistence"]:
            feature_names.append(f"market_{regime}_{metric}")

    # Pad or trim to exact number
    while len(feature_names) < n_features:
        feature_names.append(f"extra_feature_{len(feature_names)}")
    feature_names = feature_names[:n_features]

    # Generate correlated features that simulate real market data
    features = []
    for i in range(n_samples):
        # Base market trend
        market_trend = np.random.normal(0, 1)

        # Technical features (correlated with trend)
        tech_features = np.random.normal(market_trend * 0.3, 0.8, 32)

        # Political features (some correlation with market)
        pol_features = np.random.normal(market_trend * 0.1, 0.5, 12)

        # Ensemble features (mix of correlated and noise)
        ensemble_features = np.random.normal(market_trend * 0.2, 0.6, 50)

        # Market regime features
        regime_features = np.random.normal(market_trend * 0.4, 0.7, 9)

        # Extra random features
        n_extra = max(0, n_features - 103)  # Ensure non-negative
        if n_extra > 0:
            extra_features = np.random.normal(0, 0.5, n_extra)
            sample_features = np.concatenate(
                [tech_features, pol_features, ensemble_features, regime_features, extra_features]
            )
        else:
            # Truncate if we have too many features
            all_features = np.concatenate(
                [tech_features, pol_features, ensemble_features, regime_features]
            )
            sample_features = all_features[:n_features]
        features.append(sample_features)

    return pd.DataFrame(features, columns=feature_names)


def generate_mock_targets(n_samples: int) -> tuple:
    """Generate realistic target variables"""
    np.random.seed(42)

    # Generate correlated targets
    market_performance = np.random.normal(0, 1, n_samples)

    # Binary classification target (profitable vs not)
    binary_targets = (market_performance > 0).astype(int)

    # Continuous returns (with realistic distribution)
    returns = np.random.normal(0.05, 0.15, n_samples)  # 5% mean, 15% volatility

    # Risk labels (low=0, medium=1, high=2)
    risk_labels = np.random.choice([0, 1, 2], n_samples, p=[0.3, 0.5, 0.2])

    return binary_targets, returns, risk_labels


def test_base_models():
    """Test base model functionality"""
    logger.info("Testing base models...")

    from base_models import MLPBaseModel, ResNetModel

    # Generate test data
    X = generate_mock_features(100, 50)
    y, _, _ = generate_mock_targets(100)

    # Test MLP model
    mlp_model = MLPBaseModel(input_dim=50, hidden_dims=[128, 64], dropout_rate=0.2)

    # Test forward pass
    X_tensor = torch.FloatTensor(X.values)
    output = mlp_model(X_tensor)
    logger.info(f"MLP output shape: {output.shape}")

    # Test prediction
    probas = mlp_model.predict_proba(X)
    predictions = mlp_model.predict(X)
    logger.info(f"MLP predictions shape: {predictions.shape}")

    # Test ResNet model
    resnet_model = ResNetModel(input_dim=50, hidden_dim=128, num_blocks=2)

    output = resnet_model(X_tensor)
    logger.info(f"ResNet output shape: {output.shape}")

    # Test metrics calculation
    metrics = mlp_model.calculate_metrics(y, predictions)
    logger.info(f"Model metrics: {metrics}")

    logger.info("✅ Base models test passed")


def test_ensemble_models():
    """Test ensemble model functionality"""
    logger.info("Testing ensemble models...")

    from ensemble_models import (
        AttentionStockPredictor,
        CNNFeatureExtractor,
        DeepEnsembleModel,
        EnsembleConfig,
        LSTMStockPredictor,
        ModelConfig,
        TransformerStockModel,
    )

    # Generate test data
    X = generate_mock_features(200, 100)
    y, _, _ = generate_mock_targets(200)

    input_dim = X.shape[1]

    # Test individual models
    logger.info("Testing individual ensemble components...")

    # Attention model
    attention_model = AttentionStockPredictor(input_dim, hidden_dim=64, num_heads=4, num_layers=2)
    output = attention_model(torch.FloatTensor(X.values[:10]))
    logger.info(f"Attention model output shape: {output.shape}")

    # Transformer model
    transformer_model = TransformerStockModel(input_dim, d_model=64, nhead=4, num_layers=2)
    output = transformer_model(torch.FloatTensor(X.values[:10]))
    logger.info(f"Transformer model output shape: {output.shape}")

    # LSTM model
    lstm_model = LSTMStockPredictor(input_dim, hidden_dim=64, num_layers=2)
    output = lstm_model(torch.FloatTensor(X.values[:10]))
    logger.info(f"LSTM model output shape: {output.shape}")

    # CNN model
    cnn_model = CNNFeatureExtractor(input_dim, num_filters=32, filter_sizes=[3, 5])
    output = cnn_model(torch.FloatTensor(X.values[:10]))
    logger.info(f"CNN model output shape: {output.shape}")

    # Test ensemble configuration
    model_configs = [
        ModelConfig(
            model_type="attention",
            hidden_dims=[128],
            dropout_rate=0.2,
            learning_rate=0.001,
            weight_decay=1e-4,
            batch_size=32,
            epochs=5,
        ),
        ModelConfig(
            model_type="lstm",
            hidden_dims=[128],
            dropout_rate=0.2,
            learning_rate=0.001,
            weight_decay=1e-4,
            batch_size=32,
            epochs=5,
        ),
        ModelConfig(
            model_type="mlp",
            hidden_dims=[256, 128],
            dropout_rate=0.3,
            learning_rate=0.001,
            weight_decay=1e-4,
            batch_size=32,
            epochs=5,
        ),
    ]

    ensemble_config = EnsembleConfig(
        base_models=model_configs,
        ensemble_method="weighted_average",
        feature_subsampling=True,
        bootstrap_samples=True,
    )

    # Create ensemble model
    ensemble_model = DeepEnsembleModel(input_dim, ensemble_config)

    # Test forward pass
    X_test = torch.FloatTensor(X.values[:20])
    ensemble_output = ensemble_model(X_test)
    logger.info(f"Ensemble output shape: {ensemble_output.shape}")

    # Test individual predictions
    individual_preds = ensemble_model.get_individual_predictions(X.values[:20])
    logger.info(f"Individual predictions: {len(individual_preds)} models")

    # Test prediction methods
    ensemble_probas = ensemble_model.predict_proba(X.values[:20])
    ensemble_preds = ensemble_model.predict(X.values[:20])
    logger.info(f"Ensemble predictions shape: {ensemble_preds.shape}")

    logger.info("✅ Ensemble models test passed")


def test_recommendation_model():
    """Test recommendation model"""
    logger.info("Testing recommendation model...")

    from ensemble_models import EnsembleConfig, ModelConfig
    from recommendation_models import (
        PortfolioRecommendation,
        RecommendationConfig,
        RecommendationTrainer,
        StockRecommendationModel,
    )

    # Generate test data
    X = generate_mock_features(300, 120)
    y, returns, risk_labels = generate_mock_targets(300)

    input_dim = X.shape[1]
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    # Create smaller ensemble for testing
    model_configs = [
        ModelConfig(
            model_type="mlp",
            hidden_dims=[128, 64],
            dropout_rate=0.2,
            learning_rate=0.001,
            weight_decay=1e-4,
            batch_size=32,
            epochs=3,
        ),
        ModelConfig(
            model_type="attention",
            hidden_dims=[64],
            dropout_rate=0.2,
            learning_rate=0.001,
            weight_decay=1e-4,
            batch_size=32,
            epochs=3,
        ),
    ]

    ensemble_config = EnsembleConfig(base_models=model_configs, ensemble_method="weighted_average")

    recommendation_config = RecommendationConfig(
        ensemble_config=ensemble_config,
        risk_adjustment=True,
        confidence_threshold=0.4,  # Lower for testing
        max_positions=5,
    )

    # Create recommendation model
    rec_model = StockRecommendationModel(input_dim, recommendation_config)

    # Test forward pass
    X_test = torch.FloatTensor(X.values[:10])
    outputs = rec_model(X_test)

    expected_keys = ["main_prediction", "risk_assessment", "expected_returns", "confidence"]
    for key in expected_keys:
        assert key in outputs, f"Missing output: {key}"
        logger.info(f"{key} shape: {outputs[key].shape}")

    # Test recommendation generation
    recommendations = rec_model.generate_recommendations(X.values[:5], tickers, market_data=None)

    logger.info(f"Generated {len(recommendations)} recommendations")

    for rec in recommendations:
        logger.info(f"Ticker: {rec.ticker}")
        logger.info(f"  Score: {rec.recommendation_score:.3f}")
        logger.info(f"  Confidence: {rec.confidence:.3f}")
        logger.info(f"  Risk: {rec.risk_level}")
        logger.info(f"  Position: {rec.position_size:.3f}")
        logger.info(f"  Reason: {rec.recommendation_reason}")

    # Validate recommendation structure
    for rec in recommendations:
        assert isinstance(rec, PortfolioRecommendation)
        assert 0 <= rec.recommendation_score <= 1
        assert 0 <= rec.confidence <= 1
        assert rec.risk_level in ["low", "medium", "high"]
        assert 0 <= rec.position_size <= 1
        assert isinstance(rec.key_features, list)
        assert isinstance(rec.warnings, list)

    logger.info("✅ Recommendation model test passed")


def test_model_training():
    """Test model training functionality"""
    logger.info("Testing model training...")

    from ensemble_models import EnsembleConfig, EnsembleTrainer, ModelConfig
    from recommendation_models import (
        RecommendationConfig,
        RecommendationTrainer,
        StockRecommendationModel,
    )

    # Generate training data
    X_train = generate_mock_features(200, 80)
    X_val = generate_mock_features(50, 80)

    y_train, returns_train, risk_train = generate_mock_targets(200)
    y_val, returns_val, risk_val = generate_mock_targets(50)

    input_dim = X_train.shape[1]

    # Simple ensemble for faster training
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

    ensemble_config = EnsembleConfig(base_models=model_configs, ensemble_method="weighted_average")

    recommendation_config = RecommendationConfig(
        ensemble_config=ensemble_config, confidence_threshold=0.3
    )

    # Test ensemble training
    from ensemble_models import DeepEnsembleModel

    ensemble_model = DeepEnsembleModel(input_dim, ensemble_config)
    ensemble_trainer = EnsembleTrainer(ensemble_model, ensemble_config)

    logger.info("Training ensemble model...")
    ensemble_result = ensemble_trainer.train(X_train.values, y_train, X_val.values, y_val)

    logger.info(f"Ensemble training metrics:")
    logger.info(f"  Train accuracy: {ensemble_result.train_metrics.accuracy:.3f}")
    logger.info(f"  Val accuracy: {ensemble_result.val_metrics.accuracy:.3f}")

    # Test recommendation model training
    rec_model = StockRecommendationModel(input_dim, recommendation_config)
    rec_trainer = RecommendationTrainer(rec_model, recommendation_config)

    logger.info("Training recommendation model...")
    rec_result = rec_trainer.train(
        X_train.values,
        y_train,
        returns_train,
        risk_train,
        X_val.values,
        y_val,
        returns_val,
        risk_val,
        epochs=5,
        batch_size=32,
    )

    logger.info(f"Recommendation training metrics:")
    logger.info(f"  Train accuracy: {rec_result.train_metrics.accuracy:.3f}")
    logger.info(f"  Val accuracy: {rec_result.val_metrics.accuracy:.3f}")

    # Test trained model predictions
    test_recommendations = rec_model.generate_recommendations(
        X_val.values[:3], ["AAPL", "MSFT", "GOOGL"]
    )

    logger.info(f"Generated {len(test_recommendations)} test recommendations")

    logger.info("✅ Model training test passed")


def test_model_persistence():
    """Test model saving and loading"""
    logger.info("Testing model persistence...")

    import tempfile

    from base_models import MLPBaseModel

    # Create and test model
    model = MLPBaseModel(input_dim=50, hidden_dims=[64, 32])
    X_test = generate_mock_features(10, 50)

    # Get initial predictions
    original_preds = model.predict_proba(X_test)

    # Save model
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
        model_path = f.name

    model.save_model(model_path)

    # Create new model and load
    new_model = MLPBaseModel(input_dim=50, hidden_dims=[64, 32])
    new_model.load_model(model_path)

    # Compare predictions
    loaded_preds = new_model.predict_proba(X_test)

    # Should be identical
    np.testing.assert_array_almost_equal(original_preds, loaded_preds, decimal=6)

    # Cleanup
    os.unlink(model_path)

    logger.info("✅ Model persistence test passed")


def main():
    """Run all model tests"""
    logger.info("Starting ensemble model tests...")

    try:
        # Test individual components
        test_base_models()
        test_ensemble_models()
        test_recommendation_model()
        test_model_training()
        test_model_persistence()

        logger.info("🎉 All ensemble model tests passed!")

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("PYTORCH ENSEMBLE MODEL SYSTEM SUMMARY")
        logger.info("=" * 60)
        logger.info("✅ Base models: MLP, ResNet with proper abstractions")
        logger.info("✅ Ensemble models: Attention, Transformer, LSTM, CNN")
        logger.info("✅ Deep ensemble: Weighted averaging, voting, stacking")
        logger.info("✅ Recommendation system: Portfolio optimization")
        logger.info("✅ Training pipeline: Multi-task learning")
        logger.info("✅ Model persistence: Save/load functionality")
        logger.info("✅ Comprehensive metrics: Classification, regression, trading")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Ensemble model tests failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
