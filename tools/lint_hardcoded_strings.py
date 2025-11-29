#!/usr/bin/env python3
"""Linter to detect hardcoded strings that should be in constants module.

This linter scans Python files for string literals and checks if they should
be defined in the mcli.lib.constants module instead of being hardcoded.

Usage:
    python tools/lint_hardcoded_strings.py <file_or_directory>...
    python tools/lint_hardcoded_strings.py --check-all
    python tools/lint_hardcoded_strings.py --json  # Output JSON for CI/CD

Exit codes:
    0: No violations found
    1: Violations found
    2: Error occurred (syntax errors, file not found, etc.)
"""

import argparse
import ast
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Import configuration from separate config file for better maintainability
from linter_config import ALLOWED_PATTERNS, COMMON_ACCEPTABLE_STRINGS
from linter_config import CONSTANT_LIKE_PATTERN as CONSTANT_PATTERN_STR
from linter_config import EXCLUDED_DIRS, EXCLUDED_FILE_PATTERNS
from linter_config import IDENTIFIER_PATTERN as IDENTIFIER_PATTERN_STR
from linter_config import MAX_STRING_LENGTH, MIN_STRING_LENGTH

# Compile regex patterns
CONSTANT_LIKE_PATTERN = re.compile(CONSTANT_PATTERN_STR)
IDENTIFIER_PATTERN = re.compile(IDENTIFIER_PATTERN_STR)


class HardcodedStringVisitor(ast.NodeVisitor):
    """AST visitor to find hardcoded strings."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: list[tuple[int, int, str, str]] = []
        self.in_docstring = False
        self.in_constant_assignment = False

    def visit_Module(self, node: ast.Module) -> None:
        """Visit module node, checking for module docstring."""
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            # Skip module docstring
            self.in_docstring = True
            self.generic_visit(node.body[0])
            self.in_docstring = False
            # Visit the rest
            for child in node.body[1:]:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition, checking for docstring."""
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            # Skip function docstring
            self.in_docstring = True
            self.generic_visit(node.body[0])
            self.in_docstring = False
            # Visit the rest
            for child in node.body[1:]:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition, checking for docstring."""
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            # Skip class docstring
            self.in_docstring = True
            self.generic_visit(node.body[0])
            self.in_docstring = False
            # Visit the rest
            for child in node.body[1:]:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment, checking if it's a constant assignment."""
        # Use any() to check if assigning to an ALL_CAPS variable (likely a constant)
        is_constant = any(
            (isinstance(target, ast.Name) and CONSTANT_LIKE_PATTERN.match(target.id))
            or (isinstance(target, ast.Attribute) and CONSTANT_LIKE_PATTERN.match(target.attr))
            for target in node.targets
        )

        if is_constant:
            self.in_constant_assignment = True
            self.generic_visit(node)
            self.in_constant_assignment = False
        else:
            self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignment (similar to visit_Assign)."""
        is_constant = (
            isinstance(node.target, ast.Name) and CONSTANT_LIKE_PATTERN.match(node.target.id)
        ) or (
            isinstance(node.target, ast.Attribute) and CONSTANT_LIKE_PATTERN.match(node.target.attr)
        )

        if is_constant:
            self.in_constant_assignment = True
            self.generic_visit(node)
            self.in_constant_assignment = False
        else:
            self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Visit constant node (Python 3.8+)."""
        if isinstance(node.value, str):
            self._check_string(node.value, node.lineno, node.col_offset)
        self.generic_visit(node)

    def _check_string(self, string: str, lineno: int, col_offset: int) -> None:
        """Check if a string should be flagged as hardcoded."""
        # Skip if in docstring
        if self.in_docstring:
            return

        # Skip if in constant assignment (defining constants is ok)
        if self.in_constant_assignment:
            return

        # Skip very short or very long strings
        if len(string) < MIN_STRING_LENGTH or len(string) > MAX_STRING_LENGTH:
            return

        # Skip if matches allowed patterns
        if any(re.match(pattern, string) for pattern in ALLOWED_PATTERNS):
            return

        # Skip common acceptable strings
        if string in COMMON_ACCEPTABLE_STRINGS:
            return

        # Skip if it looks like a simple identifier or format string
        if IDENTIFIER_PATTERN.match(string) and len(string) < 20:
            # Allow simple identifiers in some contexts
            return

        # Skip if it's a path-like string that's being constructed
        if "/" in string or "\\" in string:
            # Likely a path being constructed
            return

        # Skip strings that are mostly format placeholders
        if string.count("{") > len(string) // 4:
            return

        # If we get here, it's likely a hardcoded string that should be in constants
        self.violations.append(
            (
                lineno,
                col_offset,
                string[:50] + ("..." if len(string) > 50 else ""),
                "Hardcoded string should be in constants module",
            )
        )

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """Visit f-string (formatted string literal).

        Check the literal parts of f-strings for hardcoded strings.
        """
        for value in node.values:
            # Check literal parts of f-strings (Python 3.8+ uses ast.Constant)
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                self._check_string(value.value, value.lineno, value.col_offset)

        self.generic_visit(node)


