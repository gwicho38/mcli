"""Model management commands for MCLI."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
import psutil

from mcli.lib.logger.logger import get_logger
from mcli.workflow.model_service.lightweight_model_server import (
    LIGHTWEIGHT_MODELS,
    LightweightModelServer,
)

logger = get_logger(__name__)


def _start_openai_server(server, host: str, port: int, api_key: Optional[str], model: str):
    """Start FastAPI server with OpenAI compatibility"""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn

        from mcli.workflow.model_service.openai_adapter import create_openai_adapter

        # Create FastAPI app
        app = FastAPI(
            title="MCLI Model Service (OpenAI Compatible)",
            description="OpenAI-compatible API for MCLI lightweight models",
            version="1.0.0",
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Create OpenAI adapter
        require_auth = api_key is not None
        adapter = create_openai_adapter(server, require_auth=require_auth)

        # Add API key if provided
        if api_key:
            adapter.api_key_manager.add_key(api_key, name="default")
            click.echo(f"🔐 API key authentication enabled")

        # Include OpenAI routes
        app.include_router(adapter.router)

        # Add health check endpoint
        @app.get("/health")
        async def health():
            return {"status": "healthy", "model": model}

        # Display server info
        click.echo(f"\n📝 Server running at:")
        click.echo(f"   - Base URL: http://{host}:{port}")
        click.echo(f"   - OpenAI API: http://{host}:{port}/v1")
        click.echo(f"   - Models: http://{host}:{port}/v1/models")
        click.echo(f"   - Chat: http://{host}:{port}/v1/chat/completions")
        click.echo(f"   - Health: http://{host}:{port}/health")

        if require_auth:
            click.echo(f"\n🔐 Authentication: Required")
            click.echo(f"   Use: Authorization: Bearer {api_key}")
        else:
            click.echo(f"\n⚠️  Authentication: Disabled (not recommended for public access)")

        if host == "0.0.0.0":
            click.echo(f"\n⚠️  Server is publicly accessible on all interfaces!")

        click.echo(f"\n📚 For aider, use:")
        if require_auth:
            click.echo(f"   export OPENAI_API_KEY={api_key}")
        click.echo(f"   export OPENAI_API_BASE=http://{host}:{port}/v1")
        click.echo(f"   aider --model {model}")

        click.echo(f"\n   Press Ctrl+C to stop the server")

        # Start server
        uvicorn.run(app, host=host, port=port, log_level="info")

    except ImportError as e:
        click.echo(f"❌ Missing dependencies for OpenAI-compatible server: {e}")
        click.echo(f"   Install with: pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Failed to start OpenAI-compatible server: {e}")
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


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
@click.option(
    "--port", "-p", default=None, help="Port to run server on (default: from config or 51234)"
)
@click.option(
    "--host", "-h", default="localhost", help="Host to bind to (use 0.0.0.0 for public access)"
)
@click.option(
    "--auto-download",
    is_flag=True,
    default=True,
    help="Automatically download model if not available",
)
@click.option(
    "--openai-compatible",
    is_flag=True,
    default=False,
    help="Enable OpenAI-compatible API endpoints",
)
@click.option(
    "--api-key",
    default=None,
    help="API key for authentication (if not set, auth is disabled)",
)
def start(
    model: Optional[str],
    port: Optional[int],
    host: str,
    auto_download: bool,
    openai_compatible: bool,
    api_key: Optional[str],
):
    """Start the lightweight model server."""
    # Load port from config if not specified
    if port is None:
        try:
            from mcli.lib.config.config import load_config

            config = load_config()
            port = config.get("model", {}).get("server_port", 51234)
        except Exception:
            port = 51234  # Default ephemeral port

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

    # Start server with OpenAI compatibility if requested
    if openai_compatible:
        click.echo(f"🚀 Starting OpenAI-compatible server on {host}:{port}...")
        _start_openai_server(server, host, port, api_key, model)
    else:
        click.echo(f"🚀 Starting lightweight server on {host}:{port}...")
        server.start_server()

        click.echo(f"\n📝 Server running at:")
        click.echo(f"   - API: http://{host}:{port}")
        click.echo(f"   - Health: http://{host}:{port}/health")
        click.echo(f"   - Models: http://{host}:{port}/models")

        if host == "0.0.0.0":
            click.echo(f"\n⚠️  Server is publicly accessible!")
            click.echo(f"   Consider using --openai-compatible with --api-key for security")

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
@click.option(
    "--port",
    "-p",
    default=None,
    help="Port where server is running (default: from config or 51234)",
)
def status(port: Optional[int]):
    """Check status of the lightweight model server."""
    # Load port from config if not specified
    if port is None:
        try:
            from mcli.lib.config.config import load_config

            config = load_config()
            port = config.get("model", {}).get("server_port", 51234)
        except Exception:
            port = 51234  # Default ephemeral port

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


@model.command()
@click.option(
    "--port",
    "-p",
    default=None,
    help="Port where server is running (default: from config or 51234)",
)
def stop(port: Optional[int]):
    """Stop the lightweight model server."""
    # Load port from config if not specified
    if port is None:
        try:
            from mcli.lib.config.config import load_config

            config = load_config()
            port = config.get("model", {}).get("server_port", 51234)
        except Exception:
            port = 51234  # Default ephemeral port

    import psutil
    import requests

    try:
        # First check if server is running
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code != 200:
                click.echo(f"❌ No server running on port {port}")
                return
        except requests.exceptions.ConnectionError:
            click.echo(f"❌ No server running on port {port}")
            return

        # Find and kill the process using the port
        for proc in psutil.process_iter(["pid", "name", "connections"]):
            try:
                connections = proc.info.get("connections")
                if connections:
                    for conn in connections:
                        if hasattr(conn, "laddr") and conn.laddr.port == port:
                            click.echo(f"🛑 Stopping server (PID: {proc.pid})...")
                            proc.terminate()
                            proc.wait(timeout=5)
                            click.echo("✅ Server stopped successfully")
                            return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue

        click.echo("⚠️  Could not find server process")

    except Exception as e:
        click.echo(f"❌ Error stopping server: {e}")


@model.command()
@click.argument("model_name")
def pull(model_name: str):
    """Pull (download) a specific lightweight model."""
    if model_name not in LIGHTWEIGHT_MODELS:
        click.echo(f"❌ Model '{model_name}' not found.")
        click.echo("Available models:")
        for key in LIGHTWEIGHT_MODELS.keys():
            click.echo(f"  • {key}")
        sys.exit(1)

    server = LightweightModelServer()

    click.echo(f"Pulling model: {model_name}")
    success = server.download_and_load_model(model_name)

    if success:
        click.echo(f"✅ Successfully pulled {model_name}")
    else:
        click.echo(f"❌ Failed to pull {model_name}")
        sys.exit(1)


@model.command()
@click.argument("model_name")
@click.option("--force", "-f", is_flag=True, help="Force deletion without confirmation")
def delete(model_name: str, force: bool):
    """Delete a downloaded lightweight model."""
    server = LightweightModelServer()
    downloaded_models = server.downloader.get_downloaded_models()

    if model_name not in downloaded_models:
        click.echo(f"❌ Model '{model_name}' not found.")
        click.echo("Downloaded models:")
        if downloaded_models:
            for model in downloaded_models:
                click.echo(f"  • {model}")
        else:
            click.echo("  (none)")
        sys.exit(1)

    # Confirm deletion unless --force is used
    if not force:
        model_info = LIGHTWEIGHT_MODELS.get(model_name, {})
        name = model_info.get("name", model_name)
        size = model_info.get("size_mb", "unknown")
        click.echo(f"⚠️  About to delete:")
        click.echo(f"   Model: {name}")
        click.echo(f"   Size: {size} MB")
        if not click.confirm("Are you sure you want to delete this model?"):
            click.echo("❌ Deletion cancelled")
            return

    success = server.delete_model(model_name)

    if success:
        click.echo(f"✅ Successfully deleted {model_name}")
    else:
        click.echo(f"❌ Failed to delete {model_name}")
        sys.exit(1)


if __name__ == "__main__":
    model()
