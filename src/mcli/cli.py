import click

from mcli.lib.api.mcli_decorators import chat


@click.group()
def cli():
    """MCLI - Modern Command Line Interface"""
    pass


# Add the chat command group
cli.add_command(chat(name="chat"))


@cli.command()
def version():
    """Show MCLI version"""
    from mcli import __version__

    click.echo(f"MCLI version {__version__}")


if __name__ == "__main__":
    cli()
