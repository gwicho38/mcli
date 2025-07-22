import os
import sys
import json
import inspect
import functools
from typing import Dict, Any, Optional, Callable, List, Union
from pathlib import Path
import click
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import threading
import time
import requests
from contextlib import asynccontextmanager

# Import existing utilities
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

# Global FastAPI app instance
_api_app: Optional[FastAPI] = None
_api_server_thread: Optional[threading.Thread] = None
_api_server_running = False

class ClickToAPIDecorator:
    """Decorator that makes Click commands also serve as API endpoints."""
    
    def __init__(self, 
                 endpoint_path: str = None,
                 http_method: str = "POST",
                 response_model: BaseModel = None,
                 description: str = None,
                 tags: List[str] = None):
        """
        Initialize the decorator.
        
        Args:
            endpoint_path: API endpoint path (defaults to command name)
            http_method: HTTP method (GET, POST, PUT, DELETE)
            response_model: Pydantic model for response validation
            description: API endpoint description
            tags: API tags for grouping
        """
        self.endpoint_path = endpoint_path
        self.http_method = http_method.upper()
        self.response_model = response_model
        self.description = description
        self.tags = tags or []
        
    def __call__(self, func: Callable) -> Callable:
        """Apply the decorator to a function."""
        
        # Get the original function signature
        sig = inspect.signature(func)
        
        # Create a wrapper that registers the API endpoint
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Register the API endpoint
            self._register_api_endpoint(func, sig)
            
            # Call the original function
            return func(*args, **kwargs)
        
        # Store decorator info for later registration
        wrapper._api_decorator = self
        wrapper._original_func = func
        
        return wrapper
    
    def _register_api_endpoint(self, func: Callable, sig: inspect.Signature):
        """Register the function as an API endpoint."""
        global _api_app
        
        if _api_app is None:
            _api_app = self._create_fastapi_app()
        
        # Determine endpoint path
        endpoint_path = self.endpoint_path or f"/{func.__name__}"
        
        # Create request model from function signature
        request_model = self._create_request_model(func, sig)
        
        # Create response model
        response_model = self.response_model or self._create_response_model()
        
        # Register the endpoint
        self._register_endpoint(
            app=_api_app,
            path=endpoint_path,
            method=self.http_method,
            func=func,
            request_model=request_model,
            response_model=response_model,
            description=self.description or func.__doc__,
            tags=self.tags
        )
        
        logger.info(f"Registered API endpoint: {self.http_method} {endpoint_path}")
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create and configure FastAPI app."""
        app = FastAPI(
            title="MCLI API",
            description="API endpoints for MCLI commands",
            version="1.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add health check endpoint
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "MCLI API"}
        
        # Add root endpoint
        @app.get("/")
        async def root():
            return {
                "service": "MCLI API",
                "version": "1.0.0",
                "status": "running",
                "endpoints": self._get_registered_endpoints(app)
            }
        
        return app
    
    def _create_request_model(self, func: Callable, sig: inspect.Signature) -> BaseModel:
        """Create a Pydantic model from function signature."""
        fields = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'ctx']:
                continue
                
            # Get parameter type and default
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else ...
            
            # Handle Click-specific types
            if hasattr(param_type, '__origin__') and param_type.__origin__ is Union:
                # Handle Union types (e.g., Optional[str])
                param_type = str
            elif param_type == bool:
                # Handle boolean flags
                param_type = bool
            elif param_type in [int, float]:
                param_type = param_type
            else:
                param_type = str
            
            fields[param_name] = (param_type, default)
        
        # Create dynamic model
        model_name = f"{func.__name__}Request"
        return type(model_name, (BaseModel,), fields)
    
    def _create_response_model(self) -> BaseModel:
        """Create a default response model."""
        class DefaultResponse(BaseModel):
            success: bool = Field(..., description="Operation success status")
            result: Any = Field(None, description="Operation result")
            message: str = Field("", description="Operation message")
            error: str = Field(None, description="Error message if any")
        
        return DefaultResponse
    
    def _register_endpoint(self, 
                          app: FastAPI,
                          path: str,
                          method: str,
                          func: Callable,
                          request_model: BaseModel,
                          response_model: BaseModel,
                          description: str,
                          tags: List[str]):
        """Register an endpoint with FastAPI."""
        
        async def api_endpoint(request: request_model):
            """API endpoint wrapper."""
            try:
                # Convert request model to kwargs
                kwargs = request.dict()
                
                # Call the original function
                result = func(**kwargs)
                
                # Return response
                return response_model(
                    success=True,
                    result=result,
                    message="Operation completed successfully"
                )
                
            except Exception as e:
                logger.error(f"API endpoint error: {e}")
                return response_model(
                    success=False,
                    error=str(e),
                    message="Operation failed"
                )
        
        # Register with FastAPI
        if method == "GET":
            app.get(path, response_model=response_model, description=description, tags=tags)(api_endpoint)
        elif method == "POST":
            app.post(path, response_model=response_model, description=description, tags=tags)(api_endpoint)
        elif method == "PUT":
            app.put(path, response_model=response_model, description=description, tags=tags)(api_endpoint)
        elif method == "DELETE":
            app.delete(path, response_model=response_model, description=description, tags=tags)(api_endpoint)
    
    def _get_registered_endpoints(self, app: FastAPI) -> List[Dict[str, str]]:
        """Get list of registered endpoints."""
        endpoints = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                for method in route.methods:
                    endpoints.append({
                        "path": route.path,
                        "method": method,
                        "name": getattr(route, 'name', 'Unknown')
                    })
        return endpoints


def api_endpoint(endpoint_path: str = None,
                http_method: str = "POST",
                response_model: BaseModel = None,
                description: str = None,
                tags: List[str] = None):
    """
    Decorator that makes Click commands also serve as API endpoints.
    
    Args:
        endpoint_path: API endpoint path (defaults to command name)
        http_method: HTTP method (GET, POST, PUT, DELETE)
        response_model: Pydantic model for response validation
        description: API endpoint description
        tags: API tags for grouping
    
    Example:
        @click.command()
        @api_endpoint("/generate", "POST")
        def generate_text(prompt: str, max_length: int = 100):
            return {"text": "Generated text"}
    """
    return ClickToAPIDecorator(
        endpoint_path=endpoint_path,
        http_method=http_method,
        response_model=response_model,
        description=description,
        tags=tags
    )


def start_api_server(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    """Start the API server."""
    global _api_app, _api_server_thread, _api_server_running
    
    if _api_app is None:
        _api_app = FastAPI(
            title="MCLI API",
            description="API endpoints for MCLI commands",
            version="1.0.0"
        )
        
        # Add CORS middleware
        _api_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add health check endpoint
        @_api_app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "MCLI API"}
        
        # Add root endpoint
        @_api_app.get("/")
        async def root():
            return {
                "service": "MCLI API",
                "version": "1.0.0",
                "status": "running"
            }
    
    def run_server():
        uvicorn.run(_api_app, host=host, port=port, log_level="info" if not debug else "debug")
    
    if not _api_server_running:
        _api_server_thread = threading.Thread(target=run_server, daemon=True)
        _api_server_thread.start()
        _api_server_running = True
        
        # Wait a moment for server to start
        time.sleep(1)
        
        logger.info(f"API server started at http://{host}:{port}")
        logger.info(f"Health check: http://{host}:{port}/health")
    
    return f"http://{host}:{port}"


def stop_api_server():
    """Stop the API server."""
    global _api_server_running
    
    if _api_server_running:
        # In a real implementation, you'd want to properly shutdown the server
        # For now, we'll just set the flag
        _api_server_running = False
        logger.info("API server stopped")


def get_api_app() -> Optional[FastAPI]:
    """Get the FastAPI app instance."""
    return _api_app


def is_api_server_running() -> bool:
    """Check if the API server is running."""
    return _api_server_running


def register_command_as_api(command_func: Callable, 
                          endpoint_path: str = None,
                          http_method: str = "POST",
                          response_model: BaseModel = None,
                          description: str = None,
                          tags: List[str] = None):
    """
    Register a Click command as an API endpoint.
    
    Args:
        command_func: The Click command function
        endpoint_path: API endpoint path
        http_method: HTTP method
        response_model: Pydantic model for response
        description: API endpoint description
        tags: API tags for grouping
    """
    decorator = ClickToAPIDecorator(
        endpoint_path=endpoint_path,
        http_method=http_method,
        response_model=response_model,
        description=description,
        tags=tags
    )
    
    # Register the endpoint
    decorator._register_api_endpoint(command_func, inspect.signature(command_func))
    
    logger.info(f"Registered command as API endpoint: {http_method} {endpoint_path or f'/{command_func.__name__}'}")


# Convenience function for common response models
def create_success_response_model(result_type: type = str):
    """Create a success response model."""
    class SuccessResponse(BaseModel):
        success: bool = Field(True, description="Operation success status")
        result: result_type = Field(..., description="Operation result")
        message: str = Field("Operation completed successfully", description="Operation message")
    
    return SuccessResponse


def create_error_response_model():
    """Create an error response model."""
    class ErrorResponse(BaseModel):
        success: bool = Field(False, description="Operation success status")
        error: str = Field(..., description="Error message")
        message: str = Field("Operation failed", description="Operation message")
    
    return ErrorResponse


