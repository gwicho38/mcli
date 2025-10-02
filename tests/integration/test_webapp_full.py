import pytest

pytestmark = pytest.mark.skip(reason="webapp module does not exist")

def test_skipped():
    """Placeholder test that is skipped"""
    pass