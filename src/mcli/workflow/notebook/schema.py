"""
Notebook schema definitions for MCLI workflow notebooks.

This module defines the structure for Jupyter-compatible workflow notebooks
that can be edited with Monaco editor while maintaining backward compatibility
with existing MCLI workflow JSON format.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class CellType(str, Enum):
    """Types of cells in a workflow notebook."""

    CODE = "code"
    MARKDOWN = "markdown"
    RAW = "raw"


class CellLanguage(str, Enum):
    """Programming languages supported in code cells."""

    PYTHON = "python"
    SHELL = "shell"
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"


@dataclass
class CellOutput:
    """Output from a cell execution."""

    output_type: str  # stream, execute_result, error, display_data
    data: Optional[dict[str, Any]] = None
    text: Optional[list[str]] = None
    name: Optional[str] = None  # stdout, stderr
    execution_count: Optional[int] = None
    ename: Optional[str] = None  # error name
    evalue: Optional[str] = None  # error value
    traceback: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Jupyter output format."""
        result: dict[str, Any] = {"output_type": self.output_type}

        if self.data is not None:
            result["data"] = self.data
        if self.text is not None:
            result["text"] = self.text
        if self.name is not None:
            result["name"] = self.name
        if self.execution_count is not None:
            result["execution_count"] = self.execution_count
        if self.ename is not None:
            result["ename"] = self.ename
        if self.evalue is not None:
            result["evalue"] = self.evalue
        if self.traceback is not None:
            result["traceback"] = self.traceback

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CellOutput":
        """Create from Jupyter output format."""
        return cls(
            output_type=data["output_type"],
            data=data.get("data"),
            text=data.get("text"),
            name=data.get("name"),
            execution_count=data.get("execution_count"),
            ename=data.get("ename"),
            evalue=data.get("evalue"),
            traceback=data.get("traceback"),
        )


