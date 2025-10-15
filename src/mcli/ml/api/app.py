"""FastAPI application factory and configuration"""

from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from mcli.ml.cache import init_cache
from mcli.ml.config import settings
from mcli.ml.database.session import init_db
from mcli.ml.logging import get_logger, setup_logging

from .middleware import ErrorHandlingMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from .routers import (
    admin_router,
    auth_router,
    backtest_router,
    data_router,
    model_router,
    monitoring_router,
    portfolio_router,
    prediction_router,
    trade_router,
    websocket_router,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting ML API server...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Initialize cache
    await init_cache()
    logger.info("Cache initialized")

    # Initialize ML models
    from mcli.ml.models import load_production_models

    await load_production_models()
    logger.info("ML models loaded")

    yield

    # Shutdown
    logger.info("Shutting down ML API server...")

    # Cleanup cache connections
    from mcli.ml.cache import close_cache

    await close_cache()

    # Cleanup database connections
    from mcli.ml.database.session import async_engine

    await async_engine.dispose()


def create_app() -> FastAPI:
    """Create FastAPI application with all configurations"""

    # Setup logging
    setup_logging()

    # Create FastAPI app
    app = FastAPI(
        title="MCLI ML System API",
        description="ML system for politician trading analysis and stock recommendations",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Add middlewares
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.api.rate_limit)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.api.secret_key,
        session_cookie="ml_session",
        max_age=3600,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.mcli-ml.com", "mcli-ml.com"])

    # Include routers
    app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(model_router.router, prefix="/api/v1/models", tags=["Models"])
    app.include_router(prediction_router.router, prefix="/api/v1/predictions", tags=["Predictions"])
    app.include_router(portfolio_router.router, prefix="/api/v1/portfolios", tags=["Portfolios"])
    app.include_router(data_router.router, prefix="/api/v1/data", tags=["Data"])
    app.include_router(trade_router.router, prefix="/api/v1/trades", tags=["Trades"])
    app.include_router(backtest_router.router, prefix="/api/v1/backtests", tags=["Backtesting"])
    app.include_router(monitoring_router.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
    app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(websocket_router.router, prefix="/ws", tags=["WebSocket"])

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "environment": settings.environment, "version": "1.0.0"}

    # Ready check endpoint
    @app.get("/ready", tags=["Health"])
    async def ready_check():
        """Readiness check endpoint"""
        from mcli.ml.cache import check_cache_health
        from mcli.ml.database.session import check_database_health

        db_healthy = await check_database_health()
        cache_healthy = await check_cache_health()

        if db_healthy and cache_healthy:
            return {"status": "ready", "database": "healthy", "cache": "healthy"}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not ready",
                    "database": "healthy" if db_healthy else "unhealthy",
                    "cache": "healthy" if cache_healthy else "unhealthy",
                },
            )

    # Metrics endpoint (Prometheus format)
    @app.get("/metrics", tags=["Monitoring"])
    async def metrics():
        """Prometheus metrics endpoint"""
        from mcli.ml.monitoring.metrics import get_metrics

        return Response(content=get_metrics(), media_type="text/plain")

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "MCLI ML System API",
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else None,
        }

    # Exception handlers
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(status_code=404, content={"detail": "Resource not found"})

    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc):
        logger.error(f"Internal server error: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


def get_application() -> FastAPI:
    """Get configured FastAPI application"""
    return create_app()


# Create app instance
app = get_application()


if __name__ == "__main__":
    """Run the application directly"""
    uvicorn.run(
        "mcli.ml.api.app:app",
        host=settings.api.host,
        port=settings.api.port,
        workers=settings.api.workers,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
