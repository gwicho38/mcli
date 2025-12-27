"""UI message constants for mcli.

This module defines all user-facing messages used throughout the mcli application.
Using these constants ensures consistency in user communication and makes
internationalization easier in the future.
"""


class ErrorMessages:
    """Error message constants."""

    EDITOR_NOT_FOUND = (
        "No editor found. Please set the EDITOR environment variable or install vim/nano."
    )
    CONFIG_NOT_FOUND = (
        "Config file not found in $MCLI_CONFIG, $HOME/.config/mcli/config.toml, or project root."
    )
    COMMAND_NOT_FOUND = "Command '{name}' not found"
    COMMAND_NOT_AVAILABLE = "Command {name} is not available"
    GIT_COMMAND_FAILED = "Git command failed: {error}"
    FILE_NOT_FOUND = "File not found: {path}"
    DIRECTORY_NOT_FOUND = "Directory not found: {path}"
    INVALID_COMMAND_FORMAT = "Invalid command format"
    PERMISSION_DENIED = "Permission denied: {path}"
    NETWORK_ERROR = "Network error: {error}"
    API_ERROR = "API error: {error}"
    DATABASE_ERROR = "Database error: {error}"
    IMPORT_ERROR = "Failed to import: {module}"
    INVALID_CONFIG = "Invalid configuration: {error}"
    MISSING_REQUIRED_FIELD = "Missing required field: {field}"


class SuccessMessages:
    """Success message constants."""

    INITIALIZED_GIT_REPO = "Initialized git repository at {path}"
    COMMAND_STORE_INITIALIZED = "Command store initialized at {path}"
    CREATED_COMMAND = "Created portable custom command: {name}"
    SAVED_TO = "Saved to: {path}"
    UPDATED_SUCCESSFULLY = "Successfully updated {item}"
    DELETED_SUCCESSFULLY = "Successfully deleted {item}"
    COPIED_SUCCESSFULLY = "Successfully copied {source} to {dest}"
    INSTALLED_SUCCESSFULLY = "Successfully installed {item}"
    UNINSTALLED_SUCCESSFULLY = "Successfully uninstalled {item}"
    COMMAND_COMPLETED = "Command completed successfully"
    FILE_CREATED = "Created file: {path}"
    DIRECTORY_CREATED = "Created directory: {path}"


class WarningMessages:
    """Warning message constants."""

    NO_CHANGES = "No changes to commit"
    NO_REMOTE = "No remote configured or push failed. Commands committed locally."
    ALREADY_EXISTS = "{item} already exists"
    DEPRECATED_FEATURE = "{feature} is deprecated and will be removed in {version}"
    SKIPPED = "Skipped: {reason}"
    PARTIAL_SUCCESS = "Partially successful: {details}"
    RATE_LIMIT_WARNING = "Approaching rate limit for {service}"
    LARGE_FILE_WARNING = "Large file detected: {path} ({size})"


class InfoMessages:
    """Informational message constants."""

    COPYING_COMMANDS = "Copying commands from {source} to {dest}..."
    NO_CHANGES_TO_COMMIT = "No changes to commit"
    LOADING = "Loading {item}..."
    PROCESSING = "Processing {item}..."
    CONNECTING = "Connecting to {service}..."
    FETCHING = "Fetching {item}..."
    BUILDING = "Building {item}..."
    TESTING = "Testing {item}..."
    DEPLOYING = "Deploying {item}..."
    CLEANING = "Cleaning {item}..."
    ANALYZING = "Analyzing {item}..."
    VALIDATING = "Validating {item}..."


class PromptMessages:
    """User prompt constants."""

    CONFIRM_DELETE = "Are you sure you want to delete {item}?"
    CONFIRM_OVERWRITE = "File {path} already exists. Overwrite?"
    ENTER_VALUE = "Enter {field}:"
    SELECT_OPTION = "Select an option:"
    CONTINUE = "Continue?"


