import os
import readline
from typing import List, Dict, Optional
from dotenv import load_dotenv
from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

# Load environment variables
load_dotenv()
logger = get_logger(__name__)

# Configure LLM provider
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo")

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
            
            prompt = f"""SYSTEM: {os.getenv("SYSTEM_PROMPT")}
            
            Available Commands:
            {command_context}
            
            USER QUERY: {query}
            
            Respond with:
            1. A natural language answer
            2. Relevant commands in markdown format
            3. Example usage in a code block"""
            
            if LLM_PROVIDER == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=float(os.getenv("TEMPERATURE", 0.7))
                )
                return console.print(response.choices[0].message.content)
            
            elif LLM_PROVIDER == "anthropic":
                from anthropic import Anthropic
                client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                response = client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=1000,
                    temperature=float(os.getenv("TEMPERATURE", 0.7)),
                    system=os.getenv("SYSTEM_PROMPT"),
                    messages=[{"role": "user", "content": query}]
                )
                return console.print(response.content[0].text)
            
            else:
                raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")
            
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            console.print("[red]Error:[/red] Could not generate LLM response")
            console.print("Please check your LLM configuration in .env file")

if __name__ == "__main__":
    client = ChatClient()
    client.start_interactive_session()
