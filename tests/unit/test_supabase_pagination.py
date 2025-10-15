"""Unit tests for Supabase pagination fix

Tests to validate that get_disclosures_data() correctly fetches ALL records
when for_training=True, overcoming Supabase's default 1000 record limit.

Bug: Supabase has implicit 1000 record limit even without .range()
Fix: Must explicitly use .range(0, total_count - 1) to fetch all records
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import logging
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSupabasePaginationFix:
    """Test that Supabase pagination correctly fetches all records"""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client"""
        client = MagicMock()

        # Mock the count response
        count_response = MagicMock()
        count_response.count = 7633  # Total records in database

        # Mock the data response (simulate returning all 7633 records)
        data_response = MagicMock()
        # Create 7633 mock records
        data_response.data = [
            {
                "id": f"record-{i}",
                "politician_id": f"pol-{i % 100}",
                "transaction_date": "2024-01-01T00:00:00Z",
                "disclosure_date": "2024-01-01T00:00:00Z",
                "transaction_type": "purchase",
                "asset_name": f"Asset {i}",
                "asset_ticker": "AAPL" if i % 2 == 0 else "MSFT",
                "asset_type": "Stock",
                "amount_range_min": 1000,
                "amount_range_max": 10000,
                "politicians": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "full_name": "John Doe",
                    "party": "Democrat",
                    "state_or_country": "CA",
                },
            }
            for i in range(7633)
        ]

        # Set up the query chain
        table_mock = MagicMock()
        select_mock = MagicMock()
        order_mock = MagicMock()
        range_mock = MagicMock()

        # Configure the chain
        client.table.return_value = table_mock
        table_mock.select.return_value = select_mock

        # For count query
        def select_side_effect(*args, **kwargs):
            if kwargs.get("count") == "exact":
                mock = MagicMock()
                mock.execute.return_value = count_response
                return mock
            else:
                return select_mock

        table_mock.select.side_effect = select_side_effect
        select_mock.order.return_value = order_mock
        order_mock.range.return_value = range_mock
        range_mock.execute.return_value = data_response
        order_mock.execute.return_value = data_response

        return client

    def test_for_training_true_fetches_all_records(self, mock_supabase_client):
        """Test that for_training=True fetches ALL 7633 records, not just 1000"""
        logger.info("Testing for_training=True fetches all records...")

        # Import the dashboard module
        try:
            from mcli.ml.dashboard.app_integrated import get_disclosures_data
        except ImportError:
            pytest.skip("Dashboard module not available")
            return

        # Patch the Supabase client
        with patch(
            "mcli.ml.dashboard.app_integrated.get_supabase_client",
            return_value=mock_supabase_client,
        ):
            # Patch streamlit to avoid rendering issues
            with patch("mcli.ml.dashboard.app_integrated.st") as mock_st:
                # Call with for_training=True
                result = get_disclosures_data(for_training=True)

                # Critical assertions
                assert result is not None, "Result should not be None"
                assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
                assert len(result) == 7633, f"Expected 7633 records, got {len(result)}"

                # Verify that .range(0, 7632) was called to fetch all records
                # (Supabase uses inclusive range, so 0 to total_count-1)
                table_mock = mock_supabase_client.table.return_value
                select_mock = table_mock.select.return_value
                order_mock = select_mock.order.return_value

                # Check that range was called with correct parameters
                order_mock.range.assert_called_with(0, 7632)

                # Verify info message was shown about loading all records
                mock_st.info.assert_called()
                info_call = mock_st.info.call_args[0][0]
                assert "7,633" in info_call, "Info message should mention total count"
                assert "ALL" in info_call, "Info message should say 'ALL'"

        logger.info("✅ Test passed: for_training=True fetches all 7633 records")

    def test_for_training_false_respects_pagination(self, mock_supabase_client):
        """Test that for_training=False uses pagination (limit=1000, offset=0)"""
        logger.info("Testing for_training=False respects pagination...")

        try:
            from mcli.ml.dashboard.app_integrated import get_disclosures_data
        except ImportError:
            pytest.skip("Dashboard module not available")
            return

        # Patch the Supabase client
        with patch(
            "mcli.ml.dashboard.app_integrated.get_supabase_client",
            return_value=mock_supabase_client,
        ):
            # Patch streamlit
            with patch("mcli.ml.dashboard.app_integrated.st") as mock_st:
                # Call with for_training=False (default), limit=1000, offset=0
                result = get_disclosures_data(for_training=False, limit=1000, offset=0)

                assert result is not None, "Result should not be None"
                assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"

                # Verify that .range(0, 999) was called for pagination
                table_mock = mock_supabase_client.table.return_value
                select_mock = table_mock.select.return_value
                order_mock = select_mock.order.return_value

                # Check that range was called with pagination parameters
                order_mock.range.assert_called_with(0, 999)  # offset=0, limit=1000 -> range(0, 999)

                # Verify pagination info was shown
                mock_st.info.assert_called()
                info_call = mock_st.info.call_args[0][0]
                assert "7,633 total" in info_call, "Info message should show total count"

        logger.info("✅ Test passed: for_training=False respects pagination")

    def test_pagination_with_offset(self, mock_supabase_client):
        """Test pagination with offset (e.g., page 2)"""
        logger.info("Testing pagination with offset...")

        try:
            from mcli.ml.dashboard.app_integrated import get_disclosures_data
        except ImportError:
            pytest.skip("Dashboard module not available")
            return

        with patch(
            "mcli.ml.dashboard.app_integrated.get_supabase_client",
            return_value=mock_supabase_client,
        ):
            with patch("mcli.ml.dashboard.app_integrated.st"):
                # Call with offset=1000 (page 2)
                result = get_disclosures_data(for_training=False, limit=1000, offset=1000)

                assert result is not None, "Result should not be None"

                # Verify that .range(1000, 1999) was called
                table_mock = mock_supabase_client.table.return_value
                select_mock = table_mock.select.return_value
                order_mock = select_mock.order.return_value

                order_mock.range.assert_called_with(
                    1000, 1999
                )  # offset=1000, limit=1000 -> range(1000, 1999)

        logger.info("✅ Test passed: pagination with offset works correctly")

    def test_supabase_unavailable_returns_demo_data(self):
        """Test that demo data is returned when Supabase is unavailable"""
        logger.info("Testing Supabase unavailable fallback...")

        try:
            from mcli.ml.dashboard.app_integrated import get_disclosures_data
        except ImportError:
            pytest.skip("Dashboard module not available")
            return

        # Patch get_supabase_client to return None (unavailable)
        with patch("mcli.ml.dashboard.app_integrated.get_supabase_client", return_value=None):
            result = get_disclosures_data(for_training=True)

            assert result is not None, "Result should not be None"
            assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
            assert not result.empty, "Demo data should not be empty"

            # Demo data should have expected columns
            expected_columns = [
                "transaction_date",
                "politician_name",
                "transaction_type",
                "asset_name",
            ]
            for col in expected_columns:
                assert col in result.columns, f"Demo data should have {col} column"

        logger.info("✅ Test passed: demo data returned when Supabase unavailable")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
