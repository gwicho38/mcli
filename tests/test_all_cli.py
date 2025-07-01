import pytest
from click.testing import CliRunner
import importlib
import sys
from pathlib import Path

# Import all CLI groups
from src.mcli.workflow.webapp.webapp import webapp
from src.mcli.workflow.file.file import file
from src.mcli.workflow.registry.registry import registry
from src.mcli.workflow.repo.repo import repo
from src.mcli.workflow.gcloud.gcloud import gcloud
from src.mcli.workflow.videos.videos import videos
from src.mcli.workflow.wakatime.wakatime import wakatime
from src.mcli.public.oi.oi import oi
from src.mcli.self.self_cmd import self_app
from src.mcli.lib.lib import lib
from src.mcli.lib.auth.auth import auth
from src.mcli.workflow.workflow import workflow
from src.mcli.app.main import create_app


def test_all_cli_groups_exist():
    """Test that all CLI groups can be imported and have help"""
    groups = [
        (webapp, "webapp"),
        (file, "file"),
        (registry, "registry"),
        (repo, "repo"),
        (gcloud, "gcloud"),
        (videos, "videos"),
        (wakatime, "wakatime"),
        (oi, "oi"),
        (self_app, "self"),
        (lib, "lib"),
        (auth, "auth"),
        (workflow, "workflow"),
    ]
    
    runner = CliRunner()
    
    for group, name in groups:
        result = runner.invoke(group, ['--help'])
        assert result.exit_code == 0, f"Group {name} help failed"
        assert result.output, f"Group {name} has no help output"


def test_main_app_commands():
    """Test main app commands"""
    runner = CliRunner()
    app = create_app()
    
    # Test main help
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'mcli' in result.output
    
    # Test hello command
    result = runner.invoke(app, ['hello'])
    assert result.exit_code == 0
    assert 'Hello from mcli!' in result.output
    
    # Test version command
    result = runner.invoke(app, ['version'])
    assert result.exit_code == 0
    assert 'mcli version' in result.output


def test_workflow_subcommands():
    """Test workflow subcommands"""
    runner = CliRunner()
    
    # Test webapp subcommand
    result = runner.invoke(workflow, ['webapp', '--help'])
    assert result.exit_code == 0
    assert 'Web application generation and installation commands' in result.output
    
    # Test file subcommand
    result = runner.invoke(workflow, ['file', '--help'])
    assert result.exit_code == 0 or 'Usage:' in result.output
    
    # Test videos subcommand
    result = runner.invoke(workflow, ['videos', '--help'])
    assert result.exit_code == 0 or 'Usage:' in result.output


def test_webapp_commands():
    """Test webapp commands"""
    runner = CliRunner()
    
    commands = ['generate', 'install', 'run', 'list', 'delete']
    
    for cmd in commands:
        result = runner.invoke(webapp, [cmd, '--help'])
        assert result.exit_code == 0, f"webapp {cmd} help failed"
        assert result.output, f"webapp {cmd} has no help output"


def test_file_commands():
    """Test file commands"""
    runner = CliRunner()
    
    # Test oxps-to-pdf
    result = runner.invoke(file, ['oxps-to-pdf', '--help'])
    assert result.exit_code == 0
    assert 'Converts an OXPS file' in result.output
    
    # Test search
    result = runner.invoke(file, ['search', '--help'])
    assert result.exit_code == 0
    assert 'Search for a string with ripgrep' in result.output


def test_registry_commands():
    """Test registry commands"""
    runner = CliRunner()
    
    commands = ['catalog', 'tags', 'search-tags', 'search', 'image-info', 'count', 'pull', 'fuzzy-search']
    
    for cmd in commands:
        result = runner.invoke(registry, [cmd, '--help'])
        assert result.exit_code == 0, f"registry {cmd} help failed"
        assert result.output, f"registry {cmd} has no help output"


def test_repo_commands():
    """Test repo commands"""
    runner = CliRunner()
    
    commands = ['analyze', 'wt', 'commit', 'revert', 'migration-loe']
    
    for cmd in commands:
        result = runner.invoke(repo, [cmd, '--help'])
        assert result.exit_code == 0, f"repo {cmd} help failed"
        assert result.output, f"repo {cmd} has no help output"


def test_gcloud_commands():
    """Test gcloud commands"""
    runner = CliRunner()
    
    commands = ['start', 'stop', 'describe', 'tunnel', 'login']
    
    for cmd in commands:
        result = runner.invoke(gcloud, [cmd, '--help'])
        assert result.exit_code == 0, f"gcloud {cmd} help failed"
        assert result.output, f"gcloud {cmd} has no help output"


def test_videos_commands():
    """Test videos commands"""
    runner = CliRunner()
    
    commands = ['remove-overlay', 'extract-frames', 'frames-to-video']
    
    for cmd in commands:
        result = runner.invoke(videos, [cmd, '--help'])
        assert result.exit_code == 0, f"videos {cmd} help failed"
        assert result.output, f"videos {cmd} has no help output"


def test_self_commands():
    """Test self commands"""
    runner = CliRunner()
    
    # Test main commands
    commands = ['search', 'add-command']
    for cmd in commands:
        result = runner.invoke(self_app, [cmd, '--help'])
        assert result.exit_code == 0, f"self {cmd} help failed"
        assert result.output, f"self {cmd} has no help output"
    
    # Test plugin subcommands
    plugin_commands = ['add', 'remove', 'update']
    for cmd in plugin_commands:
        result = runner.invoke(self_app, ['plugin', cmd, '--help'])
        assert result.exit_code == 0, f"self plugin {cmd} help failed"
        assert result.output, f"self plugin {cmd} has no help output" 