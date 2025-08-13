import os
import readline
from typing import List, Dict, Optional
from mcli.lib.toml.toml import read_from_toml
from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.discovery.command_discovery import get_command_discovery
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console



# Load config from config.toml
CONFIG_PATH = "config.toml"
config = {}
try:
    config = read_from_toml(CONFIG_PATH, "llm") or {}
except Exception:
    # Silently handle config loading errors
    config = {}

if not config or not config.get("openai_api_key"):
    # Silently set defaults - don't expose config details
    config = {
        "provider": "openai",
        "model": "gpt-4-turbo", 
        "temperature": 0.7,
        "system_prompt": "You are the MCLI Chat Assistant."
    }

logger = get_logger(__name__)

# Fallbacks if not set in config.toml
LLM_PROVIDER = config.get("provider", "openai")
MODEL_NAME = config.get("model", "gpt-4-turbo")
OPENAI_API_KEY = config.get("openai_api_key", None)
TEMPERATURE = float(config.get("temperature", 0.7))
SYSTEM_PROMPT = config.get("system_prompt", None)

class ChatClient:
    """Interactive chat client for MCLI command management"""
    
    def __init__(self):
        self.daemon = get_daemon_client()
        self.history = []
        self.session_active = True
        self._ensure_daemon_running()
        
    def start_interactive_session(self):
        """Start the chat interface"""
        console.print("[bold green]MCLI Chat Assistant[/bold green] (type 'exit' to quit)")
        console.print("How can I help you with your MCLI commands today?")
        console.print("\n[bold cyan]Available Commands:[/bold cyan]")
        console.print("• [yellow]commands[/yellow] - List available functions")
        console.print("• [yellow]run <command> [args][/yellow] - Execute command in container")
        console.print("• [yellow]ps[/yellow] - List running processes (Docker-style)")
        console.print("• [yellow]logs <id>[/yellow] - View process logs")
        console.print("• [yellow]inspect <id>[/yellow] - Detailed process info")
        console.print("• [yellow]start/stop <id>[/yellow] - Control process lifecycle")
        console.print("• Ask questions about functions and codebase\n")
        
        while self.session_active:
            try:
                user_input = console.input("[bold cyan]>>> [/bold cyan]").strip()
                if not user_input:
                    continue
                    
                if user_input.lower() in ('exit', 'quit'):
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
        
        # Check for 'run <command> [args...]' pattern (containerized execution)
        if user_input.lower().startswith("run "):
            command_part = user_input[4:].strip()
            
            # Handle natural language patterns like "run the hello world command"
            if " command" in command_part.lower():
                # Extract the actual command name from natural language
                command_part = command_part.lower().replace(" command", "").replace("the ", "").strip()
            
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

        if daemon_available and any(keyword in user_input.lower() for keyword in ["command", "list", "show", "find", "search"]):
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
            "call the", "execute the", "run the", "call", "execute", 
            "hello world", "hello-world", "helloworld"
        ]
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
            r'(?:call|execute|run)\s+(?:the\s+)?([a-zA-Z0-9\-_]+)(?:\s+command)?',
            r'([a-zA-Z0-9\-_]+)\s+command',
            r'the\s+([a-zA-Z0-9\-_]+)\s+command'
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
            logger.debug(f"Could not fetch commands from daemon: {e}. Falling back to LLM-only mode.")
            return self.generate_llm_response(query)

        # Simple keyword matching for initial implementation
        lowered = query.lower()
        if "list command" in lowered or "show command" in lowered or "available command" in lowered or "what can i do" in lowered or "commands" in lowered:
            self.list_commands()  # Always use discovery system, ignore daemon commands
        elif "search" in lowered or "find" in lowered:
            self.search_commands(query)  # Always use discovery system, ignore daemon commands
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
            if 'full_name' in cmd:
                # New discovery format
                console.print(f"• [green]{cmd['full_name']}[/green]")
            else:
                # Old daemon format
                status = "[INACTIVE] " if not cmd.get('is_active', True) else ""
                console.print(f"{status}• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})")
            
            if cmd.get('description'):
                console.print(f"  {cmd['description']}")
            if cmd.get('module'):
                console.print(f"  Module: {cmd['module']}")
            elif cmd.get('tags'):
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
                cmd for cmd in commands
                if (search_term in cmd['name'].lower() or
                    search_term in (cmd['description'] or "").lower() or
                    any(search_term in tag.lower() for tag in cmd.get('tags', [])))
            ]
        
        if not results:
            console.print(f"No commands found matching '[yellow]{search_term}[/yellow]'")
            return
            
        console.print(f"[bold]Matching Commands for '{search_term}' ({len(results)}):[/bold]")
        for cmd in results[:10]:  # Show first 10 results
            if 'full_name' in cmd:
                # New discovery format
                console.print(f"• [green]{cmd['full_name']}[/green]")
            else:
                # Old daemon format
                console.print(f"• [green]{cmd['name']}[/green] ({cmd.get('language', 'python')})")
            
            console.print(f"  [italic]{cmd['description']}[/italic]")
            console.print()
        
        if len(results) > 10:
            console.print(f"[dim]... and {len(results) - 10} more results[/dim]")
    
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
                console.print("[bold]CONTAINER ID   NAME           COMMAND                  STATUS    UPTIME     CPU      MEMORY[/bold]")
                for proc in processes:
                    console.print(f"{proc['id']:<13} {proc['name']:<14} {proc['command'][:24]:<24} {proc['status']:<9} {proc['uptime']:<10} {proc['cpu']:<8} {proc['memory']}")
            else:
                console.print(f"[red]Error: Failed to get process list (HTTP {response.status_code})[/red]")
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
                if info.get('stats'):
                    stats = info['stats']
                    console.print(f"CPU: {stats.get('cpu_percent', 0):.1f}%")
                    console.print(f"Memory: {stats.get('memory_mb', 0):.1f} MB")
                    console.print(f"Uptime: {stats.get('uptime_seconds', 0)} seconds")
            elif response.status_code == 404:
                console.print(f"[red]Process {process_id} not found[/red]")
            else:
                console.print(f"[red]Error: Failed to inspect process (HTTP {response.status_code})[/red]")
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
                console.print(f"[red]Error: Failed to stop process (HTTP {response.status_code})[/red]")
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
                console.print(f"[red]Error: Failed to start process (HTTP {response.status_code})[/red]")
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
                    if cmd['name'].lower() == command.lower():
                        matching_cmd = cmd
                        break
                
                if matching_cmd:
                    # Execute via the existing command system but in a container
                    response = requests.post(f"{self.daemon.base_url}/processes/run", json={
                        "name": f"cmd-{matching_cmd['name']}",
                        "command": "python" if matching_cmd['language'] == "python" else matching_cmd['language'],
                        "args": ["-c", matching_cmd['code']] + args,
                        "detach": True
                    })
                    
                    if response.status_code == 200:
                        result = response.json()
                        console.print(f"[green]Started containerized command '{matching_cmd['name']}' with ID {result['id'][:12]}[/green]")
                        console.print("Use 'logs <id>' to view output or 'ps' to see status")
                    else:
                        console.print(f"[red]Failed to start containerized command[/red]")
                    return
            except Exception:
                pass  # Fall through to shell command execution
            
            # Execute as shell command in container
            response = requests.post(f"{self.daemon.base_url}/processes/run", json={
                "name": f"shell-{command}",
                "command": command,
                "args": args,
                "detach": True
            })
            
            if response.status_code == 200:
                result = response.json()
                console.print(f"[green]Started containerized process with ID {result['id'][:12]}[/green]")
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
                from mcli.workflow.daemon.api_daemon import APIDaemonService
                import threading
                import time
                
                # Start daemon in a separate thread
                daemon_service = APIDaemonService()
                daemon_thread = threading.Thread(target=daemon_service.start, daemon=True)
                daemon_thread.start()
                
                # Wait for daemon to be ready with progress
                for i in range(10):  # Wait up to 10 seconds
                    time.sleep(1)
                    if self.daemon.is_running():
                        console.print(f"[green]✅ MCLI daemon started successfully on {self.daemon.base_url}[/green]")
                        return
                    if i % 2 == 0:  # Show progress every 2 seconds
                        console.print(f"[dim]Waiting for daemon to start... ({i+1}/10)[/dim]")
                
                console.print("[red]❌ Daemon failed to start within 10 seconds[/red]")
                console.print("[yellow]Try starting manually: mcli workflow api-daemon start[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Could not start daemon: {e}[/red]")
            console.print("[yellow]Try starting manually: mcli workflow api-daemon start[/yellow]")

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

            command_context = "\n".join(
                f"Command: {cmd['name']}\nDescription: {cmd.get('description', '')}\nTags: {', '.join(cmd.get('tags', []))}\nStatus: {'INACTIVE' if not cmd.get('is_active', True) else 'ACTIVE'}"
                for cmd in commands
            ) if commands else "(No command context available)"

            prompt = f"""SYSTEM: {SYSTEM_PROMPT}\n\nAvailable Commands (including inactive):\n{command_context}\n\nUSER QUERY: {query}\n\nRespond with:\n1. A natural language answer\n2. Relevant commands in markdown format\n3. Example usage in a code block"""

            if LLM_PROVIDER == "openai":
                from openai import OpenAI
                if not OPENAI_API_KEY:
                    console.print("[red]OpenAI API key not configured. Please set it in config.toml[/red]")
                    return
                client = OpenAI(api_key=OPENAI_API_KEY)
                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=TEMPERATURE
                    )
                    # Only print the first section (natural language answer) before any markdown/code block
                    content = response.choices[0].message.content
                    # Split on '```' or '2.' or 'Relevant commands' to avoid printing command/code blocks
                    import re
                    # Try to split on numbered sections or code block
                    split_patterns = [r'\n2\.', r'\n```', r'\nRelevant commands', r'\n3\.', r'\n- \*\*Command']
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
                        messages=[{"role": "user", "content": query}]
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

if __name__ == "__main__":
    client = ChatClient()
    client.start_interactive_session()
