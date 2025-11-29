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


__all__ = [
    "ErrorMessages",
    "SuccessMessages",
    "WarningMessages",
    "InfoMessages",
    "PromptMessages",
    "ChatMessages",
    "ModelServiceMessages",
    "CommandMessages",
]
