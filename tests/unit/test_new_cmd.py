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
        # The docstring may contain nested """ (in examples), so we need to find the
        # closing """ that is on its own line (the actual end of the docstring)
        if final_code.lstrip().startswith('"""'):
            lines = final_code.split("\n")
            docstring_end_line = None

            for i, line in enumerate(lines):
                if i == 0:
                    continue
                # Look for a line that is just """ (possibly with whitespace)
                if line.strip() == '"""':
                    docstring_end_line = i
                    break

            if docstring_end_line is not None:
                # Check if the docstring contains instruction markers
                docstring_lines = lines[: docstring_end_line + 1]
                docstring_content = "\n".join(docstring_lines)
                if "Instructions:" in docstring_content or "Example Click command" in docstring_content:
                    # Remove the instruction docstring
                    final_code = "\n".join(lines[docstring_end_line + 1 :]).lstrip("\n")

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

    def test_preserves_user_code_with_function_docstrings(self):
        """Test that user code with function docstrings is preserved."""
        code = '''"""
ollama command for mcli.workflows.

Instructions:
1. Write your Python command logic below

Example Click command structure:
@click.command()
def my_command(name):
    # Example comment
    pass
"""
import click

@click.group(name="ollama")
def app():
    """Description for ollama command group."""
    print("ollama")

@app.command("hello")
def hello():
    """Example subcommand."""
    print("hello")
'''
        result = self.extract_code(code)
        assert "import click" in result
        assert 'print("ollama")' in result
        assert "def app():" in result
        assert '"""Description for ollama command group."""' in result
        assert '"""Example subcommand."""' in result
        # The instruction docstring should be removed
        assert "Instructions:" not in result

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

    def test_handles_code_without_docstrings(self):
        """Test extraction of code that has no docstrings."""
        code = '''import click

@click.command()
def simple():
    print("simple command")
'''
        result = self.extract_code(code)
        assert result == code.strip()

    def test_handles_nested_docstrings_in_instruction(self):
        """Test that nested docstrings in the instruction docstring don't break extraction."""
        code = '''"""
Command description.

Instructions:
Example:
@click.command()
def example():
    # This is a comment, not a docstring
    pass
"""
import click

@click.group(name="test")
def app():
    """Real function docstring."""
    print("real code")
'''
        result = self.extract_code(code)
        assert "import click" in result
        assert 'print("real code")' in result
        assert '"""Real function docstring."""' in result
        assert "Instructions:" not in result

    def test_empty_code_after_extraction(self):
        """Test that empty results are handled."""
        code = '''"""
Instructions:
Just instructions, no code.
"""
'''
        result = self.extract_code(code)
        # Should be empty
        assert not result.strip()
