# Transparent Click Superset Guide

This guide explains how MCLI is a **transparent superset of Click** that provides all Click functionality plus built-in API endpoints and background processing capabilities.

## What is a Transparent Superset?

MCLI is designed to be a **drop-in replacement** for Click that:

- ✅ **Preserves all Click functionality** - Every Click feature works exactly as expected
- ✅ **Adds optional capabilities** - API endpoints and background processing when needed
- ✅ **Maintains familiar syntax** - Same decorators, same parameters, same behavior
- ✅ **Provides backward compatibility** - Existing Click code works without changes
- ✅ **Offers gradual enhancement** - Add API/background features incrementally

## Core Philosophy

**"Everything that works in Click works in MCLI, plus more."**

### Standard Click Usage (Works Exactly as Before)

```python
import mcli  # Instead of import click

@mcli.group()
def mycli():
    """My CLI - works exactly as in Click"""
    pass

@mycli.command()
@click.option('--name', default='World', help='Name to greet')
def greet(name: str):
    """Standard Click command - no changes needed"""
    message = f"Hello, {name}!"
    click.echo(message)
    return message
```

### Enhanced Usage (When You Want More)

```python
@mycli.command(api_endpoint="/greet", api_method="POST")
@click.option('--name', default='World', help='Name to greet')
def greet_api(name: str):
    """Same Click command, now also an API endpoint"""
    message = f"Hello, {name}!"
    click.echo(message)  # Still works as CLI
    return {"message": message}  # Also works as API
```

## Decorator Reference

### 1. @mcli.command - Enhanced Click Command

```python
@mcli.command(
    # All standard Click parameters (work exactly as in Click)
    name="my-command",
    help="My command help",
    short_help="Short help",
    no_args_is_help=True,
    hidden=False,
    deprecated=False,
    
    # MCLI extensions (optional)
    api_endpoint="/my-endpoint",      # Enable API endpoint
    api_method="POST",                # HTTP method
    api_description="My API endpoint", # API documentation
    api_tags=["my-tag"],             # OpenAPI tags
    background=True,                  # Enable background processing
    background_timeout=60             # Background timeout
)
def my_command():
    return {"result": "success"}
```

**All Click parameters work exactly as expected:**
- `name`, `help`, `epilog`, `short_help`
- `options_metavar`, `add_help_option`, `no_args_is_help`
- `hidden`, `deprecated`, `cls`
- All other Click parameters

### 2. @mcli.group - Enhanced Click Group

```python
@mcli.group(
    # All standard Click parameters
    name="mygroup",
    help="My group help",
    
    # MCLI extensions (optional)
    api_base_path="/api/v1",         # Base path for child commands
    api_description="API group",      # API documentation
    api_tags=["my-group"]            # OpenAPI tags
)
def mygroup():
    pass
```

### 3. Convenience Decorators

```python
# For API endpoints
@mcli.api_command("/greet", "POST", description="Greet someone")
def greet(name: str):
    return {"message": f"Hello, {name}!"}

# For background processing
@mcli.background_command(timeout=300)
def process_file(file_path: str):
    return {"processed": file_path}
```

## Usage Patterns

### 1. Standard Click Commands (No Changes)

```python
import mcli
import click

@mcli.group()
def mycli():
    """Standard Click group"""
    pass

@mycli.command()
@click.option('--name', default='World')
@click.option('--verbose', '-v', is_flag=True)
def greet(name: str, verbose: bool):
    """Standard Click command - works exactly as before"""
    message = f"Hello, {name}!"
    if verbose:
        click.echo(f"Verbose: {message}")
    else:
        click.echo(message)
    return message
```

### 2. Click Commands with API Endpoints

```python
@mycli.command(api_endpoint="/greet", api_method="POST")
@click.option('--name', default='World')
def greet_api(name: str):
    """Same Click command, now also an API endpoint"""
    message = f"Hello, {name}!"
    click.echo(message)  # CLI output
    return {"message": message}  # API response
```

### 3. Click Commands with Background Processing

```python
@mycli.command(background=True, background_timeout=60)
@click.option('--file', type=click.Path(exists=True), required=True)
def process_file(file: str):
    """Click command with background processing"""
    file_path = Path(file)
    
    # Simulate processing
    time.sleep(2)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "processed": True
    }
    
    click.echo(f"Processed: {result}")
    return result
```

### 4. Click Commands with Both API and Background

```python
@mycli.command(
    api_endpoint="/process-file",
    api_method="POST",
    background=True,
    background_timeout=300
)
@click.option('--file', type=click.Path(exists=True), required=True)
def process_file_full(file: str):
    """Click command with both API endpoint and background processing"""
    file_path = Path(file)
    
    # Simulate processing
    time.sleep(2)
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "processed": True,
        "processed_at": time.time()
    }
    
    click.echo(f"Processed: {result}")
    return result
```

### 5. All Click Features Still Work

```python
@mycli.command(
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
    """Complex Click command - all features work exactly as in Click"""
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
```

## Migration from Click

### Before (Pure Click)

