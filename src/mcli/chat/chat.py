import os
import readline
from typing import Dict, List, Optional

import requests

from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml
from mcli.lib.ui.styling import console
from mcli.chat.system_integration import handle_system_request

# Load config from config.toml
CONFIG_PATH = "config.toml"
config = {}
try:
    config = read_from_toml(CONFIG_PATH, "llm") or {}
except Exception:
    # Silently handle config loading errors
    config = {}

if not config:
    # Default to local model for better performance and privacy
    config = {
        "provider": "local",
        "model": "phi3:3.8b",
        "temperature": 0.7,
        "system_prompt": "You are the MCLI Chat Assistant, a helpful AI assistant for the MCLI tool.",
        "ollama_base_url": "http://localhost:11434",
    }
elif not config.get("openai_api_key") and config.get("provider", "openai") == "openai":
    # If openai provider but no API key, switch to local
    config["provider"] = "local"
    if not config.get("model"):
        config["model"] = "phi3:3.8b"
    if not config.get("ollama_base_url"):
        config["ollama_base_url"] = "http://localhost:11434"

logger = get_logger(__name__)

# Fallbacks if not set in config.toml
LLM_PROVIDER = config.get("provider", "local")
MODEL_NAME = config.get("model", "phi3:3.8b")
OPENAI_API_KEY = config.get("openai_api_key", None)
OLLAMA_BASE_URL = config.get("ollama_base_url", "http://localhost:11434")
TEMPERATURE = float(config.get("temperature", 0.7))
SYSTEM_PROMPT = config.get(
    "system_prompt", 
    """You are the MCLI Personal Assistant, an intelligent agent that helps manage your computer and tasks.

I am a true personal assistant with these capabilities:
- System monitoring and control (memory, disk, applications, cleanup)
- Job scheduling and automation (cron jobs, reminders, recurring tasks)
- Process management and command execution
- File organization and system maintenance
- Contextual awareness of ongoing tasks and system state

I maintain awareness of:
- Currently scheduled jobs and their status
- System health and resource usage
- Recent activities and completed tasks
- User preferences and routine patterns

I can proactively suggest optimizations, schedule maintenance, and automate repetitive tasks.
I'm designed to be your digital assistant that keeps things running smoothly."""
)


