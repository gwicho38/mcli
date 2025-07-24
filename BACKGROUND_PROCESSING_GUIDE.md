# Background Processing Guide

This guide explains the background processing functionality in MCLI and how to use it effectively.

## What is Background Processing?

Background processing allows your CLI commands to run in a separate service that provides:

- **Non-blocking execution**: Commands don't block the main process
- **Concurrent operations**: Multiple commands can run simultaneously  
- **Better resource management**: Optimized memory and CPU usage
- **Long-running tasks**: Support for operations that take minutes or hours
- **Automatic fallback**: If background service is unavailable, runs locally

## When to Use Background Processing

### ✅ Use Background Processing For:

- **File processing operations** (large files, batch processing)
- **Database operations** (bulk inserts, data migrations)
- **Machine learning tasks** (model training, inference)
- **Data analysis** (complex calculations, report generation)
- **API calls** (external service integration)
- **Any operation that might take more than a few seconds**

### ❌ Don't Use Background Processing For:

- **Simple calculations** (quick math, string operations)
- **Quick data lookups** (cache hits, simple queries)
- **Health checks** (status queries, availability checks)
- **Configuration operations** (reading settings, validation)
- **Immediate responses** (where blocking is acceptable)

## How Background Processing Works

### 1. Service Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Your CLI      │    │  Background      │    │   Background    │
│   Application   │───▶│  Service         │───▶│   Worker        │
│                 │    │  (API Daemon)    │    │   Process       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 2. Execution Flow

1. **Command Submission**: Your CLI command is submitted to the background service
2. **Queue Management**: The service queues the command for execution
3. **Worker Processing**: A background worker picks up and executes the command
4. **Result Return**: Results are returned to your CLI application
5. **Fallback**: If background service is unavailable, command runs locally

### 3. Benefits

- **Scalability**: Multiple workers can handle concurrent requests
- **Reliability**: Automatic retry and fallback mechanisms
- **Performance**: Optimized resource allocation and management
- **Monitoring**: Built-in logging and status tracking

## Usage Examples

### 1. Basic Background Processing

```python
import click
import mcli

@click.command()
@click.option('--file', type=click.Path(exists=True), required=True)
@mcli.background(auto_route=True, fallback_to_local=True)
def process_large_file(file: str):
    """Process a large file in background"""
    file_path = Path(file)
    
    # This will run in background if available
    # Falls back to local execution if not
    result = process_file(file_path)
    
    return result
```

### 2. API Endpoint with Background Processing

```python
@click.command()
@click.option('--input', type=click.Path(exists=True), required=True)
@mcli.api(
    "/process-file",
    "POST",
    description="Process files with background processing",
    enable_background=True,
    background_timeout=60
)
def process_file(input: str):
    """Process a file with both API endpoint and background processing"""
    file_path = Path(input)
    
    # Simulate heavy processing
    time.sleep(5)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "processed": True,
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    return result
```

### 3. Long-Running Tasks

```python
@click.command()
@click.option('--task-name', required=True)
@click.option('--duration', default=300, type=int)
@mcli.background(timeout=600)  # 10 minute timeout
def long_running_task(task_name: str, duration: int):
    """Long running task with background processing"""
    print(f"Starting task: {task_name}")
    
    # Simulate long-running work
    for i in range(duration):
        time.sleep(1)
        if i % 60 == 0:  # Log every minute
            print(f"Task {task_name}: {i//60} minutes completed")
    
    result = {
        "task_name": task_name,
        "duration": duration,
        "status": "completed",
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    return result
```

### 4. Database Operations

```python
@click.command()
@click.option('--table', required=True)
@click.option('--data', help='JSON data')
@mcli.api(
    "/db/bulk-insert",
    "POST",
    description="Bulk insert data into database",
    tags=["database"],
    enable_background=True,
    background_timeout=300
)
def bulk_insert_data(table: str, data: str):
    """Bulk insert data with background processing"""
    import json
    
    parsed_data = json.loads(data)
    
    # Simulate bulk database operation
    time.sleep(10)  # Simulate processing time
    
    result = {
        "table": table,
        "records_inserted": len(parsed_data),
        "status": "success",
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    return result
```

### 5. Machine Learning Tasks

