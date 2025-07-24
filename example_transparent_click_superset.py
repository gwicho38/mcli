#!/usr/bin/env python3
"""
Example: Transparent Click Superset with MCLI

This example demonstrates how MCLI is a transparent superset of Click.
All Click functionality works exactly as expected, with additional
API and background processing capabilities available when needed.
"""

import click
import time
from typing import Optional, Dict, Any
from pathlib import Path

# Import MCLI as a transparent Click superset
import mcli

# =============================================================================
# Example 1: Standard Click Commands (Work Exactly as Before)
# =============================================================================

@mcli.group(name="standardcli")
def standardcli():
    """Standard Click group - works exactly as before"""
    pass

@standardcli.command()
@click.option('--name', default='World', help='Name to greet')
def greet(name: str):
    """Standard Click command - no API, no background processing"""
    message = f"Hello, {name}!"
    click.echo(message)
    return message

@standardcli.command()
@click.option('--file', type=click.Path(exists=True), required=True)
def show_file_info(file: str):
    """Standard Click command - works exactly as in Click"""
    file_path = Path(file)
    info = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines())
    }
    click.echo(f"File info: {info}")
    return info

# =============================================================================
# Example 2: Click Commands with API Endpoints
# =============================================================================

@mcli.group(name="apicli")
def apicli():
    """Click group with API endpoints"""
    pass

@apicli.command(api_endpoint="/greet", api_method="POST")
@click.option('--name', default='World', help='Name to greet')
def greet_api(name: str):
    """Click command with API endpoint - works as CLI and API"""
    message = f"Hello, {name}!"
    click.echo(message)  # Still works as CLI
    return {"message": message, "name": name}  # Also works as API

@apicli.command(api_endpoint="/file-info", api_method="POST")
@click.option('--file', type=click.Path(exists=True), required=True)
def file_info_api(file: str):
    """Click command with API endpoint"""
    file_path = Path(file)
    info = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines())
    }
    click.echo(f"File info: {info}")  # CLI output
    return info  # API response

# =============================================================================
# Example 3: Click Commands with Background Processing
# =============================================================================

@mcli.group(name="backgroundcli")
def backgroundcli():
    """Click group with background processing"""
    pass

@backgroundcli.command(background=True, background_timeout=60)
@click.option('--file', type=click.Path(exists=True), required=True)
def process_file_background(file: str):
    """Click command with background processing"""
    file_path = Path(file)
    
    # Simulate processing
    time.sleep(2)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "processed": True,
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    click.echo(f"Processed: {result}")
    return result

@backgroundcli.command(background=True, background_timeout=300)
@click.option('--task-name', required=True)
@click.option('--duration', default=5, type=int)
def long_task_background(task_name: str, duration: int):
    """Click command with background processing for long tasks"""
    click.echo(f"Starting task: {task_name}")
    
    # Simulate long-running work
    for i in range(duration):
        time.sleep(1)
        if i % 60 == 0:  # Log every minute
            click.echo(f"Task {task_name}: {i//60} minutes completed")
    
    result = {
        "task_name": task_name,
        "duration": duration,
        "status": "completed",
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    click.echo(f"Task completed: {result}")
    return result

# =============================================================================
# Example 4: Click Commands with Both API and Background
# =============================================================================

@mcli.group(name="fullcli")
def fullcli():
    """Click group with both API endpoints and background processing"""
    pass

@fullcli.command(
    api_endpoint="/process-file",
    api_method="POST",
    background=True,
    background_timeout=60
)
@click.option('--file', type=click.Path(exists=True), required=True)
@click.option('--output', type=click.Path())
def process_file_full(file: str, output: Optional[str]):
    """Click command with both API endpoint and background processing"""
    file_path = Path(file)
    
    # Simulate processing
    time.sleep(2)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines()),
        "processed": True,
        "processed_at": time.time(),
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    if output:
        output_path = Path(output)
        output_path.write_text(str(result))
        result["output_file"] = str(output_path)
    
    click.echo(f"Processed: {result}")
    return result

# =============================================================================
# Example 5: Convenience Decorators
# =============================================================================

@mcli.group(name="conveniencecli")
def conveniencecli():
    """Click group using convenience decorators"""
    pass

@conveniencecli.command()
@mcli.api_command("/health", "GET", description="Health check")
def health():
    """Health check using convenience decorator"""
    return mcli.health_check()

