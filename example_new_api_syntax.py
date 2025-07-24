#!/usr/bin/env python3
"""
Example: New MCLI API Syntax

This example demonstrates the new clean decorator syntax:
- @mcli.api - Create API endpoints with optional background processing
- @mcli.background - Enable background processing for better performance

The new syntax is much cleaner and more intuitive!
"""

import click
import time
from typing import Optional, Dict, Any
from pathlib import Path

# Import the clean decorators
import mcli

# =============================================================================
# Example 1: Simple API Endpoint (No Background Processing)
# =============================================================================

@click.group(name="simplecli")
def simplecli():
    """Simple CLI with API endpoints"""
    pass

@simplecli.command()
@click.option('--name', default='World', help='Name to greet')
@mcli.api("/greet", "POST", description="Greet someone", enable_background=False)
def greet(name: str):
    """Greet someone - runs immediately"""
    message = f"Hello, {name}!"
    return {"message": message, "name": name}

# =============================================================================
# Example 2: API Endpoint with Background Processing
# =============================================================================

@click.group(name="backgroundcli")
def backgroundcli():
    """CLI with background processing"""
    pass

@backgroundcli.command()
@click.option('--file', type=click.Path(exists=True), required=True)
@mcli.api(
    "/process-file",
    "POST",
    description="Process a file with background processing",
    tags=["file-processing"],
    enable_background=True,
    background_timeout=60
)
def process_file(file: str):
    """Process a file - can run in background for better performance"""
    file_path = Path(file)
    
    # Simulate processing
    time.sleep(2)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines()),
        "processed": True,
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    return result

# =============================================================================
# Example 3: Background Processing Only (No API Endpoint)
# =============================================================================

@click.group(name="backgroundonlycli")
def backgroundonlycli():
    """CLI with background processing only"""
    pass

@backgroundonlycli.command()
@click.option('--task-name', required=True)
@click.option('--duration', default=5, type=int)
@mcli.background(auto_route=True, fallback_to_local=True, timeout=300)
def long_running_task(task_name: str, duration: int):
    """Long running task - runs in background for better performance"""
    print(f"Starting task: {task_name}")
    time.sleep(duration)
    print(f"Completed task: {task_name}")
    
    result = {
        "task_name": task_name,
        "duration": duration,
        "status": "completed",
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    return result

# =============================================================================
# Example 4: Health and Status Endpoints
# =============================================================================

@click.group(name="healthcli")
def healthcli():
    """CLI with health and status endpoints"""
    pass

@healthcli.command()
@mcli.api("/health", "GET", description="Health check", enable_background=False)
def health():
    """Health check endpoint"""
    return mcli.health_check()

@healthcli.command()
@mcli.api("/status", "GET", description="System status", enable_background=False)
def status():
    """System status endpoint"""
    return mcli.status_check()

# =============================================================================
# Example 5: Database Operations with Background Processing
# =============================================================================

@click.group(name="dbcli")
def dbcli():
    """CLI with database operations"""
    pass

@dbcli.command()
@click.option('--table', required=True)
@click.option('--data', help='JSON data')
@mcli.api(
    "/db/insert",
    "POST",
    description="Insert data into database",
    tags=["database"],
    enable_background=True,
    background_timeout=30
)
def insert_data(table: str, data: Optional[str]):
    """Insert data into database - can run in background"""
    import json
    from datetime import datetime
    
    if data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            raise click.BadParameter("Invalid JSON data")
    else:
        parsed_data = {"timestamp": datetime.now().isoformat()}
    
    # Simulate database operation
    time.sleep(1)
    
    result = {
        "table": table,
        "data": parsed_data,
        "inserted_at": datetime.now().isoformat(),
        "status": "success",
        "processed_in": "background" if mcli.is_background_available() else "local"
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
    """Main CLI with new API syntax and server management"""
    if start_server:
        server_url = mcli.start_server(host=host, port=port, debug=debug)
        if server_url:
            click.echo(f"API server running at: {server_url}")
            click.echo("Available endpoints:")
            click.echo("  POST /greet - Greet someone (immediate)")
            click.echo("  POST /process-file - Process files (background)")
            click.echo("  POST /db/insert - Insert database data (background)")
            click.echo("  GET  /health - Health check")
            click.echo("  GET  /status - System status")
            click.echo("")
            click.echo("Background processing:")
            if mcli.is_background_available():
                click.echo("  ✅ Background service is available")
            else:
                click.echo("  ⚠️  Background service not available (will use local execution)")

# Add all subcommands
maincli.add_command(simplecli)
maincli.add_command(backgroundcli)
maincli.add_command(backgroundonlycli)
maincli.add_command(healthcli)
maincli.add_command(dbcli)

# =============================================================================
# Background Processing Explanation
# =============================================================================

def explain_background_processing():
    """
    Explanation of background processing functionality:
    
    Background processing provides several benefits:
    
    1. **Non-blocking execution**: Commands run in background, don't block the main process
    2. **Concurrent operations**: Multiple commands can run simultaneously
    3. **Better resource management**: Background service manages memory and CPU usage
    4. **Long-running tasks**: Support for tasks that take minutes or hours
    5. **Automatic fallback**: If background service is unavailable, runs locally
    
    When to use background processing:
    - File processing operations
    - Database operations
    - Machine learning tasks
    - Data analysis
    - Any operation that might take more than a few seconds
    
    When NOT to use background processing:
    - Simple calculations
    - Quick data lookups
    - Health checks
    - Status queries
    """
    pass

# =============================================================================
# Usage Examples
# =============================================================================

if __name__ == "__main__":
    # Example usage:
    #
    # 1. Start CLI with API server:
    #    python example_new_api_syntax.py --start-server
    #
    # 2. Use CLI commands:
    #    python example_new_api_syntax.py greet --name Alice
    #    python example_new_api_syntax.py process-file --file data.txt
    #    python example_new_api_syntax.py long-running-task --task-name "test" --duration 10
    #
    # 3. Use API endpoints (when server is running):
    #    curl -X POST http://localhost:8000/greet \
    #         -H "Content-Type: application/json" \
    #         -d '{"name": "Bob"}'
    #
    #    curl -X POST http://localhost:8000/process-file \
    #         -H "Content-Type: application/json" \
    #         -d '{"file": "data.txt"}'
    #
    # 4. Check health and status:
    #    curl http://localhost:8000/health
    #    curl http://localhost:8000/status
    #
    # 5. Database operations:
    #    curl -X POST http://localhost:8000/db/insert \
    #         -H "Content-Type: application/json" \
    #         -d '{"table": "users", "data": "{\"name\": \"John\"}"}'
    
    maincli() 