"""Overview page - Introduction to the Politician Trading Tracker"""

import streamlit as st

# Try to import streamlit-extras for enhanced UI
try:
    from mcli.ml.dashboard.streamlit_extras_utils import info_card, section_header, vertical_space

    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False
    section_header = lambda label, desc="", **kwargs: st.header(label)
    info_card = None
    vertical_space = lambda x: st.write("")


def show_overview():
    """Main overview page"""

    # Hero section
    st.markdown(
        """
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: #1f77b4; font-size: 3rem; margin-bottom: 0.5rem;'>
                📊 Politician Trading Tracker
            </h1>
            <h3 style='color: #666; font-weight: normal;'>
                Track, Analyze & Replicate Congressional Trading Patterns
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # What is this?
    section_header(
        "🎯 What is Politician Trading Tracker?",
        "Your comprehensive tool for analyzing Congressional stock trades",
        divider="blue",
    )

    st.markdown(
        """
    This dashboard provides **real-time access** to Congressional stock trading disclosures,
    allowing you to track when U.S. politicians buy and sell stocks, analyze their patterns,
    and make informed investment decisions.

    ### Why Track Politician Trading?

    📈 **Historical Outperformance**: Studies show Congressional portfolios often outperform the market
    🔍 **Early Insights**: Politicians may have access to non-public information through briefings
    💡 **Smart Money**: Following experienced investors can inform your strategy
    📊 **Transparency**: Make use of public disclosure data for better decisions
    """
    )

    vertical_space(2)

    # Key Features
    section_header("✨ Key Features", "Powerful tools for trading analysis", divider="green")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        ### 📊 Data Tracking
        - **Real-time updates** from official sources
        - **Historical data** going back years
        - **Multiple sources**: Senate, House, Senate Stock Watcher
        - **Automated scraping** for latest disclosures
        """
        )

    with col2:
        st.markdown(
            """
        ### 🤖 ML Predictions
        - **Machine learning models** for stock prediction
        - **Monte Carlo simulations** for risk analysis
        - **Pattern recognition** in trading behavior
        - **Price forecasting** based on historical data
        """
        )

    with col3:
        st.markdown(
            """
        ### 💼 Trading Tools
        - **Paper trading** integration (Alpaca)
        - **Portfolio tracking** and management
        - **Risk assessment** tools
        - **Performance analytics**
        """
        )

    vertical_space(2)

    # Quick Start Guide
    section_header("🚀 Quick Start Guide", "Get started in 3 easy steps", divider="violet")

    st.markdown(
        """
    ### Step 1: Explore Trading Data

    👉 Navigate to **"Scrapers & Logs"** to:
    - View recent politician stock disclosures
    - Search for specific politicians or stocks
    - See transaction details (buy/sell amounts, dates)
    - Export data for further analysis

    ### Step 2: Analyze with ML

    👉 Go to **"Predictions"** or **"Monte Carlo Predictions"** to:
    - See ML-generated stock predictions based on politician trades
    - Run Monte Carlo simulations for risk analysis
    - View expected returns and probability of profit
    - Understand confidence intervals

    ### Step 3: Track Your Portfolio

    👉 Use **"Trading Dashboard"** or **"Test Portfolio"** to:
    - Create paper trading portfolios
    - Replicate politician trades
    - Track your performance
    - Compare to market benchmarks
    """
    )

    vertical_space(2)

    # Page Navigation Guide
    section_header("🗺️ Page Navigation Guide", "Explore all available features", divider="orange")

    # Create expandable sections for each page category
    with st.expander("📊 **Data & Monitoring Pages**", expanded=True):
        st.markdown(
            """
        - **Pipeline Overview**: System status and data processing metrics
        - **Scrapers & Logs**: Manual and automated data collection from government sources
        - **System Health**: Monitor data pipeline health and API connections
        - **LSH Jobs**: Background job status and processing queues
        """
        )

    with st.expander("🤖 **ML & Predictions Pages**"):
        st.markdown(
            """
        - **Predictions**: Enhanced ML predictions based on politician trading patterns
        - **Monte Carlo Predictions**: Probabilistic simulation of price paths and returns
        - **Model Performance**: Evaluation metrics for ML models
        - **Model Training & Evaluation**: Train new models and compare performance
        """
        )

    with st.expander("💼 **Trading & Portfolio Pages**"):
        st.markdown(
            """
        - **Trading Dashboard**: Full-featured paper trading interface
        - **Test Portfolio**: Simplified portfolio testing and tracking
        - **Paper trading** via Alpaca API integration
        - Track performance against politician portfolios
        """
        )

    with st.expander("⚙️ **Technical & DevOps Pages**"):
        st.markdown(
            """
        - **CI/CD Pipelines**: Monitor build and deployment pipelines
        - **Workflows**: Track automated workflow executions
        - **ML Processing**: Data preprocessing and feature engineering
        - **Debug Dependencies**: Troubleshoot installation and import issues (useful for alpaca-py debugging)
        """
        )

    vertical_space(2)

    # FAQ Section
    section_header("❓ Frequently Asked Questions", "Common questions answered", divider="gray")

    with st.expander("**Q: Is this legal? Can I really track politician trades?**"):
        st.markdown(
            """
        **A:** Yes, absolutely! The STOCK Act (Stop Trading on Congressional Knowledge Act)
        requires members of Congress to publicly disclose their stock trades within 45 days.
        This app aggregates and analyzes publicly available data.

        All data comes from official sources:
        - Senate eFiling system
        - House Financial Disclosure reports
        - Senate Stock Watcher (GitHub dataset)
        """
        )

    with st.expander("**Q: How recent is the data?**"):
        st.markdown(
            """
        **A:** Data freshness depends on the source:

        - **Senate Stock Watcher**: Updated daily from official sources
        - **Manual scrapers**: Run on-demand for latest disclosures
        - **Automated jobs**: Process new filings regularly

        Note: Due to the 45-day disclosure requirement, trades are not real-time.
        You're seeing what politicians bought/sold 1-6 weeks ago.
        """
        )

    with st.expander("**Q: Can I actually trade based on this data?**"):
        st.markdown(
            """
        **A:** Yes! The dashboard includes:

        - **Paper Trading**: Practice with virtual money via Alpaca paper trading API
        - **Real Trading Integration**: Configure real Alpaca account (at your own risk)
        - **Portfolio Tracking**: Monitor your replicated politician portfolios

        ⚠️ **Important Disclaimers:**
        - Past performance doesn't guarantee future results
        - Politician trades are disclosed 45 days late
        - This is for educational/informational purposes
        - Always do your own research before investing
        """
        )

    with st.expander("**Q: Which politicians can I track?**"):
        st.markdown(
            """
        **A:** The dashboard tracks:

        - All U.S. Senators
        - All U.S. Representatives
        - High-profile traders (Pelosi, McConnell, etc.)
        - Committee members with oversight of industries

        Search by name in the **Predictions** or **Scrapers & Logs** pages.
        """
        )

    with st.expander("**Q: How do the ML predictions work?**"):
        st.markdown(
            """
        **A:** The system uses multiple techniques:

        1. **Historical Pattern Analysis**: Identifies successful trading patterns
        2. **Feature Engineering**: Incorporates politician profile, committee assignments, transaction size
        3. **Machine Learning Models**: Trains on historical data to predict outcomes
        4. **Monte Carlo Simulation**: Models thousands of possible price paths
        5. **Risk Metrics**: Calculates probability of profit, Value at Risk, confidence intervals

        See the **Model Training & Evaluation** page for technical details.
        """
        )

    with st.expander("**Q: What data sources does this use?**"):
        st.markdown(
            """
        **A:** Multiple official and curated sources:

        **Primary Sources:**
        - Senate eFiling system (senate.gov)
        - House Financial Disclosure (clerk.house.gov)
        - Senate Stock Watcher GitHub (curated dataset)

        **Supporting Data:**
        - UK Companies House API (for UK company data)
        - Yahoo Finance (for stock prices and fundamentals)
        - Alpaca API (for trading and market data)
        """
        )

    with st.expander("**Q: Is my trading data private?**"):
        st.markdown(
            """
        **A:** Yes! This is a personal dashboard:

        - Paper trading portfolios are stored locally or in your Supabase instance
        - No trading data is shared publicly
        - API keys are stored securely in Streamlit secrets
        - You control your own data
        """
        )

    with st.expander("**Q: What if I find a bug or have a feature request?**"):
        st.markdown(
            """
        **A:** Contributions welcome!

        - **Report bugs**: Open an issue on GitHub
        - **Request features**: Submit feature requests
        - **Contribute**: Pull requests accepted
        - **Documentation**: Help improve the docs

        This is an open-source project built for the community.
        """
        )

    with st.expander("**Q: Why are some pages showing errors or not loading?**"):
        st.markdown(
            """
        **A:** Some pages require optional dependencies that may not be installed:

        **Common Issues:**
        - **Trading Dashboard/Test Portfolio**: Requires `alpaca-py` package
        - **Advanced ML pages**: May require `torch` or `pytorch-lightning` (not available on Streamlit Cloud)

        **Troubleshooting:**
        1. Check the error message displayed at the top of the dashboard
        2. Visit the **Debug Dependencies** page for detailed diagnostics
        3. The Debug page shows:
           - Which packages are installed
           - Detailed import error messages
           - Python environment information
           - Troubleshooting suggestions

        **Note:** Most pages have graceful fallbacks and will work with demo data if dependencies are missing.
        """
        )

    vertical_space(2)

    # Getting Started Actions
    section_header("🎬 Ready to Get Started?", "Choose your path", divider="rainbow")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        ### 🔍 **Explore Data**
        Start by browsing recent politician trades

        👉 Go to **Scrapers & Logs**
        """
        )
        if st.button("View Trading Data", key="btn_scrapers", use_container_width=True):
            st.info("Navigate to 'Scrapers & Logs' in the sidebar →")

    with col2:
        st.markdown(
            """
        ### 📊 **Run Analysis**
        See ML predictions and simulations

        👉 Go to **Monte Carlo Predictions**
        """
        )
        if st.button("Analyze Stocks", key="btn_monte_carlo", use_container_width=True):
            st.info("Navigate to 'Monte Carlo Predictions' in the sidebar →")

    with col3:
        st.markdown(
            """
        ### 💼 **Start Trading**
        Create a paper trading portfolio

        👉 Go to **Trading Dashboard**
        """
        )
        if st.button("Paper Trade", key="btn_trading", use_container_width=True):
            st.info("Navigate to 'Trading Dashboard' in the sidebar →")

    vertical_space(2)

    # Disclaimers
    st.markdown("---")
    st.markdown(
        """
    ### ⚠️ Important Disclaimers

    - **Not Financial Advice**: This tool is for educational and informational purposes only
    - **Do Your Research**: Always conduct your own due diligence before investing
    - **Risk Warning**: All investments carry risk. Past performance doesn't guarantee future results
    - **Delayed Data**: Politician trades are disclosed 45 days after execution
    - **No Guarantees**: ML predictions are probabilistic, not certainties
    - **Paper Trading**: Practice with virtual money before risking real capital

    **Legal Note**: All data comes from public sources. This dashboard aggregates
    publicly disclosed information under the STOCK Act and is compliant with all regulations.
    """
    )

    vertical_space(1)

    # Footer
    st.markdown(
        """
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <p>Built with ❤️ for transparent government and informed investing</p>
        <p style='font-size: 0.9rem;'>
            Data sources: Senate.gov • House.gov • Senate Stock Watcher • Yahoo Finance
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    show_overview()