class ChatMessages:
    """Chat module message constants."""

    # System prompts
    DEFAULT_SYSTEM_PROMPT = (
        "You are the MCLI Chat Assistant, a helpful AI assistant for the MCLI tool."
    )
    FULL_SYSTEM_PROMPT = (
        "You are the MCLI Personal Assistant, an intelligent agent that helps "
        "manage your computer and tasks.\n\n"
        "I am a true personal assistant with these capabilities:\n"
        "- System monitoring and control (memory, disk, applications, cleanup)\n"
        "- Job scheduling and automation (cron jobs, reminders, recurring tasks)\n"
        "- Process management and command execution\n"
        "- File organization and system maintenance\n"
        "- Contextual awareness of ongoing tasks and system state\n\n"
        "I maintain awareness of:\n"
        "- Currently scheduled jobs and their status\n"
        "- System health and resource usage\n"
        "- Recent activities and completed tasks\n"
        "- User preferences and routine patterns\n\n"
        "I can proactively suggest optimizations, schedule maintenance, and "
        "automate repetitive tasks.\n"
        "I'm designed to be your digital assistant that keeps things running smoothly."
    )

    # Success messages
    MODEL_SERVER_RUNNING = "[green]✅ Lightweight model server already running[/green]"
    MODEL_LOADED = "[green]✅ Model {model} already loaded[/green]"
    MODEL_SERVER_STARTED = "[green]✅ Lightweight model server started with {model}[/green]"
    COMMAND_EXECUTED = "[green]✅ Command executed successfully[/green]"
    EXECUTING_COMMAND = "[green]Executing command:[/green] {command}"
    COMMAND_OUTPUT = "[green]Command Output:[/green]\n{output}"

    # Warning messages
    MODEL_NOT_LOADED = "[yellow]Model {model} not loaded, will auto-load on first use[/yellow]"
    STARTING_MODEL_SERVER = "[yellow]Starting lightweight model server...[/yellow]"
    SERVER_HEALTH_FAILED = "[yellow]⚠️ Server started but health check failed[/yellow]"
    COULD_NOT_DOWNLOAD_MODEL = "[yellow]⚠️ Could not download/load model {model}[/yellow]"
    COULD_NOT_START_SERVER = "[yellow]⚠️ Could not start lightweight model server: {error}[/yellow]"
    FALLING_BACK_REMOTE = "Falling back to remote models..."
    COMMAND_NO_CALLBACK = "[yellow]Command found but has no callback[/yellow]"
    TRY_COMMANDS_LIST = "[yellow]Try 'commands' to see available commands[/yellow]"

    # Error messages
    SERVER_THREAD_ERROR = "[red]Server thread error: {error}[/red]"
    CHAT_ERROR = "Chat error: {error}"
    ERROR_DISPLAY = "[red]Error:[/red] {error}"
    COMMAND_NOT_FOUND = "[red]Command '{name}' not found[/red]"
    FAILED_EXECUTE_COMMAND = "[red]Failed to execute command:[/red] {error}"
    ERROR_FINDING_COMMAND = "[red]Error finding command:[/red] {error}"
    ERROR_EXECUTING_COMMAND = "[red]Error executing command:[/red] {error}"
    NO_COMMAND_PROVIDED = "[red]No command provided after 'run'.[/red]"
    USAGE_LOGS = "[red]Usage: logs <process_id>[/red]"
    USAGE_INSPECT = "[red]Usage: inspect <process_id>[/red]"
    USAGE_STOP = "[red]Usage: stop <process_id>[/red]"
    USAGE_START = "[red]Usage: start <process_id>[/red]"

    # Info messages
    PERSONAL_ASSISTANT_HEADER = (
        "[bold green]MCLI Personal Assistant[/bold green] (type 'exit' to quit)"
    )
    USING_LIGHTWEIGHT_LOCAL = "[dim]Using lightweight local model: {model} (offline mode)[/dim]"
    USING_LOCAL_OLLAMA = "[dim]Using local model: {model} via Ollama[/dim]"
    USING_OPENAI = "[dim]Using OpenAI model: {model}[/dim]"
    USING_ANTHROPIC = "[dim]Using Anthropic model: {model}[/dim]"
    HOW_CAN_HELP = "How can I help you with your tasks today?"
    AVAILABLE_COMMANDS_HEADER = "\n[bold cyan]Available Commands:[/bold cyan]"
    EXIT_HINT = "\nUse 'exit' to quit the chat session"
    DAEMON_UNAVAILABLE = "Daemon unavailable, running in LLM-only mode. Details: {error}"
    COULD_NOT_FETCH_COMMANDS = (
        "Could not fetch commands from daemon: {error}. Falling back to LLM-only mode."
    )

    # Command help text
    HELP_COMMANDS = "• [yellow]commands[/yellow] - List available functions"
    HELP_RUN = "• [yellow]run <command> [args][/yellow] - Execute command in container"
    HELP_PS = "• [yellow]ps[/yellow] - List running processes (Docker-style)"
    HELP_LOGS = "• [yellow]logs <id>[/yellow] - View process logs"
    HELP_INSPECT = "• [yellow]inspect <id>[/yellow] - Detailed process info"
    HELP_START_STOP = "• [yellow]start/stop <id>[/yellow] - Control process lifecycle"
    HELP_SYSTEM_CONTROL = (
        "• [yellow]System Control[/yellow] - "
        "Control applications (e.g., 'open TextEdit', 'take screenshot')"
    )
    HELP_JOB_SCHEDULING = (
        "• [yellow]Job Scheduling[/yellow] - "
        "Schedule tasks (e.g., 'schedule cleanup daily', 'what's my status?')"
    )
    HELP_ASK_QUESTIONS = "• Ask questions about functions and codebase\n"

    # Execution keywords (for pattern matching)
    KEYWORD_CALL_THE = "call the"
    KEYWORD_EXECUTE_THE = "execute the"
    KEYWORD_RUN_THE = "run the"
    KEYWORD_EXECUTE_COMMAND = "execute command"
    KEYWORD_HELLO_WORLD = "hello world"
    KEYWORD_HELLO_WORLD_DASH = "hello-world"

    # Pattern matching strings
    PATTERN_COMMAND = " command"
    PATTERN_THE = "the "
    PATTERN_RUN = "run "
    PATTERN_SELF_PREFIX = "self."
    PATTERN_DOCKER_PS = "docker ps"
    PATTERN_LOGS = "logs "
    PATTERN_INSPECT = "inspect "
    PATTERN_STOP = "stop "
    PATTERN_START = "start "

    # Query patterns
    QUERY_LIST_COMMAND = "list command"
    QUERY_SHOW_COMMAND = "show command"
    QUERY_AVAILABLE_COMMAND = "available command"
    QUERY_WHAT_CAN_I_DO = "what can i do"

    # Command list display
    ERROR_DISCOVERING_COMMANDS = "[red]Error discovering commands: {error}[/red]"
    ERROR_SEARCHING_COMMANDS = "[red]Error searching commands: {error}[/red]"
    NO_COMMANDS_FOUND = "No commands found"
    NO_COMMANDS_MATCHING = "No commands found matching '[yellow]{query}[/yellow]'"
    AVAILABLE_COMMANDS_COUNT = "[bold]Available Commands ({count}):[/bold]"
    COMMAND_BULLET = "• [green]{name}[/green]"
    COMMAND_INACTIVE = "[INACTIVE] "
    COMMAND_MODULE = "  Module: {module}"
    COMMAND_TAGS = "  Tags: {tags}"
    AND_MORE = "[dim]... and {count} more[/dim]"

    # Config setup instructions
    CONFIG_PROVIDER_EXAMPLE = '  provider = "openai"'
    CONFIG_API_KEY_EXAMPLE = '  openai_api_key = "your-key-here"'
    CHECK_LLM_CONFIG = "Please check your LLM configuration in .env file"
    CREATE_MCLI_COMMAND = "I'll create a complete working MCLI command for you."
    COMMAND_NOT_EXIST_MARKER = "**[Command Does Not Exist]** "
    COPY_GENERATED_CODE = "1. Copy the generated code to a new Python file"
    SAVE_IN_MCLI_MODULE = "2. Save it in the appropriate MCLI module directory"
    TEST_COMMAND_STEP = "3. Test the command with: [yellow]mcli <your-command>[/yellow]"
    VERIFY_COMMAND_STEP = "4. Use [yellow]mcli commands list[/yellow] to verify it's available"
    AUTO_DISCOVERY_TIP = "[dim]Tip: Commands are automatically discovered when placed in the correct directories[/dim]"

    # Automated command creation messages
    NEXT_STEPS_HEADER = "[bold cyan]💡 Next Steps:[/bold cyan]"
    STARTING_AUTO_CREATION = "[bold blue]🤖 Starting automated command creation...[/bold blue]"
    GENERATING_CODE_STEP = "1. [cyan]Generating command code...[/cyan]"
    CREATING_FILE_STEP = "2. [cyan]Creating command file: {filename}[/cyan]"
    TESTING_COMMAND_STEP = "3. [cyan]Testing command: {name}[/cyan]"
    FAILED_GENERATE_CODE = "[red]❌ Failed to generate code. Falling back to code-only mode.[/red]"
    FAILED_PARSE_COMMAND = (
        "[red]❌ Could not parse command information. Showing generated code:[/red]"
    )
    FAILED_CREATE_FILE = "[red]❌ Failed to create command file.[/red]"
    COMMAND_CREATED_SUCCESS = "[bold green]✅ Command created successfully![/bold green]"
    COMMAND_FILE_PATH_GREEN = "📁 File: [green]{file_path}[/green]"
    COMMAND_USAGE_HINT = "🚀 Usage: [yellow]mcli {name} --help[/yellow]"
    COMMAND_TEST_HINT = "📋 Test: [yellow]mcli {name}[/yellow]"
    COMMAND_NEEDS_DEBUG = "[yellow]⚠️  Command created but may need debugging[/yellow]"
    COMMAND_FILE_PATH_YELLOW = "📁 File: [yellow]{file_path}[/yellow]"
    CHECK_FILE_HINT = "💡 Check the file and test manually"
    COMMAND_AVAILABLE = "[dim]Command is now available in MCLI![/dim]"
    COMMAND_WARNING_NOTE = "\n\n⚠️  **Note**: The command mentioned above does not exist in MCLI. To create this functionality, you would need to implement a new command. Would you like me to help you create it?"
    MCLI_COMMAND_NOT_EXIST = "\n\n⚠️  **Note**: 'mcli {cmd}' does not exist. Available commands can be listed with the 'commands' chat command."

    # Rich formatted file markers
    FILE_MARKER_GREEN = "[green]"
    FILE_MARKER_YELLOW = "[yellow]"

    # Additional keyword patterns
    KEYWORD_HELLOWORLD = "helloworld"

    # Process management messages
    USE_MCLI_COMMANDS_LIST = "[dim]Use 'mcli commands list' to see all commands[/dim]"
    MATCHING_COMMANDS_HEADER = "[bold]Matching Commands for '{search_term}' ({count}):[/bold]"
    COMMAND_FORMAT_GREEN = "• [green]{name}[/green]"
    COMMAND_FORMAT_WITH_LANG = "• [green]{name}[/green] ({language})"
    COMMAND_DESCRIPTION_ITALIC = "[italic]{description}[/italic]"
    MORE_RESULTS = "[dim]... and {count} more results[/dim]"

    # Daemon command listing
    NO_COMMANDS_DAEMON = "[yellow]No commands available through daemon[/yellow]"
    AVAILABLE_COMMANDS_HEADER = "[bold green]Available Commands ({count}):[/bold green]"
    COMMAND_FORMAT_CYAN = "• [cyan]{name}[/cyan]"
    MORE_COMMANDS_DAEMON = "[dim]... and {count} more commands[/dim]"
    USE_NATURAL_LANGUAGE = "[dim]Use natural language to ask about specific commands[/dim]"
    COMMAND_LIST_UNAVAILABLE = (
        "[yellow]Command listing not available - daemon may not be running[/yellow]"
    )
    TRY_START_DAEMON = "Try starting the daemon with: [cyan]mcli workflow daemon start[/cyan]"
    COULD_NOT_RETRIEVE_COMMANDS = "[yellow]Could not retrieve commands list[/yellow]"
    AVAILABLE_BUILTIN_COMMANDS = "Available built-in chat commands:"
    BUILTIN_COMMANDS = "• [cyan]commands[/cyan] - This command"
    BUILTIN_PS = "• [cyan]ps[/cyan] - List running processes"
    BUILTIN_RUN = "• [cyan]run <command>[/cyan] - Execute a command"
    BUILTIN_LOGS = "• [cyan]logs <id>[/cyan] - View process logs"
    BUILTIN_INSPECT = "• [cyan]inspect <id>[/cyan] - Detailed process info"
    BUILTIN_STARTSTOP = "• [cyan]start/stop <id>[/cyan] - Control process lifecycle"

    # Process list display
    NO_PROCESSES_RUNNING = "No processes running"
    PROCESS_LIST_HEADER = "[bold]CONTAINER ID   NAME           COMMAND                  STATUS    UPTIME     CPU      MEMORY[/bold]"
    PROCESS_LIST_ERROR = "[red]Error: Failed to get process list (HTTP {status_code})[/red]"
    DAEMON_CONNECTION_ERROR = "[red]Error connecting to daemon: {error}[/red]"

    # Process logs
    LOGS_HEADER = "[bold]Logs for {process_id}:[/bold]"
    STDOUT_LABEL = "[green]STDOUT:[/green]"
    STDERR_LABEL = "[red]STDERR:[/red]"
    NO_LOGS_AVAILABLE = "No logs available"
    PROCESS_NOT_FOUND = "[red]Process {process_id} not found[/red]"
    LOGS_FETCH_ERROR = "[red]Error: Failed to get logs (HTTP {status_code})[/red]"

    # Process inspect
    PROCESS_DETAILS_HEADER = "[bold]Process {process_id} Details:[/bold]"
    INSPECT_ERROR = "[red]Error: Failed to inspect process (HTTP {status_code})[/red]"

    # Process lifecycle
    PROCESS_STOPPED = "[green]Process {process_id} stopped[/green]"
    STOP_PROCESS_ERROR = "[red]Error: Failed to stop process (HTTP {status_code})[/red]"
    PROCESS_STARTED = "[green]Process {process_id} started[/green]"
    START_PROCESS_ERROR = "[red]Error: Failed to start process (HTTP {status_code})[/red]"

    # Containerized run
    CONTAINERIZED_COMMAND_STARTED = (
        "[green]Started containerized command '{name}' with ID {id}[/green]"
    )
    CONTAINERIZED_PROCESS_STARTED = "[green]Started containerized process with ID {id}[/green]"
    USE_LOGS_HINT = "Use 'logs <id>' to view output or 'ps' to see status"
    FAILED_START_COMMAND = "[red]Failed to start containerized command[/red]"
    FAILED_START_PROCESS = "[red]Failed to start containerized process[/red]"

    # Daemon startup
    STARTING_DAEMON = "[yellow]Starting MCLI daemon...[/yellow]"
    DAEMON_STARTED_SUCCESS = "[green]✅ MCLI daemon started successfully on {url}[/green]"
    DAEMON_WAITING = "[dim]Waiting for daemon to start... ({i}/10)[/dim]"
    DAEMON_FAILED_START = "[red]❌ Daemon failed to start within 10 seconds[/red]"
    TRY_MANUAL_DAEMON_START = (
        "[yellow]Try starting manually: mcli workflow api-daemon start[/yellow]"
    )
    COULD_NOT_START_DAEMON = "[red]❌ Could not start daemon: {error}[/red]"

    # Model pulling
    DOWNLOADING_MODEL = (
        "[yellow]Downloading model '{model_name}'. This may take a few minutes...[/yellow]"
    )
    MODEL_DOWNLOADED = "[green]✅ Model '{model_name}' downloaded successfully[/green]"
    MODEL_DOWNLOAD_FAILED = "[red]❌ Failed to download model '{model_name}': {error}[/red]"
    MODEL_DOWNLOAD_TIMEOUT = "[red]❌ Download of model '{model_name}' timed out[/red]"
    OLLAMA_NOT_FOUND = "[red]❌ Ollama command not found. Please install Ollama first:[/red]"
    BREW_INSTALL_OLLAMA = "  brew install ollama"
    MODEL_DOWNLOAD_ERROR = "[red]❌ Error downloading model '{model_name}': {error}[/red]"

    # LLM provider setup errors
    OLLAMA_NOT_INSTALLED = "[red]Error: ollama is not installed.[/red]"
    INSTALL_OLLAMA_LOCAL = "[yellow]For local model support, install ollama:[/yellow]"
    PIP_INSTALL_OLLAMA = "  pip install ollama"
    SWITCH_TO_OPENAI = "[yellow]Or switch to OpenAI by configuring:[/yellow]"

    # Model not found / lightweight server
    MODEL_NOT_FOUND_LIGHTWEIGHT = (
        "[yellow]Model '{model_name}' not found on lightweight server.[/yellow]"
    )
    ENSURING_LIGHTWEIGHT_SERVER = "[yellow]Ensuring lightweight model server is running...[/yellow]"
    MODEL_NOT_FOUND_PULLING = (
        "[yellow]Model '{model_name}' not found. Attempting to pull it...[/yellow]"
    )
    FAILED_AFTER_RESTART = "Failed to generate response after restarting lightweight server"
    FAILED_AFTER_PULL = "Failed to generate response after pulling model"
    OLLAMA_API_ERROR = "Ollama API error: {error}"

    # Connection / timeout errors
    OLLAMA_CONNECTION_ERROR = (
        "[red]Could not connect to Ollama. Please ensure Ollama is running:[/red]"
    )
    OLLAMA_SERVE_CMD = "  ollama serve"
    VISIT_URL = "  Visit: {url}"
    REQUEST_TIMEOUT = (
        "[yellow]Request timed out. The model might be processing a complex query.[/yellow]"
    )
    OPENAI_NOT_CONFIGURED = "[red]OpenAI API key not configured. Please set it in config.toml[/red]"
    UNSUPPORTED_LLM_PROVIDER = "Unsupported LLM provider: {provider}"

    # LLM error response
    LLM_ERROR_HEADER = "[red]Error:[/red] Could not generate LLM response"

    # Command creation mode UI
    COMMAND_CREATION_MODE_HEADER = (
        "[bold green]\U0001f6e0\ufe0f  Command Creation Mode[/bold green]"
    )
    CODE_ONLY_SELECTED = "[yellow]Code-only mode selected[/yellow]"
    CHOOSE_APPROACH = "[bold cyan]Choose your approach:[/bold cyan]"
    FULL_AUTOMATION_OPTION = (
        "1. [green]Full automation[/green] - I'll create, save, and test the command"
    )
    CODE_ONLY_OPTION = (
        "2. [yellow]Code only[/yellow] - I'll just generate code for you to implement"
    )
    CODE_ONLY_TIP = "[dim]Tip: You can also say 'code only' in your original request[/dim]"
    ENTER_CHOICE_PROMPT = "[bold cyan]Enter choice (1 or 2, default=1): [/bold cyan]"
    DEFAULTING_AUTOMATION = "Defaulting to full automation..."

    # Disk space suggestions
    DISK_FULL_WARNING = "Your disk is getting full! I can help you clear system caches."
    DISK_FULL_HINT = "Try: 'clear system caches' to free up space"
    DISK_HIGH_USAGE = "You're using quite a bit of disk space. Consider cleaning up."
    DISK_CLEANUP_HINT = "I can help with: 'clear system caches'"
    SIMULATOR_SPACE_WARNING = "You have {size:.1f}GB in iOS/watchOS simulators."
    SIMULATOR_CLEANUP_HINT = "Consider cleaning old simulator data if you don't need it."

    # Memory suggestions
    MEMORY_HIGH_WARNING = "Your memory usage is quite high!"
    MEMORY_CLOSE_APPS = "Consider closing unused applications to free up RAM."
    SWAP_HIGH_WARNING = "High swap usage detected - your system is using disk as memory."
    SWAP_SLOWDOWN_HINT = "This can slow things down. Try closing memory-intensive apps."
    MEMORY_MONITOR_HINT = "Want to monitor your system? Try: 'show system specs'"
    MEMORY_HIGH_SIMPLE = "Memory usage is high. Consider closing unused applications."
    RESTART_HINT = "Consider restarting to refresh system performance."
    CAN_HELP_WITH = "I can help you with:"
    CHECK_MEMORY_HINT = "- 'how much RAM do I have?' - Check memory usage"
    CHECK_STORAGE_HINT = "- 'how much disk space do I have?' - Check storage"
    CLEAR_CACHES_HINT = "- 'clear system caches' - Free up space"

    # Time-based suggestions
    LATE_NIGHT_MSG = "It's quite late! Consider taking a break."
    WORK_TIME_MSG = "It's work time! Stay productive."
    EVENING_MSG = "Good evening! Wrapping up for the day?"
    SCHEDULE_HINT = "I can also help you schedule tasks with the workflow system!"

    # Section headers
    SUGGESTIONS_HEADER = "\n[cyan]Suggestions:[/cyan]"
    MEMORY_TIPS_HEADER = "\n[cyan]Memory Tips:[/cyan]"
    SYSTEM_INSIGHTS_HEADER = "\n[cyan]System Insights:[/cyan]"
    TIME_TIPS_HEADER = "\n[cyan]Time Tips:[/cyan]"


