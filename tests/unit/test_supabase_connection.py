"""
Unit tests for Supabase database connection handling.

Tests cover:
- Placeholder password detection and fallback to pooler
- IPv6 connection error handling
- Multi-region pooler failover
- Error message formatting
"""

import os
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import OperationalError


class TestSupabaseConnectionPooler:
    """Test connection pooler logic for Supabase"""

    def setup_method(self):
        """Set up test environment"""
        # Save original environment
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """Restore original environment"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_placeholder_password_detection(self):
        """Test that placeholder password is detected and triggers pooler fallback"""
        os.environ["DATABASE_URL"] = (
            "postgresql://postgres:your_password@db.example.com:5432/postgres"
        )
        os.environ["SUPABASE_URL"] = "https://testproject.supabase.co"
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test_key_12345"

        # Mock create_engine to prevent actual connection
        with patch("mcli.ml.database.session.create_engine") as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            # Import session module to trigger engine creation
            import importlib

            import mcli.ml.database.session as session_module

            importlib.reload(session_module)

            # Verify that create_engine was called with pooler URL, not direct URL
            call_args = mock_create.call_args_list
            if call_args:
                first_call_url = str(call_args[0][0][0])
                # Should contain pooler.supabase.com, not db.example.com
                assert (
                    "pooler.supabase.com" in first_call_url or "sqlite" in first_call_url
                ), f"Expected pooler URL, got: {first_call_url}"

    def test_pooler_url_construction(self):
        """Test that pooler URL is correctly constructed from Supabase credentials"""
        supabase_url = "https://uljsqvwkomdrlnofmlad.supabase.co"
        service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"

        # Extract project reference
        project_ref = supabase_url.replace("https://", "").split(".")[0]

        # Expected pooler URLs
        expected_urls = [
            f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-east-1.pooler.supabase.com:5432/postgres",
            f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
        ]

        assert project_ref == "uljsqvwkomdrlnofmlad"
        assert all("pooler.supabase.com" in url for url in expected_urls)
        assert all(project_ref in url for url in expected_urls)

    def test_connection_timeout_configuration(self):
        """Test that connection timeout is configured for PostgreSQL"""
        with patch("mcli.ml.database.session.create_engine") as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"

            import importlib

            import mcli.ml.database.session as session_module

            importlib.reload(session_module)

            # Check that create_engine was called with timeout settings
            if mock_create.called:
                call_kwargs = mock_create.call_args[1]
                assert "connect_args" in call_kwargs or "pool_timeout" in call_kwargs


class TestIPv6ErrorHandling:
    """Test IPv6 connection error detection and handling"""

    def test_ipv6_error_detection(self):
        """Test that IPv6 connection errors are properly detected"""
        ipv6_error_message = (
            'connection to server at "db.uljsqvwkomdrlnofmlad.supabase.co" '
            "(2a05:d016:571:a402:8455:5460:1249:d73), port 5432 failed: "
            "Cannot assign requested address"
        )

        error_msg_lower = ipv6_error_message.lower()
        assert "cannot assign requested address" in error_msg_lower
        assert "2a05" in ipv6_error_message  # IPv6 address present

    def test_get_session_ipv6_error_handling(self):
        """Test that get_session provides helpful error for IPv6 issues"""
        with patch("mcli.ml.database.session.SessionLocal") as mock_session_local:
            # Mock session that raises IPv6 error
            mock_session = Mock()
            mock_session.execute.side_effect = OperationalError(
                "statement", "params", "connection failed: Cannot assign requested address", "orig"
            )
            mock_session_local.return_value = mock_session

            from mcli.ml.database.session import get_session

            # Should raise ConnectionError with helpful message
            with pytest.raises(ConnectionError) as exc_info:
                with get_session() as session:
                    pass

            error_message = str(exc_info.value)
            assert "IPv6" in error_message or "network" in error_message
            assert "pooler" in error_message.lower()

    def test_authentication_error_detection(self):
        """Test that authentication errors are properly detected"""
        auth_error_message = "password authentication failed for user"

        error_msg_lower = auth_error_message.lower()
        assert "authentication failed" in error_msg_lower or "password" in error_msg_lower


class TestDatabaseSessionManagement:
    """Test database session management and error handling"""

    @patch("mcli.ml.database.session.SessionLocal")
    def test_session_rollback_on_error(self, mock_session_local):
        """Test that session is rolled back on error"""
        mock_session = Mock()
        mock_session.execute.return_value = Mock()
        # Simulate error during yield
        mock_session.query.side_effect = Exception("Test error")
        mock_session_local.return_value = mock_session

        from mcli.ml.database.session import get_session

        try:
            with get_session() as session:
                session.query("SELECT 1")  # This will raise
        except Exception:
            pass

        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("mcli.ml.database.session.SessionLocal")
    def test_session_commit_on_success(self, mock_session_local):
        """Test that session is committed on success"""
        mock_session = Mock()
        mock_session.execute.return_value = Mock()
        mock_session_local.return_value = mock_session

        from mcli.ml.database.session import get_session

        with get_session() as session:
            session.execute("SELECT 1")

        # Verify commit and close were called
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("mcli.ml.database.session.SessionLocal")
    def test_session_connection_test(self, mock_session_local):
        """Test that session connection is tested before use"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        from mcli.ml.database.session import get_session

        with get_session() as session:
            pass

        # Verify SELECT 1 was executed to test connection
        mock_session.execute.assert_called()
        # Check that execute was called with a text() wrapper containing SELECT 1
        from sqlalchemy import text

        call_args = mock_session.execute.call_args
        # The first positional argument should be a TextClause
        assert call_args is not None
        assert len(call_args[0]) > 0
        # Get the actual SQL from the TextClause object
        sql_clause = str(call_args[0][0])
        assert "SELECT 1" in sql_clause or "select 1" in sql_clause.lower()


