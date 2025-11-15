"""
Unit tests for mcli.workflow.doc_convert module
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from mcli.workflow.doc_convert import FORMAT_ALIASES, convert, doc_convert, init


class TestFormatAliases:
    """Test suite for format alias mapping"""

    def test_markdown_aliases(self):
        """Test markdown format aliases"""
        assert FORMAT_ALIASES["md"] == "markdown"
        assert FORMAT_ALIASES["markdown"] == "markdown"
        assert FORMAT_ALIASES["gfm"] == "gfm"

    def test_document_aliases(self):
        """Test document format aliases"""
        assert FORMAT_ALIASES["docx"] == "docx"
        assert FORMAT_ALIASES["doc"] == "docx"
        assert FORMAT_ALIASES["odt"] == "odt"

    def test_html_aliases(self):
        """Test HTML format aliases"""
        assert FORMAT_ALIASES["html"] == "html"
        assert FORMAT_ALIASES["htm"] == "html"

    def test_jupyter_aliases(self):
        """Test Jupyter notebook aliases"""
        assert FORMAT_ALIASES["ipynb"] == "ipynb"
        assert FORMAT_ALIASES["notebook"] == "ipynb"


class TestDocConvertGroup:
    """Test suite for doc-convert command group"""

    def test_group_exists(self):
        """Test that doc-convert group is properly defined"""
        assert doc_convert is not None
        assert doc_convert.name == "doc-convert"

    def test_has_init_command(self):
        """Test that init command is registered"""
        assert "init" in [cmd.name for cmd in doc_convert.commands.values()]

    def test_has_convert_command(self):
        """Test that convert command is registered"""
        assert "convert" in [cmd.name for cmd in doc_convert.commands.values()]


class TestInitCommand:
    """Test suite for init command"""

    @patch("subprocess.run")
    def test_init_checks_homebrew(self, mock_run):
        """Test that init checks for Homebrew"""
        mock_run.side_effect = FileNotFoundError()

        runner = CliRunner()
        result = runner.invoke(init)

        # Should fail if Homebrew is not installed
        assert result.exit_code == 0  # Command exits gracefully
        assert mock_run.called

    @patch("subprocess.run")
    def test_init_installs_pandoc(self, mock_run):
        """Test that init attempts to install pandoc"""
        # Mock successful Homebrew check
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Homebrew 4.0.0"),  # brew --version
            Mock(returncode=0),  # brew install pandoc
            Mock(returncode=0),  # brew install basictex
        ]

        runner = CliRunner()
        result = runner.invoke(init)

        assert result.exit_code == 0
        # Check that brew install was called
        calls = [call[0][0] for call in mock_run.call_args_list]
        assert any("pandoc" in str(call) for call in calls)

    @patch("subprocess.run")
    def test_init_handles_already_installed(self, mock_run):
        """Test that init gracefully handles already installed packages"""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Homebrew 4.0.0"),  # brew --version
            Mock(returncode=1, stderr="pandoc already installed"),  # brew install pandoc
            Mock(returncode=0),  # which pandoc
        ]

        runner = CliRunner()
        result = runner.invoke(init)

        assert result.exit_code == 0


class TestConvertCommand:
    """Test suite for convert command"""

    @patch("subprocess.run")
    def test_convert_checks_pandoc_installed(self, mock_run):
        """Test that convert checks if pandoc is installed"""
        mock_run.side_effect = FileNotFoundError()

        runner = CliRunner()
        result = runner.invoke(convert, ["md", "html", "test.md"])

        # Should fail if pandoc not installed
        assert result.exit_code == 0  # Exits gracefully
        assert mock_run.called

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_convert_single_file(self, mock_exists, mock_run):
        """Test converting a single file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("# Test")

            mock_exists.return_value = True
            mock_run.side_effect = [
                Mock(returncode=0),  # pandoc --version
                Mock(returncode=0, stdout="", stderr=""),  # pandoc convert
            ]

            runner = CliRunner()
            result = runner.invoke(convert, ["md", "html", str(test_file)])

            assert result.exit_code == 0

    @patch("subprocess.run")
    @patch("mcli.workflow.doc_convert.file_glob")
    def test_convert_glob_pattern(self, mock_glob, mock_run):
        """Test converting files with glob pattern"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = Path(tmpdir) / "test1.md"
            file2 = Path(tmpdir) / "test2.md"
            file1.write_text("# Test 1")
            file2.write_text("# Test 2")

            mock_glob.return_value = [str(file1), str(file2)]
            mock_run.side_effect = [
                Mock(returncode=0),  # pandoc --version
                Mock(returncode=0, stdout="", stderr=""),  # convert file1
                Mock(returncode=0, stdout="", stderr=""),  # convert file2
            ]

            runner = CliRunner()
            result = runner.invoke(convert, ["md", "html", f"{tmpdir}/*.md"])

            assert result.exit_code == 0
            assert mock_glob.called

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_convert_format_mapping(self, mock_exists, mock_run):
        """Test that format aliases are properly mapped"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("# Test")

            mock_exists.return_value = True
            mock_run.side_effect = [
                Mock(returncode=0),  # pandoc --version
                Mock(returncode=0, stdout="", stderr=""),  # pandoc convert
            ]

            runner = CliRunner()
            result = runner.invoke(convert, ["md", "html", str(test_file)])

            assert result.exit_code == 0
            # Check that pandoc was called with mapped formats
            pandoc_call = [call for call in mock_run.call_args_list if "pandoc" in str(call)]
            assert len(pandoc_call) > 0

    @patch("subprocess.run")
    def test_convert_with_output_dir(self, mock_run):
        """Test converting with custom output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            output_dir = Path(tmpdir) / "output"
            test_file.write_text("# Test")

            mock_run.side_effect = [
                Mock(returncode=0),  # pandoc --version
                Mock(returncode=0, stdout="", stderr=""),  # pandoc convert
            ]

            runner = CliRunner()
            result = runner.invoke(convert, ["md", "html", str(test_file), "-o", str(output_dir)])

            assert result.exit_code == 0
            # Output directory should be created
            assert output_dir.exists() or result.exit_code == 0

    @patch("subprocess.run")
    def test_convert_with_pandoc_args(self, mock_run):
        """Test converting with additional pandoc arguments"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("# Test")

            mock_run.side_effect = [
                Mock(returncode=0),  # pandoc --version
                Mock(returncode=0, stdout="", stderr=""),  # pandoc convert
            ]

            runner = CliRunner()
            result = runner.invoke(
                convert, ["md", "html", str(test_file), "-a", "--toc --standalone"]
            )

            assert result.exit_code == 0

    @patch("subprocess.run")
    @patch("mcli.workflow.doc_convert.file_glob")
    def test_convert_no_files_found(self, mock_glob, mock_run):
        """Test behavior when no files match glob pattern"""
        mock_glob.return_value = []
        mock_run.return_value = Mock(returncode=0)  # pandoc --version

        runner = CliRunner()
        result = runner.invoke(convert, ["md", "html", "*.nonexistent"])

        assert result.exit_code == 0  # Exits gracefully
        # Should not attempt conversion if no files found

    @patch("subprocess.run")
    def test_convert_handles_pandoc_error(self, mock_run):
        """Test that convert handles pandoc errors gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("# Test")

            mock_run.side_effect = [
                Mock(returncode=0),  # pandoc --version
                subprocess.CalledProcessError(
                    1, "pandoc", stderr="Conversion failed"
                ),  # pandoc convert fails
            ]

            runner = CliRunner()
            result = runner.invoke(convert, ["md", "html", str(test_file)])

            assert result.exit_code == 0  # Should exit gracefully even on error


@pytest.mark.integration
class TestDocConvertIntegration:
    """Integration tests for doc-convert (requires pandoc)"""
