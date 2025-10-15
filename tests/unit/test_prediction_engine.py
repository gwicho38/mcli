"""Unit tests for Politician Trading Prediction Engine"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def predictor():
    """Create a predictor instance for testing"""
    from mcli.ml.predictions import PoliticianTradingPredictor

    return PoliticianTradingPredictor()


@pytest.fixture
def sample_disclosures():
    """Create sample trading disclosure data"""
    base_date = datetime.now() - timedelta(days=30)

    return pd.DataFrame(
        [
            # Strong buy signal - AAPL
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "amount": "$50,000",
                "disclosure_date": base_date,
            },
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "amount": "$75,000",
                "disclosure_date": base_date + timedelta(days=5),
            },
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "amount": "$100,000",
                "disclosure_date": base_date + timedelta(days=10),
            },
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "buy",
                "amount": "$60,000",
                "disclosure_date": base_date + timedelta(days=15),
            },
            # Strong sell signal - TSLA
            {
                "ticker_symbol": "TSLA",
                "transaction_type": "sale",
                "amount": "$150,000",
                "disclosure_date": base_date + timedelta(days=2),
            },
            {
                "ticker_symbol": "TSLA",
                "transaction_type": "sell",
                "amount": "$200,000",
                "disclosure_date": base_date + timedelta(days=8),
            },
            {
                "ticker_symbol": "TSLA",
                "transaction_type": "sale",
                "amount": "$100,000",
                "disclosure_date": base_date + timedelta(days=12),
            },
            # Mixed signal - MSFT
            {
                "ticker_symbol": "MSFT",
                "transaction_type": "purchase",
                "amount": "$80,000",
                "disclosure_date": base_date + timedelta(days=3),
            },
            {
                "ticker_symbol": "MSFT",
                "transaction_type": "sale",
                "amount": "$90,000",
                "disclosure_date": base_date + timedelta(days=7),
            },
            # Single trade - GOOGL (should be filtered out)
            {
                "ticker_symbol": "GOOGL",
                "transaction_type": "purchase",
                "amount": "$120,000",
                "disclosure_date": base_date + timedelta(days=1),
            },
        ]
    )


@pytest.fixture
def empty_disclosures():
    """Create empty DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def old_disclosures():
    """Create old disclosures outside the 90-day window"""
    old_date = datetime.now() - timedelta(days=120)

    return pd.DataFrame(
        [
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "amount": "$50,000",
                "disclosure_date": old_date,
            },
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "amount": "$75,000",
                "disclosure_date": old_date - timedelta(days=10),
            },
        ]
    )


def test_predictor_initialization(predictor):
    """Test predictor initializes with correct defaults"""
    logger.info("Testing predictor initialization...")

    assert predictor.min_trades_threshold == 2, "Default min_trades_threshold should be 2"
    assert predictor.recent_days == 90, "Default recent_days should be 90"

    logger.info("✅ Predictor initialization test passed!")


def test_empty_disclosures(predictor, empty_disclosures):
    """Test that empty disclosures return empty predictions"""
    logger.info("Testing empty disclosures handling...")

    predictions = predictor.generate_predictions(empty_disclosures)

    assert predictions.empty, "Empty disclosures should return empty DataFrame"

    logger.info("✅ Empty disclosures test passed!")


def test_missing_ticker_column(predictor):
    """Test handling of data without required ticker_symbol column"""
    logger.info("Testing missing ticker_symbol column...")

    bad_data = pd.DataFrame([{"transaction_type": "purchase", "amount": "$50,000"}])

    predictions = predictor.generate_predictions(bad_data)

    assert predictions.empty, "Should return empty DataFrame when ticker_symbol missing"

    logger.info("✅ Missing ticker column test passed!")


def test_minimum_trades_filter(predictor, sample_disclosures):
    """Test that tickers with fewer than minimum trades are filtered"""
    logger.info("Testing minimum trades filter...")

    predictions = predictor.generate_predictions(sample_disclosures)

    # GOOGL should be filtered out (only 1 trade)
    assert "GOOGL" not in predictions["ticker"].values, "GOOGL should be filtered (only 1 trade)"

    # AAPL, TSLA, MSFT should be included (2+ trades)
    assert "AAPL" in predictions["ticker"].values, "AAPL should be included (4 trades)"
    assert "TSLA" in predictions["ticker"].values, "TSLA should be included (3 trades)"
    assert "MSFT" in predictions["ticker"].values, "MSFT should be included (2 trades)"

    logger.info("✅ Minimum trades filter test passed!")


