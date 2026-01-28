"""Tests for IPFS sync retry logic with exponential backoff."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from mcli.lib.ipfs_sync import IPFSSync


class TestRetryWithBackoff:
    """Tests for the _retry_with_backoff helper method."""

    def test_succeeds_on_first_attempt(self):
        """Test that successful first attempt returns immediately."""
        sync = IPFSSync()
        call_count = 0

        def success_func():
            nonlocal call_count
            call_count += 1
            return (True, "result")

        result = sync._retry_with_backoff(success_func, max_retries=3)

        assert result == "result"
        assert call_count == 1

    def test_retries_on_failure(self):
        """Test that failures trigger retries."""
        sync = IPFSSync()
        call_count = 0

        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return (False, None)
            return (True, "success")

        # Use very small delays for testing
        result = sync._retry_with_backoff(
            fail_then_succeed, max_retries=3, base_delay=0.01, max_delay=0.05
        )

        assert result == "success"
        assert call_count == 3

    def test_retries_on_exception(self):
        """Test that exceptions trigger retries."""
        sync = IPFSSync()
        call_count = 0

        def raise_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.exceptions.Timeout("Connection timed out")
            return (True, "recovered")

        result = sync._retry_with_backoff(
            raise_then_succeed, max_retries=3, base_delay=0.01, max_delay=0.05
        )

        assert result == "recovered"
        assert call_count == 2

    def test_returns_none_after_max_retries(self):
        """Test that None is returned after all retries exhausted."""
        sync = IPFSSync()
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            return (False, None)

        result = sync._retry_with_backoff(
            always_fail, max_retries=2, base_delay=0.01, max_delay=0.05
        )

        assert result is None
        assert call_count == 3  # Initial + 2 retries

    def test_exponential_backoff_timing(self):
        """Test that delays follow exponential backoff pattern."""
        sync = IPFSSync()
        timestamps = []

        def record_and_fail():
            timestamps.append(time.time())
            return (False, None)

        sync._retry_with_backoff(
            record_and_fail, max_retries=2, base_delay=0.1, backoff_factor=2.0, max_delay=1.0
        )

        # Should have 3 timestamps (initial + 2 retries)
        assert len(timestamps) == 3

        # First delay should be ~0.1s
        first_delay = timestamps[1] - timestamps[0]
        assert 0.08 < first_delay < 0.15

        # Second delay should be ~0.2s (0.1 * 2)
        second_delay = timestamps[2] - timestamps[1]
        assert 0.15 < second_delay < 0.3

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        sync = IPFSSync()
        timestamps = []

        def record_and_fail():
            timestamps.append(time.time())
            return (False, None)

        sync._retry_with_backoff(
            record_and_fail,
            max_retries=3,
            base_delay=0.1,
            backoff_factor=10.0,  # Would be 1.0s without cap
            max_delay=0.15,
        )

        # All delays after first should be capped at 0.15
        for i in range(1, len(timestamps) - 1):
            delay = timestamps[i + 1] - timestamps[i]
            assert delay < 0.25  # Allow some margin for timing


class TestUploadWithRetry:
    """Tests for upload_to_ipfs with retry logic."""

    @patch.object(IPFSSync, "_check_local_ipfs", return_value=True)
    @patch("mcli.lib.ipfs_sync.requests.post")
    def test_upload_succeeds_with_retry(self, mock_post, mock_check):
        """Test upload succeeds after transient failure."""
        sync = IPFSSync()

        # First call fails, second succeeds
        mock_post.side_effect = [
            requests.exceptions.Timeout("timeout"),
            MagicMock(status_code=200, json=lambda: {"Hash": "QmTest123"}),
        ]

        result = sync.upload_to_ipfs({"test": "data"}, max_retries=2)

        assert result == "QmTest123"
        assert mock_post.call_count == 2

    @patch.object(IPFSSync, "_check_local_ipfs", return_value=True)
    @patch("mcli.lib.ipfs_sync.requests.post")
    def test_upload_fails_after_max_retries(self, mock_post, mock_check):
        """Test upload fails after exhausting retries."""
        sync = IPFSSync()

        # All calls fail
        mock_post.side_effect = requests.exceptions.ConnectionError("connection failed")

        result = sync.upload_to_ipfs({"test": "data"}, max_retries=2)

        assert result is None
        assert mock_post.call_count == 3  # Initial + 2 retries


class TestRetrieveWithRetry:
    """Tests for retrieve_from_ipfs with retry logic."""

    @patch("mcli.lib.ipfs_sync.requests.get")
    def test_retrieve_retries_on_rate_limit(self, mock_get):
        """Test retrieve retries on 429 rate limit response."""
        sync = IPFSSync()

        # First call rate limited, second succeeds
        mock_get.side_effect = [
            MagicMock(status_code=429),
            MagicMock(status_code=200, json=lambda: {"data": "value"}),
        ]

        result = sync.retrieve_from_ipfs("QmTest123", max_retries_per_gateway=2)

        assert result == {"data": "value"}
        assert mock_get.call_count == 2

    @patch("mcli.lib.ipfs_sync.requests.get")
    def test_retrieve_retries_on_server_error(self, mock_get):
        """Test retrieve retries on 5xx server error."""
        sync = IPFSSync()

        # First call server error, second succeeds
        mock_get.side_effect = [
            MagicMock(status_code=503),
            MagicMock(status_code=200, json=lambda: {"data": "value"}),
        ]

        result = sync.retrieve_from_ipfs("QmTest123", max_retries_per_gateway=2)

        assert result == {"data": "value"}

    @patch("mcli.lib.ipfs_sync.requests.get")
    def test_retrieve_tries_next_gateway_on_404(self, mock_get):
        """Test retrieve moves to next gateway on 404 (not found)."""
        sync = IPFSSync()

        # First gateway 404, second gateway succeeds
        mock_get.side_effect = [
            MagicMock(status_code=404),
            MagicMock(status_code=200, json=lambda: {"data": "value"}),
        ]

        result = sync.retrieve_from_ipfs("QmTest123", max_retries_per_gateway=1)

        assert result == {"data": "value"}
        # Should have tried 2 different gateways
        assert mock_get.call_count == 2

    @patch("mcli.lib.ipfs_sync.requests.get")
    def test_retrieve_fails_after_all_gateways_exhausted(self, mock_get):
        """Test retrieve returns None after all gateways fail."""
        sync = IPFSSync()

        # All calls fail with connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("failed")

        result = sync.retrieve_from_ipfs("QmTest123", max_retries_per_gateway=1)

        assert result is None
        # Should have tried each gateway with retries
        # 5 gateways * (1 initial + 1 retry) = 10 calls
        assert mock_get.call_count == 10
