"""
Test suite for optional dependency handling.

Tests that optional dependencies (redis) are handled gracefully
when not installed.
"""

import pytest


class TestOptionalRedisImport:
    """Test that redis import is handled gracefully when not available."""

    def test_cached_vectorizer_imports_without_redis(self):
        """Verify cached_vectorizer module can be imported without redis."""
        try:
            from mcli.lib.search import cached_vectorizer

            assert hasattr(cached_vectorizer, "REDIS_AVAILABLE")
        except ImportError as e:
            # Should not fail due to redis import
            if "redis" in str(e):
                pytest.fail(f"cached_vectorizer should not require redis: {e}")
            raise

    def test_redis_available_flag_set_correctly(self):
        """Verify REDIS_AVAILABLE flag reflects actual availability."""
        from mcli.lib.search import cached_vectorizer

        # Check that REDIS_AVAILABLE is a boolean
        assert isinstance(cached_vectorizer.REDIS_AVAILABLE, bool)

        # If redis is available, verify it can be used
        if cached_vectorizer.REDIS_AVAILABLE:
            assert cached_vectorizer.redis is not None
        else:
            # If not available, redis should be None
            assert cached_vectorizer.redis is None

    @pytest.mark.asyncio
    async def test_cached_vectorizer_works_without_redis(self):
        """Verify CachedTfIdfVectorizer can initialize without redis."""
        from mcli.lib.search.cached_vectorizer import REDIS_AVAILABLE, CachedTfIdfVectorizer

        # Should be able to create instance even without redis
        vectorizer = CachedTfIdfVectorizer()
        assert vectorizer is not None

        # Initialize should succeed (with warning if redis unavailable)
        await vectorizer.initialize()

        # Redis client state should match REDIS_AVAILABLE
        # If redis is not available, redis_client should be None
        # If redis is available, redis_client may or may not be None depending on connection
        if not REDIS_AVAILABLE:
            assert vectorizer.redis_client is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