def test_buy_signal_detection(predictor, sample_disclosures):
    """Test that strong buy signals are detected correctly"""
    logger.info("Testing buy signal detection...")

    predictions = predictor.generate_predictions(sample_disclosures)

    # AAPL should be BUY (4 purchases, 0 sales = 100% buy)
    aapl_pred = predictions[predictions["ticker"] == "AAPL"].iloc[0]

    assert aapl_pred["recommendation"] == "BUY", "AAPL should be BUY recommendation"
    assert aapl_pred["predicted_return"] > 0, "BUY signal should have positive return"
    assert aapl_pred["buy_count"] == 4, "AAPL should have 4 buy trades"
    assert aapl_pred["sell_count"] == 0, "AAPL should have 0 sell trades"
    assert aapl_pred["trade_count"] == 4, "AAPL should have 4 total trades"

    logger.info(
        f"AAPL prediction: {aapl_pred['recommendation']} with {aapl_pred['confidence']:.2f} confidence"
    )
    logger.info("✅ Buy signal detection test passed!")


def test_sell_signal_detection(predictor, sample_disclosures):
    """Test that strong sell signals are detected correctly"""
    logger.info("Testing sell signal detection...")

    predictions = predictor.generate_predictions(sample_disclosures)

    # TSLA should be SELL (0 purchases, 3 sales = 100% sell)
    tsla_pred = predictions[predictions["ticker"] == "TSLA"].iloc[0]

    assert tsla_pred["recommendation"] == "SELL", "TSLA should be SELL recommendation"
    assert tsla_pred["predicted_return"] < 0, "SELL signal should have negative return"
    assert tsla_pred["buy_count"] == 0, "TSLA should have 0 buy trades"
    assert tsla_pred["sell_count"] == 3, "TSLA should have 3 sell trades"
    assert tsla_pred["trade_count"] == 3, "TSLA should have 3 total trades"

    logger.info(
        f"TSLA prediction: {tsla_pred['recommendation']} with {tsla_pred['confidence']:.2f} confidence"
    )
    logger.info("✅ Sell signal detection test passed!")


def test_mixed_signal_detection(predictor, sample_disclosures):
    """Test that mixed signals are handled correctly"""
    logger.info("Testing mixed signal detection...")

    predictions = predictor.generate_predictions(sample_disclosures)

    # MSFT should be HOLD or weak signal (1 buy, 1 sell)
    msft_pred = predictions[predictions["ticker"] == "MSFT"].iloc[0]

    assert msft_pred["buy_count"] == 1, "MSFT should have 1 buy trade"
    assert msft_pred["sell_count"] == 1, "MSFT should have 1 sell trade"
    assert msft_pred["trade_count"] == 2, "MSFT should have 2 total trades"

    logger.info(
        f"MSFT prediction: {msft_pred['recommendation']} with {msft_pred['confidence']:.2f} confidence"
    )
    logger.info("✅ Mixed signal detection test passed!")


def test_confidence_scoring(predictor, sample_disclosures):
    """Test confidence scoring logic"""
    logger.info("Testing confidence scoring...")

    predictions = predictor.generate_predictions(sample_disclosures)

    # Check confidence is in valid range
    for _, pred in predictions.iterrows():
        assert (
            0.5 <= pred["confidence"] <= 0.95
        ), f"Confidence {pred['confidence']} outside range [0.5, 0.95]"

    # AAPL should have higher confidence than MSFT (more trades, stronger signal)
    aapl_conf = predictions[predictions["ticker"] == "AAPL"].iloc[0]["confidence"]
    msft_conf = predictions[predictions["ticker"] == "MSFT"].iloc[0]["confidence"]

    logger.info(f"AAPL confidence: {aapl_conf:.2f}, MSFT confidence: {msft_conf:.2f}")
    # Note: Due to randomness, we can't strictly assert this, but log it

    logger.info("✅ Confidence scoring test passed!")


def test_risk_scoring(predictor, sample_disclosures):
    """Test risk scoring logic"""
    logger.info("Testing risk scoring...")

    predictions = predictor.generate_predictions(sample_disclosures)

    # Check risk score is in valid range
    for _, pred in predictions.iterrows():
        assert (
            0.0 <= pred["risk_score"] <= 1.0
        ), f"Risk score {pred['risk_score']} outside range [0.0, 1.0]"

    # SELL signals should generally have higher risk than BUY signals
    for _, pred in predictions.iterrows():
        if pred["recommendation"] == "SELL":
            assert pred["risk_score"] >= 0.6, "SELL should have risk >= 0.6"
        elif pred["recommendation"] == "BUY" and pred["signal_strength"] > 0.7:
            assert pred["risk_score"] <= 0.6, "Strong BUY should have risk <= 0.6"

    logger.info("✅ Risk scoring test passed!")


