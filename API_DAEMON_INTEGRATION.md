# MCLI API Daemon Integration

## Overview

The MCLI API Daemon provides a persistent service for executing MCLI commands, similar to Docker daemon or Emacs server mode. This integration allows for:

- **Persistent Command Execution**: Commands run in a persistent daemon process
- **Resource Management**: Better resource utilization and caching
- **Remote Execution**: Execute commands via HTTP API
- **Automatic Routing**: Decorators for automatic daemon routing
- **Command History**: Track and monitor command execution

## Architecture

```
┌─────────────────┐    HTTP API    ┌─────────────────┐
│   MCLI Client   │ ──────────────► │  API Daemon     │
│                 │                 │                 │
│ • CLI Commands  │                 │ • FastAPI Server│
│ • Decorators    │ ◄────────────── │ • Command Exec  │
│ • Auto-routing  │                 │ • History DB    │
└─────────────────┘                 └─────────────────┘
```

## Quick Start

### 1. Start the API Daemon

```bash
# Start the daemon service
python -m mcli workflow api-daemon start

# Check daemon status
python -m mcli workflow api-daemon status

# List available commands
python -m mcli workflow api-daemon commands

# Stop the daemon
python -m mcli workflow api-daemon stop
```

### 2. Enable Daemon Routing

```bash
# Enable automatic daemon routing
export MCLI_DAEMON_ROUTING=true

# Or enable in config.toml
[api_daemon]
enabled = true
```

### 3. Use Daemon Decorators

```python
from mcli.lib.api.daemon_decorator import daemon_command

@daemon_command(command_name="my_function", timeout=30)
def my_function(name: str, verbose: bool = False):
    """Function that can be executed via daemon"""
    result = f"Hello {name}!"
    if verbose:
        result += " (verbose mode)"
    return result

# Execute via daemon (if enabled) or locally (fallback)
result = my_function("World", verbose=True)
```

## Configuration

### Environment Variables

```bash
# Enable daemon routing
export MCLI_DAEMON_ROUTING=true

# Daemon configuration
export MCLI_API_DAEMON_ENABLED=true
export MCLI_API_DAEMON_HOST=0.0.0.0
export MCLI_API_DAEMON_PORT=8000
export MCLI_API_DAEMON_DEBUG=false
```

### config.toml Configuration

```toml
[api_daemon]
enabled = false
host = "0.0.0.0"
port = null  # null means use random port
use_random_port = true
debug = false
auto_start = false
command_timeout = 300  # 5 minutes
max_concurrent_commands = 10
enable_command_caching = true
enable_command_history = true
```

## API Endpoints

The daemon provides the following HTTP endpoints:

### Health & Status
- `GET /health` - Health check
- `GET /status` - Daemon status
- `GET /` - Root endpoint with service info

### Commands
- `GET /commands` - List available commands
- `POST /execute` - Execute a command

### Daemon Control
- `POST /daemon/start` - Start daemon via HTTP
- `POST /daemon/stop` - Stop daemon via HTTP

## Client Library

### Basic Usage

```python
from mcli.lib.api.daemon_client import get_daemon_client

# Get daemon client
client = get_daemon_client()

# Check if daemon is running
if client.is_running():
    # Execute command
    result = client.execute_command(
        command_name="hello",
        args=["--verbose"]
    )
    print(f"Result: {result}")
```

### Advanced Usage

```python
from mcli.lib.api.daemon_client import APIDaemonClient, DaemonClientConfig

# Custom configuration
config = DaemonClientConfig(
    host="localhost",
    port=8000,
    timeout=30,
    retry_attempts=3
)

client = APIDaemonClient(config)

# Health check
health = client.health_check()

# Get status
status = client.status()

# List commands
commands = client.list_commands()

# Wait for daemon
if client.wait_for_daemon(timeout=30):
    print("Daemon is ready")
```

## Decorators

### @daemon_command

Automatically route Click commands to the daemon when enabled.

```python
from mcli.lib.api.daemon_decorator import daemon_command

@daemon_command(
    command_name="my_command",
    auto_route=True,
    fallback_to_local=True,
    timeout=30
)
def my_command(name: str, verbose: bool = False):
    """My command that can run via daemon"""
    return f"Hello {name}!"
```

### @daemon_group

Route Click groups to the daemon.

```python
from mcli.lib.api.daemon_decorator import daemon_group

@daemon_group(group_name="my_group")
def my_group():
    """My group that can run via daemon"""
    pass
```

## Integration Examples

### 1. Model Service Integration

