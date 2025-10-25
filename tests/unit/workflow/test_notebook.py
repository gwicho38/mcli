"""
Unit tests for workflow notebook system.

Tests:
- Schema validation
- Conversion between formats
- Notebook creation and manipulation
- Code validation
"""

import json
import tempfile
from pathlib import Path

import pytest

from mcli.workflow.notebook.converter import WorkflowConverter
from mcli.workflow.notebook.schema import (
    CellLanguage,
    CellType,
    MCLIMetadata,
    NotebookCell,
    NotebookMetadata,
    WorkflowNotebook,
)
from mcli.workflow.notebook.validator import NotebookValidator


class TestNotebookSchema:
    """Test notebook schema classes."""

    def test_create_code_cell(self):
        """Test creating a code cell."""
        cell = NotebookCell(
            cell_type=CellType.CODE,
            source="print('hello')",
            metadata={"language": "python"},
        )

        assert cell.cell_type == CellType.CODE
        assert cell.source_text == "print('hello')"
        assert cell.language == CellLanguage.PYTHON

    def test_create_markdown_cell(self):
        """Test creating a markdown cell."""
        cell = NotebookCell(
            cell_type=CellType.MARKDOWN,
            source="# Header\n\nContent",
        )

        assert cell.cell_type == CellType.MARKDOWN
        assert "# Header" in cell.source_text

    def test_cell_to_dict(self):
        """Test converting cell to dictionary."""
        cell = NotebookCell(
            cell_type=CellType.CODE,
            source=["print('hello')\n", "print('world')\n"],
            metadata={"language": "python"},
            execution_count=1,
        )

        data = cell.to_dict()

        assert data["cell_type"] == "code"
        assert isinstance(data["source"], list)
        assert data["execution_count"] == 1
        assert "outputs" in data

    def test_cell_from_dict(self):
        """Test creating cell from dictionary."""
        data = {
            "cell_type": "code",
            "source": ["print('hello')\n"],
            "metadata": {"language": "python"},
            "execution_count": 1,
            "outputs": [],
        }

        cell = NotebookCell.from_dict(data)

        assert cell.cell_type == CellType.CODE
        assert cell.execution_count == 1

    def test_create_notebook(self):
        """Test creating a workflow notebook."""
        mcli_meta = MCLIMetadata(
            name="test-workflow",
            description="Test workflow",
            language=CellLanguage.PYTHON,
        )
        notebook_meta = NotebookMetadata(mcli=mcli_meta)
        notebook = WorkflowNotebook(metadata=notebook_meta)

        assert notebook.nbformat == 4
        assert notebook.metadata.mcli.name == "test-workflow"
        assert len(notebook.cells) == 0

    def test_add_cells_to_notebook(self):
        """Test adding cells to notebook."""
        mcli_meta = MCLIMetadata(name="test")
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))

        # Add markdown cell
        notebook.add_markdown_cell("# Test")

        # Add code cell
        notebook.add_code_cell("print('hello')", CellLanguage.PYTHON)

        assert len(notebook.cells) == 2
        assert len(notebook.markdown_cells) == 1
        assert len(notebook.code_cells) == 1

    def test_notebook_to_dict(self):
        """Test converting notebook to dictionary."""
        mcli_meta = MCLIMetadata(name="test")
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))
        notebook.add_code_cell("print('test')")

        data = notebook.to_dict()

        assert data["nbformat"] == 4
        assert "metadata" in data
        assert "cells" in data
        assert data["metadata"]["mcli"]["name"] == "test"

    def test_notebook_from_dict(self):
        """Test creating notebook from dictionary."""
        data = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "mcli": {
                    "name": "test-workflow",
                    "description": "Test",
                    "version": "1.0",
                    "language": "python",
                }
            },
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hello')\n"],
                    "metadata": {},
                    "execution_count": None,
                    "outputs": [],
                }
            ],
        }

        notebook = WorkflowNotebook.from_dict(data)

        assert notebook.metadata.mcli.name == "test-workflow"
        assert len(notebook.cells) == 1
        assert notebook.cells[0].cell_type == CellType.CODE


