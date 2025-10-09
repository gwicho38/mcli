"""Trading service for managing portfolios and executing trades"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from mcli.ml.trading.alpaca_client import AlpacaTradingClient, create_trading_client
from mcli.ml.trading.models import (
    TradingAccount, Portfolio, Position, TradingOrder, PortfolioPerformanceSnapshot,
    TradingSignal, OrderStatus, OrderType, OrderSide, PositionSide, PortfolioType,
    TradingAccountCreate, PortfolioCreate, OrderCreate, PortfolioResponse,
    PositionResponse, OrderResponse, TradingSignalResponse
)

logger = logging.getLogger(__name__)


class TradingService:
    """Service for managing trading operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_trading_account(self, user_id: UUID, account_data: TradingAccountCreate) -> TradingAccount:
        """Create a new trading account"""
        try:
            account = TradingAccount(
                user_id=user_id,
                account_name=account_data.account_name,
                account_type=account_data.account_type,
                alpaca_api_key=account_data.alpaca_api_key,
                alpaca_secret_key=account_data.alpaca_secret_key,
                paper_trading=account_data.paper_trading,
                risk_level=account_data.risk_level,
                max_position_size=account_data.max_position_size,
                max_portfolio_risk=account_data.max_portfolio_risk,
            )
            
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            
            logger.info(f"Created trading account {account.id} for user {user_id}")
            return account
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create trading account: {e}")
            raise
    
    def get_trading_account(self, account_id: UUID) -> Optional[TradingAccount]:
        """Get trading account by ID"""
        return self.db.query(TradingAccount).filter(
            TradingAccount.id == account_id,
            TradingAccount.is_active == True
        ).first()
    
    def create_portfolio(self, account_id: UUID, portfolio_data: PortfolioCreate) -> Portfolio:
        """Create a new portfolio"""
        try:
            portfolio = Portfolio(
                trading_account_id=account_id,
                name=portfolio_data.name,
                description=portfolio_data.description,
                initial_capital=Decimal(str(portfolio_data.initial_capital)),
                current_value=Decimal(str(portfolio_data.initial_capital)),
                cash_balance=Decimal(str(portfolio_data.initial_capital)),
            )
            
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)
            
            logger.info(f"Created portfolio {portfolio.id} for account {account_id}")
            return portfolio
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create portfolio: {e}")
            raise
    
    def get_portfolio(self, portfolio_id: UUID) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        return self.db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.is_active == True
        ).first()
    
    def get_user_portfolios(self, user_id: UUID) -> List[Portfolio]:
        """Get all portfolios for a user"""
        return self.db.query(Portfolio).join(TradingAccount).filter(
            TradingAccount.user_id == user_id,
            Portfolio.is_active == True
        ).all()
    
    def create_alpaca_client(self, account: TradingAccount) -> AlpacaTradingClient:
        """Create Alpaca client for trading account"""
        if not account.alpaca_api_key or not account.alpaca_secret_key:
            raise ValueError("Alpaca credentials not configured for this account")
        
        return create_trading_client(
            api_key=account.alpaca_api_key,
            secret_key=account.alpaca_secret_key,
            paper_trading=account.paper_trading
        )
    
    def sync_portfolio_with_alpaca(self, portfolio: Portfolio) -> bool:
        """Sync portfolio data with Alpaca"""
        try:
            account = self.get_trading_account(portfolio.trading_account_id)
            if not account:
                return False
            
            alpaca_client = self.create_alpaca_client(account)
            alpaca_portfolio = alpaca_client.get_portfolio()
            
            # Update portfolio values
            portfolio.current_value = Decimal(str(alpaca_portfolio.portfolio_value))
            portfolio.cash_balance = Decimal(str(alpaca_portfolio.cash))
            portfolio.unrealized_pl = Decimal(str(alpaca_portfolio.unrealized_pl))
            portfolio.realized_pl = Decimal(str(alpaca_portfolio.realized_pl))
            
            # Calculate returns
            if portfolio.initial_capital > 0:
                total_return = portfolio.current_value - portfolio.initial_capital
                portfolio.total_return = float(total_return)
                portfolio.total_return_pct = float(total_return / portfolio.initial_capital * 100)
            
            # Update positions
            self._sync_positions(portfolio, alpaca_portfolio.positions)
            
            # Create performance snapshot
            self._create_performance_snapshot(portfolio)
            
            self.db.commit()
            logger.info(f"Synced portfolio {portfolio.id} with Alpaca")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to sync portfolio with Alpaca: {e}")
            return False
    
    def _sync_positions(self, portfolio: Portfolio, alpaca_positions: List):
        """Sync positions with Alpaca data"""
        # Clear existing positions
        self.db.query(Position).filter(Position.portfolio_id == portfolio.id).delete()
        
        # Add new positions
        for alpaca_pos in alpaca_positions:
            position = Position(
                portfolio_id=portfolio.id,
                symbol=alpaca_pos.symbol,
                quantity=alpaca_pos.quantity,
                side=PositionSide.LONG if alpaca_pos.quantity > 0 else PositionSide.SHORT,
                average_price=Decimal(str(alpaca_pos.cost_basis / alpaca_pos.quantity)),
                current_price=Decimal(str(alpaca_pos.current_price)),
                market_value=Decimal(str(alpaca_pos.market_value)),
                cost_basis=Decimal(str(alpaca_pos.cost_basis)),
                unrealized_pnl=Decimal(str(alpaca_pos.unrealized_pl)),
                unrealized_pnl_pct=float(alpaca_pos.unrealized_plpc),
                position_size_pct=float(alpaca_pos.market_value / portfolio.current_value * 100),
                weight=float(alpaca_pos.market_value / portfolio.current_value),
            )
            self.db.add(position)
    
    def _create_performance_snapshot(self, portfolio: Portfolio):
        """Create daily performance snapshot"""
        snapshot = PortfolioPerformanceSnapshot(
            portfolio_id=portfolio.id,
            snapshot_date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            portfolio_value=portfolio.current_value,
            cash_balance=portfolio.cash_balance,
            daily_return=portfolio.daily_return,
            daily_return_pct=portfolio.daily_return_pct,
            total_return=Decimal(str(portfolio.total_return)),
            total_return_pct=portfolio.total_return_pct,
            volatility=portfolio.volatility,
            sharpe_ratio=portfolio.sharpe_ratio,
            max_drawdown=portfolio.max_drawdown,
            positions_data=self._get_positions_data(portfolio.id),
        )
        self.db.add(snapshot)
    
    def _get_positions_data(self, portfolio_id: UUID) -> Dict:
        """Get positions data for snapshot"""
        positions = self.db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        return {
            pos.symbol: {
                "quantity": pos.quantity,
                "side": pos.side.value,
                "average_price": float(pos.average_price),
                "current_price": float(pos.current_price),
                "market_value": float(pos.market_value),
                "unrealized_pnl": float(pos.unrealized_pnl),
                "weight": pos.weight,
            }
            for pos in positions
        }
    
    def place_order(self, portfolio_id: UUID, order_data: OrderCreate, check_risk: bool = True) -> TradingOrder:
        """Place a trading order"""
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                raise ValueError("Portfolio not found")
            
            account = self.get_trading_account(portfolio.trading_account_id)
            if not account:
                raise ValueError("Trading account not found")
            
            # Check risk limits if enabled
            if check_risk:
                from mcli.ml.trading.risk_management import RiskManager
                risk_manager = RiskManager(self)
                
                order_dict = {
                    "symbol": order_data.symbol,
                    "quantity": order_data.quantity,
                    "side": order_data.side.value,
                }
                
                risk_ok, warnings = risk_manager.check_risk_limits(portfolio_id, order_dict)
                if not risk_ok:
                    raise ValueError(f"Order violates risk limits: {'; '.join(warnings)}")
            
            # Create order record
            order = TradingOrder(
                trading_account_id=account.id,
                portfolio_id=portfolio.id,
                symbol=order_data.symbol,
                side=order_data.side,
                order_type=order_data.order_type,
                quantity=order_data.quantity,
                limit_price=Decimal(str(order_data.limit_price)) if order_data.limit_price else None,
                stop_price=Decimal(str(order_data.stop_price)) if order_data.stop_price else None,
                remaining_quantity=order_data.quantity,
                time_in_force=order_data.time_in_force,
                extended_hours=order_data.extended_hours,
            )
            
            self.db.add(order)
            self.db.flush()  # Get the ID
            
            # Place order with Alpaca if account has credentials
            if account.alpaca_api_key and account.alpaca_secret_key:
                alpaca_client = self.create_alpaca_client(account)
                
                if order_data.order_type == OrderType.MARKET:
                    alpaca_order = alpaca_client.place_market_order(
                        symbol=order_data.symbol,
                        quantity=order_data.quantity,
                        side=order_data.side.value,
                        time_in_force=order_data.time_in_force
                    )
                elif order_data.order_type == OrderType.LIMIT:
                    alpaca_order = alpaca_client.place_limit_order(
                        symbol=order_data.symbol,
                        quantity=order_data.quantity,
                        side=order_data.side.value,
                        limit_price=order_data.limit_price,
                        time_in_force=order_data.time_in_force
                    )
                else:
                    raise ValueError(f"Unsupported order type: {order_data.order_type}")
                
                order.alpaca_order_id = alpaca_order.id
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(order)
            
            logger.info(f"Placed order {order.id} for portfolio {portfolio_id}")
            return order
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to place order: {e}")
            raise
    
    def get_portfolio_positions(self, portfolio_id: UUID) -> List[PositionResponse]:
        """Get all positions for a portfolio"""
        positions = self.db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        return [
            PositionResponse(
                id=pos.id,
                symbol=pos.symbol,
                quantity=pos.quantity,
                side=pos.side,
                average_price=float(pos.average_price),
                current_price=float(pos.current_price),
                market_value=float(pos.market_value),
                cost_basis=float(pos.cost_basis),
                unrealized_pnl=float(pos.unrealized_pnl),
                unrealized_pnl_pct=pos.unrealized_pnl_pct,
                realized_pnl=float(pos.realized_pnl),
                position_size_pct=pos.position_size_pct,
                weight=pos.weight,
                created_at=pos.created_at,
                updated_at=pos.updated_at,
            )
            for pos in positions
        ]
    
    def get_portfolio_orders(self, portfolio_id: UUID, status: Optional[OrderStatus] = None) -> List[OrderResponse]:
        """Get orders for a portfolio"""
        query = self.db.query(TradingOrder).filter(TradingOrder.portfolio_id == portfolio_id)
        if status:
            query = query.filter(TradingOrder.status == status)
        
        orders = query.order_by(desc(TradingOrder.created_at)).all()
        return [
            OrderResponse(
                id=order.id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                limit_price=float(order.limit_price) if order.limit_price else None,
                stop_price=float(order.stop_price) if order.stop_price else None,
                average_fill_price=float(order.average_fill_price) if order.average_fill_price else None,
                status=order.status,
                filled_quantity=order.filled_quantity,
                remaining_quantity=order.remaining_quantity,
                created_at=order.created_at,
                submitted_at=order.submitted_at,
                filled_at=order.filled_at,
                cancelled_at=order.cancelled_at,
                time_in_force=order.time_in_force,
                extended_hours=order.extended_hours,
                alpaca_order_id=order.alpaca_order_id,
            )
            for order in orders
        ]
    
    def get_portfolio_performance(self, portfolio_id: UUID, days: int = 30) -> pd.DataFrame:
        """Get portfolio performance history"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        snapshots = self.db.query(PortfolioPerformanceSnapshot).filter(
            PortfolioPerformanceSnapshot.portfolio_id == portfolio_id,
            PortfolioPerformanceSnapshot.snapshot_date >= start_date
        ).order_by(PortfolioPerformanceSnapshot.snapshot_date).all()
        
        data = []
        for snapshot in snapshots:
            data.append({
                "date": snapshot.snapshot_date,
                "portfolio_value": float(snapshot.portfolio_value),
                "cash_balance": float(snapshot.cash_balance),
                "daily_return": float(snapshot.daily_return),
                "daily_return_pct": snapshot.daily_return_pct,
                "total_return": float(snapshot.total_return),
                "total_return_pct": snapshot.total_return_pct,
                "volatility": snapshot.volatility,
                "sharpe_ratio": snapshot.sharpe_ratio,
                "max_drawdown": snapshot.max_drawdown,
            })
        
        return pd.DataFrame(data)
    
    def create_trading_signal(
        self,
        portfolio_id: UUID,
        symbol: str,
        signal_type: str,
        confidence: float,
        strength: float,
        model_id: Optional[str] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        position_size: Optional[float] = None,
        expires_hours: int = 24
    ) -> TradingSignal:
        """Create a trading signal"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours) if expires_hours > 0 else None
            
            signal = TradingSignal(
                portfolio_id=portfolio_id,
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                strength=strength,
                model_id=model_id,
                target_price=Decimal(str(target_price)) if target_price else None,
                stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                take_profit=Decimal(str(take_profit)) if take_profit else None,
                position_size=position_size,
                expires_at=expires_at,
            )
            
            self.db.add(signal)
            self.db.commit()
            self.db.refresh(signal)
            
            logger.info(f"Created trading signal {signal.id} for {symbol}")
            return signal
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create trading signal: {e}")
            raise
    
    def get_active_signals(self, portfolio_id: UUID) -> List[TradingSignalResponse]:
        """Get active trading signals for a portfolio"""
        signals = self.db.query(TradingSignal).filter(
            TradingSignal.portfolio_id == portfolio_id,
            TradingSignal.is_active == True,
            TradingSignal.expires_at > datetime.utcnow()
        ).order_by(desc(TradingSignal.created_at)).all()
        
        return [
            TradingSignalResponse(
                id=signal.id,
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                strength=signal.strength,
                model_id=signal.model_id,
                model_version=signal.model_version,
                target_price=float(signal.target_price) if signal.target_price else None,
                stop_loss=float(signal.stop_loss) if signal.stop_loss else None,
                take_profit=float(signal.take_profit) if signal.take_profit else None,
                position_size=signal.position_size,
                created_at=signal.created_at,
                expires_at=signal.expires_at,
                is_active=signal.is_active,
            )
            for signal in signals
        ]
    
    def calculate_portfolio_metrics(self, portfolio_id: UUID) -> Dict:
        """Calculate portfolio performance metrics"""
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            return {}
        
        # Get performance history
        performance_df = self.get_portfolio_performance(portfolio_id, days=90)
        
        if performance_df.empty:
            return {
                "total_return": 0.0,
                "total_return_pct": 0.0,
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "current_value": float(portfolio.current_value),
                "cash_balance": float(portfolio.cash_balance),
            }
        
        # Calculate metrics
        returns = performance_df["daily_return_pct"].dropna()
        
        total_return = performance_df["total_return"].iloc[-1] if not performance_df.empty else 0
        total_return_pct = performance_df["total_return_pct"].iloc[-1] if not performance_df.empty else 0
        volatility = returns.std() * (252 ** 0.5) if len(returns) > 1 else 0  # Annualized
        sharpe_ratio = (returns.mean() * 252) / volatility if volatility > 0 else 0  # Annualized
        max_drawdown = performance_df["max_drawdown"].max() if not performance_df.empty else 0
        
        return {
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "current_value": float(portfolio.current_value),
            "cash_balance": float(portfolio.cash_balance),
            "num_positions": len(self.get_portfolio_positions(portfolio_id)),
        }