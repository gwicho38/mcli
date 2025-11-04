"""
Converter for transforming between MCLI workflow JSON and notebook format.

This module provides bidirectional conversion between:
1. Legacy MCLI workflow JSON format (single code field)
2. New Jupyter-compatible notebook format (multi-cell)
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcli.lib.logger.logger import get_logger

from .schema import (
    CellLanguage,
    CellType,
    MCLIMetadata,
    NotebookCell,
    NotebookMetadata,
    WorkflowNotebook,
)

logger = get_logger()


class WorkflowConverter:
    """Convert between workflow JSON and notebook formats."""

    @staticmethod
    def _split_code_into_cells(code: str, language: str = "python") -> List[NotebookCell]:
        """
        Split a monolithic code block into logical cells.

        This attempts to intelligently split code based on:
        - Comment markers like # %% or # CELL
        - Function/class definitions
        - Major logical blocks
        """
        cells = []

        # First, try to split by cell markers (VSCode/Jupyter style)
        cell_marker_pattern = r"^#\s*%%|^#\s*<cell>|^#\s*CELL"
        segments = re.split(cell_marker_pattern, code, flags=re.MULTILINE)

        if len(segments) > 1:
            # Found cell markers
            for _i, segment in enumerate(segments):
                if segment.strip():
                    cells.append(
                        NotebookCell(
                            cell_type=CellType.CODE,
                            source=segment.strip() + "\n",
                            metadata={"language": language},
                        )
                    )
        else:
            # No cell markers, try to split intelligently by blank lines or major blocks
            lines = code.split("\n")
            current_cell_lines = []

            for i, line in enumerate(lines):
                current_cell_lines.append(line)

                # Split on double blank lines or before major definitions
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                is_double_blank = line.strip() == "" and next_line.strip() == ""
                is_major_def = (
                    next_line.strip().startswith("def ")
                    or next_line.strip().startswith("class ")
                    or next_line.strip().startswith("@")
                )

                if (is_double_blank or is_major_def) and len(current_cell_lines) > 3:
                    cell_code = "\n".join(current_cell_lines).strip()
                    if cell_code:
                        cells.append(
                            NotebookCell(
                                cell_type=CellType.CODE,
                                source=cell_code + "\n",
                                metadata={"language": language},
                            )
                        )
                    current_cell_lines = []

            # Add remaining lines as final cell
            if current_cell_lines:
                cell_code = "\n".join(current_cell_lines).strip()
                if cell_code:
                    cells.append(
                        NotebookCell(
                            cell_type=CellType.CODE,
                            source=cell_code + "\n",
                            metadata={"language": language},
                        )
                    )

        # If no cells were created, add the entire code as one cell
        if not cells and code.strip():
            cells.append(
                NotebookCell(
                    cell_type=CellType.CODE,
                    source=code,
                    metadata={"language": language},
                )
            )

        return cells

    @classmethod
    def workflow_to_notebook(
        cls, workflow_data: Dict[str, Any], add_description: bool = True
    ) -> WorkflowNotebook:
        """
        Convert legacy workflow JSON to notebook format.

        Args:
            workflow_data: Legacy workflow JSON data
            add_description: Add description as markdown cell

        Returns:
            WorkflowNotebook instance
        """
        # Extract metadata
        name = workflow_data.get("name", "untitled")
        description = workflow_data.get("description", "")
        group = workflow_data.get("group")
        version = workflow_data.get("version", "1.0")
        language = workflow_data.get("language", "python")
        created_at = workflow_data.get("created_at")
        updated_at = workflow_data.get("updated_at")
        extra_metadata = workflow_data.get("metadata", {})

        # Create MCLI metadata
        mcli_metadata = MCLIMetadata(
            name=name,
            description=description,
            group=group,
            version=version,
            language=CellLanguage(language),
            created_at=created_at,
            updated_at=updated_at,
            extra=extra_metadata,
        )

        # Create notebook metadata
        notebook_metadata = NotebookMetadata(mcli=mcli_metadata)

        # Create notebook
        notebook = WorkflowNotebook(metadata=notebook_metadata)

        # Add description as markdown cell if present
        if add_description and description:
            notebook.add_markdown_cell(f"# {name}\n\n{description}")

        # Extract and split code into cells
        code = workflow_data.get("code", "")
        if code:
            cells = cls._split_code_into_cells(code, language)
            notebook.cells.extend(cells)

        return notebook

    @staticmethod
    def notebook_to_workflow(notebook: WorkflowNotebook) -> Dict[str, Any]:
        """
        Convert notebook format to legacy workflow JSON.

        Args:
            notebook: WorkflowNotebook instance

        Returns:
            Legacy workflow JSON data
        """
        mcli_meta = notebook.metadata.mcli

        # Combine all code cells into single code field
        code_parts = []
        for cell in notebook.cells:
            if cell.cell_type == CellType.CODE:
                code_parts.append(cell.source_text)

        # Join with cell markers for potential round-trip conversion
        combined_code = "\n# %%\n".join(code_parts)

        # Build workflow data
        workflow_data = {
            "name": mcli_meta.name,
            "description": mcli_meta.description,
            "version": mcli_meta.version,
            "language": mcli_meta.language.value,
            "code": combined_code,
        }

        # Add optional fields
        if mcli_meta.group:
            workflow_data["group"] = mcli_meta.group
        if mcli_meta.created_at:
            workflow_data["created_at"] = mcli_meta.created_at
        if mcli_meta.updated_at:
            workflow_data["updated_at"] = mcli_meta.updated_at
        else:
            workflow_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        if mcli_meta.extra:
            workflow_data["metadata"] = mcli_meta.extra

        return workflow_data

    @classmethod
    def load_workflow_json(cls, path: Union[str, Path]) -> Dict[str, Any]:
        """Load workflow JSON from file."""
        path = Path(path)
        with open(path, "r") as f:
            return json.load(f)

    @classmethod
    def save_workflow_json(cls, data: Dict[str, Any], path: Union[str, Path]) -> None:
        """Save workflow JSON to file."""
        path = Path(path)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_notebook_json(cls, path: Union[str, Path]) -> WorkflowNotebook:
        """Load notebook from JSON file."""
        path = Path(path)
        with open(path, "r") as f:
            data = json.load(f)

        # Check if it's a notebook or legacy workflow format
        if "nbformat" in data:
            # It's already a notebook
            return WorkflowNotebook.from_dict(data)
        else:
            # It's a legacy workflow, convert it
            logger.info(f"Converting legacy workflow to notebook format: {path}")
            return cls.workflow_to_notebook(data)

    @classmethod
    def save_notebook_json(cls, notebook: WorkflowNotebook, path: Union[str, Path]) -> None:
        """Save notebook to JSON file."""
        path = Path(path)
        data = notebook.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def convert_file_to_notebook(
        cls, input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Convert a workflow JSON file to notebook format.

        Args:
            input_path: Path to legacy workflow JSON
            output_path: Optional output path (defaults to same path)

        Returns:
            Path to the converted notebook file
        """
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path

        # Load legacy workflow
        workflow_data = cls.load_workflow_json(input_path)

        # Convert to notebook
        notebook = cls.workflow_to_notebook(workflow_data)

        # Save notebook
        cls.save_notebook_json(notebook, output_path)

        logger.info(f"Converted {input_path} to notebook format at {output_path}")
        return output_path

    @classmethod
    def convert_file_to_workflow(
        cls, input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Convert a notebook file to legacy workflow JSON format.

        Args:
            input_path: Path to notebook JSON
            output_path: Optional output path (defaults to same path)

        Returns:
            Path to the converted workflow file
        """
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path

        # Load notebook
        notebook = cls.load_notebook_json(input_path)

        # Convert to workflow
        workflow_data = cls.notebook_to_workflow(notebook)

        # Save workflow
        cls.save_workflow_json(workflow_data, output_path)

        logger.info(f"Converted {input_path} to workflow format at {output_path}")
        return output_path

    @classmethod
    def migrate_directory(
        cls, directory: Union[str, Path], backup: bool = True, in_place: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate all workflow JSON files in a directory to notebook format.

        Args:
            directory: Directory containing workflow JSON files
            backup: Create backup files before conversion
            in_place: Convert files in place (vs creating new files)

        Returns:
            Dictionary with migration results
        """
        directory = Path(directory)
        results = {
            "total": 0,
            "converted": 0,
            "failed": 0,
            "skipped": 0,
            "files": [],
        }

        for json_file in directory.glob("*.json"):
            # Skip lockfile and already-converted notebooks
            if json_file.name == "commands.lock.json":
                continue

            try:
                # Load and check if already a notebook
                with open(json_file, "r") as f:
                    data = json.load(f)

                results["total"] += 1

                if "nbformat" in data:
                    # Already a notebook
                    results["skipped"] += 1
                    logger.debug(f"Skipping {json_file.name} - already a notebook")
                    continue

                # Backup if requested
                if backup:
                    backup_path = json_file.with_suffix(".json.bak")
                    cls.save_workflow_json(data, backup_path)
                    logger.debug(f"Created backup: {backup_path}")

                # Convert to notebook
                if in_place:
                    output_path = json_file
                else:
                    output_path = json_file.with_stem(f"{json_file.stem}.notebook")

                cls.convert_file_to_notebook(json_file, output_path)

                results["converted"] += 1
                results["files"].append(str(json_file))

            except Exception as e:
                logger.error(f"Failed to convert {json_file}: {e}")
                results["failed"] += 1

        logger.info(
            f"Migration complete: {results['converted']} converted, "
            f"{results['skipped']} skipped, {results['failed']} failed"
        )
        return results
