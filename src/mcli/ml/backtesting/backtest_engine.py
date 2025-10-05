"""Backtesting engine for trading strategies"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ml.models.recommendation_models import PortfolioRecommendation, StockRecommendationModel

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order side"""

    BUY = "buy"
    SELL = "sell"


@dataclass
class BacktestConfig:
    """Backtesting configuration"""

    initial_capital: float = 100000.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    commission: float = 0.001  # 0.1%
    slippage: float = 0.001  # 0.1%
    max_positions: int = 20
    position_sizing: str = "equal"  # equal, kelly, risk_parity
    rebalance_frequency: str = "weekly"  # daily, weekly, monthly
    stop_loss: Optional[float] = 0.1  # 10% stop loss
    take_profit: Optional[float] = 0.2  # 20% take profit
    benchmark: str = "SPY"
    risk_free_rate: float = 0.02  # 2% annual
    verbose: bool = True


@dataclass
class BacktestResult:
    """Backtesting results"""

    portfolio_value: pd.Series
    returns: pd.Series
    positions: pd.DataFrame
    trades: pd.DataFrame
    metrics: Dict[str, float]
    benchmark_returns: Optional[pd.Series] = None
    strategy_name: str = "strategy"


class TradingStrategy:
    """Base trading strategy class"""

    def __init__(self, model: Optional[StockRecommendationModel] = None):
        self.model = model
        self.current_positions = {}
        self.pending_orders = []

    def generate_signals(
        self, data: pd.DataFrame, current_date: datetime, portfolio_value: float
    ) -> List[Dict[str, Any]]:
        """Generate trading signals"""
        signals = []

        if self.model:
            # Use ML model for predictions
            recommendations = self._get_model_recommendations(data, current_date)

            for rec in recommendations:
                signal = {
                    "ticker": rec.ticker,
                    "action": "buy" if rec.recommendation_score > 0.6 else "sell",
                    "confidence": rec.confidence,
                    "position_size": rec.position_size,
                    "entry_price": rec.entry_price,
                    "target_price": rec.target_price,
                    "stop_loss": rec.stop_loss,
                }
                signals.append(signal)
        else:
            # Simple momentum strategy as fallback
            signals = self._momentum_strategy(data, current_date)

        return signals

    def _get_model_recommendations(
        self, data: pd.DataFrame, current_date: datetime
    ) -> List[PortfolioRecommendation]:
        """Get recommendations from ML model"""
        # Filter data up to current date
        historical_data = data[data["date"] <= current_date]

        # Extract features (simplified)
        features = historical_data.select_dtypes(include=[np.number]).values[-1:, :]

        # Get unique tickers
        tickers = historical_data["symbol"].unique()[:5]  # Limit to 5 for speed

        # Generate recommendations
        try:
            recommendations = self.model.generate_recommendations(features, tickers.tolist())
            return recommendations
        except Exception as e:
            logger.warning(f"Model prediction failed: {e}")
            return []

    def _momentum_strategy(
        self, data: pd.DataFrame, current_date: datetime
    ) -> List[Dict[str, Any]]:
        """Simple momentum strategy"""
        signals = []

        # Get recent data
        recent_data = data[data["date"] <= current_date].tail(20)

        if len(recent_data) < 20:
            return signals

        # Calculate momentum for each ticker
        for ticker in recent_data["symbol"].unique():
            ticker_data = recent_data[recent_data["symbol"] == ticker]

            if len(ticker_data) < 2:
                continue

            # Simple momentum: compare current price to 20-day average
            current_price = ticker_data["close"].iloc[-1]
            avg_price = ticker_data["close"].mean()

            if current_price > avg_price * 1.05:  # 5% above average
                signals.append(
                    {
                        "ticker": ticker,
                        "action": "buy",
                        "confidence": 0.6,
                        "position_size": 0.05,  # 5% position
                    }
                )
            elif current_price < avg_price * 0.95:  # 5% below average
                signals.append(
                    {"ticker": ticker, "action": "sell", "confidence": 0.6, "position_size": 0.05}
                )

        return signals


