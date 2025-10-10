"""Monte Carlo Simulation Dashboard for Politician Trading Predictions

Inspired by best practices from:
- mesmith027/streamlit_webapps (Monte Carlo techniques)
- jumitti/tfinder (UI/UX patterns)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

logger = logging.getLogger(__name__)

# Try to import Monte Carlo simulator
HAS_MONTE_CARLO = True
try:
    from mcli.ml.predictions.monte_carlo import (
        MonteCarloTradingSimulator,
        simulate_politician_trade_impact,
    )
except ImportError:
    HAS_MONTE_CARLO = False
    MonteCarloTradingSimulator = None

# Try to import streamlit-extras
try:
    from mcli.ml.dashboard.streamlit_extras_utils import (
        section_header,
        enhanced_metrics,
        vertical_space,
    )
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False
    section_header = lambda *args, **kwargs: st.header(args[0])
    enhanced_metrics = None
    vertical_space = lambda x: st.write("")


def show_monte_carlo_predictions():
    """Main Monte Carlo predictions page"""

    # Page header with custom styling
    st.markdown(
        """
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #749BC2;
            text-align: center;
            padding: 1rem 0;
        }
        .sub-header {
            font-size: 1.2rem;
            color: #4A6FA5;
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="main-header">🎲 Monte Carlo Trading Simulator</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Simulate potential outcomes of politician trades using Monte Carlo methods</div>',
        unsafe_allow_html=True,
    )

    if not HAS_MONTE_CARLO:
        st.error("⚠️ Monte Carlo simulator not available. Please ensure all dependencies are installed.")
        st.info(
            """
            **Required:**
            - numpy
            - pandas
            - plotly

            Install with: `pip install numpy pandas plotly`
            """
        )
        return

    # Sidebar configuration
    with st.sidebar:
        st.markdown("## ⚙️ Simulation Settings")

        st.markdown("---")
        st.markdown("### 📊 Parameters")

        num_simulations = st.slider(
            "Number of Simulations",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100,
            help="More simulations = better accuracy but slower performance",
        )

        days_forward = st.slider(
            "Days to Simulate",
            min_value=30,
            max_value=365,
            value=90,
            step=30,
            help="How far into the future to project",
        )

        confidence_level = st.select_slider(
            "Confidence Level",
            options=[0.90, 0.95, 0.99],
            value=0.95,
            format_func=lambda x: f"{x*100:.0f}%",
            help="Confidence interval for predictions",
        )

        st.markdown("---")
        st.markdown("### 📈 Display Options")

        num_paths_display = st.slider(
            "Paths to Display",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="Number of individual simulation paths to show on chart",
        )

        show_percentiles = st.checkbox(
            "Show Confidence Bands",
            value=True,
            help="Display 50% and 90% confidence bands",
        )

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.info(
            """
            **Monte Carlo Simulation** uses random sampling to model
            possible future price movements based on historical volatility
            and returns.

            **Key Concepts:**
            - Uses Geometric Brownian Motion (GBM)
            - Assumes log-normal price distribution
            - Estimates drift (μ) and volatility (σ) from historical data
            """
        )

    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Quick Simulation",
        "📊 Advanced Analysis",
        "📚 Learn More",
        "⚙️ Custom Parameters"
    ])

    with tab1:
        show_quick_simulation(
            num_simulations, days_forward, num_paths_display,
            show_percentiles, confidence_level
        )

    with tab2:
        show_advanced_analysis(num_simulations, days_forward, confidence_level)

    with tab3:
        show_educational_content()

    with tab4:
        show_custom_parameters(num_simulations, days_forward)


