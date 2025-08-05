import click
from mcli.chat.chat import ChatClient

@click.group()
def chat():
    """Interact with the MCLI Chat Assistant."""
    pass

@chat.command()
def interactive():
    """Start an interactive chat session with the MCLI Chat Assistant."""
    client = ChatClient()
    client.start_interactive_session()
