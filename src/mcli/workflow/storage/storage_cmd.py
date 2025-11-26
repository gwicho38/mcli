"""
Storage workflow command for MCLI.

Provides CLI access to the storage abstraction layer with support for:
- Storacha/IPFS storage
- Authentication and setup
- Upload/download operations
- Cache management
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import click

from mcli.lib.ui.styling import error, info, success, warning


def run_async(coro):
    """Run async function synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


@click.group(name="storage", help="Decentralized storage with Storacha/IPFS")
def storage():
    """
    Storage workflow - manage decentralized storage with Storacha/IPFS.

    Examples:
        mcli workflows storage status          # Show storage status
        mcli workflows storage login <email>   # Login to Storacha
        mcli workflows storage setup           # Complete setup flow
        mcli workflows storage upload <file>   # Upload a file
        mcli workflows storage download <cid>  # Download by CID
        mcli workflows storage list            # List cached files
    """
    pass


@storage.command(name="status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status_cmd(as_json: bool):
    """Show current storage status."""
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        run_async(backend.connect())
        status = backend.get_status()

        if as_json:
            click.echo(json.dumps(status, indent=2, default=str))
        else:
            info("Storage Status")
            click.echo()

            # Backend status
            click.echo(f"  Enabled:    {status.get('enabled', False)}")
            click.echo(f"  Connected:  {status.get('connected', False)}")
            click.echo(f"  Has Tokens: {status.get('has_tokens', False)}")
            click.echo()

            # CLI status
            cli_status = status.get("cli", {})
            click.echo("  Storacha CLI:")
            click.echo(f"    Installed:     {cli_status.get('cli_installed', False)}")
            click.echo(f"    Authenticated: {cli_status.get('authenticated', False)}")
            agent_did = cli_status.get("agent_did", "None")
            click.echo(
                f"    Agent DID:     {agent_did[:40]}..."
                if agent_did and len(agent_did) > 40
                else f"    Agent DID:     {agent_did}"
            )
            space_did = cli_status.get("space_did", "None")
            click.echo(
                f"    Space DID:     {space_did[:40]}..."
                if space_did and len(space_did) > 40
                else f"    Space DID:     {space_did}"
            )
            click.echo()

            # Cache stats
            cache_stats = status.get("cache", {})
            click.echo("  Local Cache:")
            click.echo(f"    Files:  {cache_stats.get('total_files', 0)}")
            click.echo(f"    Size:   {cache_stats.get('total_size_mb', 0)} MB")
            click.echo(f"    Path:   {cache_stats.get('cache_dir', 'N/A')}")

    except Exception as e:
        error(f"Failed to get status: {e}")
        raise click.Abort()


@storage.command(name="login")
@click.argument("email")
def login_cmd(email: str):
    """
    Login to Storacha with email verification.

    This will send a verification email. Click the link in your email
    to complete authentication.
    """
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        result = run_async(backend.login(email))

        if result:
            success("Login successful!")
        else:
            error("Login failed. Check the error messages above.")

    except Exception as e:
        error(f"Login error: {e}")
        raise click.Abort()


@storage.command(name="setup")
@click.option("--email", "-e", help="Email for authentication (if not already logged in)")
def setup_cmd(email: Optional[str]):
    """
    Complete storage setup: login, create space, generate tokens.

    If already authenticated, this will ensure a space exists and
    generate HTTP bridge tokens for programmatic access.
    """
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        result = run_async(backend.setup(email=email))

        if result:
            success("Setup complete! Storage is ready to use.")
            info("  Run 'mcli workflows storage status' to verify")
        else:
            error("Setup failed. Check the error messages above.")

    except Exception as e:
        error(f"Setup error: {e}")
        raise click.Abort()


@storage.command(name="upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--key", "-k", help="Storage key/identifier (default: filename)")
@click.option("--metadata", "-m", multiple=True, help="Metadata as KEY=VALUE pairs")
def upload_cmd(file_path: str, key: Optional[str], metadata: tuple):
    """
    Upload a file to storage.

    The file will be encrypted and uploaded to Storacha/IPFS.
    Returns the CID (Content Identifier) that can be used to retrieve it.
    """
    from mcli.storage import get_storage_backend

    path = Path(file_path)
    if not path.exists():
        error(f"File not found: {file_path}")
        raise click.Abort()

    # Parse metadata
    meta = {}
    for item in metadata:
        if "=" in item:
            k, v = item.split("=", 1)
            meta[k] = v

    # Use filename as key if not specified
    if not key:
        key = path.name

    try:
        info(f"Uploading {path.name}...")
        backend = get_storage_backend()
        run_async(backend.connect())

        # Read file
        data = path.read_bytes()

        # Store
        cid = run_async(backend.store(key, data, meta))

        success("Uploaded successfully!")
        click.echo(f"  CID: {cid}")
        click.echo(f"  Key: {key}")
        click.echo(f"  Gateway: https://{cid}.ipfs.storacha.link")

    except Exception as e:
        error(f"Upload failed: {e}")
        raise click.Abort()


@storage.command(name="download")
@click.argument("cid")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def download_cmd(cid: str, output: Optional[str]):
    """
    Download a file by CID.

    Retrieves and decrypts data from local cache or Storacha network.
    """
    from mcli.storage import get_storage_backend

    try:
        info(f"Downloading {cid}...")
        backend = get_storage_backend()
        run_async(backend.connect())

        data = run_async(backend.retrieve(cid))

        if data is None:
            error(f"Data not found for CID: {cid}")
            raise click.Abort()

        if output:
            output_path = Path(output)
            output_path.write_bytes(data)
            success(f"Downloaded to {output_path}")
            click.echo(f"  Size: {len(data)} bytes")
        else:
            # Output to stdout
            click.echo(data.decode("utf-8", errors="replace"))

    except Exception as e:
        error(f"Download failed: {e}")
        raise click.Abort()


@storage.command(name="list")
@click.option("--limit", "-n", default=20, help="Maximum number of results")
@click.option("--prefix", "-p", help="Filter by CID prefix")
@click.option("--remote", "-r", is_flag=True, help="List remote uploads (not just cache)")
def list_cmd(limit: int, prefix: Optional[str], remote: bool):
    """List stored files."""
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        run_async(backend.connect())

        if remote:
            info("Remote uploads:")
            cids = run_async(backend.list_recent_uploads(limit=limit))
        else:
            info("Local cache:")
            cids = run_async(backend.list_all(prefix=prefix, limit=limit))

        if not cids:
            warning("No files found")
            return

        for cid in cids:
            metadata = run_async(backend.get_metadata(cid))
            if metadata:
                size = metadata.get("size", "?")
                cached_at = metadata.get("cached_at", "")[:10]
                click.echo(f"  {cid[:20]}...  {size:>10} bytes  {cached_at}")
            else:
                click.echo(f"  {cid}")

        click.echo()
        info(f"Total: {len(cids)} files")

    except Exception as e:
        error(f"List failed: {e}")
        raise click.Abort()


@storage.command(name="delete")
@click.argument("cid")
@click.confirmation_option(prompt="Are you sure you want to delete this from local cache?")
def delete_cmd(cid: str):
    """
    Delete a file from local cache.

    Note: This only removes from local cache. IPFS data is immutable
    and cannot be deleted from the network.
    """
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        run_async(backend.connect())

        result = run_async(backend.delete(cid))

        if result:
            success(f"Deleted from local cache: {cid}")
        else:
            warning(f"File not found in cache: {cid}")

    except Exception as e:
        error(f"Delete failed: {e}")
        raise click.Abort()


@storage.command(name="enable")
def enable_cmd():
    """Enable Storacha network sync."""
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        backend.enable()
        success("Storacha network sync enabled")

    except Exception as e:
        error(f"Failed to enable: {e}")
        raise click.Abort()


@storage.command(name="disable")
def disable_cmd():
    """Disable Storacha network sync (use local cache only)."""
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        backend.disable()
        success("Storacha network sync disabled")
        info("Using local cache only")

    except Exception as e:
        error(f"Failed to disable: {e}")
        raise click.Abort()


@storage.command(name="cache")
@click.option("--stats", is_flag=True, help="Show cache statistics")
@click.option("--cleanup", is_flag=True, help="Clean up old cache files")
@click.option("--max-age", default=30, help="Max age in days for cleanup (default: 30)")
def cache_cmd(stats: bool, cleanup: bool, max_age: int):
    """Manage local cache."""
    from mcli.storage import get_storage_backend

    try:
        backend = get_storage_backend()

        if stats:
            cache_stats = backend.cache.get_stats()
            info("Cache Statistics")
            click.echo()
            click.echo(f"  Total Files: {cache_stats.get('total_files', 0)}")
            click.echo(f"  Total Size:  {cache_stats.get('total_size_mb', 0)} MB")
            click.echo(f"  Cache Path:  {cache_stats.get('cache_dir', 'N/A')}")

            types = cache_stats.get("types", {})
            if types:
                click.echo()
                click.echo("  By Type:")
                for t, count in types.items():
                    click.echo(f"    {t}: {count}")

        elif cleanup:
            deleted = run_async(backend.cache.cleanup(max_age_days=max_age))
            success(f"Cleaned up {deleted} old cache files")

        else:
            # Default: show stats
            cache_stats = backend.cache.get_stats()
            files = cache_stats.get("total_files", 0)
            size_mb = cache_stats.get("total_size_mb", 0)
            click.echo(f"Cache: {files} files, {size_mb} MB")

    except Exception as e:
        error(f"Cache operation failed: {e}")
        raise click.Abort()


@storage.group(name="space")
def space_group():
    """Manage Storacha spaces."""
    pass


@space_group.command(name="list")
def space_list_cmd():
    """List available spaces."""
    from mcli.storage.storacha_cli import StorachaCLI

    try:
        cli = StorachaCLI()
        spaces = cli.list_spaces()

        if not spaces:
            warning("No spaces found")
            info("Create one with: mcli workflows storage space create")
            return

        current = cli.get_current_space()

        info("Available Spaces:")
        for space in spaces:
            marker = " *" if space == current else "  "
            click.echo(f"{marker} {space}")

    except Exception as e:
        error(f"Failed to list spaces: {e}")
        raise click.Abort()


@space_group.command(name="create")
@click.option("--name", "-n", help="Space name")
def space_create_cmd(name: Optional[str]):
    """Create a new space."""
    from mcli.storage.storacha_cli import StorachaCLI

    try:
        cli = StorachaCLI()
        space_did = cli.create_space(name)

        if space_did:
            success(f"Created space: {space_did}")
        else:
            error("Failed to create space")

    except Exception as e:
        error(f"Failed to create space: {e}")
        raise click.Abort()


@space_group.command(name="use")
@click.argument("space_did")
def space_use_cmd(space_did: str):
    """Select a space to use."""
    from mcli.storage.storacha_cli import StorachaCLI

    try:
        cli = StorachaCLI()
        if cli.select_space(space_did):
            success(f"Selected space: {space_did}")
        else:
            error("Failed to select space")

    except Exception as e:
        error(f"Failed to select space: {e}")
        raise click.Abort()


@storage.command(name="tokens")
@click.option("--refresh", "-r", is_flag=True, help="Force refresh tokens")
@click.option("--expiration", "-e", default=24, help="Token expiration in hours (default: 24)")
def tokens_cmd(refresh: bool, expiration: int):
    """Manage HTTP bridge tokens."""
    from mcli.storage.storacha_cli import StorachaCLI

    try:
        cli = StorachaCLI()

        if refresh:
            tokens = cli.generate_bridge_tokens(expiration_hours=expiration)
        else:
            tokens = cli.get_bridge_tokens(auto_refresh=True)

        if tokens:
            success("Bridge Tokens:")
            click.echo()
            click.echo(f"  Agent DID: {tokens.agent_did}")
            click.echo(f"  Space DID: {tokens.space_did}")
            if tokens.expires_at:
                click.echo(f"  Expires:   {tokens.expires_at.isoformat()}")
            click.echo(f"  Capabilities: {', '.join(tokens.capabilities)}")
            click.echo()
            info("Tokens are stored in ~/.mcli/storacha-config.json")
        else:
            error("No tokens available")
            info("Run 'mcli workflows storage setup' to configure")

    except Exception as e:
        error(f"Failed to manage tokens: {e}")
        raise click.Abort()
