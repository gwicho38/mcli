#!/usr/bin/env python3
"""Linter to detect hardcoded strings that should be in constants module.

This linter scans Python files for string literals and checks if they should
be defined in the mcli.lib.constants module instead of being hardcoded.

Usage:
    python tools/lint_hardcoded_strings.py <file_or_directory>...
    python tools/lint_hardcoded_strings.py --check-all

Exit codes:
    0: No violations found
    1: Violations found
    2: Error occurred
"""

import ast
import argparse
import sys
from pathlib import Path
from typing import List, Set, Tuple, Optional
import re


# Minimum string length to check (ignore very short strings)
MIN_STRING_LENGTH = 3

# Maximum string length to check (ignore very long strings like documentation)
MAX_STRING_LENGTH = 200

# Patterns that are always allowed
ALLOWED_PATTERNS = [
    r"^[\s\n\r\t]*$",  # Whitespace only
    r"^[.,;:!?\-_/\\]+$",  # Punctuation only
    r"^[0-9]+$",  # Numbers only
    r"^[a-z]$",  # Single lowercase letter
    r"^[A-Z]$",  # Single uppercase letter
    r"^__[a-z_]+__$",  # Dunder names (__init__, __name__, etc.)
    r"^%[sd]$",  # Simple format strings
    r"^{}$",  # Empty format string
    r"^\{[a-z_]+\}$",  # Single format variable like {name}
    r"^[rgbfu]?['\"]",  # String prefixes (handled separately)
]

# File patterns to exclude from checking
EXCLUDED_FILE_PATTERNS = [
    "**/test_*.py",
    "**/*_test.py",
    "**/tests/**",
    "**/conftest.py",
    "**/setup.py",
    "**/__init__.py",  # Often have version strings and imports
    "**/constants/**/*.py",  # The constants files themselves
]

# Directories to exclude
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "build",
    "dist",
    "*.egg-info",
    "node_modules",
}

# Common strings that are acceptable to hardcode
COMMON_ACCEPTABLE_STRINGS = {
    # Common separators
    ",", ", ", "; ", ": ", " - ", " | ", "/", "\\", "-", "_", ".",
    # Common formatting
    "\n", "\r\n", "\t", " ",
    # Common characters
    "yes", "no", "true", "false", "null", "none",
    # File modes
    "r", "w", "a", "rb", "wb", "ab", "r+", "w+", "a+",
    # HTTP/encoding
    "utf-8", "utf8", "ascii", "latin-1",
    # Common keys that vary by context
    "name", "id", "key", "value", "data", "result", "status",
    "type", "kind", "format", "version",
}

# Strings that look like constants (ALL_CAPS or camelCase identifiers)
CONSTANT_LIKE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class HardcodedStringVisitor(ast.NodeVisitor):
    """AST visitor to find hardcoded strings."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, int, str, str]] = []
        self.in_docstring = False
        self.in_constant_assignment = False

    def visit_Module(self, node: ast.Module) -> None:
        """Visit module node, checking for module docstring."""
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, (ast.Str, ast.Constant))
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
            and isinstance(node.body[0].value, (ast.Str, ast.Constant))
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
            and isinstance(node.body[0].value, (ast.Str, ast.Constant))
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
        # Check if assigning to an ALL_CAPS variable (likely a constant)
        is_constant = False
        for target in node.targets:
            if isinstance(target, ast.Name) and CONSTANT_LIKE_PATTERN.match(target.id):
                is_constant = True
                break
            elif isinstance(target, ast.Attribute) and CONSTANT_LIKE_PATTERN.match(
                target.attr
            ):
                is_constant = True
                break

        if is_constant:
            self.in_constant_assignment = True
            self.generic_visit(node)
            self.in_constant_assignment = False
        else:
            self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignment (similar to visit_Assign)."""
        is_constant = False
        if isinstance(node.target, ast.Name) and CONSTANT_LIKE_PATTERN.match(
            node.target.id
        ):
            is_constant = True
        elif isinstance(node.target, ast.Attribute) and CONSTANT_LIKE_PATTERN.match(
            node.target.attr
        ):
            is_constant = True

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

    def visit_Str(self, node: ast.Str) -> None:
        """Visit string node (Python 3.7 and earlier)."""
        self._check_string(node.s, node.lineno, node.col_offset)
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
        for pattern in ALLOWED_PATTERNS:
            if re.match(pattern, string):
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
        """Visit f-string (formatted string literal)."""
        # F-strings are usually fine, but check their components
        for value in node.values:
            if isinstance(value, (ast.Constant, ast.Str)):
                # These are the literal parts of the f-string
                # Check for hardcoded strings
                string_value = value.s if isinstance(value, ast.Str) else value.value
                self._check_string(string_value, getattr(value, "lineno", node.lineno), getattr(value, "col_offset", node.col_offset))
        self.generic_visit(node)


def should_check_file(file_path: Path) -> bool:
    """Check if a file should be linted."""
    # Must be a Python file
    if file_path.suffix != ".py":
        return False

    # Check against excluded patterns
    for pattern in EXCLUDED_FILE_PATTERNS:
        if file_path.match(pattern):
            return False

    # Check if in excluded directory
    for part in file_path.parts:
        if part in EXCLUDED_DIRS:
            return False

    return True


def lint_file(file_path: Path) -> List[Tuple[int, int, str, str]]:
    """Lint a single Python file for hardcoded strings."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        visitor = HardcodedStringVisitor(str(file_path))
        visitor.visit(tree)
        return visitor.violations

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return []


def lint_directory(directory: Path) -> dict:
    """Lint all Python files in a directory."""
    results = {}
    for file_path in directory.rglob("*.py"):
        if should_check_file(file_path):
            violations = lint_file(file_path)
            if violations:
                results[file_path] = violations
    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Lint Python files for hardcoded strings"
    )
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

    args = parser.parse_args()

    if args.check_all:
        paths = [Path("src/mcli")]
    elif args.paths:
        paths = [Path(p) for p in args.paths]
    else:
        parser.print_help()
        return 0

    all_violations = {}

    for path in paths:
        if not path.exists():
            print(f"Error: Path does not exist: {path}", file=sys.stderr)
            return 2

        if path.is_file():
            if should_check_file(path):
                violations = lint_file(path)
                if violations:
                    all_violations[path] = violations
        else:
            violations = lint_directory(path)
            all_violations.update(violations)

    if all_violations:
        print("Found hardcoded strings that should be in constants module:\n")
        for file_path, violations in sorted(all_violations.items()):
            print(f"{file_path}:")
            for lineno, col_offset, string, message in violations:
                print(f"  Line {lineno}:{col_offset}: {message}")
                print(f"    String: {repr(string)}")
            print()

        total_violations = sum(len(v) for v in all_violations.values())
        print(
            f"Total: {total_violations} violation(s) in {len(all_violations)} file(s)"
        )
        print("\nTo fix these violations:")
        print("1. Add the string to the appropriate constants file in src/mcli/lib/constants/")
        print("2. Import and use the constant instead of the hardcoded string")
        print("3. Example:")
        print("   from mcli.lib.constants import EnvVars")
        print('   api_key = os.getenv(EnvVars.OPENAI_API_KEY)  # Instead of "OPENAI_API_KEY"')
        return 1

    print("No hardcoded string violations found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
