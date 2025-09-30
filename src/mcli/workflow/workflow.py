import click

from .daemon.api_daemon import api_daemon
from .daemon.commands import daemon
from .dashboard.dashboard_cmd import dashboard
from .file.file import file
from .git_commit.commands import git_commit_cli
from .politician_trading.commands import politician_trading_cli
from .scheduler.commands import scheduler
from .sync.sync_cmd import sync
from .videos.videos import videos


@click.group(name="workflow")
def workflow():
    """Workflow commands"""
    pass


# Add subcommands
def register_workflow_commands():
    workflow.add_command(file)
    workflow.add_command(videos)
    workflow.add_command(daemon)
    workflow.add_command(api_daemon)
    workflow.add_command(dashboard)
    workflow.add_command(git_commit_cli)
    workflow.add_command(scheduler)
    workflow.add_command(sync)
    workflow.add_command(politician_trading_cli)


register_workflow_commands()


if __name__ == "__main__":
    workflow()
