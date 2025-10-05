"""Custom middleware for API"""

import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from mcli.ml.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests and responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response {request_id}: status={response.status_code} " f"duration={process_time:.3f}s"
        )

        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.clients = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host

        # Check rate limit
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip] if req_time > minute_ago
        ]

        # Check if limit exceeded
        if len(self.clients[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": "60"},
            )

        # Record request
        self.clients[client_ip].append(now)

        # Process request
        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except HTTPException as e:
            # Let FastAPI handle HTTP exceptions
            raise e

        except Exception as e:
            # Log unexpected errors
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(f"Unhandled exception in request {request_id}: {str(e)}", exc_info=True)

            # Return generic error response
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal error occurred", "request_id": request_id},
            )


class CompressionMiddleware(BaseHTTPMiddleware):
    """Response compression middleware"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" in accept_encoding.lower():
            # Response will be compressed by GZipMiddleware
            response.headers["Vary"] = "Accept-Encoding"

        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add cache control headers"""

    def __init__(self, app: ASGIApp, max_age: int = 0):
        super().__init__(app)
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add cache control headers based on endpoint
        if request.url.path.startswith("/api/v1/data"):
            # Cache data endpoints
            response.headers["Cache-Control"] = f"public, max-age=300"
        elif request.url.path.startswith("/api/v1/predictions"):
            # Don't cache predictions
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        else:
            # Default cache control
            response.headers["Cache-Control"] = f"public, max-age={self.max_age}"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss: https:;"
        )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect metrics for monitoring"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Record metrics
        endpoint = f"{request.method} {request.url.path}"
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Update metrics
        duration = time.time() - start_time
        self.request_count[endpoint] += 1
        self.request_duration[endpoint].append(duration)

        # Limit history size
        if len(self.request_duration[endpoint]) > 1000:
            self.request_duration[endpoint] = self.request_duration[endpoint][-1000:]

        return response

    def get_metrics(self) -> dict:
        """Get collected metrics"""
        metrics = {}
        for endpoint, count in self.request_count.items():
            durations = self.request_duration[endpoint]
            if durations:
                metrics[endpoint] = {
                    "count": count,
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }
        return metrics
