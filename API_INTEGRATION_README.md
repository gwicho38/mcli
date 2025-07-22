# MCLI API Integration

This document explains how to use the API decorator that automatically makes Click commands also serve as API endpoints.

## Overview

The API decorator allows you to expose Click commands as REST API endpoints without writing additional code. When you apply the `@api_endpoint` decorator to a Click command, it automatically:

1. Creates a FastAPI endpoint for the command
2. Handles parameter conversion between HTTP requests and Click options
3. Provides automatic response formatting
4. Includes error handling and logging
5. **Uses random ports by default for security**

## Quick Start

### 1. Basic Usage

```python
import click
from mcli.lib.api.api import api_endpoint, create_success_response_model

@click.command()
@api_endpoint("/hello", "GET", create_success_response_model(str))
@click.option('--name', default='World', help='Name to greet')
def hello(name: str):
    """Simple hello command with API endpoint."""
    message = f"Hello, {name}!"
    click.echo(message)
    return message
```

### 2. Enable API Server

#### Option A: Environment Variable (Quick)
```bash
export MCLI_API_SERVER=true
python -m mcli
```

#### Option B: Configuration File (Recommended)
Edit `config.toml`:
```toml
[api]
enabled = true
host = "0.0.0.0"
port = null  # null means use random port
use_random_port = true
debug = false
```

### 3. Run the Application

```bash
python -m mcli
```

The API server will start automatically with a random port and expose all decorated commands as endpoints.

## Configuration

### Configuration File (`config.toml`)

The API server can be configured through the `config.toml` file:

```toml
[api]
enabled = true           # Enable/disable API server
host = "0.0.0.0"        # Host to bind to
port = null              # Port (null = random port)
use_random_port = true   # Use random port if port is null
debug = false            # Enable debug mode
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCLI_API_SERVER` | `false` | Enable API server (`true`, `1`, `yes`) |
| `MCLI_API_HOST` | `0.0.0.0` | API server host |
| `MCLI_API_PORT` | `null` | API server port (null = random) |
| `MCLI_API_DEBUG` | `false` | Enable debug mode |

### Configuration Priority

1. **Environment variables** (highest priority)
2. **User config**: `~/.config/mcli/config.toml`
3. **Project config**: `./config.toml`
4. **Default values** (lowest priority)

## Random Port Behavior

### Security Benefits

- **No port conflicts**: Random ports prevent conflicts with other services
- **Security through obscurity**: Harder to guess the API endpoint
- **Multiple instances**: Can run multiple MCLI instances simultaneously

### Port Selection

The system will:
1. Try ports starting from 8000
2. Find the first available port
3. If no ports available in range, use random port in safe range (49152-65535)

### Finding Your Port

When the API server starts, it logs the URL:
```
✅ API server started at http://0.0.0.0:8473
📋 Available endpoints:
   GET  http://0.0.0.0:8473/health
   GET  http://0.0.0.0:8473/
   GET  http://0.0.0.0:8473/docs
   GET  http://0.0.0.0:8473/redoc
```

## Decorator Parameters

### `@api_endpoint()`

```python
@api_endpoint(
    endpoint_path: str = None,           # API endpoint path (defaults to command name)
    http_method: str = "POST",           # HTTP method (GET, POST, PUT, DELETE)
    response_model: BaseModel = None,    # Pydantic model for response validation
    description: str = None,             # API endpoint description
    tags: List[str] = None              # API tags for grouping
)
```

### Examples

#### GET Endpoint
```python
@click.command()
@api_endpoint("/users", "GET", create_success_response_model(list))
def list_users():
    """List all users."""
    users = ["Alice", "Bob", "Charlie"]
    return users
```

#### POST Endpoint with Custom Response Model
```python
from pydantic import BaseModel, Field

class UserResponse(BaseModel):
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="User name")
    email: str = Field(..., description="User email")

@click.command()
@api_endpoint("/users", "POST", UserResponse)
@click.option('--name', required=True, help='User name')
@click.option('--email', required=True, help='User email')
def create_user(name: str, email: str):
    """Create a new user."""
    user_id = 123  # In real app, this would be generated
    return {"id": user_id, "name": name, "email": email}
```

#### Complex Parameters
```python
@click.command()
@api_endpoint("/calculate", "POST", create_success_response_model(dict))
@click.option('--a', required=True, type=int, help='First number')
@click.option('--b', required=True, type=int, help='Second number')
@click.option('--operation', default='add', 
              type=click.Choice(['add', 'subtract', 'multiply', 'divide']), 
              help='Operation to perform')
def calculate(a: int, b: int, operation: str):
    """Calculate with two numbers."""
    if operation == 'add':
        result = a + b
    elif operation == 'subtract':
        result = a - b
    elif operation == 'multiply':
        result = a * b
    elif operation == 'divide':
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
    
    return {
        "a": a,
        "b": b,
        "operation": operation,
        "result": result
    }
```

## Automatic Integration

