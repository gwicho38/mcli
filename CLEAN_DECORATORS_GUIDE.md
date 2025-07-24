# Clean MCLI Decorators Guide

This guide shows how to use the new clean, intuitive decorator syntax for creating CLIs with API endpoints.

## Overview

The new decorator system provides a much cleaner and more intuitive API:

- **`@mcli.api`** - Create API endpoints from Click commands
- **`@mcli.daemon`** - Route commands to background daemon
- **`@mcli.cli_with_api`** - Combined decorator for most common use case

## New vs Old Syntax

### Old Syntax (Still Available)
```python
from mcli.lib.api.api import api_endpoint
from mcli.lib.api.daemon_decorator import daemon_command

@api_endpoint("/greet", "POST")
@daemon_command(auto_route=True, fallback_to_local=True)
def greet(name: str):
    return {"message": f"Hello, {name}!"}
```

### New Clean Syntax
```python
import mcli

@mcli.api("/greet", "POST")
@mcli.daemon(auto_route=True, fallback_to_local=True)
def greet(name: str):
    return {"message": f"Hello, {name}!"}
```

## Decorator Reference

### 1. @mcli.api - Create API Endpoints

```python
@mcli.api(
    endpoint_path="/my-endpoint",      # API endpoint path
    http_method="POST",                # HTTP method
    description="My endpoint",         # API documentation
    tags=["my-tag"]                   # OpenAPI tags
)
def my_command():
    return {"result": "success"}
```

**Parameters:**
- `endpoint_path`: API endpoint path (defaults to function name)
- `http_method`: HTTP method (GET, POST, PUT, DELETE)
- `response_model`: Custom Pydantic response model
- `description`: API documentation description
- `tags`: OpenAPI tags for grouping

### 2. @mcli.daemon - Route to Background Daemon

```python
@mcli.daemon(
    auto_route=True,                   # Auto-route to daemon
    fallback_to_local=True,            # Fallback to local execution
    timeout=30                         # Command timeout
)
def process_large_file(file_path: str):
    # This runs in background daemon if available
    return process_file(file_path)
```

**Parameters:**
- `command_name`: Custom command name (defaults to function name)
- `auto_route`: Automatically route to daemon if enabled
- `fallback_to_local`: Fallback to local execution if daemon fails
- `timeout`: Command timeout in seconds

### 3. @mcli.cli_with_api - Combined Decorator

```python
@mcli.cli_with_api(
    "/process-file",                   # API endpoint path
    "POST",                           # HTTP method
    description="Process files",       # API description
    tags=["file-processing"],          # OpenAPI tags
    enable_daemon=True,               # Enable daemon routing
    daemon_timeout=60                 # Daemon timeout
)
def process_file(input: str, output: str):
    # This creates both API endpoint and daemon support
    return {"processed": input}
```

**Parameters:**
- `endpoint_path`: API endpoint path
- `http_method`: HTTP method for the API endpoint
- `response_model`: Custom Pydantic response model
- `description`: API documentation description
- `tags`: OpenAPI tags for grouping
- `enable_daemon`: Whether to enable daemon routing
- `daemon_timeout`: Daemon command timeout

## Usage Examples

### 1. Simple API Endpoint

```python
import click
import mcli

@click.group(name="mycli")
def mycli():
    """My CLI with clean decorators"""
    pass

@mycli.command()
@click.option('--name', default='World', help='Name to greet')
@mcli.api("/greet", "POST", description="Greet someone")
def greet(name: str):
    """Greet someone with a clean decorator"""
    message = f"Hello, {name}!"
    return {"message": message, "name": name}

if __name__ == "__main__":
    mycli()
```

### 2. Daemon Processing

```python
@click.command()
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
```

### 3. Combined Decorator (Recommended)

```python
@click.command()
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
```

### 4. Health and Status Endpoints

```python
@click.command()
@mcli.api("/health", "GET", description="Health check")
def health():
    """Health check endpoint"""
    return mcli.health_check()

@click.command()
@mcli.api("/status", "GET", description="System status")
def status():
    """System status endpoint"""
    return mcli.status_check()
```

### 5. Background Tasks

```python
@click.command()
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
```

## Server Management

### Start API Server

```python
import mcli

# Start server with default settings
server_url = mcli.start_server()

# Start server with custom settings
server_url = mcli.start_server(
    host="0.0.0.0",
    port=8000,
    debug=True
)

if server_url:
    print(f"API server running at: {server_url}")
```

