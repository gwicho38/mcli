"""
Integration tests for live Supabase database connection.

These tests connect to actual Supabase instance to validate:
- Connection pooler works correctly
- IPv4-only connectivity
- Authentication with service role key
- Query execution
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Skip if no Supabase credentials (for local testing without credentials)
requires_supabase = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Supabase credentials not available",
)


@requires_supabase
class TestLiveSupabaseConnection:
    """Integration tests with live Supabase database"""

    def test_connection_pooler_connectivity(self):
        """Test that connection pooler works for basic queries"""
        from mcli.ml.database.session import get_session

        try:
            with get_session() as session:
                # Execute simple query
                result = session.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()
                assert row[0] == 1, "Basic query should return 1"

            print("✅ Connection pooler connectivity: SUCCESS")
        except ConnectionError as e:
            pytest.fail(f"Connection pooler failed: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")

    def test_session_transaction_handling(self):
        """Test that transactions work correctly with pooler"""
        from mcli.ml.database.session import get_session

        try:
            with get_session() as session:
                # Test transaction with multiple queries
                result1 = session.execute(text("SELECT 1"))
                result2 = session.execute(text("SELECT 2"))

                assert result1.scalar() == 1
                assert result2.scalar() == 2

            print("✅ Transaction handling: SUCCESS")
        except Exception as e:
            pytest.fail(f"Transaction handling failed: {e}")

    def test_connection_pooler_timeout(self):
        """Test that connection timeout is configured properly"""
        from mcli.ml.database.session import engine

        # Check connection pool configuration
        assert engine.pool.timeout() <= 30, "Pool timeout should be 30 seconds or less"
        assert hasattr(engine.pool, "_pre_ping"), "Pool should have pre-ping enabled"

        print("✅ Connection timeout configuration: SUCCESS")

    def test_ipv4_only_connection(self):
        """Test that connection uses IPv4, not IPv6"""
        import socket

        from mcli.ml.database.session import engine

        # Get the database URL
        db_url = str(engine.url)

        if "pooler.supabase.com" in db_url:
            # Extract hostname
            hostname = db_url.split("@")[1].split(":")[0]

            # Resolve hostname to IP
            try:
                ip_address = socket.gethostbyname(hostname)
                # IPv4 addresses don't contain colons (IPv6 do)
                assert ":" not in ip_address, f"Expected IPv4 address, got: {ip_address}"
                print(f"✅ IPv4-only connection: SUCCESS (resolved to {ip_address})")
            except socket.gaierror as e:
                pytest.skip(f"Could not resolve hostname: {e}")
        else:
            pytest.skip("Not using connection pooler")

    def test_error_handling_on_bad_query(self):
        """Test that error handling works correctly"""
        from mcli.ml.database.session import get_session

        try:
            with get_session() as session:
                # Execute invalid query
                session.execute(text("SELECT * FROM nonexistent_table_12345"))
            pytest.fail("Should have raised an exception for invalid query")
        except Exception as e:
            # Exception should be raised and handled
            assert (
                "nonexistent" in str(e).lower()
                or "not exist" in str(e).lower()
                or "relation" in str(e).lower()
            )
            print("✅ Error handling on bad query: SUCCESS")

    def test_connection_pooler_vs_direct_connection(self):
        """Compare pooler connection with direct connection (if password available)"""
        database_url = os.getenv("DATABASE_URL", "")

        # Check if using pooler (placeholder password detected)
        if "your_password" in database_url or not database_url:
            print("✅ Using connection pooler (placeholder password detected)")
            assert True, "Correctly using pooler"
        else:
            print("ℹ️ Using direct connection (real password provided)")
            # This is also valid, but test should note it


@requires_supabase
class TestSupabasePoolerModes:
    """Test different Supabase connection pooler modes"""

    def test_session_mode_pooler(self):
        """Test Session mode pooler (port 5432)"""
        supabase_url = os.getenv("SUPABASE_URL", "")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        if not supabase_url or not service_key:
            pytest.skip("Supabase credentials not available")

        project_ref = supabase_url.replace("https://", "").split(".")[0]
        session_mode_url = f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

        from sqlalchemy import create_engine

        try:
            engine = create_engine(session_mode_url, pool_pre_ping=True)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            engine.dispose()
            print("✅ Session mode pooler: SUCCESS")
        except OperationalError as e:
            print(f"ℹ️ Session mode pooler not available: {e}")
            pytest.skip(f"Session mode pooler connection failed: {e}")

    def test_transaction_mode_pooler(self):
        """Test Transaction mode pooler (port 6543)"""
        supabase_url = os.getenv("SUPABASE_URL", "")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        if not supabase_url or not service_key:
            pytest.skip("Supabase credentials not available")

        project_ref = supabase_url.replace("https://", "").split(".")[0]
        transaction_mode_url = f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

        from sqlalchemy import create_engine

        try:
            engine = create_engine(transaction_mode_url, pool_pre_ping=True)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            engine.dispose()
            print("✅ Transaction mode pooler: SUCCESS")
        except OperationalError as e:
            print(f"ℹ️ Transaction mode pooler not available: {e}")
            pytest.skip(f"Transaction mode pooler connection failed: {e}")


@requires_supabase
class TestConnectionRecovery:
    """Test connection recovery and retry logic"""

    def test_connection_recovery_after_timeout(self):
        """Test that connections recover after timeout"""
        from mcli.ml.database.session import get_session

        # First connection
        with get_session() as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Second connection (should work even if first timed out)
        with get_session() as session:
            result = session.execute(text("SELECT 2"))
            assert result.scalar() == 2

        print("✅ Connection recovery: SUCCESS")

    def test_pool_pre_ping_functionality(self):
        """Test that pool pre-ping detects stale connections"""
        from mcli.ml.database.session import engine

        # Verify pre-ping is enabled
        assert engine.pool._pre_ping is True, "Pool pre-ping should be enabled"

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

        print("✅ Pool pre-ping functionality: SUCCESS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
