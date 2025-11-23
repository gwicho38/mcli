"""
Notebook executor for running Jupyter notebooks (.ipynb files) as workflows.

This module provides the ability to execute .ipynb files cell by cell,
capturing outputs and handling execution state.
"""

import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcli.lib.logger.logger import get_logger

from .converter import WorkflowConverter
from .schema import CellType, WorkflowNotebook

logger = get_logger()


class NotebookExecutor:
    """Execute Jupyter notebooks cell by cell."""

    def __init__(self, notebook: WorkflowNotebook):
        """
        Initialize the notebook executor.

        Args:
            notebook: WorkflowNotebook instance to execute
        """
        self.notebook = notebook
        self.execution_count = 0
        self.globals_dict: dict[str, Any] = {}
        self.outputs: list[dict[str, Any]] = []

    def execute_python_cell(self, source: str) -> tuple[bool, str, str]:
        """
        Execute a single Python code cell.

        Args:
            source: Python code to execute

        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Execute the code in the shared globals dictionary
            exec(source, self.globals_dict)

            success = True
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()

        except Exception as e:
            success = False
            stdout_text = stdout_capture.getvalue()
            stderr_text = f"{stderr_capture.getvalue()}\n{type(e).__name__}: {str(e)}"

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return success, stdout_text, stderr_text

    def execute_shell_cell(self, source: str) -> tuple[bool, str, str]:
        """
        Execute a single shell/bash code cell.

        Args:
            source: Shell code to execute

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Create a temporary script file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tmp_file:
                tmp_file.write(source)
                tmp_path = tmp_file.name

            # Execute the shell script
            result = subprocess.run(
                ["bash", tmp_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            success = result.returncode == 0
            stdout_text = result.stdout
            stderr_text = result.stderr

            # Clean up temp file
            Path(tmp_path).unlink()

        except subprocess.TimeoutExpired:
            success = False
            stdout_text = ""
            stderr_text = "Execution timed out after 5 minutes"
        except Exception as e:
            success = False
            stdout_text = ""
            stderr_text = f"{type(e).__name__}: {str(e)}"

        return success, stdout_text, stderr_text

    def execute_cell(self, cell_index: int) -> dict[str, Any]:
        """
        Execute a single cell by index.

        Args:
            cell_index: Index of the cell to execute

        Returns:
            Dictionary with execution results
        """
        if cell_index >= len(self.notebook.cells):
            raise IndexError(f"Cell index {cell_index} out of range")

        cell = self.notebook.cells[cell_index]
        self.execution_count += 1

        result = {
            "cell_index": cell_index,
            "cell_type": cell.cell_type.value,
            "execution_count": self.execution_count,
            "success": True,
            "stdout": "",
            "stderr": "",
        }

        # Skip markdown cells
        if cell.cell_type == CellType.MARKDOWN:
            logger.debug(f"Skipping markdown cell {cell_index}")
            return result

        # Execute code cell
        source = cell.source_text
        language = cell.metadata.get("language", self.notebook.metadata.mcli.language.value)

        logger.info(f"Executing cell {cell_index} ({language})")

        if language in ("python", "py"):
            success, stdout, stderr = self.execute_python_cell(source)
        elif language in ("shell", "bash", "sh"):
            success, stdout, stderr = self.execute_shell_cell(source)
        else:
            success = False
            stdout = ""
            stderr = f"Unsupported language: {language}"

        result.update(
            {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
            }
        )

        self.outputs.append(result)
        return result

    def execute_all(self, stop_on_error: bool = False, verbose: bool = False) -> dict[str, Any]:
        """
        Execute all cells in the notebook.

        Args:
            stop_on_error: Stop execution if a cell fails
            verbose: Print output as cells execute

        Returns:
            Dictionary with overall execution results
        """
        total_cells = len(self.notebook.cells)
        code_cells = len(self.notebook.code_cells)

        logger.info(
            f"Executing notebook: {self.notebook.metadata.mcli.name} "
            f"({code_cells} code cells, {total_cells} total cells)"
        )

        results = {
            "notebook_name": self.notebook.metadata.mcli.name,
            "total_cells": total_cells,
            "code_cells": code_cells,
            "executed_cells": 0,
            "successful_cells": 0,
            "failed_cells": 0,
            "cell_results": [],
        }

        for i, cell in enumerate(self.notebook.cells):
            # Skip markdown cells
            if cell.cell_type == CellType.MARKDOWN:
                continue

            try:
                cell_result = self.execute_cell(i)
                results["cell_results"].append(cell_result)
                results["executed_cells"] += 1

                if cell_result["success"]:
                    results["successful_cells"] += 1
                else:
                    results["failed_cells"] += 1

                # Print output if verbose
                if verbose:
                    if cell_result["stdout"]:
                        print(cell_result["stdout"], end="")
                    if cell_result["stderr"]:
                        print(cell_result["stderr"], end="", file=sys.stderr)

                # Stop on error if requested
                if stop_on_error and not cell_result["success"]:
                    logger.error(f"Cell {i} failed, stopping execution")
                    break

            except Exception as e:
                logger.error(f"Error executing cell {i}: {e}")
                results["failed_cells"] += 1

                if stop_on_error:
                    break

        logger.info(
            f"Execution complete: {results['successful_cells']} succeeded, "
            f"{results['failed_cells']} failed"
        )

        return results

    @classmethod
    def from_file(cls, notebook_path: Path) -> "NotebookExecutor":
        """
        Create an executor from a notebook file.

        Args:
            notebook_path: Path to the notebook JSON file

        Returns:
            NotebookExecutor instance
        """
        notebook = WorkflowConverter.load_notebook_json(notebook_path)
        return cls(notebook)

    @classmethod
    def execute_file(
        cls,
        notebook_path: Path,
        stop_on_error: bool = False,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a notebook file.

        Args:
            notebook_path: Path to the notebook JSON file
            stop_on_error: Stop execution if a cell fails
            verbose: Print output as cells execute

        Returns:
            Dictionary with execution results
        """
        executor = cls.from_file(notebook_path)
        return executor.execute_all(stop_on_error=stop_on_error, verbose=verbose)