class ModelServiceMessages:
    """Model service message constants."""

    # Model loading
    USING_DEVICE = "Using device: {device}"
    LOADING_MODEL = "Loading model: {model}"
    MODEL_ALREADY_LOADED = "Model {model} already loaded"
    MODEL_LOADED_SUCCESS = "Successfully loaded model: {model}"
    MODEL_UNLOADED = "Unloaded model: {model}"
    MODEL_NOT_LOADED = "Model {model} not loaded"

    # Model types
    TYPE_TEXT_GENERATION = "text-generation"
    TYPE_TEXT_CLASSIFICATION = "text-classification"
    TYPE_IMAGE_GENERATION = "image-generation"

    # Errors
    ERROR_ADDING_MODEL = "Error adding model: {error}"
    ERROR_UPDATING_MODEL = "Error updating model: {error}"
    ERROR_DELETING_MODEL = "Error deleting model: {error}"
    ERROR_LOADING_MODEL = "Error loading model {model}: {error}"
    ERROR_RECORDING_INFERENCE = "Error recording inference: {error}"
    ERROR_GENERATING_TEXT = "Error generating text: {error}"
    ERROR_CLASSIFYING_TEXT = "Error classifying text: {error}"
    ERROR_GENERATING_IMAGE = "Error generating image: {error}"
    UNSUPPORTED_MODEL_TYPE = "Unsupported model type: {type}"
    IMAGE_GEN_NOT_IMPLEMENTED = "Image generation models not yet implemented"

    # Database
    DB_FILE = "models.db"
    SQL_DELETE_MODEL = "DELETE FROM models WHERE id = ?"


