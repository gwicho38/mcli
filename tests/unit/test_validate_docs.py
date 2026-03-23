"""Tests for the documentation validator."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the validate_docs module from tools/ directly
_TOOLS_PATH = Path(__file__).resolve().parent.parent.parent / "tools" / "validate_docs.py"
_spec = importlib.util.spec_from_file_location("validate_docs", _TOOLS_PATH)
validate_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_docs)

check_version_consistency = validate_docs.check_version_consistency
check_python_syntax = validate_docs.check_python_syntax


@pytest.fixture
def doc_dir(tmp_path):
    """Create a temporary docs directory with test files."""
    docs = tmp_path / "docs"
    docs.mkdir()
    return docs


class TestVersionConsistency:
    """Test version consistency checking."""

    def test_matching_version(self, doc_dir):
        """No errors when versions match."""
        md_file = doc_dir / "install.md"
        md_file.write_text("Install with: `pip install mcli-framework==1.0.0`\n")

        errors = check_version_consistency([md_file], "1.0.0", verbose=False)
        assert errors == []

    def test_mismatched_version(self, doc_dir):
        """Error when version doesn't match."""
        md_file = doc_dir / "install.md"
        md_file.write_text("Install with: `pip install mcli==0.9.0`\n")

        errors = check_version_consistency([md_file], "1.0.0", verbose=False)
        assert len(errors) == 1
        assert "0.9.0" in errors[0]

    def test_skips_historical_docs(self, doc_dir):
        """Historical docs are skipped."""
        releases_dir = doc_dir / "releases"
        releases_dir.mkdir()
        md_file = releases_dir / "0.9.0.md"
        md_file.write_text("Install with: `pip install mcli==0.9.0`\n")

        errors = check_version_consistency([md_file], "1.0.0", verbose=False)
        assert errors == []


class TestPythonSyntax:
    """Test Python code block syntax checking."""

    def test_valid_code_block(self, doc_dir):
        """No errors for valid Python."""
        md_file = doc_dir / "example.md"
        md_file.write_text(
            "```python\nimport os\n\ndef hello():\n    print('hi')\n```\n"
        )

        errors = check_python_syntax([md_file], verbose=False)
        assert errors == []

    def test_invalid_code_block(self, doc_dir):
        """Errors for invalid Python that starts with import."""
        md_file = doc_dir / "example.md"
        md_file.write_text(
            "```python\nimport os\n\nif True:\n\n```\n"
        )

        errors = check_python_syntax([md_file], verbose=False)
        assert len(errors) == 1

    def test_fragment_skipped(self, doc_dir):
        """Code fragments (unexpected indent) are skipped."""
        md_file = doc_dir / "example.md"
        md_file.write_text("```python\n    x = 1\n    y = 2\n```\n")

        errors = check_python_syntax([md_file], verbose=False)
        assert errors == []
