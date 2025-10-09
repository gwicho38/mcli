"""Monte Carlo simulation for politician trading predictions

Uses Monte Carlo methods to simulate possible price paths and estimate
expected returns based on politician trading patterns.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class MonteCarloTradingSimulator:
    """Monte Carlo simulator for politician trading predictions"""

    def __init__(
        self,
        initial_price: float,
        days_to_simulate: int = 90,
        num_simulations: int = 1000,
        random_seed: Optional[int] = None,
    ):
        """
        Initialize Monte Carlo simulator

        Args:
            initial_price: Starting stock price
            days_to_simulate: Number of days to project forward
            num_simulations: Number of Monte Carlo paths to generate
            random_seed: Random seed for reproducibility
        """
        self.initial_price = initial_price
        self.days_to_simulate = days_to_simulate
        self.num_simulations = num_simulations
        self.random_seed = random_seed

        if random_seed is not None:
            np.random.seed(random_seed)

        # Store simulation results
        self.simulated_paths: Optional[np.ndarray] = None
        self.final_prices: Optional[np.ndarray] = None
        self.returns: Optional[np.ndarray] = None

    def estimate_parameters(
        self, historical_prices: pd.Series
    ) -> Tuple[float, float]:
        """
        Estimate drift (μ) and volatility (σ) from historical data

        Args:
            historical_prices: Series of historical prices

        Returns:
            Tuple of (drift, volatility)
        """
        # Calculate daily returns
        returns = historical_prices.pct_change().dropna()

        # Estimate parameters
        daily_return = returns.mean()
        daily_volatility = returns.std()

        # Annualize (assuming 252 trading days)
        annual_return = daily_return * 252
        annual_volatility = daily_volatility * np.sqrt(252)

        logger.info(
            f"Estimated parameters: drift={annual_return:.4f}, "
            f"volatility={annual_volatility:.4f}"
        )

        return annual_return, annual_volatility

    def simulate_price_paths(
        self, drift: float, volatility: float
    ) -> np.ndarray:
        """
        Generate Monte Carlo price paths using Geometric Brownian Motion

        Args:
            drift: Expected return (μ)
            volatility: Standard deviation (σ)

        Returns:
            Array of shape (num_simulations, days_to_simulate + 1) with price paths
        """
        # Time step (assuming daily)
        dt = 1 / 252  # Daily time step in years

        # Initialize price paths matrix
        paths = np.zeros((self.num_simulations, self.days_to_simulate + 1))
        paths[:, 0] = self.initial_price

        # Generate random shocks
        random_shocks = np.random.normal(
            0, 1, size=(self.num_simulations, self.days_to_simulate)
        )

        # Simulate paths using Geometric Brownian Motion
        # S(t+dt) = S(t) * exp((μ - σ²/2)dt + σ√dt * Z)
        for t in range(1, self.days_to_simulate + 1):
            drift_component = (drift - 0.5 * volatility**2) * dt
            shock_component = volatility * np.sqrt(dt) * random_shocks[:, t - 1]

            paths[:, t] = paths[:, t - 1] * np.exp(
                drift_component + shock_component
            )

        self.simulated_paths = paths
        self.final_prices = paths[:, -1]
        self.returns = (self.final_prices - self.initial_price) / self.initial_price

        logger.info(
            f"Simulated {self.num_simulations} price paths over {self.days_to_simulate} days"
        )

        return paths

    def calculate_statistics(self) -> Dict[str, float]:
        """
        Calculate statistics from simulation results

        Returns:
            Dictionary with statistical measures
        """
        if self.final_prices is None:
            raise ValueError("Must run simulation first")

        stats = {
            "expected_final_price": np.mean(self.final_prices),
            "median_final_price": np.median(self.final_prices),
            "std_final_price": np.std(self.final_prices),
            "min_final_price": np.min(self.final_prices),
            "max_final_price": np.max(self.final_prices),
            "expected_return": np.mean(self.returns) * 100,
            "median_return": np.median(self.returns) * 100,
            "std_return": np.std(self.returns) * 100,
            "probability_profit": np.sum(self.returns > 0) / len(self.returns) * 100,
            "value_at_risk_95": np.percentile(self.returns, 5) * 100,  # 95% VaR
            "percentile_5": np.percentile(self.final_prices, 5),
            "percentile_25": np.percentile(self.final_prices, 25),
            "percentile_75": np.percentile(self.final_prices, 75),
            "percentile_95": np.percentile(self.final_prices, 95),
        }

        return stats

    def create_path_visualization(
        self, num_paths_to_plot: int = 100, show_percentiles: bool = True
    ) -> go.Figure:
        """
        Create visualization of simulated price paths

        Args:
            num_paths_to_plot: Number of individual paths to display
            show_percentiles: Whether to show percentile bands

        Returns:
            Plotly figure object
        """
        if self.simulated_paths is None:
            raise ValueError("Must run simulation first")

        fig = go.Figure()

        # Plot sample paths
        num_to_plot = min(num_paths_to_plot, self.num_simulations)
        sample_indices = np.random.choice(
            self.num_simulations, num_to_plot, replace=False
        )

        for idx in sample_indices:
            fig.add_trace(
                go.Scatter(
                    x=list(range(self.days_to_simulate + 1)),
                    y=self.simulated_paths[idx],
                    mode="lines",
                    line=dict(color="lightblue", width=0.5),
                    opacity=0.3,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # Add mean path
        mean_path = np.mean(self.simulated_paths, axis=0)
        fig.add_trace(
            go.Scatter(
                x=list(range(self.days_to_simulate + 1)),
                y=mean_path,
                mode="lines",
                line=dict(color="blue", width=3),
                name="Expected Path",
            )
        )

        if show_percentiles:
            # Add percentile bands
            percentile_5 = np.percentile(self.simulated_paths, 5, axis=0)
            percentile_25 = np.percentile(self.simulated_paths, 25, axis=0)
            percentile_75 = np.percentile(self.simulated_paths, 75, axis=0)
            percentile_95 = np.percentile(self.simulated_paths, 95, axis=0)

            x_vals = list(range(self.days_to_simulate + 1))

            # 90% confidence band (5th to 95th percentile)
            fig.add_trace(
                go.Scatter(
                    x=x_vals + x_vals[::-1],
                    y=list(percentile_95) + list(percentile_5[::-1]),
                    fill="toself",
                    fillcolor="rgba(255, 0, 0, 0.1)",
                    line=dict(color="rgba(255, 0, 0, 0)"),
                    name="90% Confidence",
                    hoverinfo="skip",
                )
            )

            # 50% confidence band (25th to 75th percentile)
            fig.add_trace(
                go.Scatter(
                    x=x_vals + x_vals[::-1],
                    y=list(percentile_75) + list(percentile_25[::-1]),
                    fill="toself",
                    fillcolor="rgba(0, 255, 0, 0.2)",
                    line=dict(color="rgba(0, 255, 0, 0)"),
                    name="50% Confidence",
                    hoverinfo="skip",
                )
            )

        fig.update_layout(
            title=f"Monte Carlo Simulation: {self.num_simulations:,} Price Paths",
            xaxis_title="Days",
            yaxis_title="Price ($)",
            hovermode="x unified",
            template="plotly_white",
        )

        return fig

    def create_distribution_visualization(self) -> go.Figure:
        """
        Create histogram of final price distribution

        Returns:
            Plotly figure object
        """
        if self.final_prices is None:
            raise ValueError("Must run simulation first")

        stats = self.calculate_statistics()

        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Final Price Distribution", "Return Distribution"),
        )

        # Price distribution
        fig.add_trace(
            go.Histogram(
                x=self.final_prices,
                nbinsx=50,
                name="Final Price",
                marker_color="lightblue",
                showlegend=False,
            ),
            row=1,
            col=1,
        )

        # Add vertical lines for statistics
        fig.add_vline(
            x=stats["expected_final_price"],
            line_dash="dash",
            line_color="blue",
            annotation_text="Mean",
            row=1,
            col=1,
        )

        fig.add_vline(
            x=self.initial_price,
            line_dash="solid",
            line_color="red",
            annotation_text="Current",
            row=1,
            col=1,
        )

        # Return distribution
        fig.add_trace(
            go.Histogram(
                x=self.returns * 100,
                nbinsx=50,
                name="Returns",
                marker_color="lightgreen",
                showlegend=False,
            ),
            row=1,
            col=2,
        )

        # Add vertical line at 0% return
        fig.add_vline(
            x=0, line_dash="dash", line_color="red", annotation_text="0%", row=1, col=2
        )

        fig.update_xaxes(title_text="Price ($)", row=1, col=1)
        fig.update_xaxes(title_text="Return (%)", row=1, col=2)
        fig.update_yaxes(title_text="Frequency", row=1, col=1)
        fig.update_yaxes(title_text="Frequency", row=1, col=2)

        fig.update_layout(
            title="Monte Carlo Simulation Results",
            template="plotly_white",
            height=400,
        )

        return fig

    def calculate_confidence_intervals(
        self, confidence_levels: List[float] = [0.90, 0.95, 0.99]
    ) -> Dict[float, Tuple[float, float]]:
        """
        Calculate confidence intervals for final price

        Args:
            confidence_levels: List of confidence levels (e.g., [0.90, 0.95])

        Returns:
            Dictionary mapping confidence level to (lower, upper) bounds
        """
        if self.final_prices is None:
            raise ValueError("Must run simulation first")

        intervals = {}
        for level in confidence_levels:
            alpha = 1 - level
            lower = np.percentile(self.final_prices, alpha / 2 * 100)
            upper = np.percentile(self.final_prices, (1 - alpha / 2) * 100)
            intervals[level] = (lower, upper)

        return intervals


def simulate_politician_trade_impact(
    stock_symbol: str,
    politician_name: str,
    transaction_amount: float,
    historical_prices: pd.Series,
    days_forward: int = 90,
    num_simulations: int = 1000,
) -> Dict:
    """
    Simulate potential outcomes of following a politician's trade

    Args:
        stock_symbol: Stock ticker symbol
        politician_name: Name of politician
        transaction_amount: Dollar amount of politician's trade
        historical_prices: Historical price data
        days_forward: Days to simulate forward
        num_simulations: Number of Monte Carlo simulations

    Returns:
        Dictionary with simulation results and statistics
    """
    if len(historical_prices) < 30:
        logger.warning(f"Insufficient historical data for {stock_symbol}")
        return None

    current_price = historical_prices.iloc[-1]

    # Initialize simulator
    simulator = MonteCarloTradingSimulator(
        initial_price=current_price,
        days_to_simulate=days_forward,
        num_simulations=num_simulations,
    )

    # Estimate parameters from historical data
    drift, volatility = simulator.estimate_parameters(historical_prices)

    # Run simulation
    simulator.simulate_price_paths(drift, volatility)

    # Calculate statistics
    stats = simulator.calculate_statistics()

    # Create visualizations
    path_fig = simulator.create_path_visualization(num_paths_to_plot=100)
    dist_fig = simulator.create_distribution_visualization()

    # Calculate confidence intervals
    confidence_intervals = simulator.calculate_confidence_intervals()

    return {
        "stock_symbol": stock_symbol,
        "politician_name": politician_name,
        "transaction_amount": transaction_amount,
        "current_price": current_price,
        "simulation_days": days_forward,
        "num_simulations": num_simulations,
        "drift": drift,
        "volatility": volatility,
        "statistics": stats,
        "confidence_intervals": confidence_intervals,
        "path_visualization": path_fig,
        "distribution_visualization": dist_fig,
        "simulated_paths": simulator.simulated_paths,
    }


# Export main classes and functions
__all__ = [
    "MonteCarloTradingSimulator",
    "simulate_politician_trade_impact",
]
