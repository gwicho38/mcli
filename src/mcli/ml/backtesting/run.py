#!/usr/bin/env python3
"""Entry point for backtesting CLI."""

import click

from mcli.lib.ui.styling import error, info, success


@click.group(name="mcli-backtest", help="Backtesting CLI for MCLI trading strategies")
def cli():
    """Main CLI group for backtesting."""
    pass


@cli.command(name="run", help="Run a backtest on historical data")
@click.option("--strategy", required=True, help="Strategy to backtest")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--initial-capital", default=100000, help="Initial capital")
@click.option("--output", help="Output file for results")
def run_backtest(strategy: str, start_date: str, end_date: str, initial_capital: float, output: str):
    """Run a backtest with the specified parameters."""
    info(f"Running backtest for strategy: {strategy}")
    info(f"Period: {start_date} to {end_date}")
    info(f"Initial capital: ${initial_capital:,.2f}")
    
    # TODO: Implement actual backtesting logic
    error("Backtesting functionality not yet implemented")


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
    # TODO: Implement results analysis
    error("Results analysis not yet implemented")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()