"""Alpaca Trading API client for executing trades"""

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderStatus, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    GetPortfolioHistoryRequest,
    LimitOrderRequest,
    MarketOrderRequest,
)
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class TradingConfig(BaseModel):
    """Configuration for Alpaca trading"""

    api_key: str = Field(..., description="Alpaca API key")
    secret_key: str = Field(..., description="Alpaca secret key")
    base_url: str = Field(default="https://paper-api.alpaca.markets", description="Alpaca base URL")
    data_url: str = Field(default="https://data.alpaca.markets", description="Alpaca data URL")
    paper_trading: bool = Field(default=True, description="Use paper trading")


class Position(BaseModel):
    """Represents a trading position"""

    symbol: str
    quantity: int
    side: str  # "long" or "short"
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float
    qty_available: int


class Order(BaseModel):
    """Represents a trading order"""

    id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: int
    order_type: str
    status: str
    created_at: datetime
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None


class Portfolio(BaseModel):
    """Represents portfolio information"""

    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    unrealized_pl: float
    realized_pl: float
    positions: List[Position] = []


class AlpacaTradingClient:
    """Client for Alpaca Trading API operations"""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.trading_client = TradingClient(
            api_key=config.api_key, secret_key=config.secret_key, paper=config.paper_trading
        )
        self.data_client = StockHistoricalDataClient(
            api_key=config.api_key, secret_key=config.secret_key
        )

    def get_account(self) -> Dict:
        """Get account information"""
        try:
            account = self.trading_client.get_account()

            # Build response with safe attribute access
            response = {
                "account_id": account.id,
                "equity": float(account.equity) if hasattr(account, "equity") else 0.0,
                "cash": float(account.cash) if hasattr(account, "cash") else 0.0,
                "buying_power": (
                    float(account.buying_power) if hasattr(account, "buying_power") else 0.0
                ),
                "currency": account.currency if hasattr(account, "currency") else "USD",
                "status": (
                    account.status.value
                    if hasattr(account.status, "value")
                    else str(account.status)
                ),
                "trading_blocked": (
                    account.trading_blocked if hasattr(account, "trading_blocked") else False
                ),
                "pattern_day_trader": (
                    account.pattern_day_trader if hasattr(account, "pattern_day_trader") else False
                ),
            }

            # Add optional fields that may not exist in all account types
            if hasattr(account, "portfolio_value"):
                response["portfolio_value"] = float(account.portfolio_value)
            else:
                response["portfolio_value"] = response["equity"]

            if hasattr(account, "long_market_value"):
                response["unrealized_pl"] = float(account.long_market_value) - float(account.cash)
            else:
                response["unrealized_pl"] = 0.0

            response["realized_pl"] = 0.0  # Not always available in paper accounts

            return response
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise

    def get_positions(self) -> List[Position]:
        """Get current positions"""
        try:
            positions = self.trading_client.get_all_positions()
            return [
                Position(
                    symbol=pos.symbol,
                    quantity=int(pos.qty),
                    side="long" if int(pos.qty) > 0 else "short",
                    market_value=float(pos.market_value),
                    cost_basis=float(pos.cost_basis),
                    unrealized_pl=float(pos.unrealized_pl),
                    unrealized_plpc=float(pos.unrealized_plpc),
                    current_price=float(pos.current_price),
                    qty_available=int(pos.qty_available),
                )
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def get_orders(self, status: Optional[str] = None, limit: int = 100) -> List[Order]:
        """Get orders with optional status filter"""
        try:
            request = GetOrdersRequest(status=status, limit=limit)
            orders = self.trading_client.get_orders(request)
            return [
                Order(
                    id=order.id,
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=int(order.qty),
                    order_type=order.order_type.value,
                    status=order.status.value,
                    created_at=order.created_at,
                    filled_at=order.filled_at,
                    filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                    filled_quantity=int(order.filled_qty) if order.filled_qty else None,
                )
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    def place_market_order(
        self, symbol: str, quantity: int, side: str, time_in_force: str = "day"
    ) -> Order:
        """Place a market order"""
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            time_in_force_enum = (
                TimeInForce.DAY if time_in_force.lower() == "day" else TimeInForce.GTC
            )

            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                time_in_force=time_in_force_enum,
            )

            order = self.trading_client.submit_order(order_request)

            return Order(
                id=order.id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=int(order.qty),
                order_type=order.order_type.value,
                status=order.status.value,
                created_at=order.created_at,
            )
        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            raise

    def place_limit_order(
        self, symbol: str, quantity: int, side: str, limit_price: float, time_in_force: str = "day"
    ) -> Order:
        """Place a limit order"""
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            time_in_force_enum = (
                TimeInForce.DAY if time_in_force.lower() == "day" else TimeInForce.GTC
            )

            order_request = LimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                time_in_force=time_in_force_enum,
                limit_price=limit_price,
            )

            order = self.trading_client.submit_order(order_request)

            return Order(
                id=order.id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=int(order.qty),
                order_type=order.order_type.value,
                status=order.status.value,
                created_at=order.created_at,
            )
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_portfolio_history(self, period: str = "1M", timeframe: str = "1Day") -> pd.DataFrame:
        """Get portfolio history"""
        try:
            # Convert period to start/end dates
            end_date = datetime.now()
            if period == "1D":
                start_date = end_date - timedelta(days=1)
            elif period == "1W":
                start_date = end_date - timedelta(weeks=1)
            elif period == "1M":
                start_date = end_date - timedelta(days=30)
            elif period == "3M":
                start_date = end_date - timedelta(days=90)
            elif period == "1Y":
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=30)

            # Convert timeframe
            tf = TimeFrame.Day if timeframe == "1Day" else TimeFrame.Hour

            request = GetPortfolioHistoryRequest(
                start=start_date,
                end=end_date,
                timeframe=tf,
            )

            history = self.trading_client.get_portfolio_history(request)

            # Convert to DataFrame
            data = []
            for i, timestamp in enumerate(history.timestamp):
                data.append(
                    {
                        "timestamp": timestamp,
                        "equity": float(history.equity[i]) if history.equity else 0,
                        "profit_loss": float(history.profit_loss[i]) if history.profit_loss else 0,
                        "profit_loss_pct": (
                            float(history.profit_loss_pct[i]) if history.profit_loss_pct else 0
                        ),
                    }
                )

            return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Failed to get portfolio history: {e}")
            return pd.DataFrame()

    def get_stock_data(
        self, symbols: List[str], start_date: datetime, end_date: datetime, timeframe: str = "1Day"
    ) -> pd.DataFrame:
        """Get historical stock data"""
        try:
            tf = TimeFrame.Day if timeframe == "1Day" else TimeFrame.Hour

            request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=tf,
                start=start_date,
                end=end_date,
            )

            bars = self.data_client.get_stock_bars(request)

            # Convert to DataFrame
            data = []
            for symbol, bar_list in bars.items():
                for bar in bar_list:
                    data.append(
                        {
                            "symbol": symbol,
                            "timestamp": bar.timestamp,
                            "open": float(bar.open),
                            "high": float(bar.high),
                            "low": float(bar.low),
                            "close": float(bar.close),
                            "volume": int(bar.volume),
                        }
                    )

            return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Failed to get stock data: {e}")
            return pd.DataFrame()

    def get_portfolio(self) -> Portfolio:
        """Get complete portfolio information"""
        try:
            account = self.get_account()
            positions = self.get_positions()

            return Portfolio(
                equity=account["equity"],
                cash=account["cash"],
                buying_power=account["buying_power"],
                portfolio_value=account["portfolio_value"],
                unrealized_pl=account["unrealized_pl"],
                realized_pl=account["realized_pl"],
                positions=positions,
            )
        except Exception as e:
            logger.error(f"Failed to get portfolio: {e}")
            raise


