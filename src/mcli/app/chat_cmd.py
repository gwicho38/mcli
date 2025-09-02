import click

from mcli.chat.chat import ChatClient
from mcli.chat.enhanced_chat import EnhancedChatClient


@click.command()
@click.option(
    "--remote", is_flag=True, help="Use remote online models instead of local lightweight models"
)
@click.option("--model", "-m", help="Specific model to use (overrides default behavior)")
@click.option(
    "--enhanced",
    is_flag=True,
    default=True,
    help="Use enhanced chat with RAG-based command search (default: enabled)",
)
@click.option("--classic", is_flag=True, help="Use classic chat interface without command search")
def chat(remote: bool, model: str, enhanced: bool, classic: bool):
    """Start an interactive chat session with the MCLI Chat Assistant.

    🤖 Enhanced Mode (Default):
    - Self-referential command discovery and suggestions
    - RAG-based semantic search of available MCLI commands
    - Intelligent intent analysis and contextual recommendations
    - Real-time system status awareness

    💬 Classic Mode:
    - Traditional chat interface
    - Basic system integration

    By default, uses lightweight local models for privacy and speed.
    Use --remote to connect to online models like OpenAI or Anthropic.
    """
    # Choose chat client based on options
    if classic:
        client = ChatClient(use_remote=remote, model_override=model)
        client.start_interactive_session()
    else:
        # Use enhanced client by default
        client = EnhancedChatClient(use_remote=remote, model_override=model)
        client.start_interactive_session()