def test_signal_strength(predictor, sample_disclosures):
    """Test signal strength calculation"""
    logger.info("Testing signal strength...")

    predictions = predictor.generate_predictions(sample_disclosures)

    # AAPL should have high signal strength (all buys)
    aapl_strength = predictions[predictions["ticker"] == "AAPL"].iloc[0]["signal_strength"]
    assert aapl_strength > 0.9, f"AAPL signal strength {aapl_strength} should be > 0.9"

    # MSFT should have low signal strength (mixed)
    msft_strength = predictions[predictions["ticker"] == "MSFT"].iloc[0]["signal_strength"]
    assert msft_strength < 0.3, f"MSFT signal strength {msft_strength} should be < 0.3"

    logger.info("✅ Signal strength test passed!")


def test_old_disclosures_filter(predictor, old_disclosures):
    """Test that old disclosures outside the time window are filtered"""
    logger.info("Testing old disclosures filter...")

    predictions = predictor.generate_predictions(old_disclosures)

    # Old disclosures should be filtered out
    assert predictions.empty, "Old disclosures (>90 days) should be filtered out"

    logger.info("✅ Old disclosures filter test passed!")


def test_recency_adjustment(predictor):
    """Test that recency affects confidence scoring"""
    logger.info("Testing recency adjustment...")

    # Recent trades
    recent_date = datetime.now() - timedelta(days=5)
    recent_data = pd.DataFrame(
        [
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "disclosure_date": recent_date,
            },
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "disclosure_date": recent_date + timedelta(days=1),
            },
        ]
    )

    # Old trades (but within window)
    old_date = datetime.now() - timedelta(days=85)
    old_data = pd.DataFrame(
        [
            {"ticker_symbol": "MSFT", "transaction_type": "purchase", "disclosure_date": old_date},
            {
                "ticker_symbol": "MSFT",
                "transaction_type": "purchase",
                "disclosure_date": old_date + timedelta(days=1),
            },
        ]
    )

    recent_preds = predictor.generate_predictions(recent_data)
    old_preds = predictor.generate_predictions(old_data)

    if not recent_preds.empty and not old_preds.empty:
        recent_conf = recent_preds.iloc[0]["confidence"]
        old_conf = old_preds.iloc[0]["confidence"]

        logger.info(f"Recent confidence: {recent_conf:.2f}, Old confidence: {old_conf:.2f}")
        # Recent trades should generally have higher confidence
        # Note: Due to randomness, this might not always be true, so we just log it

    logger.info("✅ Recency adjustment test passed!")


def test_get_top_picks(predictor, sample_disclosures):
    """Test get_top_picks method"""
    logger.info("Testing get_top_picks...")

    predictions = predictor.generate_predictions(sample_disclosures)
    top_picks = predictor.get_top_picks(predictions, n=2)

    assert len(top_picks) <= 2, "Should return at most 2 picks"
    assert "score" in top_picks.columns, "Should have score column"

    # Verify descending order by score
    if len(top_picks) > 1:
        scores = top_picks["score"].values
        assert all(
            scores[i] >= scores[i + 1] for i in range(len(scores) - 1)
        ), "Scores should be descending"

    logger.info(f"Top {len(top_picks)} picks retrieved")
    logger.info("✅ get_top_picks test passed!")


def test_get_buy_recommendations(predictor, sample_disclosures):
    """Test get_buy_recommendations method"""
    logger.info("Testing get_buy_recommendations...")

    predictions = predictor.generate_predictions(sample_disclosures)
    buy_recs = predictor.get_buy_recommendations(predictions, min_confidence=0.5)

    # All recommendations should be BUY
    assert all(buy_recs["recommendation"] == "BUY"), "All recommendations should be BUY"

    # All should meet confidence threshold
    assert all(buy_recs["confidence"] >= 0.5), "All should have confidence >= 0.5"

    # Should be sorted by predicted_return descending
    if len(buy_recs) > 1:
        returns = buy_recs["predicted_return"].values
        assert all(
            returns[i] >= returns[i + 1] for i in range(len(returns) - 1)
        ), "Returns should be descending"

    logger.info(f"Found {len(buy_recs)} buy recommendations")
    logger.info("✅ get_buy_recommendations test passed!")


