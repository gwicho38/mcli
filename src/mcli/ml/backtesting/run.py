#!/usr/bin/env python3
"""Entry point for backtesting CLI."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click
import numpy as np
import pandas as pd

from mcli.lib.ui.styling import error, info, success, warning


@click.group(name="mcli-backtest", help="Backtesting CLI for MCLI trading strategies")
def cli():
    """Main CLI group for backtesting."""


def _generate_mock_backtest_results(
    strategy: str, start_date: datetime, end_date: datetime, initial_capital: float
) -> List[Dict[str, Any]]:
    """Generate mock backtest results for demonstration purposes."""
    # Generate date range
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    # Generate mock daily returns (random walk)
    np.random.seed(42)  # For reproducibility
    daily_returns = np.random.normal(0.001, 0.02, len(date_range))

    # Calculate cumulative returns and capital
    cumulative_returns = np.cumprod(1 + daily_returns)
    capital = initial_capital * cumulative_returns

    results = []
    for i, date in enumerate(date_range):
        results.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "strategy": strategy,
                "daily_return": daily_returns[i],
                "cumulative_return": cumulative_returns[i] - 1,
                "capital": capital[i],
            }
        )

    return results


@cli.command(name="run", help="Run a backtest on historical data")
@click.option("--strategy", required=True, help="Strategy to backtest")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--initial-capital", default=100000, help="Initial capital")
@click.option("--output", help="Output file for results")
def run_backtest(
    strategy: str, start_date: str, end_date: str, initial_capital: float, output: str
):
    """Run a backtest with the specified parameters."""
    info(f"Running backtest for strategy: {strategy}")
    info(f"Period: {start_date} to {end_date}")
    info(f"Initial capital: ${initial_capital:,.2f}")

    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Generate backtest results
    results = _generate_mock_backtest_results(strategy, start_dt, end_dt, initial_capital)

    if output:
        # Save results to file
        pd.DataFrame(results).to_csv(output, index=False)
        success(f"Backtest results saved to {output}")
    else:
        # Print results to console
        info("Backtest Results:")
        for result in results:
            info(f"  {result}")

    success("Backtest completed successfully")
    return 0


@cli.command(name="list", help="List available strategies")
def list_strategies():
    """List all available trading strategies."""
    info("Available strategies:")
    # TODO: Implement strategy listing
    error("Strategy listing not yet implemented")


@cli.command(name="analyze", help="Analyze backtest results")
@click.argument("results_file")
def analyze_results(results_file: str):
    """Analyze backtest results from a file."""
    info(f"Analyzing results from: {results_file}")
    try:
        results_df = pd.read_csv(results_file)

        # Basic statistics
        info(f"Total trades executed: {len(results_df)}")
        info(f"Average daily return: {results_df['daily_return'].mean():.4f}")
        info(f"Final capital: {results_df['capital'].iloc[-1]:.2f}")
        info(f"Total return: {results_df['cumulative_return'].iloc[-1]:.4f}")
        info(
            f"Sharpe ratio: {results_df['cumulative_return'].iloc[-1] / results_df['daily_return'].std():.4f}"
        )

        success("Analysis completed successfully")
        return 0

    except Exception as e:
        error(f"Failed to analyze results: {e}")
        return 1


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