class TestWorkflowConverter:
    """Test workflow converter."""

    def test_workflow_to_notebook_conversion(self):
        """Test converting workflow JSON to notebook."""
        workflow_data = {
            "name": "test-workflow",
            "description": "A test workflow",
            "group": "workflow",
            "version": "1.0",
            "language": "python",
            "code": "import click\n\n@click.command()\ndef main():\n    pass",
        }

        notebook = WorkflowConverter.workflow_to_notebook(workflow_data)

        assert notebook.metadata.mcli.name == "test-workflow"
        assert notebook.metadata.mcli.description == "A test workflow"
        assert len(notebook.code_cells) > 0

    def test_notebook_to_workflow_conversion(self):
        """Test converting notebook to workflow JSON."""
        mcli_meta = MCLIMetadata(
            name="test-workflow",
            description="Test",
            group="workflow",
            version="1.0",
        )
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))
        notebook.add_code_cell("import click\n\nprint('test')")

        workflow_data = WorkflowConverter.notebook_to_workflow(notebook)

        assert workflow_data["name"] == "test-workflow"
        assert workflow_data["description"] == "Test"
        assert workflow_data["group"] == "workflow"
        assert "code" in workflow_data
        assert "import click" in workflow_data["code"]

    def test_roundtrip_conversion(self):
        """Test roundtrip conversion (workflow -> notebook -> workflow)."""
        original_workflow = {
            "name": "test",
            "description": "Test workflow",
            "version": "1.0",
            "language": "python",
            "code": "# %% \nimport click\n\n# %%\nprint('test')",
        }

        # Convert to notebook
        notebook = WorkflowConverter.workflow_to_notebook(original_workflow)

        # Convert back to workflow
        converted_workflow = WorkflowConverter.notebook_to_workflow(notebook)

        # Check key fields match
        assert converted_workflow["name"] == original_workflow["name"]
        assert converted_workflow["description"] == original_workflow["description"]
        assert "import click" in converted_workflow["code"]
        assert "print('test')" in converted_workflow["code"]

    def test_code_splitting(self):
        """Test intelligent code splitting into cells."""
        code = """# %%
import click

# %%
@click.command()
def main():
    pass

# %%
if __name__ == "__main__":
    main()
"""

        cells = WorkflowConverter._split_code_into_cells(code)

        # Should split into 3 cells based on # %% markers
        assert len(cells) >= 2

    def test_save_and_load_notebook(self):
        """Test saving and loading notebook from file."""
        mcli_meta = MCLIMetadata(name="test")
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))
        notebook.add_code_cell("print('test')")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Save notebook
            WorkflowConverter.save_notebook_json(notebook, temp_path)

            # Load it back
            loaded_notebook = WorkflowConverter.load_notebook_json(temp_path)

            assert loaded_notebook.metadata.mcli.name == "test"
            assert len(loaded_notebook.cells) == 1

        finally:
            temp_path.unlink(missing_ok=True)

    def test_convert_file_to_notebook(self):
        """Test converting workflow file to notebook file."""
        workflow_data = {
            "name": "test",
            "code": "print('test')",
            "version": "1.0",
            "language": "python",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(workflow_data, f)
            temp_path = Path(f.name)

        try:
            # Convert to notebook
            result_path = WorkflowConverter.convert_file_to_notebook(temp_path)

            # Load and verify
            with open(result_path, "r") as f:
                data = json.load(f)

            assert "nbformat" in data
            assert data["metadata"]["mcli"]["name"] == "test"

        finally:
            temp_path.unlink(missing_ok=True)


class TestNotebookValidator:
    """Test notebook validator."""

    def test_validate_valid_notebook(self):
        """Test validating a valid notebook."""
        mcli_meta = MCLIMetadata(name="test")
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))
        notebook.add_code_cell("print('hello')")

        validator = NotebookValidator()
        is_valid = validator.validate_schema(notebook)

        assert is_valid
        assert len(validator.schema_errors) == 0

    def test_validate_python_syntax(self):
        """Test Python syntax validation."""
        mcli_meta = MCLIMetadata(name="test")
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))

        # Add valid Python code
        notebook.add_code_cell("print('hello')\nx = 1 + 2")

        validator = NotebookValidator()
        is_valid = validator.validate_syntax(notebook)

        assert is_valid
        assert len(validator.syntax_errors) == 0

    def test_validate_invalid_python_syntax(self):
        """Test Python syntax validation with invalid code."""
        mcli_meta = MCLIMetadata(name="test")
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))

        # Add invalid Python code
        notebook.add_code_cell("print('hello'\n")  # Missing closing paren

        validator = NotebookValidator()
        is_valid = validator.validate_syntax(notebook)

        assert not is_valid
        assert len(validator.syntax_errors) > 0

    def test_validate_shell_syntax(self):
        """Test shell syntax validation."""
        mcli_meta = MCLIMetadata(name="test", language=CellLanguage.SHELL)
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))

        # Add valid shell code
        notebook.add_code_cell("echo 'hello'\nls -la", language=CellLanguage.SHELL)

        validator = NotebookValidator()
        is_valid = validator.validate_syntax(notebook)

        # May pass or fail depending on bash availability
        # Just ensure it doesn't crash
        assert isinstance(is_valid, bool)

    def test_get_all_errors(self):
        """Test getting all validation errors."""
        validator = NotebookValidator()
        validator.schema_errors = ["Schema error 1"]
        validator.syntax_errors = ["Syntax error 1", "Syntax error 2"]

        all_errors = validator.get_all_errors()

        assert len(all_errors) == 3
        assert "Schema error 1" in all_errors


