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
    # Rich markup patterns with content
    r"^\[dim\].*\[/dim\]$",  # Dim styled text
    r"^\[bold\].*\[/bold\]$",  # Bold styled text
    r"^\[red\].*\[/red\]$",  # Red styled text (often error prefixes)
    r"^\[green\].*\[/green\]$",  # Green styled text
    r"^\[yellow\].*\[/yellow\]$",  # Yellow styled text
    r"^• \[[a-z]+\]",  # Bullet with styled content
    # Rich markup prefixes (partial strings for f-string formatting)
    r"^\[bold\]",  # Bold prefix
    r"^\[dim\]",  # Dim prefix
    r"^\[italic\]",  # Italic prefix
    r"^\[bold green\]",  # Bold green prefix
    r"^\[bold cyan\]",  # Bold cyan prefix
    r"^\[red\]Process ",  # Process error prefix
    r"^\[red\]Error:",  # Error prefix
    r"^\[bold\]Process ",  # Process info prefix
    r"^\[bold\]Logs for ",  # Logs header prefix
    r"^\[bold\]Matching Commands",  # Command search prefix
    r"^\[dim\]\.\.\. and ",  # Truncation indicator
    # Partial format patterns used in f-strings
    r"^Secret '",  # Secret prefix for messages
    r"^Command '",  # Command prefix for messages
    r"^✅ Model '",  # Model success message prefix
    r"^❌ Model ",  # Model error message prefix
    r"^Avg [A-Z][a-z]+",  # Average statistics
    # Workflow/daemon patterns
    r"^Error connecting to daemon: ",
    r"^\[red\]Error connecting to daemon: ",
    r"^Commands directory does not exist: ",
    r"^Invalid command name: ",
    r"^Invalid group name: ",
    # Common log patterns
    r"^Loading notebook commands from ",
    r"^Secrets workflow not available: ",
    r"^Notebook commands not available: ",
    r"^Sync commands not available: ",
    r"^Storage commands not available: ",
    r"^\[dim\]Saved to: ",
    r"^\[dim\]Git repository: ",
    # Generic error patterns
    r"^Error: HTTP ",
    r"^Model not found",
    # Docstring/help text patterns (often in command help)
    r" command\.\"\)\n",
    r"\. Use lowercase letters",
    # Code templates (strings containing Python code)
    r"import click",
    r"@click\.",
    r"def \w+\(",
    r"\"\"\"\n\s+",  # Docstring markers in templates
    r"^\[red\]Command '",  # Rich error prefix
    r"^✅ Model ",
    # HTML/GraphViz templates
    r"^<TR><TD",
    r"BGCOLOR=",
    r"COLSPAN=",
    # Multi-line code templates (Python code in string literals)
    r"\n\"\"\"\n",  # Docstrings in templates
    r"pass\n\n@",  # Empty function followed by decorator
    r"# Your command implementation",  # Template comments
    r"# Example",  # Example comments in templates
    r"^\.\n\"\"\"",  # Template starting with docstring
    # Regex patterns used in validation code
    r"^\^",  # Starts with ^ (regex anchor)
    r"\$$",  # Ends with $ (regex anchor)
    r"\[[a-z]+-[a-z]+\]",  # Character classes like [a-z0-9]
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
    # Dashboard files have many Streamlit-specific UI strings
    "**/dashboard/**/*.py",
    "**/pages/**/*.py",
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
    # Dashboard directories (Streamlit-specific UI strings are impractical to constantize)
    "dashboard",
    "pages",
    # ERD module (GraphViz template strings)
    "erd",
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
    " files",
    " -> ",
    ") - ",
    # Common UI prefixes (partial strings for f-string formatting)
    "Process ",
    "Found ",
    "Model ",
    "Cell ",
    "Command: ",
    "Loaded ",
    "Processed ",
    "Skipping ",
    "Extracted ",
    "Description: ",
    "Module: ",
    "Tags: ",
    "Bearer ",
    "process:",
    # Common status prefixes
    "✅ ",
    "❌ ",
    "⚠️ ",
    "ℹ️ ",
    # Database column names (domain-specific)
    "politician_name_cleaned",
    "transaction_amount_cleaned",
    "transaction_date_cleaned",
    "gravity_anomaly_mgal",
    # Config files
    "config.toml",
    # Test data that may appear in examples
    "Nancy Pelosi",
    # Common log prefixes
    "Error: ",
    "Warning: ",
    "Info: ",
    "Debug: ",
    "Exported ",
    "export ",
    # UI label patterns
    "   Connection URL: ",
    "  Path: ",
    " (ID: ",
    "🎯 Recommended model: ",
    "❌ Visual effects not available: ",
    ".\n\nDescription: ",
    # Command documentation patterns
    " command for mcli.",
    "command:",
    # Common file names
    "commands.lock.json",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    # API names
    "MCLI API",
    # Common partial f-string patterns
    "[red]Error: ",
    "Created: ",
    "Executing: ",
    "Copying commands from ",
    "Copying ",
    " FPS...",
    " frames.",
    "GB total (",
    " to edit command logic...",
    # Chat UI patterns
    "No description",
    "No processes running",
    "No logs available",
    "ID: ",
    "Status: ",
    "Name: ",
    "Started: ",
    "Error listing commands: ",
    "Available built-in chat commands:",
    " more",
    " more commands",
    # Common action/status prefixes
    "❌ Error: ",
    "✅ Command '",
    "Cleaned up ",
    "File not found: ",
    "    Exists: ",
    "Plugin '",
    " failed: ",
    "Experiment ",
    " features",
    " = ",
    "Imported ",
    "Execution time: ",
    "Container ",
    "  RAM: ",
    # HTTP headers
    "WWW-Authenticate",
    "Content-Length",
    "Content-Type",
    "Authorization",
    "Accept",
    "User-Agent",
    # Database columns and table names
    "portfolios.id",
    "transaction_type_cleaned",
    # Model names
    "phi3-mini",
    "llama3",
    "gemma",
    # Command status messages
    "🎯 Using specified model: ",
    " script(s) to JSON",
    "  CID: [bold cyan]",
    "  [dim]Retrieve with: mcli workflows sync pull ",
    "[red]✗ Failed to import IPFS sync module: ",
    "[red]✗ IPFS push failed: ",
    "Delete command '",
    "[green]Deleted custom command: ",
    "[red]Failed to delete command: ",
    "[red]Command not found: ",
    "[red]Failed to load command: ",
    "[red]Command has no code: ",
}

# Regex pattern for constant-like names (ALL_CAPS)
CONSTANT_LIKE_PATTERN = r"^[A-Z][A-Z0-9_]*$"

# Regex pattern for identifier-like names
IDENTIFIER_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