class CommandMessages:
    """Command store and workflow message constants."""

    # Git operations
    GIT_REPO_EXISTS = "Git repository already exists at {path}"
    ADDED_REMOTE = "Added remote: {remote}"
    STORE_PATH_SAVED = "Store path saved to {path}"
    GIT_INIT_FAILED = "Git init failed: {error}"
    COMMITTED_CHANGES = "Committed changes: {message}"
    PUSHED_TO_REMOTE = "Pushed to remote"
    PULLED_FROM_REMOTE = "Pulled latest changes from remote"
    NO_REMOTE_PULL = "No remote configured or pull failed. Using local store."
    FAILED_TO_PUSH = "Failed to push commands: {error}"
    FAILED_TO_PULL = "Failed to pull commands: {error}"

    # Store operations
    COPIED_ITEMS = "Copied {count} items to store"
    PULLED_ITEMS = "Pulled {count} items from store"
    BACKED_UP_TO = "Backed up existing commands to {path}"
    UPDATE_COMMANDS = "Update commands {timestamp}"

    # Command operations
    COMMAND_IMPORTED = "Imported command: {name}"
    COMMAND_EXPORTED = "Exported command to: {path}"
    COMMAND_REMOVED = "Removed command: {name}"
    COMMAND_VERIFIED = "Command {name} verified successfully"
    LOCKFILE_UPDATED = "Updated lockfile: {path}"

    # Status messages
    STORE_STATUS_HEADER = "[bold]Command Store Status[/bold]"
    STORE_PATH = "  Store path: {path}"
    TOTAL_COMMANDS = "  Total commands: {count}"
    GIT_STATUS = "  Git status: {status}"

    # Errors
    INVALID_COMMAND_NAME = "Invalid command name: {name}"
    INVALID_GROUP_NAME = "Invalid group name: {name}"
    STORE_NOT_INITIALIZED = "Command store not initialized. Run 'mcli workflow store init' first."


