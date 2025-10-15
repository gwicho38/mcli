"""Trading and portfolio models for the ML system"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class OrderStatus(Enum):
    """Order status enumeration"""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """Order type enumeration"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    """Order side enumeration"""

    BUY = "buy"
    SELL = "sell"


class PositionSide(Enum):
    """Position side enumeration"""

    LONG = "long"
    SHORT = "short"


class PortfolioType(Enum):
    """Portfolio type enumeration"""

    TEST = "test"
    LIVE = "live"
    PAPER = "paper"


class RiskLevel(Enum):
    """Risk level enumeration"""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


# Database Models
class TradingAccount(Base):
    """Trading account information"""

    __tablename__ = "trading_accounts"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), nullable=False)  # Remove foreign key for now
    account_name = Column(String(100), nullable=False)
    account_type = Column(SQLEnum(PortfolioType), nullable=False, default=PortfolioType.TEST)

    # Alpaca credentials (encrypted)
    alpaca_api_key = Column(String(255), nullable=True)
    alpaca_secret_key = Column(String(255), nullable=True)
    alpaca_base_url = Column(String(255), nullable=True)

    # Account settings
    paper_trading = Column(Boolean, default=True)
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.MODERATE)
    max_position_size = Column(Float, default=0.1)  # Max 10% per position
    max_portfolio_risk = Column(Float, default=0.2)  # Max 20% portfolio risk

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="trading_account")
    orders = relationship("TradingOrder", back_populates="trading_account")


class Portfolio(Base):
    """Portfolio information"""

    __tablename__ = "portfolios"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    trading_account_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("trading_accounts.id"), nullable=False
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Portfolio settings
    initial_capital = Column(Numeric(15, 2), nullable=False, default=100000.00)
    current_value = Column(Numeric(15, 2), nullable=False, default=100000.00)
    cash_balance = Column(Numeric(15, 2), nullable=False, default=100000.00)

    # Performance metrics
    total_return = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    daily_return = Column(Float, default=0.0)
    daily_return_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_duration = Column(Integer, default=0)
    volatility = Column(Float, default=0.0)

    # Risk metrics
    var_95 = Column(Float, default=0.0)  # Value at Risk 95%
    cvar_95 = Column(Float, default=0.0)  # Conditional Value at Risk 95%
    beta = Column(Float, default=1.0)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trading_account = relationship("TradingAccount", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    orders = relationship("TradingOrder", back_populates="portfolio")
    performance_snapshots = relationship("PortfolioPerformanceSnapshot", back_populates="portfolio")


class Position(Base):
    """Individual position in a portfolio"""

    __tablename__ = "positions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id = Column(PostgresUUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(10), nullable=False, index=True)

    # Position details
    quantity = Column(Integer, nullable=False)
    side = Column(SQLEnum(PositionSide), nullable=False)
    average_price = Column(Numeric(10, 4), nullable=False)
    current_price = Column(Numeric(10, 4), nullable=False)

    # Financial metrics
    market_value = Column(Numeric(15, 2), nullable=False)
    cost_basis = Column(Numeric(15, 2), nullable=False)
    unrealized_pnl = Column(Numeric(15, 2), nullable=False, default=0.0)
    unrealized_pnl_pct = Column(Float, nullable=False, default=0.0)
    realized_pnl = Column(Numeric(15, 2), nullable=False, default=0.0)

    # Position sizing
    position_size_pct = Column(Float, nullable=False, default=0.0)  # % of portfolio
    weight = Column(Float, nullable=False, default=0.0)  # Portfolio weight

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    trades = relationship("TradingOrder", back_populates="position")

    # Indexes
    __table_args__ = (Index("idx_position_portfolio_symbol", "portfolio_id", "symbol"),)


class TradingOrder(Base):
    """Trading order information"""

    __tablename__ = "trading_orders"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    trading_account_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("trading_accounts.id"), nullable=False
    )
    portfolio_id = Column(PostgresUUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    position_id = Column(PostgresUUID(as_uuid=True), ForeignKey("positions.id"), nullable=True)

    # Order details
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    quantity = Column(Integer, nullable=False)

    # Pricing
    limit_price = Column(Numeric(10, 4), nullable=True)
    stop_price = Column(Numeric(10, 4), nullable=True)
    average_fill_price = Column(Numeric(10, 4), nullable=True)

    # Status and execution
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    filled_quantity = Column(Integer, nullable=False, default=0)
    remaining_quantity = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Additional info
    time_in_force = Column(String(20), default="day")
    extended_hours = Column(Boolean, default=False)
    client_order_id = Column(String(100), nullable=True)
    alpaca_order_id = Column(String(100), nullable=True, index=True)

    # Relationships
    trading_account = relationship("TradingAccount", back_populates="orders")
    portfolio = relationship("Portfolio", back_populates="orders")
    position = relationship("Position", back_populates="trades")

    # Indexes
    __table_args__ = (
        Index("idx_order_portfolio_status", "portfolio_id", "status"),
        Index("idx_order_symbol_status", "symbol", "status"),
    )


class PortfolioPerformanceSnapshot(Base):
    """Daily portfolio performance snapshots"""

    __tablename__ = "portfolio_performance_snapshots"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id = Column(PostgresUUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)

    # Snapshot data
    snapshot_date = Column(DateTime, nullable=False, index=True)
    portfolio_value = Column(Numeric(15, 2), nullable=False)
    cash_balance = Column(Numeric(15, 2), nullable=False)

    # Daily performance
    daily_return = Column(Numeric(15, 2), nullable=False, default=0.0)
    daily_return_pct = Column(Float, nullable=False, default=0.0)

    # Cumulative performance
    total_return = Column(Numeric(15, 2), nullable=False, default=0.0)
    total_return_pct = Column(Float, nullable=False, default=0.0)

    # Risk metrics
    volatility = Column(Float, nullable=False, default=0.0)
    sharpe_ratio = Column(Float, nullable=False, default=0.0)
    max_drawdown = Column(Float, nullable=False, default=0.0)

    # Position data (JSON)
    positions_data = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="performance_snapshots")

    # Indexes
    __table_args__ = (Index("idx_snapshot_portfolio_date", "portfolio_id", "snapshot_date"),)


class TradingSignal(Base):
    """Trading signals generated by ML models"""

    __tablename__ = "trading_signals"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id = Column(PostgresUUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)

    # Signal details
    symbol = Column(String(10), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # "buy", "sell", "hold"
    confidence = Column(Float, nullable=False)
    strength = Column(Float, nullable=False)  # Signal strength 0-1

    # ML model info
    model_id = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    prediction_id = Column(PostgresUUID(as_uuid=True), nullable=True)

    # Signal parameters
    target_price = Column(Numeric(10, 4), nullable=True)
    stop_loss = Column(Numeric(10, 4), nullable=True)
    take_profit = Column(Numeric(10, 4), nullable=True)
    position_size = Column(Float, nullable=True)  # Suggested position size as % of portfolio

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    portfolio = relationship("Portfolio")

    # Indexes
    __table_args__ = (
        Index("idx_signal_portfolio_symbol", "portfolio_id", "symbol"),
        Index("idx_signal_created_active", "created_at", "is_active"),
    )


# Pydantic Models for API
class TradingAccountCreate(BaseModel):
    """Create trading account request"""

    account_name: str = Field(..., min_length=1, max_length=100)
    account_type: PortfolioType = Field(default=PortfolioType.TEST)
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    paper_trading: bool = Field(default=True)
    risk_level: RiskLevel = Field(default=RiskLevel.MODERATE)
    max_position_size: float = Field(default=0.1, ge=0.01, le=1.0)
    max_portfolio_risk: float = Field(default=0.2, ge=0.01, le=1.0)


class PortfolioCreate(BaseModel):
    """Create portfolio request"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    initial_capital: float = Field(default=100000.0, gt=0)