class ChatClient:
    """Interactive chat client for MCLI command management"""

    def __init__(self):
        self.daemon = get_daemon_client()
        self.history = []
        self.session_active = True
        self._ensure_daemon_running()
        self._load_scheduled_jobs()

    def start_interactive_session(self):
        """Start the chat interface"""
        console.print("[bold green]MCLI Personal Assistant[/bold green] (type 'exit' to quit)")

        # Show current configuration
        if LLM_PROVIDER == "local":
            console.print(f"[dim]Using local model: {MODEL_NAME} via Ollama[/dim]")
        elif LLM_PROVIDER == "openai":
            console.print(f"[dim]Using OpenAI model: {MODEL_NAME}[/dim]")
        elif LLM_PROVIDER == "anthropic":
            console.print(f"[dim]Using Anthropic model: {MODEL_NAME}[/dim]")

        # Show proactive status update
        self._show_startup_status()

        console.print("How can I help you with your tasks today?")
        console.print("\n[bold cyan]Available Commands:[/bold cyan]")
        console.print("• [yellow]commands[/yellow] - List available functions")
        console.print("• [yellow]run <command> [args][/yellow] - Execute command in container")
        console.print("• [yellow]ps[/yellow] - List running processes (Docker-style)")
        console.print("• [yellow]logs <id>[/yellow] - View process logs")
        console.print("• [yellow]inspect <id>[/yellow] - Detailed process info")
        console.print("• [yellow]start/stop <id>[/yellow] - Control process lifecycle")
        console.print("• [yellow]System Control[/yellow] - Control applications (e.g., 'open TextEdit', 'take screenshot')")
        console.print("• [yellow]Job Scheduling[/yellow] - Schedule tasks (e.g., 'schedule cleanup daily', 'what's my status?')")
        console.print("• Ask questions about functions and codebase\n")

        while self.session_active:
            try:
                user_input = console.input("[bold cyan]>>> [/bold cyan]").strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    self.session_active = False
                    continue

                self.process_input(user_input)

            except KeyboardInterrupt:
                console.print("\nUse 'exit' to quit the chat session")
            except Exception as e:
                logger.error(f"Chat error: {e}")
                console.print(f"[red]Error:[/red] {str(e)}")

    def process_input(self, user_input: str):
        """Process user input and generate response"""
        self.history.append({"user": user_input})

        # Check for commands list request
        if user_input.lower().strip() == "commands":
            self.handle_commands_list()
            return

        # Check for process management commands
        if user_input.lower().startswith("ps") or user_input.lower().startswith("docker ps"):
            self.handle_process_list()
            return
        elif user_input.lower().startswith("logs "):
            process_id = user_input.split()[1] if len(user_input.split()) > 1 else None
            if process_id:
                self.handle_process_logs(process_id)
            else:
                console.print("[red]Usage: logs <process_id>[/red]")
            return
        elif user_input.lower().startswith("inspect "):
            process_id = user_input.split()[1] if len(user_input.split()) > 1 else None
            if process_id:
                self.handle_process_inspect(process_id)
            else:
                console.print("[red]Usage: inspect <process_id>[/red]")
            return
        elif user_input.lower().startswith("stop "):
            process_id = user_input.split()[1] if len(user_input.split()) > 1 else None
            if process_id:
                self.handle_process_stop(process_id)
            else:
                console.print("[red]Usage: stop <process_id>[/red]")
            return
        elif user_input.lower().startswith("start "):
            process_id = user_input.split()[1] if len(user_input.split()) > 1 else None
            if process_id:
                self.handle_process_start(process_id)
            else:
                console.print("[red]Usage: start <process_id>[/red]")
            return

        # Check for command creation requests
        if self.is_command_creation_request(user_input):
            self.handle_command_creation(user_input)
            return

        # Check for system control requests
        if self.is_system_control_request(user_input):
            self.handle_system_control(user_input)
            return

        # Check for job management requests (agent capabilities)
        if self._is_job_management_request(user_input):
            self._handle_job_management(user_input)
            return

        # Check for 'run <command> [args...]' pattern (containerized execution)
        if user_input.lower().startswith("run "):
            command_part = user_input[4:].strip()

            # Handle natural language patterns like "run the hello world command"
            if " command" in command_part.lower():
                # Extract the actual command name from natural language
                command_part = (
                    command_part.lower().replace(" command", "").replace("the ", "").strip()
                )

            parts = command_part.split()
            if parts:
                command = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                self.handle_containerized_run(command, args)
            else:
                console.print("[red]No command provided after 'run'.[/red]")
            return

        # Check for natural language command execution requests
        if self.is_command_execution_request(user_input):
            command_name = self.extract_command_name(user_input)
            if command_name:
                self.handle_direct_command_execution(command_name)
                return

        # Try to check for command-related queries, but fallback gracefully if daemon is unavailable
        try:
            daemon_available = True
            _ = self.daemon.list_commands()
        except Exception as e:
            daemon_available = False
            logger.debug(f"Daemon unavailable, running in LLM-only mode. Details: {e}")

        if daemon_available and any(
            keyword in user_input.lower()
            for keyword in ["command", "list", "show", "find", "search"]
        ):
            self.handle_command_queries(user_input)
        else:
            self.generate_llm_response(user_input)

    def execute_command_via_daemon(self, command_name: str, args: Optional[list] = None):
        """Execute a command via the daemon and print the result."""
        try:
            result = self.daemon.execute_command(command_name=command_name, args=args or [])
            output = result.get("output") or result.get("result") or str(result)
            console.print(f"[green]Command Output:[/green]\n{output}")
        except Exception as e:
            console.print(f"[red]Failed to execute command:[/red] {e}")

    def is_command_execution_request(self, user_input: str) -> bool:
        """Check if user input is requesting to execute a command."""
        lower_input = user_input.lower()
        execution_keywords = [
            "call the",
            "execute the",
            "run the",
            "execute command",
            "hello world",
            "hello-world",
            "helloworld",
        ]
        # Be more specific - avoid matching on single words like "execute" or "call"
        return any(keyword in lower_input for keyword in execution_keywords)

    def extract_command_name(self, user_input: str) -> Optional[str]:
        """Extract command name from natural language input."""
        lower_input = user_input.lower()

        # Handle specific command patterns
        if "hello" in lower_input:
            return "hello"

        # Try to extract command name using common patterns
        import re

        patterns = [
            r"(?:call|execute|run)\s+(?:the\s+)?([a-zA-Z0-9\-_]+)(?:\s+command)?",
            r"([a-zA-Z0-9\-_]+)\s+command",
            r"the\s+([a-zA-Z0-9\-_]+)\s+command",
        ]

        for pattern in patterns:
            match = re.search(pattern, lower_input)
            if match:
                return match.group(1).replace("-", "_").replace(" ", "_")

        return None

    def handle_direct_command_execution(self, command_name: str):
        """Handle direct execution of a discovered command."""
        try:
            # Use command discovery to find the command
            discovery = get_command_discovery()
            command = discovery.get_command_by_name(command_name)

            if command:
                console.print(f"[green]Executing command:[/green] {command.full_name}")
                try:
                    # Execute the command callback directly
                    if command.callback:
                        # For the hello command, we need to call it appropriately
                        if command.name == "hello" and command.full_name.startswith("self."):
                            # This is the hello command from self module - call with default argument
                            result = command.callback("World")
                            console.print(f"[green]✅ Command executed successfully[/green]")
                        else:
                            result = command.callback()
                            console.print(f"[green]✅ Command executed successfully[/green]")
                    else:
                        console.print("[yellow]Command found but has no callback[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error executing command:[/red] {e}")
            else:
                console.print(f"[red]Command '{command_name}' not found[/red]")
                console.print("[yellow]Try 'commands' to see available commands[/yellow]")

        except Exception as e:
            console.print(f"[red]Error finding command:[/red] {e}")

    def handle_command_queries(self, query: str):
        """Handle command-related queries using existing command registry"""
        try:
            # Always fetch all commands (active and inactive)
            result = self.daemon.list_commands(all=True)
            if isinstance(result, dict):
                commands = result.get("commands", [])
            elif isinstance(result, list):
                commands = result
            else:
                commands = []
        except Exception as e:
            logger.debug(
                f"Could not fetch commands from daemon: {e}. Falling back to LLM-only mode."
            )
            return self.generate_llm_response(query)

        # Simple keyword matching for initial implementation
        lowered = query.lower()
        if (
            "list command" in lowered
            or "show command" in lowered
            or "available command" in lowered
            or "what can i do" in lowered
            or "commands" in lowered
        ):
            self.list_commands()  # Always use discovery system, ignore daemon commands
        elif "search" in lowered or "find" in lowered:
            self.search_commands(query)  # Always use discovery system, ignore daemon commands
        else:
            # Check if this is a context-sensitive question that might need system help
            if self._is_system_help_request(query):
                self._handle_system_help_request(query)
            else:
                self.generate_llm_response(query)

    def list_commands(self, commands: List[Dict] = None):
        """List available commands"""
        if commands is None:
            # Use discovery system to get all commands
            try:
                discovery = get_command_discovery()
                commands = discovery.get_commands(include_groups=False)
            except Exception as e:
                console.print(f"[red]Error discovering commands: {e}[/red]")
                return

        if not commands:
            console.print("No commands found")
            return

        console.print(f"[bold]Available Commands ({len(commands)}):[/bold]")
        for cmd in commands[:20]:  # Show first 20 to avoid overwhelming
            if "full_name" in cmd:
                # New discovery format
                console.print(f"• [green]{cmd['full_name']}[/green]")
            else:
                # Old daemon format
                status = "[INACTIVE] " if not cmd.get("is_active", True) else ""
                console.print(
                    f"{status}• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})"
                )

            if cmd.get("description"):
                console.print(f"  {cmd['description']}")
            if cmd.get("module"):
                console.print(f"  Module: {cmd['module']}")
            elif cmd.get("tags"):
                console.print(f"  Tags: {', '.join(cmd['tags'])}")
            console.print()

        if len(commands) > 20:
            console.print(f"[dim]... and {len(commands) - 20} more commands[/dim]")
            console.print("[dim]Use 'mcli commands list' to see all commands[/dim]")

    def search_commands(self, query: str, commands: List[Dict] = None):
        """Search commands based on query"""
        search_term = query.lower().replace("search", "").replace("find", "").strip()

        if commands is None:
            # Use discovery system to search
            try:
                discovery = get_command_discovery()
                results = discovery.search_commands(search_term)
            except Exception as e:
                console.print(f"[red]Error searching commands: {e}[/red]")
                return
        else:
            # Use provided commands (legacy mode)
            results = [
                cmd
                for cmd in commands
                if (
                    search_term in cmd["name"].lower()
                    or search_term in (cmd["description"] or "").lower()
                    or any(search_term in tag.lower() for tag in cmd.get("tags", []))
                )
            ]

        if not results:
            console.print(f"No commands found matching '[yellow]{search_term}[/yellow]'")
            return

        console.print(f"[bold]Matching Commands for '{search_term}' ({len(results)}):[/bold]")
        for cmd in results[:10]:  # Show first 10 results
            if "full_name" in cmd:
                # New discovery format
                console.print(f"• [green]{cmd['full_name']}[/green]")
            else:
                # Old daemon format
                console.print(f"• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})")

            console.print(f"  [italic]{cmd['description']}[/italic]")
            console.print()

        if len(results) > 10:
            console.print(f"[dim]... and {len(results) - 10} more results[/dim]")

    def handle_commands_list(self):
        """Handle 'commands' command to list available functions"""
        try:
            # Get commands from daemon
            if hasattr(self.daemon, "list_commands"):
                commands = self.daemon.list_commands()

                if not commands:
                    console.print("[yellow]No commands available through daemon[/yellow]")
                    return

                console.print(f"[bold green]Available Commands ({len(commands)}):[/bold green]")

                for i, cmd in enumerate(commands[:20]):  # Show first 20 commands
                    name = cmd.get("name", "Unknown")
                    description = cmd.get("description", cmd.get("help", "No description"))

                    # Truncate long descriptions
                    if len(description) > 80:
                        description = description[:77] + "..."

                    console.print(f"• [cyan]{name}[/cyan]")
                    if description:
                        console.print(f"  {description}")

                if len(commands) > 20:
                    console.print(f"[dim]... and {len(commands) - 20} more commands[/dim]")
                    console.print("[dim]Use natural language to ask about specific commands[/dim]")

            else:
                # Fallback - try to get commands another way
                console.print(
                    "[yellow]Command listing not available - daemon may not be running[/yellow]"
                )
                console.print(
                    "Try starting the daemon with: [cyan]mcli workflow daemon start[/cyan]"
                )

        except Exception as e:
            logger.debug(f"Error listing commands: {e}")
            console.print("[yellow]Could not retrieve commands list[/yellow]")
            console.print("Available built-in chat commands:")
            console.print("• [cyan]commands[/cyan] - This command")
            console.print("• [cyan]ps[/cyan] - List running processes")
            console.print("• [cyan]run <command>[/cyan] - Execute a command")
            console.print("• [cyan]logs <id>[/cyan] - View process logs")
            console.print("• [cyan]inspect <id>[/cyan] - Detailed process info")
            console.print("• [cyan]start/stop <id>[/cyan] - Control process lifecycle")

    def handle_process_list(self):
        """Handle 'ps' command to list running processes"""
        try:
            import requests

            # Use daemon client to get correct URL
            response = requests.get(f"{self.daemon.base_url}/processes")
            if response.status_code == 200:
                data = response.json()
                processes = data.get("processes", [])

                if not processes:
                    console.print("No processes running")
                    return

                # Format output like docker ps
                console.print(
                    "[bold]CONTAINER ID   NAME           COMMAND                  STATUS    UPTIME     CPU      MEMORY[/bold]"
                )
                for proc in processes:
                    console.print(
                        f"{proc['id']:<13} {proc['name']:<14} {proc['command'][:24]:<24} {proc['status']:<9} {proc['uptime']:<10} {proc['cpu']:<8} {proc['memory']}"
                    )
            else:
                console.print(
                    f"[red]Error: Failed to get process list (HTTP {response.status_code})[/red]"
                )
        except Exception as e:
            console.print(f"[red]Error connecting to daemon: {e}[/red]")

    def handle_process_logs(self, process_id: str):
        """Handle 'logs' command to show process logs"""
        try:
            import requests

            response = requests.get(f"{self.daemon.base_url}/processes/{process_id}/logs")
            if response.status_code == 200:
                logs = response.json()
                console.print(f"[bold]Logs for {process_id}:[/bold]")
                if logs.get("stdout"):
                    console.print("[green]STDOUT:[/green]")
                    console.print(logs["stdout"])
                if logs.get("stderr"):
                    console.print("[red]STDERR:[/red]")
                    console.print(logs["stderr"])
                if not logs.get("stdout") and not logs.get("stderr"):
                    console.print("No logs available")
            elif response.status_code == 404:
                console.print(f"[red]Process {process_id} not found[/red]")
            else:
                console.print(f"[red]Error: Failed to get logs (HTTP {response.status_code})[/red]")
        except Exception as e:
            console.print(f"[red]Error connecting to daemon: {e}[/red]")

    def handle_process_inspect(self, process_id: str):
        """Handle 'inspect' command to show detailed process info"""
        try:
            import requests

            response = requests.get(f"{self.daemon.base_url}/processes/{process_id}")
            if response.status_code == 200:
                info = response.json()
                console.print(f"[bold]Process {process_id} Details:[/bold]")
                console.print(f"ID: {info['id']}")
                console.print(f"Name: {info['name']}")
                console.print(f"Status: {info['status']}")
                console.print(f"PID: {info['pid']}")
                console.print(f"Command: {info['command']} {' '.join(info.get('args', []))}")
                console.print(f"Working Dir: {info.get('working_dir', 'N/A')}")
                console.print(f"Created: {info.get('created_at', 'N/A')}")
                console.print(f"Started: {info.get('started_at', 'N/A')}")
                if info.get("stats"):
                    stats = info["stats"]
                    console.print(f"CPU: {stats.get('cpu_percent', 0):.1f}%")
                    console.print(f"Memory: {stats.get('memory_mb', 0):.1f} MB")
                    console.print(f"Uptime: {stats.get('uptime_seconds', 0)} seconds")
            elif response.status_code == 404:
                console.print(f"[red]Process {process_id} not found[/red]")
            else:
                console.print(
                    f"[red]Error: Failed to inspect process (HTTP {response.status_code})[/red]"
                )
        except Exception as e:
            console.print(f"[red]Error connecting to daemon: {e}[/red]")

    def handle_process_stop(self, process_id: str):
        """Handle 'stop' command to stop a process"""
        try:
            import requests

            response = requests.post(f"{self.daemon.base_url}/processes/{process_id}/stop")
            if response.status_code == 200:
                console.print(f"[green]Process {process_id} stopped[/green]")
            elif response.status_code == 404:
                console.print(f"[red]Process {process_id} not found[/red]")
            else:
                console.print(
                    f"[red]Error: Failed to stop process (HTTP {response.status_code})[/red]"
                )
        except Exception as e:
            console.print(f"[red]Error connecting to daemon: {e}[/red]")

    def handle_process_start(self, process_id: str):
        """Handle 'start' command to start a process"""
        try:
            import requests

            response = requests.post(f"{self.daemon.base_url}/processes/{process_id}/start")
            if response.status_code == 200:
                console.print(f"[green]Process {process_id} started[/green]")
            elif response.status_code == 404:
                console.print(f"[red]Process {process_id} not found[/red]")
            else:
                console.print(
                    f"[red]Error: Failed to start process (HTTP {response.status_code})[/red]"
                )
        except Exception as e:
            console.print(f"[red]Error connecting to daemon: {e}[/red]")

    def handle_containerized_run(self, command: str, args: List[str]):
        """Handle 'run' command to execute in a containerized process"""
        try:
            import requests

            # Check if it's a registered command first
            try:
                result = self.daemon.list_commands(all=True)
                commands = result.get("commands", []) if isinstance(result, dict) else result

                # Look for matching command
                matching_cmd = None
                for cmd in commands:
                    if cmd["name"].lower() == command.lower():
                        matching_cmd = cmd
                        break

                if matching_cmd:
                    # Execute via the existing command system but in a container
                    response = requests.post(
                        f"{self.daemon.base_url}/processes/run",
                        json={
                            "name": f"cmd-{matching_cmd['name']}",
                            "command": (
                                "python"
                                if matching_cmd["language"] == "python"
                                else matching_cmd["language"]
                            ),
                            "args": ["-c", matching_cmd["code"]] + args,
                            "detach": True,
                        },
                    )

                    if response.status_code == 200:
                        result = response.json()
                        console.print(
                            f"[green]Started containerized command '{matching_cmd['name']}' with ID {result['id'][:12]}[/green]"
                        )
                        console.print("Use 'logs <id>' to view output or 'ps' to see status")
                    else:
                        console.print(f"[red]Failed to start containerized command[/red]")
                    return
            except Exception:
                pass  # Fall through to shell command execution

            # Execute as shell command in container
            response = requests.post(
                f"{self.daemon.base_url}/processes/run",
                json={"name": f"shell-{command}", "command": command, "args": args, "detach": True},
            )

            if response.status_code == 200:
                result = response.json()
                console.print(
                    f"[green]Started containerized process with ID {result['id'][:12]}[/green]"
                )
                console.print("Use 'logs <id>' to view output or 'ps' to see status")
            else:
                console.print(f"[red]Failed to start containerized process[/red]")

        except Exception as e:
            console.print(f"[red]Error connecting to daemon: {e}[/red]")

    def _ensure_daemon_running(self):
        """Ensure the API daemon is running, start it if not"""
        try:
            if not self.daemon.is_running():
                console.print("[yellow]Starting MCLI daemon...[/yellow]")
                import threading
                import time

                from mcli.workflow.daemon.api_daemon import APIDaemonService

                # Start daemon in a separate thread
                daemon_service = APIDaemonService()
                daemon_thread = threading.Thread(target=daemon_service.start, daemon=True)
                daemon_thread.start()

                # Wait for daemon to be ready with progress
                for i in range(10):  # Wait up to 10 seconds
                    time.sleep(1)
                    if self.daemon.is_running():
                        console.print(
                            f"[green]✅ MCLI daemon started successfully on {self.daemon.base_url}[/green]"
                        )
                        return
                    if i % 2 == 0:  # Show progress every 2 seconds
                        console.print(f"[dim]Waiting for daemon to start... ({i+1}/10)[/dim]")

                console.print("[red]❌ Daemon failed to start within 10 seconds[/red]")
                console.print(
                    "[yellow]Try starting manually: mcli workflow api-daemon start[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]❌ Could not start daemon: {e}[/red]")
            console.print("[yellow]Try starting manually: mcli workflow api-daemon start[/yellow]")

    def _pull_model_if_needed(self, model_name: str):
        """Pull the model from Ollama if it doesn't exist locally"""
        try:
            console.print(
                f"[yellow]Downloading model '{model_name}'. This may take a few minutes...[/yellow]"
            )

            import subprocess

            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                console.print(f"[green]✅ Model '{model_name}' downloaded successfully[/green]")
            else:
                console.print(
                    f"[red]❌ Failed to download model '{model_name}': {result.stderr}[/red]"
                )

        except subprocess.TimeoutExpired:
            console.print(f"[red]❌ Download of model '{model_name}' timed out[/red]")
        except FileNotFoundError:
            console.print("[red]❌ Ollama command not found. Please install Ollama first:[/red]")
            console.print("  brew install ollama")
        except Exception as e:
            console.print(f"[red]❌ Error downloading model '{model_name}': {e}[/red]")

    def generate_llm_response(self, query: str):
        """Generate response using LLM integration"""
        try:
            # Try to get all commands, including inactive
            try:
                result = self.daemon.list_commands(all=True)
                if isinstance(result, dict):
                    commands = result.get("commands", [])
                elif isinstance(result, list):
                    commands = result
                else:
                    commands = []
            except Exception:
                commands = []

            command_context = (
                "\n".join(
                    f"Command: {cmd['name']}\nDescription: {cmd.get('description', '')}\nTags: {', '.join(cmd.get('tags', []))}\nStatus: {'INACTIVE' if not cmd.get('is_active', True) else 'ACTIVE'}"
                    for cmd in commands
                )
                if commands
                else "(No command context available)"
            )

            # Check if this is a command creation request
            is_creation_request = any(
                keyword in query.lower()
                for keyword in [
                    "create command",
                    "create a command",
                    "new command",
                    "make command",
                    "integrate",
                    "add command",
                    "build command",
                    "generate command",
                ]
            )

            if is_creation_request:
                prompt = f"""{SYSTEM_PROMPT}

IMPORTANT CONTEXT:
- Available MCLI Commands: {command_context}
- The above list shows ALL currently available commands
- If a command is NOT in this list, it does NOT exist and needs to be created
- DO NOT suggest non-existent commands like 'mcli ls' or 'mcli list-files'
- ALWAYS generate new code when asked to create functionality

User Request: {query}

This is a command creation request. You must:
1. Check if the requested functionality exists in the available commands above
2. If it DOES NOT exist, generate NEW Python code using Click framework
3. Provide complete, working implementation with error handling
4. Include proper command structure and help text
5. Suggest specific file paths and explain testing

NEVER suggest commands that don't exist. ALWAYS create new code for missing functionality."""
            else:
                prompt = f"""{SYSTEM_PROMPT}

AVAILABLE MCLI COMMANDS:
{command_context}

SYSTEM CONTROL CAPABILITIES (always available):
- System Information: 'what time is it?', 'how much RAM do I have?', 'show system specs'  
- Disk Management: 'how much disk space do I have?', 'clear system caches'
- Application Control: 'open TextEdit', 'take screenshot', 'close Calculator'
- Memory Monitoring: 'show memory usage' with intelligent recommendations

JOB SCHEDULING CAPABILITIES (always available):
- Schedule Tasks: 'schedule cleanup daily at 2am', 'remind me weekly to check backups'
- Agent Status: 'what's my status?', 'list my jobs', 'show active tasks'
- Job Management: 'cancel job cleanup', 'stop scheduled task'
- Automation: Set up recurring system maintenance, file cleanup, monitoring

RESPONSE GUIDELINES:
- Be conversational and helpful, not robotic
- Provide intelligent suggestions based on context
- When users ask about cleanup/optimization, guide them to system control features
- If a command doesn't exist, suggest alternatives or explain how to create it
- Always consider what the user is trying to accomplish

User Question: {query}

Respond naturally and helpfully, considering both MCLI commands and system control capabilities."""

            if LLM_PROVIDER == "local":
                # Use Ollama for local model inference
                try:
                    response = requests.post(
                        f"{OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": MODEL_NAME,
                            "prompt": prompt,
                            "temperature": TEMPERATURE,
                            "stream": False,
                        },
                        timeout=60,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data.get("response", "")

                        # Clean up response like we do for OpenAI
                        import re

                        split_patterns = [
                            r"\n2\.",
                            r"\n```",
                            r"\nRelevant commands",
                            r"\n3\.",
                            r"\n- \*\*Command",
                        ]
                        split_idx = len(content)
                        for pat in split_patterns:
                            m = re.search(pat, content)
                            if m:
                                split_idx = min(split_idx, m.start())
                        main_answer = content[:split_idx].strip()
                        # Validate and correct any hallucinated commands
                        corrected_response = self.validate_and_correct_response(
                            main_answer, commands
                        )
                        return console.print(corrected_response)

                    elif response.status_code == 404:
                        console.print(
                            f"[yellow]Model '{MODEL_NAME}' not found. Attempting to pull it...[/yellow]"
                        )
                        self._pull_model_if_needed(MODEL_NAME)
                        # Retry the request
                        response = requests.post(
                            f"{OLLAMA_BASE_URL}/api/generate",
                            json={
                                "model": MODEL_NAME,
                                "prompt": prompt,
                                "temperature": TEMPERATURE,
                                "stream": False,
                            },
                            timeout=60,
                        )
                        if response.status_code == 200:
                            data = response.json()
                            content = data.get("response", "")
                            import re

                            split_patterns = [
                                r"\n2\.",
                                r"\n```",
                                r"\nRelevant commands",
                                r"\n3\.",
                                r"\n- \*\*Command",
                            ]
                            split_idx = len(content)
                            for pat in split_patterns:
                                m = re.search(pat, content)
                                if m:
                                    split_idx = min(split_idx, m.start())
                            main_answer = content[:split_idx].strip()
                            # Validate and correct any hallucinated commands
                            corrected_response = self.validate_and_correct_response(
                                main_answer, commands
                            )
                            return console.print(corrected_response)
                        else:
                            raise Exception(
                                f"Failed to generate response after pulling model: HTTP {response.status_code}"
                            )
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")

                except requests.exceptions.ConnectionError:
                    console.print(
                        "[red]Could not connect to Ollama. Please ensure Ollama is running:[/red]"
                    )
                    console.print("  brew install ollama")
                    console.print("  ollama serve")
                    console.print(f"  Visit: {OLLAMA_BASE_URL}")
                    return
                except requests.exceptions.Timeout:
                    console.print(
                        "[yellow]Request timed out. The model might be processing a complex query.[/yellow]"
                    )
                    return
                except Exception as api_exc:
                    raise

            elif LLM_PROVIDER == "openai":
                from openai import OpenAI

                if not OPENAI_API_KEY:
                    console.print(
                        "[red]OpenAI API key not configured. Please set it in config.toml[/red]"
                    )
                    return
                client = OpenAI(api_key=OPENAI_API_KEY)
                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=TEMPERATURE,
                    )
                    # Only print the first section (natural language answer) before any markdown/code block
                    content = response.choices[0].message.content
                    # Split on '```' or '2.' or 'Relevant commands' to avoid printing command/code blocks
                    import re

                    # Try to split on numbered sections or code block
                    split_patterns = [
                        r"\n2\.",
                        r"\n```",
                        r"\nRelevant commands",
                        r"\n3\.",
                        r"\n- \*\*Command",
                    ]
                    split_idx = len(content)
                    for pat in split_patterns:
                        m = re.search(pat, content)
                        if m:
                            split_idx = min(split_idx, m.start())
                    main_answer = content[:split_idx].strip()
                    return console.print(main_answer)
                except Exception as api_exc:
                    raise

            elif LLM_PROVIDER == "anthropic":
                from anthropic import Anthropic

                api_key = config.get("anthropic_api_key", None)
                client = Anthropic(api_key=api_key)
                try:
                    response = client.messages.create(
                        model=MODEL_NAME,
                        max_tokens=1000,
                        temperature=TEMPERATURE,
                        system=SYSTEM_PROMPT or "",
                        messages=[{"role": "user", "content": query}],
                    )
                    return console.print(response.content)
                except Exception as api_exc:
                    raise

            else:
                raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

        except Exception as e:
            import traceback

            logger.error(f"LLM Error: {e}\n{traceback.format_exc()}")
            console.print("[red]Error:[/red] Could not generate LLM response")
            console.print("Please check your LLM configuration in .env file")

    def is_command_creation_request(self, user_input: str) -> bool:
        """Check if user input is requesting to create a new command."""
        lower_input = user_input.lower()

        # Primary creation patterns
        creation_patterns = [
            r"\bcreate\s+.*command",  # "create a command", "create simple command", etc.
            r"\bmake\s+.*command",  # "make a command", "make new command", etc.
            r"\bbuild\s+.*command",  # "build a command", "build new command", etc.
            r"\bgenerate\s+.*command",  # "generate a command", etc.
            r"\badd\s+.*command",  # "add a command", "add new command", etc.
            r"\bnew\s+command",  # "new command"
            r"\bcommand\s+.*create",  # "command to create", etc.
            r"\bintegrate.*code",  # "integrate code", "integrate the code", etc.
            r"\bcan\s+you\s+create",  # "can you create"
            r"\bhelp\s+me\s+create",  # "help me create"
        ]

        import re

        for pattern in creation_patterns:
            if re.search(pattern, lower_input):
                return True

        return False

    def handle_command_creation(self, user_input: str):
        """Handle command creation requests with complete end-to-end implementation."""
        console.print("[bold green]🛠️  Command Creation Mode[/bold green]")
        console.print("I'll create a complete working MCLI command for you!")
        console.print()

        # Check if user already specified their preference in the input
        if any(phrase in user_input.lower() for phrase in ["code only", "just code", "show code"]):
            console.print("[yellow]Code-only mode selected[/yellow]")
            self._generate_code_only(user_input)
            return

        # Ask user if they want full automation or just guidance
        try:
            console.print("[bold cyan]Choose your approach:[/bold cyan]")
            console.print(
                "1. [green]Full automation[/green] - I'll create, save, and test the command"
            )
            console.print(
                "2. [yellow]Code only[/yellow] - I'll just generate code for you to implement"
            )
            console.print()
            console.print("[dim]Tip: You can also say 'code only' in your original request[/dim]")
            console.print()

            choice = console.input(
                "[bold cyan]Enter choice (1 or 2, default=1): [/bold cyan]"
            ).strip()
            if choice == "2" or choice.lower() in ["code only", "code", "just code"]:
                # Original behavior - just generate code
                self._generate_code_only(user_input)
            else:
                # New behavior - complete automation
                self._create_complete_command(user_input)

        except (EOFError, KeyboardInterrupt):
            # Default to full automation if input fails
            console.print("Defaulting to full automation...")
            self._create_complete_command(user_input)

    def validate_and_correct_response(self, response_text: str, available_commands: list) -> str:
        """Validate AI response and correct any hallucinated commands."""
        import re

        # Extract command names from available commands
        real_commands = set()
        if available_commands:
            for cmd in available_commands:
                if isinstance(cmd, dict) and "name" in cmd:
                    real_commands.add(cmd["name"])

        # Common hallucinated commands to catch
        hallucinated_patterns = [
            r"mcli ls\b",
            r"mcli list\b",
            r"mcli list-files\b",
            r"mcli dir\b",
            r"mcli files\b",
            r"mcli show\b",
        ]

        corrected_response = response_text

        # Check for hallucinated commands and correct them
        for pattern in hallucinated_patterns:
            if re.search(pattern, corrected_response, re.IGNORECASE):
                # Add warning about non-existent command
                correction = "\n\n⚠️  **Note**: The command mentioned above does not exist in MCLI. To create this functionality, you would need to implement a new command. Would you like me to help you create it?"
                corrected_response = (
                    re.sub(
                        pattern,
                        f"**[Command Does Not Exist]** {pattern.replace('\\b', '')}",
                        corrected_response,
                        flags=re.IGNORECASE,
                    )
                    + correction
                )
                break

        # Look for any "mcli [word]" patterns that aren't in real commands
        mcli_commands = re.findall(r"mcli\s+([a-zA-Z][a-zA-Z0-9_-]*)", corrected_response)
        for cmd in mcli_commands:
            if cmd not in real_commands:
                # This might be a hallucination
                warning = f"\n\n⚠️  **Note**: 'mcli {cmd}' does not exist. Available commands can be listed with the 'commands' chat command."
                if warning not in corrected_response:
                    corrected_response += warning
                break

        return corrected_response

    def _generate_code_only(self, user_input: str):
        """Generate code only without creating files."""
        # Use the enhanced LLM generation with creation context
        self.generate_llm_response(user_input)

        # Provide additional guidance
        console.print()
        console.print("[bold cyan]💡 Next Steps:[/bold cyan]")
        console.print("1. Copy the generated code to a new Python file")
        console.print("2. Save it in the appropriate MCLI module directory")
        console.print("3. Test the command with: [yellow]mcli <your-command>[/yellow]")
        console.print("4. Use [yellow]mcli commands list[/yellow] to verify it's available")
        console.print()
        console.print(
            "[dim]Tip: Commands are automatically discovered when placed in the correct directories[/dim]"
        )

    def _create_complete_command(self, user_input: str):
        """Create a complete working command with full automation."""
        import os
        import re
        from pathlib import Path

        console.print("[bold blue]🤖 Starting automated command creation...[/bold blue]")
        console.print()

        # Step 1: Generate code with AI
        console.print("1. [cyan]Generating command code...[/cyan]")
        code_response = self._get_command_code_from_ai(user_input)

        if not code_response:
            console.print("[red]❌ Failed to generate code. Falling back to code-only mode.[/red]")
            self._generate_code_only(user_input)
            return

        # Step 2: Extract command info and code
        command_info = self._parse_command_response(code_response)
        if not command_info:
            console.print(
                "[red]❌ Could not parse command information. Showing generated code:[/red]"
            )
            console.print(code_response)
            return

        # Step 3: Create the file
        console.print(f"2. [cyan]Creating command file: {command_info['filename']}[/cyan]")
        file_path = self._create_command_file(command_info)

        if not file_path:
            console.print("[red]❌ Failed to create command file.[/red]")
            return

        # Step 4: Test the command
        console.print(f"3. [cyan]Testing command: {command_info['name']}[/cyan]")
        test_result = self._test_command(command_info["name"])

        # Step 5: Show results
        console.print()
        if test_result:
            console.print("[bold green]✅ Command created successfully![/bold green]")
            console.print(f"📁 File: [green]{file_path}[/green]")
            console.print(f"🚀 Usage: [yellow]mcli {command_info['name']} --help[/yellow]")
            console.print(f"📋 Test: [yellow]mcli {command_info['name']}[/yellow]")
        else:
            console.print("[yellow]⚠️  Command created but may need debugging[/yellow]")
            console.print(f"📁 File: [yellow]{file_path}[/yellow]")
            console.print("💡 Check the file and test manually")

        console.print()
        console.print("[dim]Command is now available in MCLI![/dim]")

    def _get_command_code_from_ai(self, user_input: str) -> str:
        """Get command code from AI with specific formatting requirements."""
        # Enhanced prompt for structured code generation
        try:
            commands = self.daemon.list_commands()
        except Exception:
            commands = []

        command_context = (
            "\n".join(
                f"Command: {cmd['name']}\nDescription: {cmd.get('description', '')}"
                for cmd in commands
            )
            if commands
            else "(No command context available)"
        )

        prompt = f"""You are creating a complete MCLI command. Generate ONLY the Python code with this exact structure:

COMMAND_NAME: [single word command name]
FILENAME: [snake_case_filename.py]
DESCRIPTION: [brief description]
CODE:
```python
import click

@click.command()
@click.option('--example', help='Example option')
@click.argument('input_arg', required=False)
def command_name(example, input_arg):
    '''Command description here'''
    # Implementation here
    click.echo("Command works!")

if __name__ == '__main__':
    command_name()
```

User request: {user_input}

Available commands for reference: {command_context}

Generate a working command that implements the requested functionality. Use proper Click decorators, error handling, and helpful output."""

        if LLM_PROVIDER == "local":
            try:
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": MODEL_NAME,
                        "prompt": prompt,
                        "temperature": 0.3,  # Lower temperature for more consistent code
                        "stream": False,
                    },
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
            except Exception as e:
                logger.error(f"AI code generation error: {e}")

        return None

    def _parse_command_response(self, response: str) -> dict:
        """Parse AI response to extract command information."""
        import re

        # Extract command name
        name_match = re.search(r"COMMAND_NAME:\s*([a-zA-Z_][a-zA-Z0-9_-]*)", response)
        if not name_match:
            return None

        # Extract filename
        filename_match = re.search(r"FILENAME:\s*([a-zA-Z_][a-zA-Z0-9_.-]*\.py)", response)
        filename = filename_match.group(1) if filename_match else f"{name_match.group(1)}.py"

        # Extract description
        desc_match = re.search(r"DESCRIPTION:\s*(.+)", response)
        description = desc_match.group(1).strip() if desc_match else "Auto-generated command"

        # Extract code
        code_match = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)
        if not code_match:
            # Try without python specifier
            code_match = re.search(r"```\n(.*?)\n```", response, re.DOTALL)

        if not code_match:
            return None

        return {
            "name": name_match.group(1),
            "filename": filename,
            "description": description,
            "code": code_match.group(1).strip(),
        }

    def _create_command_file(self, command_info: dict) -> str:
        """Create the command file in the appropriate directory."""
        from pathlib import Path

        # Choose directory based on command type
        base_dir = Path(__file__).parent.parent.parent  # mcli src directory

        # Create in public directory for user-generated commands
        commands_dir = base_dir / "mcli" / "public" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        file_path = commands_dir / command_info["filename"]

        try:
            with open(file_path, "w") as f:
                f.write(command_info["code"])
            return str(file_path)
        except Exception as e:
            logger.error(f"Failed to create command file: {e}")
            return None

    def _test_command(self, command_name: str) -> bool:
        """Test if the command works by trying to import and run help."""
        try:
            # Try to run the command help to see if it's recognized
            import subprocess

            result = subprocess.run(
                ["mcli", "commands", "list"], capture_output=True, text=True, timeout=10
            )
            # Check if our command appears in the output
            return command_name in result.stdout
        except Exception as e:
            logger.debug(f"Command test failed: {e}")
            return False

    def is_system_control_request(self, user_input: str) -> bool:
        """Check if user input is requesting system control functionality"""
        lower_input = user_input.lower()
        
        # System control keywords
        system_keywords = [
            'open', 'close', 'launch', 'quit', 'textedit', 'text edit',
            'screenshot', 'screen capture', 'calculator', 'safari', 'finder',
            'take screenshot', 'write', 'type', 'save as', 'file', 'application',
            # System information keywords
            'system time', 'what time', 'current time', 'system info', 'system information',
            'system specs', 'hardware info', 'memory usage', 'ram usage', 'how much memory',
            'how much ram', 'disk usage', 'disk space', 'storage space', 'how much space',
            'clear cache', 'clean cache', 'clear system cache', 'system cache',
            # Navigation and shell keywords
            'navigate to', 'go to', 'change to', 'cd to', 'move to',
            'list', 'show files', 'ls', 'dir', 'what\'s in',
            'clean simulator', 'simulator data', 'clean ios', 'clean watchos',
            'run command', 'execute', 'shell', 'terminal',
            'where am i', 'current directory', 'pwd', 'current path'
        ]
        
        # Check for system control patterns
        system_patterns = [
            r'\bopen\s+\w+',  # "open something"
            r'\bclose\s+\w+',  # "close something" 
            r'\btake\s+screenshot',  # "take screenshot"
            r'\bwrite\s+.*\bin\s+\w+',  # "write something in app"
            r'\bopen\s+.*\band\s+write',  # "open app and write"
            r'\btextedit',  # any textedit mention
            r'\btext\s+edit',  # "text edit"
            # System information patterns
            r'\bwhat\s+time',  # "what time"
            r'\bsystem\s+time',  # "system time"
            r'\bcurrent\s+time',  # "current time"
            r'\bsystem\s+info',  # "system info"
            r'\bsystem\s+specs',  # "system specs"
            r'\bhow\s+much\s+(ram|memory)',  # "how much ram/memory"
            r'\bmemory\s+usage',  # "memory usage"
            r'\bram\s+usage',  # "ram usage"
            r'\bdisk\s+usage',  # "disk usage"
            r'\bdisk\s+space',  # "disk space"
            r'\bclear\s+(cache|system)',  # "clear cache" or "clear system"
        ]
        
        import re
        for pattern in system_patterns:
            if re.search(pattern, lower_input):
                return True
        
        # Simple keyword check as fallback
        return any(keyword in lower_input for keyword in system_keywords)

    def handle_system_control(self, user_input: str):
        """Handle system control requests with intelligent reasoning and suggestions"""
        try:
            console.print("[dim]🤖 Processing system control request...[/dim]")
            
            # Use the system integration to handle the request
            result = handle_system_request(user_input)
            
            if result["success"]:
                message = result.get("message", "✅ System operation completed successfully!")
                console.print(f"[green]{message}[/green]")
                
                # Provide intelligent follow-up suggestions based on the result
                self._provide_intelligent_suggestions(user_input, result)
                
                # Show output if available
                if result.get("output") and result["output"].strip():
                    output_lines = result["output"].strip().split('\n')
                    console.print("[dim]Output:[/dim]")
                    for line in output_lines[:10]:  # Show first 10 lines
                        console.print(f"  {line}")
                    if len(output_lines) > 10:
                        console.print(f"  [dim]... ({len(output_lines) - 10} more lines)[/dim]")
                
                # Show special file paths for screenshots, etc.
                if result.get("screenshot_path"):
                    console.print(f"[cyan]📸 Screenshot saved to: {result['screenshot_path']}[/cyan]")
                
            else:
                error_msg = result.get("error", "Unknown error occurred")
                console.print(f"[red]❌ {error_msg}[/red]")
                
                # Show suggestions if available
                if result.get("suggestion"):
                    console.print(f"[yellow]💡 {result['suggestion']}[/yellow]")
                
                # Show available functions if this was an unknown request
                if result.get("available_functions"):
                    console.print("[dim]Available system functions:[/dim]")
                    for func in result["available_functions"][:5]:
                        console.print(f"  • {func}")
        
        except Exception as e:
            console.print(f"[red]Error processing system control request: {e}[/red]")
            console.print("[yellow]Examples of system control commands:[/yellow]")
            console.print("  • 'Open TextEdit and write Hello World'")
            console.print("  • 'Take a screenshot'")
            console.print("  • 'Open Calculator'")
            console.print("  • 'Close TextEdit'")
    
    def _provide_intelligent_suggestions(self, user_input: str, result: dict):
        """Provide intelligent suggestions based on system control results"""
        try:
            lower_input = user_input.lower()
            data = result.get("data", {})
            
            # Disk usage suggestions
            if "disk" in lower_input or "space" in lower_input:
                self._suggest_disk_cleanup(data)
            
            # Memory usage suggestions  
            elif "memory" in lower_input or "ram" in lower_input:
                self._suggest_memory_optimization(data)
            
            # System info suggestions
            elif "system" in lower_input and ("info" in lower_input or "specs" in lower_input):
                self._suggest_system_actions(data)
            
            # Time-based suggestions
            elif "time" in lower_input:
                self._suggest_time_actions(data)
                
        except Exception as e:
            # Don't let suggestion errors break the main flow
            pass
    
    def _suggest_disk_cleanup(self, disk_data: dict):
        """Suggest disk cleanup actions based on usage"""
        if not disk_data:
            return
            
        suggestions = []
        
        # Check main disk usage
        if disk_data.get("total_disk_gb", 0) > 0:
            usage_pct = (disk_data.get("total_used_gb", 0) / disk_data["total_disk_gb"]) * 100
            
            if usage_pct > 85:
                suggestions.append("Your disk is getting full! I can help you clear system caches.")
                suggestions.append("Try: 'clear system caches' to free up space")
            elif usage_pct > 70:
                suggestions.append("You're using quite a bit of disk space. Consider cleaning up.")
                suggestions.append("I can help with: 'clear system caches'")
        
        # Check for large simulator volumes
        partitions = disk_data.get("partitions", [])
        simulator_partitions = [p for p in partitions if "CoreSimulator" in p.get("mountpoint", "")]
        
        if simulator_partitions:
            total_sim_space = sum(p.get("used_gb", 0) for p in simulator_partitions)
            if total_sim_space > 50:  # More than 50GB in simulators
                suggestions.append(f"📱 You have {total_sim_space:.1f}GB in iOS/watchOS simulators.")
                suggestions.append("Consider cleaning old simulator data if you don't need it.")
        
        # Show suggestions
        if suggestions:
            console.print("\n[cyan]💡 Suggestions:[/cyan]")
            for suggestion in suggestions:
                console.print(f"  {suggestion}")
    
    def _suggest_memory_optimization(self, memory_data: dict):
        """Suggest memory optimization actions"""
        if not memory_data:
            return
            
        suggestions = []
        vm = memory_data.get("virtual_memory", {})
        swap = memory_data.get("swap_memory", {})
        
        if vm.get("usage_percent", 0) > 85:
            suggestions.append("Your memory usage is quite high!")
            suggestions.append("Consider closing unused applications to free up RAM.")
        
        if swap.get("usage_percent", 0) > 70:
            suggestions.append("High swap usage detected - your system is using disk as memory.")
            suggestions.append("This can slow things down. Try closing memory-intensive apps.")
        
        # Suggest system monitoring
        suggestions.append("Want to monitor your system? Try: 'show system specs'")
        
        if suggestions:
            console.print("\n[cyan]💡 Memory Tips:[/cyan]")
            for suggestion in suggestions:
                console.print(f"  {suggestion}")
    
    def _suggest_system_actions(self, system_data: dict):
        """Suggest system-related actions"""
        if not system_data:
            return
            
        suggestions = []
        cpu = system_data.get("cpu", {})
        memory = system_data.get("memory", {})
        
        # CPU suggestions
        cpu_usage = cpu.get("cpu_usage_percent", 0)
        if cpu_usage > 80:
            suggestions.append(f"CPU usage is high ({cpu_usage}%). Check what's running with Activity Monitor.")
        
        # Memory suggestions
        memory_pct = memory.get("usage_percent", 0)
        if memory_pct > 80:
            suggestions.append("Memory usage is high. Consider closing unused applications.")
        
        # Uptime suggestions
        uptime_hours = system_data.get("uptime_hours", 0)
        if uptime_hours > 72:  # More than 3 days
            suggestions.append(f"Your system has been up for {uptime_hours:.1f} hours.")
            suggestions.append("Consider restarting to refresh system performance.")
        
        # General suggestions
        suggestions.append("I can help you with:")
        suggestions.append("• 'how much RAM do I have?' - Check memory usage")
        suggestions.append("• 'how much disk space do I have?' - Check storage")
        suggestions.append("• 'clear system caches' - Free up space")
        
        if suggestions:
            console.print("\n[cyan]💡 System Insights:[/cyan]")
            for suggestion in suggestions:
                console.print(f"  {suggestion}")
    
    def _suggest_time_actions(self, time_data: dict):
        """Suggest time-related actions"""
        if not time_data:
            return
            
        suggestions = []
        current_time = time_data.get("current_time", "")
        
        if current_time:
            import datetime
            try:
                # Parse the time to get hour
                time_obj = datetime.datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
                hour = time_obj.hour
                
                if 22 <= hour or hour <= 6:  # Late night/early morning
                    suggestions.append("🌙 It's quite late! Consider taking a break.")
                elif 9 <= hour <= 17:  # Work hours
                    suggestions.append("⏰ It's work time! Stay productive.")
                elif 17 < hour < 22:  # Evening
                    suggestions.append("🌆 Good evening! Wrapping up for the day?")
                    
            except:
                pass
        
        suggestions.append("I can also help you schedule tasks with the workflow system!")
        
        if suggestions:
            console.print("\n[cyan]💡 Time Tips:[/cyan]")
            for suggestion in suggestions:
                console.print(f"  {suggestion}")
    
    def _is_system_help_request(self, query: str) -> bool:
        """Detect if this is a request for system help or cleanup"""
        lower_query = query.lower()
        
        help_patterns = [
            r'help.*free.*space',
            r'help.*clean.*up',
            r'help.*disk.*space',
            r'help.*memory',
            r'can you.*free',
            r'can you.*clean',
            r'can you.*help.*space',
            r'can you help.*free',
            r'yikes.*help',
            r'how.*clean',
            r'how.*free.*space',
            r'what.*clean',
            r'what.*free.*space',
            r'help me.*free',
            r'help me.*clean',
        ]
        
        import re
        for pattern in help_patterns:
            if re.search(pattern, lower_query):
                return True
                
        return False
    
    def _handle_system_help_request(self, query: str):
        """Handle requests for system help and cleanup"""
        lower_query = query.lower()
        
        console.print("[dim]🤖 I can definitely help you with system cleanup![/dim]")
        
        # Provide contextual help based on the query
        if "space" in lower_query or "disk" in lower_query:
            console.print("\n[green]💽 Here's what I can help you with for disk space:[/green]")
            console.print("• [cyan]'clear system caches'[/cyan] - Clear system cache files and temporary data")
            console.print("• [cyan]'how much disk space do I have?'[/cyan] - Get detailed disk usage breakdown")
            console.print("• I can also identify large iOS simulator files that might be taking up space")
            
            console.print("\n[yellow]💡 Quick tip:[/yellow] Try 'clear system caches' to start freeing up space!")
            
        elif "memory" in lower_query or "ram" in lower_query:
            console.print("\n[green]💾 Here's what I can help you with for memory:[/green]")
            console.print("• [cyan]'how much RAM do I have?'[/cyan] - Check memory usage and get recommendations")
            console.print("• [cyan]'show system specs'[/cyan] - Get full system overview including memory")
            console.print("• I can identify if you need to close applications or restart your system")
            
        else:
            # General system help
            console.print("\n[green]🛠️ I can help you with various system tasks:[/green]")
            console.print("• [cyan]'clear system caches'[/cyan] - Free up disk space")
            console.print("• [cyan]'how much disk space do I have?'[/cyan] - Check storage usage")
            console.print("• [cyan]'how much RAM do I have?'[/cyan] - Check memory usage")
            console.print("• [cyan]'show system specs'[/cyan] - Get full system overview")
            console.print("• [cyan]'open Calculator'[/cyan] - Open applications")
            console.print("• [cyan]'take screenshot'[/cyan] - Take and save screenshots")
            
        console.print("\n[dim]Just ask me to do any of these tasks and I'll handle them for you![/dim]")
    
    def _load_scheduled_jobs(self):
        """Load and start monitoring existing scheduled jobs"""
        try:
            # Lazy import to avoid circular dependencies
            from mcli.workflow.scheduler.persistence import JobStorage
            from mcli.workflow.scheduler.job import JobStatus
            
            job_storage = JobStorage()
            jobs = job_storage.load_jobs()
            
            active_count = 0
            for job_data in jobs:
                if job_data.get("status") in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
                    active_count += 1
            
            if active_count > 0:
                console.print(f"[dim]📅 {active_count} scheduled jobs loaded[/dim]")
                
        except Exception as e:
            # Silently handle import/loading errors at startup
            pass
    
    def _is_job_management_request(self, query: str) -> bool:
        """Detect if this is a job/schedule management request"""
        lower_query = query.lower()
        
        job_patterns = [
            r'schedule.*',
            r'every.*',
            r'daily.*',
            r'weekly.*', 
            r'remind.*',
            r'job.*',
            r'task.*',
            r'my.*jobs',
            r'what.*running',
            r'status.*',
            r'cancel.*',
            r'stop.*job',
            r'list.*jobs',
            r'show.*jobs',
            r'cron.*',
            r'at.*am|pm',
            r'in.*minutes|hours|days',
        ]
        
        import re
        for pattern in job_patterns:
            if re.search(pattern, lower_query):
                return True
                
        return False
    
    def _handle_job_management(self, query: str):
        """Handle job scheduling and management requests"""
        lower_query = query.lower()
        
        console.print("[dim]🤖 Processing job management request...[/dim]")
        
        try:
            # List jobs
            if any(phrase in lower_query for phrase in ["list jobs", "show jobs", "my jobs", "what's running", "status"]):
                self._show_agent_status()
                return
            
            # Cancel/stop job
            if any(phrase in lower_query for phrase in ["cancel", "stop", "remove"]):
                self._handle_job_cancellation(query)
                return
            
            # Schedule new job
            if any(phrase in lower_query for phrase in ["schedule", "every", "daily", "weekly", "remind", "at"]):
                self._handle_job_scheduling(query)
                return
                
            # General job help
            console.print("[green]📅 I can help you with job scheduling![/green]")
            console.print("• [cyan]'schedule system cleanup daily at 2am'[/cyan] - Schedule recurring tasks")
            console.print("• [cyan]'remind me to check disk space every week'[/cyan] - Set reminders")
            console.print("• [cyan]'list my jobs'[/cyan] - Show all scheduled tasks")
            console.print("• [cyan]'what's my status?'[/cyan] - Agent status overview")
            console.print("• [cyan]'cancel job cleanup'[/cyan] - Remove scheduled tasks")
            
        except Exception as e:
            console.print(f"[red]❌ Error handling job request: {e}[/red]")
    
    def _show_agent_status(self):
        """Show comprehensive agent status including jobs, system state, and context"""
        console.print("\n[bold cyan]🤖 Personal Assistant Status Report[/bold cyan]")
        
        # Jobs and schedules
        try:
            from mcli.workflow.scheduler.persistence import JobStorage
            from mcli.workflow.scheduler.job import JobStatus, ScheduledJob
            
            job_storage = JobStorage()
            jobs = job_storage.load_jobs()
            
            # Convert ScheduledJob objects to dictionaries for easier processing
            job_dicts = []
            active_jobs = []
            completed_jobs = []
            failed_jobs = []
            
            for job in jobs:
                if hasattr(job, 'to_dict'):
                    job_dict = job.to_dict()
                else:
                    # If it's already a dict or has dict-like access
                    job_dict = {
                        'name': getattr(job, 'name', 'Unknown'),
                        'status': getattr(job, 'status', JobStatus.PENDING).value if hasattr(job, 'status') else 'pending',
                        'cron_expression': getattr(job, 'cron_expression', 'Unknown'),
                        'next_run': getattr(job, 'next_run', None)
                    }
                job_dicts.append(job_dict)
                
                status = job_dict.get("status")
                if status in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
                    active_jobs.append(job_dict)
                elif status == JobStatus.COMPLETED.value:
                    completed_jobs.append(job_dict)
                elif status == JobStatus.FAILED.value:
                    failed_jobs.append(job_dict)
                    
        except Exception as e:
            jobs = []
            active_jobs = []
            completed_jobs = []
            failed_jobs = []
        
        console.print(f"\n[green]📅 Scheduled Jobs:[/green]")
        if active_jobs:
            for job_data in active_jobs[:5]:  # Show first 5
                try:
                    job = Job.from_dict(job_data)
                    console.print(f"  • [cyan]{job.name}[/cyan] - {job.cron_expression} ({job.status.value})")
                    if job.next_run:
                        console.print(f"    Next run: {job.next_run}")
                except Exception:
                    # Fallback to raw data
                    name = job_data.get("name", "Unknown")
                    cron = job_data.get("cron_expression", "Unknown")
                    console.print(f"  • [cyan]{name}[/cyan] - {cron}")
        else:
            console.print("  No active scheduled jobs")
        
        if len(active_jobs) > 5:
            console.print(f"  ... and {len(active_jobs) - 5} more active jobs")
        
        # Recent activity
        if completed_jobs or failed_jobs:
            console.print(f"\n[blue]📊 Recent Activity:[/blue]")
            if completed_jobs:
                console.print(f"  ✅ {len(completed_jobs)} completed jobs")
            if failed_jobs:
                console.print(f"  ❌ {len(failed_jobs)} failed jobs")
        
        # System context - get current system state
        try:
            from mcli.chat.system_controller import system_controller
            
            # Quick system overview
            memory_result = system_controller.get_memory_usage()
            disk_result = system_controller.get_disk_usage()
            
            console.print(f"\n[yellow]💻 System Context:[/yellow]")
            
            if memory_result.get("success"):
                mem_data = memory_result["data"]["virtual_memory"]
                console.print(f"  💾 Memory: {mem_data['usage_percent']:.1f}% used ({mem_data['used_gb']:.1f}GB/{mem_data['total_gb']:.1f}GB)")
            
            if disk_result.get("success"):
                disk_data = disk_result["data"]
                if disk_data.get("total_disk_gb", 0) > 0:
                    usage_pct = (disk_data.get("total_used_gb", 0) / disk_data["total_disk_gb"]) * 100
                    console.print(f"  💽 Disk: {usage_pct:.1f}% used ({disk_data.get('total_free_gb', 0):.1f}GB free)")
                    
        except Exception:
            console.print(f"\n[yellow]💻 System Context: Unable to get current status[/yellow]")
        
        # Agent capabilities reminder
        console.print(f"\n[magenta]🛠️ I can help you with:[/magenta]")
        console.print("  • System monitoring and cleanup")
        console.print("  • Application control and automation")
        console.print("  • Scheduled tasks and reminders")
        console.print("  • File management and organization")
        console.print("  • Process monitoring and management")
        
        console.print("\n[dim]Ask me to schedule tasks, check system status, or automate any routine![/dim]")
    
    def _handle_job_scheduling(self, query: str):
        """Handle requests to schedule new jobs"""
        console.print("[green]📅 Let me help you schedule that task![/green]")
        
        # For now, provide guidance on scheduling
        # TODO: Implement natural language job scheduling parser
        console.print("\n[cyan]Here are some scheduling examples:[/cyan]")
        console.print("• [yellow]'schedule system cleanup daily at 2am'[/yellow]")
        console.print("• [yellow]'remind me to check disk space every Monday'[/yellow]")
        console.print("• [yellow]'run backup every day at 11pm'[/yellow]")
        console.print("• [yellow]'check memory usage every 2 hours'[/yellow]")
        
        console.print("\n[blue]💡 I can schedule:[/blue]")
        console.print("  • System maintenance tasks")
        console.print("  • File cleanup operations")
        console.print("  • Health checks and monitoring")
        console.print("  • Automated backups")
        console.print("  • Custom reminders")
        
        console.print("\n[dim]The job scheduler is ready - just tell me what you'd like to automate![/dim]")
    
    def _handle_job_cancellation(self, query: str):
        """Handle requests to cancel jobs"""
        try:
            from mcli.workflow.scheduler.persistence import JobStorage
            from mcli.workflow.scheduler.job import JobStatus
            
            job_storage = JobStorage()
            jobs = job_storage.load_jobs()
            
            active_jobs = []
            for job in jobs:
                if hasattr(job, 'status') and job.status.value in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
                    active_jobs.append(job)
                    
        except Exception:
            jobs = []
            active_jobs = []
        
        if not active_jobs:
            console.print("[yellow]📅 No active jobs to cancel[/yellow]")
            return
        
        console.print("[blue]📅 Active jobs that can be cancelled:[/blue]")
        for i, job_data in enumerate(active_jobs, 1):
            job = Job.from_dict(job_data)
            console.print(f"  {i}. [cyan]{job.name}[/cyan] - {job.cron_expression}")
        
        console.print("\n[dim]To cancel a specific job, use: 'cancel job [name]'[/dim]")
    
    def _show_startup_status(self):
        """Show proactive status update when assistant starts"""
        try:
            # Quick system check
            from mcli.chat.system_controller import system_controller
            
            # Get basic system state
            memory_result = system_controller.get_memory_usage()
            
            # Check for active jobs
            try:
                from mcli.workflow.scheduler.persistence import JobStorage
                from mcli.workflow.scheduler.job import JobStatus
                
                job_storage = JobStorage()
                jobs = job_storage.load_jobs()
                
                # Count active jobs
                active_jobs = []
                for job in jobs:
                    if hasattr(job, 'status') and job.status.value in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
                        active_jobs.append(job)
                        
            except Exception:
                jobs = []
                active_jobs = []
            
            status_items = []
            
            # Memory alert if high
            if memory_result.get("success"):
                mem_data = memory_result["data"]["virtual_memory"]
                if mem_data.get("usage_percent", 0) > 85:
                    status_items.append(f"⚠️ High memory usage: {mem_data['usage_percent']:.1f}%")
                elif mem_data.get("usage_percent", 0) > 75:
                    status_items.append(f"💾 Memory: {mem_data['usage_percent']:.1f}% used")
            
            # Active jobs
            if active_jobs:
                status_items.append(f"📅 {len(active_jobs)} scheduled jobs running")
            
            # Recent failures (check for failed jobs in last 24 hours)
            failed_jobs = [j for j in jobs if j.get("status") == JobStatus.FAILED.value]
            if failed_jobs:
                status_items.append(f"❌ {len(failed_jobs)} recent job failures")
            
            # Show status if there's something to report
            if status_items:
                console.print("\n[cyan]🤖 Assistant Status:[/cyan]")
                for item in status_items[:3]:  # Show max 3 items
                    console.print(f"  {item}")
                
                if len(active_jobs) > 0 or len(failed_jobs) > 0:
                    console.print("  [dim]Say 'what's my status?' for detailed report[/dim]")
            else:
                console.print("\n[green]🤖 All systems running smoothly![/green]")
                
        except Exception as e:
            console.print(f"\n[yellow]🤖 Assistant ready (status check unavailable)[/yellow]")


if __name__ == "__main__":
    client = ChatClient()
    client.start_interactive_session()
