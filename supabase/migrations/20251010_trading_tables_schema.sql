-- Trading Tables Schema for Supabase
-- Execute this in your Supabase SQL editor to add trading functionality
-- This adds: trading_accounts, portfolios, positions, trading_orders, portfolio_performance_snapshots, trading_signals

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Trading Accounts Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,  -- Nullable for now since we don't have user auth yet
    account_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(20) NOT NULL DEFAULT 'test',  -- test, paper, live

    -- Alpaca credentials (encrypted in production)
    alpaca_api_key VARCHAR(255),
    alpaca_secret_key VARCHAR(255),
    alpaca_base_url VARCHAR(255),

    -- Account settings
    paper_trading BOOLEAN DEFAULT TRUE,
    risk_level VARCHAR(20) DEFAULT 'moderate',  -- conservative, moderate, aggressive
    max_position_size FLOAT DEFAULT 0.1,  -- Max 10% per position
    max_portfolio_risk FLOAT DEFAULT 0.2,  -- Max 20% portfolio risk

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- Portfolios Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trading_account_id UUID NOT NULL REFERENCES trading_accounts(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Portfolio settings
    initial_capital NUMERIC(15, 2) NOT NULL DEFAULT 100000.00,
    current_value NUMERIC(15, 2) NOT NULL DEFAULT 100000.00,
    cash_balance NUMERIC(15, 2) NOT NULL DEFAULT 100000.00,

    -- Performance metrics
    total_return FLOAT DEFAULT 0.0,
    total_return_pct FLOAT DEFAULT 0.0,
    daily_return FLOAT DEFAULT 0.0,
    daily_return_pct FLOAT DEFAULT 0.0,
    sharpe_ratio FLOAT DEFAULT 0.0,
    sortino_ratio FLOAT DEFAULT 0.0,
    max_drawdown FLOAT DEFAULT 0.0,
    max_drawdown_duration INTEGER DEFAULT 0,
    volatility FLOAT DEFAULT 0.0,

    -- Risk metrics
    var_95 FLOAT DEFAULT 0.0,  -- Value at Risk 95%
    cvar_95 FLOAT DEFAULT 0.0,  -- Conditional Value at Risk 95%
    beta FLOAT DEFAULT 1.0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Positions Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,

    -- Position details
    quantity INTEGER NOT NULL,
    side VARCHAR(10) NOT NULL,  -- long, short
    average_price NUMERIC(10, 4) NOT NULL,
    current_price NUMERIC(10, 4) NOT NULL,

    -- Financial metrics
    market_value NUMERIC(15, 2) NOT NULL,
    cost_basis NUMERIC(15, 2) NOT NULL,
    unrealized_pnl NUMERIC(15, 2) NOT NULL DEFAULT 0.0,
    unrealized_pnl_pct FLOAT NOT NULL DEFAULT 0.0,
    realized_pnl NUMERIC(15, 2) NOT NULL DEFAULT 0.0,

    -- Position sizing
    position_size_pct FLOAT NOT NULL DEFAULT 0.0,  -- % of portfolio
    weight FLOAT NOT NULL DEFAULT 0.0,  -- Portfolio weight

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Trading Orders Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trading_account_id UUID NOT NULL REFERENCES trading_accounts(id) ON DELETE CASCADE,
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    position_id UUID REFERENCES positions(id) ON DELETE SET NULL,

    -- Order details
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- buy, sell
    order_type VARCHAR(20) NOT NULL,  -- market, limit, stop, stop_limit, trailing_stop
    quantity INTEGER NOT NULL,

    -- Pricing
    limit_price NUMERIC(10, 4),
    stop_price NUMERIC(10, 4),
    average_fill_price NUMERIC(10, 4),

    -- Status and execution
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, submitted, filled, partially_filled, cancelled, rejected, expired
    filled_quantity INTEGER NOT NULL DEFAULT 0,
    remaining_quantity INTEGER NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    -- Additional info
    time_in_force VARCHAR(20) DEFAULT 'day',
    extended_hours BOOLEAN DEFAULT FALSE,
    client_order_id VARCHAR(100),
    alpaca_order_id VARCHAR(100)
);

