"""
Tests for the new command extraction logic.
"""

import pytest


class TestCodeExtraction:
    """Test the code extraction logic in new_cmd.py."""

    def extract_code(self, edited_code: str) -> str:
        """
        Simulate the extraction logic from new_cmd.py.

        This mirrors the logic in open_editor_for_command().
        """
        final_code = edited_code

        # Remove the instruction docstring if present (triple-quoted string at the start)
        if final_code.lstrip().startswith('"""'):
            # Find the closing triple quotes
            first_quote = final_code.find('"""')
            if first_quote != -1:
                second_quote = final_code.find('"""', first_quote + 3)
                if second_quote != -1:
                    # Check if this docstring contains instruction markers
                    docstring_content = final_code[first_quote : second_quote + 3]
                    if "Instructions:" in docstring_content or "Example Click command" in docstring_content:
                        # Remove the instruction docstring
                        final_code = final_code[second_quote + 3 :].lstrip("\n")

        # Also remove the "# Your command implementation goes here:" comment and below
        # if the user didn't write anything there (keep user code above it)
        marker = "# Your command implementation goes here:"
        if marker in final_code:
            marker_pos = final_code.find(marker)
            code_before_marker = final_code[:marker_pos].rstrip()
            code_after_marker = final_code[marker_pos + len(marker) :].strip()

            # Check if there's meaningful code after the marker (not just comments)
            after_lines = [
                l for l in code_after_marker.split("\n") if l.strip() and not l.strip().startswith("#")
            ]

            if after_lines:
                # User wrote code after marker, keep everything
                final_code = final_code.strip()
            else:
                # No meaningful code after marker, just use code before it
                final_code = code_before_marker

        return final_code.strip()

    def test_removes_instruction_docstring(self):
        """Test that the instruction docstring is removed."""
        code = '''"""
ollama command for mcli.workflows.

Instructions:
1. Write your Python command logic below
2. Use Click decorators for command definition
"""
import click

@click.command()
def hello():
    print("hello")
'''
        result = self.extract_code(code)
        assert "Instructions:" not in result
        assert "import click" in result
        assert 'print("hello")' in result

    def test_keeps_user_code_before_marker(self):
        """Test that user code written before the marker is preserved."""
        code = '''import click
from mcli.lib.logger.logger import get_logger

logger = get_logger()

@click.group(name="ollama")
def app():
    print("ollama")

# Your command implementation goes here:
# Example:
# @click.command()
# def my_command():
#     pass
'''
        result = self.extract_code(code)
        assert "import click" in result
        assert 'print("ollama")' in result
        assert "def app():" in result
        # The marker and comments after it should be removed
        assert "# Your command implementation goes here:" not in result
        assert "# Example:" not in result

    def test_keeps_all_code_when_user_writes_after_marker(self):
        """Test that all code is kept when user writes meaningful code after marker."""
        code = '''import click

@click.group(name="test")
def app():
    pass

# Your command implementation goes here:

@app.command()
def subcommand():
    print("real code")
'''
        result = self.extract_code(code)
        assert "import click" in result
        assert "def app():" in result
        assert "def subcommand():" in result
        assert 'print("real code")' in result

    def test_preserves_normal_docstrings(self):
        """Test that normal docstrings (without instruction markers) are preserved."""
        code = '''"""
My custom module docstring.
This is not an instruction docstring.
"""
import click

@click.command()
def hello():
    """Command docstring."""
    print("hello")
'''
        result = self.extract_code(code)
        assert "My custom module docstring" in result
        assert "import click" in result

    def test_handles_code_without_markers(self):
        """Test extraction of code that has no instruction markers."""
        code = '''import click

@click.command()
def simple():
    print("simple command")
'''
        result = self.extract_code(code)
        assert result == code.strip()

    def test_empty_code_after_extraction(self):
        """Test that empty results are handled."""
        code = '''"""
Instructions:
Just instructions, no code.
"""
# Your command implementation goes here:
# Only comments here
'''
        result = self.extract_code(code)
        # Should be empty or just whitespace
        assert not result.strip() or result.strip().startswith("#")
