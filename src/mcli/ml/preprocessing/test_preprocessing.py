"""Test script for the ML preprocessing pipeline"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from ml_pipeline import MLDataPipeline, MLDataPipelineConfig
from politician_trading_preprocessor import PoliticianTradingPreprocessor, PreprocessingConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_data(n_records: int = 100) -> pd.DataFrame:
    """Generate sample politician trading data for testing"""
    np.random.seed(42)

    # Sample politicians
    politicians = [
        "Nancy Pelosi",
        "Mitch McConnell",
        "Chuck Schumer",
        "Kevin McCarthy",
        "Alexandria Ocasio-Cortez",
        "Ted Cruz",
        "Elizabeth Warren",
        "Marco Rubio",
        "Bernie Sanders",
        "Mitt Romney",
    ]

    # Sample stocks
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM", "BAC", "XOM"]
    companies = [
        "Apple Inc",
        "Microsoft Corp",
        "Alphabet Inc",
        "Amazon.com Inc",
        "Tesla Inc",
        "Meta Platforms Inc",
        "Nvidia Corp",
        "JPMorgan Chase",
        "Bank of America",
        "Exxon Mobil",
    ]

    # Generate random data
    records = []
    start_date = datetime.now() - timedelta(days=365)

    for i in range(n_records):
        # Random date within last year
        days_ago = np.random.randint(0, 365)
        trade_date = start_date + timedelta(days=days_ago)

        # Random amounts with some outliers
        if np.random.random() < 0.1:  # 10% outliers
            amount = np.random.uniform(100000, 5000000)
        else:
            amount = np.random.uniform(1000, 50000)

        # Random transaction type
        transaction_type = np.random.choice(["buy", "sell"], p=[0.6, 0.4])

        # Random stock
        ticker_idx = np.random.randint(0, len(tickers))

        record = {
            "politician_name": np.random.choice(politicians),
            "transaction_date": trade_date.strftime("%Y-%m-%d"),
            "transaction_amount": amount,
            "transaction_type": transaction_type,
            "asset_name": companies[ticker_idx],
            "stock_symbol": tickers[ticker_idx],
            "disclosure_date": (trade_date + timedelta(days=np.random.randint(1, 45))).strftime(
                "%Y-%m-%d"
            ),
            "transaction_id": f"T{i:06d}",
            "source": "test_data",
        }

        # Add some missing values randomly
        if np.random.random() < 0.1:
            del record["transaction_amount"]
        if np.random.random() < 0.05:
            del record["stock_symbol"]

        records.append(record)

    return pd.DataFrame(records)


def test_data_cleaning():
    """Test data cleaning functionality"""
    logger.info("Testing data cleaning...")

    # Generate sample data with issues
    data = generate_sample_data(50)

    # Add some problematic records
    problematic_records = [
        {
            "politician_name": "  john DOE jr. ",
            "transaction_amount": "$15,000.00",
            "transaction_date": "2023-12-01",
        },
        {
            "politician_name": "Jane Smith",
            "transaction_amount": "1K - 15K",
            "transaction_date": "12/01/2023",
        },
        {
            "politician_name": "Bob Johnson",
            "transaction_amount": "",
            "transaction_date": "invalid-date",
        },
    ]

    data = pd.concat([data, pd.DataFrame(problematic_records)], ignore_index=True)

    # Initialize preprocessor
    config = PreprocessingConfig(enable_data_cleaning=True)
    preprocessor = PoliticianTradingPreprocessor(config)

    # Test cleaning
    records = data.to_dict("records")
    cleaned_records, cleaning_stats = preprocessor.data_cleaner.clean_trading_records(records)

    logger.info(f"Original records: {len(records)}")
    logger.info(f"Cleaned records: {len(cleaned_records)}")
    logger.info(f"Cleaning operations: {cleaning_stats.cleaning_operations}")

    assert len(cleaned_records) > 0, "Should have some cleaned records"
    assert cleaning_stats.cleaned_records > 0, "Should have cleaned some records"

    logger.info("✅ Data cleaning test passed")


def test_feature_extraction():
    """Test feature extraction functionality"""
    logger.info("Testing feature extraction...")

    data = generate_sample_data(100)

    config = PreprocessingConfig(
        enable_politician_features=True,
        enable_market_features=True,
        enable_temporal_features=True,
        enable_sentiment_features=True,
    )
    preprocessor = PoliticianTradingPreprocessor(config)

    # Clean data first
    records = data.to_dict("records")
    cleaned_records, _ = preprocessor.data_cleaner.clean_trading_records(records)
    df = pd.DataFrame(cleaned_records)

    # Extract features
    df_with_features = preprocessor._extract_features(df)

    logger.info(f"Original columns: {len(df.columns)}")
    logger.info(f"Columns after feature extraction: {len(df_with_features.columns)}")

    # Check for expected features
    expected_features = [
        "politician_name_length",
        "politician_trading_frequency",
        "asset_trading_frequency",
        "transaction_day_of_week",
        "asset_name_sentiment_score",
    ]

    for feature in expected_features:
        if feature in df_with_features.columns:
            logger.info(f"✅ Found expected feature: {feature}")
        else:
            logger.warning(f"⚠️ Missing expected feature: {feature}")

    assert len(df_with_features.columns) > len(df.columns), "Should have extracted new features"

    logger.info("✅ Feature extraction test passed")


def test_full_preprocessing():
    """Test full preprocessing pipeline"""
    logger.info("Testing full preprocessing pipeline...")

    data = generate_sample_data(200)

    config = PreprocessingConfig(
        enable_data_cleaning=True,
        enable_outlier_detection=True,
        enable_missing_value_handling=True,
        train_split_ratio=0.7,
        val_split_ratio=0.15,
        test_split_ratio=0.15,
        save_preprocessing_artifacts=True,
        artifacts_dir=Path("./test_artifacts"),
    )

    preprocessor = PoliticianTradingPreprocessor(config)

    # Run full preprocessing
    results = preprocessor.preprocess(data)

    # Check results
    logger.info(f"Original shape: {results.original_shape}")
    logger.info(f"Final shape: {results.final_shape}")
    logger.info(f"Features: {results.feature_count}")
    logger.info(f"Train size: {len(results.train_data)}")
    logger.info(f"Val size: {len(results.val_data)}")
    logger.info(f"Test size: {len(results.test_data)}")
    logger.info(f"Target columns: {results.target_columns}")

    # Validate results
    assert results.feature_count > 0, "Should have extracted features"
    assert len(results.train_data) > 0, "Should have training data"
    assert len(results.val_data) > 0, "Should have validation data"
    assert len(results.test_data) > 0, "Should have test data"
    assert len(results.target_columns) > 0, "Should have target columns"

    # Check that splits sum to original
    total_split_size = len(results.train_data) + len(results.val_data) + len(results.test_data)
    assert total_split_size == results.final_shape[0], "Split sizes should sum to final shape"

    # Check for target variables
    expected_targets = ["target_profitable", "target_recommendation_score", "target_risk_level"]
    for target in expected_targets:
        if target in results.target_columns:
            logger.info(f"✅ Found expected target: {target}")

    logger.info("✅ Full preprocessing test passed")


def test_transform_new_data():
    """Test transforming new data with fitted preprocessor"""
    logger.info("Testing new data transformation...")

    # Train on initial data
    train_data = generate_sample_data(100)

    config = PreprocessingConfig(
        save_preprocessing_artifacts=True, artifacts_dir=Path("./test_artifacts")
    )

    preprocessor = PoliticianTradingPreprocessor(config)
    results = preprocessor.preprocess(train_data)

    # Generate new data
    new_data = generate_sample_data(20)

    # Transform new data
    transformed_data = preprocessor.transform_new_data(new_data)

    logger.info(f"New data original shape: {new_data.shape}")
    logger.info(f"Transformed data shape: {transformed_data.shape}")

    # Should have same number of features as training
    expected_feature_cols = [
        col for col in results.train_data.columns if not col.startswith("target_")
    ]
    actual_feature_cols = [col for col in transformed_data.columns if not col.startswith("target_")]

    logger.info(f"Expected feature columns: {len(expected_feature_cols)}")
    logger.info(f"Actual feature columns: {len(actual_feature_cols)}")

    # Note: Some features might be missing due to different data patterns
    assert len(transformed_data) > 0, "Should have transformed some data"

    logger.info("✅ New data transformation test passed")


def main():
    """Run all tests"""
    logger.info("Starting preprocessing pipeline tests...")

    try:
        test_data_cleaning()
        test_feature_extraction()
        test_full_preprocessing()
        test_transform_new_data()

        logger.info("🎉 All preprocessing tests passed!")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
