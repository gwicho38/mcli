"""
Validation utilities for workflow notebooks.

Provides validation for:
- JSON schema compliance
- Code syntax checking
- Shell script validation
- MCLI API validation
"""

import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

from mcli.lib.logger.logger import get_logger

from .schema import NOTEBOOK_SCHEMA, CellLanguage, CellType, WorkflowNotebook

logger = get_logger()


class NotebookValidator:
    """Validator for workflow notebooks."""

    def __init__(self):
        self.schema_errors: List[str] = []
        self.syntax_errors: List[str] = []

    def validate_schema(self, notebook: WorkflowNotebook) -> bool:
        """
        Validate notebook against JSON schema.

        Args:
            notebook: WorkflowNotebook to validate

        Returns:
            True if valid, False otherwise
        """
        self.schema_errors = []

        try:
            import jsonschema

            data = notebook.to_dict()
            jsonschema.validate(instance=data, schema=NOTEBOOK_SCHEMA)
            return True

        except ImportError:
            # jsonschema not installed, do basic validation
            logger.warning("jsonschema not installed, performing basic validation")
            return self._basic_schema_validation(notebook)

        except Exception as e:
            self.schema_errors.append(str(e))
            return False

    def _basic_schema_validation(self, notebook: WorkflowNotebook) -> bool:
        """Basic schema validation without jsonschema library."""
        valid = True

        # Check required fields
        if not notebook.metadata.mcli.name:
            self.schema_errors.append("Missing required field: metadata.mcli.name")
            valid = False

        if notebook.nbformat != 4:
            self.schema_errors.append(f"Invalid nbformat: {notebook.nbformat} (expected 4)")
            valid = False

        # Validate cells
        for i, cell in enumerate(notebook.cells):
            if not cell.cell_type:
                self.schema_errors.append(f"Cell {i}: Missing cell_type")
                valid = False

            if not cell.source and not isinstance(cell.source, (str, list)):
                self.schema_errors.append(f"Cell {i}: Missing or invalid source")
                valid = False

        return valid

    def validate_syntax(self, notebook: WorkflowNotebook) -> bool:
        """
        Validate code syntax in all code cells.

        Args:
            notebook: WorkflowNotebook to validate

        Returns:
            True if all code is syntactically valid, False otherwise
        """
        self.syntax_errors = []
        all_valid = True

        for i, cell in enumerate(notebook.cells):
            if cell.cell_type != CellType.CODE:
                continue

            language = cell.language
            code = cell.source_text

            if language == CellLanguage.PYTHON:
                if not self._validate_python_syntax(code, i):
                    all_valid = False

            elif language in (
                CellLanguage.SHELL,
                CellLanguage.BASH,
                CellLanguage.ZSH,
            ):  # noqa: SIM102
                if not self._validate_shell_syntax(code, i):
                    all_valid = False

        return all_valid

    def _validate_python_syntax(self, code: str, cell_index: int) -> bool:
        """Validate Python code syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.syntax_errors.append(
                f"Cell {cell_index} (Python): Syntax error at line {e.lineno}: {e.msg}"
            )
            return False
        except Exception as e:
            self.syntax_errors.append(f"Cell {cell_index} (Python): {str(e)}")
            return False

    def _validate_shell_syntax(self, code: str, cell_index: int) -> bool:
        """Validate shell script syntax using bash -n."""
        try:
            # Create temporary file with shell script
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Use bash -n to check syntax without executing
                result = subprocess.run(
                    ["bash", "-n", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    self.syntax_errors.append(f"Cell {cell_index} (Shell): {error_msg}")
                    return False

                return True

            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            self.syntax_errors.append(f"Cell {cell_index} (Shell): Validation timeout")
            return False
        except Exception as e:
            self.syntax_errors.append(f"Cell {cell_index} (Shell): {str(e)}")
            return False

    def validate_mcli_apis(self, notebook: WorkflowNotebook) -> bool:
        """
        Validate MCLI API usage in code cells.

        This checks for:
        - Proper Click decorator usage
        - MCLI library imports
        - Common API patterns

        Args:
            notebook: WorkflowNotebook to validate

        Returns:
            True if API usage is valid, False otherwise
        """
        # TODO: Implement MCLI-specific API validation
        # This could check for:
        # - @click.command() or @click.group() decorators
        # - Proper import statements
        # - Common anti-patterns
        return True

    def get_all_errors(self) -> List[str]:
        """Get all validation errors."""
        return self.schema_errors + self.syntax_errors


class CodeLinter:
    """Linter for workflow notebook code."""

    def __init__(self):
        self.issues: List[Dict[str, any]] = []

    def lint_python(self, code: str) -> List[Dict[str, any]]:
        """
        Lint Python code using available linters.

        Tries to use (in order):
        1. flake8
        2. pylint
        3. Basic AST-based checks

        Returns:
            List of lint issues
        """
        self.issues = []

        # Try flake8
        try:
            import flake8.api.legacy as flake8_api

            style_guide = flake8_api.get_style_guide()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                report = style_guide.check_files([temp_path])
                # Convert flake8 results to our format
                # (this is simplified - actual implementation would parse flake8 output)
                if report.total_errors > 0:
                    self.issues.append(
                        {
                            "severity": "warning",
                            "message": f"Found {report.total_errors} style issues",
                            "line": 0,
                        }
                    )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        except ImportError:
            # flake8 not available, try basic checks
            self._basic_python_lint(code)

        return self.issues

    def _basic_python_lint(self, code: str):
        """Basic Python linting using AST."""
        try:
            tree = ast.parse(code)

            # Check for common issues
            for node in ast.walk(tree):
                # Check for unused imports (simplified)
                if isinstance(node, ast.Import):
                    # TODO: Check if imports are actually used
                    pass

                # Check for bare except
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    self.issues.append(
                        {
                            "severity": "warning",
                            "message": "Bare except clause - consider specifying exception type",
                            "line": node.lineno,
                        }
                    )

        except SyntaxError:
            # Already caught by syntax validation
            pass

    def lint_shell(self, code: str) -> List[Dict[str, any]]:
        """
        Lint shell script using shellcheck if available.

        Returns:
            List of lint issues
        """
        self.issues = []

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Try to use shellcheck
                result = subprocess.run(
                    ["shellcheck", "-", "json", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.stdout:
                    import json

                    issues = json.loads(result.stdout)
                    self.issues = [
                        {
                            "severity": issue.get("level", "warning"),
                            "message": issue.get("message", ""),
                            "line": issue.get("line", 0),
                            "code": issue.get("code", ""),
                        }
                        for issue in issues
                    ]

            finally:
                Path(temp_path).unlink(missing_ok=True)

        except FileNotFoundError:
            # shellcheck not installed
            logger.debug("shellcheck not found, skipping shell linting")
        except Exception as e:
            logger.warning(f"Shell linting failed: {e}")

        return self.issues
