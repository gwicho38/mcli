import click

from mcli.chat.chat import ChatClient


@click.command()
@click.option(
    "--remote",
    is_flag=True,
    help="Use remote online models instead of local lightweight models"
)
@click.option(
    "--model", "-m",
    help="Specific model to use (overrides default behavior)"
)
def chat(remote: bool, model: str):
    """Start an interactive chat session with the MCLI Chat Assistant.
    
    By default, uses lightweight local models for privacy and speed.
    Use --remote to connect to online models like OpenAI or Anthropic.
    """
    client = ChatClient(use_remote=remote, model_override=model)
    client.start_interactive_session()
