import click

from mcli.chat.chat import ChatClient


@click.command()
def chat():
    """Start an interactive chat session with the MCLI Chat Assistant."""
    client = ChatClient()
    client.start_interactive_session()
