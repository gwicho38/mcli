"""Paper trading implementation for testing portfolios without real money"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from mcli.ml.trading.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
    PositionSide,
    TradingOrder,
)
from mcli.ml.trading.trading_service import TradingService

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """Paper trading engine for testing strategies without real money"""

    def __init__(self, trading_service: TradingService):
        self.trading_service = trading_service
        self.db = trading_service.db

    def execute_paper_order(self, order: TradingOrder) -> bool:
        """Execute a paper trade order"""
        try:
            # Get current market price
            current_price = self._get_current_price(order.symbol)
            if current_price is None:
                logger.error(f"Could not get current price for {order.symbol}")
                return False

            # Calculate execution details
            if order.order_type == OrderType.MARKET:
                execution_price = current_price
            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and order.limit_price >= current_price:
                    execution_price = current_price
                elif order.side == OrderSide.SELL and order.limit_price <= current_price:
                    execution_price = current_price
                else:
                    # Order not executed
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = datetime.utcnow()
                    self.db.commit()
                    return False
            else:
                logger.error(f"Unsupported order type for paper trading: {order.order_type}")
                return False

            # Execute the order
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.utcnow()
            order.filled_quantity = order.quantity
            order.remaining_quantity = 0
            order.average_fill_price = Decimal(str(execution_price))

            # Update portfolio and positions
            self._update_portfolio_positions(order, execution_price)

            self.db.commit()
            logger.info(
                f"Paper trade executed: {order.symbol} {order.side.value} {order.quantity} @ ${execution_price}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to execute paper order: {e}")
            self.db.rollback()
            return False

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if not data.empty:
                return float(data["Close"].iloc[-1])
            return None
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    def _update_portfolio_positions(self, order: TradingOrder, execution_price: float):
        """Update portfolio positions after order execution"""
        try:
            portfolio = self.trading_service.get_portfolio(order.portfolio_id)
            if not portfolio:
                return

            # Calculate trade value
            trade_value = execution_price * order.quantity

            if order.side == OrderSide.BUY:
                # Buying shares
                portfolio.cash_balance -= Decimal(str(trade_value))

                # Update or create position
                position = (
                    self.db.query(Position)
                    .filter(
                        Position.portfolio_id == order.portfolio_id, Position.symbol == order.symbol
                    )
                    .first()
                )

                if position:
                    # Update existing position
                    total_quantity = position.quantity + order.quantity
                    total_cost = (position.cost_basis * position.quantity) + trade_value
                    new_avg_price = total_cost / total_quantity

                    position.quantity = total_quantity
                    position.average_price = new_avg_price
                    position.cost_basis = total_cost
                    position.current_price = Decimal(str(execution_price))
                    position.market_value = total_quantity * execution_price
                    position.unrealized_pnl = position.market_value - total_cost
                    position.unrealized_pnl_pct = float(position.unrealized_pnl / total_cost * 100)
                else:
                    # Create new position
                    position = Position(
                        portfolio_id=order.portfolio_id,
                        symbol=order.symbol,
                        quantity=order.quantity,
                        side=PositionSide.LONG,
                        average_price=Decimal(str(execution_price)),
                        current_price=Decimal(str(execution_price)),
                        market_value=Decimal(str(trade_value)),
                        cost_basis=Decimal(str(trade_value)),
                        unrealized_pnl=Decimal("0"),
                        unrealized_pnl_pct=0.0,
                        realized_pnl=Decimal("0"),
                        position_size_pct=0.0,
                        weight=0.0,
                    )
                    self.db.add(position)

            else:  # SELL
                # Selling shares
                portfolio.cash_balance += Decimal(str(trade_value))

                # Update position
                position = (
                    self.db.query(Position)
                    .filter(
                        Position.portfolio_id == order.portfolio_id, Position.symbol == order.symbol
                    )
                    .first()
                )

                if position and position.quantity >= order.quantity:
                    # Calculate realized P&L
                    cost_basis = position.cost_basis * (order.quantity / position.quantity)
                    realized_pnl = trade_value - float(cost_basis)

                    # Update position
                    position.quantity -= order.quantity
                    position.cost_basis -= cost_basis
                    position.realized_pnl += Decimal(str(realized_pnl))

                    if position.quantity == 0:
                        # Remove position if fully sold
                        self.db.delete(position)
                    else:
                        # Update remaining position
                        position.current_price = Decimal(str(execution_price))
                        position.market_value = position.quantity * execution_price
                        position.unrealized_pnl = position.market_value - position.cost_basis
                        if position.cost_basis > 0:
                            position.unrealized_pnl_pct = float(
                                position.unrealized_pnl / position.cost_basis * 100
                            )

            # Update portfolio value
            self._update_portfolio_value(portfolio)

        except Exception as e:
            logger.error(f"Failed to update portfolio positions: {e}")
            raise

    def _update_portfolio_value(self, portfolio: Portfolio):
        """Update portfolio value and metrics"""
        try:
            # Get all positions
            positions = self.db.query(Position).filter(Position.portfolio_id == portfolio.id).all()

            # Calculate total market value
            total_market_value = sum(float(pos.market_value) for pos in positions)
            portfolio.current_value = Decimal(
                str(total_market_value + float(portfolio.cash_balance))
            )

            # Calculate returns
            if portfolio.initial_capital > 0:
                total_return = portfolio.current_value - portfolio.initial_capital
                portfolio.total_return = float(total_return)
                portfolio.total_return_pct = float(total_return / portfolio.initial_capital * 100)

            # Update position weights
            for position in positions:
                if portfolio.current_value > 0:
                    position.weight = float(position.market_value / portfolio.current_value)
                    position.position_size_pct = position.weight * 100

        except Exception as e:
            logger.error(f"Failed to update portfolio value: {e}")
            raise

    def simulate_market_movement(self, portfolio_id: UUID, days: int = 1):
        """Simulate market movement for paper trading"""
        try:
            portfolio = self.trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                return

            positions = self.db.query(Position).filter(Position.portfolio_id == portfolio_id).all()

            for position in positions:
                # Get historical data for the symbol
                ticker = yf.Ticker(position.symbol)
                end_date = datetime.now()
                start_date = end_date - timedelta(
                    days=days + 5
                )  # Get extra days for weekend handling

                data = ticker.history(start=start_date, end=end_date)
                if not data.empty:
                    # Get the most recent price
                    new_price = float(data["Close"].iloc[-1])

                    # Update position
                    position.current_price = Decimal(str(new_price))
                    position.market_value = position.quantity * new_price
                    position.unrealized_pnl = position.market_value - position.cost_basis
                    if position.cost_basis > 0:
                        position.unrealized_pnl_pct = float(
                            position.unrealized_pnl / position.cost_basis * 100
                        )

            # Update portfolio value
            self._update_portfolio_value(portfolio)
            self.db.commit()

            logger.info(f"Simulated market movement for portfolio {portfolio_id}")

        except Exception as e:
            logger.error(f"Failed to simulate market movement: {e}")
            self.db.rollback()

    def create_test_portfolio(
        self, user_id: UUID, name: str = "Test Portfolio", initial_capital: float = 100000.0
    ) -> Portfolio:
        """Create a test portfolio for paper trading"""
        try:
            # Create trading account
            from mcli.ml.trading.models import TradingAccountCreate

            account_data = TradingAccountCreate(
                account_name="Test Account", account_type="test", paper_trading=True
            )
            account = self.trading_service.create_trading_account(user_id, account_data)

            # Create portfolio
            portfolio_data = PortfolioCreate(
                name=name,
                description="Test portfolio for paper trading",
                initial_capital=initial_capital,
            )
            portfolio = self.trading_service.create_portfolio(account.id, portfolio_data)

            logger.info(f"Created test portfolio {portfolio.id} for user {user_id}")
            return portfolio

        except Exception as e:
            logger.error(f"Failed to create test portfolio: {e}")
            raise

    def run_backtest(
        self,
        portfolio_id: UUID,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
    ) -> Dict:
        """Run a backtest on historical data"""
        try:
            portfolio = self.trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                raise ValueError("Portfolio not found")

            # Reset portfolio to initial state
            portfolio.current_value = Decimal(str(initial_capital))
            portfolio.cash_balance = Decimal(str(initial_capital))
            portfolio.total_return = 0.0
            portfolio.total_return_pct = 0.0

            # Clear existing positions
            self.db.query(Position).filter(Position.portfolio_id == portfolio_id).delete()

            # Get historical data for the period
            date_range = pd.date_range(start=start_date, end=end_date, freq="D")

            # This is a simplified backtest - in practice you'd want to:
            # 1. Get historical signals
            # 2. Execute trades based on signals
            # 3. Track performance over time

            backtest_results = {
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "final_value": float(portfolio.current_value),
                "total_return": float(portfolio.total_return),
                "total_return_pct": portfolio.total_return_pct,
                "trades_executed": 0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
            }

            self.db.commit()
            logger.info(f"Backtest completed for portfolio {portfolio_id}")
            return backtest_results

        except Exception as e:
            logger.error(f"Failed to run backtest: {e}")
            self.db.rollback()
            raise


def create_paper_trading_engine(db_session: Session) -> PaperTradingEngine:
    """Create a paper trading engine"""
    trading_service = TradingService(db_session)
    return PaperTradingEngine(trading_service)
