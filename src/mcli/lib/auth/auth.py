from typing import Optional

import click

from .token_manager import TokenManager


def configure():
    """Configure authentication token"""
    token_manager = TokenManager()

    # Prompt for token, hiding input
    token = click.prompt(
        "Please enter your authentication token",
        hide_input=True,
        confirmation_prompt=True,
    )

    try:
        token_manager.save_token(token)
        click.echo("Token saved successfully!")
    except Exception as e:
        click.echo(f"Error saving token: {str(e)}", err=True)
        return


def show_token():
    """Display the current authentication token"""
    token_manager = TokenManager()
    token = token_manager.get_token()

    if token:
        click.echo(f"Current token: {token}")
    else:
        click.echo("No token configured. Run `configure` to set up a token.")


def clear_token():
    """Clear the stored authentication token"""
    token_manager = TokenManager()

    if click.confirm("Are you sure you want to clear the stored token?"):
        try:
            if token_manager.config_file.exists():
                token_manager.config_file.unlink()
            click.echo("Token cleared successfully!")
        except Exception as e:
            click.echo(f"Error clearing token: {str(e)}", err=True)


def get_current_token() -> Optional[str]:
    """
    Utility function to get the current token.
    Can be used by other parts of your application.
    """
    token_manager = TokenManager()
    return token_manager.get_token()


def get_current_url() -> Optional[str]:
    """
    Utility function to get the current token.
    Can be used by other parts of your application.
    """
    token_manager = TokenManager()
    return token_manager.get_url()


def get_mcli_basic_auth() -> Optional[str]:
    """
    Utility function to get the current token.
    Can be used by other parts of your application.
    """
    token_manager = TokenManager()
    return token_manager.get_mcli_basic_auth()


@click.group(name="auth")
def auth():
    """Authentication commands"""
    pass


if __name__ == "__main__":
    auth()