@conveniencecli.command()
@mcli.api_command("/status", "GET", description="System status")
def status():
    """Status check using convenience decorator"""
    return mcli.status_check()

@conveniencecli.command()
@mcli.background_command(timeout=300)
@click.option('--task-name', required=True)
def background_task(task_name: str):
    """Background task using convenience decorator"""
    click.echo(f"Starting background task: {task_name}")
    time.sleep(5)
    return {"task": task_name, "status": "completed"}

# =============================================================================
# Example 6: All Click Features Still Work
# =============================================================================

@mcli.group(name="clickfeatures")
def clickfeatures():
    """Demonstrating that all Click features still work"""
    pass

@clickfeatures.command(
    name="complex-command",
    help="A complex command with all Click features",
    short_help="Complex command",
    no_args_is_help=True,
    hidden=False,
    deprecated=False
)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--count', '-c', default=1, help='Number of times')
@click.argument('message', nargs=-1)
def complex_command(verbose: bool, count: int, message: tuple):
    """Complex Click command with all features - works exactly as in Click"""
    if verbose:
        click.echo("Verbose mode enabled")
    
    msg = " ".join(message) if message else "Hello"
    
    for i in range(count):
        click.echo(f"{i+1}: {msg}")
    
    result = {
        "message": msg,
        "count": count,
        "verbose": verbose
    }
    
    return result

# =============================================================================
# Main CLI with Server Management
# =============================================================================

@mcli.group(name="maincli")
@click.option('--start-server', is_flag=True, help='Start API server')
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--port', type=int, help='Server port')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def maincli(start_server: bool, host: str, port: Optional[int], debug: bool):
    """Main CLI demonstrating transparent Click superset"""
    if start_server:
        server_url = mcli.start_server(host=host, port=port, debug=debug)
        if server_url:
            click.echo(f"API server running at: {server_url}")
            click.echo("Available endpoints:")
            click.echo("  POST /greet - Greet someone")
            click.echo("  POST /file-info - Get file info")
            click.echo("  POST /process-file - Process files")
            click.echo("  GET  /health - Health check")
            click.echo("  GET  /status - System status")
            click.echo("")
            click.echo("Background processing:")
            if mcli.is_background_available():
                click.echo("  ✅ Background service is available")
            else:
                click.echo("  ⚠️  Background service not available (will use local execution)")

# Add all subcommands
maincli.add_command(standardcli)
maincli.add_command(apicli)
maincli.add_command(backgroundcli)
maincli.add_command(fullcli)
maincli.add_command(conveniencecli)
maincli.add_command(clickfeatures)

# =============================================================================
# Usage Examples
# =============================================================================

if __name__ == "__main__":
    # Example usage:
    #
    # 1. Standard Click commands (work exactly as before):
    #    python example_transparent_click_superset.py standardcli greet --name Alice
    #    python example_transparent_click_superset.py standardcli show-file-info --file data.txt
    #
    # 2. Click commands with API endpoints:
    #    python example_transparent_click_superset.py apicli greet-api --name Bob
    #    python example_transparent_click_superset.py apicli file-info-api --file data.txt
    #
    # 3. Click commands with background processing:
    #    python example_transparent_click_superset.py backgroundcli process-file-background --file data.txt
    #    python example_transparent_click_superset.py backgroundcli long-task-background --task-name "test" --duration 10
    #
    # 4. Click commands with both API and background:
    #    python example_transparent_click_superset.py fullcli process-file-full --file data.txt
    #
    # 5. Convenience decorators:
    #    python example_transparent_click_superset.py conveniencecli health
    #    python example_transparent_click_superset.py conveniencecli background-task --task-name "test"
    #
    # 6. All Click features:
    #    python example_transparent_click_superset.py clickfeatures complex-command --verbose --count 3 "Hello World"
    #
    # 7. Start with API server:
    #    python example_transparent_click_superset.py --start-server
    #
    # 8. Use API endpoints (when server is running):
    #    curl -X POST http://localhost:8000/greet \
    #         -H "Content-Type: application/json" \
    #         -d '{"name": "Bob"}'
    #
    #    curl -X POST http://localhost:8000/process-file \
    #         -H "Content-Type: application/json" \
    #         -d '{"file": "data.txt"}'
    
    maincli() 