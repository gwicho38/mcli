#!/usr/bin/env python3
"""
Example: Complete Click Subsume with MCLI

This example demonstrates how MCLI completely subsumes Click functionality.
Users only need to import mcli and get everything - Click functionality,
API endpoints, and background processing - all in one unified interface.
"""

import time
from typing import Optional, Dict, Any
from pathlib import Path

# Import MCLI - that's it! No need to import click separately
import mcli

# =============================================================================
# Example 1: Standard Click Commands (Work Exactly as Before)
# =============================================================================

@mcli.group()
def standardcli():
    """Standard Click group - works exactly as before"""
    pass

@standardcli.command()
@mcli.option('--name', default='World', help='Name to greet')
def greet(name: str):
    """Standard Click command - no API, no background processing"""
    message = f"Hello, {name}!"
    mcli.echo(message)
    return message

@standardcli.command()
@mcli.option('--file', type=mcli.Path(exists=True), required=True)
def show_file_info(file: str):
    """Standard Click command - works exactly as in Click"""
    file_path = Path(file)
    info = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines())
    }
    mcli.echo(f"File info: {info}")
    return info

# =============================================================================
# Example 2: Click Commands with API Endpoints
# =============================================================================

@mcli.group()
def apicli():
    """Click group with API endpoints"""
    pass

@apicli.command(api_endpoint="/greet", api_method="POST")
@mcli.option('--name', default='World', help='Name to greet')
def greet_api(name: str):
    """Click command with API endpoint - works as CLI and API"""
    message = f"Hello, {name}!"
    mcli.echo(message)  # Still works as CLI
    return {"message": message, "name": name}  # Also works as API

@apicli.command(api_endpoint="/file-info", api_method="POST")
@mcli.option('--file', type=mcli.Path(exists=True), required=True)
def file_info_api(file: str):
    """Click command with API endpoint"""
    file_path = Path(file)
    info = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "lines": len(file_path.read_text().splitlines())
    }
    mcli.echo(f"File info: {info}")  # CLI output
    return info  # API response

# =============================================================================
# Example 3: Click Commands with Background Processing
# =============================================================================

@mcli.group()
def backgroundcli():
    """Click group with background processing"""
    pass

@backgroundcli.command(background=True, background_timeout=60)
@mcli.option('--file', type=mcli.Path(exists=True), required=True)
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
    
    mcli.echo(f"Processed: {result}")
    return result

@backgroundcli.command(background=True, background_timeout=300)
@mcli.option('--task-name', required=True)
@mcli.option('--duration', default=5, type=int)
def long_task_background(task_name: str, duration: int):
    """Click command with background processing for long tasks"""
    mcli.echo(f"Starting task: {task_name}")
    
    # Simulate long-running work
    for i in range(duration):
        time.sleep(1)
        if i % 60 == 0:  # Log every minute
            mcli.echo(f"Task {task_name}: {i//60} minutes completed")
    
    result = {
        "task_name": task_name,
        "duration": duration,
        "status": "completed",
        "processed_in": "background" if mcli.is_background_available() else "local"
    }
    
    mcli.echo(f"Task completed: {result}")
    return result

# =============================================================================
# Example 4: Click Commands with Both API and Background
# =============================================================================

@mcli.group()
def fullcli():
    """Click group with both API endpoints and background processing"""
    pass

@fullcli.command(
    api_endpoint="/process-file",
    api_method="POST",
    background=True,
    background_timeout=60
)
@mcli.option('--file', type=mcli.Path(exists=True), required=True)
@mcli.option('--output', type=mcli.Path())
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
    
    mcli.echo(f"Processed: {result}")
    return result

# =============================================================================
# Example 5: Convenience Decorators
# =============================================================================

@mcli.group()
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
@mcli.option('--task-name', required=True)
def background_task(task_name: str):
    """Background task using convenience decorator"""
    mcli.echo(f"Starting background task: {task_name}")
    time.sleep(5)
    return {"task": task_name, "status": "completed"}

# =============================================================================
# Example 6: All Click Features Still Work
# =============================================================================

@mcli.group()
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
@mcli.option('--verbose', '-v', is_flag=True, help='Verbose output')
@mcli.option('--count', '-c', default=1, help='Number of times')
@mcli.argument('message', nargs=-1)
def complex_command(verbose: bool, count: int, message: tuple):
    """Complex Click command with all features - works exactly as in Click"""
    if verbose:
        mcli.echo("Verbose mode enabled")
    
    msg = " ".join(message) if message else "Hello"
    
    for i in range(count):
        mcli.echo(f"{i+1}: {msg}")
    
    result = {
        "message": msg,
        "count": count,
        "verbose": verbose
    }
    
    return result

# =============================================================================
# Example 7: Advanced Click Features
# =============================================================================

@mcli.group()
def advancedcli():
    """Demonstrating advanced Click features"""
    pass

