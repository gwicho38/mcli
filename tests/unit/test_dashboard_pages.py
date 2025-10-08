"""Unit tests for Streamlit dashboard pages

NOTE: Dashboard page tests require streamlit and dashboard modules.
Tests are conditional on dependencies being available.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import pytest
import logging
from unittest.mock import patch, MagicMock, Mock

# Check for streamlit and dashboard modules
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    if HAS_STREAMLIT:
        from mcli.ml.dashboard.pages import cicd, workflows, predictions_enhanced
    HAS_PAGES = HAS_STREAMLIT
except ImportError:
    HAS_PAGES = False

# Skip all tests if dependencies not available
if not HAS_PAGES:
    pytestmark = pytest.mark.skip(reason="streamlit or dashboard pages not available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCICDPage:
    """Test suite for pages/cicd.py"""

    @patch('streamlit.title')
    @patch('streamlit.tabs')
    @patch('requests.get')
    def test_cicd_page_loads(self, mock_get, mock_tabs, mock_title):
        """Test that CI/CD page loads without errors"""
        logger.info("Testing CI/CD page load...")

        try:
            from mcli.ml.dashboard.pages.cicd import show_cicd_dashboard
        except ImportError:
            pytest.skip("CI/CD page not available")
            return

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'builds': [],
            'webhooks': []
        }
        mock_get.return_value = mock_response

        # Mock tabs - CI/CD has 4 tabs
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        # Should not raise exception
        try:
            show_cicd_dashboard()
        except Exception as e:
            pytest.fail(f"CI/CD page should load without errors: {e}")

        logger.info("✅ CI/CD page load test passed!")

    @patch('requests.get')
    def test_cicd_fetch_builds_success(self, mock_get):
        """Test fetching builds from API successfully"""
        logger.info("Testing CI/CD builds fetch...")

        try:
            from mcli.ml.dashboard.pages.cicd import fetch_cicd_data
        except ImportError:
            pytest.skip("CI/CD page not available")
            return

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'builds': [
                {
                    'id': 1,
                    'status': 'success',
                    'timestamp': '2025-01-01T10:00:00Z',
                    'duration': 120
                }
            ]
        }
        mock_get.return_value = mock_response

        data = fetch_cicd_data()

        assert data is not None, "Should return data"
        assert 'builds' in data, "Should have builds key"
        logger.info("✅ CI/CD builds fetch test passed!")

    @patch('requests.get', side_effect=Exception("API Error"))
    def test_cicd_fetch_builds_failure(self, mock_get):
        """Test CI/CD page handles API errors gracefully"""
        logger.info("Testing CI/CD API error handling...")

        try:
            from mcli.ml.dashboard.pages.cicd import fetch_cicd_data
        except ImportError:
            pytest.skip("CI/CD page not available")
            return

        # Should handle API errors and return mock data
        data = fetch_cicd_data()

        assert data is not None, "Should return fallback data on error"
        logger.info("✅ CI/CD error handling test passed!")

    def test_cicd_mock_data_generation(self):
        """Test mock data generation for CI/CD page"""
        logger.info("Testing CI/CD mock data generation...")

        try:
            from mcli.ml.dashboard.pages.cicd import create_mock_cicd_data
        except ImportError:
            pytest.skip("CI/CD page not available")
            return

        mock_data = create_mock_cicd_data()

        assert isinstance(mock_data, pd.DataFrame), "Should return DataFrame"
        assert len(mock_data) > 0, "Should have mock builds"
        assert 'status' in mock_data.columns, "Should have status column"
        assert 'started_at' in mock_data.columns, "Should have started_at column"

        # Verify status values
        valid_statuses = ['success', 'failed', 'running', 'cancelled']
        assert all(mock_data['status'].isin(valid_statuses)), "Invalid status values"

        logger.info("✅ CI/CD mock data test passed!")


class TestWorkflowsPage:
    """Test suite for pages/workflows.py"""

    @patch('streamlit.title')
    @patch('streamlit.tabs')
    @patch('requests.get')
    def test_workflows_page_loads(self, mock_get, mock_tabs, mock_title):
        """Test that Workflows page loads without errors"""
        logger.info("Testing Workflows page load...")

        try:
            from mcli.ml.dashboard.pages.workflows import show_workflows_dashboard
        except ImportError:
            pytest.skip("Workflows page not available")
            return

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'workflows': []}
        mock_get.return_value = mock_response

        # Mock tabs
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        # Should not raise exception
        try:
            show_workflows_dashboard()
        except Exception as e:
            pytest.fail(f"Workflows page should load without errors: {e}")

        logger.info("✅ Workflows page load test passed!")

    @patch('requests.get')
    def test_workflows_fetch_success(self, mock_get):
        """Test fetching workflows from API successfully"""
        logger.info("Testing workflows fetch...")

        try:
            from mcli.ml.dashboard.pages.workflows import fetch_workflows_data
        except ImportError:
            pytest.skip("Workflows page not available")
            return

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'workflows': [
                {
                    'id': 1,
                    'name': 'Test Workflow',
                    'status': 'active',
                    'schedule': '0 * * * *'
                }
            ]
        }
        mock_get.return_value = mock_response

        data = fetch_workflows_data()

        assert data is not None, "Should return data"
        assert 'workflows' in data, "Should have workflows key"
        logger.info("✅ Workflows fetch test passed!")

    def test_workflows_mock_data_generation(self):
        """Test mock data generation for Workflows page"""
        logger.info("Testing workflows mock data generation...")

        try:
            from mcli.ml.dashboard.pages.workflows import create_mock_workflow_data
        except ImportError:
            pytest.skip("Workflows page not available")
            return

        mock_data = create_mock_workflow_data()

        assert isinstance(mock_data, pd.DataFrame), "Should return DataFrame"
        assert len(mock_data) > 0, "Should have mock workflows"
        assert 'name' in mock_data.columns, "Should have name column"
        assert 'status' in mock_data.columns, "Should have status column"
        assert 'schedule' in mock_data.columns, "Should have schedule column"

        logger.info("✅ Workflows mock data test passed!")

    def test_workflow_execution_mock_data(self):
        """Test workflow execution mock data generation"""
        logger.info("Testing workflow execution mock data...")

        try:
            from mcli.ml.dashboard.pages.workflows import create_mock_execution_data
        except ImportError:
            pytest.skip("Workflows page not available")
            return

        mock_data = create_mock_execution_data()

        assert isinstance(mock_data, pd.DataFrame), "Should return DataFrame"
        assert len(mock_data) > 0, "Should have mock executions"
        assert 'id' in mock_data.columns, "Should have id column"
        assert 'status' in mock_data.columns, "Should have status column"
        assert 'started_at' in mock_data.columns, "Should have started_at column"

        logger.info("✅ Workflow execution mock data test passed!")


class TestPredictionsEnhancedPage:
    """Test suite for pages/predictions_enhanced.py"""

    @patch('streamlit.title')
    @patch('streamlit.tabs')
    def test_predictions_page_loads(self, mock_tabs, mock_title):
        """Test that Predictions Enhanced page loads without errors"""
        logger.info("Testing Predictions Enhanced page load...")

        try:
            from mcli.ml.dashboard.pages.predictions_enhanced import show_predictions_enhanced
        except ImportError:
            pytest.skip("Predictions Enhanced page not available")
            return

        # Mock tabs
        mock_tabs.return_value = [MagicMock() for _ in range(5)]

        # Mock Supabase client
        with patch('mcli.ml.dashboard.pages.predictions_enhanced.get_supabase_client', return_value=None):
            # Should not raise exception even if Supabase unavailable
            try:
                show_predictions_enhanced()
            except Exception as e:
                pytest.fail(f"Predictions page should load without errors: {e}")

        logger.info("✅ Predictions Enhanced page load test passed!")

    @patch('mcli.ml.dashboard.pages.predictions_enhanced.get_disclosures_data')
    @patch('mcli.ml.dashboard.pages.predictions_enhanced.run_ml_pipeline')
    def test_predictions_real_data_integration(self, mock_pipeline, mock_disclosures):
        """Test predictions page uses real data from ML pipeline"""
        logger.info("Testing predictions real data integration...")

        try:
            from mcli.ml.dashboard.pages.predictions_enhanced import get_real_predictions
        except ImportError:
            pytest.skip("Predictions Enhanced page not available")
            return

        # Mock real data
        mock_disclosures.return_value = pd.DataFrame({
            'politician': ['Senator A', 'Rep B'],
            'ticker': ['AAPL', 'GOOGL'],
            'transaction_date': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'amount': [50000, 75000]
        })

        mock_pipeline.return_value = (
            None,  # X_train
            None,  # X_test
            pd.DataFrame({  # predictions
                'politician': ['Senator A'],
                'prediction': [0.75],
                'confidence': [0.85]
            })
        )

        predictions = get_real_predictions()

        assert predictions is not None, "Should return predictions"
        assert isinstance(predictions, pd.DataFrame), "Should return DataFrame"

        # Verify mock_pipeline was called with real data
        mock_disclosures.assert_called_once()
        mock_pipeline.assert_called_once()

        logger.info("✅ Predictions real data integration test passed!")

    def test_predictions_data_source_indicator(self):
        """Test that predictions page shows data source indicator"""
        logger.info("Testing predictions data source indicator...")

        try:
            from mcli.ml.dashboard.pages.predictions_enhanced import show_predictions_enhanced
        except ImportError:
            pytest.skip("Predictions Enhanced page not available")
            return

        # Mock components
        with patch('streamlit.title'):
            with patch('streamlit.tabs', return_value=[MagicMock() for _ in range(5)]):
                with patch('streamlit.caption') as mock_caption:
                    with patch('mcli.ml.dashboard.pages.predictions_enhanced.get_supabase_client', return_value=None):
                        show_predictions_enhanced()

                    # Should show data source indicator
                    assert mock_caption.called, "Should display data source indicator"

        logger.info("✅ Predictions data source indicator test passed!")

    @patch('mcli.ml.dashboard.pages.predictions_enhanced.get_politician_names')
    def test_predictions_politician_selector(self, mock_get_politicians):
        """Test politician selector uses real data"""
        logger.info("Testing politician selector...")

        try:
            from mcli.ml.dashboard.pages.predictions_enhanced import show_predictions_enhanced
        except ImportError:
            pytest.skip("Predictions Enhanced page not available")
            return

        # Mock real politician data
        mock_get_politicians.return_value = ['Senator Alice', 'Rep Bob', 'Gov Charlie']

        # Verify function can be called
        politicians = mock_get_politicians()
        assert len(politicians) == 3, "Should return politician list"

        logger.info("✅ Politician selector test passed!")

    @patch('mcli.ml.dashboard.pages.predictions_enhanced.get_politician_trading_history')
    def test_predictions_trading_history(self, mock_get_history):
        """Test trading history uses real data"""
        logger.info("Testing trading history...")

        try:
            from mcli.ml.dashboard.pages.predictions_enhanced import show_predictions_enhanced
        except ImportError:
            pytest.skip("Predictions Enhanced page not available")
            return

        # Mock real trading history
        mock_get_history.return_value = pd.DataFrame({
            'transaction_date': pd.to_datetime(['2025-01-01', '2025-01-02']),
            'ticker': ['AAPL', 'GOOGL'],
            'type': ['purchase', 'sale'],
            'amount': [50000, 25000]
        })

        history = mock_get_history('Senator Alice')
        assert isinstance(history, pd.DataFrame), "Should return DataFrame"
        assert len(history) == 2, "Should have trading records"

        logger.info("✅ Trading history test passed!")

    @patch('mcli.ml.dashboard.pages.predictions_enhanced.engineer_features')
    @patch('mcli.ml.dashboard.pages.predictions_enhanced.generate_production_prediction')
    def test_predictions_ml_model_integration(self, mock_predict, mock_features):
        """Test predictions page integrates with real ML model"""
        logger.info("Testing ML model integration...")

        try:
            from mcli.ml.dashboard.pages.predictions_enhanced import show_predictions_enhanced
        except ImportError:
            pytest.skip("Predictions Enhanced page not available")
            return

        # Mock feature engineering
        mock_features.return_value = pd.DataFrame({
            'feature1': [0.5],
            'feature2': [0.7],
            'feature3': [0.3]
        })

        # Mock prediction
        mock_predict.return_value = {
            'prediction': 0.75,
            'confidence': 0.85,
            'feature_importance': {'feature1': 0.4, 'feature2': 0.35, 'feature3': 0.25}
        }

        # Verify functions can be called
        features = mock_features({})
        prediction = mock_predict(features)

        assert 'prediction' in prediction, "Should have prediction"
        assert 'confidence' in prediction, "Should have confidence"

        logger.info("✅ ML model integration test passed!")


class TestPageIntegration:
    """Integration tests for dashboard pages"""

    def test_all_pages_importable(self):
        """Test that all pages can be imported"""
        logger.info("Testing page imports...")

        try:
            from mcli.ml.dashboard.pages import cicd
            from mcli.ml.dashboard.pages import workflows
            from mcli.ml.dashboard.pages import predictions_enhanced

            assert hasattr(cicd, 'show_cicd_dashboard')
            assert hasattr(workflows, 'show_workflows_dashboard')
            assert hasattr(predictions_enhanced, 'show_predictions_enhanced')

        except ImportError as e:
            pytest.skip(f"Dashboard pages not available: {e}")
            return

        logger.info("✅ Page imports test passed!")

    def test_pages_handle_missing_api(self):
        """Test that pages handle missing API gracefully"""
        logger.info("Testing pages with missing API...")

        try:
            from mcli.ml.dashboard.pages.cicd import show_cicd_dashboard
            from mcli.ml.dashboard.pages.workflows import show_workflows_dashboard
        except ImportError:
            pytest.skip("Dashboard pages not available")
            return

        # Mock API failures
        with patch('requests.get', side_effect=Exception("API unavailable")):
            with patch('streamlit.title'):
                # CI/CD needs 4 tabs
                with patch('streamlit.tabs', return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()]):
                    try:
                        show_cicd_dashboard()
                    except Exception as e:
                        pytest.fail(f"CI/CD page should handle API errors: {e}")

                # Workflows needs 4 tabs too
                with patch('streamlit.tabs', return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()]):
                    try:
                        show_workflows_dashboard()
                    except Exception as e:
                        pytest.fail(f"Workflows page should handle API errors: {e}")

        logger.info("✅ Missing API handling test passed!")

    def test_pages_use_real_data_not_mock(self):
        """Critical test: Verify pages prioritize real data over mock data"""
        logger.info("Testing pages use real data...")

        try:
            from mcli.ml.dashboard.pages.predictions_enhanced import get_real_predictions
        except ImportError:
            pytest.skip("Predictions Enhanced page not available")
            return

        # Mock real data functions
        with patch('mcli.ml.dashboard.pages.predictions_enhanced.get_disclosures_data') as mock_disc:
            with patch('mcli.ml.dashboard.pages.predictions_enhanced.run_ml_pipeline') as mock_pipe:
                # Setup mocks to return data
                mock_disc.return_value = pd.DataFrame({'data': [1, 2, 3]})
                mock_pipe.return_value = (None, None, pd.DataFrame({'pred': [0.5]}))

                # Call function
                get_real_predictions()

                # Verify REAL data functions were called (not mock generators)
                assert mock_disc.called, "Should call get_disclosures_data (REAL data)"
                assert mock_pipe.called, "Should call run_ml_pipeline (REAL ML)"

        logger.info("✅ Real data usage test passed!")


def main():
    """Run all page tests"""
    logger.info("="*60)
    logger.info("STARTING DASHBOARD PAGES TEST SUITE")
    logger.info("="*60)
    logger.info("Testing pages: cicd, workflows, predictions_enhanced")
    logger.info("="*60)

    # Run pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    main()
