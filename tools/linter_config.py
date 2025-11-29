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
    # Rich markup patterns (console styling)
    r"^\[/?[a-z]+\]$",  # Simple tags like [green], [/green], [bold], [dim]
    r"^\[/?[a-z]+ [a-z]+\]$",  # Tags with modifiers like [bold green]
    r"^\[/?[a-z_]+\]$",  # Tags with underscores
    r"^•\s*$",  # Bullet points
    r"^\s+$",  # Indentation only
    r"^\[bold cyan\]>>> \[/bold cyan\]$",  # Input prompt pattern
    # Python format specifiers (f-strings and .format())
    r"^[,+<>]?\.[0-9]+[fdeEgG%]$",  # Format specs: .1f, .2%, +.1f, etc.
    r"^[0-9]+d$",  # Integer format: 05d, etc.
    r"^<[0-9]+$",  # Left align: <10
    r"^>[0-9]+$",  # Right align: >10
    r"^\^[0-9]+$",  # Center align: ^10
    # File extensions
    r"^\.[a-z0-9]+$",  # File extensions: .json, .py, .png, etc.
    # UI formatting
    r"^\s+[•\-→]\s*$",  # Indented bullets/arrows: "  • ", "  - ", " → "
    # Version strings
    r"^[0-9]+\.[0-9]+(\.[0-9]+)?$",  # Versions: 1.0, 1.0.0
    # Date/time format strings
    r"^%[YymdHMSp]+[_\-:]*%?[YymdHMSp]*",  # Date formats: %Y%m%d, %H:%M:%S
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
    "  ",  # Two spaces indentation
    "• ",
    "...",
    # Common characters
    "yes",
    "no",
    "true",
    "false",
    "null",
    "none",
    "on",
    "off",
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
    "error",
    "message",
    "output",
    "input",
    "path",
    "file",
    "url",
    "method",
    "content",
    # CLI keywords (lookup strings for startswith checks)
    "ps",
    "run",
    "exit",
    "quit",
    "help",
    "search",
    "find",
    "list",
    "show",
    "commands",
    "hello",
    # LLM providers
    "local",
    "openai",
    "anthropic",
    "ollama",
    # Common languages
    "python",
    "bash",
    "shell",
    "javascript",
    "json",
    "yaml",
    "toml",
    # Common units
    " MB",
    " GB",
    " KB",
    " bytes",
    " seconds",
    " minutes",
    " hours",
    " days",
    " ms",
    # Common prefixes/suffixes (often used in console output)
    " to ",
    " of ",
    " in ",
    " for ",
    " not found",
    " commands",
    " items",
    # Database column names
    "politician_name_cleaned",
    "transaction_amount_cleaned",
    # Config files
    "config.toml",
}

# Regex pattern for constant-like names (ALL_CAPS)
CONSTANT_LIKE_PATTERN = r"^[A-Z][A-Z0-9_]*$"

# Regex pattern for identifier-like names
IDENTIFIER_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
