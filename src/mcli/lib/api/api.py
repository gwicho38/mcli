import functools
import inspect
import json
import os
import random
import socket
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import click
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import existing utilities
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

logger = get_logger(__name__)

# Global FastAPI app instance
_api_app: Optional[FastAPI] = None
_api_server_thread: Optional[threading.Thread] = None
_api_server_running = False


def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    Find a free port starting from start_port.

    Args:
        start_port: Starting port number
        max_attempts: Maximum number of attempts to find a free port

    Returns:
        A free port number
    """
    for attempt in range(max_attempts):
        port = start_port + attempt
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue

    # If no free port found, use a random port in a safe range
    return random.randint(49152, 65535)


def get_api_config() -> Dict[str, Any]:
    """
    Get API configuration from MCLI config files.

    Returns:
        Dictionary with API configuration
    """
    config = {
        "enabled": False,
        "host": "0.0.0.0",
        "port": None,  # Will be set to random port if None
        "use_random_port": True,
        "debug": False,
    }

    # Try to load from config.toml files
    config_paths = [
        Path("config.toml"),  # Current directory
        Path.home() / ".config" / "mcli" / "config.toml",  # User config
        Path(__file__).parent.parent.parent.parent.parent / "config.toml",  # Project root
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                api_config = read_from_toml(str(config_path), "api")
                if api_config:
                    config.update(api_config)
                    logger.debug(f"Loaded API config from {config_path}")
                    break
            except Exception as e:
                logger.debug(f"Could not load API config from {config_path}: {e}")

    # Override with environment variables
    if os.environ.get("MCLI_API_SERVER", "false").lower() in ("true", "1", "yes"):
        config["enabled"] = True

    if os.environ.get("MCLI_API_HOST"):
        config["host"] = os.environ.get("MCLI_API_HOST")

    if os.environ.get("MCLI_API_PORT"):
        config["port"] = int(os.environ.get("MCLI_API_PORT"))
        config["use_random_port"] = False

    if os.environ.get("MCLI_API_DEBUG", "false").lower() in ("true", "1", "yes"):
        config["debug"] = True

    # Set random port if needed
    if config["enabled"] and config["use_random_port"] and config["port"] is None:
        config["port"] = find_free_port()
        logger.info(f"Using random port: {config['port']}")

    return config


class ClickToAPIDecorator:
    """Decorator that makes Click commands also serve as API endpoints."""

    def __init__(
        self,
        endpoint_path: str = None,
        http_method: str = "POST",
        response_model: BaseModel = None,
        description: str = None,
        tags: List[str] = None,
    ):
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

        # Ensure API app exists
        if _api_app is None:
            _api_app = ensure_api_app()
            if _api_app is None:
                logger.warning("Could not create API app, skipping endpoint registration")
                return

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
            tags=self.tags,
        )

        logger.info(f"Registered API endpoint: {self.http_method} {endpoint_path}")

    def _create_fastapi_app(self) -> FastAPI:
        """Create and configure FastAPI app."""
        app = FastAPI(
            title="MCLI API", description="API endpoints for MCLI commands", version="1.0.0"
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
                "endpoints": self._get_registered_endpoints(app),
            }

        return app

    def _create_request_model(self, func: Callable, sig: inspect.Signature) -> BaseModel:
        """Create a Pydantic model from function signature."""
        fields = {}

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "ctx"]:
                continue

            # Get parameter type and default
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else ...

            # Handle Click-specific types
            if hasattr(param_type, "__origin__") and param_type.__origin__ is Union:
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

    def _register_endpoint(
        self,
        app: FastAPI,
        path: str,
        method: str,
        func: Callable,
        request_model: BaseModel,
        response_model: BaseModel,
        description: str,
        tags: List[str],
    ):
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
                    success=True, result=result, message="Operation completed successfully"
                )

            except Exception as e:
                logger.error(f"API endpoint error: {e}")
                return response_model(success=False, error=str(e), message="Operation failed")

        # Register with FastAPI
        if method == "GET":
            app.get(path, response_model=response_model, description=description, tags=tags)(
                api_endpoint
            )
        elif method == "POST":
            app.post(path, response_model=response_model, description=description, tags=tags)(
                api_endpoint
            )
        elif method == "PUT":
            app.put(path, response_model=response_model, description=description, tags=tags)(
                api_endpoint
            )
        elif method == "DELETE":
            app.delete(path, response_model=response_model, description=description, tags=tags)(
                api_endpoint
            )

    def _get_registered_endpoints(self, app: FastAPI) -> List[Dict[str, str]]:
        """Get list of registered endpoints."""
        endpoints = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    endpoints.append(
                        {
                            "path": route.path,
                            "method": method,
                            "name": getattr(route, "name", "Unknown"),
                        }
                    )
        return endpoints


def api_endpoint(
    endpoint_path: str = None,
    http_method: str = "POST",
    response_model: BaseModel = None,
    description: str = None,
    tags: List[str] = None,
):
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
        tags=tags,
    )


def ensure_api_app() -> Optional[FastAPI]:
    """Ensure the API app is created and return it."""
    global _api_app

    if _api_app is None:
        # Get configuration
        config = get_api_config()

        # Check if API server should be enabled
        if not config["enabled"]:
            logger.debug("API server is disabled in configuration")
            return None

        # Create the API app
        _api_app = FastAPI(
            title="MCLI API", description="API endpoints for MCLI commands", version="1.0.0"
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
                "status": "running",
                "config": {
                    "host": config.get("host", "0.0.0.0"),
                    "port": config.get("port", "random"),
                    "debug": config.get("debug", False),
                },
            }

        logger.debug("API app created successfully")

    return _api_app


def start_api_server(host: str = None, port: int = None, debug: bool = None) -> str:
    """Start the API server with configuration from MCLI config."""
    global _api_app, _api_server_thread, _api_server_running

    # Get configuration
    config = get_api_config()

    # Override with parameters if provided
    if host is not None:
        config["host"] = host
    if port is not None:
        config["port"] = port
        config["use_random_port"] = False
    if debug is not None:
        config["debug"] = debug

    # Check if API server should be enabled
    if not config["enabled"]:
        logger.info("API server is disabled in configuration")
        return None

    # Find port if not specified
    if config["port"] is None:
        config["port"] = find_free_port()
        logger.info(f"Using random port: {config['port']}")

    if _api_app is None:
        _api_app = FastAPI(
            title="MCLI API", description="API endpoints for MCLI commands", version="1.0.0"
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
                "status": "running",
                "config": {
                    "host": config["host"],
                    "port": config["port"],
                    "debug": config["debug"],
                },
            }

    def run_server():
        uvicorn.run(
            _api_app, host=config["host"], port=config["port"], log_level="error", access_log=False
        )

    if not _api_server_running:
        _api_server_thread = threading.Thread(target=run_server, daemon=True)
        _api_server_thread.start()
        _api_server_running = True

        # Wait a moment for server to start
        time.sleep(1)

        api_url = f"http://{config['host']}:{config['port']}"
        logger.info(f"API server started at {api_url}")
        logger.info(f"Health check: {api_url}/health")
        logger.info(f"Documentation: {api_url}/docs")

        return api_url

    return f"http://{config['host']}:{config['port']}"


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


def register_command_as_api(
    command_func: Callable,
    endpoint_path: str = None,
    http_method: str = "POST",
    response_model: BaseModel = None,
    description: str = None,
    tags: List[str] = None,
):
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
    logger.info(
        f"register_command_as_api called for: {command_func.__name__} with path: {endpoint_path}"
    )

    # Ensure API app is created
    api_app = ensure_api_app()
    if api_app is None:
        logger.debug("API app not available, skipping endpoint registration")
        return

    logger.info(f"API app available, proceeding with registration")

    decorator = ClickToAPIDecorator(
        endpoint_path=endpoint_path,
        http_method=http_method,
        response_model=response_model,
        description=description,
        tags=tags,
    )

    # Register the endpoint directly with the API app
    sig = inspect.signature(command_func)
    decorator._register_api_endpoint(command_func, sig)

    logger.info(
        f"Registered command as API endpoint: {http_method} {endpoint_path or f'/{command_func.__name__}'}"
    )


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
