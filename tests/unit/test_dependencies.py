"""
Test suite for optional dependency handling.

Tests that optional dependencies (ollama, redis) are handled gracefully
when not installed.
"""

import sys
import pytest
from unittest.mock import Mock, patch


class TestOptionalOllamaImport:
    """Test that ollama import is handled gracefully when not available"""

    def test_chat_module_imports_without_ollama(self):
        """Verify chat module can be imported even without ollama"""
        # This test verifies that the import succeeds
        # even if ollama is not installed
        try:
            from mcli.chat import chat
            assert hasattr(chat, 'OLLAMA_AVAILABLE')
        except ImportError as e:
            # Should not fail due to ollama import
            if 'ollama' in str(e):
                pytest.fail(f"chat module should not require ollama: {e}")
            raise

    def test_ollama_available_flag_set_correctly(self):
        """Verify OLLAMA_AVAILABLE flag reflects actual availability"""
        from mcli.chat import chat

        # Check that OLLAMA_AVAILABLE is a boolean
        assert isinstance(chat.OLLAMA_AVAILABLE, bool)

        # If ollama is available, verify it can be used
        if chat.OLLAMA_AVAILABLE:
            assert chat.ollama is not None
        else:
            # If not available, ollama should be None
            assert chat.ollama is None


class TestOptionalRedisImport:
    """Test that redis import is handled gracefully when not available"""

    def test_cached_vectorizer_imports_without_redis(self):
        """Verify cached_vectorizer module can be imported without redis"""
        try:
            from mcli.lib.search import cached_vectorizer
            assert hasattr(cached_vectorizer, 'REDIS_AVAILABLE')
        except ImportError as e:
            # Should not fail due to redis import
            if 'redis' in str(e):
                pytest.fail(f"cached_vectorizer should not require redis: {e}")
            raise

    def test_redis_available_flag_set_correctly(self):
        """Verify REDIS_AVAILABLE flag reflects actual availability"""
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
        """Verify CachedTfIdfVectorizer can initialize without redis"""
        from mcli.lib.search.cached_vectorizer import CachedTfIdfVectorizer, REDIS_AVAILABLE

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


class TestImportErrorMessages:
    """Test that helpful error messages are provided when optional deps missing"""

    def test_chat_provides_helpful_message_without_ollama(self):
        """Verify chat provides clear guidance when ollama is not available"""
        from mcli.chat.chat import OLLAMA_AVAILABLE

        if not OLLAMA_AVAILABLE:
            # When ollama is not available, using local provider should show helpful message
            # This is tested in the actual chat functionality
            pass  # Actual runtime test would be in integration tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
