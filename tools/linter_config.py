"""Configuration for the hardcoded strings linter.

This file contains all the patterns, exclusions, and rules used by the
hardcoded strings linter. Keeping configuration separate from logic makes
it easier to customize and maintain the linter.
"""

# Minimum string length to check (ignore very short strings)
MIN_STRING_LENGTH = 3

# Maximum string length to check (ignore very long strings like documentation)
MAX_STRING_LENGTH = 200

# Patterns that are always allowed (regex patterns)
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

# File patterns to exclude from checking (glob patterns)
EXCLUDED_FILE_PATTERNS = [
    "**/test_*.py",
    "**/*_test.py",
    "**/tests/**",
    "**/conftest.py",
    "**/setup.py",
    "**/__init__.py",
    "**/constants/**/*.py",
]

# Directories to exclude from checking
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
    ",",
    ", ",
    "; ",
    ": ",
    " - ",
    " | ",
    "/",
    "\\",
    "-",
    "_",
    ".",
    # Common formatting
    "\n",
    "\r\n",
    "\t",
    " ",
    # Common characters
    "yes",
    "no",
    "true",
    "false",
    "null",
    "none",
    # File modes
    "r",
    "w",
    "a",
    "rb",
    "wb",
    "ab",
    "r+",
    "w+",
    "a+",
    # HTTP/encoding
    "utf-8",
    "utf8",
    "ascii",
    "latin-1",
    # Common keys that vary by context
    "name",
    "id",
    "key",
    "value",
    "data",
    "result",
    "status",
    "type",
    "kind",
    "format",
    "version",
}

# Regex pattern for constant-like names (ALL_CAPS)
CONSTANT_LIKE_PATTERN = r"^[A-Z][A-Z0-9_]*$"

# Regex pattern for identifier-like names
IDENTIFIER_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