class SystemIntegrationMessages:
    """System integration message constants for chat system control."""

    # Error messages
    SYSTEM_CONTROL_DISABLED = "System control is disabled"
    ENABLE_SYSTEM_CONTROL = "Enable system control to use this feature"
    COULD_NOT_UNDERSTAND_REQUEST = "Could not understand system request"
    COULD_NOT_EXTRACT_COMMAND = "Could not extract command to execute"
    COULD_NOT_EXTRACT_PATH = "Could not extract directory path from request"
    COULD_NOT_DETERMINE_OPEN = "Could not determine what to open"
    COMMAND_BLOCKED_SECURITY = "Command blocked for security reasons"

    # Suggestion messages
    TRY_TEXTEDIT_EXAMPLE = "Try: 'Open TextEdit and write Hello World' or 'Take a screenshot'"
    TRY_RUN_EXAMPLE = "Try: 'Run ls' or 'Execute date'"
    TRY_NAVIGATE_EXAMPLE = "Try: 'navigate to /path/to/directory' or 'cd to ~/Documents'"
    TRY_SHELL_EXAMPLE = "Try: 'run command ls -la' or 'execute find /path -name pattern'"
    SPECIFY_URL_OR_PATH = "Specify a URL (like https://google.com) or file path"
    TRY_SYSTEM_INFO = "Try 'system info' for general hardware information"

    # Success message templates
    TEXTEDIT_SUCCESS = "✅ Opened TextEdit and wrote: '{text}'"
    TEXTEDIT_SAVED = " (saved as {filename})"
    APP_CONTROL_SUCCESS = "✅ {action} {app_name}"
    SCREENSHOT_SUCCESS = "✅ Screenshot saved to: {path}"
    OPENED_SUCCESS = "✅ Opened: {path}"
    EXECUTED_SUCCESS = "✅ Executed: {command}"
    CURRENT_DIR_SUCCESS = "📍 Current directory: {path}"
    NAVIGATION_SUCCESS = "📁 Contains: {summary}"
    SIMULATOR_CLEANUP_SUCCESS = "🧹 Simulator cleanup completed!\n💾 Freed {mb} MB of storage"
    CACHE_CLEANUP_HEADER = "🧹 Cache Cleanup Results:"
    CACHE_ITEM_SUCCESS = "  ✅ {item}"
    NO_CACHE_ITEMS = "  ℹ️ No cache items found to clear"
    TOTAL_SPACE_FREED = "💾 Total space freed: {mb:.1f} MB"

    # System info format
    SYSTEM_TIME_FMT = "⏰ Current time: {time} ({timezone})"
    SYSTEM_SUMMARY_SYSTEM = "💻 System: {system} {machine}"
    SYSTEM_SUMMARY_CPU = "🧠 CPU: {cores} cores, {usage}% usage"
    SYSTEM_SUMMARY_RAM = "💾 RAM: {used:.1f}GB used / {total:.1f}GB total ({percent}%)"
    SYSTEM_SUMMARY_UPTIME = "⏰ Uptime: {hours:.1f} hours"

    # Memory display
    MEMORY_HEADER = "💾 Memory Usage:"
    MEMORY_RAM_FMT = "  RAM: {used:.1f}GB used / {total:.1f}GB total ({percent}%)"
    MEMORY_AVAILABLE_FMT = "  Available: {available:.1f}GB"
    MEMORY_SWAP_FMT = "  Swap: {used:.1f}GB used / {total:.1f}GB total ({percent}%)"
    RECOMMENDATIONS_HEADER = "📋 Recommendations:"
    RECOMMENDATION_ITEM = "  • {rec}"

    # Disk display
    DISK_HEADER = "💽 Disk Usage:"
    DISK_MAIN_FMT = "  Main: {used:.1f}GB used / {total:.1f}GB total ({percent:.1f}%)"
    DISK_FREE_FMT = "  Free: {free:.1f}GB available"
    DISK_OTHER_HEADER = "  Other partitions:"
    DISK_PARTITION_FMT = "    {mount}: {used:.1f}GB / {total:.1f}GB ({percent}%)"

    # Hardware devices
    HARDWARE_HEADER = "🔌 Connected Hardware Devices:"
    USB_DEVICES_HEADER = "💾 USB Devices:"
    NETWORK_INTERFACES_HEADER = "🌐 Network Interfaces:"
    AUDIO_DEVICES_HEADER = "🔊 Audio Devices:"
    DEVICE_ITEM = "  • {name}"
    NO_HARDWARE_DETECTED = "ℹ️  No specific hardware devices detected via system profiler"
    HARDWARE_HINT = "💡 Try: 'system info' for general hardware information"

    # Directory listing
    DIR_SUMMARY_DIRS = "📁 {count} directories"
    DIR_SUMMARY_FILES = "📄 {count} files"
    DIR_LISTING_HEADER = "📂 {path}"
    SHOWING_FIRST_N = "(showing first {shown} of {total} items)"
    DIR_ENTRY = "📁 {name}/"
    FILE_ENTRY = "📄 {name}{size}"

    # Error format templates
    ERROR_TEXTEDIT = "Error handling TextEdit request: {error}"
    ERROR_APP_CONTROL = "Error handling app control request: {error}"
    ERROR_SCREENSHOT = "Error taking screenshot: {error}"
    ERROR_OPEN = "Error opening file/URL: {error}"
    ERROR_COMMAND = "Error executing command: {error}"
    ERROR_SYSTEM_TIME = "Error getting system time: {error}"
    ERROR_SYSTEM_INFO = "Error getting system information: {error}"
    ERROR_HARDWARE_DEVICES = "Error getting hardware devices: {error}"
    ERROR_MEMORY = "Error getting memory usage: {error}"
    ERROR_DISK = "Error getting disk usage: {error}"
    ERROR_CACHE = "Error clearing caches: {error}"
    ERROR_NAVIGATION = "Navigation error: {error}"
    ERROR_DIR_LISTING = "Directory listing error: {error}"
    ERROR_SIMULATOR_CLEANUP = "Simulator cleanup error: {error}"
    ERROR_SHELL_COMMAND = "Shell command error: {error}"
    ERROR_CURRENT_DIR = "Current directory error: {error}"

    # Function descriptions (for system_functions dict)
    DESC_TEXTEDIT = "Open TextEdit and write specified text"
    DESC_CONTROL_APP = "Control system applications (open, close, interact)"
    DESC_EXECUTE_COMMAND = "Execute shell/terminal commands"
    DESC_TAKE_SCREENSHOT = "Take a screenshot and save to Desktop"
    DESC_OPEN_FILE_URL = "Open files or URLs with default system application"
    DESC_SYSTEM_INFO = "Get comprehensive system information (CPU, memory, disk, etc.)"
    DESC_SYSTEM_TIME = "Get current system time and date"
    DESC_MEMORY_USAGE = "Get detailed memory usage information"
    DESC_DISK_USAGE = "Get disk space and usage information"
    DESC_CLEAR_CACHES = "Clear system caches and temporary files"
    DESC_CHANGE_DIR = "Navigate to a directory"
    DESC_LIST_DIR = "List contents of a directory"
    DESC_CLEAN_SIMULATOR = "Clean iOS/watchOS simulator cache and temporary data"
    DESC_SHELL_COMMAND = "Execute shell commands with full terminal access"
    DESC_CURRENT_DIR = "Get current working directory"

    # Parameter descriptions
    PARAM_TEXT = "Text to write in TextEdit"
    PARAM_FILENAME = "Optional filename to save (will save to Desktop)"
    PARAM_APP_NAME = "Name of the application (e.g., 'TextEdit', 'Calculator')"
    PARAM_ACTION = "Action to perform (open, close, new_document, write_text)"
    PARAM_KWARGS = "Additional parameters like text, filename"
    PARAM_KWARGS_KEY = "**kwargs"  # Dictionary key for kwargs parameter
    PARAM_COMMAND = "Shell command to execute"
    PARAM_COMMAND_DESC = "Optional description of what the command does"
    PARAM_SCREENSHOT_FN = "Optional filename (will auto-generate if not provided)"
    PARAM_PATH_OR_URL = "File path or URL to open"
    PARAM_DIR_PATH = "Directory path to navigate to"
    PARAM_LIST_PATH = "Directory path to list (optional, defaults to current)"
    PARAM_SHOW_HIDDEN = "Show hidden files (optional)"
    PARAM_DETAILED = "Show detailed file information (optional)"
    PARAM_WORKING_DIR = "Directory to run command in (optional)"

    # Default values
    DEFAULT_TEXT = "Hello, World!"
    DEFAULT_APP = "TextEdit"
    DEFAULT_FILENAME_EXT = ".txt"
    DEFAULT_SCREENSHOT_EXT = ".png"

    # Request pattern keywords (for matching user requests)
    # Time-related patterns
    PATTERNS_TIME = ["what time", "current time", "system time", "what is the time"]
    # System info patterns
    PATTERNS_SYSTEM_INFO = ["system info", "system information", "system specs", "hardware info"]
    # Hardware device patterns
    PATTERNS_HARDWARE = [
        "hardware devices",
        "connected devices",
        "list hardware",
        "show devices",
        "connected hardware",
    ]
    # Memory patterns
    PATTERNS_MEMORY = [
        "memory usage",
        "ram usage",
        "how much memory",
        "how much ram",
        "memory info",
    ]
    # Disk patterns
    PATTERNS_DISK = [
        "disk usage",
        "disk space",
        "storage space",
        "how much space",
        "free space",
    ]
    # Cache clear patterns
    PATTERNS_CACHE = [
        "clear cache",
        "clean cache",
        "clear temp",
        "free up space",
        "clean system",
        "clear system cache",
    ]
    # Navigation patterns
    PATTERNS_NAVIGATION = ["navigate to", "go to", "change to", "cd to", "move to"]
    # Directory listing patterns
    PATTERNS_DIR_LIST = ["list files", "list directory", "show files", "ls", "dir", "what's in"]
    # Simulator patterns
    PATTERNS_SIMULATOR = ["clean simulator", "simulator data", "clean ios", "clean watchos"]
    # Shell command patterns
    PATTERNS_SHELL = ["run command", "execute", "shell", "terminal"]
    # Current directory patterns
    PATTERNS_CURRENT_DIR = ["where am i", "current directory", "pwd", "current path"]
    # App control keywords (single words)
    KEYWORDS_APP_CONTROL = ["open", "close", "launch", "quit"]
    # Command execution keywords
    KEYWORDS_COMMAND_EXEC = ["run", "execute", "command", "terminal"]
    # Screenshot patterns
    PATTERN_SCREENSHOT = "screenshot"
    PATTERN_SCREEN_CAPTURE = "screen capture"
    # TextEdit patterns
    PATTERN_TEXTEDIT = "textedit"
    PATTERN_WRITE = "write"
    PATTERN_TYPE = "type"
    # File/URL patterns
    PATTERN_FILE = "file"
    PATTERN_URL = "url"
    PATTERN_HTTP = "http"
    # Open pattern
    PATTERN_OPEN = "open"
    # Common URL defaults
    URL_GOOGLE = "https://google.com"
    PATTERN_GOOGLE = "google"
    PATTERN_CURRENT_DIR = "current directory"
    PATTERN_THIS_FOLDER = "this folder"

    # Text extraction word patterns
    WORDS_TO_REMOVE_TEXTEDIT = ["in textedit", "to textedit", "and save", "then save"]

    # Common apps mapping (lowercase key -> proper name)
    COMMON_APPS = {
        "textedit": "TextEdit",
        "calculator": "Calculator",
        "finder": "Finder",
        "safari": "Safari",
        "chrome": "Google Chrome",
        "firefox": "Firefox",
        "terminal": "Terminal",
        "preview": "Preview",
        "notes": "Notes",
        "mail": "Mail",
    }

    # Dangerous commands for security blocking
    DANGEROUS_COMMANDS = ["rm -rf", "sudo", "format", "del /", "> /dev"]

    # USB device keywords for filtering
    USB_DEVICE_KEYWORDS = ["mouse", "keyboard", "disk", "camera", "audio", "hub"]

    # Audio device keywords for filtering
    AUDIO_DEVICE_KEYWORDS = ["Built-in", "USB", "Bluetooth"]

    # Command extraction patterns
    PATTERN_RUN = "run "
    PATTERN_EXECUTE = "execute "

    # App control patterns
    PATTERN_NEW_DOCUMENT = "new document"

    # URL patterns
    URL_PREFIX_WWW = "www."

    # Directory listing patterns
    PATTERN_WHATS_IN = "what's in "
    PATTERN_ALL_FILES = "all files"

    # Description strings
    DESCRIPTION_HARDWARE_DEVICES = "List connected hardware devices"

    # Shell command safety patterns
    SHELL_DANGEROUS_COMMANDS = ["rm -rf /", "sudo rm", "format", "mkfs", "> /dev/null"]

    # Output messages
    OUTPUT_TRUNCATED = "\n... (output truncated)"

    # Examples for system functions (user-facing help text)
    EXAMPLES_TEXTEDIT = [
        "Open TextEdit and write 'Hello, World!'",
        "Write 'My notes' in TextEdit and save as 'notes.txt'",
    ]
    EXAMPLES_CONTROL_APP = [
        "Open Calculator",
        "Close TextEdit",
        "Open new document in TextEdit",
    ]
    EXAMPLES_EXECUTE_COMMAND = [
        "List files in current directory",
        "Check system uptime",
        "Create a new folder",
    ]
    EXAMPLES_SCREENSHOT = [
        "Take a screenshot",
        "Take screenshot and save as 'my_screen.png'",
    ]
    EXAMPLES_OPEN_FILE_URL = [
        "Open https://google.com",
        "Open ~/Documents/file.txt",
        "Open current directory in Finder",
    ]
    EXAMPLES_SYSTEM_INFO = [
        "What is my system information?",
        "Show system specs",
        "How much RAM do I have?",
    ]
    EXAMPLES_SYSTEM_TIME = [
        "What time is it?",
        "What is the current time?",
        "Show me the date and time",
    ]
    EXAMPLES_MEMORY_USAGE = [
        "How much memory am I using?",
        "Show memory usage",
        "Check RAM usage",
    ]
    EXAMPLES_DISK_USAGE = [
        "How much disk space do I have?",
        "Show disk usage",
        "Check storage space",
    ]
    EXAMPLES_CLEAR_CACHES = [
        "Clear system caches",
        "Clean up temporary files",
        "Free up space",
    ]
    EXAMPLES_CHANGE_DIR = [
        "Navigate to /System/Volumes/Data",
        "Go to ~/Documents",
        "Change to /tmp",
    ]
    EXAMPLES_LIST_DIR = [
        "List current directory",
        "Show files in /System/Volumes/Data",
        "List all files including hidden ones",
    ]
    EXAMPLES_CLEAN_SIMULATOR = [
        "Clean simulator data",
        "Remove iOS simulator caches",
        "Free up simulator storage",
    ]
    EXAMPLES_SHELL_COMMAND = [
        "Run ls -la",
        "Execute find command",
        "Run custom shell scripts",
    ]
    EXAMPLES_CURRENT_DIR = [
        "Where am I?",
        "Show current directory",
        "What's my current path?",
    ]


