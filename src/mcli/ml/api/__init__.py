"""API routes and endpoints for ML system."""

from .app import create_app, get_application
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

__all__ = [
    "auth_router",
    "model_router",
    "prediction_router",
    "portfolio_router",
    "data_router",
    "trade_router",
    "backtest_router",
    "monitoring_router",
    "admin_router",
    "websocket_router",
    "create_app",
    "get_application",
]
