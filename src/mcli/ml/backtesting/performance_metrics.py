"""Performance metrics and analysis for backtesting"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""

    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    recovery_factor: float
    payoff_ratio: float


@dataclass
class RiskMetrics:
    """Risk metrics"""

    value_at_risk_95: float
    conditional_var_95: float
    value_at_risk_99: float
    conditional_var_99: float
    beta: float
    alpha: float
    correlation: float
    information_ratio: float
    treynor_ratio: float
    downside_deviation: float
    upside_capture: float
    downside_capture: float


class PerformanceAnalyzer:
    """Analyze backtest performance"""

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate

    def calculate_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        trades: Optional[pd.DataFrame] = None,
    ) -> Tuple[PortfolioMetrics, RiskMetrics]:
        """Calculate comprehensive performance metrics"""

        # Portfolio metrics
        portfolio_metrics = self._calculate_portfolio_metrics(returns, trades)

        # Risk metrics
        risk_metrics = self._calculate_risk_metrics(returns, benchmark_returns)

        return portfolio_metrics, risk_metrics

    def _calculate_portfolio_metrics(
        self, returns: pd.Series, trades: Optional[pd.DataFrame] = None
    ) -> PortfolioMetrics:
        """Calculate portfolio performance metrics"""

        # Basic returns
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1

        # Volatility
        volatility = returns.std() * np.sqrt(252)

        # Sharpe ratio
        excess_returns = returns - self.risk_free_rate / 252
        sharpe_ratio = (
            excess_returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        )

        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = (
            (annualized_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0
        )

        # Drawdown analysis
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        max_drawdown = drawdown.min()
        max_dd_duration = self._calculate_max_drawdown_duration(drawdown)

        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # Trade analysis
        if trades is not None and len(trades) > 0:
            trade_metrics = self._analyze_trades(trades)
        else:
            trade_metrics = {
                "win_rate": 0.5,
                "profit_factor": 1.0,
                "avg_win": 0,
                "avg_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "consecutive_wins": 0,
                "consecutive_losses": 0,
                "payoff_ratio": 1.0,
            }

        # Recovery factor
        recovery_factor = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

        return PortfolioMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            recovery_factor=recovery_factor,
            **trade_metrics,
        )

    def _calculate_risk_metrics(
        self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None
    ) -> RiskMetrics:
        """Calculate risk metrics"""

        # Value at Risk (VaR)
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)

        # Conditional VaR (CVaR) or Expected Shortfall
        cvar_95 = returns[returns <= var_95].mean()
        cvar_99 = returns[returns <= var_99].mean()

        # Market risk metrics
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            # Align series
            aligned = pd.DataFrame({"returns": returns, "benchmark": benchmark_returns}).dropna()

            if len(aligned) > 1:
                # Beta
                covariance = aligned.cov()
                beta = covariance.loc["returns", "benchmark"] / aligned["benchmark"].var()

                # Alpha
                alpha = aligned["returns"].mean() - beta * aligned["benchmark"].mean()
                alpha = alpha * 252  # Annualize

                # Correlation
                correlation = aligned.corr().loc["returns", "benchmark"]

                # Information ratio
                active_returns = aligned["returns"] - aligned["benchmark"]
                tracking_error = active_returns.std() * np.sqrt(252)
                information_ratio = (
                    active_returns.mean() * 252 / tracking_error if tracking_error > 0 else 0
                )

                # Treynor ratio
                treynor_ratio = (
                    (aligned["returns"].mean() * 252 - self.risk_free_rate) / beta
                    if beta != 0
                    else 0
                )

                # Capture ratios
                up_market = aligned[aligned["benchmark"] > 0]
                down_market = aligned[aligned["benchmark"] < 0]

                upside_capture = (
                    up_market["returns"].mean() / up_market["benchmark"].mean()
                    if len(up_market) > 0 and up_market["benchmark"].mean() != 0
                    else 1.0
                )

                downside_capture = (
                    down_market["returns"].mean() / down_market["benchmark"].mean()
                    if len(down_market) > 0 and down_market["benchmark"].mean() != 0
                    else 1.0
                )
            else:
                beta = alpha = correlation = information_ratio = treynor_ratio = 0
                upside_capture = downside_capture = 1.0
        else:
            beta = alpha = correlation = information_ratio = treynor_ratio = 0
            upside_capture = downside_capture = 1.0

        # Downside deviation
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)

        return RiskMetrics(
            value_at_risk_95=var_95,
            conditional_var_95=cvar_95,
            value_at_risk_99=var_99,
            conditional_var_99=cvar_99,
            beta=beta,
            alpha=alpha,
            correlation=correlation,
            information_ratio=information_ratio,
            treynor_ratio=treynor_ratio,
            downside_deviation=downside_deviation,
            upside_capture=upside_capture,
            downside_capture=downside_capture,
        )

    def _calculate_max_drawdown_duration(self, drawdown: pd.Series) -> int:
        """Calculate maximum drawdown duration in days"""
        is_drawdown = drawdown < 0
        drawdown_periods = []
        current_duration = 0

        for is_dd in is_drawdown:
            if is_dd:
                current_duration += 1
            else:
                if current_duration > 0:
                    drawdown_periods.append(current_duration)
                current_duration = 0

        if current_duration > 0:
            drawdown_periods.append(current_duration)

        return max(drawdown_periods) if drawdown_periods else 0

    def _analyze_trades(self, trades: pd.DataFrame) -> Dict[str, float]:
        """Analyze trade statistics"""
        # Filter for trades with PnL
        pnl_trades = trades[trades["pnl"].notna()].copy()

        if len(pnl_trades) == 0:
            return {
                "win_rate": 0.5,
                "profit_factor": 1.0,
                "avg_win": 0,
                "avg_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "consecutive_wins": 0,
                "consecutive_losses": 0,
                "payoff_ratio": 1.0,
            }

        # Winning and losing trades
        winning_trades = pnl_trades[pnl_trades["pnl"] > 0]
        losing_trades = pnl_trades[pnl_trades["pnl"] < 0]

        # Win rate
        win_rate = len(winning_trades) / len(pnl_trades)

        # Average win/loss
        avg_win = winning_trades["pnl"].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades["pnl"].mean()) if len(losing_trades) > 0 else 0

        # Profit factor
        gross_profit = winning_trades["pnl"].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades["pnl"].sum()) if len(losing_trades) > 0 else 1
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

        # Largest win/loss
        largest_win = winning_trades["pnl"].max() if len(winning_trades) > 0 else 0
        largest_loss = abs(losing_trades["pnl"].min()) if len(losing_trades) > 0 else 0

        # Consecutive wins/losses
        pnl_trades["is_win"] = pnl_trades["pnl"] > 0
        consecutive_wins = self._max_consecutive(pnl_trades["is_win"].values, True)
        consecutive_losses = self._max_consecutive(pnl_trades["is_win"].values, False)

        # Payoff ratio
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "consecutive_wins": consecutive_wins,
            "consecutive_losses": consecutive_losses,
            "payoff_ratio": payoff_ratio,
        }

    def _max_consecutive(self, arr: np.ndarray, value: bool) -> int:
        """Calculate maximum consecutive occurrences of value"""
        max_count = 0
        current_count = 0

        for val in arr:
            if val == value:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0

        return max_count


def plot_performance(backtest_result, save_path: Optional[str] = None):
    """Plot backtest performance charts"""
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))

    # Portfolio value
    ax = axes[0, 0]
    ax.plot(
        backtest_result.portfolio_value.index,
        backtest_result.portfolio_value.values,
        label="Portfolio",
    )
    if backtest_result.benchmark_returns is not None:
        benchmark_cumulative = (1 + backtest_result.benchmark_returns).cumprod()
        benchmark_value = benchmark_cumulative * backtest_result.portfolio_value.iloc[0]
        ax.plot(benchmark_value.index, benchmark_value.values, label="Benchmark", alpha=0.7)
    ax.set_title("Portfolio Value")
    ax.set_xlabel("Date")
    ax.set_ylabel("Value ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Returns distribution
    ax = axes[0, 1]
    ax.hist(backtest_result.returns.values * 100, bins=50, edgecolor="black")
    ax.set_title("Returns Distribution")
    ax.set_xlabel("Daily Return (%)")
    ax.set_ylabel("Frequency")
    ax.axvline(x=0, color="red", linestyle="--", alpha=0.5)
    ax.grid(True, alpha=0.3)

    # Drawdown
    ax = axes[1, 0]
    cumulative = (1 + backtest_result.returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = ((cumulative - running_max) / running_max) * 100
    ax.fill_between(drawdown.index, drawdown.values, 0, color="red", alpha=0.3)
    ax.set_title("Drawdown")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.3)

    # Rolling Sharpe Ratio
    ax = axes[1, 1]
    rolling_sharpe = (
        backtest_result.returns.rolling(window=60).mean()
        / backtest_result.returns.rolling(window=60).std()
        * np.sqrt(252)
    )
    ax.plot(rolling_sharpe.index, rolling_sharpe.values)
    ax.set_title("Rolling Sharpe Ratio (60 days)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Sharpe Ratio")
    ax.axhline(y=0, color="red", linestyle="--", alpha=0.5)
    ax.grid(True, alpha=0.3)

    # Trade analysis
    ax = axes[2, 0]
    if not backtest_result.trades.empty and "pnl" in backtest_result.trades.columns:
        pnl_trades = backtest_result.trades[backtest_result.trades["pnl"].notna()]
        if not pnl_trades.empty:
            colors = ["green" if pnl > 0 else "red" for pnl in pnl_trades["pnl"]]
            ax.bar(range(len(pnl_trades)), pnl_trades["pnl"].values, color=colors, alpha=0.6)
            ax.set_title("Trade PnL")
            ax.set_xlabel("Trade Number")
            ax.set_ylabel("PnL ($)")
            ax.axhline(y=0, color="black", linestyle="-", alpha=0.3)
    else:
        ax.text(0.5, 0.5, "No trades", ha="center", va="center")
        ax.set_title("Trade PnL")
    ax.grid(True, alpha=0.3)

    # Metrics summary
    ax = axes[2, 1]
    ax.axis("off")
    metrics_text = f"""
Performance Metrics:
─────────────────
Total Return: {backtest_result.metrics['total_return']:.2%}
Annual Return: {backtest_result.metrics['annualized_return']:.2%}
Volatility: {backtest_result.metrics['volatility']:.2%}
Sharpe Ratio: {backtest_result.metrics['sharpe_ratio']:.2f}
Max Drawdown: {backtest_result.metrics['max_drawdown']:.2%}
Win Rate: {backtest_result.metrics['win_rate']:.2%}
Total Trades: {backtest_result.metrics['total_trades']}
"""
    ax.text(
        0.1,
        0.9,
        metrics_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        fontfamily="monospace",
    )

    plt.suptitle(f"Backtest Results - {backtest_result.strategy_name}", fontsize=14)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=100, bbox_inches="tight")
        logger.info(f"Performance chart saved to {save_path}")

    return fig
