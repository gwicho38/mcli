"""Database models for ML system"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


# Association tables for many-to-many relationships
portfolio_stocks = Table(
    "portfolio_stocks",
    Base.metadata,
    Column("portfolio_id", UUID(as_uuid=True), ForeignKey("portfolios.id")),
    Column("stock_ticker", String, ForeignKey("stock_data.ticker")),
    Column("weight", Float, nullable=False),
    Column("shares", Integer, default=0),
    Column("entry_price", Float),
    Column("created_at", DateTime, default=datetime.utcnow),
)

experiment_models = Table(
    "experiment_models",
    Base.metadata,
    Column("experiment_id", UUID(as_uuid=True), ForeignKey("experiments.id")),
    Column("model_id", UUID(as_uuid=True), ForeignKey("models.id")),
)


class UserRole(PyEnum):
    """User role enumeration"""

    ADMIN = "admin"
    USER = "user"
    ANALYST = "analyst"
    VIEWER = "viewer"


class ModelStatus(PyEnum):
    """Model status enumeration"""

    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"
    FAILED = "failed"


class TradeType(PyEnum):
    """Trade type enumeration"""

    BUY = "buy"
    SELL = "sell"
    OPTION = "option"


class AlertType(PyEnum):
    """Alert type enumeration"""

    POLITICIAN_TRADE = "politician_trade"
    PRICE_MOVEMENT = "price_movement"
    VOLUME_SPIKE = "volume_spike"
    MODEL_PREDICTION = "model_prediction"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"


class User(Base):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    first_name = Column(String(50))
    last_name = Column(String(50))
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    api_key = Column(String(255), unique=True, index=True)
    api_key_created_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="user")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'", name="valid_email"
        ),
        Index("idx_user_active", "is_active"),
    )

    @validates("email")
    def validate_email(self, key, email):
        """Validate email format"""
        import re

        if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$", email):
            raise ValueError("Invalid email format")
        return email.lower()


class Politician(Base):
    """Politician information"""

    __tablename__ = "politicians"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    party = Column(String(50))
    state = Column(String(2))
    position = Column(String(50))  # Senator, Representative, etc.

    bioguide_id = Column(String(20), unique=True, index=True)
    fec_id = Column(String(20), index=True)

    active = Column(Boolean, default=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    metadata_json = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trades = relationship("Trade", back_populates="politician", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_politician_active", "active"),
        Index("idx_politician_party_state", "party", "state"),
    )


class Trade(Base):
    """Political trading records"""

    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    politician_id = Column(UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False)

    ticker = Column(String(10), nullable=False, index=True)
    trade_type = Column(Enum(TradeType), nullable=False)
    amount_min = Column(Float)
    amount_max = Column(Float)

    disclosure_date = Column(DateTime, nullable=False, index=True)
    trade_date = Column(DateTime, index=True)

    asset_description = Column(Text)
    source = Column(String(50))  # Data source
    source_url = Column(String(500))

    metadata_json = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    politician = relationship("Politician", back_populates="trades")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_trade_ticker_date", "ticker", "disclosure_date"),
        Index("idx_trade_politician_date", "politician_id", "disclosure_date"),
        UniqueConstraint(
            "politician_id", "ticker", "disclosure_date", "trade_type", name="unique_trade"
        ),
    )

    @hybrid_property
    def estimated_amount(self):
        """Get estimated trade amount (midpoint)"""
        if self.amount_min and self.amount_max:
            return (self.amount_min + self.amount_max) / 2
        return self.amount_min or self.amount_max


class StockData(Base):
    """Stock market data"""

    __tablename__ = "stock_data"

    ticker = Column(String(10), primary_key=True)
    company_name = Column(String(200))
    sector = Column(String(50), index=True)
    industry = Column(String(100))

    market_cap = Column(BigInteger)
    shares_outstanding = Column(BigInteger)

    # Current data
    current_price = Column(Float)
    volume = Column(BigInteger)
    avg_volume_30d = Column(BigInteger)

    # Performance metrics
    change_1d = Column(Float)
    change_7d = Column(Float)
    change_30d = Column(Float)
    change_90d = Column(Float)
    change_1y = Column(Float)

    # Technical indicators
    rsi_14 = Column(Float)
    macd = Column(Float)
    bollinger_upper = Column(Float)
    bollinger_lower = Column(Float)

    # Fundamental data
    pe_ratio = Column(Float)
    eps = Column(Float)
    dividend_yield = Column(Float)
    beta = Column(Float)

    metadata_json = Column(JSON, default={})

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    predictions = relationship("Prediction", back_populates="stock")

    # Indexes
    __table_args__ = (
        Index("idx_stock_sector_cap", "sector", "market_cap"),
        Index("idx_stock_updated", "last_updated"),
    )


class Prediction(Base):
    """Model predictions"""

    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    ticker = Column(String(10), ForeignKey("stock_data.ticker"), nullable=False, index=True)

    # Prediction details
    prediction_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    target_date = Column(DateTime, nullable=False)

    predicted_return = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    risk_score = Column(Float)

    # Recommendation
    action = Column(String(10))  # buy, sell, hold
    position_size = Column(Float)  # Recommended position size
    stop_loss = Column(Float)
    take_profit = Column(Float)

    # Feature importance
    feature_importance = Column(JSON)

    # Actual outcomes (for backtesting)
    actual_return = Column(Float)
    outcome_date = Column(DateTime)

    metadata_json = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    model = relationship("Model", back_populates="predictions")
    user = relationship("User", back_populates="predictions")
    stock = relationship("StockData", back_populates="predictions")

    # Indexes
    __table_args__ = (
        Index("idx_prediction_date_ticker", "prediction_date", "ticker"),
        Index("idx_prediction_model_date", "model_id", "prediction_date"),
        Index("idx_prediction_confidence", "confidence_score"),
    )


class Portfolio(Base):
    """User portfolios"""

    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text)

    initial_capital = Column(Float, nullable=False)
    current_value = Column(Float)
    cash_balance = Column(Float)

    # Performance metrics
    total_return = Column(Float)
    annual_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)

    # Risk settings
    max_position_size = Column(Float, default=0.2)  # 20% max per position
    stop_loss_pct = Column(Float, default=0.05)  # 5% stop loss

    is_active = Column(Boolean, default=True)
    is_paper = Column(Boolean, default=True)  # Paper trading vs real

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="portfolios")
    backtest_results = relationship("BacktestResult", back_populates="portfolio")

    # Many-to-many relationship with stocks
    stocks = relationship("StockData", secondary=portfolio_stocks, backref="portfolios")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="unique_user_portfolio"),
        Index("idx_portfolio_active", "is_active"),
    )


class Alert(Base):
    """User alerts and notifications"""

    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(String(10), default="info")  # info, warning, critical

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Related entities
    ticker = Column(String(10), index=True)
    politician_id = Column(UUID(as_uuid=True), ForeignKey("politicians.id"))
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"))

    is_read = Column(Boolean, default=False, index=True)
    is_sent = Column(Boolean, default=False)

    metadata_json = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_at = Column(DateTime)
    sent_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="alerts")

    # Indexes
    __table_args__ = (
        Index("idx_alert_user_unread", "user_id", "is_read"),
        Index("idx_alert_created", "created_at"),
    )


class BacktestResult(Base):
    """Backtesting results"""

    __tablename__ = "backtest_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"))

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Performance metrics
    total_return = Column(Float, nullable=False)
    annual_return = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    calmar_ratio = Column(Float)

    # Risk metrics
    volatility = Column(Float)
    var_95 = Column(Float)  # Value at Risk
    cvar_95 = Column(Float)  # Conditional VaR

    # Trading statistics
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    profit_factor = Column(Float)

    # Detailed results
    equity_curve = Column(JSON)  # Time series of portfolio value
    trade_log = Column(JSON)  # Detailed trade history
    metrics_json = Column(JSON)  # Additional metrics

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    model = relationship("Model", back_populates="backtest_results")
    portfolio = relationship("Portfolio", back_populates="backtest_results")

    # Indexes
    __table_args__ = (
        Index("idx_backtest_model", "model_id"),
        Index("idx_backtest_sharpe", "sharpe_ratio"),
    )


class Experiment(Base):
    """ML experiments tracking"""

    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)

    # MLflow integration
    mlflow_experiment_id = Column(String(50), unique=True, index=True)
    mlflow_run_id = Column(String(50), index=True)

    # Hyperparameters
    hyperparameters = Column(JSON, nullable=False)

    # Metrics
    train_metrics = Column(JSON)
    val_metrics = Column(JSON)
    test_metrics = Column(JSON)

    # Status
    status = Column(String(20), default="running")  # running, completed, failed

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Versioning
    code_version = Column(String(50))  # Git commit hash
    data_version = Column(String(50))  # DVC version

    metadata_json = Column(JSON, default={})

    created_by = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Many-to-many relationship with models
    models = relationship("Model", secondary=experiment_models, back_populates="experiments")

    # Indexes
    __table_args__ = (
        Index("idx_experiment_status", "status"),
        Index("idx_experiment_created", "created_at"),
    )


class Model(Base):
    """ML models registry"""

    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(20), nullable=False)

    model_type = Column(String(50), nullable=False)  # ensemble, lstm, transformer, etc.
    framework = Column(String(20), default="pytorch")  # pytorch, tensorflow, sklearn

    # MLflow integration
    mlflow_model_uri = Column(String(500))
    mlflow_run_id = Column(String(50), index=True)

    # Performance metrics
    train_accuracy = Column(Float)
    val_accuracy = Column(Float)
    test_accuracy = Column(Float)

    train_loss = Column(Float)
    val_loss = Column(Float)
    test_loss = Column(Float)

    # Additional metrics (Bitcoin-style metrics)
    metrics = Column(JSON)  # Can include: rmse, mae, r2, mape, cv_scores, etc.
    hyperparameters = Column(JSON)

    # Cross-validation metrics
    cv_scores = Column(ARRAY(Float))
    cv_mean = Column(Float)
    cv_std = Column(Float)

    # Regression metrics
    train_rmse = Column(Float)
    train_mae = Column(Float)
    train_r2 = Column(Float)
    val_rmse = Column(Float)
    val_mae = Column(Float)
    val_r2 = Column(Float)
    test_rmse = Column(Float)
    test_mae = Column(Float)
    test_r2 = Column(Float)
    mape = Column(Float)

    # Residuals analysis
    residuals_stats = Column(JSON)  # mean, std, normality tests, etc.

    # Model artifacts
    model_path = Column(String(500))
    feature_names = Column(ARRAY(String))
    input_shape = Column(JSON)
    output_shape = Column(JSON)

    # Deployment
    status = Column(Enum(ModelStatus), default=ModelStatus.TRAINING, nullable=False)
    deployed_at = Column(DateTime)
    deployment_endpoint = Column(String(200))

    # Metadata
    description = Column(Text)
    tags = Column(ARRAY(String))

    created_by = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    predictions = relationship("Prediction", back_populates="model")
    backtest_results = relationship("BacktestResult", back_populates="model")
    feature_sets = relationship("FeatureSet", back_populates="model")
    experiments = relationship("Experiment", secondary=experiment_models, back_populates="models")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("name", "version", name="unique_model_version"),
        Index("idx_model_status", "status"),
        Index("idx_model_created", "created_at"),
    )


class FeatureSet(Base):
    """Feature sets for models"""

    __tablename__ = "feature_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)

    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)

    # Feature details
    features = Column(JSON, nullable=False)  # List of feature definitions
    feature_count = Column(Integer, nullable=False)

    # Feature engineering pipeline
    pipeline_config = Column(JSON)
    transformations = Column(JSON)

    # Statistics
    feature_stats = Column(JSON)  # Mean, std, min, max per feature
    correlation_matrix = Column(JSON)

    # Data quality
    missing_values = Column(JSON)
    outlier_detection = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    model = relationship("Model", back_populates="feature_sets")

    # Constraints
    __table_args__ = (
        UniqueConstraint("model_id", "name", "version", name="unique_feature_set"),
        Index("idx_feature_set_model", "model_id"),
    )


class DataVersion(Base):
    """Data versioning for DVC"""

    __tablename__ = "data_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    dataset_name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)

    # DVC details
    dvc_hash = Column(String(100), unique=True, index=True)
    dvc_path = Column(String(500))

    # Dataset info
    row_count = Column(Integer)
    column_count = Column(Integer)
    file_size_bytes = Column(BigInteger)

    # Time range
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Metadata
    description = Column(Text)
    tags = Column(ARRAY(String))
    schema_json = Column(JSON)
    statistics_json = Column(JSON)

    created_by = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint("dataset_name", "version", name="unique_data_version"),
        Index("idx_data_version_created", "created_at"),
    )


# Database events and triggers
@event.listens_for(User, "before_insert")
def generate_api_key(mapper, connection, target):
    """Generate API key for new users"""
    if not target.api_key:
        import secrets

        target.api_key = secrets.token_urlsafe(32)
        target.api_key_created_at = datetime.utcnow()


@event.listens_for(Portfolio, "before_update")
def update_portfolio_metrics(mapper, connection, target):
    """Update portfolio performance metrics"""
    if target.current_value and target.initial_capital:
        target.total_return = (
            (target.current_value - target.initial_capital) / target.initial_capital
        ) * 100


# Create indexes for better query performance
def create_indexes(engine):
    """Create additional database indexes"""
    from sqlalchemy import text

    indexes = [
        # Composite indexes for common queries
        "CREATE INDEX IF NOT EXISTS idx_trade_analysis ON trades(ticker, disclosure_date, politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_prediction_latest ON predictions(ticker, prediction_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_portfolio_performance ON portfolios(user_id, total_return DESC)",
        "CREATE INDEX IF NOT EXISTS idx_alert_priority ON alerts(user_id, is_read, severity, created_at DESC)",
        # Full text search indexes (PostgreSQL specific)
        "CREATE INDEX IF NOT EXISTS idx_politician_name_search ON politicians USING gin(to_tsvector('english', name))",
        "CREATE INDEX IF NOT EXISTS idx_stock_company_search ON stock_data USING gin(to_tsvector('english', company_name))",
    ]

    with engine.connect() as conn:
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                conn.commit()
            except Exception as e:
                print(f"Warning: Could not create index: {e}")
