import click
from .webapp.webapp import webapp
from .file.file import file
from .videos.videos import videos


@click.group(name="workflow")
def workflow():
    """Workflow commands"""
    pass


# Add subcommands
def register_workflow_commands():
    workflow.add_command(webapp)
    workflow.add_command(file)
    workflow.add_command(videos)


register_workflow_commands()


if __name__ == "__main__":
    workflow()