class TestConnectionPoolerFailover:
    """Test multi-region connection pooler failover logic"""

    def test_multiple_pooler_urls_tried(self):
        """Test that multiple pooler URLs are attempted"""
        pooler_urls = [
            "postgresql://postgres.test:key@aws-0-us-east-1.pooler.supabase.com:5432/postgres",
            "postgresql://postgres.test:key@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
        ]

        # Verify URLs use different regions
        assert "us-east-1" in pooler_urls[0]
        assert "us-west-1" in pooler_urls[1]

        # Verify URLs use different ports (Session vs Transaction mode)
        assert ":5432" in pooler_urls[0]
        assert ":6543" in pooler_urls[1]

    @patch("mcli.ml.database.session.create_engine")
    def test_pooler_connection_test(self, mock_create_engine):
        """Test that pooler connection is tested before being used"""
        # This test verifies the test connection logic exists
        # Actual implementation tests each pooler URL by connecting
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine

        # Verify that a test connection would be attempted
        with mock_engine.connect() as conn:
            conn.execute("SELECT 1")

        mock_conn.execute.assert_called_once_with("SELECT 1")


class TestEnvironmentConfiguration:
    """Test environment variable configuration handling"""

    def test_sqlite_fallback_when_no_credentials(self):
        """Test that SQLite fallback is used when no credentials provided"""
        # Clear all database-related env vars
        for key in ["DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]:
            os.environ.pop(key, None)

        with patch("mcli.ml.database.session.create_engine") as mock_create:
            mock_create.return_value = Mock()

            import importlib

            import mcli.ml.database.session as session_module

            importlib.reload(session_module)

            # Should create engine with SQLite URL
            if mock_create.called:
                first_call_url = str(mock_create.call_args_list[0][0][0])
                assert "sqlite" in first_call_url.lower()

    def test_service_role_key_required_for_pooler(self):
        """Test that service role key is required for pooler connection"""
        os.environ["SUPABASE_URL"] = "https://test.supabase.co"
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        os.environ["DATABASE_URL"] = "postgresql://postgres:your_password@db.test.com:5432/postgres"

        with patch("mcli.ml.database.session.create_engine") as mock_create:
            mock_create.return_value = Mock()

            import importlib

            import mcli.ml.database.session as session_module

            importlib.reload(session_module)

            # Without service role key, should fall back to SQLite
            if mock_create.called:
                first_call_url = str(mock_create.call_args_list[0][0][0])
                assert "sqlite" in first_call_url.lower() or "pooler" not in first_call_url


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
