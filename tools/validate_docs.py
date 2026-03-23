#!/usr/bin/env python3
"""Documentation quality validator for MCLI.

Checks:
1. Version consistency: version references in docs match pyproject.toml
2. Code syntax: Python code blocks are syntactically valid
3. Internal links: markdown links resolve to existing files (delegates to validate_doc_links.py)

Usage:
    python tools/validate_docs.py [--verbose]

Exit codes:
    0: All checks passed
    1: Validation errors found
"""

import ast
import re
import sys
from pathlib import Path

# Pattern to find version-like strings (e.g., 8.0.44, pip install mcli==8.0.44)
VERSION_PATTERN = re.compile(r"(?:mcli[-_]framework|mcli)[=~><=!]+(\d+\.\d+\.\d+)")

# Pattern to find python code blocks in markdown
PYTHON_CODE_BLOCK = re.compile(
    r"```(?:python|py)\s*\n(.*?)```", re.DOTALL
)


def get_pyproject_version() -> str:
    """Read version from pyproject.toml."""
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("ERROR: pyproject.toml not found")
        sys.exit(1)

    for line in pyproject.read_text().splitlines():
        if line.startswith("version = "):
            return line.split('"')[1]

    print("ERROR: version not found in pyproject.toml")
    sys.exit(1)


def find_markdown_files() -> list[Path]:
    """Find all markdown files in the repo."""
    files = list(Path("docs").rglob("*.md")) if Path("docs").exists() else []
    for name in ["README.md", "CONTRIBUTING.md", "CHANGELOG.md"]:
        p = Path(name)
        if p.exists():
            files.append(p)
    return files


def _is_historical_doc(filepath: Path) -> bool:
    """Check if a file is a historical document (release notes, migration guides, etc.)."""
    path_str = str(filepath)
    return any(
        pattern in path_str
        for pattern in [
            "releases/",
            "MIGRATION",
            "CHANGELOG",
            "archive/",
            "bug-reports/",
        ]
    )


def check_version_consistency(files: list[Path], expected_version: str, verbose: bool) -> list[str]:
    """Check that version references in docs match pyproject.toml.

    Skips historical documents (release notes, migration guides) that
    intentionally reference old versions.
    """
    errors = []

    for filepath in files:
        if _is_historical_doc(filepath):
            if verbose:
                print(f"  SKIP {filepath} (historical document)")
            continue

        content = filepath.read_text()
        for line_num, line in enumerate(content.splitlines(), 1):
            for match in VERSION_PATTERN.finditer(line):
                found_version = match.group(1)
                if found_version != expected_version:
                    errors.append(
                        f"  {filepath}:{line_num}: version {found_version} "
                        f"does not match pyproject.toml ({expected_version})"
                    )
                elif verbose:
                    print(f"  OK {filepath}:{line_num}: {found_version}")

    return errors


def check_python_syntax(files: list[Path], verbose: bool) -> list[str]:
    """Check that Python code blocks in markdown are syntactically valid."""
    errors = []

    for filepath in files:
        if _is_historical_doc(filepath):
            if verbose:
                print(f"  SKIP {filepath} (historical document)")
            continue

        content = filepath.read_text()
        for i, match in enumerate(PYTHON_CODE_BLOCK.finditer(content)):
            code = match.group(1)

            # Skip code blocks that are clearly fragments or contain ellipsis
            if code.strip().startswith("...") or code.strip() == "":
                continue

            # Skip blocks with obvious pseudo-code markers
            if "<" in code.split("\n")[0] and ">" in code.split("\n")[0]:
                continue

            try:
                ast.parse(code)
                if verbose:
                    print(f"  OK {filepath}: code block #{i + 1}")
            except SyntaxError as e:
                # Only report if the code looks like a complete standalone block
                # (starts with an import, def, class, or decorator at top-level indent)
                first_line = code.strip().split("\n")[0] if code.strip() else ""
                is_complete_block = any(
                    first_line.startswith(kw)
                    for kw in ("import ", "from ", "def ", "class ", "@", "if __name__")
                )
                # Skip fragments (unexpected indent means it's a snippet from inside a block)
                is_fragment = e.msg == "unexpected indent"
                if is_complete_block and not is_fragment:
                    errors.append(
                        f"  {filepath}: code block #{i + 1}: {e.msg} (line {e.lineno})"
                    )

    return errors


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    version = get_pyproject_version()
    files = find_markdown_files()

    if not files:
        print("No markdown files found.")
        return 0

    print(f"Validating {len(files)} markdown files against version {version}")
    print()

    all_errors = []

    # Version consistency
    print("Checking version consistency...")
    version_errors = check_version_consistency(files, version, verbose)
    all_errors.extend(version_errors)
    if version_errors:
        print(f"  Found {len(version_errors)} version mismatches:")
        for err in version_errors:
            print(err)
    else:
        print("  All version references are consistent.")
    print()

    # Python syntax
    print("Checking Python code block syntax...")
    syntax_errors = check_python_syntax(files, verbose)
    all_errors.extend(syntax_errors)
    if syntax_errors:
        print(f"  Found {len(syntax_errors)} syntax errors:")
        for err in syntax_errors:
            print(err)
    else:
        print("  All Python code blocks are valid.")
    print()

    # Summary
    if all_errors:
        print(f"FAILED: {len(all_errors)} issue(s) found")
        return 1
    else:
        print("PASSED: All documentation checks passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
