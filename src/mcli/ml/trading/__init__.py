"""Trading module for portfolio management and trade execution."""

from mcli.ml.trading.alpaca_client import (
    AlpacaTradingClient,
    create_trading_client,
    get_alpaca_config_from_env,
)
from mcli.ml.trading.models import (  # Enums; Database models; Pydantic models
    OrderCreate,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Portfolio,
    PortfolioCreate,
    PortfolioPerformanceSnapshot,
    PortfolioResponse,
    PortfolioType,
    Position,
    PositionResponse,
    PositionSide,
    RiskLevel,
    TradingAccount,
    TradingAccountCreate,
    TradingOrder,
    TradingSignal,
    TradingSignalResponse,
)
from mcli.ml.trading.paper_trading import PaperTradingEngine
from mcli.ml.trading.risk_management import RiskManager
from mcli.ml.trading.trading_service import TradingService

__all__ = [
    # Enums
    "OrderStatus",
    "OrderType",
    "OrderSide",
    "PositionSide",
    "PortfolioType",
    "RiskLevel",
    # Database models
    "TradingAccount",
    "Portfolio",
    "Position",
    "TradingOrder",
    "PortfolioPerformanceSnapshot",
    "TradingSignal",
    # Pydantic models
    "TradingAccountCreate",
    "PortfolioCreate",
    "OrderCreate",
    "PositionResponse",
    "OrderResponse",
    "PortfolioResponse",
    "TradingSignalResponse",
    # Services
    "TradingService",
    "AlpacaTradingClient",
    "create_trading_client",
    "get_alpaca_config_from_env",
    "RiskManager",
    "PaperTradingEngine",
]
