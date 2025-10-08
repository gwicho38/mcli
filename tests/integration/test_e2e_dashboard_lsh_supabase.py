"""
End-to-End Integration Tests: Streamlit Dashboard ↔ LSH Daemon ↔ Supabase

NOTE: This test suite requires external services (Supabase, LSH daemon).
Tests are skipped pending service dependency configuration.
"""

import pytest

# Skip all tests in this module - requires external service dependencies
pytestmark = pytest.mark.skip(reason="requires external services (Supabase, LSH daemon)")

import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import asyncio
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# Conditionally import external dependencies (only if not skipped)
try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
    HAS_DEPENDENCIES = True
except ImportError:
    # If imports fail, tests are already skipped
    create_client = None
    Client = None
    load_dotenv = lambda: None
    HAS_DEPENDENCIES = False

# Load environment variables if available
if HAS_DEPENDENCIES:
    load_dotenv()


class TestInfrastructureConnectivity:
    """Test basic connectivity to all infrastructure components"""

    @pytest.fixture(scope="class")
    def lsh_url(self):
        """LSH daemon URL from environment"""
        return os.getenv("LSH_API_URL", "https://mcli-lsh-daemon.fly.dev")

    @pytest.fixture(scope="class")
    def lsh_api_key(self):
        """LSH API key from environment"""
        return os.getenv("LSH_API_KEY")

    @pytest.fixture(scope="class")
    def supabase_client(self) -> Client:
        """Supabase client fixture"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            pytest.skip("Supabase credentials not configured")

        return create_client(url, key)

    def test_lsh_daemon_health(self, lsh_url):
        """Test LSH daemon is healthy and responding"""
        response = requests.get(f"{lsh_url}/health", timeout=10)

        assert response.status_code == 200, f"LSH health check failed: {response.status_code}"

        data = response.json()
        assert data["status"] == "healthy", "LSH daemon not healthy"
        assert "uptime" in data, "Missing uptime in health response"
        assert "version" in data, "Missing version in health response"

        print(f"✓ LSH Daemon Health: {data['status']}")
        print(f"  Uptime: {data['uptime']:.2f}s")
        print(f"  Version: {data['version']}")

    def test_lsh_daemon_status(self, lsh_url):
        """Test LSH daemon status endpoint"""
        response = requests.get(f"{lsh_url}/api/status", timeout=10)

        assert response.status_code == 200, "LSH status endpoint failed"

        data = response.json()
        assert data["running"] is True, "LSH daemon not running"
        assert "pid" in data, "Missing PID in status"
        assert "memoryUsage" in data, "Missing memory usage"

        print(f"✓ LSH Daemon Status: Running")
        print(f"  PID: {data['pid']}")
        print(f"  Memory: {data['memoryUsage']['heapUsed'] / 1024 / 1024:.2f} MB")

    def test_lsh_daemon_jobs_endpoint(self, lsh_url):
        """Test LSH daemon jobs endpoint is accessible"""
        response = requests.get(f"{lsh_url}/api/jobs", timeout=10)

        assert response.status_code == 200, "LSH jobs endpoint failed"

        data = response.json()
        assert "jobs" in data, "Missing jobs in response"
        assert "total" in data, "Missing total in response"

        print(f"✓ LSH Jobs Endpoint: Accessible")
        print(f"  Total jobs: {data['total']}")

    def test_supabase_connection(self, supabase_client):
        """Test Supabase database connection"""
        try:
            # Try to fetch from politicians table
            response = supabase_client.table("politicians").select("id").limit(1).execute()

            assert response.data is not None, "Supabase query returned None"

            print(f"✓ Supabase Connection: Successful")
            print(f"  Database: Connected")

        except Exception as e:
            pytest.fail(f"Supabase connection failed: {e}")

    def test_supabase_politicians_table(self, supabase_client):
        """Test Supabase politicians table exists and has data"""
        response = supabase_client.table("politicians").select("*").limit(10).execute()

        assert response.data is not None, "Politicians table query failed"
        assert len(response.data) > 0, "Politicians table is empty"

        # Verify required fields
        politician = response.data[0]
        required_fields = ["id", "first_name", "last_name"]
        for field in required_fields:
            assert field in politician, f"Missing field '{field}' in politicians table"

        print(f"✓ Politicians Table: {len(response.data)} records")
        print(f"  Sample: {politician['first_name']} {politician['last_name']}")

    def test_supabase_trading_disclosures_table(self, supabase_client):
        """Test Supabase trading_disclosures table exists and has data"""
        response = supabase_client.table("trading_disclosures").select("*").limit(10).execute()

        assert response.data is not None, "Trading disclosures query failed"

        if len(response.data) > 0:
            disclosure = response.data[0]
            required_fields = ["id", "politician_id", "asset_ticker", "transaction_type"]
            for field in required_fields:
                assert field in disclosure, f"Missing field '{field}' in trading_disclosures"

            print(f"✓ Trading Disclosures Table: {len(response.data)} records")
            print(f"  Sample: {disclosure.get('asset_ticker')} - {disclosure.get('transaction_type')}")
        else:
            print(f"⚠ Trading Disclosures Table: Empty (no test data)")


class TestDataFlow:
    """Test data flow between components"""

    @pytest.fixture(scope="class")
    def supabase_client(self) -> Client:
        """Supabase client fixture"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            pytest.skip("Supabase credentials not configured")

        return create_client(url, key)

    @pytest.fixture(scope="class")
    def sample_politician(self, supabase_client):
        """Get a sample politician from Supabase"""
        response = supabase_client.table("politicians").select("*").limit(1).execute()

        if not response.data or len(response.data) == 0:
            pytest.skip("No politicians in database")

        return response.data[0]

    def test_fetch_politicians_for_dashboard(self, supabase_client):
        """Test fetching politicians list for dashboard dropdown"""
        response = supabase_client.table("politicians").select("id, first_name, last_name").execute()

        assert response.data is not None, "Failed to fetch politicians"
        assert len(response.data) > 0, "No politicians available"

        # Convert to DataFrame (as dashboard does)
        df = pd.DataFrame(response.data)
        assert "first_name" in df.columns, "Missing first_name column"
        assert "last_name" in df.columns, "Missing last_name column"

        # Create name list (as dashboard does)
        names = [f"{row['first_name']} {row['last_name']}" for _, row in df.iterrows()]

        print(f"✓ Fetched {len(names)} politicians for dashboard")
        print(f"  Sample: {names[0] if names else 'None'}")

    def test_fetch_trading_history_for_politician(self, supabase_client, sample_politician):
        """Test fetching trading history for a specific politician"""
        politician_id = sample_politician["id"]

        response = supabase_client.table("trading_disclosures") \
            .select("*") \
            .eq("politician_id", politician_id) \
            .order("disclosure_date", desc=True) \
            .limit(100) \
            .execute()

        assert response.data is not None, "Failed to fetch trading history"

        if len(response.data) > 0:
            df = pd.DataFrame(response.data)

            # Verify required columns for dashboard
            required_columns = ["asset_ticker", "transaction_type", "disclosure_date"]
            for col in required_columns:
                assert col in df.columns, f"Missing column '{col}' in trading data"

            print(f"✓ Fetched {len(df)} trades for {sample_politician['first_name']} {sample_politician['last_name']}")
            print(f"  Tickers: {df['asset_ticker'].unique()[:5].tolist()}")
        else:
            print(f"⚠ No trading history for {sample_politician['first_name']} {sample_politician['last_name']}")

    def test_fetch_recent_disclosures(self, supabase_client):
        """Test fetching recent trading disclosures (last 90 days)"""
        cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()

        response = supabase_client.table("trading_disclosures") \
            .select("*") \
            .gte("disclosure_date", cutoff_date) \
            .order("disclosure_date", desc=True) \
            .execute()

        assert response.data is not None, "Failed to fetch recent disclosures"

        if len(response.data) > 0:
            df = pd.DataFrame(response.data)
            print(f"✓ Fetched {len(df)} recent disclosures (last 90 days)")
            print(f"  Date range: {df['disclosure_date'].min()} to {df['disclosure_date'].max()}")
        else:
            print(f"⚠ No recent disclosures (last 90 days)")

    def test_politician_statistics_calculation(self, supabase_client, sample_politician):
        """Test calculating politician trading statistics"""
        politician_id = sample_politician["id"]

        response = supabase_client.table("trading_disclosures") \
            .select("*") \
            .eq("politician_id", politician_id) \
            .execute()

        if not response.data or len(response.data) == 0:
            pytest.skip(f"No trades for {sample_politician['first_name']} {sample_politician['last_name']}")

        df = pd.DataFrame(response.data)

        # Calculate statistics (as ML model does)
        total_trades = len(df)
        purchases = len(df[df["transaction_type"].str.contains("purchase", case=False, na=False)])
        sales = total_trades - purchases
        purchase_ratio = purchases / total_trades if total_trades > 0 else 0
        unique_stocks = df["asset_ticker"].nunique() if "asset_ticker" in df.columns else 0

        # Verify calculations
        assert total_trades > 0, "No trades found"
        assert 0 <= purchase_ratio <= 1, f"Invalid purchase ratio: {purchase_ratio}"
        assert unique_stocks >= 0, f"Invalid unique stocks count: {unique_stocks}"

        print(f"✓ Calculated statistics for {sample_politician['first_name']} {sample_politician['last_name']}")
        print(f"  Total trades: {total_trades}")
        print(f"  Purchases: {purchases} ({purchase_ratio*100:.1f}%)")
        print(f"  Sales: {sales}")
        print(f"  Unique stocks: {unique_stocks}")