class EditMessages:
    """Edit command message constants."""

    # Info messages
    OPENING_IN_EDITOR = "Opening command in {editor}..."
    EDITING_NATIVE_SCRIPT = "Editing native script: {path}"
    LEGACY_JSON_NOTE = (
        "[dim]Note: This is a legacy JSON command. Consider migrating to native scripts.[/dim]"
    )

    # Success messages
    EDITED_FILE = "[green]Edited: {filename}[/green]"
    UPDATED_COMMAND = "[green]Updated command: {name}[/green]"
    SAVED_TO = "[dim]Saved to: {path}[/dim]"
    RELOAD_HINT = "[dim]Reload with: mcli self reload or restart mcli[/dim]"

    # Warning messages
    EDITOR_EXIT_CODE = "[yellow]Editor exited with code {code}[/yellow]"
    NO_CHANGES = "No changes made"

    # Error messages
    COMMAND_NOT_FOUND = "[red]Command not found: {name}[/red]"
    SEARCHED_IN = "[dim]Searched in: {path}[/dim]"
    LOOKING_FOR_EXTENSIONS = "[dim]Looking for: .py, .sh, .js, .ts, .ipynb, or .json[/dim]"
    FAILED_TO_LOAD = "[red]Failed to load command: {error}[/red]"
    NO_CODE = "[red]Command has no code: {name}[/red]"
    SYNTAX_ERROR = "[red]Syntax error in edited code: {error}[/red]"


