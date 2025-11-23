"""
CLI commands for MCLI workflow notebook management.

Provides commands for:
- Converting between workflow and notebook formats
- Migrating existing workflows
- Validating notebooks
- Launching the visual editor
"""

import json
from pathlib import Path
from typing import Optional

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.ui.styling import error, info, success, warning

from .converter import WorkflowConverter
from .schema import WorkflowNotebook
from .validator import NotebookValidator

logger = get_logger()


@click.group(name="notebook")
def notebook():
    """Workflow notebook management commands."""


@notebook.command(name="convert")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--to",
    "format_type",
    type=click.Choice(["notebook", "workflow"]),
    required=True,
    help="Target format",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output file path (defaults to input file)",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before conversion",
)
def convert(input_file: str, format_type: str, output: Optional[str], backup: bool):
    """
    Convert between workflow and notebook formats.

    Examples:

        # Convert workflow to notebook
        mcli workflow notebook convert workflow.json --to notebook

        # Convert notebook to workflow
        mcli workflow notebook convert notebook.json --to workflow -o output.json
    """
    input_path = Path(input_file)
    output_path = Path(output) if output else input_path

    # Create backup if requested
    if backup and output_path == input_path:
        backup_path = input_path.with_suffix(".json.bak")
        import shutil

        shutil.copy2(input_path, backup_path)
        info(f"Created backup: {backup_path}")

    try:
        if format_type == "notebook":
            # Convert to notebook format
            result_path = WorkflowConverter.convert_file_to_notebook(input_path, output_path)
            success(f"Converted to notebook format: {result_path}")
        else:
            # Convert to workflow format
            result_path = WorkflowConverter.convert_file_to_workflow(input_path, output_path)
            success(f"Converted to workflow format: {result_path}")

    except Exception as e:
        error(f"Conversion failed: {e}")
        raise click.Abort()


@notebook.command(name="migrate")
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Directory to migrate (defaults to ~/.mcli/commands)",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup files before migration",
)
@click.option(
    "--in-place/--separate",
    default=True,
    help="Convert in place or create separate files",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be migrated without making changes",
)
def migrate(directory: Optional[str], backup: bool, in_place: bool, dry_run: bool):
    """
    Migrate all workflow files in a directory to notebook format.

    Examples:

        # Migrate all workflows in default directory
        mcli workflow notebook migrate

        # Dry run to see what would be migrated
        mcli workflow notebook migrate --dry-run

        # Migrate specific directory without backup
        mcli workflow notebook migrate -d /path/to/workflows --no-backup
    """
    target_dir = Path(directory) if directory else get_custom_commands_dir()

    info(f"Migrating workflows in: {target_dir}")

    if dry_run:
        warning("DRY RUN MODE - No files will be modified")
        # Count files that would be migrated
        count = 0
        for json_file in target_dir.glob("*.json"):
            if json_file.name == "commands.lock.json":
                continue
            try:
                with open(json_file) as f:
                    data = json.load(f)
                if "nbformat" not in data:
                    count += 1
                    info(f"  Would convert: {json_file.name}")
            except Exception as e:
                warning(f"  Would skip {json_file.name}: {e}")

        info(f"\nTotal files to migrate: {count}")
        return

    try:
        results = WorkflowConverter.migrate_directory(target_dir, backup=backup, in_place=in_place)

        success("\nMigration complete:")
        info(f"  Total files: {results['total']}")
        success(f"  Converted: {results['converted']}")
        warning(f"  Skipped: {results['skipped']}")
        if results["failed"] > 0:
            error(f"  Failed: {results['failed']}")

        if results["files"]:
            info("\nConverted files:")
            for file_path in results["files"]:
                info(f"  - {Path(file_path).name}")

    except Exception as e:
        error(f"Migration failed: {e}")
        raise click.Abort()


