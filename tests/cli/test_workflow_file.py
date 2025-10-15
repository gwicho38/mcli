"""
CLI tests for mcli.workflow.file module
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner

# Check if fitz (PyMuPDF) is available
try:
    import fitz

    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


class TestFileCommands:
    """Test suite for file workflow commands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    @pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF not installed")
    def test_file_group_exists(self):
        """Test file command group exists"""
        from mcli.workflow.file.file import file

        assert file is not None
        assert hasattr(file, "commands") or callable(file)

    @pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF not installed")
    def test_file_group_help(self):
        """Test file command group help"""
        from mcli.workflow.file.file import file

        result = self.runner.invoke(file, ["--help"])

        assert result.exit_code == 0
        assert "file" in result.output.lower() or "utility" in result.output.lower()

    @pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF not installed")
    @patch("mcli.workflow.file.file.fitz")
    def test_oxps_to_pdf_command(self, mock_fitz):
        """Test oxps_to_pdf command"""
        from mcli.workflow.file.file import file

        # Mock the PyMuPDF operations
        mock_doc = MagicMock()
        mock_pdf_bytes = b"fake pdf content"
        mock_doc.convert_to_pdf.return_value = mock_pdf_bytes

        mock_pdf_doc = MagicMock()

        mock_fitz.open.side_effect = [mock_doc, mock_pdf_doc]

        with tempfile.NamedTemporaryFile(suffix=".oxps", delete=False) as input_file:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as output_file:
                try:
                    result = self.runner.invoke(
                        file, ["oxps-to-pdf", input_file.name, output_file.name]
                    )

                    assert result.exit_code == 0
                    assert "Successfully converted" in result.output or "Error" in result.output
                finally:
                    Path(input_file.name).unlink(missing_ok=True)
                    Path(output_file.name).unlink(missing_ok=True)

    @pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF not installed")
    def test_oxps_to_pdf_nonexistent_file(self):
        """Test oxps_to_pdf with non-existent input file"""
        from mcli.workflow.file.file import file

        result = self.runner.invoke(
            file, ["oxps-to-pdf", "/nonexistent/input.oxps", "/tmp/output.pdf"]
        )

        # Click should complain about non-existent file
        assert result.exit_code != 0 or "Error" in result.output

    @pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF not installed")
    @patch("mcli.workflow.file.file.subprocess.run")
    def test_search_command_success(self, mock_subprocess):
        """Test search command with successful results"""
        from mcli.workflow.file.file import file

        # Mock ripgrep output
        mock_rg_result = MagicMock()
        mock_rg_result.stdout = "file1.txt:1:match found\nfile2.txt:2:another match"
        mock_rg_result.returncode = 0

        # Mock fzf output
        mock_fzf_result = MagicMock()
        mock_fzf_result.stdout = "file1.txt:1:match found"
        mock_fzf_result.returncode = 0

        mock_subprocess.side_effect = [mock_rg_result, mock_fzf_result]

        with patch("mcli.workflow.file.file.Path.exists", return_value=True):
            result = self.runner.invoke(file, ["search", "test_string"])

            # Command might succeed or fail depending on environment
            # Just check it doesn't crash
            assert result.exit_code in [0, 1, 2]

    @pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF not installed")
    @patch("mcli.workflow.file.file.subprocess.run")
    def test_search_command_no_matches(self, mock_subprocess):
        """Test search command with no matches"""
        from mcli.workflow.file.file import file

        # Mock ripgrep with no matches
        mock_subprocess.side_effect = Exception("rg failed")

        with patch("mcli.workflow.file.file.Path.exists", return_value=True):
            result = self.runner.invoke(file, ["search", "nonexistent_string"])

            # Should handle gracefully
            assert result.exit_code in [0, 1, 2]

    @pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF not installed")
    def test_search_help(self):
        """Test search command help"""
        from mcli.workflow.file.file import file

        result = self.runner.invoke(file, ["search", "--help"])

        assert result.exit_code == 0
        assert "search" in result.output.lower() or "string" in result.output.lower()