```python
from mcli.lib.api.daemon_decorator import daemon_command

@daemon_command(command_name="model_generate")
def generate_text(prompt: str, model: str = "gpt-3.5-turbo"):
    """Generate text using model service via daemon"""
    # This will execute via daemon if enabled
    return f"Generated text for: {prompt}"
```

### 2. File Processing Integration

```python
from mcli.lib.api.daemon_decorator import daemon_command

@daemon_command(command_name="process_file")
def process_file(file_path: str, output_format: str = "json"):
    """Process file via daemon"""
    # File processing logic
    return {"processed": file_path, "format": output_format}
```

### 3. Workflow Integration

```python
from mcli.lib.api.daemon_decorator import daemon_command

@daemon_command(command_name="workflow_run")
def run_workflow(workflow_name: str, parameters: dict = None):
    """Run workflow via daemon"""
    # Workflow execution logic
    return {"workflow": workflow_name, "status": "completed"}
```

## Monitoring & Debugging

### Check Daemon Status

```bash
# CLI status
python -m mcli workflow api-daemon status

# HTTP status
curl http://localhost:8000/status

# Health check
curl http://localhost:8000/health
```

### View Command History

```python
from mcli.lib.api.daemon_client import get_daemon_client

client = get_daemon_client()
status = client.status()
print(f"Active commands: {status['active_commands']}")
print(f"Command history: {status['command_history_count']}")
```

### Debug Mode

```bash
# Enable debug mode
export MCLI_API_DAEMON_DEBUG=true

# Start daemon with debug
python -m mcli workflow api-daemon start --debug
```

## Benefits

### 1. Persistent Execution
- Commands run in a persistent daemon process
- No startup overhead for repeated commands
- Better resource utilization

### 2. Resource Management
- Centralized command execution
- Memory and CPU optimization
- Connection pooling

### 3. Remote Execution
- Execute commands via HTTP API
- Network-accessible command execution
- Load balancing capabilities

### 4. Monitoring & History
- Track command execution
- Performance monitoring
- Error logging and debugging

### 5. Auto-routing
- Automatic daemon routing with decorators
- Fallback to local execution
- Transparent integration

## Use Cases

### 1. Development Environment
```bash
# Start daemon for development
python -m mcli workflow api-daemon start --debug

# Enable auto-routing
export MCLI_DAEMON_ROUTING=true

# Commands automatically route to daemon
python -m mcli workflow model generate --prompt "Hello world"
```

### 2. Production Deployment
```bash
# Start daemon in production
python -m mcli workflow api-daemon start --host 0.0.0.0 --port 8000

# Monitor daemon
python -m mcli workflow api-daemon status
```

### 3. CI/CD Integration
```python
# In CI/CD pipeline
from mcli.lib.api.daemon_client import get_daemon_client

client = get_daemon_client()
result = client.execute_command("test_workflow", args=["--verbose"])
assert result["success"]
```

## Troubleshooting

### Common Issues

1. **Daemon not starting**
   ```bash
   # Check if port is available
   lsof -i :8000
   
   # Start with different port
   python -m mcli workflow api-daemon start --port 8001
   ```

2. **Commands not routing to daemon**
   ```bash
   # Check if routing is enabled
   echo $MCLI_DAEMON_ROUTING
   
   # Enable routing
   export MCLI_DAEMON_ROUTING=true
   ```

3. **Connection errors**
   ```python
   # Check daemon status
   from mcli.lib.api.daemon_client import get_daemon_client
   client = get_daemon_client()
   print(client.is_running())
   ```

### Debug Commands

```bash
# Check daemon logs
python -m mcli workflow api-daemon start --debug

# Test HTTP endpoints
curl http://localhost:8000/health
curl http://localhost:8000/status

# Check configuration
python -c "from mcli.lib.api.daemon_decorator import _is_daemon_routing_enabled; print(_is_daemon_routing_enabled())"
```

## Future Enhancements

1. **Authentication & Security**
   - API key authentication
   - SSL/TLS encryption
   - Role-based access control

2. **Scalability**
   - Multiple daemon instances
   - Load balancing
   - Cluster management

3. **Advanced Features**
   - Command scheduling
   - Batch execution
   - Real-time monitoring
   - WebSocket support

4. **Integration**
   - Docker containerization
   - Kubernetes deployment
   - Cloud service integration

## Conclusion

The MCLI API Daemon provides a powerful foundation for persistent command execution and resource management. With automatic routing, comprehensive monitoring, and flexible configuration, it enables efficient command execution in both development and production environments.

The integration follows the same patterns as Docker daemon and Emacs server mode, providing familiar and reliable command execution patterns for users and developers. 