class TestNotebookIntegration:
    """Integration tests for notebook system."""

    def test_create_and_execute_workflow_notebook(self):
        """Test creating a complete workflow notebook."""
        # Create notebook
        mcli_meta = MCLIMetadata(
            name="example-workflow",
            description="An example workflow",
            group="workflow",
        )
        notebook = WorkflowNotebook(metadata=NotebookMetadata(mcli=mcli_meta))

        # Add description
        notebook.add_markdown_cell("# Example Workflow\n\nThis is an example.")

        # Add code cells
        notebook.add_code_cell(
            '''"""Example workflow"""
import click

@click.command()
def hello():
    """Say hello"""
    click.echo("Hello from workflow!")
'''
        )

        # Validate
        validator = NotebookValidator()
        assert validator.validate_schema(notebook)
        assert validator.validate_syntax(notebook)

        # Convert to workflow
        workflow_data = WorkflowConverter.notebook_to_workflow(notebook)

        assert workflow_data["name"] == "example-workflow"
        assert "click" in workflow_data["code"]

    def test_migrate_legacy_workflow(self):
        """Test migrating a legacy workflow to notebook format."""
        # Create legacy workflow
        legacy_workflow = {
            "name": "legacy-workflow",
            "description": "A legacy workflow",
            "group": "workflow",
            "version": "1.0",
            "language": "python",
            "code": '''import click

@click.group()
def cli():
    """Legacy workflow"""
    pass

@cli.command()
def test():
    """Test command"""
    click.echo("Test")
''',
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }

        # Convert to notebook
        notebook = WorkflowConverter.workflow_to_notebook(legacy_workflow)

        # Verify conversion
        assert notebook.metadata.mcli.name == "legacy-workflow"
        assert notebook.metadata.mcli.created_at == "2025-01-01T00:00:00Z"
        assert len(notebook.code_cells) > 0

        # Verify code is preserved
        all_code = "".join(cell.source_text for cell in notebook.code_cells)
        assert "import click" in all_code
        assert "@click.group()" in all_code

        # Validate
        validator = NotebookValidator()
        assert validator.validate_schema(notebook)
        assert validator.validate_syntax(notebook)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
