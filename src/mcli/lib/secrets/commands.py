"""
CLI commands for secrets management.
"""

from pathlib import Path
from typing import Optional

import click

from mcli.lib.ui.styling import error, info, success, warning

from .manager import SecretsManager
from .repl import run_repl
from .store import SecretsStore


@click.group(name="secrets", help="Secure secrets management with encryption and git sync")
def secrets_group():
    """Secrets management commands."""


@secrets_group.command(name="repl", help="Launch interactive secrets shell")
def secrets_repl():
    """Launch the interactive secrets REPL."""
    run_repl()


@secrets_group.command(name="set", help="Set a secret value")
@click.argument("key")
@click.argument("value")
@click.option("-n", "--namespace", default="default", help="Namespace for the secret")
def secrets_set(key: str, value: str, namespace: str):
    """Set a secret value."""
    manager = SecretsManager()
    try:
        manager.set(key, value, namespace)
        success(f"Secret '{key}' set in namespace '{namespace}'")
    except Exception as e:
        error(f"Failed to set secret: {e}")


@secrets_group.command(name="get", help="Get a secret value")
@click.argument("key")
@click.option("-n", "--namespace", default="default", help="Namespace for the secret")
@click.option("-s", "--show", is_flag=True, help="Show the full value (not masked)")
def secrets_get(key: str, namespace: str, show: bool):
    """Get a secret value."""
    manager = SecretsManager()
    value = manager.get(key, namespace)

    if value is not None:
        if show:
            click.echo(value)
        else:
            # Mask the value
            masked = (
                value[:3] + "*" * (len(value) - 6) + value[-3:]
                if len(value) > 6
                else "*" * len(value)
            )
            info(f"{key} = {masked}")
            info("Use --show to display the full value")
    else:
        warning(f"Secret '{key}' not found in namespace '{namespace}'")


@secrets_group.command(name="list", help="List all secrets")
@click.option("-n", "--namespace", help="Filter by namespace")
def secrets_list(namespace: Optional[str]):
    """List all secrets."""
    manager = SecretsManager()
    secrets = manager.list(namespace)

    if secrets:
        info("Secrets:")
        for secret in secrets:
            click.echo(f"  • {secret}")
    else:
        info("No secrets found")


@secrets_group.command(name="delete", help="Delete a secret")
@click.argument("key")
@click.option("-n", "--namespace", default="default", help="Namespace for the secret")
@click.confirmation_option(prompt="Are you sure you want to delete this secret?")
def secrets_delete(key: str, namespace: str):
    """Delete a secret."""
    manager = SecretsManager()
    if manager.delete(key, namespace):
        success(f"Secret '{key}' deleted from namespace '{namespace}'")
    else:
        warning(f"Secret '{key}' not found in namespace '{namespace}'")


@secrets_group.command(name="export", help="Export secrets as environment variables")
@click.option("-n", "--namespace", help="Namespace to export")
@click.option("-o", "--output", type=click.Path(), help="Output file (defaults to stdout)")
def secrets_export(namespace: Optional[str], output: Optional[str]):
    """Export secrets as environment variables."""
    manager = SecretsManager()
    env_vars = manager.export_env(namespace)

    if env_vars:
        if output:
            with open(output, "w") as f:
                for key, value in env_vars.items():
                    f.write(f"export {key}={value}\n")
            success(f"Exported {len(env_vars)} secrets to {output}")
        else:
            for key, value in env_vars.items():
                click.echo(f"export {key}={value}")
    else:
        info("No secrets to export")


@secrets_group.command(name="import", help="Import secrets from environment file")
@click.argument("env_file", type=click.Path(exists=True))
@click.option("-n", "--namespace", default="default", help="Namespace to import into")
def secrets_import(env_file: str, namespace: str):
    """Import secrets from environment file."""
    manager = SecretsManager()
    count = manager.import_env(Path(env_file), namespace)
    success(f"Imported {count} secrets into namespace '{namespace}'")


@secrets_group.group(name="store", help="Git-based secrets synchronization")
def store_group():
    """Store management commands."""


@store_group.command(name="init", help="Initialize secrets store")
@click.option("-r", "--remote", help="Git remote URL")
def store_init(remote: Optional[str]):
    """Initialize the secrets store."""
    store = SecretsStore()
    store.init(remote)


@store_group.command(name="push", help="Push secrets to store")
@click.option("-m", "--message", help="Commit message")
def store_push(message: Optional[str]):
    """Push secrets to store."""
    manager = SecretsManager()
    store = SecretsStore()
    store.push(manager.secrets_dir, message)


@store_group.command(name="pull", help="Pull secrets from store")
def store_pull():
    """Pull secrets from store."""
    manager = SecretsManager()
    store = SecretsStore()
    store.pull(manager.secrets_dir)


@store_group.command(name="sync", help="Sync secrets with store")
@click.option("-m", "--message", help="Commit message")
def store_sync(message: Optional[str]):
    """Sync secrets with store."""
    manager = SecretsManager()
    store = SecretsStore()
    store.sync(manager.secrets_dir, message)


@store_group.command(name="status", help="Show store status")
def store_status():
    """Show store status."""
    store = SecretsStore()
    status = store.status()

    info("Secrets Store Status:")
    click.echo(f"  Initialized: {status['initialized']}")
    click.echo(f"  Path: {status['store_path']}")

    if status["initialized"]:
        click.echo(f"  Branch: {status['branch']}")
        click.echo(f"  Commit: {status['commit']}")
        click.echo(f"  Clean: {status['clean']}")

        if status["has_remote"]:
            click.echo(f"  Remote: {status['remote_url']}")
        else:
            click.echo("  Remote: Not configured")
