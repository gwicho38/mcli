#!/usr/bin/env python3
"""
Test script to demonstrate the API decorator integration.
This script shows how to use the API decorator with Click commands.
"""

import os
import sys
import click
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the API decorator
from mcli.lib.api.api import api_endpoint, start_api_server, create_success_response_model

# Set environment variable to enable API server
os.environ['MCLI_API_SERVER'] = 'true'
os.environ['MCLI_API_HOST'] = '0.0.0.0'
os.environ['MCLI_API_PORT'] = '8000'

@click.group(name="test")
def test_app():
    """Test application with API endpoints."""
    pass

@test_app.command()
@api_endpoint("/test/hello", "GET", create_success_response_model(str))
@click.option('--name', default='World', help='Name to greet')
def hello(name: str):
    """Simple hello command with API endpoint."""
    message = f"Hello, {name}!"
    click.echo(message)
    return message

@test_app.command()
@api_endpoint("/test/calculate", "POST", create_success_response_model(dict))
@click.option('--a', required=True, type=int, help='First number')
@click.option('--b', required=True, type=int, help='Second number')
@click.option('--operation', default='add', type=click.Choice(['add', 'subtract', 'multiply', 'divide']), help='Operation to perform')
def calculate(a: int, b: int, operation: str):
    """Calculate with two numbers."""
    result = None
    
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
    
    message = f"{a} {operation} {b} = {result}"
    click.echo(message)
    
    return {
        "a": a,
        "b": b,
        "operation": operation,
        "result": result,
        "message": message
    }

@test_app.command()
@api_endpoint("/test/echo", "POST", create_success_response_model(str))
@click.argument('message', required=True)
def echo(message: str):
    """Echo a message."""
    click.echo(f"Echo: {message}")
    return message

if __name__ == "__main__":
    print("🚀 Starting MCLI with API integration test")
    print("=" * 50)
    
    # Start the API server
    api_url = start_api_server(host='0.0.0.0', port=8000)
    print(f"✅ API server started at {api_url}")
    print(f"📋 Available endpoints:")
    print(f"   GET  {api_url}/test/hello")
    print(f"   POST {api_url}/test/calculate")
    print(f"   POST {api_url}/test/echo")
    print(f"   GET  {api_url}/health")
    print(f"   GET  {api_url}/")
    print()
    print("🧪 Testing CLI commands:")
    print("=" * 30)
    
    # Test CLI commands
    test_app(['hello', '--name', 'API'])
    test_app(['calculate', '--a', '10', '--b', '5', '--operation', 'multiply'])
    test_app(['echo', 'Hello from CLI!'])
    
    print()
    print("🌐 API endpoints are now available!")
    print("You can test them with curl:")
    print()
    print(f"# Test hello endpoint")
    print(f"curl -X GET '{api_url}/test/hello?name=API'")
    print()
    print(f"# Test calculate endpoint")
    print(f"curl -X POST '{api_url}/test/calculate' \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{{\"a\": 10, \"b\": 5, \"operation\": \"multiply\"}}'")
    print()
    print(f"# Test echo endpoint")
    print(f"curl -X POST '{api_url}/test/echo' \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{{\"message\": \"Hello from API!\"}}'")
    print()
    print("Press Ctrl+C to stop the server")
    
    try:
        # Keep the server running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n�� Server stopped") 