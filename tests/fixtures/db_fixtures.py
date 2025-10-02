"""Shared fixtures for database testing"""
import pytest
from unittest.mock import Mock, MagicMock
import sqlite3
from pathlib import Path


@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    conn = Mock(spec=sqlite3.Connection)
    cursor = Mock()

    # Mock cursor methods
    cursor.execute = Mock()
    cursor.fetchall = Mock(return_value=[])
    cursor.fetchone = Mock(return_value=None)
    cursor.close = Mock()

    conn.cursor = Mock(return_value=cursor)
    conn.commit = Mock()
    conn.close = Mock()

    return conn


@pytest.fixture
def temp_sqlite_db(tmp_path):
    """Create a temporary SQLite database"""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))

    # Create sample tables
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            title TEXT NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Insert sample data
    conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "alice@example.com"))
    conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Bob", "bob@example.com"))

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    client = Mock()

    # Mock table operations
    table_mock = Mock()
    table_mock.select = Mock(return_value=table_mock)
    table_mock.insert = Mock(return_value=table_mock)
    table_mock.update = Mock(return_value=table_mock)
    table_mock.delete = Mock(return_value=table_mock)
    table_mock.eq = Mock(return_value=table_mock)
    table_mock.execute = Mock(return_value=Mock(data=[], error=None))

    client.table = Mock(return_value=table_mock)
    client.auth = Mock()

    return client


@pytest.fixture
def sample_db_records():
    """Provide sample database records"""
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ]