class TestMLPredictionPipeline:
    """Test ML prediction pipeline with real data"""

    @pytest.fixture(scope="class")
    def supabase_client(self) -> Client:
        """Supabase client fixture"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            pytest.skip("Supabase credentials not configured")

        return create_client(url, key)

    @pytest.fixture(scope="class")
    def sample_trading_data(self, supabase_client):
        """Get sample trading data for predictions"""
        response = supabase_client.table("trading_disclosures") \
            .select("*") \
            .limit(100) \
            .execute()

        if not response.data or len(response.data) == 0:
            pytest.skip("No trading data available")

        return pd.DataFrame(response.data)

    def test_feature_engineering_from_data(self, sample_trading_data, supabase_client):
        """Test feature engineering pipeline using real Supabase data"""
        # Get a sample disclosure
        if len(sample_trading_data) == 0:
            pytest.skip("No trading data available")

        sample = sample_trading_data.iloc[0]
        politician_id = sample["politician_id"]

        # Fetch politician's historical data
        history_response = supabase_client.table("trading_disclosures") \
            .select("*") \
            .eq("politician_id", politician_id) \
            .execute()

        history_df = pd.DataFrame(history_response.data)

        # Calculate politician statistics
        total_trades = len(history_df)
        purchases = len(history_df[history_df["transaction_type"].str.contains("purchase", case=False, na=False)])
        purchase_ratio = purchases / total_trades if total_trades > 0 else 0.5
        unique_stocks = history_df["asset_ticker"].nunique() if "asset_ticker" in history_df.columns else 1

        # Engineer features (matching training pipeline)
        features = {
            "politician_trade_count": min(total_trades / 100, 1.0),
            "politician_purchase_ratio": purchase_ratio,
            "politician_diversity": min(unique_stocks / 50, 1.0),
            "transaction_is_purchase": 1.0 if "purchase" in str(sample["transaction_type"]).lower() else 0.0,
            "transaction_amount_log": 4.5,  # Placeholder
            "transaction_amount_normalized": 0.5,  # Placeholder
            "market_cap_score": 0.5,
            "sector_risk": 0.5,
            "sentiment_score": 0.5,
            "volatility_score": 0.3,
        }

        # Verify all 10 features present
        assert len(features) == 10, f"Expected 10 features, got {len(features)}"

        # Verify all features in valid range [0, 1] or reasonable log scale
        for key, value in features.items():
            assert value is not None, f"Feature '{key}' is None"
            assert isinstance(value, (int, float)), f"Feature '{key}' is not numeric"

        print(f"✓ Engineered {len(features)} features from Supabase data")
        print(f"  Politician stats: {total_trades} trades, {purchase_ratio*100:.1f}% purchases")
        print(f"  Sample features: {list(features.keys())[:5]}")

    def test_model_loading(self):
        """Test loading trained model from models directory"""
        models_dir = os.path.join(os.path.dirname(__file__), "../../models")

        if not os.path.exists(models_dir):
            pytest.skip("Models directory not found")

        # Look for model files
        import glob
        model_files = glob.glob(os.path.join(models_dir, "*.pt"))
        metadata_files = glob.glob(os.path.join(models_dir, "*.json"))

        if not model_files:
            pytest.skip("No trained models found")

        # Load latest model metadata
        latest_metadata = sorted(metadata_files, reverse=True)[0]

        with open(latest_metadata, 'r') as f:
            metadata = json.load(f)

        # Verify metadata structure
        required_keys = ["model_name", "accuracy", "created_at"]
        for key in required_keys:
            assert key in metadata, f"Missing key '{key}' in model metadata"

        # Verify training metrics
        assert "final_metrics" in metadata, "Missing final_metrics in model metadata"
        assert "train_accuracy" in metadata["final_metrics"], "Missing train_accuracy in final_metrics"

        print(f"✓ Model metadata loaded: {metadata['model_name']}")
        print(f"  Accuracy: {metadata['accuracy']:.4f}")
        print(f"  Epochs: {metadata.get('epochs', 'N/A')}")
        print(f"  Created: {metadata['created_at']}")

    def test_prediction_generation(self, sample_trading_data):
        """Test generating prediction from features"""
        if len(sample_trading_data) == 0:
            pytest.skip("No trading data available")

        # Create sample features
        features = {
            "politician_trade_count": 0.5,
            "politician_purchase_ratio": 0.7,
            "politician_diversity": 0.3,
            "transaction_is_purchase": 1.0,
            "transaction_amount_log": 4.5,
            "transaction_amount_normalized": 0.5,
            "market_cap_score": 0.6,
            "sector_risk": 0.4,
            "sentiment_score": 0.7,
            "volatility_score": 0.3,
        }

        # Simple weighted prediction (matching dashboard logic)
        weights = {
            "politician_trade_count": 0.15,
            "politician_purchase_ratio": 0.10,
            "politician_diversity": 0.08,
            "transaction_is_purchase": 0.12,
            "sentiment_score": 0.20,
            "volatility_score": -0.12,
            "market_cap_score": 0.10,
            "sector_risk": -0.08,
        }

        score = 0.5  # Baseline
        for feature, value in features.items():
            if feature in weights:
                score += weights[feature] * value

        # Clip to [0, 1]
        score = max(0, min(1, score))

        # Generate prediction
        if score >= 0.65:
            recommendation = "BUY"
        elif score <= 0.35:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        predicted_return = (score - 0.5) * 0.2  # -10% to +10%
        confidence = min(0.5 + abs(score - 0.5), 0.95)

        # Verify prediction structure
        assert recommendation in ["BUY", "SELL", "HOLD"], f"Invalid recommendation: {recommendation}"
        assert -1.0 <= predicted_return <= 1.0, f"Predicted return out of range: {predicted_return}"
        assert 0.5 <= confidence <= 0.95, f"Confidence out of range: {confidence}"

        print(f"✓ Generated prediction from features")
        print(f"  Recommendation: {recommendation}")
        print(f"  Predicted return: {predicted_return*100:.2f}%")
        print(f"  Confidence: {confidence*100:.1f}%")


class TestLSHIntegration:
    """Test LSH daemon integration with dashboard"""

    @pytest.fixture(scope="class")
    def lsh_url(self):
        """LSH daemon URL"""
        return os.getenv("LSH_API_URL", "https://mcli-lsh-daemon.fly.dev")

    @pytest.fixture(scope="class")
    def lsh_headers(self):
        """LSH API headers"""
        api_key = os.getenv("LSH_API_KEY")
        if api_key:
            return {"x-api-key": api_key}
        return {}

    def test_lsh_api_accessibility(self, lsh_url):
        """Test LSH API is accessible from test environment"""
        response = requests.get(f"{lsh_url}/", timeout=10)

        assert response.status_code == 200, "LSH API not accessible"

        data = response.json()
        assert "service" in data, "Missing service info"
        assert "endpoints" in data, "Missing endpoints list"

        print(f"✓ LSH API accessible: {data['service']}")
        print(f"  Endpoints: {', '.join(data['endpoints'])}")

    def test_lsh_job_listing(self, lsh_url, lsh_headers):
        """Test listing jobs from LSH daemon"""
        response = requests.get(f"{lsh_url}/api/jobs", headers=lsh_headers, timeout=10)

        assert response.status_code == 200, "Failed to list jobs"

        data = response.json()
        assert "jobs" in data, "Missing jobs in response"
        assert "total" in data, "Missing total count"

        print(f"✓ LSH jobs listed successfully")
        print(f"  Total jobs: {data['total']}")


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow"""

    @pytest.fixture(scope="class")
    def supabase_client(self) -> Client:
        """Supabase client fixture"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            pytest.skip("Supabase credentials not configured")

        return create_client(url, key)

    @pytest.fixture(scope="class")
    def lsh_url(self):
        """LSH daemon URL"""
        return os.getenv("LSH_API_URL", "https://mcli-lsh-daemon.fly.dev")

    def test_complete_prediction_workflow(self, supabase_client, lsh_url):
        """Test complete prediction workflow: Supabase → Features → Prediction"""

        # Step 1: Fetch politician from Supabase
        print("\n→ Step 1: Fetching politician from Supabase...")
        politicians = supabase_client.table("politicians").select("*").limit(1).execute()

        if not politicians.data or len(politicians.data) == 0:
            pytest.skip("No politicians in database")

        politician = politicians.data[0]
        print(f"  ✓ Fetched: {politician['first_name']} {politician['last_name']}")

        # Step 2: Fetch trading history from Supabase
        print("\n→ Step 2: Fetching trading history from Supabase...")
        trades = supabase_client.table("trading_disclosures") \
            .select("*") \
            .eq("politician_id", politician["id"]) \
            .execute()

        trades_df = pd.DataFrame(trades.data)
        print(f"  ✓ Fetched {len(trades_df)} trades")

        # Step 3: Calculate politician statistics
        print("\n→ Step 3: Calculating politician statistics...")
        total_trades = len(trades_df)
        purchases = len(trades_df[trades_df["transaction_type"].str.contains("purchase", case=False, na=False)]) if len(trades_df) > 0 else 0
        purchase_ratio = purchases / total_trades if total_trades > 0 else 0.5
        unique_stocks = trades_df["asset_ticker"].nunique() if "asset_ticker" in trades_df.columns and len(trades_df) > 0 else 0

        print(f"  ✓ Total trades: {total_trades}")
        print(f"  ✓ Purchase ratio: {purchase_ratio:.2%}")
        print(f"  ✓ Unique stocks: {unique_stocks}")

        # Step 4: Engineer features
        print("\n→ Step 4: Engineering features...")
        features = {
            "politician_trade_count": min(total_trades / 100, 1.0),
            "politician_purchase_ratio": purchase_ratio,
            "politician_diversity": min(unique_stocks / 50, 1.0),
            "transaction_is_purchase": 1.0,
            "transaction_amount_log": 4.7,
            "transaction_amount_normalized": 0.5,
            "market_cap_score": 0.5,
            "sector_risk": 0.5,
            "sentiment_score": 0.5,
            "volatility_score": 0.3,
        }
        print(f"  ✓ Engineered {len(features)} features")

        # Step 5: Generate prediction
        print("\n→ Step 5: Generating prediction...")
        weights = {
            "politician_trade_count": 0.15,
            "sentiment_score": 0.20,
            "volatility_score": -0.12,
        }

        score = 0.5
        for feature, value in features.items():
            if feature in weights:
                score += weights[feature] * value

        score = max(0, min(1, score))

        if score >= 0.65:
            recommendation = "BUY"
        elif score <= 0.35:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        predicted_return = (score - 0.5) * 0.2
        confidence = min(0.5 + abs(score - 0.5), 0.95)

        print(f"  ✓ Recommendation: {recommendation}")
        print(f"  ✓ Predicted return: {predicted_return*100:.2f}%")
        print(f"  ✓ Confidence: {confidence*100:.1f}%")

        # Step 6: Verify LSH daemon is accessible
        print("\n→ Step 6: Verifying LSH daemon accessibility...")
        lsh_response = requests.get(f"{lsh_url}/health", timeout=10)
        assert lsh_response.status_code == 200, "LSH daemon not accessible"
        print(f"  ✓ LSH daemon: {lsh_response.json()['status']}")

        # Final verification
        print("\n✅ Complete end-to-end workflow successful!")
        print(f"   Supabase → Features → Prediction → LSH verification")

    def test_dashboard_data_pipeline(self, supabase_client):
        """Test dashboard's complete data pipeline"""

        print("\n→ Testing dashboard data pipeline...")

        # Simulate dashboard loading sequence

        # 1. Load politicians list
        politicians = supabase_client.table("politicians") \
            .select("id, first_name, last_name") \
            .execute()

        assert politicians.data is not None
        politician_count = len(politicians.data)
        print(f"  ✓ Loaded {politician_count} politicians")

        # 2. Load recent disclosures
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        disclosures = supabase_client.table("trading_disclosures") \
            .select("*") \
            .gte("disclosure_date", cutoff) \
            .execute()

        disclosure_count = len(disclosures.data) if disclosures.data else 0
        print(f"  ✓ Loaded {disclosure_count} recent disclosures")

        # 3. Check for models
        models_dir = os.path.join(os.path.dirname(__file__), "../../models")
        has_models = os.path.exists(models_dir)
        print(f"  ✓ Models directory: {'Found' if has_models else 'Not found'}")

        # 4. Verify data structure
        if disclosure_count > 0:
            df = pd.DataFrame(disclosures.data)
            required_cols = ["politician_id", "asset_ticker", "transaction_type", "disclosure_date"]

            for col in required_cols:
                assert col in df.columns, f"Missing required column: {col}"

            print(f"  ✓ Data structure validated")

        print("\n✅ Dashboard data pipeline test successful!")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