The API decorator is automatically integrated into the MCLI command discovery system. When you run MCLI with the API server enabled, all commands are automatically registered as API endpoints.

### Endpoint Naming Convention

Endpoints are automatically named based on the module and command structure:

- Module: `mcli.app.model.model`
- Command: `generate`
- Endpoint: `/mcli/app/model/model/generate`

### Example API Endpoints

Based on the existing MCLI commands, you'll get endpoints like:

```
GET  /health                           # Health check
GET  /                                # Root endpoint with service info
POST /mcli/app/model/model/generate   # Video generation
POST /mcli/app/model/model/config     # Configuration management
GET  /mcli/app/model/model/list-models # List available models
GET  /mcli/app/model/model/check-comfyui # Check ComfyUI status
```

## Testing API Endpoints

### Using curl

```bash
# First, find your API server URL from the logs
# Example: http://0.0.0.0:8473

# Test hello endpoint
curl -X GET 'http://0.0.0.0:8473/test/hello?name=API'

# Test calculate endpoint
curl -X POST 'http://0.0.0.0:8473/test/calculate' \
  -H 'Content-Type: application/json' \
  -d '{"a": 10, "b": 5, "operation": "multiply"}'

# Test echo endpoint
curl -X POST 'http://0.0.0.0:8473/test/echo' \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hello from API!"}'
```

### Using Python requests

```python
import requests

# Replace with your actual port from the logs
api_url = "http://0.0.0.0:8473"

# Test GET endpoint
response = requests.get(f'{api_url}/test/hello', 
                       params={'name': 'API'})
print(response.json())

# Test POST endpoint
response = requests.post(f'{api_url}/test/calculate',
                        json={'a': 10, 'b': 5, 'operation': 'multiply'})
print(response.json())
```

## Response Format

All API endpoints return a standardized response format:

### Success Response
```json
{
  "success": true,
  "result": "actual result data",
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "message": "Operation failed"
}
```

## Configuration Examples

### Enable API with Random Port
```toml
[api]
enabled = true
use_random_port = true
```

### Enable API with Fixed Port
```toml
[api]
enabled = true
port = 8000
use_random_port = false
```

### Enable API with Debug Mode
```toml
[api]
enabled = true
debug = true
use_random_port = true
```

### Disable API Server
```toml
[api]
enabled = false
```

## Advanced Features

### Custom Response Models

You can create custom Pydantic models for more structured responses:

```python
from pydantic import BaseModel, Field
from typing import List

class User(BaseModel):
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="User name")
    email: str = Field(..., description="User email")

class UserListResponse(BaseModel):
    users: List[User] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")

@click.command()
@api_endpoint("/users", "GET", UserListResponse)
def list_users():
    """List all users with structured response."""
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"}
    ]
    return {"users": users, "total": len(users)}
```

### Error Handling

The decorator automatically handles exceptions and returns appropriate error responses:

```python
@click.command()
@api_endpoint("/divide", "POST", create_success_response_model(float))
@click.option('--a', required=True, type=float, help='First number')
@click.option('--b', required=True, type=float, help='Second number')
def divide(a: float, b: float):
    """Divide two numbers with error handling."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

### API Documentation

The API server automatically generates OpenAPI documentation at:

- Swagger UI: `http://your-port/docs`
- ReDoc: `http://your-port/redoc`

## Integration with Existing Commands

The API decorator is automatically applied to all existing MCLI commands. For example, the video generation commands in `src/mcli/app/model/model.py` are now available as API endpoints:

```bash
# CLI usage
mcli app model model generate --input video.mp4 --output output.mp4 --prompt "A beautiful landscape"

# API usage (replace PORT with your actual port)
curl -X POST 'http://0.0.0.0:PORT/mcli/app/model/model/generate' \
  -H 'Content-Type: application/json' \
  -d '{
    "input": "video.mp4",
    "output": "output.mp4", 
    "prompt": "A beautiful landscape",
    "fps": 8,
    "strength": 0.75
  }'
```

## Troubleshooting

### Common Issues

1. **API server not starting**: Check that API is enabled in config or environment
2. **Port conflicts**: Random ports should prevent this, but you can set a specific port
3. **Import errors**: Ensure all dependencies are installed (`fastapi`, `uvicorn`, `pydantic`)

### Debug Mode

Enable debug logging:

```bash
export MCLI_API_DEBUG=true
python -m mcli
```

Or in config:
```toml
[api]
enabled = true
debug = true
```

### Check API Status

```bash
# Replace PORT with your actual port
curl http://0.0.0.0:PORT/health
```

### Find Your Port

The port is logged when the server starts:
```
✅ API server started at http://0.0.0.0:8473
```

You can also check the root endpoint:
```bash
curl http://0.0.0.0:PORT/
```

## Example Test Script

Run the included test script to see the API decorator in action:

```bash
python test_api_demo.py
```

This will start a test server with example endpoints and show you how to test them with curl commands. 