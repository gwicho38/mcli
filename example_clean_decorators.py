#!/usr/bin/env python3
"""
Example: Using Clean MCLI Decorators

This example demonstrates the new clean decorator syntax:
- @mcli.api - Create API endpoints
- @mcli.daemon - Route to daemon
- @mcli.cli_with_api - Combined decorator

The new syntax is much cleaner and more intuitive!
"""

import click
import time
from typing import Optional, Dict, Any
from pathlib import Path

# Import the clean decorators
import mcli

# =============================================================================
# Example 1: Simple API Endpoint
# =============================================================================

@click.group(name="simplecli")
def simplecli():
    """Simple CLI with clean decorators"""
    pass

@simplecli.command()
@click.option('--name', default='World', help='Name to greet')
@mcli.api("/greet", "POST", description="Greet someone")
def greet(name: str):
    """Greet someone with a clean decorator"""
    message = f"Hello, {name}!"
    return {"message": message, "name": name}

# =============================================================================
# Example 2: Daemon Processing
# =============================================================================

@click.group(name="daemoncli")
def daemoncli():
    """CLI with daemon processing"""
    pass

@daemoncli.command()
@click.option('--file', type=click.Path(exists=True), required=True)
@mcli.daemon(auto_route=True, fallback_to_local=True)
def process_large_file(file: str):
    """Process a large file using daemon"""
    file_path = Path(file)
    
    # Simulate heavy processing
    time.sleep(2)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "processed": True,
        "processed_by": "daemon"
    }
    
    return result

# =============================================================================
# Example 3: Combined Decorator (Most Common Use Case)
# =============================================================================

@click.group(name="combinedcli")
def combinedcli():
    """CLI using the combined decorator"""
    pass

@combinedcli.command()
@click.option('--input', type=click.Path(exists=True), required=True)
@click.option('--output', type=click.Path())
@mcli.cli_with_api(
    "/process-file",
    "POST",
    description="Process files with API and daemon support",
    tags=["file-processing"],
    enable_daemon=True,
    daemon_timeout=60
)
def process_file(input: str, output: Optional[str]):
    """Process a file with both API endpoint and daemon support"""
    input_path = Path(input)
    
    # Simulate processing
    time.sleep(1)
    
    result = {
        "input_file": input_path.name,
        "size_bytes": input_path.stat().st_size,
        "lines": len(input_path.read_text().splitlines()),
        "processed": True,
        "processed_at": time.time()
    }
    
    if output:
        output_path = Path(output)
        output_path.write_text(str(result))
        result["output_file"] = str(output_path)
    
    return result

# =============================================================================
# Example 4: Health and Status Endpoints
# =============================================================================

@click.group(name="healthcli")
def healthcli():
    """CLI with health and status endpoints"""
    pass

@healthcli.command()
@mcli.api("/health", "GET", description="Health check")
def health():
    """Health check endpoint"""
    return mcli.health_check()

@healthcli.command()
@mcli.api("/status", "GET", description="System status")
def status():
    """System status endpoint"""
    return mcli.status_check()

# =============================================================================
# Example 5: Background Tasks
# =============================================================================

@click.group(name="taskcli")
def taskcli():
    """CLI with background tasks"""
    pass

@taskcli.command()
@click.option('--task-name', required=True)
@click.option('--duration', default=5, type=int)
@mcli.cli_with_api(
    "/tasks/start",
    "POST",
    description="Start background task",
    tags=["tasks"]
)
def start_task(task_name: str, duration: int):
    """Start a background task"""
    import threading
    
    def run_task():
        print(f"Starting task: {task_name}")
        time.sleep(duration)
        print(f"Completed task: {task_name}")
    
    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    
    result = {
        "task_name": task_name,
        "duration": duration,
        "status": "started",
        "thread_id": thread.ident,
        "started_at": time.time()
    }
    
    return result

# =============================================================================
# Main CLI with Server Management
# =============================================================================

@click.group(name="maincli")
@click.option('--start-server', is_flag=True, help='Start API server')
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--port', type=int, help='Server port')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def maincli(start_server: bool, host: str, port: Optional[int], debug: bool):
    """Main CLI with clean decorators and server management"""
    if start_server:
        server_url = mcli.start_server(host=host, port=port, debug=debug)
        if server_url:
            click.echo(f"API server running at: {server_url}")
            click.echo("Available endpoints:")
            click.echo("  POST /greet - Greet someone")
            click.echo("  POST /process-file - Process files")
            click.echo("  POST /tasks/start - Start background task")
            click.echo("  GET  /health - Health check")
            click.echo("  GET  /status - System status")

# Add all subcommands
maincli.add_command(simplecli)
maincli.add_command(daemoncli)
maincli.add_command(combinedcli)
maincli.add_command(healthcli)
maincli.add_command(taskcli)

# =============================================================================
# Usage Examples
# =============================================================================

if __name__ == "__main__":
    # Example usage:
    #
    # 1. Start CLI with API server:
    #    python example_clean_decorators.py --start-server
    #
    # 2. Use CLI commands:
    #    python example_clean_decorators.py greet --name Alice
    #    python example_clean_decorators.py process-file --input data.txt
    #
    # 3. Use API endpoints (when server is running):
    #    curl -X POST http://localhost:8000/greet \
    #         -H "Content-Type: application/json" \
    #         -d '{"name": "Bob"}'
    #
    #    curl -X POST http://localhost:8000/process-file \
    #         -H "Content-Type: application/json" \
    #         -d '{"input": "data.txt", "output": "result.json"}'
    #
    # 4. Check health and status:
    #    curl http://localhost:8000/health
    #    curl http://localhost:8000/status
    #
    # 5. Start background task:
    #    curl -X POST http://localhost:8000/tasks/start \
    #         -H "Content-Type: application/json" \
    #         -d '{"task_name": "my_task", "duration": 10}'
    
    maincli() 