@notebook.command(name="validate")
@click.argument("notebook_file", type=click.Path(exists=True))
@click.option(
    "--schema",
    is_flag=True,
    help="Validate against JSON schema",
)
@click.option(
    "--syntax",
    is_flag=True,
    help="Validate code syntax",
)
@click.option(
    "--all",
    "validate_all",
    is_flag=True,
    help="Run all validations",
)
def validate(notebook_file: str, schema: bool, syntax: bool, validate_all: bool):
    """
    Validate a workflow notebook.

    Examples:

        # Validate schema only
        mcli workflow notebook validate notebook.json --schema

        # Validate code syntax
        mcli workflow notebook validate notebook.json --syntax

        # Run all validations
        mcli workflow notebook validate notebook.json --all
    """
    if validate_all:  # noqa: SIM114
        schema = syntax = True
    elif not (schema or syntax):
        # Default to all if no specific validation requested
        schema = syntax = True

    notebook_path = Path(notebook_file)
    validator = NotebookValidator()

    try:
        # Load notebook
        notebook = WorkflowConverter.load_notebook_json(notebook_path)

        all_valid = True

        if schema:
            info("Validating JSON schema...")
            schema_valid = validator.validate_schema(notebook)
            if schema_valid:
                success("  Schema validation passed")
            else:
                error("  Schema validation failed")
                for err in validator.schema_errors:
                    error(f"    - {err}")
                all_valid = False

        if syntax:
            info("Validating code syntax...")
            syntax_valid = validator.validate_syntax(notebook)
            if syntax_valid:
                success("  Syntax validation passed")
            else:
                error("  Syntax validation failed")
                for err in validator.syntax_errors:
                    error(f"    - {err}")
                all_valid = False

        if all_valid:
            success(f"\nNotebook is valid: {notebook_path}")
        else:
            error(f"\nNotebook has validation errors: {notebook_path}")
            raise click.Abort()

    except Exception as e:
        error(f"Validation failed: {e}")
        raise click.Abort()


@notebook.command(name="info")
@click.argument("notebook_file", type=click.Path(exists=True))
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def notebook_info(notebook_file: str, output_json: bool):
    """
    Display information about a workflow notebook.

    Examples:

        # Show notebook info
        mcli workflow notebook info notebook.json

        # Output as JSON
        mcli workflow notebook info notebook.json --json
    """
    notebook_path = Path(notebook_file)

    try:
        notebook = WorkflowConverter.load_notebook_json(notebook_path)

        if output_json:
            # Output as JSON
            info_data = {
                "name": notebook.metadata.mcli.name,
                "description": notebook.metadata.mcli.description,
                "group": notebook.metadata.mcli.group,
                "version": notebook.metadata.mcli.version,
                "language": notebook.metadata.mcli.language.value,
                "total_cells": len(notebook.cells),
                "code_cells": len(notebook.code_cells),
                "markdown_cells": len(notebook.markdown_cells),
                "created_at": notebook.metadata.mcli.created_at,
                "updated_at": notebook.metadata.mcli.updated_at,
            }
            click.echo(json.dumps(info_data, indent=2))
        else:
            # Pretty print
            info(f"Notebook: {notebook.metadata.mcli.name}")
            if notebook.metadata.mcli.description:
                info(f"Description: {notebook.metadata.mcli.description}")
            if notebook.metadata.mcli.group:
                info(f"Group: {notebook.metadata.mcli.group}")
            info(f"Version: {notebook.metadata.mcli.version}")
            info(f"Language: {notebook.metadata.mcli.language.value}")
            info("\nCells:")
            info(f"  Total: {len(notebook.cells)}")
            info(f"  Code: {len(notebook.code_cells)}")
            info(f"  Markdown: {len(notebook.markdown_cells)}")
            if notebook.metadata.mcli.created_at:
                info(f"\nCreated: {notebook.metadata.mcli.created_at}")
            if notebook.metadata.mcli.updated_at:
                info(f"Updated: {notebook.metadata.mcli.updated_at}")

    except Exception as e:
        error(f"Failed to read notebook: {e}")
        raise click.Abort()


