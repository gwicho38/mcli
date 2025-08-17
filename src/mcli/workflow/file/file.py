import click
import fitz  # PyMuPDF


@click.group(name="file")
def file():
    """Personal file utility to use with custom and/or default file system paths."""
    pass


@file.command()
@click.argument("input_oxps", type=click.Path(exists=True))
@click.argument("output_pdf", type=click.Path())
def oxps_to_pdf(input_oxps, output_pdf):
    """Converts an OXPS file (INPUT_OXPS) to a PDF file (OUTPUT_PDF)."""
    try:
        # Open the OXPS file
        oxps_document = fitz.open(input_oxps)

        # Convert to PDF bytes
        pdf_bytes = oxps_document.convert_to_pdf()

        # Open the PDF bytes as a new PDF document
        pdf_document = fitz.open("pdf", pdf_bytes)

        # Save the PDF document to a file
        pdf_document.save(output_pdf)

        click.echo(f"Successfully converted '{input_oxps}' to '{output_pdf}'")

    except Exception as e:
        click.echo(f"Error converting file: {e}", err=True)


import os
import subprocess
from pathlib import Path
from typing import List, Optional

DEFAULT_DIRS = ["~/repos/lefv-vault", "~/Documents/OneDrive", "~/Documents/Documents"]


@file.command(name="search")
@click.argument("search-string", type=str)
@click.argument("search-dirs", default=DEFAULT_DIRS)
@click.argument("context-lines", default=3, type=int)
def find_string_with_fzf(
    search_string: str = "foo",
    search_dirs: Optional[List[str]] = DEFAULT_DIRS,
    context_lines: int = 3,
) -> List[str]:
    """
    Search for a string with ripgrep in given directories and select matches with fzf.

    Parameters:
        search_string (str): The string to search for.
        search_dirs (Optional[List[str]]): Directories to search in. Defaults to a predefined list.
        context_lines (int): Number of lines of context above and below the match.

    Returns:
        List[str]: List of selected lines with context from fzf.
    """
    if not search_string.strip():
        raise ValueError("Search string cannot be empty")

    dirs_to_search = search_dirs or DEFAULT_DIRS
    expanded_dirs = [str(Path(d).expanduser()) for d in dirs_to_search]

    # Validate directories exist
    valid_dirs = [d for d in expanded_dirs if Path(d).exists()]
    if not valid_dirs:
        raise FileNotFoundError("None of the provided or default directories exist")

    # Run ripgrep with context lines
    rg_command = ["rg", "--color=always", f"-C{context_lines}", search_string, *valid_dirs]

    try:
        rg_proc = subprocess.run(rg_command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print("No matches found or error running rg.")
        return []

    # Pipe the output through fzf
    try:
        fzf_proc = subprocess.run(
            ["fzf", "--ansi", "--multi"],
            input=rg_proc.stdout,
            capture_output=True,
            text=True,
            check=True,
        )
        selections = fzf_proc.stdout.strip().split("\n")
        return [s for s in selections if s.strip()]
    except subprocess.CalledProcessError:
        # User exited fzf without selection
        return []


if __name__ == "__main__":
    file()