```python
import click

@click.group()
def mycli():
    pass

@mycli.command()
@click.option('--name', default='World')
def greet(name: str):
    message = f"Hello, {name}!"
    click.echo(message)
    return message

if __name__ == "__main__":
    mycli()
```

### After (MCLI - Drop-in Replacement)

```python
import mcli  # Only change: import mcli instead of click
import click

@mcli.group()  # Only change: @mcli.group instead of @click.group
def mycli():
    pass

@mycli.command()  # Only change: @mycli.command instead of @click.command
@click.option('--name', default='World')
def greet(name: str):
    message = f"Hello, {name}!"
    click.echo(message)
    return message

if __name__ == "__main__":
    mycli()
```

**Result:** Your CLI works exactly the same, but now you can optionally add API endpoints and background processing!

## Gradual Enhancement

### Step 1: Drop-in Replacement
```python
# Change this:
import click
@click.command()

# To this:
import mcli
@mcli.command()
```

### Step 2: Add API Endpoints (Optional)
```python
@mcli.command(api_endpoint="/greet", api_method="POST")
def greet(name: str):
    return {"message": f"Hello, {name}!"}
```

### Step 3: Add Background Processing (Optional)
```python
@mcli.command(background=True, background_timeout=60)
def process_file(file_path: str):
    return {"processed": file_path}
```

### Step 4: Combine Both (Optional)
```python
@mcli.command(
    api_endpoint="/process",
    api_method="POST",
    background=True,
    background_timeout=300
)
def process_file(file_path: str):
    return {"processed": file_path}
```

## Benefits of Transparent Superset

### 1. Zero Learning Curve
- All Click knowledge applies directly
- Same decorators, same parameters, same behavior
- No need to learn new concepts

### 2. Backward Compatibility
- Existing Click code works without changes
- Gradual migration possible
- No breaking changes

### 3. Optional Enhancement
- Add API endpoints when needed
- Add background processing when needed
- Keep it simple when you don't need extra features

### 4. Familiar Development Experience
- Same debugging experience
- Same testing approach
- Same deployment process

### 5. Future-Proof
- Click updates automatically benefit MCLI
- New Click features work immediately
- No vendor lock-in

## Complete Example

```python
#!/usr/bin/env python3
"""
Complete example showing transparent Click superset
"""

import mcli  # Instead of import click
import click
import time
from pathlib import Path

@mcli.group()
def myapp():
    """My application - works exactly like Click"""
    pass

# Standard Click command (no changes needed)
@myapp.command()
@click.option('--name', default='World')
def greet(name: str):
    """Standard Click command"""
    message = f"Hello, {name}!"
    click.echo(message)
    return message

# Click command with API endpoint
@myapp.command(api_endpoint="/greet", api_method="POST")
@click.option('--name', default='World')
def greet_api(name: str):
    """Same command, now also an API endpoint"""
    message = f"Hello, {name}!"
    click.echo(message)  # CLI output
    return {"message": message}  # API response

# Click command with background processing
@myapp.command(background=True, background_timeout=60)
@click.option('--file', type=click.Path(exists=True), required=True)
def process_file(file: str):
    """Click command with background processing"""
    file_path = Path(file)
    time.sleep(2)  # Simulate processing
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "processed": True
    }
    
    click.echo(f"Processed: {result}")
    return result

# Click command with both API and background
@myapp.command(
    api_endpoint="/process-file",
    api_method="POST",
    background=True,
    background_timeout=300
)
@click.option('--file', type=click.Path(exists=True), required=True)
def process_file_full(file: str):
    """Click command with both API endpoint and background processing"""
    file_path = Path(file)
    time.sleep(2)  # Simulate processing
    
    result = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "processed": True,
        "processed_at": time.time()
    }
    
    click.echo(f"Processed: {result}")
    return result

if __name__ == "__main__":
    myapp()
```

## Usage

### CLI Usage (Works Exactly as Click)
```bash
# Standard Click commands
python myapp.py greet --name Alice
python myapp.py process-file --file data.txt

# Commands with API endpoints (still work as CLI)
python myapp.py greet-api --name Bob
python myapp.py process-file-full --file data.txt
```

### API Usage (When Server is Running)
```bash
# Start API server
python myapp.py --start-server

# Use API endpoints
curl -X POST http://localhost:8000/greet \
     -H "Content-Type: application/json" \
     -d '{"name": "Bob"}'

curl -X POST http://localhost:8000/process-file \
     -H "Content-Type: application/json" \
     -d '{"file": "data.txt"}'
```

## Summary

MCLI is a **transparent superset of Click** that:

1. **Preserves all Click functionality** - Every feature works exactly as expected
2. **Adds optional capabilities** - API endpoints and background processing when needed
3. **Maintains familiar syntax** - Same decorators, same parameters, same behavior
4. **Provides backward compatibility** - Existing Click code works without changes
5. **Offers gradual enhancement** - Add features incrementally as needed

**The result:** You get all the power and familiarity of Click, plus the additional capabilities of API endpoints and background processing, with zero learning curve and complete backward compatibility. 