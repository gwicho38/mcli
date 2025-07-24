# Custom CLI with API Endpoints Guide

This guide shows how to use mcli's decorator logic to create custom CLIs that automatically come with API endpoints using uvicorn.

## Overview

The mcli project provides powerful decorators that allow you to:
1. **Create API endpoints** from Click commands using `@api_endpoint`
2. **Route commands to daemon** using `@daemon_command`
3. **Automatically start uvicorn servers** with FastAPI
4. **Register endpoints dynamically** without manual setup

## Key Components

### 1. API Endpoint Decorator
```python
from mcli.lib.api.api import api_endpoint

@api_endpoint(
    endpoint_path="/my-endpoint",
    http_method="POST",
    description="My API endpoint",
    tags=["my-tag"]
)
def my_command():
    # Your command logic here
    return {"result": "success"}
```

### 2. Daemon Command Decorator
```python
from mcli.lib.api.daemon_decorator import daemon_command

@daemon_command(
    auto_route=True,
    fallback_to_local=True,
    timeout=30
)
def my_command():
    # Your command logic here
    pass
```

### 3. API Server Management
```python
from mcli.lib.api.api import start_api_server, stop_api_server

# Start API server
server_url = start_api_server(host="0.0.0.0", port=8000)

# Stop API server
stop_api_server()
```

## Basic Example

Here's a simple example of creating a CLI with API endpoints:

```python
import click
from mcli.lib.api.api import api_endpoint
from mcli.lib.api.daemon_decorator import daemon_command
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

@click.group(name="mycli")
def mycli():
    """My Custom CLI with API Endpoints"""
    pass

@mycli.command()
@click.option('--name', default='World', help='Name to greet')
@api_endpoint(
    endpoint_path="/greet",
    http_method="POST",
    description="Greet someone",
    tags=["greeting"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def greet(name: str):
    """Greet someone with a custom message"""
    message = f"Hello, {name}!"
    logger.info(f"Greeted: {name}")
    return {"message": message, "name": name}

if __name__ == "__main__":
    mycli()
```

## Advanced Example

Here's a more complex example with multiple endpoints and background tasks:

```python
import click
import threading
import time
from typing import Optional, Dict, Any
from pathlib import Path

from mcli.lib.api.api import api_endpoint, start_api_server
from mcli.lib.api.daemon_decorator import daemon_command
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

@click.group(name="advancedcli")
@click.option('--api-server', is_flag=True, help='Start API server')
def advancedcli(api_server: bool):
    """Advanced CLI with API Endpoints"""
    if api_server:
        server_url = start_api_server(host="0.0.0.0", port=8000)
        click.echo(f"API server running at: {server_url}")

@advancedcli.command()
@click.option('--file', type=click.Path(exists=True), required=True)
@click.option('--output', type=click.Path())
@api_endpoint(
    endpoint_path="/process-file",
    http_method="POST",
    description="Process a file and return statistics",
    tags=["file-processing"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def process_file(file: str, output: Optional[str]):
    """Process a file and return statistics"""
    file_path = Path(file)
    
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

@advancedcli.command()
@click.option('--task-name', required=True)
@click.option('--duration', default=5, type=int)
@api_endpoint(
    endpoint_path="/tasks/start",
    http_method="POST",
    description="Start a background task",
    tags=["tasks"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def start_task(task_name: str, duration: int):
    """Start a background task"""
    def run_task():
        logger.info(f"Starting task: {task_name}")
        time.sleep(duration)
        logger.info(f"Completed task: {task_name}")
    
    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    
    result = {
        "task_name": task_name,
        "duration": duration,
        "status": "started",
        "thread_id": thread.ident
    }
    
    logger.info(f"Started background task: {task_name}")
    return result

if __name__ == "__main__":
    advancedcli()
```

## Decorator Options

### @api_endpoint Options

```python
@api_endpoint(
    endpoint_path="/my-endpoint",      # API endpoint path
    http_method="POST",                # HTTP method (GET, POST, PUT, DELETE)
    response_model=None,               # Custom Pydantic response model
    description="My endpoint",         # API documentation description
    tags=["my-tag"]                   # OpenAPI tags for grouping
)
```

### @daemon_command Options

```python
@daemon_command(
    command_name="my-command",         # Custom command name
    auto_route=True,                   # Auto-route to daemon if enabled
    fallback_to_local=True,            # Fallback to local execution
    timeout=30                         # Command timeout in seconds
)
```

## API Server Configuration

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

### Configuration File (config.toml)
```toml
[api]
enabled = true
host = "0.0.0.0"
port = 8000
use_random_port = false
debug = false

[api_daemon]
enabled = true
host = "0.0.0.0"
port = 8001
auto_start = true
command_timeout = 300
```

## Usage Patterns

### 1. CLI Usage
```bash
# Start CLI with API server
python my_cli.py --api-server

# Use CLI commands
python my_cli.py greet --name Alice
python my_cli.py process-file --file data.txt
```

### 2. API Usage
```bash
# Call API endpoints
curl -X POST http://localhost:8000/greet \
     -H "Content-Type: application/json" \
     -d '{"name": "Bob"}'

curl -X POST http://localhost:8000/process-file \
     -H "Content-Type: application/json" \
     -d '{"file": "data.txt", "output": "stats.json"}'
```