def create_trading_client(
    api_key: str = None, secret_key: str = None, paper_trading: bool = True
) -> AlpacaTradingClient:
    """
    Create a trading client with the given credentials or from environment variables

    Args:
        api_key: Alpaca API key (if None, loads from ALPACA_API_KEY env var)
        secret_key: Alpaca secret key (if None, loads from ALPACA_SECRET_KEY env var)
        paper_trading: Whether to use paper trading (default: True)

    Returns:
        AlpacaTradingClient instance
    """
    # Load from environment if not provided
    if api_key is None:
        api_key = os.getenv("ALPACA_API_KEY")
    if secret_key is None:
        secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise ValueError(
            "Alpaca API credentials not found. "
            "Please provide api_key and secret_key, or set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
        )

    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    config = TradingConfig(
        api_key=api_key, secret_key=secret_key, base_url=base_url, paper_trading=paper_trading
    )
    return AlpacaTradingClient(config)


def get_alpaca_config_from_env() -> Optional[Dict[str, str]]:
    """
    Get Alpaca configuration from environment variables

    Returns:
        Dictionary with API configuration or None if not configured
    """
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    if not api_key or not secret_key:
        return None

    return {
        "api_key": api_key,
        "secret_key": secret_key,
        "base_url": base_url,
        "is_paper": "paper" in base_url.lower(),
    }
