import os
import readline
from typing import List, Dict, Optional
from mcli.lib.toml.toml import read_from_toml
from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console


# Load config from config.toml
CONFIG_PATH = "config.toml"
config = {}
try:
    config = read_from_toml(CONFIG_PATH, "llm") or {}
except Exception:
    config = {}

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
        
    def start_interactive_session(self):
        """Start the chat interface"""
        console.print("[bold green]MCLI Chat Assistant[/bold green] (type 'exit' to quit)")
        console.print("How can I help you with your MCLI commands today?")
        
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
        # Store interaction
        self.history.append({"user": user_input})
        
        # First check for command-related queries
        if any(keyword in user_input.lower() for keyword in ["command", "list", "show", "find", "search"]):
            self.handle_command_queries(user_input)
        else:
            self.generate_llm_response(user_input)

    def handle_command_queries(self, query: str):
        """Handle command-related queries using existing command registry"""
        commands = self.daemon.list_commands().get("commands", [])
        
        # Simple keyword matching for initial implementation
        if "list commands" in query.lower():
            self.list_commands(commands)
        elif "search" in query.lower() or "find" in query.lower():
            self.search_commands(query, commands)
        else:
            self.generate_llm_response(query)

    def list_commands(self, commands: List[Dict]):
        """List available commands"""
        if not commands:
            console.print("No commands found")
            return
            
        console.print("[bold]Available Commands:[/bold]")
        for cmd in commands:
            console.print(f"• [green]{cmd['name']}[/green] ({cmd['language']})")
            if cmd['description']:
                console.print(f"  {cmd['description']}")
            if cmd['tags']:
                console.print(f"  Tags: {', '.join(cmd['tags'])}")
            console.print()

    def search_commands(self, query: str, commands: List[Dict]):
        """Search commands based on query"""
        search_term = query.lower().replace("search", "").replace("find", "").strip()
        results = [
            cmd for cmd in commands
            if (search_term in cmd['name'].lower() or
                search_term in (cmd['description'] or "").lower() or
                any(search_term in tag.lower() for tag in cmd['tags']))
        ]
        
        if not results:
            console.print(f"No commands found matching '[yellow]{search_term}[/yellow]'")
            return
            
        console.print(f"[bold]Matching Commands for '{search_term}':[/bold]")
        for cmd in results:
            console.print(f"• [green]{cmd['name']}[/green] ({cmd['language']})")
            console.print(f"  [italic]{cmd['description']}[/italic]")
            console.print()

    def generate_llm_response(self, query: str):
        """Generate response using LLM integration"""
        try:
            commands = self.daemon.list_commands().get("commands", [])
            command_context = "\n".join(
                f"Command: {cmd['name']}\nDescription: {cmd.get('description', '')}\nTags: {', '.join(cmd.get('tags', []))}"
                for cmd in commands
            )
            
            prompt = f"""SYSTEM: {SYSTEM_PROMPT}\n\nAvailable Commands:\n{command_context}\n\nUSER QUERY: {query}\n\nRespond with:\n1. A natural language answer\n2. Relevant commands in markdown format\n3. Example usage in a code block"""

            if LLM_PROVIDER == "openai":
                from openai import OpenAI
                api_key = OPENAI_API_KEY or "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"
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=TEMPERATURE
                )
                return console.print(response.choices[0].message.content)

            elif LLM_PROVIDER == "anthropic":
                from anthropic import Anthropic
                api_key = config.get("anthropic_api_key", None)
                client = Anthropic(api_key=api_key)
                response = client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=1000,
                    temperature=TEMPERATURE,
                    system=SYSTEM_PROMPT or "",
                    messages=[{"role": "user", "content": query}]
                )
                return console.print(response.content)

            else:
                raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")
            
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            console.print("[red]Error:[/red] Could not generate LLM response")
            console.print("Please check your LLM configuration in .env file")

if __name__ == "__main__":
    client = ChatClient()
    client.start_interactive_session()