def should_check_file(file_path: Path) -> bool:
    """Check if a file should be linted.

    Uses fnmatch for reliable glob pattern matching instead of Path.match().
    """
    # Must be a Python file
    if file_path.suffix != ".py":
        return False

    # Convert path to string with forward slashes for consistent matching
    path_str = str(file_path).replace("\\", "/")

    # Check against excluded patterns using fnmatch
    # Support both ** and * wildcards
    for pattern in EXCLUDED_FILE_PATTERNS:
        # Convert ** to * for fnmatch (it doesn't support **)
        # But first check if path contains the key directory
        if "constants" in pattern and "constants" in path_str:
            return False
        # For other patterns, use standard fnmatch
        if fnmatch.fnmatch(path_str, pattern.replace("**/", "*/").replace("**", "*")):
            return False

    # Check if in excluded directory
    if any(part in EXCLUDED_DIRS for part in file_path.parts):
        return False

    return True


def lint_file(file_path: Path) -> tuple[list[tuple[int, int, str, str]], bool]:
    """Lint a single Python file for hardcoded strings.

    Returns:
        Tuple of (violations list, had_error boolean)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        visitor = HardcodedStringVisitor(str(file_path))
        visitor.visit(tree)
        return visitor.violations, False

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return [], True
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return [], True


def lint_directory(directory: Path) -> tuple[dict[Path, list], bool]:
    """Lint all Python files in a directory.

    Returns:
        Tuple of (results dict, had_any_errors boolean)
    """
    results = {}
    had_errors = False

    for file_path in directory.rglob("*.py"):
        if should_check_file(file_path):
            violations, had_error = lint_file(file_path)
            if had_error:
                had_errors = True
            if violations:
                results[file_path] = violations

    return results, had_errors


def output_text(all_violations: dict[Path, list]) -> None:
    """Output violations in human-readable text format."""
    print("Found hardcoded strings that should be in constants module:\n")
    for file_path, violations in sorted(all_violations.items()):
        print(f"{file_path}:")
        for lineno, col_offset, string, message in violations:
            print(f"  Line {lineno}:{col_offset}: {message}")
            print(f"    String: {repr(string)}")
        print()

    total_violations = sum(len(v) for v in all_violations.values())
    print(f"Total: {total_violations} violation(s) in {len(all_violations)} file(s)")
    print("\nTo fix these violations:")
    print("1. Add the string to the appropriate constants file in src/mcli/lib/constants/")
    print("2. Import and use the constant instead of the hardcoded string")
    print("3. Example:")
    print("   from mcli.lib.constants import EnvVars")
    print('   api_key = os.getenv(EnvVars.OPENAI_API_KEY)  # Instead of "OPENAI_API_KEY"')


def output_json(all_violations: dict[Path, list]) -> None:
    """Output violations in JSON format for CI/CD integration."""
    result = {
        "total_violations": sum(len(v) for v in all_violations.values()),
        "total_files": len(all_violations),
        "files": {},
    }

    for file_path, violations in all_violations.items():
        result["files"][str(file_path)] = [
            {
                "line": lineno,
                "column": col_offset,
                "string": string,
                "message": message,
            }
            for lineno, col_offset, string, message in violations
        ]

    print(json.dumps(result, indent=2))


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lint Python files for hardcoded strings")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to check",
    )
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="Check all Python files in src/mcli",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (fewer exceptions)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format for CI/CD integration",
    )

    args = parser.parse_args()

    if args.check_all:
        paths = [Path("src/mcli")]
    elif args.paths:
        paths = [Path(p) for p in args.paths]
    else:
        parser.print_help()
        return 0

    all_violations = {}
    had_errors = False

    for path in paths:
        if not path.exists():
            print(f"Error: Path does not exist: {path}", file=sys.stderr)
            return 2

        if path.is_file():
            if should_check_file(path):
                violations, had_error = lint_file(path)
                if had_error:
                    had_errors = True
                if violations:
                    all_violations[path] = violations
        else:
            violations, dir_had_errors = lint_directory(path)
            if dir_had_errors:
                had_errors = True
            all_violations.update(violations)

    # If we had syntax or processing errors, return error code
    if had_errors:
        return 2

    if all_violations:
        if args.json:
            output_json(all_violations)
        else:
            output_text(all_violations)
        return 1

    if not args.json:
        print("No hardcoded string violations found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