```python
@click.command()
@click.option('--model', required=True)
@click.option('--data-path', required=True)
@mcli.api(
    "/ml/train",
    "POST",
    description="Train machine learning model",
    tags=["machine-learning"],
    enable_background=True,
    background_timeout=3600  # 1 hour timeout
)
def train_model(model: str, data_path: str):
    """Train ML model with background processing"""
    print(f"Starting training for model: {model}")
    
    # Simulate model training
    for epoch in range(10):
        time.sleep(30)  # Simulate training time
        print(f"Epoch {epoch+1}/10 completed")
    
    result = {
        "model": model,
        "data_path": data_path,
        "epochs": 10,
        "status": "training_completed",
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    return result
```

## Configuration Options

### 1. Background Processing Parameters

```python
@mcli.background(
    command_name="custom_name",      # Custom command name
    auto_route=True,                 # Auto-route to background
    fallback_to_local=True,          # Fallback to local execution
    timeout=300                      # 5 minute timeout
)
```

### 2. API with Background Processing

```python
@mcli.api(
    "/endpoint",
    "POST",
    description="My endpoint",
    enable_background=True,          # Enable background processing
    background_timeout=60            # 1 minute timeout
)
```

### 3. Environment Variables

```bash
# Enable background processing
export MCLI_BACKGROUND_ENABLED=true

# Configure background service
export MCLI_BACKGROUND_HOST=localhost
export MCLI_BACKGROUND_PORT=8001

# Set timeouts
export MCLI_BACKGROUND_TIMEOUT=300
```

## Monitoring and Status

### 1. Check Background Service Status

```python
import mcli

# Check if background service is available
if mcli.is_background_available():
    print("✅ Background service is available")
else:
    print("⚠️  Background service not available (will use local execution)")
```

### 2. Get System Status

```python
@click.command()
@mcli.api("/status", "GET", description="System status")
def status():
    """Get system status including background service"""
    return mcli.status_check()
```

### 3. Health Check

```python
@click.command()
@mcli.api("/health", "GET", description="Health check")
def health():
    """Health check endpoint"""
    return mcli.health_check()
```

## Best Practices

### 1. Choose the Right Decorator

```python
# For simple API endpoints (no background processing)
@mcli.api("/health", "GET", enable_background=False)

# For operations that benefit from background processing
@mcli.api("/process", "POST", enable_background=True)

# For CLI-only commands with background processing
@mcli.background(auto_route=True, fallback_to_local=True)
```

### 2. Set Appropriate Timeouts

```python
# Quick operations
@mcli.background(timeout=30)

# Medium operations
@mcli.background(timeout=300)  # 5 minutes

# Long operations
@mcli.background(timeout=3600)  # 1 hour
```

### 3. Handle Fallbacks Gracefully

```python
@click.command()
@mcli.background(fallback_to_local=True)
def my_command():
    """Command that works with or without background processing"""
    if mcli.is_background_available():
        print("Running in background for better performance")
    else:
        print("Running locally (background service not available)")
    
    # Your command logic here
    return {"result": "success"}
```

### 4. Provide Progress Feedback

```python
@click.command()
@mcli.background(timeout=600)
def long_task():
    """Long task with progress feedback"""
    total_steps = 100
    
    for step in range(total_steps):
        # Do work
        time.sleep(1)
        
        # Provide progress feedback
        if step % 10 == 0:
            print(f"Progress: {step}/{total_steps} ({step/total_steps*100:.1f}%)")
    
    return {"status": "completed", "steps": total_steps}
```

## Troubleshooting

### 1. Background Service Not Available

**Symptoms**: Commands run locally instead of in background

**Solutions**:
- Check if background service is running
- Verify network connectivity
- Check configuration settings
- Review service logs

### 2. Timeout Issues

**Symptoms**: Commands fail with timeout errors

**Solutions**:
- Increase timeout values
- Optimize command performance
- Break large tasks into smaller chunks
- Use progress feedback for long operations

### 3. Resource Issues

**Symptoms**: Poor performance or memory issues

**Solutions**:
- Monitor resource usage
- Optimize command efficiency
- Use appropriate timeouts
- Consider task queuing for very heavy operations

## Summary

Background processing in MCLI provides:

1. **Better Performance**: Non-blocking execution with optimized resource management
2. **Scalability**: Support for concurrent operations and long-running tasks
3. **Reliability**: Automatic fallback to local execution when needed
4. **Flexibility**: Easy configuration and monitoring options

Use `@mcli.background` for CLI-only commands and `@mcli.api` with `enable_background=True` for API endpoints that benefit from background processing. 