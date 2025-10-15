"""Shared fixtures for test data generation"""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_json_data():
    """Provide sample JSON data for testing"""
    return {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ],
        "posts": [
            {"id": 1, "user_id": 1, "title": "First Post", "content": "Hello World"},
            {"id": 2, "user_id": 2, "title": "Second Post", "content": "Test Content"},
        ],
    }


@pytest.fixture
def sample_csv_data():
    """Provide sample CSV data for testing"""
    return """name,age,city
Alice,30,New York
Bob,25,San Francisco
Charlie,35,Seattle
"""


@pytest.fixture
def temp_json_file(tmp_path, sample_json_data):
    """Create a temporary JSON file"""
    json_file = tmp_path / "test_data.json"
    json_file.write_text(json.dumps(sample_json_data, indent=2))
    return json_file


@pytest.fixture
def temp_csv_file(tmp_path, sample_csv_data):
    """Create a temporary CSV file"""
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(sample_csv_data)
    return csv_file


@pytest.fixture
def sample_log_entries():
    """Provide sample log entries for testing"""
    return [
        "2025-10-02 10:00:00 INFO Starting application",
        "2025-10-02 10:00:01 DEBUG Loading configuration",
        "2025-10-02 10:00:02 INFO Configuration loaded successfully",
        "2025-10-02 10:00:05 WARNING API rate limit approaching",
        "2025-10-02 10:00:10 ERROR Failed to connect to database",
        "2025-10-02 10:00:15 INFO Retrying connection...",
        "2025-10-02 10:00:20 INFO Connection established",
    ]


@pytest.fixture
def temp_log_file(tmp_path, sample_log_entries):
    """Create a temporary log file"""
    log_file = tmp_path / "test.log"
    log_file.write_text("\n".join(sample_log_entries))
    return log_file


@pytest.fixture
def sample_ml_dataset():
    """Provide sample ML dataset for testing"""
    import numpy as np

    return {
        "features": np.random.rand(100, 10).tolist(),
        "labels": np.random.randint(0, 2, 100).tolist(),
        "feature_names": [f"feature_{i}" for i in range(10)],
    }


@pytest.fixture
def sample_time_series():
    """Provide sample time series data"""
    import random
    from datetime import datetime, timedelta

    start_date = datetime(2025, 1, 1)
    data = []

    for i in range(30):
        date = start_date + timedelta(days=i)
        value = random.uniform(10, 100)
        data.append({"date": date.isoformat(), "value": value})

    return data
