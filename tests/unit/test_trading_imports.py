"""Unit tests for trading module imports"""

import pytest


def test_trading_module_imports():
    """Test that trading module can be imported without errors"""
    try:
        from mcli.ml.trading import (
            TradingService,
            OrderCreate,
            PortfolioType,
            OrderType,
            OrderSide,
            RiskLevel,
        )
        assert TradingService is not None
        assert OrderCreate is not None
        assert PortfolioType is not None
        assert OrderType is not None
        assert OrderSide is not None
        assert RiskLevel is not None
    except ImportError as e:
        pytest.fail(f"Failed to import trading module: {e}")


def test_trading_enums():
    """Test that trading enums are properly defined"""
    from mcli.ml.trading import PortfolioType, OrderType, OrderSide, RiskLevel

    # Test PortfolioType enum
    assert hasattr(PortfolioType, 'TEST')
    assert hasattr(PortfolioType, 'PAPER')
    assert hasattr(PortfolioType, 'LIVE')

    # Test OrderType enum
    assert hasattr(OrderType, 'MARKET')
    assert hasattr(OrderType, 'LIMIT')

    # Test OrderSide enum
    assert hasattr(OrderSide, 'BUY')
    assert hasattr(OrderSide, 'SELL')

    # Test RiskLevel enum
    assert hasattr(RiskLevel, 'CONSERVATIVE')
    assert hasattr(RiskLevel, 'MODERATE')
    assert hasattr(RiskLevel, 'AGGRESSIVE')


def test_trading_pydantic_models():
    """Test that trading Pydantic models can be instantiated"""
    from mcli.ml.trading import (
        TradingAccountCreate,
        PortfolioCreate,
        OrderCreate,
        PortfolioType,
        RiskLevel,
        OrderType,
        OrderSide,
    )

    # Test TradingAccountCreate
    account = TradingAccountCreate(
        account_name="Test Account",
        account_type=PortfolioType.TEST,
        risk_level=RiskLevel.MODERATE,
    )
    assert account.account_name == "Test Account"
    assert account.account_type == PortfolioType.TEST

    # Test PortfolioCreate
    portfolio = PortfolioCreate(
        name="Test Portfolio",
        description="Test Description",
        initial_capital=100000.0,
    )
    assert portfolio.name == "Test Portfolio"
    assert portfolio.initial_capital == 100000.0

    # Test OrderCreate
    order = OrderCreate(
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
    )
    assert order.symbol == "AAPL"
    assert order.side == OrderSide.BUY
    assert order.quantity == 10


@pytest.mark.skipif(
    True, reason="Requires database connection - integration test"
)
def test_trading_service_initialization():
    """Test that TradingService can be initialized (requires DB)"""
    from mcli.ml.trading import TradingService
    from mcli.ml.database.session import get_session

    with get_session() as db:
        service = TradingService(db)
        assert service is not None


def test_trading_page_imports():
    """Test that trading dashboard page can be imported"""
    try:
        import sys
        import streamlit as st

        # Mock streamlit session state
        class MockSessionState(dict):
            def __getattr__(self, key):
                return self.get(key)
            def __setattr__(self, key, value):
                self[key] = value

        st.session_state = MockSessionState()

        from mcli.ml.dashboard.pages.trading import show_trading_dashboard
        assert show_trading_dashboard is not None
    except ImportError as e:
        pytest.fail(f"Failed to import trading page: {e}")
