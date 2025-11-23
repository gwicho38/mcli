"""
Tests for notebook executor functionality.
"""

import json
import tempfile
from pathlib import Path

import pytest

from mcli.workflow.notebook.converter import WorkflowConverter
from mcli.workflow.notebook.executor import NotebookExecutor
from mcli.workflow.notebook.schema import (
    CellLanguage,
    MCLIMetadata,
    NotebookMetadata,
    WorkflowNotebook,
)


@pytest.fixture
def simple_python_notebook():
    """Create a simple Python notebook for testing."""
    mcli_meta = MCLIMetadata(
        name="test-notebook",
        description="Test notebook",
        language=CellLanguage.PYTHON,
    )
    notebook_meta = NotebookMetadata(mcli=mcli_meta)
    notebook = WorkflowNotebook(metadata=notebook_meta)

    # Add a simple print cell
    notebook.add_code_cell('print("Hello, World!")', CellLanguage.PYTHON)

    # Add a variable assignment cell
    notebook.add_code_cell("x = 42\ny = 10", CellLanguage.PYTHON)

    # Add a calculation cell that uses previous variables
    notebook.add_code_cell("result = x + y\nprint(f'Result: {result}')", CellLanguage.PYTHON)

    return notebook


@pytest.fixture
def shell_notebook():
    """Create a simple shell notebook for testing."""
    mcli_meta = MCLIMetadata(
        name="test-shell-notebook",
        description="Test shell notebook",
        language=CellLanguage.SHELL,
    )
    notebook_meta = NotebookMetadata(mcli=mcli_meta)
    notebook = WorkflowNotebook(metadata=notebook_meta)

    # Add a simple echo cell
    notebook.add_code_cell('echo "Hello from shell!"', CellLanguage.SHELL)

    return notebook


@pytest.fixture
def failing_notebook():
    """Create a notebook with a failing cell."""
    mcli_meta = MCLIMetadata(
        name="failing-notebook",
        description="Notebook with errors",
        language=CellLanguage.PYTHON,
    )
    notebook_meta = NotebookMetadata(mcli=mcli_meta)
    notebook = WorkflowNotebook(metadata=notebook_meta)

    # Add a good cell
    notebook.add_code_cell('print("This works")', CellLanguage.PYTHON)

    # Add a failing cell
    notebook.add_code_cell("raise ValueError('Intentional error')", CellLanguage.PYTHON)

    # Add another cell after the error
    notebook.add_code_cell(
        'print("This should not run if stop_on_error=True")', CellLanguage.PYTHON
    )

    return notebook


def test_executor_initialization(simple_python_notebook):
    """Test that executor can be initialized with a notebook."""
    executor = NotebookExecutor(simple_python_notebook)
    assert executor.notebook == simple_python_notebook
    assert executor.execution_count == 0
    assert len(executor.globals_dict) == 0


def test_execute_simple_python_cell(simple_python_notebook):
    """Test executing a simple Python cell."""
    executor = NotebookExecutor(simple_python_notebook)

    # Execute first cell (print statement)
    result = executor.execute_cell(0)

    assert result["success"] is True
    assert result["cell_index"] == 0
    assert result["execution_count"] == 1
    assert "Hello, World!" in result["stdout"]


def test_execute_with_state_preservation(simple_python_notebook):
    """Test that execution state is preserved across cells."""
    executor = NotebookExecutor(simple_python_notebook)

    # Execute variable assignment cell
    result1 = executor.execute_cell(1)
    assert result1["success"] is True

    # Verify variables are in globals
    assert "x" in executor.globals_dict
    assert executor.globals_dict["x"] == 42
    assert executor.globals_dict["y"] == 10

    # Execute calculation cell that uses previous variables
    result2 = executor.execute_cell(2)
    assert result2["success"] is True
    assert "Result: 52" in result2["stdout"]


def test_execute_all_cells(simple_python_notebook):
    """Test executing all cells in a notebook."""
    executor = NotebookExecutor(simple_python_notebook)

    results = executor.execute_all(verbose=False)

    assert results["notebook_name"] == "test-notebook"
    assert results["code_cells"] == 3
    assert results["executed_cells"] == 3
    assert results["successful_cells"] == 3
    assert results["failed_cells"] == 0


def test_execute_shell_cell(shell_notebook):
    """Test executing shell commands."""
    executor = NotebookExecutor(shell_notebook)

    result = executor.execute_cell(0)

    assert result["success"] is True
    assert "Hello from shell!" in result["stdout"]


def test_failing_cell_handling(failing_notebook):
    """Test handling of cells that throw errors."""
    executor = NotebookExecutor(failing_notebook)

    # Execute first (good) cell
    result1 = executor.execute_cell(0)
    assert result1["success"] is True

    # Execute failing cell
    result2 = executor.execute_cell(1)
    assert result2["success"] is False
    assert "ValueError" in result2["stderr"]
    assert "Intentional error" in result2["stderr"]


def test_stop_on_error(failing_notebook):
    """Test stop_on_error flag."""
    executor = NotebookExecutor(failing_notebook)

    results = executor.execute_all(stop_on_error=True, verbose=False)

    # Should only execute 2 cells (good cell + failing cell, then stop)
    assert results["executed_cells"] == 2
    assert results["successful_cells"] == 1
    assert results["failed_cells"] == 1


def test_continue_on_error(failing_notebook):
    """Test continuing execution after errors."""
    executor = NotebookExecutor(failing_notebook)

    results = executor.execute_all(stop_on_error=False, verbose=False)

    # Should execute all 3 cells
    assert results["executed_cells"] == 3
    assert results["successful_cells"] == 2  # First and third cells succeed
    assert results["failed_cells"] == 1  # Second cell fails


def test_execute_from_file(simple_python_notebook, tmp_path):
    """Test executing a notebook from a file."""
    # Save notebook to temp file
    notebook_path = tmp_path / "test_notebook.json"
    WorkflowConverter.save_notebook_json(simple_python_notebook, notebook_path)

    # Execute from file
    results = NotebookExecutor.execute_file(notebook_path, verbose=False)

    assert results["notebook_name"] == "test-notebook"
    assert results["successful_cells"] == 3
    assert results["failed_cells"] == 0


def test_markdown_cells_are_skipped(simple_python_notebook):
    """Test that markdown cells are skipped during execution."""
    # Add a markdown cell
    simple_python_notebook.add_markdown_cell("# This is a markdown cell")

    executor = NotebookExecutor(simple_python_notebook)
    results = executor.execute_all(verbose=False)

    # Should still execute only the 3 code cells
    assert results["executed_cells"] == 3
    assert results["code_cells"] == 3


def test_unsupported_language():
    """Test handling of unsupported languages."""
    mcli_meta = MCLIMetadata(
        name="unsupported",
        description="Unsupported language",
        language=CellLanguage.PYTHON,  # Metadata says Python
    )
    notebook_meta = NotebookMetadata(mcli=mcli_meta)
    notebook = WorkflowNotebook(metadata=notebook_meta)

    # Add a cell with unsupported language in metadata
    from mcli.workflow.notebook.schema import CellType, NotebookCell

    cell = NotebookCell(
        cell_type=CellType.CODE,
        source="some code",
        metadata={"language": "unsupported"},
    )
    notebook.cells.append(cell)

    executor = NotebookExecutor(notebook)
    result = executor.execute_cell(0)

    assert result["success"] is False
    assert "Unsupported language" in result["stderr"]