@advancedcli.command()
@mcli.option('--color', default='blue', help='Text color')
@mcli.option('--style', default='bold', help='Text style')
def styled_output(color: str, style: str):
    """Demonstrating Click styling features"""
    text = "This is styled text!"
    styled_text = mcli.style(text, fg=color, bold=(style == 'bold'))
    mcli.echo(styled_text)
    return {"text": text, "color": color, "style": style}

@advancedcli.command()
@mcli.option('--confirm', is_flag=True, help='Require confirmation')
def interactive_command(confirm: bool):
    """Demonstrating Click interactive features"""
    if confirm:
        if mcli.confirm("Do you want to proceed?"):
            mcli.echo("Proceeding...")
            return {"status": "proceeded"}
        else:
            mcli.echo("Cancelled.")
            return {"status": "cancelled"}
    else:
        name = mcli.prompt("Enter your name")
        age = mcli.prompt("Enter your age", type=int)
        return {"name": name, "age": age}

@advancedcli.command()
@mcli.option('--items', default=10, help='Number of items')
def progress_demo(items: int):
    """Demonstrating Click progress bar"""
    with mcli.progressbar(length=items, label="Processing") as bar:
        for i in range(items):
            time.sleep(0.1)  # Simulate work
            bar.update(1)
    
    mcli.echo("Processing complete!")
    return {"processed_items": items}

# =============================================================================
# Main CLI with Server Management
# =============================================================================

@mcli.group()
@mcli.option('--start-server', is_flag=True, help='Start API server')
@mcli.option('--host', default='0.0.0.0', help='Server host')
@mcli.option('--port', type=int, help='Server port')
@mcli.option('--debug', is_flag=True, help='Enable debug mode')
def maincli(start_server: bool, host: str, port: Optional[int], debug: bool):
    """Main CLI demonstrating complete Click subsume"""
    if start_server:
        server_url = mcli.start_server(host=host, port=port, debug=debug)
        if server_url:
            mcli.echo(f"API server running at: {server_url}")
            mcli.echo("Available endpoints:")
            mcli.echo("  POST /greet - Greet someone")
            mcli.echo("  POST /file-info - Get file info")
            mcli.echo("  POST /process-file - Process files")
            mcli.echo("  GET  /health - Health check")
            mcli.echo("  GET  /status - System status")
            mcli.echo("")
            mcli.echo("Background processing:")
            if mcli.is_background_available():
                mcli.echo("  ✅ Background service is available")
            else:
                mcli.echo("  ⚠️  Background service not available (will use local execution)")

# Add all subcommands
maincli.add_command(standardcli)
maincli.add_command(apicli)
maincli.add_command(backgroundcli)
maincli.add_command(fullcli)
maincli.add_command(conveniencecli)
maincli.add_command(clickfeatures)
maincli.add_command(advancedcli)

# =============================================================================
# Usage Examples
# =============================================================================

if __name__ == "__main__":
    # Example usage:
    #
    # 1. Standard Click commands (work exactly as before):
    #    python example_complete_click_subsume.py standardcli greet --name Alice
    #    python example_complete_click_subsume.py standardcli show-file-info --file data.txt
    #
    # 2. Click commands with API endpoints:
    #    python example_complete_click_subsume.py apicli greet-api --name Bob
    #    python example_complete_click_subsume.py apicli file-info-api --file data.txt
    #
    # 3. Click commands with background processing:
    #    python example_complete_click_subsume.py backgroundcli process-file-background --file data.txt
    #    python example_complete_click_subsume.py backgroundcli long-task-background --task-name "test" --duration 10
    #
    # 4. Click commands with both API and background:
    #    python example_complete_click_subsume.py fullcli process-file-full --file data.txt
    #
    # 5. Convenience decorators:
    #    python example_complete_click_subsume.py conveniencecli health
    #    python example_complete_click_subsume.py conveniencecli background-task --task-name "test"
    #
    # 6. All Click features:
    #    python example_complete_click_subsume.py clickfeatures complex-command --verbose --count 3 "Hello World"
    #
    # 7. Advanced Click features:
    #    python example_complete_click_subsume.py advancedcli styled-output --color red --style bold
    #    python example_complete_click_subsume.py advancedcli interactive-command --confirm
    #    python example_complete_click_subsume.py advancedcli progress-demo --items 20
    #
    # 8. Start with API server:
    #    python example_complete_click_subsume.py --start-server
    #
    # 9. Use API endpoints (when server is running):
    #    curl -X POST http://localhost:8000/greet \
    #         -H "Content-Type: application/json" \
    #         -d '{"name": "Bob"}'
    #
    #    curl -X POST http://localhost:8000/process-file \
    #         -H "Content-Type: application/json" \
    #         -d '{"file": "data.txt"}'
    
    maincli() 