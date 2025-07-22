import click
from .webapp.webapp import webapp
from .file.file import file
from .videos.videos import videos
from .daemon.commands import daemon
from .daemon.api_daemon import api_daemon


@click.group(name="workflow")
def workflow():
    """Workflow commands"""
    pass


# Add subcommands
def register_workflow_commands():
    workflow.add_command(webapp)
    workflow.add_command(file)
    workflow.add_command(videos)
    workflow.add_command(daemon)
    workflow.add_command(api_daemon)


register_workflow_commands()


if __name__ == "__main__":
    workflow()