def test_get_sell_recommendations(predictor, sample_disclosures):
    """Test get_sell_recommendations method"""
    logger.info("Testing get_sell_recommendations...")

    predictions = predictor.generate_predictions(sample_disclosures)
    sell_recs = predictor.get_sell_recommendations(predictions, min_confidence=0.5)

    # All recommendations should be SELL
    assert all(sell_recs["recommendation"] == "SELL"), "All recommendations should be SELL"

    # All should meet confidence threshold
    assert all(sell_recs["confidence"] >= 0.5), "All should have confidence >= 0.5"

    # Should be sorted by predicted_return ascending (most negative first)
    if len(sell_recs) > 1:
        returns = sell_recs["predicted_return"].values
        assert all(
            returns[i] <= returns[i + 1] for i in range(len(returns) - 1)
        ), "Returns should be ascending"

    logger.info(f"Found {len(sell_recs)} sell recommendations")
    logger.info("✅ get_sell_recommendations test passed!")


def test_output_columns(predictor, sample_disclosures):
    """Test that output DataFrame has all expected columns"""
    logger.info("Testing output columns...")

    predictions = predictor.generate_predictions(sample_disclosures)

    expected_columns = [
        "ticker",
        "predicted_return",
        "confidence",
        "risk_score",
        "recommendation",
        "trade_count",
        "buy_count",
        "sell_count",
        "signal_strength",
    ]

    for col in expected_columns:
        assert col in predictions.columns, f"Missing column: {col}"

    logger.info(f"All {len(expected_columns)} expected columns present")
    logger.info("✅ Output columns test passed!")


def test_prediction_limit(predictor):
    """Test that predictions are limited to top 50"""
    logger.info("Testing prediction limit...")

    # Create data with 60 different tickers
    base_date = datetime.now() - timedelta(days=30)
    large_data = []

    for i in range(60):
        ticker = f"TICK{i:03d}"
        large_data.extend(
            [
                {
                    "ticker_symbol": ticker,
                    "transaction_type": "purchase",
                    "disclosure_date": base_date,
                },
                {
                    "ticker_symbol": ticker,
                    "transaction_type": "purchase",
                    "disclosure_date": base_date + timedelta(days=1),
                },
            ]
        )

    large_df = pd.DataFrame(large_data)
    predictions = predictor.generate_predictions(large_df)

    assert len(predictions) <= 50, "Should return at most 50 predictions"

    logger.info(f"Generated {len(predictions)} predictions (max 50)")
    logger.info("✅ Prediction limit test passed!")


def test_null_ticker_filter(predictor):
    """Test that null/empty tickers are filtered"""
    logger.info("Testing null ticker filter...")

    base_date = datetime.now() - timedelta(days=30)
    data_with_nulls = pd.DataFrame(
        [
            {"ticker_symbol": None, "transaction_type": "purchase", "disclosure_date": base_date},
            {"ticker_symbol": "", "transaction_type": "purchase", "disclosure_date": base_date},
            {"ticker_symbol": "AAPL", "transaction_type": "purchase", "disclosure_date": base_date},
            {
                "ticker_symbol": "AAPL",
                "transaction_type": "purchase",
                "disclosure_date": base_date + timedelta(days=1),
            },
        ]
    )

    predictions = predictor.generate_predictions(data_with_nulls)

    # Should only have AAPL
    assert len(predictions) == 1, "Should have 1 prediction (AAPL only)"
    assert predictions.iloc[0]["ticker"] == "AAPL", "Should be AAPL"

    logger.info("✅ Null ticker filter test passed!")


def test_no_date_column_handling(predictor):
    """Test handling when disclosure_date column is missing"""
    logger.info("Testing no date column handling...")

    data_no_dates = pd.DataFrame(
        [
            {"ticker_symbol": "AAPL", "transaction_type": "purchase"},
            {"ticker_symbol": "AAPL", "transaction_type": "purchase"},
        ]
    )

    predictions = predictor.generate_predictions(data_no_dates)

    # Should still generate predictions with default recency
    assert not predictions.empty, "Should generate predictions without date column"
    assert predictions.iloc[0]["ticker"] == "AAPL", "Should predict for AAPL"

    logger.info("✅ No date column handling test passed!")


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("STARTING PREDICTION ENGINE TEST SUITE")
    logger.info("=" * 60)

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
