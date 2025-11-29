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
    # Emoji-prefixed UI strings (visual indicators, impractical to constantize)
    r"^[✅❌⚠️🔄🚀📝💡📊🎯🔥🏁📈💻🛑🔤📄📏🔍⬆️📦ℹ️🦀🐍⚡🎉✓✗•→─]",  # Common UI emojis
    r"^\[red\][✅❌⚠️]",  # Rich markup with emoji
    r"^\[green\][✅❌⚠️]",  # Rich markup with emoji
    r"^\[yellow\][✅❌⚠️]",  # Rich markup with emoji
    r"^\[cyan\][✅❌⚠️📦🔍ℹ️]",  # Rich markup with emoji
    # Rich markup with common UI words (process, started, downloading, etc.)
    r"^\[green\]Process ",
    r"^\[green\]Started ",
    r"^\[green\]Stopped ",
    r"^\[green\]Running ",
    r"^\[green\]Loaded ",
    r"^\[green\]Saved ",
    r"^\[green\]Created ",
    r"^\[green\]Connected ",
    r"^\[yellow\]Downloading ",
    r"^\[yellow\]Loading ",
    r"^\[yellow\]Starting ",
    r"^\[yellow\]Stopping ",
    r"^\[yellow\]Warning",
    r"^\[red\]Failed ",
    r"^\[red\]Stopped ",
    r"^\[red\]Error ",
    r"^\[cyan\]Info",
    r"^\[cyan\]Current",
    r"^\[cyan\]Checking",
    # Label patterns (ending with colon and space)
    r"^[A-Z][a-z]+ ?[A-Z]?[a-z]*: $",  # e.g., "Working Dir: ", "CPU: ", "Status: "
    r"^\\n[A-Z][a-z]+: $",  # e.g., "\nDescription: ", "\nTags: "
    r"^  [A-Z][a-z]+: $",  # Indented labels
    # Install/setup command patterns
    r"^  (pip|brew|npm|apt|yum|dnf) install ",
    r"^  (uv|cargo|go) (install|add|get) ",
    # Natural language command patterns (for chat/AI)
    r"^(create|new|make|add|build|generate) (a |the )?(command|task|job|process)",
    r"^(delete|remove|update|edit|run|execute|start|stop) (a |the )?(command|task|job|process)",
    # Common prefix patterns for UI
    r"^(cmd|shell|task|job|process|container)-",
    # Italic/formatting prefixes
    r"^  \[italic\]",
    r"^\[italic\]",
    # Cloud provider patterns
    r"^(Azure|Aws|Gcp|AWS|GCP) secrets have been",
    r"^Successfully revoked provisioned (Azure|Aws|Gcp|AWS|GCP)",
    r"^Deleted locally persisted secrets",
    r"secrets have been persisted into:",
    # Common auth patterns
    r"^Basic ",
    r"^Bearer ",
    r"^mcli_key ",
    # Common file extensions and paths
    r"^(aws|azure|gcp|config|credentials|settings)\.(json|yaml|toml)$",
    # Logger/debug patterns
    r"^logger\.(info|debug|warning|error|critical)",
    # Common action patterns
    r"^(File|Directory|Path|Key|Secret|Token) does not exist",
    r"^(File|Directory|Path|Key|Secret|Token) already exists",
    r"^Private key does not exist",
    # Allowed/available patterns
    r"^Allowed (actions|options|values) are:",
    r"^Available (commands|options|methods) are:",
    # Logging/tracing patterns
    r"tracing (enabled|disabled)",
    r"^(Python interpreter|System process) tracing",
    r"^(Registered|Unregistered) process ID",
    r"for monitoring$",
    r"^mcli\.(out|log|err)$",
    # Connection/service patterns
    r"^(Connected|Disconnected|Connecting) (to|from)",
    r"^(Service|Server|Client|Daemon) (started|stopped|running|failed)",
    # Use/Usage patterns
    r"^Use ['\"](logs|ps|stop|start|inspect|kill)",
    r"to (view|see|show|check) (output|status|logs|info)",
    # Warning/Error retrieval patterns
    r"^Warning: Error (retrieving|getting|fetching|loading)",
    r"^Error (retrieving|getting|fetching|loading)",
    # Failed action patterns
    r"^Failed to (connect|load|save|set|get|create|delete|start|stop|find)",
    r"^Could not (connect|load|save|set|get|create|delete|start|stop|find)",
    r"^Unable to (connect|load|save|set|get|create|delete|start|stop|find)",
    # Process/service not found patterns
    r"^(Process|Service|Model|File|Command|Task) not found",
    # Found/Saved/Added patterns (common log prefixes)
    r"^(Found|Saved|Added|Removed|Updated|Loaded|Logged|Created|Deleted) ",
    # SQL patterns
    r"^PRAGMA ",
    r"^SELECT ",
    r"^INSERT ",
    r"^UPDATE ",
    r"^DELETE FROM",
    r"^CREATE TABLE",
    r"^ALTER TABLE",
    r"^DROP TABLE",
    # CLI flag patterns
    r"^--[a-z]+-?[a-z]*$",  # e.g., "--url", "--api-key"
    # Received signal pattern
    r"^Received signal ",
    # Caching disabled pattern
    r"Caching disabled",
    # MLflow patterns
    r"^No active MLflow run",
    # IP addresses
    r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$",
    # Indented checkmarks/status
    r"^  [✅❌⚠️✓✗] ",
    # Code template patterns (command generation)
    r"_command\(name",
    r"command group\.\"\"\"\n",
    r"# Your command implementation",
    r"@app\.command\(",
    r"command for mcli\.",
    r"logger\.info\(f\"Hello",
    # Sync patterns
    r"^(Syncing|Synced|Synchronizing|Synchronized) ",
    # Video/Media patterns
    r"^Video saved to ",
    r"^Image saved to ",
    # Score/metric label patterns
    r"Score: $",
    r"Cores: $",
    r"Count: $",
    r"Rate: $",
    r"Size: $",
    # File quotes pattern
    r"^File '",
    # Model/action patterns
    r"^\[yellow\]Model '",
    r"^Model ID: ",
    r"^Available models:",
    # Test data patterns
    r"^test document",
    r"^Hello, World!$",
    # Using patterns
    r"^Using (random|default|specified|configured) ",
    # Transition patterns
    r"^Transitioned ",
    # Color/style names
    r"^bold (cyan|green|red|yellow|magenta|blue|white)$",
    r"^(dim|italic|underline|bold)$",
    # Download emoji pattern
    r"^📥 ",
    # Suffix patterns (often in f-strings)
    r" (records|samples|features|scripts?|items|files|bytes|entries)$",
    r" trading records$",
    r" secrets to $",
    # Optional dependency pattern
    r"^Optional dependency '",
    r"^Falling back to ",
    # Tags pattern
    r"^Tags for ",
    r"    Tags: $",
    # Action/Dataset patterns
    r"^Action '",
    r"^Dataset '",
    r"^Variant ",
    # Alias definitions (shell configuration)
    r"^alias [a-z]+='",
    # Confirmation/prompt patterns
    r"^Are you sure you want to ",
    r"^Do you want to ",
    r"^Continue\?",
    r"^Press (Ctrl\+C|Enter|any key)",
    r"^Navigate to ",
    r"^Consider (cleaning|using|updating|installing)",
    # Access/cannot patterns
    r"^Cannot access '",
    r"^Cannot (open|read|write|find|load|save|delete|create) ",
    # CSP and security headers (too technical to constantize)
    r"^default-src ",
    r"^script-src ",
    r"^style-src ",
    # CronExpression pattern (code/data structure)
    r"^CronExpression\('",
    # Main guard pattern (template)
    r"^if __name__ ==",
    r"\n\nif __name__ ==",
    # Run/execute suggestion patterns
    r"^Run '",
    r"^Use '",
    r"^Try '",
    # Installation status patterns
    r"^Installing ",
    r"^Installed ",
    r"^Uninstalling ",
    r"^Uninstalled ",
    # Info bullet patterns (leading whitespace with emoji/bullet)
    r"^\s+[ℹ️⚠️✅❌⚙️📦🐍🦀⚡]",
    r"^\s+•\s*",
    # Agent/Auth patterns
    r"^Agent DID:",
    r"^Space DID:",
    r"^Authenticated:",
    # Quote patterns for error messages
    r"^[A-Z][a-z]+ '[^']+' ",  # e.g., "Daemon 'foo' not found"
    r"' (not found|already exists|is required|is invalid|failed)$",
    # Description patterns
    r"^description contains '",
    r"^Delete secret '",
    r"^Delete command '",
    # Status label patterns (with leading whitespace)
    r"^\s+(Next run|Installed|Authenticated|Files|Path|Size|Group):",
    r"^\s+Similarity:",
    # Time-of-day greetings/messages
    r"^It's (quite|work|break) ",
    r"^🌙 ",
    r"^⏰ ",
    # What's your name pattern (prompts)
    r"^🎨 What's your ",
    # Experiment success patterns
    r"^\[green\]✓ ",
    # LocalDaemonClient patterns (debug/log messages)
    r"^\[LocalDaemonClient\]",
    # Matching/search result patterns
    r"^\\n🔍 \*\*Commands matching",
    r"^\\n💡 Use '",
    # Note patterns
    r"^\\n\\n⚠️  \*\*Note\*\*:",
    # Shell aliases
    r"^alias m[a-z]*='mcli",
    # Percentage check pattern
    r"%\)\. Check what's running",
    # More install patterns with commands
    r"^  cd [a-z_]+",
    r"^  docker run ",
    r"^  pip install ",
    r"^  brew install ",
    # Check/Some patterns
    r"^Some checks failed\.",
    r"^Check what's running",
    # Password/user patterns
    r"^Change current user's password",
    # Cleanup/cleanup suggestion
    r"^Consider cleaning ",
    # Document/PDF patterns
    r"^PDF path is required",
    r"^Text is required",
    # Path/directory error patterns
    r"^Path is not a directory:",
    r"^Plugin directory does not exist",
    # Select/save patterns
    r"^Select (model|option|file)",
    r"^save as$",
    # Simulation patterns
    r"^Must run simulation first",
    # Batch/processing patterns
    r"^Processing batch of ",
    r"^Received ",
    # MLflow patterns
    r"^Started MLflow run:",
    # Register/endpoint patterns
    r"^Registered API endpoint:",
    # Started/Stopped with detail
    r"^Started file watcher for ",
    r"^Stopped process ",
    # Skipped with reason
    r"^Skipped ",
    # Ratio/score patterns
    r"^Sharpe Ratio",
    r"^Sortino Ratio",
    # Sentence transformers (library name)
    r"^sentence_transformers$",
    # Selected pattern
    r"^Selected ",
    # Script info pattern
    r"^Script ",
    # RETURN from pattern (debugging)
    r"^RETURN from ",
    # JSON/IPYNB files
    r"^\*\.(json|ipynb)$",
    # Update pattern
    r"^update $",
    # Query pattern
    r"^query $",
    # Line number pattern
    r"^LINE $",
    # Features pattern
    r" features from $",
    # Bytes pattern
    r" bytes $",
    # Policy pattern
    r"^policy_relevant_trade$",
    # Caching/disabled suffix
    r"\. Caching disabled\.$",
    # Efficiency/CPU label patterns
    r"^\s+Efficiency Score:",
    r"^\s+CPU Cores:",
    # Metadata file
    r"^metadata\.json$",
    # LSH patterns
    r"^LSH API (URL|key)$",
    # Clean simulator
    r"^Clean simulator data$",
    # Flag patterns
    r"^ -[a-z] $",
    # TF-IDF patterns
    r"^🐍 Python TF-IDF:",
    r"^🦀 Rust TF-IDF:",
    # Speedup pattern
    r"^⚡ Speedup:",
    # String: pattern (nested quote in output)
    r'^String: "',
    # Model running/privacy messages
    r" model\. I'm running entirely on your machine",
    # Secrets into namespace
    r" secrets into namespace '",
    # Package/conversion patterns
    r"^📦 Installing ",
    # All conversion methods
    r"^All conversion methods failed$",
    r"^\[dim\] ",
    # Model/Job action patterns
    r"^Model (saved|loaded|deleted|created|updated) (to|from) ",
    r"^Job (started|stopped|completed|failed|running)",
    r"^Killed process ",
    # Open/Opening patterns
    r"^Open ",
    r"^Opening (command|file|editor|browser|terminal) ",
    # Imported/Extracted patterns
    r"^Imported from ",
    r"^Extracting (frames|data|features) from ",
    # Gateway/Function patterns (system names)
    r"^Gateway ",
    r"^Function ",
    # Sync/Store patterns
    r"^Sync commands ",
    r"^Store path (updated|created|deleted) ",
    # Missing field pattern
    r"^Missing required field:",
    # mcli product name patterns
    r"^mcli-framework$",
    r"^mcli $",
    # No commands/items found
    r"^No (commands|items|results|files|matches) found$",
    # Prediction/question patterns
    r"^prediction:$",
    r"^Is the text risky\?",
    # Fetched pattern
    r"^Fetched ",
    # Failed patterns with more context
    r"^Failed to show command:",
    r"^Failed to reload command",
    r"^Failed to list (spaces|commands|files):",
    r"^Failed to kill process",
    r"^Failed to generate recommendation",
    r"^Failed to execute (command|script)",
    # Error: patterns
    r"^Error: Command group",
    r"^Error (updating|creating|deleting|loading) command",
    r"^Error (updating|creating|deleting|loading) (file|config)",
    # Shell config patterns
    r'^fpath=\("',
    # Suffix patterns (partial f-strings)
    r" script\(s\)$",
    r" on $",
    r" bytes  $",
    # Database table.column patterns
    r"^[a-z_]+\.(id|name|status|type|value|created_at|updated_at)$",
    # Command docstring templates (multiline code)
    r"command\.\n    \"\"\"\n",
    r"logger\.info\(f\"Hello",
    r"command group\.\"\"\"\n    pass\n",
    r"Your command implementation goes here",
    r"Example",
    r"@app\.command\(",
    # More error patterns
    r"^Error (stopping|recording|reading|processing|executing|adding) ",
    r"^Error (parsing|validating|converting|importing|exporting) ",
    # DVC/git patterns
    r"^DVC command failed:",
    r"^Git command failed:",
    # Discovery/detection patterns
    r"^Discovered ",
    r"^Detected ",
    r"^Converting ",
    r"^Converted ",
    r"^Cleared ",
    # Could not patterns
    r"^Could not (extract|parse|read|write|find|load|save) ",
    # Training/ML patterns
    r"^Epoch ",
    r"^Batch ",
    r"^Auto-loading model:",
    # API patterns
    r"^API (URL|endpoint|key|token):",
    r"^Endpoint not found$",
    r"^API endpoint for ",
    # Cache patterns
    r"^Cache (miss|hit) for ",
    # ID prefix patterns (API responses)
    r"^chatcmpl-",
    r"^run-",
    r"^exp-",
    # SQL call pattern
    r"^CALL ",
    # Time period patterns
    r"^[0-9]+(mo|yr|wk|day|hr|min|sec)$",
    # Percentage patterns
    r"% used \($",
    r"% \($",
    r"^[0-9]+%$",
    # Newline prefix patterns
    r"^\\n(stderr|stdout|Description):",
    r"^\\n# MCLI completion",
    r"^\\n🧪 Testing ",
    r"^\\n📝 Test ",
    r"^\\n🚀 Starting ",
    r"^\\n🎉 Setup complete",
    r"^\\n📄 ",
    # Rich progress format
    r"^\[progress\.(description|percentage|elapsed)\]",
    # Rich patterns
    r"^\[yellow\]Editor exited",
    r"^\[red\]Syntax error",
    r"^\[green\]Updated command:",
    # Celebratory/decorative suffixes
    r"! 🚀$",
    r"\): $",
    # Execute patterns
    r"^execute $",
    # Pip install pattern (extended)
    r"^pip install [a-z]",
    # Stock/trading patterns
    r"^Could not extract stock features:",
    # Multi-line code template patterns (containing common template markers)
    r"^\\n\\n# Your command",
    r"command with name: \{name\}",
    r"^\.\n    \"\"\"\n",
    r"^\\nimport click\\n",
    r"from typing im",
    # Stream suffix patterns
    r"^:(stdout|stderr|info|error|debug)$",
    # Shutdown/status patterns
    r", shutting down\.\.\.$",
    r", needs sync$",
    # PID patterns
    r" with PID $",
    # Version patterns
    r" version $",
    # Success suffix patterns
    r" (updated|created|deleted|removed|added|saved) successfully!?$",
    r" revoked successfully$",
    # Lockfile patterns
    r" to lockfile\.$",
    r" times$",
    # Response emoji
    r"^🤖 Response:",
    # Count suffix patterns
    r" old cache files$",
    r" (records|jobs|items|files|lines) (to|from|in) $",
    r" lines\)$",
    # Unit suffix patterns
    r" (MHz|GHz|KB|MB|GB|TB|FPS)[\)\]]?$",
    r" MB \| Efficiency:$",
    # Ready/running patterns
    r" is (ready|already) (to use|running)\.?$",
    # Directory patterns
    r" is a (directory|file)$",
    # Context/namespace patterns
    r" (in context|for namespace|for user|for command) $",
    # Frame/video patterns
    r" frames to video at $",
    # Files patterns
    r" files (from|to|in) $",
    # Failed/exists suffix patterns
    r" (failed|exists|missing)$",
    r" does not (exist|match)$",
    # SQL from multi-line strings
    r"^\s+SELECT ",
    r"^\s+FROM ",
    r"^\s+WHERE ",
    r"^\s+JOIN ",
    r"^\s+ORDER BY",
    r"^\s+GROUP BY",
    r"^\s+LIMIT ",
    # More newline patterns
    r"^\\n\s+SELECT ",
    # More Rich patterns
    r"^\[cyan\].*\[/cyan\]$",
    r"^\[magenta\].*\[/magenta\]$",
    r"^\[white\].*\[/white\]$",
    # Colon suffix patterns for labels
    r"^[A-Z][a-z]+:$",  # Single word labels like "Name:", "Status:"
    # More prefixes
    r"^Sending ",
    r"^Waiting ",
    r"^Retrying ",
    r"^Validating ",
    r"^Generating ",
    r"^Executing ",
    r"^Compiling ",
    r"^Building ",
    r"^Deploying ",
    r"^Configuring ",
    r"^Initializing ",
    r"^Finalizing ",
    r"^Cleaning ",
    r"^Checking ",
    r"^Updating ",
    r"^Downloading ",
    r"^Uploading ",
    r"^Parsing ",
    r"^Reading ",
    r"^Writing ",
    r"^Closing ",
    r"^Starting ",
    r"^Stopping ",
    r"^Restarting ",
    r"^Terminating ",
    r"^Launching ",
    r"^Connecting ",
    r"^Disconnecting ",
    r"^Subscribing ",
    r"^Unsubscribing ",
    r"^Publishing ",
    r"^Querying ",
    r"^Searching ",
    r"^Filtering ",
    r"^Sorting ",
    r"^Aggregating ",
    r"^Computing ",
    r"^Calculating ",
    r"^Analyzing ",
    r"^Training ",
    r"^Testing ",
    r"^Evaluating ",
    r"^Predicting ",
    r"^Classifying ",
    r"^Clustering ",
    r"^Embedding ",
    r"^Encoding ",
    r"^Decoding ",
    r"^Encrypting ",
    r"^Decrypting ",
    r"^Hashing ",
    r"^Verifying ",
    r"^Authenticating ",
    r"^Authorizing ",
    r"^Refreshing ",
    r"^Caching ",
    r"^Invalidating ",
    r"^Migrating ",
    r"^Rollback ",
    r"^Committing ",
    r"^Pushing ",
    r"^Pulling ",
    r"^Merging ",
    r"^Rebasing ",
    r"^Cloning ",
    r"^Forking ",
    r"^Branching ",
    r"^Tagging ",
    r"^Releasing ",
    # More newline prefix patterns
    r"^\\nstderr:",
    r"^\\nstdout:",
    r"^\\nDescription:",
    r"^\\n# MCLI",
    r"^\\n📄 ",
    # Markdown/emoji streaming pattern
    r"^📡 \*\*Streaming",
    # Timer patterns
    r"^⏱️",
    # Shell type patterns
    r" \(Shell\):",
    # Bytes/size patterns
    r" bytes\)$",
    r" bytes →",
    r" (directories|command\(s\))$",
    # Hardware info label patterns (indented)
    r"^\s+(GPU|CPU|Memory)( Memory| Frequency)?:",
    r"^\s+Uptime:",
    # Accuracy/score patterns
    r"^\s+Accuracy Score:",
    # Location migration patterns
    r"^\s+(Old|New) location:",
    r"^\s+Files to migrate:",
    # Target/Source with Rich markup
    r"^\s+Target: \[cyan\]",
    r"^\s+Source: \[cyan\]",
    # Tags pattern with pipe
    r" \| Tags:",
    # at suffix
    r" at $",
    # Context flag
    r" --context $",
    # Ellipsis patterns
    r"^\.\.\.$",
    r" \.\.\.+$",
    # sudo commands (system admin)
    r"^\s+sudo ",
    # pip install standalone
    r"^pip install $",
    # Failed to execute standalone
    r"^Failed to execute $",
    # Job standalone
    r"^Job $",
    # Port/Host/Device labels (indented)
    r"^\s+(Port|Host|Device|Error|Parameters|Type):",
    r"^\s+Data [Dd]irectory:",
    # String: osascript pattern (nested output)
    r"^\s+String: ",
    # DID patterns with extra spaces
    r"^\s+(Space|Agent) DID:\s+",
    # Emoji labels with indentation
    r"^\s+📄 ",
    # Template instruction patterns
    r"^Write your (Python|Shell|Bash) ",
    # Video/Image model labels
    r"^(Video|Image|Audio) Models$",
    # Snake case identifiers (database columns, config keys)
    r"^[a-z]+_[a-z_]+$",  # e.g., transaction_size_std, processed_trading_data
    # Token error messages
    r"^Token must be ",
    # Not found patterns
    r"^(Portfolio|Trade|Stock|User|Item) not found$",
    # Package file names
    r"^(package|composer|Cargo|Gemfile|requirements)\.(json|toml|lock|txt)$",
    # Server/daemon names
    r"^(redis|postgres|mysql|mongo|nginx|apache)-server$",
    # Shell workflow pattern
    r"^Shell workflow command$",
    # Efficiency pattern with pipe
    r" MB \| Efficiency:",
    # Command count pattern
    r" command\(s\):$",
    # Newline patterns with real newlines (not escaped)
    r"^\n(stderr|stdout|Description):",
    r"^\n# MCLI",
    r"^\n🧪 Testing",
    r"^\n📝 Test",
    r"^\n🚀 Starting",
    r"^\n🎉 Setup complete",
    r"^\n📄 ",
    # Tokenizer/model files
    r"^tokenizer\.(json|model)$",
    r"^(config|model|vocab)\.(json|txt|bin)$",
    # osascript nested pattern
    r'^\s+String: "osascript',
    # Package/Install messages
    r"^Package not installed$",
    r"^Not available$",
    # Operation status patterns
    r"^Operation (success|message|status)",
    r"^Number of (Files|Items|Records)$",
    # No secrets/items patterns
    r"^No (secrets|items|commands|files|changes|code|command code) (to export|found|detected|provided)",
    r"^No (secrets|items|commands|files|changes|code) (to export|found|detected)$",
    # Log file patterns
    r"^mcli\*\.(log|txt|json)$",
    # Health check patterns
    r"^Health check endpoint\.$",
    # Token patterns
    r"^(getting|refreshing|validating) token$",
    # File Type label
    r"^File Type$",
    # Example prompts (for demos/tests)
    r"^Explain .* in simple terms\.$",
    # Editor terminal message
    r"^Editor requires an interactive terminal",
    # DID key patterns
    r"^did:(key|web|ion|ethr):",
    # Cancelled patterns
    r"(cancelled|canceled)\.$",
    r"^Deletion (cancelled|canceled)\.$",
    # Current directory
    r"^current directory$",
    # WebSocket patterns
    r"^Connect to WebSocket\.$",
    # Command creation patterns
    r"^Command (creation|code) (cancelled|captured|created)",
    r"^Command already exists\. Override\?$",
    # HTTP headers (CORS, Cache, Auth)
    r"^Cache-Control$",
    r"^Access-Control-Allow-(Origin|Headers|Methods)$",
    r"^X-[A-Za-z-]+$",  # Custom headers
    # Authentication patterns
    r"^Authentication required$",
    # API endpoint description
    r"^API endpoints for ",
    # SQLAlchemy relationship patterns
    r"^(all|save-update|merge),? ?delete-orphan$",
    # Code block markers
    r"^<string>$",
    r"^```+$",
    r"^\*{2,}$",
    # Glob patterns
    r"^\*\.(py|js|ts|json|yaml|toml|md)$",
    # Server stopped patterns
    r"^\\n🛑 Server stopped$",
    r"^\\nCommand creation cancelled",
    # More glob patterns
    r"^[a-z]+\*\.(log|txt|json)$",
    # Shell detection patterns
    r"^(ZSH|Bash|Fish|Sh) shell detected$",
    # System uptime patterns
    r"^Your system has been up for ",
    # X window patterns
    r'^xdotool (type|click|mousemove) "',
    r"^xdg-open ",
    # Performance comparison
    r"x faster with ",
    # Wrote/Write patterns
    r"^Wrote (new|updated) ",
    r"^Write a (Python|JavaScript|Bash|Shell) ",
    r"^write $",
    # Would you like patterns
    r"^Would you like to ",
    r"^Would (open|you) ",
    # Workflows directory patterns
    r"^Workflows directory does not exist:",
    r"^Workflow command$",
    # Natural language queries
    r"^(where am i|what time|how are you|who are you)$",
    # Example questions
    r"^What are the (benefits|advantages) of ",
    # Welcome patterns
    r"^Welcome to ",
    # Warning: patterns
    r"^Warning: (Error|Could not|Config file) ",
    # Cache warming patterns
    r"^(Warming|Warmed) (cache|up) ",
    # Video patterns
    r"^Video(-to-Video| Generation|processed|generation)",
    # Vectorized patterns
    r"^Vectorized (search|query) (failed|succeeded):",
    # Value pattern
    r"^Value $",
    # Validation patterns
    r"^Validation failed for ",
    # Model type labels
    r"^(VAE|CLIP|BERT|GPT|LLM|CNN|RNN) Models$",
    # Version patterns
    r"^v[0-9]+\.",
    # Using slow/fallback patterns
    r"^Using (slow|fast|existing|default) ",
    # More newline patterns
    r"^\\nCommand creation cancelled",
    r"^\\n🛑 Server",
    # Server stopped (actual newline)
    r"^\n🛑 Server stopped$",
    r"^\nCommand creation cancelled",
    # Write/create file patterns
    r"^Writing to ",
    # Using config patterns
    r"^Using config from ",
    # User patterns
    r"^user:$",
    r"^User account is ",
    # Use flag patterns
    r"^Use --[a-z]+ to ",
    # URL/URI labels
    r"^(URL|URI): $",
    # Uploaded patterns
    r"^Uploaded to ",
    # Update patterns
    r"^Update (secrets|commands|config) ",
    # Unsupported patterns
    r"^Unsupported (order type|optimization|LLM provider|HTTP method|file|backend|format)",
    # Unloading patterns
    r"^Unloading (model|resource) ",
    # Unknown patterns
    r"^Unknown (language|data type|backend|error|format) ",
    # Unhandled exception
    r"^Unhandled exception",
    # Warmed patterns
    r"^Warmed $",
    # Video patterns
    r"^Video (processed|generation) (successfully|complete)",
    # Triggered patterns
    r"^Triggered (retraining|update|sync) for ",
    r"^(Take profit|Stop loss) triggered for ",
    # Translating patterns
    r"^Translating (text|document) ",
    # Trading patterns
    r"^trading\.(data|config)\.",
    r"^Trade PnL$",
    r"^Total position size ",
    r"^Strategy based on ",
    # Trace patterns
    r"^(Trace|System trace) logging to:",
    # Model name patterns
    r"^(tinyllama|llama|phi|gemma|mistral)-[0-9a-z.-]+$",
    r"^tokenizer_config\.json$",
    # This is a patterns
    r"^This is a (single command|response|Click group)",
    # Thanks patterns
    r"^Thanks for ",
    # TF-IDF patterns
    r"^TF-IDF (extension|embedding|Cache) ",
    # Text classification/generation
    r"^text-(generation|classification|embedding)$",
    r"^Text \($",
    # Test patterns
    r"^test-",
    r"^test content ",
    r"^Test $",
    # Terminal patterns
    r"^terminal $",
    # Target directory patterns
    r"^Target directory ",
    # System patterns
    r"^system (time|specs|information|info|status)$",
    r"^System (trace|status) ",
    # Successfully patterns
    r"^Successfully (processed|migrated|connected|added|loaded|updated) ",
    # Store/Stock patterns
    r"^Store path saved to ",
    r"^storage space$",
    r"^Stock data update failed:",
    r"^stock_data\.(ticker|price)$",
    # Step patterns
    r"^Step $",
    # stdout/stderr format patterns
    r"^(stdout|stderr)> %s$",
    # API error patterns
    r"^(Ollama|OpenAI|Anthropic|LLM) (API )?[Ee]rror:",
    r"^AI (code generation|response) error:",
    # Code generation patterns
    r"^(just code|code only)$",
    # GB/MB patterns with context
    r"^GB (free|used)\)$",
    r"^GB\)$",
    # CPU patterns
    r"^CPU (usage is|is) (high|low)",
    # Command test patterns
    r"^Command test failed:",
    # Rich markup patterns with numbers
    r"^[0-9]+\. \[cyan\]",
    # Percent used pattern
    r"% used$",
    # Status/Tags with newline
    r"^\\n(Tags|Status|Description):",
    # Rich error patterns
    r"^\\n\[red\]",
    # Dim more patterns
    r"^\\n\[dim\]\.\.\. and ",
    # Yellow patterns
    r"^\[yellow\](Found|💡) ",
    # Screenshot patterns
    r"^\[cyan\]📸 Screenshot saved to:",
    # No context available
    r"^\(No (command|context|data) (context )?available\)$",
    # Numbered cyan patterns
    r"^\. \[cyan\]",
    # Phone/notification patterns
    r"^📱 You have ",
    # Test patterns with mcli
    r"^📋 Test: \[yellow\]mcli ",
    # Scheduled jobs patterns
    r" (scheduled jobs|job failures|active jobs)( running)?$",
    # Memory label
    r"^💾 Memory:",
    # Hours suffix
    r" hours\.$",
    # Kubernetes/kubectl patterns
    r"^kubectl (config|--context|apply|get|delete|patch)",
    r"^helm (install|uninstall|upgrade|list) ",
    r"^az (acr|aks|login) ",
    # Namespace patterns
    r"^Namespace is not set in ",
    r"^Creating namespace:",
    # K8s patterns
    r"^K8s (context|cluster|namespace) ",
    r"^Cannot (determine|connect) ",
    # Moving/Retrieving patterns
    r"^(Moving|Retrieving) (credentials|token|secret) ",
    # Setting pattern
    r"^Setting $",
    # Only dev context pattern
    r'^Only "dev" context is supported',
    # No context exists pattern
    r'^No context exists with the name:',
    # kubernetes package missing
    r"^kubernetes package is missing",
    # Failed to uninstall/install
    r"^Failed to (uninstall|install) helm",
    r"^Failed to retrieve token",
    # YAML template patterns
    r"^\\n(kind|apiVersion|metadata):",
    r"^\\ncat <<EOF",
    r'^{"imagePullSecrets":',
    # Run command suggestion
    r"; run `[a-z]+ (setup|init)`",
    # Suffix patterns
    r"-(secret|admin|config)$",
    r" (start|stop|restart)$",
    r" (patch|apply|delete) serviceaccount",
    r" helm chart$",
    # Proceed pattern
    r"\) and proceed forward\?$",
    # Context/namespace patterns
    r"\) & namespace to \(",
    # Simulator patterns
    r"^Simulator cleanup (error|completed)",
    # Shell command patterns
    r"^(show files in|navigate to|move to|list |go to|cd to|change to|run ) ",
    r"^Shell command (to execute|error)",
    r"^shell $",
    # GB available/usage patterns
    r"^GB (available|\()$",
    r"% usage$",
    # Error handling patterns
    r"^Error (taking screenshot|handling TextEdit|handling app|clearing caches|directory)",
    r"^(Current directory|Directory listing) error:",
    # Security block pattern
    r"^Command blocked for security",
    # First N of pattern
    r"^\\n\(showing first [0-9]+ of ",
    # Contains/Recommendations patterns
    r"^\\n📁 Contains:",
    r"^📋 Recommendations:",
    # Space freed patterns
    r"^💾 (Total space|RAM):",
    r"^🧹 Simulator cleanup completed",
    # MB/items suffix
    r" MB of storage$",
    r" items\)$",
    # osascript pattern
    r'^osascript -e \'',
    # Windows start pattern
    r'^start "" "',
    # save front document
    r"^save front document",
    # psutil pattern
    r"^psutil library not available$",
    # PowerShell patterns
    r'^powershell -Command "',
    # pkill pattern
    r"^pkill -f ",
    # Permission denied
    r"^Permission denied accessing:",
    # gtk-launch pattern
    r"^gtk-launch ",
    # Get system info patterns
    r"^Get (system information|memory usage|disk usage)$",
    # Flush DNS
    r"^Flush DNS cache$",
    # Disk patterns
    r"^(Critical: )?Disk ",
    # Could not patterns
    r"^Could not (open|clear|clean) ",
    # Clear patterns
    r"^Clear (old temp files|)$",
    r"^Cleaned ",
    # Changed directory
    r"^Changed to directory:",
    # Cleanup recommended
    r"% full - cleanup recommended$",
    # AppleScript tell patterns
    r'^\\n\s+tell application "',
    r"^\\n\s+end tell",
    r"^\(path to desktop as string\)",
    # String: osascript nested pattern (more specific)
    r'^\s+String: "osascript',
    # Environment validation
    r"^Environment must be one of ",
    r"^Ensured directory exists:",
    # Validation patterns
    r"^\\nValidation (working|failed):",
    # Configuration labels
    r" Configuration:$",
    r"^\s+(Redis|Model|Database|API|Server|Socket) (URL|Dir|Port|Host):",
    # Config help text patterns
    r"^(SSL|Token|Webhook|Redis|Pool|Model|Prometheus|Worker) [a-z]+",
    r"^(Number of|Requests per) ",
    r"^[A-Z][a-z]+ (API key|directory|path|timeout|port|host|password)$",
    # Secret placeholder
    r"^your-secret-key$",
    # Command discovery patterns
    r"^(Simple )?[Cc]ommand (discovery|initialization) ",
    r"^Rust extensions: ",
    # Request failed patterns
    r"^(OpenAI|Anthropic|Local|AI) (request|response) failed:",
    r"^Message processing failed:",
    # Matches pattern
    r"^matches $",
    # Initialized with
    r"^Initialized with ",
    # Failed to initialize
    r"^Failed to initialize ",
    # Daemon/Discovery check
    r"^(Daemon|Command) (check|discovery) failed:",
    # Command Knowledge patterns
    r"^\\n🧠 Command Knowledge:",
    # mcli command patterns
    r"^\. \*\*mcli ",
    # Count suffixes
    r", \.\.\. \(\+$",
    r" more\)$",
    r" (messages|commands|items|files) (with command context|indexed|available)$",
    r" (category|categories)$",
    # Relevance/Category/Example/Score labels
    r"^\s+(Relevance|Example|Category|Score):",
    r"^\s+\(Score:",
    # Name/didn't find patterns
    r'^\s+String: "(name|I didn\'t find)',
    r'^\\n🔍 \*\*Commands matching',
    # Help suggestion pattern
    r"^You can get more help with:",
    # Show status pattern
    r"^Show (comprehensive|system|full) status",
    # State pattern
    r"^State $",
    # Started patterns
    r"^Started (process|command|async|file watcher) ",
    # SSE connection
    r"^SSE connection error:",
    # Slow task
    r"^Slow task step:",
    # Slack alert
    r"^SLACK ALERT:",
    # Skipping patterns
    r"^Skipping (test|markdown|duplicate|disabled|invalid) ",
    # Simulator patterns
    r"^simulator data$",
    r"^Simulated (market|trade|order) ",
    # Simple hash
    r"^Simple hash embedding failed:",
    # Show files
    r"^show files$",
    # Shell linting
    r"^Shell (linting|command) ",
    # SHA patterns
    r"^sha[0-9]+:",
    r"^SHA[0-9]+-[0-9]+\(stdin\)=",
    # setup.py
    r"^setup\.py$",
    # Settings patterns
    r"^Settings:\\n",
    # set-url pattern
    r"^set-url$",
    # Session patterns
    r"^Session $",
    # Serving on
    r"^Serving on ",
    # Sentence transformers
    r"^Sentence transformers embedding failed:",
    # Sent stop signal
    r"^Sent stop signal to ",
    # Selecting from
    r"^Selecting from ",
    # Secrets Store patterns
    r"^Secrets (Store|store|pulled) ",
    # Screen capture
    r"^screen capture$",
    # Save anyway
    r"^Save anyway\?$",
    # Status suffixes
    r"^s\.\.\.$",
    r"^s, Status: $",
    # Rust patterns
    r"^Rust (TF-IDF|file watcher|extensions|command matcher) ",
    r"^Rust extensions (not available|loaded successfully)",
    # Runtime tracing
    r"^Runtime tracing enabled",
    # Running patterns
    r"^Running (experiment|DVC|batch|backtest|test|pipeline) ",
    r"^Runnable workflows for ",
    r"^Run make ",
    r"^run $",
    # Risk patterns
    r"^Risk(-free rate| parity| check) ",
    # Retrieving patterns
    r"^Retrieving from ",
    r"^Retrieved from ",
    # Resuming/Results patterns
    r"^Resuming (training|job|task) from:",
    r"^Results saved to:",
    r"^Restored to state ",
    # Response/Request patterns
    r"^Response $",
    r"^Request $",
    # Resource not found
    r"^Resource not found$",
    # Report patterns
    r"^Report (saved|generation) ",
    # Removing patterns
    r"^Removing (orphaned|model|old|cached) ",
    r"^remove $",
    # Registry patterns
    r"^Registry (upload|download) failed:",
    # Registering/Registered patterns
    r"^Registering (single|API|command) ",
    r"^Registered (shell|npm|notebook|model|make|handler|custom|command|API) ",
    r"^Registered $",
    r"^register_command_as_api called",
    r"^Register a new user\.$",
    # Refresh patterns
    r"^Refresh (access token|session|cache)",
    # Reducing patterns
    r"^Reducing (flicker|memory|cpu)",
    # Redis URL
    r"^Redis URL: $",
    # Recursively patterns
    r"^Recursively (processing|scanning) ",
    # Recreating patterns
    r"^Recreating (video|audio|image) ",
    # Config/model files
    r"^recommendation_config\.joblib$",
    r"^pytorch_model\.bin$",
    # rc format pattern
    r"^rc\s+> %s$",
    # Rate limit
    r"^Rate limit exceeded for ",
    # ram usage
    r"^ram usage$",
    # RAG system
    r"^RAG system initialized",
    # Query required
    r"^Query is required$",
    # PyTorch pattern
    r"^PyTorch not available$",
    # PyPDF/PyMuPDF patterns
    r"^PyPDF2 extraction failed:",
    r"^PyMuPDF extraction failed:",
    # python patterns
    r"^python $",
    r"^Python [0-9]",
    r"^Python (TF-IDF|execution) (benchmark |)failed:",
    # public cache header
    r"^public, max-age=",
    # Pulled patterns
    r"^Pulled (image|from remote) ",
    r"^Pulled $",
    # Providing patterns
    r"^Providing (file|path|API) ",
    # Processing patterns
    r"^Processing (Supabase|politician|frame|failed|completed|Click|batch) ",
    # Process patterns
    r"^Process (manager|ID|not found)[ :]",
    r"^processes\.db$",
    r"^proc-$",
    # Price patterns
    r"^Price \(\$\)$",
    # Preprocessed patterns
    r"^Preprocessed ",
    # Prepared patterns
    r"^Prepared ",
    # Prediction patterns
    r"^Prediction not found$",
    # Possible issue patterns
    r"^Possible issue with the ",
    # Position patterns
    r"^Position size \(",
    # Portfolio patterns
    r"^Portfolio (Metrics|value|allocation)",
    # politician patterns
    r"^politician\.data\.updated$",
    # Plugin patterns
    r"^Plugin (directory|registered|loaded) ",
    # Placed order
    r"^Placed order ",
    # PID patterns
    r"^PID (file|found):?",
    # Permission patterns
    r"^Permission denied\. Required:",
    # Performance patterns
    r"^Performance (chart|report|test) ",
    # PDF patterns
    r"^PDF (processing service|file not found)[ :]",
    # Pattern patterns
    r"^Pattern (invalidation|matching|found) ",
    # Password patterns
    r"^Password must (contain|be) ",
    # params.yaml
    r"^params\.yaml$",
    # Paper trade
    r"^Paper trade executed:",
    # Output saved
    r"^Output saved to:",
    # OS patterns
    r"^OS: $",
    # Order patterns
    r"^Order (violates|placed|executed|cancelled|failed) ",
    # Optimizing patterns
    r"^Optimizing (portfolio|model|parameters) ",
    # Optimization patterns
    r"^Optimization (failed|completed|started) ",
    # Operation patterns
    r"^Operation (result|failed|completed|cancelled)",
    # Opening patterns
    r"^Opening in ",
    # npm patterns
    r"^npm scripts from ",
    r"^npm (install|run|test) ",
    # Nothing to patterns
    r"^Nothing to (migrate|process|commit|sync)[ :]",
    # Notebook patterns
    r"^Notebook (file|saved|loaded|created) ",
    # Note: DVC patterns
    r"^Note: DVC (push|pull) failed ",
    # not set
    r"^not set$",
    # Not found
    r"^Not found$",
    # No patterns
    r"^No (targets|shebang|scripts|remote|prompt|help|frames|files|Click|changes) ",
    # navigate/move patterns
    r"^navigate to$",
    r"^move to$",
    # Multi-objective patterns
    r"^Multi-objective (optimization|search) ",
    # Motion analysis
    r"^Motion analysis (complete|failed)",
    # Monte Carlo
    r"^Monte Carlo (Simulation|simulation|analysis)[ :]",
    # model files
    r"^model\.pkl$",
    r"^model:$",
    r"^model_service\.pid$",
    # MLflow patterns
    r"^MLflow (URI|tracking) ",
    # ml-processor
    r"^ml-processor$",
    # ML system
    r"^ML (system|model|pipeline) ",
    # Politician names (used in scraper tests/examples)
    r"^(Mitch McConnell|Kevin McCarthy|Nancy Pelosi|Chuck Schumer)$",
    # Missing patterns
    r"^Missing required (columns|fields|parameters)[ :]",
    # Metadata patterns
    r"^Metadata (saved|loaded|retrieved) ",
    # Merged patterns
    r"^Merged ",
    # memory usage
    r"^memory usage$",
    # mcli patterns
    r"^mcli\.(workflow|token|fish|self|app)",
    r"^mcli-registry-$",
    r"^mcli-$",
    r"^MCLI (version|Model|ML) ",
    r"^mcli version ",
    # Max Sharpe
    r"^Max Sharpe Ratio:",
    # Make targets
    r"^Make targets from ",
    # Made patterns
    r"^Made ",
    # lsh patterns
    r"^lsh\.(supabase|job)\.",
    r"^LSH (job|API)[ :]",
    # LoRA Models
    r"^LoRA Models$",
    # Lockfile patterns
    r"^Lockfile not found:",
    # Local patterns
    r"^Local (commands|repository|models) ",
    # Loading patterns
    r"^Loading (notebook|lazy|existing|model|config) ",
    # List all
    r"^List all (available|models|commands)",
    r"^list $",
    # lightweight_client.py
    r"^lightweight_client\.py$",
    # Lazily loaded
    r"^Lazily loaded (group|command):",
    # Keeping manual JSON
    r"^Keeping manual JSON:",
    # jupyter-nbconvert
    r"^jupyter-nbconvert$",
    # JSON missing
    r"^JSON missing for ",
    # Job patterns
    r"^Job\(id=$",
    r"^Job (timed out|ID|execution|started|completed|failed) ",
    # IPFS patterns
    r"^IPFS (upload|download|storage) ",
    # Invalid patterns
    r"^Invalid (transaction|STORAGE_BACKEND|refresh|MCLI_TRACE|JSON|date|cron) ",
    # Internal server
    r"^Internal server error:",
    # Insufficient patterns
    r"^Insufficient (historical|cash|balance|data) ",
    # Initialized patterns
    r"^Initialized (git|DVC|mlflow|redis|database|model) ",
    # Initialize patterns
    r"^Initialize (SQLite|Redis|DVC|mlflow|database) ",
    # Initial Capital
    r"^Initial [Cc]apital:",
    # Image info
    r"^Image info for ",
    # If the email exists
    r"^If the email exists",
    # Hunyuan patterns
    r"^Hunyuan(Video|Image|Model)",
    # HTTP error
    r"^HTTP error ",
    # HTML intermediate
    r"^HTML intermediate failed:",
    # how much patterns
    r"^how much (space|ram|memory|cpu|disk)$",
    # Generic "Failed to" patterns (covers many error messages)
    r"^Failed to (record|read|push|pull|place|parse|optimize|migrate|manage|log|list|kill|import|generate|fetch|extract|export|execute|estimate|enable|drop|disable|decrypt|decode|convert|compute|compare|clone|clear|cleanup|check|calculate|build|authenticate|analyze|add)",
    # Additional Failed to patterns
    r"^Failed to (save|send|serialize|set|start|stop|submit|sync|terminate|transfer|transform|update|upload|validate|verify|write|create|delete|download|edit|get|handle|initialize|install|invoke|load|locate|lock|lookup|map|match|merge|modify|move|open|parse|patch)",
    # More Failed to patterns
    r"^Failed to (register|remove|retrieve|run|simulate|store)",
    # High outlier
    r"^High outlier ratio detected:",
    # Hello patterns
    r"^Hello, $",
    # Health check
    r"^Health check (failed|passed|running)[ :]",
    # Hash patterns
    r"^Hash (mismatch|computed|stored) ",
    # hardware info
    r"^hardware info$",
    # go to
    r"^go to$",
    # Global (user-wide)
    r"^Global \(user-wide\)$",
    # Git patterns
    r"^Git (repository|init|clone|checkout|push|pull) ",
    r"^git (checkout|clone|pull|push|status) ",
    # getting url
    r"^getting url$",
    # Get a database
    r"^Get a (database|redis|cache) ",
    # Generated patterns
    r"^Generated (response|Redis|JSON|AI|model|report|config|file|output) ",
    # gemma patterns
    r"^gemma[0-9]+n-[0-9]+b$",
    # GB free
    r"^GB free\\n$",
    # Force killing
    r"^Force killing (Redis|process|job) ",
    # for repository
    r"^for repository:",
    # Flushed
    r"^Flushed ",
    # Final patterns
    r"^Final (Validation|feature|accuracy|loss|score) ",
    # File watcher
    r"^File watcher (monitoring|extension|started|stopped)[ :]",
    # File is not
    r"^File is not (executable|readable|writable):",
    # feature files
    r"^feature_importance\.joblib$",
    # Feature patterns
    r"^Feature (selection|engineering|extraction|importance) ",
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
    # Command editor/creation messages
    "Opening ",
    "Editor exited with error. Command creation cancelled.",
    "Error opening editor: ",
    "Custom command already exists: ",
    "Command creation aborted.",
    "Using shell: ",
    " (from $SHELL environment variable)",
    "Using shell template for command: ",
    "Using Python template for command: ",
    "Opening editor for command: ",
    "Created portable custom command: ",
    "[green]Created portable custom command: ",
    ") [Scope: ",
    "store.conf",
    "Failed to initialize store: ",
    "Failed to get status: ",
    "Command not found: ",
    "Unknown error",
    "Language: ",
    "Group: ",
    " is not available",
    ") [",
    "\n# ",
    # Process/system info patterns
    "PID: ",
    "Processing ",
    "Control ",
    "Directory does not exist: ",
    "Execute: ",
    "Memory: ",
    "Uptime: ",
    "   Type: ",
    "   Memory: ",
    "   Process ID: ",
    "Task ",
    " stocks",
    'tell application "',
    # Version/CLI patterns
    "--version",
    # Migration/completion messages
    "Failed to create space: ",
    "Failed to select space: ",
    "✅ Completion installed to ",
    "Migration failed: ",
}

# Regex pattern for constant-like names (ALL_CAPS)
CONSTANT_LIKE_PATTERN = r"^[A-Z][A-Z0-9_]*$"

# Regex pattern for identifier-like names
IDENTIFIER_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
