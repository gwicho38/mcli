#!/usr/bin/env python3
"""
Example: Creating Custom CLIs with Built-in API Endpoints

This example demonstrates how to use mcli's decorator logic to create
custom CLIs that automatically come with API endpoints using uvicorn.

The key components:
1. @api_endpoint decorator - Creates API endpoints from Click commands
2. @daemon_command decorator - Routes commands to API daemon
3. FastAPI integration with uvicorn
4. Automatic endpoint registration
"""

import click
import uvicorn
import threading
import time
from typing import Optional, Dict, Any
from pathlib import Path

# Import mcli API decorators and utilities
from mcli.lib.api.api import api_endpoint, start_api_server, stop_api_server, get_api_app
from mcli.lib.api.daemon_decorator import daemon_command, is_daemon_available
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# Example 1: Simple CLI with API Endpoints
# =============================================================================

@click.group(name="mycli")
def mycli():
    """My Custom CLI with API Endpoints"""
    pass

@mycli.command()
@click.option('--name', default='World', help='Name to greet')
@click.option('--count', default=1, type=int, help='Number of greetings')
@api_endpoint(
    endpoint_path="/greet",
    http_method="POST",
    description="Greet someone with a custom message",
    tags=["greeting"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def greet(name: str, count: int):
    """Greet someone with a custom message"""
    result = []
    for i in range(count):
        result.append(f"Hello, {name}! (greeting #{i+1})")
    
    logger.info(f"Greeted {name} {count} times")
    return {"message": "\n".join(result), "count": count}

@mycli.command()
@click.option('--file', type=click.Path(exists=True), help='File to process')
@click.option('--output', type=click.Path(), help='Output file')
@api_endpoint(
    endpoint_path="/process-file",
    http_method="POST",
    description="Process a file and return statistics",
    tags=["file-processing"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def process_file(file: Optional[str], output: Optional[str]):
    """Process a file and return statistics"""
    if not file:
        raise click.UsageError("File path is required")
    
    file_path = Path(file)
    if not file_path.exists():
        raise click.FileError(f"File not found: {file}")
    
    # Simulate file processing
    stats = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines()),
        "processed": True
    }
    
    if output:
        output_path = Path(output)
        output_path.write_text(str(stats))
        stats["output_file"] = str(output_path)
    
    logger.info(f"Processed file: {file}")
    return stats

# =============================================================================
# Example 2: Advanced CLI with Database Operations
# =============================================================================

@click.group(name="dbcli")
def dbcli():
    """Database CLI with API Endpoints"""
    pass

@dbcli.command()
@click.option('--table', required=True, help='Table name')
@click.option('--data', help='Data to insert (JSON format)')
@api_endpoint(
    endpoint_path="/db/insert",
    http_method="POST",
    description="Insert data into a database table",
    tags=["database", "insert"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def insert_data(table: str, data: Optional[str]):
    """Insert data into a database table"""
    # Simulate database operation
    import json
    from datetime import datetime
    
    if data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            raise click.BadParameter("Invalid JSON data")
    else:
        parsed_data = {"timestamp": datetime.now().isoformat()}
    
    result = {
        "table": table,
        "data": parsed_data,
        "inserted_at": datetime.now().isoformat(),
        "status": "success"
    }
    
    logger.info(f"Inserted data into table: {table}")
    return result

@dbcli.command()
@click.option('--table', required=True, help='Table name')
@click.option('--query', help='Query conditions')
@api_endpoint(
    endpoint_path="/db/query",
    http_method="GET",
    description="Query data from a database table",
    tags=["database", "query"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def query_data(table: str, query: Optional[str]):
    """Query data from a database table"""
    # Simulate database query
    from datetime import datetime
    
    result = {
        "table": table,
        "query": query or "SELECT *",
        "results": [
            {"id": 1, "name": "Item 1", "created_at": datetime.now().isoformat()},
            {"id": 2, "name": "Item 2", "created_at": datetime.now().isoformat()}
        ],
        "count": 2,
        "queried_at": datetime.now().isoformat()
    }
    
    logger.info(f"Queried table: {table}")
    return result

# =============================================================================
# Example 3: CLI with Background Tasks
# =============================================================================

@click.group(name="taskcli")
def taskcli():
    """Task Management CLI with API Endpoints"""
    pass

@taskcli.command()
@click.option('--task-name', required=True, help='Name of the task')
@click.option('--duration', default=5, type=int, help='Task duration in seconds')
@api_endpoint(
    endpoint_path="/tasks/start",
    http_method="POST",
    description="Start a background task",
    tags=["tasks", "background"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def start_task(task_name: str, duration: int):
    """Start a background task"""
    import threading
    import time
    
    def run_task():
        logger.info(f"Starting task: {task_name}")
        time.sleep(duration)
        logger.info(f"Completed task: {task_name}")
    
    # Start task in background
    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    
    result = {
        "task_name": task_name,
        "duration": duration,
        "status": "started",
        "started_at": time.time(),
        "thread_id": thread.ident
    }
    
    logger.info(f"Started background task: {task_name}")
    return result

@taskcli.command()
@click.option('--task-id', help='Task ID to check')
@api_endpoint(
    endpoint_path="/tasks/status",
    http_method="GET",
    description="Check task status",
    tags=["tasks", "status"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def task_status(task_id: Optional[str]):
    """Check task status"""
    # Simulate task status check
    result = {
        "task_id": task_id or "default",
        "status": "running",
        "progress": 75,
        "started_at": time.time() - 300,  # 5 minutes ago
        "estimated_completion": time.time() + 100
    }
    
    logger.info(f"Checked status for task: {task_id}")
    return result

# =============================================================================
# API Server Management
# =============================================================================

def start_api_server_for_cli(host: str = "0.0.0.0", port: int = None, debug: bool = False):
    """Start the API server for the CLI"""
    try:
        # Start the API server
        server_url = start_api_server(host=host, port=port, debug=debug)
        logger.info(f"API server started at: {server_url}")
        return server_url
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        return None

def stop_api_server_for_cli():
    """Stop the API server"""
    try:
        stop_api_server()
        logger.info("API server stopped")
    except Exception as e:
        logger.error(f"Failed to stop API server: {e}")

# =============================================================================
# Main CLI with API Integration
# =============================================================================

@click.group(name="customcli")
@click.option('--api-server', is_flag=True, help='Start API server')
@click.option('--host', default='0.0.0.0', help='API server host')
@click.option('--port', type=int, help='API server port')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def customcli(api_server: bool, host: str, port: Optional[int], debug: bool):
    """Custom CLI with built-in API endpoints"""
    if api_server:
        # Start API server in background
        server_url = start_api_server_for_cli(host=host, port=port, debug=debug)
        if server_url:
            click.echo(f"API server running at: {server_url}")
            click.echo("Available endpoints:")
            click.echo("  POST /greet - Greet someone")
            click.echo("  POST /process-file - Process a file")
            click.echo("  POST /db/insert - Insert database data")
            click.echo("  GET  /db/query - Query database data")
            click.echo("  POST /tasks/start - Start background task")
            click.echo("  GET  /tasks/status - Check task status")
            click.echo("  GET  /health - Health check")
            click.echo("  GET  / - Root endpoint")

# Add subcommands
customcli.add_command(mycli)
customcli.add_command(dbcli)
customcli.add_command(taskcli)

@customcli.command()
def health():
    """Health check for the CLI"""
    return {"status": "healthy", "timestamp": time.time()}

@customcli.command()
def api_status():
    """Check API server status"""
    if is_daemon_available():
        return {"api_server": "running", "daemon": "available"}
    else:
        return {"api_server": "not_running", "daemon": "not_available"}

# =============================================================================
# Usage Examples
# =============================================================================

if __name__ == "__main__":
    # Example usage:
    # 
    # 1. Start CLI with API server:
    #    python example_custom_cli_with_api.py --api-server
    #
    # 2. Use CLI commands:
    #    python example_custom_cli_with_api.py greet --name Alice --count 3
    #    python example_custom_cli_with_api.py process-file --file data.txt
    #
    # 3. Use API endpoints (when server is running):
    #    curl -X POST http://localhost:8000/greet \
    #         -H "Content-Type: application/json" \
    #         -d '{"name": "Bob", "count": 2}'
    #
    #    curl -X POST http://localhost:8000/process-file \
    #         -H "Content-Type: application/json" \
    #         -d '{"file": "data.txt", "output": "stats.json"}'
    #
    # 4. Check API status:
    #    curl http://localhost:8000/health
    #    curl http://localhost:8000/
    
    customcli() 