class SyncMessages:
    """Script synchronization command messages.

    DEPRECATION NOTE (v7.20.0):
    The script-to-JSON synchronization system has been deprecated.
    Scripts are now loaded directly using ScriptLoader.
    Legacy messages are kept for backward compatibility.
    """

    # Legacy status messages (deprecated - kept for backward compatibility)
    SYNCING_SCRIPTS = "[dim](deprecated)[/dim] Syncing scripts in {path}..."
    SYNCED_SCRIPTS = "[dim](deprecated)[/dim] Synced {count} script(s) to JSON"
    NO_SCRIPTS_NEEDED_SYNCING = "No scripts needed syncing"
    SYNCING_SCRIPT = "[dim](deprecated)[/dim] Syncing {path}..."
    GENERATED_JSON = "[dim](deprecated)[/dim] Generated JSON: {path}"
    FAILED_TO_GENERATE_JSON = "Failed to generate JSON for {path}"

    # Status display
    SCRIPT_SYNC_STATUS_HEADER = "\n[bold]Script Synchronization Status[/bold]"
    LOCATION = "Location: {path}\n"
    IN_SYNC_COUNT = "In sync: {count} script(s)"
    NEEDS_SYNC_COUNT = "Needs sync: {count} script(s)"
    NO_JSON_COUNT = "No JSON: {count} script(s)"
    TOTAL_SCRIPTS = "Total scripts: {count}"
    RUN_SYNC_ALL_HINT = "\nRun [bold]mcli workflows sync all[/bold] to sync all scripts"

    # Cleanup messages
    SCANNING_ORPHANED = "Scanning for orphaned JSON files..."
    NO_ORPHANED_FOUND = "No orphaned JSON files found"
    FOUND_ORPHANED = "Found {count} orphaned JSON file(s):"
    REMOVE_FILES_PROMPT = "\nRemove these files?"
    CANCELLED = "Cancelled"
    REMOVED_ORPHANED = "Removed {count} orphaned JSON file(s)"
    NO_FILES_REMOVED = "No files were removed"

    # Watch mode (deprecated)
    STARTING_WATCHER = "Starting file watcher for {path}"
    PRESS_CTRL_C = "Press Ctrl+C to stop\n"
    FAILED_START_WATCHER = "Failed to start file watcher"
    WATCHING_FOR_CHANGES = "Watching for changes..."
    STOPPING_WATCHER = "Stopping watcher..."
    STOPPED = "Stopped"

    # IPFS sync
    UPLOADING_TO_IPFS = "Uploading command state to IPFS..."
    PUSHED_TO_IPFS = "Pushed to IPFS!"
    FAILED_PUSH_IPFS = "Failed to push to IPFS"
    RETRIEVING_FROM_IPFS = "Retrieving from IPFS: {cid}"
    RETRIEVED_FROM_IPFS = "Retrieved from IPFS"
    SAVED_TO = "Saved to: {path}"
    FAILED_RETRIEVE_IPFS = "Failed to retrieve from IPFS"
    CID_INVALID_OR_NOT_PROPAGATED = "CID may be invalid or not yet propagated to gateways"
    NO_SYNC_HISTORY = "No sync history found"
    RUN_PUSH_FIRST = "\nRun 'mcli sync push' to create your first sync"
    IPFS_SYNC_HISTORY_HEADER = "\n[bold]IPFS Sync History[/bold] (last {count} entries)\n"
    VERIFYING_CID = "Verifying CID: {cid}"
    CID_ACCESSIBLE = "CID is accessible on IPFS"
    CID_NOT_ACCESSIBLE = "CID is not accessible"
    PROPAGATION_DELAY_NOTE = "It may take a few minutes for new uploads to propagate"

    # IPFS daemon messages
    NO_LOCAL_IPFS_DAEMON = "No local IPFS daemon available"
    IPFS_SETUP_HEADER = "[yellow]To enable IPFS sync:[/yellow]"
    IPFS_SETUP_STEP_1 = "  1. Install IPFS: [cyan]brew install ipfs[/cyan]"
    IPFS_SETUP_STEP_1_ALT = "     (or see https://docs.ipfs.tech/install/)"
    IPFS_SETUP_STEP_2 = "  2. Initialize: [cyan]ipfs init[/cyan]"
    IPFS_SETUP_STEP_3 = "  3. Start daemon: [cyan]ipfs daemon[/cyan]"
    IPFS_SETUP_STEP_4 = "  4. Re-run this command"
    LOCAL_IPFS_DAEMON_DETECTED = "Local IPFS daemon detected"
    LOCAL_IPFS_UPLOAD_FAILED = "Local IPFS upload failed: {status}"
    LOCAL_IPFS_UPLOAD_ERROR = "Local IPFS upload error: {error}"
    HASH_VERIFICATION_FAILED = "Hash verification failed! Data may be corrupted."

    # Lockfile messages
    LOCKFILE_NOT_FOUND = "Lockfile not found: {path}"
    RUN_UPDATE_LOCKFILE = "Run 'mcli workflow update-lockfile' first"

    # Display formatting
    CID_LABEL = "\n[bold]CID:[/bold] {cid}"
    RETRIEVE_HINT = "\n[dim]Anyone can retrieve with:[/dim]"
    RETRIEVE_COMMAND = "  mcli sync pull {cid}"
    VIEW_BROWSER_HINT = "\n[dim]Or view in browser:[/dim]"
    IPFS_GATEWAY_URL = "  https://ipfs.io/ipfs/{cid}"
    COMMANDS_COUNT = "\n[bold]Commands:[/bold] {count}"
    VERSION_LABEL = "[bold]Version:[/bold] {version}"
    SYNCED_AT_LABEL = "[bold]Synced:[/bold] {timestamp}"
    DESCRIPTION_LABEL = "[bold]Description:[/bold] {description}"

    # Directory errors
    DIR_NOT_EXIST = "Commands directory does not exist: {path}"


__all__ = [
    "ErrorMessages",
    "SuccessMessages",
    "WarningMessages",
    "InfoMessages",
    "PromptMessages",
    "ChatMessages",
    "ModelServiceMessages",
    "CommandMessages",
    "SystemIntegrationMessages",
    "EditMessages",
    "SyncMessages",
]
