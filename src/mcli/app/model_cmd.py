"""Model management commands for MCLI."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

from mcli.lib.logger.logger import get_logger
from mcli.workflow.model_service.lightweight_model_server import (
    LIGHTWEIGHT_MODELS,
    LightweightModelServer,
)

logger = get_logger(__name__)


@click.group()
def model():
    """Model management commands for offline and online model usage."""
    pass


@model.command()
@click.option("--list-available", "-l", is_flag=True, help="List all available lightweight models")
@click.option("--list-downloaded", "-d", is_flag=True, help="List downloaded models")
@click.option(
    "--system-info", "-s", is_flag=True, help="Show system information and recommendations"
)
def list(list_available: bool, list_downloaded: bool, system_info: bool):
    """List available and downloaded models."""
    server = LightweightModelServer()

    if system_info:
        info = server.get_system_info()
        click.echo("🖥️  System Information:")
        click.echo(f"   CPU Cores: {info['cpu_count']}")
        click.echo(f"   RAM: {info['memory_gb']:.1f} GB")
        click.echo(f"   Free Disk: {info['disk_free_gb']:.1f} GB")
        recommended = server.recommend_model()
        click.echo(f"   Recommended Model: {recommended}")
        click.echo("")

    if list_available or (not list_downloaded and not system_info):
        click.echo("📋 Available Lightweight Models:")
        click.echo("=" * 50)

        downloaded_models = server.downloader.get_downloaded_models()

        for key, info in LIGHTWEIGHT_MODELS.items():
            status = "✅ Downloaded" if key in downloaded_models else "⏳ Available"
            click.echo(f"{status} - {info['name']} ({info['parameters']})")
            click.echo(
                f"    Size: {info['size_mb']} MB | Efficiency: {info['efficiency_score']}/10"
            )
            click.echo(f"    Type: {info['model_type']} | Tags: {', '.join(info['tags'])}")
            click.echo()

    if list_downloaded:
        downloaded_models = server.downloader.get_downloaded_models()
        if downloaded_models:
            click.echo("📦 Downloaded Models:")
            click.echo("=" * 30)
            for model in downloaded_models:
                info = LIGHTWEIGHT_MODELS.get(model, {})
                name = info.get("name", model)
                params = info.get("parameters", "Unknown")
                click.echo(f"✅ {name} ({params})")
        else:
            click.echo(
                "No models downloaded yet. Use 'mcli model download <model>' to download a model."
            )


@model.command()
@click.argument("model_name")
def download(model_name: str):
    """Download a specific lightweight model."""
    if model_name not in LIGHTWEIGHT_MODELS:
        click.echo(f"❌ Model '{model_name}' not found.")
        click.echo("Available models:")
        for key in LIGHTWEIGHT_MODELS.keys():
            click.echo(f"  • {key}")
        sys.exit(1)

    server = LightweightModelServer()

    click.echo(f"Downloading model: {model_name}")
    success = server.download_and_load_model(model_name)

    if success:
        click.echo(f"✅ Successfully downloaded {model_name}")
    else:
        click.echo(f"❌ Failed to download {model_name}")
        sys.exit(1)


@model.command()
@click.option("--model", "-m", help="Specific model to use")
@click.option("--port", "-p", default=8080, help="Port to run server on")
@click.option(
    "--auto-download",
    is_flag=True,
    default=True,
    help="Automatically download model if not available",
)
def start(model: Optional[str], port: int, auto_download: bool):
    """Start the lightweight model server."""
    server = LightweightModelServer(port=port)

    # Determine which model to use
    if not model:
        model = server.recommend_model()
        click.echo(f"🎯 Using recommended model: {model}")
    elif model not in LIGHTWEIGHT_MODELS:
        click.echo(f"❌ Model '{model}' not found.")
        click.echo("Available models:")
        for key in LIGHTWEIGHT_MODELS.keys():
            click.echo(f"  • {key}")
        sys.exit(1)

    # Check if model is downloaded, download if needed
    downloaded_models = server.downloader.get_downloaded_models()
    if model not in downloaded_models:
        if auto_download:
            click.echo(f"📥 Model {model} not found locally, downloading...")
            success = server.download_and_load_model(model)
            if not success:
                click.echo(f"❌ Failed to download {model}")
                sys.exit(1)
        else:
            click.echo(
                f"❌ Model {model} not found locally. Use --auto-download to download automatically."
            )
            sys.exit(1)
    else:
        # Load the already downloaded model
        success = server.download_and_load_model(model)
        if not success:
            click.echo(f"❌ Failed to load {model}")
            sys.exit(1)

    # Start server
    click.echo(f"🚀 Starting lightweight server on port {port}...")
    server.start_server()

    click.echo(f"\n📝 Server running at:")
    click.echo(f"   - API: http://localhost:{port}")
    click.echo(f"   - Health: http://localhost:{port}/health")
    click.echo(f"   - Models: http://localhost:{port}/models")
    click.echo(f"\n   Press Ctrl+C to stop the server")

    try:
        # Keep server running
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\n🛑 Server stopped")


@model.command()
def recommend():
    """Get model recommendation based on system capabilities."""
    server = LightweightModelServer()
    recommended = server.recommend_model()

    info = server.get_system_info()
    click.echo("🔍 System Analysis:")
    click.echo(f"   CPU Cores: {info['cpu_count']}")
    click.echo(f"   RAM: {info['memory_gb']:.1f} GB")
    click.echo(f"   Free Disk: {info['disk_free_gb']:.1f} GB")
    click.echo("")

    model_info = LIGHTWEIGHT_MODELS[recommended]
    click.echo(f"🎯 Recommended Model: {recommended}")
    click.echo(f"   Name: {model_info['name']}")
    click.echo(f"   Description: {model_info['description']}")
    click.echo(f"   Parameters: {model_info['parameters']}")
    click.echo(f"   Size: {model_info['size_mb']} MB")
    click.echo(f"   Efficiency Score: {model_info['efficiency_score']}/10")

    downloaded_models = server.downloader.get_downloaded_models()
    if recommended not in downloaded_models:
        click.echo(f"\n💡 To download: mcli model download {recommended}")
    else:
        click.echo(f"\n✅ Model already downloaded")


@model.command()
@click.option("--port", "-p", default=8080, help="Port where server is running")
def status(port: int):
    """Check status of the lightweight model server."""
    import requests

    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            click.echo(f"✅ Server is running on port {port}")

            # Get loaded models
            models_response = requests.get(f"http://localhost:{port}/models", timeout=5)
            if models_response.status_code == 200:
                models_data = models_response.json()
                models = models_data.get("models", [])
                if models:
                    click.echo(f"🤖 Loaded models ({len(models)}):")
                    for model in models:
                        click.echo(f"   - {model['name']} ({model['parameters']})")
                else:
                    click.echo("⚠️  No models currently loaded")
        else:
            click.echo(f"❌ Server responded with status {response.status_code}")

    except requests.exceptions.ConnectionError:
        click.echo(f"❌ No server running on port {port}")
    except requests.exceptions.Timeout:
        click.echo(f"⏰ Server on port {port} is not responding")
    except Exception as e:
        click.echo(f"❌ Error checking server: {e}")


if __name__ == "__main__":
    model()