class PositionManager:
    """Manage portfolio positions"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.cash = config.initial_capital
        self.portfolio_value = config.initial_capital

    def open_position(
        self, ticker: str, quantity: int, price: float, date: datetime, signal: Dict[str, Any]
    ):
        """Open a new position"""
        cost = quantity * price * (1 + self.config.commission + self.config.slippage)

        if cost > self.cash:
            logger.warning(f"Insufficient cash to open position in {ticker}")
            return False

        self.cash -= cost
        self.positions[ticker] = {
            "quantity": quantity,
            "entry_price": price,
            "entry_date": date,
            "current_price": price,
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("target_price"),
            "unrealized_pnl": 0,
            "realized_pnl": 0,
        }

        logger.debug(f"Opened position: {ticker} - {quantity} shares @ ${price:.2f}")
        return True

    def close_position(self, ticker: str, price: float, date: datetime) -> float:
        """Close a position"""
        if ticker not in self.positions:
            return 0

        position = self.positions[ticker]
        quantity = position["quantity"]

        # Calculate PnL
        gross_proceeds = quantity * price
        net_proceeds = gross_proceeds * (1 - self.config.commission - self.config.slippage)
        entry_cost = quantity * position["entry_price"]

        realized_pnl = net_proceeds - entry_cost
        self.cash += net_proceeds

        logger.debug(f"Closed position: {ticker} - PnL: ${realized_pnl:.2f}")

        del self.positions[ticker]
        return realized_pnl

    def update_positions(self, price_data: Dict[str, float]):
        """Update position prices and calculate unrealized PnL"""
        for ticker, position in self.positions.items():
            if ticker in price_data:
                current_price = price_data[ticker]
                position["current_price"] = current_price

                # Calculate unrealized PnL
                entry_cost = position["quantity"] * position["entry_price"]
                current_value = position["quantity"] * current_price
                position["unrealized_pnl"] = current_value - entry_cost

                # Check stop loss
                if position.get("stop_loss") and current_price <= position["stop_loss"]:
                    logger.info(f"Stop loss triggered for {ticker}")
                    return ticker, "stop_loss"

                # Check take profit
                if position.get("take_profit") and current_price >= position["take_profit"]:
                    logger.info(f"Take profit triggered for {ticker}")
                    return ticker, "take_profit"

        return None, None

    def get_portfolio_value(self, price_data: Dict[str, float]) -> float:
        """Calculate total portfolio value"""
        positions_value = sum(
            pos["quantity"] * price_data.get(ticker, pos["current_price"])
            for ticker, pos in self.positions.items()
        )
        return self.cash + positions_value

    def get_position_weights(self, price_data: Dict[str, float]) -> Dict[str, float]:
        """Get position weights"""
        portfolio_value = self.get_portfolio_value(price_data)
        weights = {}

        for ticker, pos in self.positions.items():
            position_value = pos["quantity"] * price_data.get(ticker, pos["current_price"])
            weights[ticker] = position_value / portfolio_value

        weights["cash"] = self.cash / portfolio_value
        return weights


class BacktestEngine:
    """Main backtesting engine"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.position_manager = PositionManager(config)
        self.trades = []
        self.portfolio_history = []
        self.strategy = None

    def set_strategy(self, strategy: TradingStrategy):
        """Set trading strategy"""
        self.strategy = strategy

    def run(
        self, price_data: pd.DataFrame, trading_data: Optional[pd.DataFrame] = None
    ) -> BacktestResult:
        """Run backtest"""
        logger.info("Starting backtest...")

        # Prepare data
        price_data = price_data.sort_values("date")

        if self.config.start_date:
            price_data = price_data[price_data["date"] >= self.config.start_date]
        if self.config.end_date:
            price_data = price_data[price_data["date"] <= self.config.end_date]

        # Get unique dates
        dates = price_data["date"].unique()

        # Initialize results
        portfolio_values = []
        daily_positions = []

        # Main backtest loop
        for i, current_date in enumerate(dates):
            # Get current prices
            current_prices = self._get_current_prices(price_data, current_date)

            # Update positions with current prices
            trigger_ticker, trigger_type = self.position_manager.update_positions(current_prices)

            # Handle stop loss or take profit triggers
            if trigger_ticker:
                self._execute_exit(
                    trigger_ticker, current_prices[trigger_ticker], current_date, trigger_type
                )

            # Generate signals (e.g., weekly rebalancing)
            if self._should_rebalance(i, current_date):
                signals = self.strategy.generate_signals(
                    price_data[price_data["date"] <= current_date],
                    current_date,
                    self.position_manager.get_portfolio_value(current_prices),
                )

                # Execute signals
                self._execute_signals(signals, current_prices, current_date)

            # Record portfolio value
            portfolio_value = self.position_manager.get_portfolio_value(current_prices)
            portfolio_values.append(
                {
                    "date": current_date,
                    "value": portfolio_value,
                    "cash": self.position_manager.cash,
                    "positions_value": portfolio_value - self.position_manager.cash,
                }
            )

            # Record positions
            position_snapshot = self._get_position_snapshot(current_date, current_prices)
            daily_positions.append(position_snapshot)

        # Create results
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df.set_index("date", inplace=True)

        # Calculate returns
        portfolio_df["returns"] = portfolio_df["value"].pct_change().fillna(0)

        # Calculate metrics
        metrics = self._calculate_metrics(portfolio_df)

        # Get benchmark returns if available
        benchmark_returns = self._get_benchmark_returns(price_data, dates)

        result = BacktestResult(
            portfolio_value=portfolio_df["value"],
            returns=portfolio_df["returns"],
            positions=pd.DataFrame(daily_positions),
            trades=pd.DataFrame(self.trades),
            metrics=metrics,
            benchmark_returns=benchmark_returns,
            strategy_name=self.strategy.__class__.__name__,
        )

        logger.info(f"Backtest complete. Total return: {metrics['total_return']:.2%}")

        return result

    def _get_current_prices(
        self, price_data: pd.DataFrame, current_date: datetime
    ) -> Dict[str, float]:
        """Get current prices for all tickers"""
        current_data = price_data[price_data["date"] == current_date]
        return dict(zip(current_data["symbol"], current_data["close"]))

    def _should_rebalance(self, day_index: int, current_date: datetime) -> bool:
        """Check if should rebalance portfolio"""
        if self.config.rebalance_frequency == "daily":
            return True
        elif self.config.rebalance_frequency == "weekly":
            return day_index % 5 == 0
        elif self.config.rebalance_frequency == "monthly":
            return day_index % 21 == 0
        return False

    def _execute_signals(
        self,
        signals: List[Dict[str, Any]],
        current_prices: Dict[str, float],
        current_date: datetime,
    ):
        """Execute trading signals"""
        for signal in signals:
            ticker = signal["ticker"]

            if ticker not in current_prices:
                continue

            price = current_prices[ticker]

            if signal["action"] == "buy":
                # Calculate position size
                portfolio_value = self.position_manager.get_portfolio_value(current_prices)
                position_value = portfolio_value * signal.get("position_size", 0.05)
                quantity = int(position_value / price)

                if quantity > 0:
                    # Check if already have position
                    if ticker not in self.position_manager.positions:
                        # Check max positions
                        if len(self.position_manager.positions) < self.config.max_positions:
                            success = self.position_manager.open_position(
                                ticker, quantity, price, current_date, signal
                            )

                            if success:
                                self.trades.append(
                                    {
                                        "date": current_date,
                                        "ticker": ticker,
                                        "action": "buy",
                                        "quantity": quantity,
                                        "price": price,
                                        "value": quantity * price,
                                    }
                                )

            elif signal["action"] == "sell":
                if ticker in self.position_manager.positions:
                    pnl = self.position_manager.close_position(ticker, price, current_date)

                    self.trades.append(
                        {
                            "date": current_date,
                            "ticker": ticker,
                            "action": "sell",
                            "quantity": self.position_manager.positions.get(ticker, {}).get(
                                "quantity", 0
                            ),
                            "price": price,
                            "pnl": pnl,
                        }
                    )

    def _execute_exit(self, ticker: str, price: float, current_date: datetime, exit_type: str):
        """Execute position exit"""
        if ticker in self.position_manager.positions:
            position = self.position_manager.positions[ticker]
            pnl = self.position_manager.close_position(ticker, price, current_date)

            self.trades.append(
                {
                    "date": current_date,
                    "ticker": ticker,
                    "action": f"sell_{exit_type}",
                    "quantity": position["quantity"],
                    "price": price,
                    "pnl": pnl,
                }
            )

    def _get_position_snapshot(
        self, date: datetime, current_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get current position snapshot"""
        snapshot = {
            "date": date,
            "num_positions": len(self.position_manager.positions),
            "cash": self.position_manager.cash,
            "portfolio_value": self.position_manager.get_portfolio_value(current_prices),
        }

        # Add position weights
        weights = self.position_manager.get_position_weights(current_prices)
        for ticker, weight in weights.items():
            snapshot[f"weight_{ticker}"] = weight

        return snapshot

    def _calculate_metrics(self, portfolio_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate performance metrics"""
        returns = portfolio_df["returns"]

        # Basic metrics
        total_return = (portfolio_df["value"].iloc[-1] / portfolio_df["value"].iloc[0]) - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1

        # Risk metrics
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (
            (annualized_return - self.config.risk_free_rate) / volatility if volatility > 0 else 0
        )

        # Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        # Win rate
        winning_trades = len([t for t in self.trades if t.get("pnl", 0) > 0])
        total_trades = len([t for t in self.trades if "pnl" in t])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": len(self.trades),
            "final_value": portfolio_df["value"].iloc[-1],
            "initial_value": self.config.initial_capital,
        }

    def _get_benchmark_returns(
        self, price_data: pd.DataFrame, dates: np.ndarray
    ) -> Optional[pd.Series]:
        """Get benchmark returns"""
        if self.config.benchmark not in price_data["symbol"].unique():
            return None

        benchmark_data = price_data[price_data["symbol"] == self.config.benchmark]
        benchmark_data = benchmark_data.set_index("date")["close"]
        benchmark_returns = benchmark_data.pct_change().fillna(0)

        return benchmark_returns[benchmark_returns.index.isin(dates)]