### 3. Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Get API documentation
curl http://localhost:8000/docs
```

## Integration Examples

### 1. Database Operations CLI
```python
@click.command()
@click.option('--table', required=True)
@click.option('--data', help='JSON data')
@api_endpoint(
    endpoint_path="/db/insert",
    http_method="POST",
    description="Insert data into database",
    tags=["database"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def insert_data(table: str, data: Optional[str]):
    """Insert data into database"""
    import json
    from datetime import datetime
    
    if data:
        parsed_data = json.loads(data)
    else:
        parsed_data = {"timestamp": datetime.now().isoformat()}
    
    result = {
        "table": table,
        "data": parsed_data,
        "inserted_at": datetime.now().isoformat(),
        "status": "success"
    }
    
    return result
```

### 2. File Processing CLI
```python
@click.command()
@click.option('--input', type=click.Path(exists=True), required=True)
@click.option('--output', type=click.Path())
@click.option('--format', default='json', type=click.Choice(['json', 'csv', 'xml']))
@api_endpoint(
    endpoint_path="/process",
    http_method="POST",
    description="Process files in various formats",
    tags=["file-processing"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def process_file(input: str, output: Optional[str], format: str):
    """Process files in various formats"""
    input_path = Path(input)
    
    # Process based on format
    if format == 'json':
        result = process_json_file(input_path)
    elif format == 'csv':
        result = process_csv_file(input_path)
    elif format == 'xml':
        result = process_xml_file(input_path)
    
    if output:
        output_path = Path(output)
        output_path.write_text(str(result))
        result["output_file"] = str(output_path)
    
    return result
```

### 3. Background Task CLI
```python
@click.command()
@click.option('--task-name', required=True)
@click.option('--priority', default='normal', type=click.Choice(['low', 'normal', 'high']))
@api_endpoint(
    endpoint_path="/tasks/start",
    http_method="POST",
    description="Start background task with priority",
    tags=["tasks"]
)
@daemon_command(auto_route=True, fallback_to_local=True)
def start_priority_task(task_name: str, priority: str):
    """Start a background task with priority"""
    def run_priority_task():
        logger.info(f"Starting priority task: {task_name} ({priority})")
        # Task logic here
        time.sleep(10)
        logger.info(f"Completed priority task: {task_name}")
    
    thread = threading.Thread(target=run_priority_task, daemon=True)
    thread.start()
    
    result = {
        "task_name": task_name,
        "priority": priority,
        "status": "started",
        "thread_id": thread.ident,
        "started_at": time.time()
    }
    
    return result
```

## Best Practices

### 1. Error Handling
```python
@api_endpoint(endpoint_path="/my-endpoint")
@daemon_command(auto_route=True, fallback_to_local=True)
def my_command():
    try:
        # Your logic here
        return {"success": True, "result": "data"}
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return {"success": False, "error": str(e)}
```

### 2. Logging
```python
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

@api_endpoint(endpoint_path="/my-endpoint")
def my_command():
    logger.info("Starting command execution")
    # Your logic here
    logger.info("Command completed successfully")
    return {"result": "success"}
```

### 3. Configuration Management
```python
from mcli.lib.config.config import get_config_directory

@api_endpoint(endpoint_path="/config")
def get_config():
    config_dir = get_config_directory()
    # Use configuration
    return {"config_dir": str(config_dir)}
```

### 4. File System Operations
```python
from mcli.lib.fs.fs import get_absolute_path, ensure_directory_exists

@api_endpoint(endpoint_path="/files")
def process_files():
    abs_path = get_absolute_path("~/data")
    ensure_directory_exists(abs_path)
    # Process files
    return {"processed_path": abs_path}
```

## Troubleshooting

### Common Issues

1. **API Server Not Starting**
   ```bash
   # Check if port is available
   lsof -i :8000
   
   # Use random port
   export MCLI_API_PORT=0
   ```

2. **Decorator Import Errors**
   ```python
   # Ensure mcli is installed
   pip install -e .
   
   # Check imports
   python -c "from mcli.lib.api.api import api_endpoint; print('OK')"
   ```

3. **Daemon Connection Issues**
   ```python
   from mcli.lib.api.daemon_decorator import is_daemon_available
   
   if is_daemon_available():
       print("Daemon is available")
   else:
       print("Daemon is not available")
   ```

## Advanced Features

### 1. Custom Response Models
```python
from pydantic import BaseModel, Field

class CustomResponse(BaseModel):
    success: bool = Field(..., description="Operation success")
    data: Dict[str, Any] = Field(..., description="Response data")
    timestamp: str = Field(..., description="Response timestamp")

@api_endpoint(
    endpoint_path="/custom",
    response_model=CustomResponse
)
def custom_endpoint():
    return CustomResponse(
        success=True,
        data={"key": "value"},
        timestamp=datetime.now().isoformat()
    )
```

### 2. Background Tasks
```python
@api_endpoint(endpoint_path="/background")
def start_background_task():
    def background_work():
        time.sleep(10)
        logger.info("Background work completed")
    
    thread = threading.Thread(target=background_work, daemon=True)
    thread.start()
    
    return {"task_id": thread.ident, "status": "started"}
```

### 3. File Upload/Download
```python
from fastapi import UploadFile, File

@api_endpoint(endpoint_path="/upload")
async def upload_file(file: UploadFile = File(...)):
    # Handle file upload
    content = await file.read()
    # Process file
    return {"filename": file.filename, "size": len(content)}
```

## Conclusion

The mcli decorator system provides a powerful way to create CLIs with built-in API endpoints. By using `@api_endpoint` and `@daemon_command`, you can:

1. **Automatically generate API endpoints** from Click commands
2. **Route commands to daemon** for better performance
3. **Start uvicorn servers** with FastAPI integration
4. **Handle both CLI and API usage** seamlessly

This approach makes it easy to create tools that work both as command-line utilities and as API services, perfect for automation and integration scenarios.

For more examples, see `example_custom_cli_with_api.py`. 