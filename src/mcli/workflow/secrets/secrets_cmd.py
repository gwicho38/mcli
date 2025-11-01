"""
Secrets workflow command - migrated from lib.secrets

This is now a workflow instead of a lib utility.
All secrets management functionality remains the same.
"""

from pathlib import Path
from typing import Optional

import click

# Import from the original lib.secrets modules (keeping the implementation)
from mcli.lib.secrets.manager import SecretsManager
from mcli.lib.secrets.repl import run_repl
from mcli.lib.secrets.store import SecretsStore
from mcli.lib.ui.styling import error, info, success, warning


@click.command(name="secrets", help="Secure secrets management with encryption and git sync")
@click.option("--repl", is_flag=True, help="Launch interactive secrets shell")
@click.option("--set", "set_secret", nargs=2, type=str, help="Set a secret (KEY VALUE)")
@click.option("--get", "get_secret", type=str, help="Get a secret value")
@click.option("--list", "list_secrets", is_flag=True, help="List all secrets")
@click.option("--delete", "delete_secret", type=str, help="Delete a secret")
@click.option("--namespace", "-n", default="default", help="Namespace for secrets")
@click.option("--show", is_flag=True, help="Show full value (not masked)")
@click.option("--export", is_flag=True, help="Export secrets as environment variables")
@click.option("--import-file", type=click.Path(exists=True), help="Import from env file")
@click.option("--store-init", is_flag=True, help="Initialize secrets store")
@click.option("--store-push", is_flag=True, help="Push secrets to store")
@click.option("--store-pull", is_flag=True, help="Pull secrets from store")
@click.option("--store-sync", is_flag=True, help="Sync secrets with store")
@click.option("--store-status", is_flag=True, help="Show store status")
@click.option("--remote", type=str, help="Git remote URL (for store init)")
@click.option("--message", "-m", type=str, help="Commit message (for store operations)")
@click.option("--output", "-o", type=click.Path(), help="Output file (for export)")
def secrets(
    repl: bool,
    set_secret: Optional[tuple],
    get_secret: Optional[str],
    list_secrets: bool,
    delete_secret: Optional[str],
    namespace: str,
    show: bool,
    export: bool,
    import_file: Optional[str],
    store_init: bool,
    store_push: bool,
    store_pull: bool,
    store_sync: bool,
    store_status: bool,
    remote: Optional[str],
    message: Optional[str],
    output: Optional[str],
):
    """
    Secrets management workflow - all-in-one command for managing secrets.

    Examples:
        mcli workflows secrets --repl                    # Interactive shell
        mcli workflows secrets --set API_KEY abc123      # Set a secret
        mcli workflows secrets --get API_KEY             # Get a secret
        mcli workflows secrets --list                    # List all secrets
        mcli workflows secrets --export                  # Export as env vars
        mcli workflows secrets --store-init              # Initialize git store
    """
    manager = SecretsManager()

    # Handle REPL
    if repl:
        run_repl()
        return

    # Handle set
    if set_secret:
        key, value = set_secret
        try:
            manager.set(key, value, namespace)
            success(f"Secret '{key}' set in namespace '{namespace}'")
        except Exception as e:
            error(f"Failed to set secret: {e}")
        return

    # Handle get
    if get_secret:
        value = manager.get(get_secret, namespace)
        if value is not None:
            if show:
                click.echo(value)
            else:
                masked = (
                    value[:3] + "*" * (len(value) - 6) + value[-3:]
                    if len(value) > 6
                    else "*" * len(value)
                )
                info(f"{get_secret} = {masked}")
                info("Use --show to display the full value")
        else:
            warning(f"Secret '{get_secret}' not found in namespace '{namespace}'")
        return

    # Handle list
    if list_secrets:
        secrets_list = manager.list(namespace if namespace != "default" else None)
        if secrets_list:
            info("Secrets:")
            for secret in secrets_list:
                click.echo(f"  • {secret}")
        else:
            info("No secrets found")
        return

    # Handle delete
    if delete_secret:
        if click.confirm(f"Are you sure you want to delete '{delete_secret}'?"):
            if manager.delete(delete_secret, namespace):
                success(f"Secret '{delete_secret}' deleted from namespace '{namespace}'")
            else:
                warning(f"Secret '{delete_secret}' not found in namespace '{namespace}'")
        return

    # Handle export
    if export:
        env_vars = manager.export_env(namespace if namespace != "default" else None)
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
        return

    # Handle import
    if import_file:
        count = manager.import_env(Path(import_file), namespace)
        success(f"Imported {count} secrets into namespace '{namespace}'")
        return

    # Store operations
    store = SecretsStore()

    if store_init:
        store.init(remote)
        success("Secrets store initialized")
        return

    if store_push:
        store.push(manager.secrets_dir, message)
        success("Secrets pushed to store")
        return

    if store_pull:
        store.pull(manager.secrets_dir)
        success("Secrets pulled from store")
        return

    if store_sync:
        store.sync(manager.secrets_dir, message)
        success("Secrets synced with store")
        return

    if store_status:
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
        return

    # If no action specified, show help
    ctx = click.get_current_context()
    click.echo(ctx.get_help())


if __name__ == "__main__":
    secrets()
