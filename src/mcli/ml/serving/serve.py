#!/usr/bin/env python3
"""Entry point for model serving CLI."""

import click

from mcli.lib.ui.styling import error, info, success


@click.group(name="mcli-serve", help="Model serving CLI for MCLI ML models")
def cli():
    """Main CLI group for model serving."""
    pass


@cli.command(name="start", help="Start model serving server")
@click.option("--model", required=True, help="Model to serve")
@click.option("--port", default=8000, help="Port to serve on")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
def start_server(model: str, port: int, host: str):
    """Start the model serving server."""
    info(f"Starting model server for: {model}")
    info(f"Serving on {host}:{port}")
    
    # TODO: Implement actual model serving
    error("Model serving functionality not yet implemented")


@cli.command(name="stop", help="Stop model serving server")
def stop_server():
    """Stop the model serving server."""
    info("Stopping model server...")
    # TODO: Implement server stopping
    error("Server stopping not yet implemented")


@cli.command(name="status", help="Check server status")
def server_status():
    """Check the status of the model server."""
    info("Checking server status...")
    # TODO: Implement status check
    error("Status check not yet implemented")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()