def show_quick_simulation(
    num_simulations: int,
    days_forward: int,
    num_paths_display: int,
    show_percentiles: bool,
    confidence_level: float,
):
    """Quick simulation interface"""

    section_header(
        "🚀 Quick Start Simulation",
        "Enter stock details and get instant Monte Carlo predictions",
        divider="blue"
    )

    # Input form
    with st.form("quick_sim_form"):
        col1, col2 = st.columns(2)

        with col1:
            stock_symbol = st.text_input(
                "Stock Symbol",
                value="AAPL",
                placeholder="e.g., AAPL, TSLA, MSFT",
            )

            current_price = st.number_input(
                "Current Price ($)",
                min_value=0.01,
                value=150.00,
                step=0.01,
            )

        with col2:
            politician_name = st.text_input(
                "Politician Name",
                value="Nancy Pelosi",
                placeholder="e.g., Nancy Pelosi",
            )

            transaction_amount = st.number_input(
                "Transaction Amount ($)",
                min_value=1000,
                value=100000,
                step=1000,
            )

        # Historical parameters
        col3, col4 = st.columns(2)

        with col3:
            annual_return = st.number_input(
                "Expected Annual Return (%)",
                min_value=-50.0,
                max_value=100.0,
                value=12.0,
                step=0.5,
                help="Historical average annual return",
            )

        with col4:
            annual_volatility = st.number_input(
                "Annual Volatility (%)",
                min_value=1.0,
                max_value=100.0,
                value=25.0,
                step=1.0,
                help="Historical standard deviation of returns",
            )

        submitted = st.form_submit_button(
            "🎲 Run Simulation",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        run_simulation(
            stock_symbol=stock_symbol,
            politician_name=politician_name,
            current_price=current_price,
            transaction_amount=transaction_amount,
            drift=annual_return / 100,
            volatility=annual_volatility / 100,
            num_simulations=num_simulations,
            days_forward=days_forward,
            num_paths_display=num_paths_display,
            show_percentiles=show_percentiles,
            confidence_level=confidence_level,
        )


def run_simulation(
    stock_symbol: str,
    politician_name: str,
    current_price: float,
    transaction_amount: float,
    drift: float,
    volatility: float,
    num_simulations: int,
    days_forward: int,
    num_paths_display: int,
    show_percentiles: bool,
    confidence_level: float,
):
    """Execute Monte Carlo simulation and display results"""

    with st.spinner(f"Running {num_simulations:,} simulations..."):
        # Initialize simulator
        simulator = MonteCarloTradingSimulator(
            initial_price=current_price,
            days_to_simulate=days_forward,
            num_simulations=num_simulations,
        )

        # Run simulation
        simulator.simulate_price_paths(drift, volatility)

        # Calculate statistics
        stats = simulator.calculate_statistics()

    vertical_space(2)

    # Display results header
    section_header(
        f"📈 Simulation Results: {stock_symbol}",
        f"{politician_name} • {num_simulations:,} simulations • {days_forward} days",
        divider="green"
    )

    # Key metrics
    if HAS_EXTRAS and enhanced_metrics:
        enhanced_metrics([
            {
                "label": "Expected Price",
                "value": f"${stats['expected_final_price']:.2f}",
                "delta": f"{stats['expected_return']:.1f}%"
            },
            {
                "label": "Probability of Profit",
                "value": f"{stats['probability_profit']:.1f}%",
            },
            {
                "label": "Value at Risk (95%)",
                "value": f"{stats['value_at_risk_95']:.1f}%",
            },
            {
                "label": "Best Case (95th %ile)",
                "value": f"${stats['percentile_95']:.2f}",
                "delta": f"+{((stats['percentile_95']/current_price - 1) * 100):.1f}%"
            },
        ])
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Expected Price", f"${stats['expected_final_price']:.2f}",
                     f"{stats['expected_return']:.1f}%")
        with col2:
            st.metric("Profit Probability", f"{stats['probability_profit']:.1f}%")
        with col3:
            st.metric("VaR (95%)", f"{stats['value_at_risk_95']:.1f}%")
        with col4:
            st.metric("Best Case", f"${stats['percentile_95']:.2f}")

    vertical_space(2)

    # Price path visualization
    st.subheader("📊 Simulated Price Paths")

    path_fig = simulator.create_path_visualization(
        num_paths_to_plot=num_paths_display,
        show_percentiles=show_percentiles
    )
    st.plotly_chart(path_fig, config={"displayModeBar": True}, use_container_width=True)

    vertical_space(1)

    # Distribution visualization
    st.subheader("📉 Price & Return Distributions")
    dist_fig = simulator.create_distribution_visualization()
    st.plotly_chart(dist_fig, config={"displayModeBar": True}, use_container_width=True)

    vertical_space(2)

    # Detailed statistics
    with st.expander("📊 Detailed Statistics", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Price Statistics**")
            st.markdown(f"- Current Price: ${current_price:.2f}")
            st.markdown(f"- Expected Final: ${stats['expected_final_price']:.2f}")
            st.markdown(f"- Median Final: ${stats['median_final_price']:.2f}")
            st.markdown(f"- Standard Dev: ${stats['std_final_price']:.2f}")
            st.markdown(f"- Min Price: ${stats['min_final_price']:.2f}")
            st.markdown(f"- Max Price: ${stats['max_final_price']:.2f}")

        with col2:
            st.markdown("**Return Statistics**")
            st.markdown(f"- Expected Return: {stats['expected_return']:.2f}%")
            st.markdown(f"- Median Return: {stats['median_return']:.2f}%")
            st.markdown(f"- Std Dev Return: {stats['std_return']:.2f}%")
            st.markdown(f"- 5th Percentile: {stats['value_at_risk_95']:.2f}%")
            st.markdown(f"- 95th Percentile: {((stats['percentile_95']/current_price - 1)*100):.2f}%")

    # Confidence intervals
    confidence_intervals = simulator.calculate_confidence_intervals([confidence_level])
    lower, upper = confidence_intervals[confidence_level]

    st.info(
        f"**{confidence_level*100:.0f}% Confidence Interval:** "
        f"${lower:.2f} - ${upper:.2f} "
        f"({((lower/current_price - 1)*100):.1f}% to {((upper/current_price - 1)*100):.1f}%)"
    )


def show_advanced_analysis(num_simulations: int, days_forward: int, confidence_level: float):
    """Advanced analysis with historical data integration"""

    section_header(
        "🔬 Advanced Analysis",
        "Use historical price data for more accurate simulations",
        divider="violet"
    )

    st.info(
        """
        **Coming Soon:**
        - Integration with real-time market data APIs
        - Historical politician trade correlation analysis
        - Portfolio optimization using Monte Carlo
        - Multi-stock scenario analysis
        """
    )


def show_educational_content():
    """Educational content about Monte Carlo methods"""

    section_header(
        "📚 Understanding Monte Carlo Simulation",
        "Learn how probabilistic modeling predicts trading outcomes",
        divider="orange"
    )

    st.markdown("""
    ## What is Monte Carlo Simulation?

    Monte Carlo simulation is a computational technique that uses random sampling
    to estimate possible outcomes of an uncertain event.

    ### How It Works for Stock Predictions

    1. **Estimate Parameters**
       - Calculate historical drift (μ): average return
       - Calculate volatility (σ): standard deviation of returns

    2. **Generate Random Paths**
       - Use Geometric Brownian Motion (GBM)
       - Formula: S(t+dt) = S(t) × exp((μ - σ²/2)dt + σ√dt × Z)
       - Where Z is a random normal variable

    3. **Analyze Results**
       - Run thousands of simulations
       - Calculate statistics on final prices
       - Estimate probability distributions

    ### Key Advantages

    - **Probabilistic**: Shows range of possible outcomes, not just one prediction
    - **Visual**: Easy to understand probability distributions
    - **Flexible**: Can incorporate different assumptions and scenarios
    - **Risk Assessment**: Calculates Value at Risk (VaR) and confidence intervals

    ### Limitations

    - Assumes log-normal distribution (may not capture extreme events)
    - Based on historical data (past performance ≠ future results)
    - Doesn't account for market structure changes
    - Ignores transaction costs and liquidity constraints

    ### For Politician Trading Analysis

    Monte Carlo is particularly useful for:
    - **Following trades**: Estimate expected returns from mimicking politician trades
    - **Risk management**: Understand downside risk before entering positions
    - **Position sizing**: Determine appropriate investment amounts
    - **Timing analysis**: Compare different holding periods
    """)


def show_custom_parameters(num_simulations: int, days_forward: int):
    """Custom parameter configuration"""

    section_header(
        "⚙️ Custom Parameters",
        "Advanced configuration for power users",
        divider="gray"
    )

    st.warning(
        "⚠️ **Advanced Users Only** - Modifying these parameters requires "
        "understanding of financial mathematics and Monte Carlo methods."
    )

    with st.form("custom_params_form"):
        st.markdown("### Geometric Brownian Motion Parameters")

        col1, col2 = st.columns(2)

        with col1:
            custom_drift = st.number_input(
                "Drift (μ) - Annual",
                min_value=-1.0,
                max_value=1.0,
                value=0.10,
                step=0.01,
                format="%.4f",
                help="Expected return rate (e.g., 0.10 = 10% per year)",
            )

            custom_volatility = st.number_input(
                "Volatility (σ) - Annual",
                min_value=0.01,
                max_value=2.0,
                value=0.25,
                step=0.01,
                format="%.4f",
                help="Standard deviation of returns (e.g., 0.25 = 25% volatility)",
            )

        with col2:
            random_seed = st.number_input(
                "Random Seed",
                min_value=0,
                max_value=999999,
                value=42,
                help="For reproducible results",
            )

            use_seed = st.checkbox("Use Random Seed", value=False)

        st.markdown("### Time Parameters")

        col3, col4 = st.columns(2)

        with col3:
            trading_days_per_year = st.number_input(
                "Trading Days/Year",
                min_value=200,
                max_value=365,
                value=252,
                help="Standard is 252 for US markets",
            )

        with col4:
            time_step = st.selectbox(
                "Time Step",
                ["Daily", "Weekly", "Monthly"],
                help="Granularity of simulation",
            )

        submitted = st.form_submit_button("Run Custom Simulation", type="primary")

    if submitted:
        st.success(
            f"Custom simulation configured with μ={custom_drift:.4f}, "
            f"σ={custom_volatility:.4f}"
        )


# Module-level execution
if __name__ == "__main__":
    show_monte_carlo_predictions()
