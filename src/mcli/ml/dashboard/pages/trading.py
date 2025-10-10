"""Trading dashboard page for portfolio management and trade execution"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Suppress Streamlit warnings when used outside runtime context
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
warnings.filterwarnings("ignore", message=".*No runtime found.*")
warnings.filterwarnings("ignore", message=".*Session state does not function.*")
warnings.filterwarnings("ignore", message=".*to view this Streamlit app.*")

# Try to import trading dependencies with fallbacks
try:
    from sqlalchemy.orm import Session
    from mcli.ml.trading.trading_service import TradingService
    from mcli.ml.trading.models import (
        TradingAccountCreate, PortfolioCreate, OrderCreate, PortfolioType, RiskLevel,
        OrderType, OrderSide, TradingSignalResponse
    )
    from mcli.ml.database.session import get_session
    HAS_TRADING_DEPS = True
except ImportError as e:
    st.error(f"Trading dependencies not available: {e}")
    HAS_TRADING_DEPS = False
    # Create dummy classes for fallback
    class TradingService:
        def __init__(self, db):
            pass
    class TradingAccountCreate:
        def __init__(self, **kwargs):
            pass
    class PortfolioCreate:
        def __init__(self, **kwargs):
            pass
    class OrderCreate:
        def __init__(self, **kwargs):
            pass
    class PortfolioType:
        TEST = "test"
        PAPER = "paper"
        LIVE = "live"
    class RiskLevel:
        CONSERVATIVE = "conservative"
        MODERATE = "moderate"
        AGGRESSIVE = "aggressive"
    class OrderType:
        MARKET = "market"
        LIMIT = "limit"
    class OrderSide:
        BUY = "buy"
        SELL = "sell"
    class TradingSignalResponse:
        def __init__(self, **kwargs):
            pass
    def get_session():
        return None

logger = logging.getLogger(__name__)


def show_trading_dashboard():
    """Main trading dashboard page"""
    st.title("📈 Trading Dashboard")
    st.markdown("Manage your portfolios and execute trades based on politician trading insights")
    
    # Add a simple test to ensure the page is rendering
    st.info("📋 Page loaded successfully - Trading Dashboard functionality is available")

    # Check if trading dependencies are available
    if not HAS_TRADING_DEPS:
        st.error("⚠️ Trading functionality is not available. Please ensure all trading dependencies are installed.")
        st.info("This page requires the trading service and database models to be properly configured.")

        with st.expander("📋 Required Dependencies"):
            st.markdown("""
            The trading page requires the following:

            1. **Trading Module** (`mcli.ml.trading`)
            2. **Database Connection** (PostgreSQL/SQLite)
            3. **Alpaca API** (for live trading - optional for testing)

            **To fix this:**
            ```bash
            # Install trading dependencies
            pip install alpaca-py sqlalchemy

            # Configure database in .env
            DATABASE_URL=postgresql://user:pass@localhost/dbname
            ```
            """)
        return

    # Initialize session state
    if "trading_page" not in st.session_state:
        st.session_state.trading_page = "overview"

    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🎯 Trading Navigation")
        page = st.radio(
            "Select Page",
            ["Overview", "Portfolios", "Trading", "Performance", "Signals", "Settings"],
            key="trading_nav"
        )

    # Route to appropriate page
    try:
        if page == "Overview":
            show_trading_overview()
        elif page == "Portfolios":
            show_portfolios_page()
        elif page == "Trading":
            show_trading_page()
        elif page == "Performance":
            show_performance_page()
        elif page == "Signals":
            show_signals_page()
        elif page == "Settings":
            show_settings_page()
    except Exception as e:
        st.error(f"Error loading trading page: {e}")
        logger.error(f"Trading page error: {e}", exc_info=True)
        st.info("Please check the logs for more details and ensure the database is properly configured.")

        with st.expander("🔍 Error Details"):
            st.code(str(e))


def show_trading_overview():
    """Show trading overview with key metrics"""
    st.header("📊 Trading Overview")

    try:
        if not HAS_TRADING_DEPS:
            st.warning("Trading service not available. Please check your configuration.")
            return

        # Check database connection
        try:
            db_session = get_session()
            if db_session is None:
                st.error("Database connection not available. Please check your database configuration.")
                with st.expander("📋 Database Configuration Help"):
                    st.markdown("""
                    **Database Setup:**

                    1. Create a `.env` file with:
                    ```
                    DATABASE_URL=sqlite:///ml_system.db
                    ```

                    2. Or for PostgreSQL:
                    ```
                    DATABASE_URL=postgresql://user:password@localhost/trading_db
                    ```

                    3. Initialize the database:
                    ```bash
                    python -m mcli.ml.database.migrations
                    ```
                    """)
                return
        except Exception as e:
            st.error(f"Failed to connect to database: {e}")
            logger.error(f"Database connection error: {e}", exc_info=True)
            return

        with db_session as db:
            trading_service = TradingService(db)
            
            # Get user portfolios (assuming user_id from session)
            user_id = st.session_state.get("user_id", "default_user")
            portfolios = trading_service.get_user_portfolios(UUID(user_id) if user_id != "default_user" else None)
            
            if not portfolios:
                st.info("No portfolios found. Create your first portfolio to get started!")
                return
            
            # Overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_value = sum(float(p.current_value) for p in portfolios)
            total_return = sum(p.total_return for p in portfolios)
            total_return_pct = (total_return / sum(float(p.initial_capital) for p in portfolios)) * 100 if portfolios else 0
            
            with col1:
                st.metric("Total Portfolio Value", f"${total_value:,.2f}")
            with col2:
                st.metric("Total Return", f"${total_return:,.2f}")
            with col3:
                st.metric("Total Return %", f"{total_return_pct:.2f}%")
            with col4:
                active_positions = sum(len(trading_service.get_portfolio_positions(p.id)) for p in portfolios)
                st.metric("Active Positions", active_positions)
            
            # Portfolio performance chart
            st.subheader("Portfolio Performance")
            
            # Get performance data for all portfolios
            performance_data = []
            for portfolio in portfolios:
                perf_df = trading_service.get_portfolio_performance(portfolio.id, days=30)
                if not perf_df.empty:
                    perf_df["portfolio_name"] = portfolio.name
                    performance_data.append(perf_df)
            
            if performance_data:
                combined_df = pd.concat(performance_data, ignore_index=True)
                
                fig = px.line(
                    combined_df,
                    x="date",
                    y="total_return_pct",
                    color="portfolio_name",
                    title="Portfolio Performance Over Time",
                    labels={"total_return_pct": "Total Return (%)", "date": "Date"}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)
            else:
                st.info("No performance data available yet. Start trading to see your performance!")
            
            # Recent activity
            st.subheader("Recent Activity")
            
            # Get recent orders across all portfolios
            recent_orders = []
            for portfolio in portfolios:
                orders = trading_service.get_portfolio_orders(portfolio.id)
                for order in orders[:5]:  # Last 5 orders per portfolio
                    recent_orders.append({
                        "portfolio": portfolio.name,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "quantity": order.quantity,
                        "status": order.status.value,
                        "created_at": order.created_at,
                    })
            
            if recent_orders:
                orders_df = pd.DataFrame(recent_orders)
                orders_df = orders_df.sort_values("created_at", ascending=False).head(10)
                st.dataframe(orders_df, use_container_width=True)
            else:
                st.info("No recent trading activity")
                
    except Exception as e:
        st.error(f"Error loading trading overview: {e}")
        logger.error(f"Trading overview error: {e}")


def show_portfolios_page():
    """Show portfolios management page"""
    st.header("💼 Portfolio Management")
    
    try:
        with get_session() as db:
            trading_service = TradingService(db)
            
            # Create new portfolio section
            with st.expander("➕ Create New Portfolio", expanded=False):
                with st.form("create_portfolio"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        portfolio_name = st.text_input("Portfolio Name", placeholder="My Trading Portfolio")
                        description = st.text_area("Description", placeholder="Optional description")
                    
                    with col2:
                        initial_capital = st.number_input(
                            "Initial Capital ($)", 
                            min_value=1000, 
                            value=100000, 
                            step=10000
                        )
                        account_type = st.selectbox(
                            "Account Type",
                            [PortfolioType.TEST, PortfolioType.PAPER, PortfolioType.LIVE]
                        )
                    
                    if st.form_submit_button("Create Portfolio", type="primary"):
                        if portfolio_name:
                            try:
                                # Create trading account first if needed
                                user_id = st.session_state.get("user_id", "default_user")
                                account_id = UUID(user_id) if user_id != "default_user" else None
                                
                                if not account_id:
                                    # Create default account
                                    account_data = TradingAccountCreate(
                                        account_name="Default Account",
                                        account_type=account_type,
                                        paper_trading=True
                                    )
                                    account = trading_service.create_trading_account(UUID("00000000-0000-0000-0000-000000000000"), account_data)
                                    account_id = account.id
                                
                                # Create portfolio
                                portfolio_data = PortfolioCreate(
                                    name=portfolio_name,
                                    description=description,
                                    initial_capital=initial_capital
                                )
                                
                                portfolio = trading_service.create_portfolio(account_id, portfolio_data)
                                st.success(f"Portfolio '{portfolio_name}' created successfully!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Failed to create portfolio: {e}")
                        else:
                            st.error("Please enter a portfolio name")
            
            # Display existing portfolios
            user_id = st.session_state.get("user_id", "default_user")
            portfolios = trading_service.get_user_portfolios(UUID(user_id) if user_id != "default_user" else None)
            
            if not portfolios:
                st.info("No portfolios found. Create your first portfolio above!")
                return
            
            # Portfolio cards
            for portfolio in portfolios:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"### {portfolio.name}")
                        if portfolio.description:
                            st.markdown(f"*{portfolio.description}*")
                    
                    with col2:
                        st.metric("Value", f"${float(portfolio.current_value):,.0f}")
                    
                    with col3:
                        st.metric("Return", f"{portfolio.total_return_pct:.2f}%")
                    
                    with col4:
                        positions = trading_service.get_portfolio_positions(portfolio.id)
                        st.metric("Positions", len(positions))
                    
                    # Portfolio actions
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"View Details", key=f"view_{portfolio.id}"):
                            st.session_state.selected_portfolio = portfolio.id
                            st.session_state.trading_page = "trading"
                    
                    with col2:
                        if st.button(f"Sync with Alpaca", key=f"sync_{portfolio.id}"):
                            with st.spinner("Syncing with Alpaca..."):
                                success = trading_service.sync_portfolio_with_alpaca(portfolio)
                                if success:
                                    st.success("Portfolio synced successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to sync portfolio")
                    
                    with col3:
                        if st.button(f"Performance", key=f"perf_{portfolio.id}"):
                            st.session_state.selected_portfolio = portfolio.id
                            st.session_state.trading_page = "performance"
                    
                    st.divider()
                    
    except Exception as e:
        st.error(f"Error loading portfolios: {e}")
        logger.error(f"Portfolios page error: {e}")


def show_trading_page():
    """Show trading interface page"""
    st.header("🎯 Trading Interface")
    
    try:
        with get_session() as db:
            trading_service = TradingService(db)
            
            # Get selected portfolio
            portfolio_id = st.session_state.get("selected_portfolio")
            if not portfolio_id:
                st.warning("Please select a portfolio from the Portfolios page")
                return
            
            portfolio = trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                st.error("Portfolio not found")
                return
            
            st.markdown(f"**Trading Portfolio:** {portfolio.name}")
            
            # Portfolio summary
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Portfolio Value", f"${float(portfolio.current_value):,.2f}")
            with col2:
                st.metric("Cash Balance", f"${float(portfolio.cash_balance):,.2f}")
            with col3:
                st.metric("Total Return", f"{portfolio.total_return_pct:.2f}%")
            with col4:
                positions = trading_service.get_portfolio_positions(portfolio_id)
                st.metric("Positions", len(positions))
            
            # Trading interface
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📈 Place Order")
                
                with st.form("place_order"):
                    symbol = st.text_input("Symbol", placeholder="AAPL", help="Stock symbol to trade")
                    side = st.selectbox("Side", [OrderSide.BUY, OrderSide.SELL])
                    order_type = st.selectbox("Order Type", [OrderType.MARKET, OrderType.LIMIT])
                    quantity = st.number_input("Quantity", min_value=1, value=1)
                    
                    limit_price = None
                    if order_type == OrderType.LIMIT:
                        limit_price = st.number_input("Limit Price", min_value=0.01, value=100.0, step=0.01)
                    
                    time_in_force = st.selectbox("Time in Force", ["day", "gtc"])
                    extended_hours = st.checkbox("Extended Hours", value=False)
                    
                    if st.form_submit_button("Place Order", type="primary"):
                        if symbol:
                            try:
                                order_data = OrderCreate(
                                    symbol=symbol.upper(),
                                    side=side,
                                    order_type=order_type,
                                    quantity=quantity,
                                    limit_price=limit_price,
                                    time_in_force=time_in_force,
                                    extended_hours=extended_hours
                                )
                                
                                order = trading_service.place_order(portfolio_id, order_data)
                                st.success(f"Order placed successfully! Order ID: {order.id}")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Failed to place order: {e}")
                        else:
                            st.error("Please enter a symbol")
            
            with col2:
                st.subheader("📊 Current Positions")
                
                positions = trading_service.get_portfolio_positions(portfolio_id)
                if positions:
                    positions_data = []
                    for pos in positions:
                        positions_data.append({
                            "Symbol": pos.symbol,
                            "Quantity": pos.quantity,
                            "Side": pos.side.value,
                            "Avg Price": f"${pos.average_price:.2f}",
                            "Current Price": f"${pos.current_price:.2f}",
                            "Market Value": f"${pos.market_value:,.2f}",
                            "P&L": f"${pos.unrealized_pnl:,.2f}",
                            "P&L %": f"{pos.unrealized_pnl_pct:.2f}%",
                            "Weight": f"{pos.weight:.1%}",
                        })
                    
                    positions_df = pd.DataFrame(positions_data)
                    st.dataframe(positions_df, use_container_width=True)
                else:
                    st.info("No positions found")
            
            # Recent orders
            st.subheader("📋 Recent Orders")
            
            orders = trading_service.get_portfolio_orders(portfolio_id)
            if orders:
                orders_data = []
                for order in orders[:10]:  # Last 10 orders
                    orders_data.append({
                        "Symbol": order.symbol,
                        "Side": order.side.value,
                        "Type": order.order_type.value,
                        "Quantity": order.quantity,
                        "Status": order.status.value,
                        "Created": order.created_at.strftime("%Y-%m-%d %H:%M"),
                        "Filled": order.filled_at.strftime("%Y-%m-%d %H:%M") if order.filled_at else "-",
                    })
                
                orders_df = pd.DataFrame(orders_data)
                st.dataframe(orders_df, use_container_width=True)
            else:
                st.info("No orders found")
                
    except Exception as e:
        st.error(f"Error loading trading page: {e}")
        logger.error(f"Trading page error: {e}")


def show_performance_page():
    """Show portfolio performance analytics"""
    st.header("📊 Performance Analytics")
    
    try:
        with get_session() as db:
            trading_service = TradingService(db)
            
            # Get selected portfolio
            portfolio_id = st.session_state.get("selected_portfolio")
            if not portfolio_id:
                st.warning("Please select a portfolio from the Portfolios page")
                return
            
            portfolio = trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                st.error("Portfolio not found")
                return
            
            st.markdown(f"**Performance Analysis for:** {portfolio.name}")
            
            # Performance metrics
            metrics = trading_service.calculate_portfolio_metrics(portfolio_id)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Return", f"${metrics.get('total_return', 0):,.2f}")
            with col2:
                st.metric("Total Return %", f"{metrics.get('total_return_pct', 0):.2f}%")
            with col3:
                st.metric("Volatility", f"{metrics.get('volatility', 0):.2f}%")
            with col4:
                st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
            
            # Performance chart
            st.subheader("Performance Over Time")
            
            performance_df = trading_service.get_portfolio_performance(portfolio_id, days=90)
            
            if not performance_df.empty:
                # Create performance chart
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("Portfolio Value", "Daily Returns"),
                    vertical_spacing=0.1
                )
                
                # Portfolio value
                fig.add_trace(
                    go.Scatter(
                        x=performance_df["date"],
                        y=performance_df["portfolio_value"],
                        mode="lines",
                        name="Portfolio Value",
                        line=dict(color="blue")
                    ),
                    row=1, col=1
                )
                
                # Daily returns
                fig.add_trace(
                    go.Bar(
                        x=performance_df["date"],
                        y=performance_df["daily_return_pct"],
                        name="Daily Return %",
                        marker_color=["green" if x >= 0 else "red" for x in performance_df["daily_return_pct"]]
                    ),
                    row=2, col=1
                )
                
                fig.update_layout(height=600, showlegend=True)
                fig.update_xaxes(title_text="Date", row=2, col=1)
                fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
                fig.update_yaxes(title_text="Daily Return (%)", row=2, col=1)
                
                st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)
            else:
                st.info("No performance data available yet")
            
            # Risk metrics
            st.subheader("Risk Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%")
                st.metric("Current Value", f"${metrics.get('current_value', 0):,.2f}")
            
            with col2:
                st.metric("Cash Balance", f"${metrics.get('cash_balance', 0):,.2f}")
                st.metric("Number of Positions", metrics.get('num_positions', 0))
                
    except Exception as e:
        st.error(f"Error loading performance page: {e}")
        logger.error(f"Performance page error: {e}")


def show_signals_page():
    """Show trading signals page"""
    st.header("🎯 Trading Signals")
    
    try:
        with get_session() as db:
            trading_service = TradingService(db)
            
            # Get selected portfolio
            portfolio_id = st.session_state.get("selected_portfolio")
            if not portfolio_id:
                st.warning("Please select a portfolio from the Portfolios page")
                return
            
            portfolio = trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                st.error("Portfolio not found")
                return
            
            st.markdown(f"**Trading Signals for:** {portfolio.name}")
            
            # Get active signals
            signals = trading_service.get_active_signals(portfolio_id)
            
            if not signals:
                st.info("No active trading signals found")
                return
            
            # Display signals
            for signal in signals:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"### {signal.symbol} - {signal.signal_type.upper()}")
                        st.markdown(f"**Confidence:** {signal.confidence:.2f} | **Strength:** {signal.strength:.2f}")
                        if signal.model_id:
                            st.markdown(f"*Generated by: {signal.model_id}*")
                    
                    with col2:
                        if signal.target_price:
                            st.metric("Target Price", f"${signal.target_price:.2f}")
                    
                    with col3:
                        if signal.stop_loss:
                            st.metric("Stop Loss", f"${signal.stop_loss:.2f}")
                    
                    with col4:
                        if signal.position_size:
                            st.metric("Position Size", f"{signal.position_size:.1%}")
                    
                    # Signal actions
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"Execute Trade", key=f"execute_{signal.id}"):
                            st.info("Trade execution would be implemented here")
                    
                    with col2:
                        if st.button(f"View Details", key=f"details_{signal.id}"):
                            st.info("Signal details would be shown here")
                    
                    with col3:
                        if st.button(f"Dismiss", key=f"dismiss_{signal.id}"):
                            st.info("Signal would be dismissed here")
                    
                    st.divider()
                    
    except Exception as e:
        st.error(f"Error loading signals page: {e}")
        logger.error(f"Signals page error: {e}")


def show_settings_page():
    """Show trading settings page"""
    import os

    st.header("⚙️ Trading Settings")

    st.subheader("Alpaca API Configuration")

    # Check current configuration from environment
    api_key_configured = bool(os.getenv("ALPACA_API_KEY"))
    secret_key_configured = bool(os.getenv("ALPACA_SECRET_KEY"))
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    is_paper = "paper" in base_url.lower()

    # Show current configuration status
    st.info("📝 **Configuration Status**")
    col1, col2, col3 = st.columns(3)

    with col1:
        if api_key_configured:
            st.success("✅ API Key Configured")
            # Show masked version
            api_key_value = os.getenv("ALPACA_API_KEY", "")
            if len(api_key_value) > 8:
                masked_key = api_key_value[:4] + "..." + api_key_value[-4:]
                st.code(masked_key)
        else:
            st.error("❌ API Key Not Set")

    with col2:
        if secret_key_configured:
            st.success("✅ Secret Key Configured")
        else:
            st.error("❌ Secret Key Not Set")

    with col3:
        st.metric("Environment", "Paper Trading" if is_paper else "Live Trading")

    st.markdown("---")

    # Configuration instructions
    with st.expander("🔧 How to Configure Alpaca API Keys"):
        st.markdown("""
        ### Setting up Alpaca API Credentials

        1. **Get your API keys from Alpaca:**
           - Visit [Alpaca Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
           - Go to "Your API Keys" section
           - Generate new API keys if needed

        2. **Add keys to your `.env` file:**
           ```bash
           ALPACA_API_KEY=your_api_key_here
           ALPACA_SECRET_KEY=your_secret_key_here
           ALPACA_BASE_URL=https://paper-api.alpaca.markets  # For paper trading
           ```

        3. **Restart the Streamlit app** to load the new configuration

        **Current Configuration File:** `/Users/lefv/repos/mcli/.env`
        """)

    st.subheader("Risk Management")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Current Max Position Size", "10%")
        st.metric("Current Max Portfolio Risk", "20%")

    with col2:
        st.metric("Active Risk Level", "Moderate")
        st.metric("Paper Trading", "Enabled" if is_paper else "Disabled")
    
    st.subheader("Portfolio Alerts")
    
    alert_types = [
        "Daily performance summary",
        "Large position changes",
        "Risk threshold breaches",
        "Signal generation",
        "Order executions"
    ]
    
    for alert_type in alert_types:
        st.checkbox(alert_type, value=True)


# Module-level execution only when run directly (not when imported)
if __name__ == "__main__":
    show_trading_dashboard()