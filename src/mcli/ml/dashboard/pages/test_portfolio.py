"""Test portfolio page for paper trading and backtesting"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from sqlalchemy.orm import Session

from mcli.ml.database.session import get_session
from mcli.ml.trading.models import OrderCreate, OrderSide, OrderType
from mcli.ml.trading.paper_trading import create_paper_trading_engine
from mcli.ml.trading.trading_service import TradingService

logger = logging.getLogger(__name__)


def show_test_portfolio():
    """Test portfolio page for paper trading"""
    st.title("🧪 Test Portfolio - Paper Trading")
    st.markdown("Test your trading strategies with paper money before going live")

    # Add a simple test to ensure the page is rendering
    st.info("📋 Page loaded successfully - Test Portfolio functionality is available")

    # Initialize session state
    if "test_portfolio_id" not in st.session_state:
        st.session_state.test_portfolio_id = None

    try:
        # Try to get database session
        try:
            session_context = get_session()
            db = session_context.__enter__()
        except Exception as db_error:
            st.error(f"⚠️ Database connection unavailable: {str(db_error)[:200]}")
            st.info(
                """
            **Note:** The Test Portfolio feature requires a PostgreSQL database connection.

            **To enable this feature on Streamlit Cloud:**

            1. Go to your [Streamlit Cloud Dashboard](https://share.streamlit.io/)
            2. Click on your app → Settings → Secrets
            3. Add a `DATABASE_URL` secret with your Supabase PostgreSQL connection string:

            ```
            DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@db.uljsqvwkomdrlnofmlad.supabase.co:5432/postgres"
            ```

            **Where to find your Supabase password:**
            - Go to your Supabase project settings
            - Navigate to Database → Connection String
            - Copy the connection pooler URL or direct connection URL
            - Replace `[YOUR-PASSWORD]` with your actual database password

            **For now, you can use these features instead:**
            - **Monte Carlo Predictions** - Stock price simulations
            - **Scrapers & Logs** - View politician trading data
            - **Predictions** - ML-based stock predictions

            These features use the Supabase REST API which is already configured.
            """
            )
            return

        try:
            trading_service = TradingService(db)
            paper_engine = create_paper_trading_engine(db)

            # Create test portfolio if none exists
            if not st.session_state.test_portfolio_id:
                if st.button("Create Test Portfolio", type="primary"):
                    with st.spinner("Creating test portfolio..."):
                        user_id = UUID("00000000-0000-0000-0000-000000000000")  # Default user
                        portfolio = paper_engine.create_test_portfolio(
                            user_id=user_id, name="My Test Portfolio", initial_capital=100000.0
                        )
                        st.session_state.test_portfolio_id = portfolio.id
                        st.success("Test portfolio created successfully!")
                        st.rerun()
            else:
                # Get portfolio
                portfolio = trading_service.get_portfolio(st.session_state.test_portfolio_id)
                if not portfolio:
                    st.error("Test portfolio not found")
                    st.session_state.test_portfolio_id = None
                    st.rerun()
                    return

                # Portfolio header
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Portfolio Value", f"${float(portfolio.current_value):,.2f}")
                with col2:
                    st.metric("Cash Balance", f"${float(portfolio.cash_balance):,.2f}")
                with col3:
                    st.metric("Total Return", f"{portfolio.total_return_pct:.2f}%")
                with col4:
                    positions = trading_service.get_portfolio_positions(portfolio.id)
                    st.metric("Positions", len(positions))

                # Trading interface
                st.subheader("📈 Paper Trading Interface")

                col1, col2 = st.columns([1, 1])

                with col1:
                    st.markdown("#### Place Test Order")

                    with st.form("test_order"):
                        symbol = st.text_input(
                            "Symbol", placeholder="AAPL", help="Stock symbol to trade"
                        )
                        side = st.selectbox("Side", [OrderSide.BUY, OrderSide.SELL])
                        order_type = st.selectbox("Order Type", [OrderType.MARKET, OrderType.LIMIT])
                        quantity = st.number_input("Quantity", min_value=1, value=1)

                        limit_price = None
                        if order_type == OrderType.LIMIT:
                            limit_price = st.number_input(
                                "Limit Price", min_value=0.01, value=100.0, step=0.01
                            )

                        if st.form_submit_button("Place Test Order", type="primary"):
                            if symbol:
                                try:
                                    order_data = OrderCreate(
                                        symbol=symbol.upper(),
                                        side=side,
                                        order_type=order_type,
                                        quantity=quantity,
                                        limit_price=limit_price,
                                        time_in_force="day",
                                        extended_hours=False,
                                    )

                                    # Create order
                                    order = trading_service.place_order(portfolio.id, order_data)

                                    # Execute paper trade
                                    success = paper_engine.execute_paper_order(order)

                                    if success:
                                        st.success(
                                            f"Test order executed: {symbol} {side.value} {quantity} shares"
                                        )
                                        st.rerun()
                                    else:
                                        st.error("Failed to execute test order")

                                except Exception as e:
                                    st.error(f"Error placing order: {e}")
                            else:
                                st.error("Please enter a symbol")

                with col2:
                    st.markdown("#### Current Positions")

                    positions = trading_service.get_portfolio_positions(portfolio.id)
                    if positions:
                        positions_data = []
                        for pos in positions:
                            positions_data.append(
                                {
                                    "Symbol": pos.symbol,
                                    "Quantity": pos.quantity,
                                    "Side": pos.side.value,
                                    "Avg Price": f"${pos.average_price:.2f}",
                                    "Current Price": f"${pos.current_price:.2f}",
                                    "Market Value": f"${pos.market_value:,.2f}",
                                    "P&L": f"${pos.unrealized_pnl:,.2f}",
                                    "P&L %": f"{pos.unrealized_pnl_pct:.2f}%",
                                    "Weight": f"{pos.weight:.1%}",
                                }
                            )

                        positions_df = pd.DataFrame(positions_data)
                        st.dataframe(positions_df, use_container_width=True)
                    else:
                        st.info("No positions found")

                # Market simulation
                st.subheader("🎲 Market Simulation")

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("Simulate 1 Day", help="Simulate market movement for 1 day"):
                        with st.spinner("Simulating market movement..."):
                            paper_engine.simulate_market_movement(portfolio.id, days=1)
                            st.success("Market simulation completed!")
                            st.rerun()

                with col2:
                    if st.button("Simulate 1 Week", help="Simulate market movement for 1 week"):
                        with st.spinner("Simulating market movement..."):
                            paper_engine.simulate_market_movement(portfolio.id, days=7)
                            st.success("Market simulation completed!")
                            st.rerun()

                with col3:
                    if st.button("Reset Portfolio", help="Reset portfolio to initial state"):
                        if st.session_state.get("confirm_reset", False):
                            # Reset portfolio
                            portfolio.current_value = portfolio.initial_capital
                            portfolio.cash_balance = portfolio.initial_capital
                            portfolio.total_return = 0.0
                            portfolio.total_return_pct = 0.0

                            # Clear positions
                            trading_service.db.query(
                                trading_service.db.query(Position)
                                .filter(Position.portfolio_id == portfolio.id)
                                .first()
                                .__class__
                            ).filter(Position.portfolio_id == portfolio.id).delete()

                            trading_service.db.commit()
                            st.success("Portfolio reset successfully!")
                            st.session_state.confirm_reset = False
                            st.rerun()
                        else:
                            st.session_state.confirm_reset = True
                            st.warning("Click again to confirm reset")

                # Performance chart
                st.subheader("📊 Performance Chart")

                performance_df = trading_service.get_portfolio_performance(portfolio.id, days=30)

                if not performance_df.empty:
                    fig = make_subplots(
                        rows=2,
                        cols=1,
                        subplot_titles=("Portfolio Value", "Daily Returns"),
                        vertical_spacing=0.1,
                    )

                    # Portfolio value
                    fig.add_trace(
                        go.Scatter(
                            x=performance_df["date"],
                            y=performance_df["portfolio_value"],
                            mode="lines",
                            name="Portfolio Value",
                            line=dict(color="blue"),
                        ),
                        row=1,
                        col=1,
                    )

                    # Daily returns
                    fig.add_trace(
                        go.Bar(
                            x=performance_df["date"],
                            y=performance_df["daily_return_pct"],
                            name="Daily Return %",
                            marker_color=[
                                "green" if x >= 0 else "red"
                                for x in performance_df["daily_return_pct"]
                            ],
                        ),
                        row=2,
                        col=1,
                    )

                    fig.update_layout(height=600, showlegend=True)
                    fig.update_xaxes(title_text="Date", row=2, col=1)
                    fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
                    fig.update_yaxes(title_text="Daily Return (%)", row=2, col=1)

                    st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)
                else:
                    st.info(
                        "No performance data available yet. Start trading to see your performance!"
                    )

                # Recent orders
                st.subheader("📋 Recent Test Orders")

                orders = trading_service.get_portfolio_orders(portfolio.id)
                if orders:
                    orders_data = []
                    for order in orders[:10]:  # Last 10 orders
                        orders_data.append(
                            {
                                "Symbol": order.symbol,
                                "Side": order.side.value,
                                "Type": order.order_type.value,
                                "Quantity": order.quantity,
                                "Status": order.status.value,
                                "Price": (
                                    f"${order.average_fill_price:.2f}"
                                    if order.average_fill_price
                                    else "-"
                                ),
                                "Created": order.created_at.strftime("%Y-%m-%d %H:%M"),
                                "Filled": (
                                    order.filled_at.strftime("%Y-%m-%d %H:%M")
                                    if order.filled_at
                                    else "-"
                                ),
                            }
                        )

                    orders_df = pd.DataFrame(orders_data)
                    st.dataframe(orders_df, use_container_width=True)
                else:
                    st.info("No test orders found")

                # Backtesting section
                st.subheader("🔬 Backtesting")

                with st.expander("Run Historical Backtest", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        start_date = st.date_input(
                            "Start Date",
                            value=datetime.now() - timedelta(days=365),
                            max_value=datetime.now() - timedelta(days=1),
                        )

                    with col2:
                        end_date = st.date_input(
                            "End Date",
                            value=datetime.now() - timedelta(days=1),
                            max_value=datetime.now(),
                        )

                    initial_capital = st.number_input(
                        "Initial Capital", min_value=1000, value=100000, step=10000
                    )

                    if st.button("Run Backtest", type="primary"):
                        with st.spinner("Running backtest..."):
                            try:
                                results = paper_engine.run_backtest(
                                    portfolio_id=portfolio.id,
                                    start_date=datetime.combine(start_date, datetime.min.time()),
                                    end_date=datetime.combine(end_date, datetime.min.time()),
                                    initial_capital=initial_capital,
                                )

                                st.success("Backtest completed!")

                                # Display results
                                col1, col2, col3, col4 = st.columns(4)

                                with col1:
                                    st.metric(
                                        "Initial Capital", f"${results['initial_capital']:,.2f}"
                                    )
                                with col2:
                                    st.metric("Final Value", f"${results['final_value']:,.2f}")
                                with col3:
                                    st.metric("Total Return", f"${results['total_return']:,.2f}")
                                with col4:
                                    st.metric(
                                        "Total Return %", f"{results['total_return_pct']:.2f}%"
                                    )

                            except Exception as e:
                                st.error(f"Backtest failed: {e}")

                # Portfolio actions
                st.subheader("⚙️ Portfolio Actions")

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(
                        "Sync with Market", help="Update all positions with current market prices"
                    ):
                        with st.spinner("Syncing with market..."):
                            paper_engine.simulate_market_movement(portfolio.id, days=0)
                            st.success("Portfolio synced with current market prices!")
                            st.rerun()

                with col2:
                    if st.button("Export Data", help="Export portfolio data to CSV"):
                        # Export portfolio data
                        positions = trading_service.get_portfolio_positions(portfolio.id)
                        if positions:
                            positions_data = []
                            for pos in positions:
                                positions_data.append(
                                    {
                                        "Symbol": pos.symbol,
                                        "Quantity": pos.quantity,
                                        "Side": pos.side.value,
                                        "Average Price": float(pos.average_price),
                                        "Current Price": float(pos.current_price),
                                        "Market Value": float(pos.market_value),
                                        "Unrealized P&L": float(pos.unrealized_pnl),
                                        "Unrealized P&L %": pos.unrealized_pnl_pct,
                                        "Weight": pos.weight,
                                    }
                                )

                            positions_df = pd.DataFrame(positions_data)
                            csv = positions_df.to_csv(index=False)
                            st.download_button(
                                label="Download Positions CSV",
                                data=csv,
                                file_name=f"test_portfolio_positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                            )
                        else:
                            st.info("No positions to export")

                with col3:
                    if st.button("Delete Portfolio", help="Delete this test portfolio"):
                        if st.session_state.get("confirm_delete", False):
                            # Delete portfolio
                            trading_service.db.delete(portfolio)
                            trading_service.db.commit()
                            st.session_state.test_portfolio_id = None
                            st.session_state.confirm_delete = False
                            st.success("Test portfolio deleted!")
                            st.rerun()
                        else:
                            st.session_state.confirm_delete = True
                            st.warning("Click again to confirm deletion")

        finally:
            # Clean up database session
            if "db" in locals() and "session_context" in locals():
                try:
                    session_context.__exit__(None, None, None)
                except Exception:
                    pass

    except Exception as e:
        st.error(f"Error loading test portfolio: {e}")
        logger.error(f"Test portfolio error: {e}")


# Import Position for the reset functionality
try:
    from mcli.ml.trading.models import Position
except ImportError:
    Position = None


# Module-level execution only when run directly (not when imported)
if __name__ == "__main__":
    show_test_portfolio()
