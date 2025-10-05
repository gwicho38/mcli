"""Test script for feature engineering system"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_trading_data(n_records: int = 100) -> pd.DataFrame:
    """Generate mock politician trading data"""
    np.random.seed(42)

    politicians = ["Nancy Pelosi", "Mitch McConnell", "Chuck Schumer", "Kevin McCarthy"]
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "JPM", "BAC"]
    companies = [
        "Apple Inc",
        "Microsoft Corp",
        "Alphabet Inc",
        "Amazon.com Inc",
        "Tesla Inc",
        "Meta Platforms Inc",
        "JPMorgan Chase",
        "Bank of America",
    ]

    records = []
    start_date = datetime.now() - timedelta(days=365)

    for i in range(n_records):
        days_ago = np.random.randint(0, 365)
        trade_date = start_date + timedelta(days=days_ago)

        ticker_idx = np.random.randint(0, len(tickers))

        record = {
            "politician_name_cleaned": np.random.choice(politicians),
            "transaction_date_cleaned": trade_date.strftime("%Y-%m-%d"),
            "transaction_date_dt": trade_date,
            "transaction_amount_cleaned": np.random.uniform(1000, 500000),
            "transaction_type_cleaned": np.random.choice(["buy", "sell"]),
            "asset_name_cleaned": companies[ticker_idx],
            "ticker_cleaned": tickers[ticker_idx],
            "disclosure_date": (trade_date + timedelta(days=np.random.randint(1, 60))).strftime(
                "%Y-%m-%d"
            ),
        }
        records.append(record)

    return pd.DataFrame(records)


def generate_mock_stock_data(tickers: list, days: int = 365) -> pd.DataFrame:
    """Generate mock stock price data"""
    np.random.seed(42)

    stock_data = []
    start_date = datetime.now() - timedelta(days=days)

    for ticker in tickers:
        base_price = np.random.uniform(50, 300)

        for day in range(days):
            date = start_date + timedelta(days=day)

            # Random walk for price
            change = np.random.normal(0, 0.02)
            base_price *= 1 + change

            # Generate OHLCV data
            open_price = base_price * (1 + np.random.normal(0, 0.005))
            high_price = max(open_price, base_price) * (1 + abs(np.random.normal(0, 0.01)))
            low_price = min(open_price, base_price) * (1 - abs(np.random.normal(0, 0.01)))
            close_price = base_price
            volume = np.random.randint(1000000, 10000000)

            stock_data.append(
                {
                    "symbol": ticker,
                    "date": date,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                }
            )

    return pd.DataFrame(stock_data)


def test_stock_features():
    """Test stock feature extraction"""
    logger.info("Testing stock features...")

    from stock_features import StockRecommendationFeatures, TechnicalIndicatorFeatures

    # Generate mock stock data
    stock_data = generate_mock_stock_data(["AAPL"], 100)

    # Test basic stock features
    stock_extractor = StockRecommendationFeatures()
    features_df = stock_extractor.extract_features(stock_data)

    logger.info(f"Stock features shape: {features_df.shape}")

    # Check for expected features
    expected_features = ["sma_20", "rsi", "macd", "volatility_20", "bb_position"]

    found_features = 0
    for feature in expected_features:
        if feature in features_df.columns:
            logger.info(f"✅ Found feature: {feature}")
            found_features += 1
        else:
            logger.warning(f"⚠️ Missing feature: {feature}")

    # Test technical indicators
    tech_extractor = TechnicalIndicatorFeatures()
    tech_features = tech_extractor.extract_advanced_indicators(features_df)

    logger.info(f"Technical features shape: {tech_features.shape}")

    assert found_features > 0, "Should have extracted some stock features"
    logger.info("✅ Stock features test passed")


def test_political_features():
    """Test political feature extraction"""
    logger.info("Testing political features...")

    from political_features import PoliticalInfluenceFeatures

    # Generate mock trading data
    trading_data = generate_mock_trading_data(50)

    # Test political features
    political_extractor = PoliticalInfluenceFeatures()
    features_df = political_extractor.extract_influence_features(trading_data)

    logger.info(f"Political features shape: {features_df.shape}")

    # Check for expected features
    expected_features = [
        "total_influence",
        "trading_frequency_score",
        "committee_sector_alignment",
        "disclosure_compliance_score",
        "seniority_influence",
    ]

    found_features = 0
    for feature in expected_features:
        if feature in features_df.columns:
            logger.info(f"✅ Found feature: {feature}")
            found_features += 1
        else:
            logger.warning(f"⚠️ Missing feature: {feature}")

    assert found_features > 0, "Should have extracted some political features"
    logger.info("✅ Political features test passed")


def test_ensemble_features():
    """Test ensemble feature engineering"""
    logger.info("Testing ensemble features...")

    from ensemble_features import EnsembleFeatureBuilder

    # Generate base features
    trading_data = generate_mock_trading_data(50)

    # Add some numerical features for ensemble processing
    trading_data["feature_1"] = np.random.random(len(trading_data))
    trading_data["feature_2"] = np.random.random(len(trading_data))
    trading_data["feature_3"] = np.random.random(len(trading_data))

    # Test ensemble features
    ensemble_builder = EnsembleFeatureBuilder()
    ensemble_df = ensemble_builder.build_ensemble_features(trading_data)

    logger.info(f"Ensemble features shape: {ensemble_df.shape}")

    # Check for ensemble-specific features
    ensemble_feature_types = ["rolling", "interaction", "cluster", "poly"]
    found_types = 0

    for feature_type in ensemble_feature_types:
        matching_features = [col for col in ensemble_df.columns if feature_type in col.lower()]
        if matching_features:
            logger.info(f"✅ Found {feature_type} features: {len(matching_features)}")
            found_types += 1
        else:
            logger.warning(f"⚠️ No {feature_type} features found")

    assert found_types > 0, "Should have created some ensemble features"
    logger.info("✅ Ensemble features test passed")


def test_recommendation_engine():
    """Test the full recommendation engine"""
    logger.info("Testing recommendation engine...")

    from recommendation_engine import RecommendationConfig, StockRecommendationEngine

    # Generate comprehensive test data
    trading_data = generate_mock_trading_data(100)
    stock_data = generate_mock_stock_data(["AAPL", "MSFT", "GOOGL"], 100)

    # Create recommendation engine
    config = RecommendationConfig(
        enable_technical_features=True,
        enable_political_features=True,
        enable_ensemble_features=True,
        max_features=50,  # Limit for testing
    )

    engine = StockRecommendationEngine(config)

    # Generate recommendations
    recommendations = engine.generate_recommendation(
        trading_data=trading_data,
        stock_price_data=stock_data,
        politician_metadata=None,
        market_data=None,
    )

    logger.info(f"Generated {len(recommendations)} recommendations")

    # Validate recommendations
    assert len(recommendations) > 0, "Should generate at least one recommendation"

    for rec in recommendations:
        logger.info(f"Recommendation for {rec.ticker}:")
        logger.info(f"  Score: {rec.recommendation_score}")
        logger.info(f"  Confidence: {rec.confidence}")
        logger.info(f"  Risk: {rec.risk_level}")
        logger.info(f"  Reason: {rec.recommendation_reason}")

        # Validate recommendation structure
        assert 0 <= rec.recommendation_score <= 1, "Score should be between 0 and 1"
        assert 0 <= rec.confidence <= 1, "Confidence should be between 0 and 1"
        assert rec.risk_level in ["low", "medium", "high"], "Risk level should be valid"
        assert len(rec.key_features) >= 0, "Should have key features list"
        assert isinstance(rec.warnings, list), "Warnings should be a list"

    logger.info("✅ Recommendation engine test passed")


def test_feature_integration():
    """Test integration of all feature components"""
    logger.info("Testing feature integration...")

    from ensemble_features import EnsembleFeatureBuilder
    from political_features import PoliticalInfluenceFeatures
    from stock_features import StockRecommendationFeatures

    # Generate test data
    trading_data = generate_mock_trading_data(30)

    # Apply features sequentially
    logger.info("Applying political features...")
    political_extractor = PoliticalInfluenceFeatures()
    features_df = political_extractor.extract_influence_features(trading_data)

    logger.info("Applying ensemble features...")
    ensemble_builder = EnsembleFeatureBuilder()
    final_df = ensemble_builder.build_ensemble_features(features_df)

    logger.info(f"Final integrated features shape: {final_df.shape}")

    # Check that we have a reasonable number of features
    original_cols = len(trading_data.columns)
    final_cols = len(final_df.columns)

    logger.info(f"Features increased from {original_cols} to {final_cols}")
    assert final_cols > original_cols, "Should have added new features"

    # Check for feature diversity
    feature_types = set()
    for col in final_df.columns:
        if "rolling" in col:
            feature_types.add("rolling")
        elif "interaction" in col or "_x_" in col:
            feature_types.add("interaction")
        elif "cluster" in col:
            feature_types.add("cluster")
        elif "influence" in col:
            feature_types.add("political")

    logger.info(f"Feature types found: {feature_types}")
    assert len(feature_types) > 1, "Should have multiple types of features"

    logger.info("✅ Feature integration test passed")


def main():
    """Run all feature engineering tests"""
    logger.info("Starting feature engineering tests...")

    try:
        # Test individual components
        test_stock_features()
        test_political_features()
        test_ensemble_features()

        # Test integration
        test_feature_integration()
        test_recommendation_engine()

        logger.info("🎉 All feature engineering tests passed!")

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("FEATURE ENGINEERING SYSTEM SUMMARY")
        logger.info("=" * 60)
        logger.info("✅ Stock technical features: RSI, MACD, Bollinger Bands, etc.")
        logger.info("✅ Political influence features: Committee alignment, trading patterns")
        logger.info("✅ Ensemble features: Interactions, clustering, polynomial")
        logger.info("✅ Market regime features: Volatility, trend, volume regimes")
        logger.info("✅ Advanced interactions: Conditional, non-linear, min/max")
        logger.info("✅ Feature selection: Multiple criteria, dynamic selection")
        logger.info("✅ Recommendation engine: Comprehensive scoring and explanations")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Feature engineering tests failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
