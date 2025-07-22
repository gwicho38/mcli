#!/usr/bin/env python3
"""
Demo script showing the API decorator in action.
This script demonstrates how Click commands automatically become API endpoints.
"""

import os
import sys
import click
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the API decorator
from mcli.lib.api.api import api_endpoint, start_api_server, create_success_response_model

# Enable API server via environment variable
os.environ['MCLI_API_SERVER'] = 'true'

@click.group(name="demo")
def demo_app():
    """Demo application with API endpoints."""
    pass

@demo_app.command()
@api_endpoint("/demo/hello", "GET", create_success_response_model(str))
@click.option('--name', default='World', help='Name to greet')
def hello(name: str):
    """Simple hello command with API endpoint."""
    message = f"Hello, {name}!"
    click.echo(message)
    return message

@demo_app.command()
@api_endpoint("/demo/calculate", "POST", create_success_response_model(dict))
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
    
    message = f"{a} {operation} {b} = {result}"
    click.echo(message)
    
    return {
        "a": a,
        "b": b,
        "operation": operation,
        "result": result,
        "message": message
    }

@demo_app.command()
@api_endpoint("/demo/echo", "POST", create_success_response_model(str))
@click.argument('message', required=True)
def echo(message: str):
    """Echo a message."""
    click.echo(f"Echo: {message}")
    return message

def main():
    """Main function to run the demo."""
    print("🚀 MCLI API Decorator Demo")
    print("=" * 40)
    
    # Start the API server (will use random port)
    api_url = start_api_server()
    
    if api_url:
        print(f"✅ API server started at {api_url}")
        
        print("\n📋 Available endpoints:")
        print(f"   GET  {api_url}/demo/hello")
        print(f"   POST {api_url}/demo/calculate")
        print(f"   POST {api_url}/demo/echo")
        print(f"   GET  {api_url}/health")
        print(f"   GET  {api_url}/")
        
        print("\n🧪 Testing CLI commands:")
        print("=" * 30)
        
        # Test CLI commands
        demo_app(['hello', '--name', 'API'])
        demo_app(['calculate', '--a', '10', '--b', '5', '--operation', 'multiply'])
        demo_app(['echo', 'Hello from CLI!'])
        
        print("\n🌐 API endpoints are now available!")
        print("You can test them with curl:")
        print()
        print(f"# Test hello endpoint")
        print(f"curl -X GET '{api_url}/demo/hello?name=API'")
        print()
        print(f"# Test calculate endpoint")
        print(f"curl -X POST '{api_url}/demo/calculate' \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d '{{\"a\": 10, \"b\": 5, \"operation\": \"multiply\"}}'")
        print()
        print(f"# Test echo endpoint")
        print(f"curl -X POST '{api_url}/demo/echo' \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d '{{\"message\": \"Hello from API!\"}}'")
        print()
        print("📖 API Documentation:")
        print(f"   Swagger UI: {api_url}/docs")
        print(f"   ReDoc: {api_url}/redoc")
        print()
        print("🔒 Security Note: Using random port for security")
        print("   - No port conflicts with other services")
        print("   - Harder to guess the API endpoint")
        print("   - Can run multiple instances simultaneously")
        print()
        print("Press Ctrl+C to stop the server")
        
        try:
            # Keep the server running
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")
    else:
        print("❌ Failed to start API server")
        print("Check your configuration in config.toml or environment variables")

if __name__ == "__main__":
    main() 