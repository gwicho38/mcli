import csv
import os

import click
import pandas as pd
from openai import OpenAI
from openpyxl.styles import Alignment

from mcli.lib.logger.logger import get_logger
from mcli.lib.shell.shell import get_shell_script_path, shell_exec

logger = get_logger(__name__)


@click.group(name="repo")
def repo():
    """repo utility - use this to interact with git and relevant utilities"""
    click.echo("repo")


@repo.command()
@click.argument("path")
def analyze(path: str):
    """Provides a source lines of code analysis for a given pkg path"""
    _analyze(path)


def _analyze(path: str):
    # Define the directory to analyze
    repo_directory = path

    # Define the file extensions to count
    file_extensions = {
        "Java": ".java",
        "Python": ".py",
        "js": ".js",
        "HTML": ".html",
        "mcli": ".mcli",
        "ts": ".ts",
        "tsx": ".tsx",
        "JSON": ".json",
        "scss": ".scss",
    }

    # Define the files and extensions to exclude
    exclude_files = [
        "node_modules",
        "resources",
        "provision",
        "jenkins",
        "git_hooks",
        "deps",
        "submodules",
    ]

    exclude_extensions = [".log", ".tmp", ".md", ".yml", ".sh", ".txt"]

    # Function to apply formatting to Excel sheets
    def format_excel_sheets(writer, sheet_name):
        workbook = writer.book
        worksheet = workbook[sheet_name]
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter  # Get the column name
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except Exception as e:
                    logger.info(e)
                    pass
            adjusted_width = max_length + 2
            worksheet.column_dimensions[column].width = adjusted_width
            for cell in col:
                cell.alignment = Alignment(wrap_text=True)

    # Function to count files and lines of code for a given directory
    def count_files_and_sloc(directory, extensions, exclude_files, exclude_extensions):
        sloc_count = {ext: {"files": 0, "sloc": 0, "details": []} for ext in extensions}
        for root, dirs, files in os.walk(directory):
            # Exclude specified directories
            dirs[:] = [d for d in dirs if d not in exclude_files]
            for file in files:
                # Exclude specified files and extensions
                if any(file.endswith(ext) for ext in exclude_extensions) or file in exclude_files:
                    continue
                for ext, ext_name in extensions.items():
                    if file.endswith(ext_name):
                        sloc_count[ext]["files"] += 1
                        file_path = os.path.join(root, file)
                        with open(file_path, "r", errors="ignore") as f:
                            sloc = sum(1 for line in f if line.strip() and line.strip() != "\n")
                            sloc_count[ext]["sloc"] += sloc
                            sloc_count[ext]["details"].append(
                                {"filename": file, "filepath": file_path, "sloc": sloc}
                            )
        return sloc_count

    # Function to write results to CSV and Excel files
    def write_results_to_files(sloc_counts, csv_file, excel_file):
        summary_data = []
        # Write the results to a CSV file
        with open(csv_file, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["File Type", "Number of Files", "SLOC"])
            for ext, counts in sloc_counts.items():
                writer.writerow([ext, counts["files"], counts["sloc"]])
                summary_data.append([ext, counts["files"], counts["sloc"]])

        # Write the detailed results to an Excel file
        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            # Write summary as the first sheet
            df_summary = pd.DataFrame(
                summary_data, columns=["File Type", "Number of Files", "SLOC"]
            )
            df_summary.to_excel(writer, sheet_name="Summary", index=False)
            format_excel_sheets(writer, "Summary")

            # Write details for each file type
            for ext, counts in sloc_counts.items():
                df = pd.DataFrame(counts["details"])
                df.to_excel(writer, sheet_name=ext, index=False)
                format_excel_sheets(writer, ext)

        logger.info(f"\nResults have been written to {csv_file} and {excel_file}")

    # Generate the SLOC counts
    sloc_counts = count_files_and_sloc(
        repo_directory, file_extensions, exclude_files, exclude_extensions
    )

    # logger.info the results in a tabular format
    logger.info("Source Lines of Code (SLOC)")
    logger.info("-" * 50)
    logger.info(f"{'File Type':<10}{'Number of Files':<20}{'SLOC':<10}")
    logger.info("-" * 50)
    for ext, counts in sloc_counts.items():
        logger.info(f"{ext:<10}{counts['files']:<20}{counts['sloc']:<10}")

    # Define the output file names
    csv_file = "sloc_report.csv"
    excel_file = "sloc_report.xlsx"

    # Write the results to CSV and Excel files
    write_results_to_files(sloc_counts, csv_file, excel_file)


@repo.command(name="wt")
def worktree():
    """Create and manage worktrees"""
    scripts_path = get_shell_script_path("repo", __file__)
    shell_exec(scripts_path, "wt")


@repo.command(name="commit")
def commit():
    """Edit commits to a repository"""
    click.echo("commit")


@repo.command(name="revert")
def revert():
    """Create and manage worktrees"""
    scripts_path = get_shell_script_path("repo", __file__)
    shell_exec(scripts_path, "revert")


@repo.command(name="migration-loe")
@click.argument("branch-a")
@click.argument("branch-b")
def loe(branch_a: str, branch_b: str):
    """Create and manage worktrees"""
    scripts_path = get_shell_script_path("repo", __file__)
    result = shell_exec(scripts_path, "migration_loe", branch_a, branch_b)
    # Assume result['result'] contains the output from the shell script
    if result is None:
        return
    # Extract the list of files from the result
    logger.info(result)
    return
    file_list = result.get("result", [])

    # Format the file list as a string for the prompt
    file_summary = "\n".join(file_list)

    # Construct the prompt for GPT-4
    prompt = f"""
    You are an expert in planning engineering projects, estimating level of effort, and a granular approach to changes for each item in an enmerated list. Analyze the following list of files to categorize the changes (e.g., UI updates, backend changes, configuration edits) and provide a detailed summary for a migration effort. Enumerate the changes in each file. Your output should also include a suggested categorization of the changes such that they can be used by the migration team to create issues in jira and track progress. The categorization must include every single file provided and report each one of them back in a category.

    {file_summary}
    """

    try:
        # Initialize the OpenAI client - API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return

        client = OpenAI(api_key=api_key)

        # Call the GPT-4 model using the client
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-4",
        )

        # Access the response content correctly
        analysis = chat_completion.choices[0].message.content
        logger.info("Analysis of changes:")
        logger.info(analysis)

    except Exception as e:
        logger.info(f"An error occurred while calling OpenAI API: {e}")


if __name__ == "__main__":
    repo()