-- ============================================================================
-- Portfolio Performance Snapshots Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS portfolio_performance_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,

    -- Snapshot data
    snapshot_date TIMESTAMPTZ NOT NULL,
    portfolio_value NUMERIC(15, 2) NOT NULL,
    cash_balance NUMERIC(15, 2) NOT NULL,

    -- Daily performance
    daily_return NUMERIC(15, 2) NOT NULL DEFAULT 0.0,
    daily_return_pct FLOAT NOT NULL DEFAULT 0.0,

    -- Cumulative performance
    total_return NUMERIC(15, 2) NOT NULL DEFAULT 0.0,
    total_return_pct FLOAT NOT NULL DEFAULT 0.0,

    -- Risk metrics
    volatility FLOAT NOT NULL DEFAULT 0.0,
    sharpe_ratio FLOAT NOT NULL DEFAULT 0.0,
    max_drawdown FLOAT NOT NULL DEFAULT 0.0,

    -- Position data (JSON)
    positions_data JSONB,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Trading Signals Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,

    -- Signal details
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,  -- buy, sell, hold
    confidence FLOAT NOT NULL,
    strength FLOAT NOT NULL,  -- Signal strength 0-1

    -- ML model info
    model_id VARCHAR(100),
    model_version VARCHAR(50),
    prediction_id UUID,

    -- Signal parameters
    target_price NUMERIC(10, 4),
    stop_loss NUMERIC(10, 4),
    take_profit NUMERIC(10, 4),
    position_size FLOAT,  -- Suggested position size as % of portfolio

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_trading_accounts_user ON trading_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_trading_accounts_active ON trading_accounts(is_active);

CREATE INDEX IF NOT EXISTS idx_portfolios_trading_account ON portfolios(trading_account_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_active ON portfolios(is_active);

CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON positions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_portfolio_symbol ON positions(portfolio_id, symbol);

CREATE INDEX IF NOT EXISTS idx_orders_portfolio ON trading_orders(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON trading_orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_alpaca_order_id ON trading_orders(alpaca_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_portfolio_status ON trading_orders(portfolio_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON trading_orders(symbol, status);

CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio ON portfolio_performance_snapshots(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON portfolio_performance_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio_date ON portfolio_performance_snapshots(portfolio_id, snapshot_date);

CREATE INDEX IF NOT EXISTS idx_signals_portfolio ON trading_signals(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_portfolio_symbol ON trading_signals(portfolio_id, symbol);
CREATE INDEX IF NOT EXISTS idx_signals_created_active ON trading_signals(created_at, is_active);

-- ============================================================================
-- Updated at Trigger Function (if not already exists)
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- Apply Updated At Triggers
-- ============================================================================
DROP TRIGGER IF EXISTS update_trading_accounts_updated_at ON trading_accounts;
CREATE TRIGGER update_trading_accounts_updated_at
    BEFORE UPDATE ON trading_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_portfolios_updated_at ON portfolios;
CREATE TRIGGER update_portfolios_updated_at
    BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_positions_updated_at ON positions;
CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Row Level Security (RLS) - Allow anon access for testing
-- ============================================================================
ALTER TABLE trading_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_performance_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;

-- Allow anon users full access for testing purposes
CREATE POLICY "Allow anon full access" ON trading_accounts
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon full access" ON portfolios
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon full access" ON positions
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon full access" ON trading_orders
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon full access" ON portfolio_performance_snapshots
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow anon full access" ON trading_signals
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================================================
-- Grant Permissions
-- ============================================================================
GRANT ALL ON trading_accounts TO anon, authenticated;
GRANT ALL ON portfolios TO anon, authenticated;
GRANT ALL ON positions TO anon, authenticated;
GRANT ALL ON trading_orders TO anon, authenticated;
GRANT ALL ON portfolio_performance_snapshots TO anon, authenticated;
GRANT ALL ON trading_signals TO anon, authenticated;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================
COMMENT ON TABLE trading_accounts IS 'Trading account information with Alpaca integration';
COMMENT ON TABLE portfolios IS 'User portfolios for tracking trading performance';
COMMENT ON TABLE positions IS 'Individual stock positions within portfolios';
COMMENT ON TABLE trading_orders IS 'Trading orders placed through the system';
COMMENT ON TABLE portfolio_performance_snapshots IS 'Daily portfolio performance snapshots for historical tracking';
COMMENT ON TABLE trading_signals IS 'ML-generated trading signals for automated trading';
