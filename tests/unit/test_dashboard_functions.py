"""Unit tests for ML Dashboard functions
Specifically testing bug fixes and edge cases
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_lsh_jobs_nonexistent_file():
    """
    Test that get_lsh_jobs returns empty DataFrame when log file doesn't exist.

    This tests the bug fix for AttributeError on Streamlit Cloud deployment.
    Bug: Function was returning None when file didn't exist
    Fix: Always return pd.DataFrame() even when file doesn't exist

    Root cause: Line 416 in app_integrated.py tried to check lsh_jobs.empty
    when lsh_jobs was None, causing AttributeError: 'NoneType' object has no attribute 'empty'
    """
    logger.info("Testing LSH jobs with nonexistent file...")

    # Import here to avoid Streamlit dependencies
    try:
        from mcli.ml.dashboard.app_integrated import get_lsh_jobs
    except ImportError:
        logger.warning("Cannot import dashboard - skipping test")
        pytest.skip("Dashboard module not available")
        return

    # Mock Path.exists to return False (file doesn't exist)
    with patch('mcli.ml.dashboard.app_integrated.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        result = get_lsh_jobs()

        # Critical assertion: result must be a DataFrame, not None
        assert result is not None, "get_lsh_jobs must not return None"
        assert isinstance(result, pd.DataFrame), "get_lsh_jobs must return DataFrame"
        assert result.empty, "DataFrame should be empty when file doesn't exist"

        # Verify we can call .empty without AttributeError
        try:
            is_empty = result.empty
            assert is_empty == True, "Empty DataFrame check should work"
        except AttributeError:
            pytest.fail("Calling .empty on result raised AttributeError (None was returned)")

    logger.info("✅ LSH jobs nonexistent file test passed!")


def test_lsh_jobs_empty_file():
    """Test that get_lsh_jobs handles empty log file correctly"""
    logger.info("Testing LSH jobs with empty file...")

    try:
        from mcli.ml.dashboard.app_integrated import get_lsh_jobs
    except ImportError:
        logger.warning("Cannot import dashboard - skipping test")
        pytest.skip("Dashboard module not available")
        return

    # Create temporary empty file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        temp_path = f.name

    try:
        # Mock Path to point to our temp file
        with patch('mcli.ml.dashboard.app_integrated.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance

            # Mock open to read our temp file
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.readlines.return_value = []

                result = get_lsh_jobs()

                assert result is not None, "get_lsh_jobs must not return None"
                assert isinstance(result, pd.DataFrame), "get_lsh_jobs must return DataFrame"
                assert result.empty, "DataFrame should be empty when log has no jobs"
    finally:
        # Clean up temp file
        Path(temp_path).unlink()

    logger.info("✅ LSH jobs empty file test passed!")


def test_lsh_jobs_with_valid_data():
    """Test that get_lsh_jobs parses valid log data correctly"""
    logger.info("Testing LSH jobs with valid data...")

    try:
        from mcli.ml.dashboard.app_integrated import get_lsh_jobs
    except ImportError:
        logger.warning("Cannot import dashboard - skipping test")
        pytest.skip("Dashboard module not available")
        return

    # Create valid log data
    log_lines = [
        "2025-10-06 10:00:00 | INFO | Started scheduled job | ml_training\n",
        "2025-10-06 10:05:00 | INFO | Completed job | ml_training\n",
        "2025-10-06 10:10:00 | INFO | Started scheduled job | data_sync\n"
    ]

    with patch('mcli.ml.dashboard.app_integrated.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = log_lines

            result = get_lsh_jobs()

            assert result is not None, "get_lsh_jobs must not return None"
            assert isinstance(result, pd.DataFrame), "get_lsh_jobs must return DataFrame"
            assert not result.empty, "DataFrame should contain parsed jobs"
            assert len(result) > 0, "Should have parsed at least one job"

            # Verify expected columns exist
            expected_columns = ['timestamp', 'status', 'job_name']
            for col in expected_columns:
                assert col in result.columns, f"Missing column: {col}"

            # Verify status values
            assert all(result['status'].isin(['running', 'completed'])), "Invalid status values"

    logger.info("✅ LSH jobs valid data test passed!")


def test_lsh_jobs_with_malformed_data():
    """Test that get_lsh_jobs handles malformed log data gracefully"""
    logger.info("Testing LSH jobs with malformed data...")

    try:
        from mcli.ml.dashboard.app_integrated import get_lsh_jobs
    except ImportError:
        logger.warning("Cannot import dashboard - skipping test")
        pytest.skip("Dashboard module not available")
        return

    # Create malformed log data (missing delimiters, etc.)
    log_lines = [
        "2025-10-06 10:00:00 - Some random log line without pipes\n",
        "Invalid line\n",
        "",
        "2025-10-06 | Only | Two | Parts\n"
    ]

    with patch('mcli.ml.dashboard.app_integrated.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = log_lines

            result = get_lsh_jobs()

            # Should still return DataFrame, not crash
            assert result is not None, "get_lsh_jobs must not return None"
            assert isinstance(result, pd.DataFrame), "get_lsh_jobs must return DataFrame"
            # May be empty if no valid lines parsed

    logger.info("✅ LSH jobs malformed data test passed!")


def test_lsh_jobs_with_file_read_error():
    """Test that get_lsh_jobs handles file read errors gracefully"""
    logger.info("Testing LSH jobs with file read error...")

    try:
        from mcli.ml.dashboard.app_integrated import get_lsh_jobs
    except ImportError:
        logger.warning("Cannot import dashboard - skipping test")
        pytest.skip("Dashboard module not available")
        return

    with patch('mcli.ml.dashboard.app_integrated.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        # Mock open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = get_lsh_jobs()

            # Should return empty DataFrame on error, not crash or return None
            assert result is not None, "get_lsh_jobs must not return None on error"
            assert isinstance(result, pd.DataFrame), "get_lsh_jobs must return DataFrame on error"
            assert result.empty, "DataFrame should be empty on read error"

    logger.info("✅ LSH jobs file read error test passed!")


def test_lsh_jobs_empty_attribute_accessible():
    """
    Regression test: Verify that .empty attribute is always accessible.

    This is the exact error that occurred on Streamlit Cloud:
    AttributeError: 'NoneType' object has no attribute 'empty'
    at line 416: active_jobs = len(lsh_jobs[lsh_jobs['status'] == 'running']) if not lsh_jobs.empty else 0
    """
    logger.info("Testing LSH jobs .empty attribute accessibility...")

    try:
        from mcli.ml.dashboard.app_integrated import get_lsh_jobs
    except ImportError:
        logger.warning("Cannot import dashboard - skipping test")
        pytest.skip("Dashboard module not available")
        return

    # Test with nonexistent file (the scenario that caused the bug)
    with patch('mcli.ml.dashboard.app_integrated.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        lsh_jobs = get_lsh_jobs()

        # This should NOT raise AttributeError
        try:
            # This is the exact code from line 416 that was failing
            active_jobs = len(lsh_jobs[lsh_jobs['status'] == 'running']) if not lsh_jobs.empty else 0
            assert active_jobs == 0, "Active jobs should be 0 for empty DataFrame"

            # Also test the code from line 420
            total_jobs_msg = f"{len(lsh_jobs)} total" if not lsh_jobs.empty else "0 total"
            assert total_jobs_msg == "0 total", "Should show 0 total jobs"

        except AttributeError as e:
            pytest.fail(f"AttributeError raised when accessing .empty: {e}")

    logger.info("✅ LSH jobs .empty attribute test passed!")


def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("STARTING DASHBOARD FUNCTIONS TEST SUITE")
    logger.info("="*60)
    logger.info("Testing bug fix: LSH jobs returns DataFrame not None")
    logger.info("="*60)

    # Run pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    main()