@dataclass
class NotebookCell:
    """A cell in a workflow notebook."""

    cell_type: CellType
    source: Union[str, list[str]]
    metadata: dict[str, Any] = field(default_factory=dict)
    outputs: list[CellOutput] = field(default_factory=list)
    execution_count: Optional[int] = None
    id: Optional[str] = None

    def __post_init__(self):
        """Normalize source to list of strings."""
        if isinstance(self.source, str):
            self.source = self.source.splitlines(keepends=True)

    @property
    def source_text(self) -> str:
        """Get source as a single string."""
        if isinstance(self.source, list):
            return "".join(self.source)
        return self.source

    @property
    def language(self) -> Optional[CellLanguage]:
        """Get the language for code cells."""
        if self.cell_type == CellType.CODE:
            lang = self.metadata.get("language", "python")
            try:
                return CellLanguage(lang)
            except ValueError:
                return CellLanguage.PYTHON
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Jupyter notebook cell format."""
        result: dict[str, Any] = {
            "cell_type": self.cell_type.value,
            "metadata": self.metadata,
            "source": self.source if isinstance(self.source, list) else [self.source],
        }

        if self.id:
            result["id"] = self.id

        if self.cell_type == CellType.CODE:
            result["execution_count"] = self.execution_count
            result["outputs"] = [output.to_dict() for output in self.outputs]

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotebookCell":
        """Create from Jupyter notebook cell format."""
        cell_type = CellType(data["cell_type"])
        outputs = []

        if cell_type == CellType.CODE and "outputs" in data:
            outputs = [CellOutput.from_dict(out) for out in data["outputs"]]

        return cls(
            cell_type=cell_type,
            source=data["source"],
            metadata=data.get("metadata", {}),
            outputs=outputs,
            execution_count=data.get("execution_count"),
            id=data.get("id"),
        )


@dataclass
class MCLIMetadata:
    """MCLI-specific metadata for workflow notebooks."""

    name: str
    description: str = ""
    group: Optional[str] = None
    version: str = "1.0"
    language: CellLanguage = CellLanguage.PYTHON
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "language": self.language.value,
        }

        if self.group:
            result["group"] = self.group
        if self.created_at:
            result["created_at"] = self.created_at
        if self.updated_at:
            result["updated_at"] = self.updated_at
        if self.extra:
            result.update(self.extra)

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCLIMetadata":
        """Create from dictionary format."""
        # Extract known fields
        known_fields = {
            "name",
            "description",
            "group",
            "version",
            "language",
            "created_at",
            "updated_at",
        }
        extra = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            group=data.get("group"),
            version=data.get("version", "1.0"),
            language=CellLanguage(data.get("language", "python")),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            extra=extra,
        )


@dataclass
class NotebookMetadata:
    """Metadata for a workflow notebook."""

    mcli: MCLIMetadata
    kernelspec: dict[str, str] = field(
        default_factory=lambda: {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
    )
    language_info: dict[str, Any] = field(
        default_factory=lambda: {
            "name": "python",
            "version": "3.11.0",
            "mimetype": "text/x-python",
            "file_extension": ".py",
        }
    )
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to Jupyter metadata format."""
        result = {
            "mcli": self.mcli.to_dict(),
            "kernelspec": self.kernelspec,
            "language_info": self.language_info,
        }
        result.update(self.extra)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotebookMetadata":
        """Create from Jupyter metadata format."""
        # Extract known fields
        mcli_data = data.get("mcli", {})
        kernelspec = data.get("kernelspec", {})
        language_info = data.get("language_info", {})

        # Backward compatibility: if no mcli metadata, try to extract from root
        if not mcli_data and "name" in data:
            mcli_data = {
                "name": data.get("name"),
                "description": data.get("description", ""),
                "group": data.get("group"),
                "version": data.get("version", "1.0"),
                "language": data.get("language", "python"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }

        extra = {k: v for k, v in data.items() if k not in {"mcli", "kernelspec", "language_info"}}

        return cls(
            mcli=MCLIMetadata.from_dict(mcli_data),
            kernelspec=kernelspec
            or {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            language_info=language_info
            or {
                "name": "python",
                "version": "3.11.0",
                "mimetype": "text/x-python",
                "file_extension": ".py",
            },
            extra=extra,
        )


@dataclass
class WorkflowNotebook:
    """A workflow notebook in Jupyter-compatible format."""

    nbformat: int = 4
    nbformat_minor: int = 5
    metadata: NotebookMetadata = field(
        default_factory=lambda: NotebookMetadata(mcli=MCLIMetadata(name="untitled"))
    )
    cells: list[NotebookCell] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to Jupyter notebook JSON format."""
        return {
            "nbformat": self.nbformat,
            "nbformat_minor": self.nbformat_minor,
            "metadata": self.metadata.to_dict(),
            "cells": [cell.to_dict() for cell in self.cells],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowNotebook":
        """Create from Jupyter notebook JSON format."""
        return cls(
            nbformat=data.get("nbformat", 4),
            nbformat_minor=data.get("nbformat_minor", 5),
            metadata=NotebookMetadata.from_dict(data.get("metadata", {})),
            cells=[NotebookCell.from_dict(cell) for cell in data.get("cells", [])],
        )

    def add_code_cell(
        self,
        source: str,
        language: Optional[CellLanguage] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> NotebookCell:
        """Add a code cell to the notebook."""
        cell_metadata = metadata or {}
        if language:
            cell_metadata["language"] = language.value

        cell = NotebookCell(
            cell_type=CellType.CODE,
            source=source,
            metadata=cell_metadata,
        )
        self.cells.append(cell)
        return cell

    def add_markdown_cell(
        self, source: str, metadata: Optional[dict[str, Any]] = None
    ) -> NotebookCell:
        """Add a markdown cell to the notebook."""
        cell = NotebookCell(
            cell_type=CellType.MARKDOWN,
            source=source,
            metadata=metadata or {},
        )
        self.cells.append(cell)
        return cell

    @property
    def code_cells(self) -> list[NotebookCell]:
        """Get all code cells."""
        return [cell for cell in self.cells if cell.cell_type == CellType.CODE]

    @property
    def markdown_cells(self) -> list[NotebookCell]:
        """Get all markdown cells."""
        return [cell for cell in self.cells if cell.cell_type == CellType.MARKDOWN]


# JSON Schema for validation
NOTEBOOK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "MCLI Workflow Notebook",
    "description": "Jupyter-compatible notebook format for MCLI workflows",
    "type": "object",
    "required": ["nbformat", "nbformat_minor", "metadata", "cells"],
    "properties": {
        "nbformat": {"type": "integer", "const": 4},
        "nbformat_minor": {"type": "integer", "minimum": 0},
        "metadata": {
            "type": "object",
            "required": ["mcli"],
            "properties": {
                "mcli": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "group": {"type": "string"},
                        "version": {"type": "string"},
                        "language": {
                            "type": "string",
                            "enum": ["python", "shell", "bash", "zsh", "fish"],
                        },
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"},
                    },
                },
                "kernelspec": {"type": "object"},
                "language_info": {"type": "object"},
            },
        },
        "cells": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["cell_type", "source", "metadata"],
                "properties": {
                    "cell_type": {"type": "string", "enum": ["code", "markdown", "raw"]},
                    "source": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                    "metadata": {"type": "object"},
                    "execution_count": {"type": ["integer", "null"]},
                    "outputs": {"type": "array", "items": {"type": "object"}},
                    "id": {"type": "string"},
                },
            },
        },
    },
}