@notebook.command(name="create")
@click.argument("name")
@click.option(
    "-d",
    "--description",
    default="",
    help="Notebook description",
)
@click.option(
    "-g",
    "--group",
    default=None,
    help="Command group",
)
@click.option(
    "-l",
    "--language",
    type=click.Choice(["python", "shell", "bash"]),
    default="python",
    help="Default language",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output file path",
)
def create(name: str, description: str, group: Optional[str], language: str, output: Optional[str]):
    """
    Create a new workflow notebook.

    Examples:

        # Create a new Python workflow notebook
        mcli workflow notebook create my-workflow

        # Create with description and group
        mcli workflow notebook create my-workflow -d "My workflow" -g workflow
    """
    from .schema import CellLanguage, MCLIMetadata, NotebookMetadata

    # Create notebook
    mcli_meta = MCLIMetadata(
        name=name,
        description=description,
        group=group,
        language=CellLanguage(language),
    )
    notebook_meta = NotebookMetadata(mcli=mcli_meta)
    notebook = WorkflowNotebook(metadata=notebook_meta)

    # Add welcome markdown cell
    notebook.add_markdown_cell(
        f"# {name}\n\n{description}\n\n"
        "This is a workflow notebook. Add code cells below to define your workflow."
    )

    # Add example code cell
    if language == "python":
        example_code = '''"""
Example workflow cell.
"""
import click

@click.command()
def hello():
    """Example command"""
    click.echo("Hello from workflow!")

if __name__ == "__main__":
    hello()
'''
    else:
        example_code = """#!/usr/bin/env bash
# Example workflow shell script

echo "Hello from workflow!"
"""

    notebook.add_code_cell(example_code, CellLanguage(language))

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        commands_dir = get_custom_commands_dir()
        output_path = commands_dir / f"{name}.json"

    # Save notebook
    WorkflowConverter.save_notebook_json(notebook, output_path)
    success(f"Created notebook: {output_path}")


@notebook.command(name="run")
@click.argument("notebook_file", type=click.Path(exists=True))
@click.option(
    "--stop-on-error",
    is_flag=True,
    help="Stop execution if a cell fails",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print output as cells execute",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def run(notebook_file: str, stop_on_error: bool, verbose: bool, output_json: bool):
    """
    Execute a notebook file cell by cell.

    This runs all code cells in the notebook in order, capturing outputs
    and maintaining execution state across cells.

    Examples:

        # Run a notebook
        mcli workflow notebook run my-workflow.json

        # Run with verbose output
        mcli workflow notebook run my-workflow.json -v

        # Stop on first error
        mcli workflow notebook run my-workflow.json --stop-on-error

        # Get JSON output
        mcli workflow notebook run my-workflow.json --json
    """
    from .executor import NotebookExecutor

    notebook_path = Path(notebook_file)

    try:
        # Execute the notebook
        results = NotebookExecutor.execute_file(
            notebook_path,
            stop_on_error=stop_on_error,
            verbose=verbose,
        )

        if output_json:
            # Output as JSON
            click.echo(json.dumps(results, indent=2))
        else:
            # Pretty print results
            if results["failed_cells"] == 0:
                success(f"\nNotebook executed successfully: {results['notebook_name']}")
            else:
                warning(f"\nNotebook completed with errors: {results['notebook_name']}")

            info(f"Total cells: {results['total_cells']}")
            info(f"Code cells: {results['code_cells']}")
            info(f"Executed: {results['executed_cells']}")
            success(f"Successful: {results['successful_cells']}")

            if results["failed_cells"] > 0:
                error(f"Failed: {results['failed_cells']}")

                # Show failed cell details
                for cell_result in results["cell_results"]:
                    if not cell_result["success"]:
                        error(f"\nCell {cell_result['cell_index']} failed:")
                        if cell_result["stderr"]:
                            error(cell_result["stderr"])

    except Exception as e:
        error(f"Failed to execute notebook: {e}")
        raise click.Abort()


@notebook.command(name="edit")
@click.argument("notebook_file", type=click.Path(exists=True))
@click.option(
    "--port",
    default=8888,
    help="Server port for editor",
)
def edit(notebook_file: str, port: int):
    """
    Open a workflow notebook in the visual editor.

    This launches a web server with Monaco editor for visual editing.

    Examples:

        # Open notebook in editor
        mcli workflow notebook edit notebook.json

        # Use custom port
        mcli workflow notebook edit notebook.json --port 9000
    """
    # TODO: Implement web editor server (Phase 2)
    warning("Visual editor is not yet implemented (coming in Phase 2)")
    info(f"Would open editor for: {notebook_file} on port {port}")
    info("\nFor now, you can:")
    info("  1. Edit the JSON file directly in your editor")
    info("  2. Use VSCode with Jupyter extension for .ipynb files")
    info("  3. Wait for the Monaco editor integration (Phase 2)")


if __name__ == "__main__":
    notebook()