class OrderCreate(BaseModel):
    """Create order request"""

    symbol: str = Field(..., min_length=1, max_length=10)
    side: OrderSide
    order_type: OrderType
    quantity: int = Field(..., gt=0)
    limit_price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)
    time_in_force: str = Field(default="day")
    extended_hours: bool = Field(default=False)


class PositionResponse(BaseModel):
    """Position response model"""

    id: UUID
    symbol: str
    quantity: int
    side: PositionSide
    average_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    position_size_pct: float
    weight: float
    created_at: datetime
    updated_at: datetime


class OrderResponse(BaseModel):
    """Order response model"""

    id: UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    limit_price: Optional[float]
    stop_price: Optional[float]
    average_fill_price: Optional[float]
    status: OrderStatus
    filled_quantity: int
    remaining_quantity: int
    created_at: datetime
    submitted_at: Optional[datetime]
    filled_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    time_in_force: str
    extended_hours: bool
    alpaca_order_id: Optional[str]


class PortfolioResponse(BaseModel):
    """Portfolio response model"""

    id: UUID
    name: str
    description: Optional[str]
    initial_capital: float
    current_value: float
    cash_balance: float
    total_return: float
    total_return_pct: float
    daily_return: float
    daily_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    positions: List[PositionResponse] = []


class TradingSignalResponse(BaseModel):
    """Trading signal response model"""

    id: UUID
    symbol: str
    signal_type: str
    confidence: float
    strength: float
    model_id: Optional[str]
    model_version: Optional[str]
    target_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size: Optional[float]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