### Stop API Server

```python
import mcli

# Stop the API server
mcli.stop_server()
```

### Check Server Status

```python
import mcli

# Check if server is running
if mcli.is_server_running():
    print("API server is running")
else:
    print("API server is not running")

# Check if daemon is available
if mcli.is_daemon_available():
    print("Daemon is available")
else:
    print("Daemon is not available")
```

## Configuration

### Environment Variables

```bash
# Enable API server
export MCLI_API_SERVER=true

# Configure host and port
export MCLI_API_HOST=0.0.0.0
export MCLI_API_PORT=8000

# Enable debug mode
export MCLI_API_DEBUG=true
```

### Programmatic Configuration

```python
import mcli

# Enable API server programmatically
mcli.enable_api_server()

# Disable API server
mcli.disable_api_server()

# Get current configuration
config = mcli.get_api_config()
print(f"API enabled: {config['enabled']}")
print(f"Host: {config['host']}")
print(f"Port: {config['port']}")
```

## Complete Example

```python
#!/usr/bin/env python3
"""
Complete example using clean MCLI decorators
"""

import click
import time
from typing import Optional
from pathlib import Path

import mcli

@click.group(name="myapp")
@click.option('--start-server', is_flag=True, help='Start API server')
def myapp(start_server: bool):
    """My application with clean MCLI decorators"""
    if start_server:
        server_url = mcli.start_server(port=8000)
        if server_url:
            click.echo(f"API server running at: {server_url}")

@myapp.command()
@click.option('--name', default='World', help='Name to greet')
@mcli.cli_with_api(
    "/greet",
    "POST",
    description="Greet someone",
    tags=["greeting"]
)
def greet(name: str):
    """Greet someone"""
    message = f"Hello, {name}!"
    return {"message": message, "name": name}

@myapp.command()
@click.option('--file', type=click.Path(exists=True), required=True)
@click.option('--output', type=click.Path())
@mcli.cli_with_api(
    "/process-file",
    "POST",
    description="Process a file",
    tags=["file-processing"]
)
def process_file(file: str, output: Optional[str]):
    """Process a file"""
    file_path = Path(file)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines()),
        "processed": True
    }
    
    if output:
        output_path = Path(output)
        output_path.write_text(str(result))
        result["output_file"] = str(output_path)
    
    return result

@myapp.command()
@mcli.api("/health", "GET", description="Health check")
def health():
    """Health check endpoint"""
    return mcli.health_check()

if __name__ == "__main__":
    myapp()
```

## Usage Patterns

### 1. CLI Usage
```bash
# Start with API server
python myapp.py --start-server

# Use CLI commands
python myapp.py greet --name Alice
python myapp.py process-file --file data.txt
```

### 2. API Usage
```bash
# Call API endpoints
curl -X POST http://localhost:8000/greet \
     -H "Content-Type: application/json" \
     -d '{"name": "Bob"}'

curl -X POST http://localhost:8000/process-file \
     -H "Content-Type: application/json" \
     -d '{"file": "data.txt", "output": "result.json"}'
```

### 3. Health Checks
```bash
# Check health
curl http://localhost:8000/health

# Get API documentation
curl http://localhost:8000/docs
```

## Benefits of New Syntax

1. **Cleaner Import**: Just `import mcli`
2. **Intuitive Names**: `@mcli.api` and `@mcli.daemon`
3. **Combined Decorator**: `@mcli.cli_with_api` for common use case
4. **Better Documentation**: Clear docstrings and examples
5. **Convenience Functions**: `mcli.health_check()`, `mcli.status_check()`
6. **Server Management**: `mcli.start_server()`, `mcli.stop_server()`

## Migration from Old Syntax

### Before (Old Syntax)
```python
from mcli.lib.api.api import api_endpoint
from mcli.lib.api.daemon_decorator import daemon_command

@api_endpoint("/greet", "POST")
@daemon_command(auto_route=True, fallback_to_local=True)
def greet(name: str):
    return {"message": f"Hello, {name}!"}
```

### After (New Syntax)
```python
import mcli

@mcli.cli_with_api("/greet", "POST")
def greet(name: str):
    return {"message": f"Hello, {name}!"}
```

The new syntax is much cleaner and more intuitive, while providing the same powerful functionality! 