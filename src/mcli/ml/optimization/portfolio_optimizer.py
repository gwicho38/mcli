"""Advanced portfolio optimization for stock recommendations"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Optimization libraries
import cvxpy as cp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import minimize
from scipy.stats import norm

logger = logging.getLogger(__name__)


class OptimizationObjective(Enum):
    """Portfolio optimization objectives"""

    MEAN_VARIANCE = "mean_variance"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_SHARPE = "maximum_sharpe"
    BLACK_LITTERMAN = "black_litterman"
    FACTOR_MODEL = "factor_model"
    CVaR = "conditional_value_at_risk"
    KELLY_CRITERION = "kelly_criterion"


@dataclass
class OptimizationConstraints:
    """Portfolio optimization constraints"""

    # Weight constraints
    min_weight: float = 0.0
    max_weight: float = 1.0
    sum_weights: float = 1.0

    # Sector/factor constraints
    max_sector_weight: Optional[Dict[str, float]] = None
    max_factor_exposure: Optional[Dict[str, float]] = None

    # Risk constraints
    max_volatility: Optional[float] = None
    max_var: Optional[float] = None
    max_cvar: Optional[float] = None

    # Transaction costs
    transaction_costs: float = 0.001
    max_turnover: Optional[float] = None

    # Long/short constraints
    allow_short: bool = False
    gross_leverage: Optional[float] = None

    # Cardinality constraints
    min_assets: Optional[int] = None
    max_assets: Optional[int] = None


@dataclass
class PortfolioAllocation:
    """Portfolio allocation result"""

    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float

    # Risk metrics
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    max_drawdown: Optional[float] = None

    # Portfolio characteristics
    concentration: float = 0.0
    turnover: float = 0.0
    transaction_cost: float = 0.0

    # Factor exposures
    factor_exposures: Dict[str, float] = field(default_factory=dict)
    sector_allocations: Dict[str, float] = field(default_factory=dict)

    # Metadata
    optimization_method: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class BaseOptimizer(ABC):
    """Base class for portfolio optimizers"""

    def __init__(self, constraints: OptimizationConstraints):
        self.constraints = constraints

    @abstractmethod
    def optimize(
        self, expected_returns: pd.Series, covariance_matrix: pd.DataFrame, **kwargs
    ) -> PortfolioAllocation:
        """Optimize portfolio allocation"""
        pass

    def _calculate_portfolio_metrics(
        self,
        weights: np.ndarray,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        risk_free_rate: float = 0.02,
    ) -> Tuple[float, float, float]:
        """Calculate portfolio return, volatility, and Sharpe ratio"""
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_variance = np.dot(weights.T, np.dot(covariance_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)

        sharpe_ratio = (
            (portfolio_return - risk_free_rate) / portfolio_volatility
            if portfolio_volatility > 0
            else 0
        )

        return portfolio_return, portfolio_volatility, sharpe_ratio

    def _calculate_var_cvar(
        self,
        weights: np.ndarray,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        confidence_level: float = 0.95,
    ) -> Tuple[float, float]:
        """Calculate Value at Risk and Conditional Value at Risk"""
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))

        # Assuming normal distribution
        z_score = norm.ppf(1 - confidence_level)
        var = portfolio_return + z_score * portfolio_volatility

        # CVaR calculation
        cvar = portfolio_return - portfolio_volatility * norm.pdf(z_score) / (1 - confidence_level)

        return var, cvar


class MeanVarianceOptimizer(BaseOptimizer):
    """Modern Portfolio Theory mean-variance optimizer"""

    def optimize(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        risk_aversion: float = 1.0,
        **kwargs,
    ) -> PortfolioAllocation:
        """Optimize using mean-variance framework"""
        n_assets = len(expected_returns)

        # Decision variable: portfolio weights
        w = cp.Variable(n_assets)

        # Objective: maximize utility (return - risk_aversion * variance)
        portfolio_return = expected_returns.values.T @ w
        portfolio_variance = cp.quad_form(w, covariance_matrix.values)
        objective = cp.Maximize(portfolio_return - 0.5 * risk_aversion * portfolio_variance)

        # Constraints
        constraints = [
            cp.sum(w) == self.constraints.sum_weights,  # Weights sum to 1
            w >= self.constraints.min_weight,  # Min weight
            w <= self.constraints.max_weight,  # Max weight
        ]

        # Additional constraints
        if not self.constraints.allow_short:
            constraints.append(w >= 0)

        if self.constraints.max_volatility:
            constraints.append(cp.sqrt(portfolio_variance) <= self.constraints.max_volatility)

        # Solve optimization problem
        problem = cp.Problem(objective, constraints)
        problem.solve()

        if problem.status not in ["infeasible", "unbounded"]:
            optimal_weights = w.value
            weights_dict = dict(zip(expected_returns.index, optimal_weights))

            # Calculate metrics
            port_return, port_vol, sharpe = self._calculate_portfolio_metrics(
                optimal_weights, expected_returns, covariance_matrix
            )

            var_95, cvar_95 = self._calculate_var_cvar(
                optimal_weights, expected_returns, covariance_matrix
            )

            return PortfolioAllocation(
                weights=weights_dict,
                expected_return=port_return,
                expected_volatility=port_vol,
                sharpe_ratio=sharpe,
                var_95=var_95,
                cvar_95=cvar_95,
                concentration=np.sum(np.square(optimal_weights)),  # Herfindahl index
                optimization_method="mean_variance",
            )
        else:
            raise ValueError(f"Optimization failed with status: {problem.status}")


class RiskParityOptimizer(BaseOptimizer):
    """Risk parity portfolio optimizer"""

    def optimize(
        self, expected_returns: pd.Series, covariance_matrix: pd.DataFrame, **kwargs
    ) -> PortfolioAllocation:
        """Optimize using risk parity approach"""

        def risk_parity_objective(weights, cov_matrix):
            """Risk parity objective function"""
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            target_contrib = np.ones(len(weights)) / len(weights)

            return np.sum((contrib / np.sum(contrib) - target_contrib) ** 2)

        # Initial guess: equal weights
        n_assets = len(expected_returns)
        initial_weights = np.ones(n_assets) / n_assets

        # Constraints
        constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1.0}]  # Weights sum to 1

        # Bounds
        bounds = [
            (self.constraints.min_weight, self.constraints.max_weight) for _ in range(n_assets)
        ]

        if not self.constraints.allow_short:
            bounds = [(0, self.constraints.max_weight) for _ in range(n_assets)]

        # Optimize
        result = minimize(
            risk_parity_objective,
            initial_weights,
            args=(covariance_matrix.values,),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            optimal_weights = result.x
            weights_dict = dict(zip(expected_returns.index, optimal_weights))

            # Calculate metrics
            port_return, port_vol, sharpe = self._calculate_portfolio_metrics(
                optimal_weights, expected_returns, covariance_matrix
            )

            var_95, cvar_95 = self._calculate_var_cvar(
                optimal_weights, expected_returns, covariance_matrix
            )

            return PortfolioAllocation(
                weights=weights_dict,
                expected_return=port_return,
                expected_volatility=port_vol,
                sharpe_ratio=sharpe,
                var_95=var_95,
                cvar_95=cvar_95,
                concentration=np.sum(np.square(optimal_weights)),
                optimization_method="risk_parity",
            )
        else:
            raise ValueError(f"Risk parity optimization failed: {result.message}")


class BlackLittermanOptimizer(BaseOptimizer):
    """Black-Litterman portfolio optimizer"""

    def optimize(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        market_caps: Optional[pd.Series] = None,
        views: Optional[Dict[str, float]] = None,
        view_uncertainties: Optional[Dict[str, float]] = None,
        tau: float = 0.1,
        risk_aversion: float = 3.0,
        **kwargs,
    ) -> PortfolioAllocation:
        """Optimize using Black-Litterman model"""

        # Market capitalization weights (if not provided, use equal weights)
        if market_caps is None:
            market_weights = np.ones(len(expected_returns)) / len(expected_returns)
        else:
            market_weights = (market_caps / market_caps.sum()).values

        # Implied equilibrium returns
        implied_returns = risk_aversion * np.dot(covariance_matrix.values, market_weights)

        # If no views provided, use implied returns
        if views is None or len(views) == 0:
            bl_returns = pd.Series(implied_returns, index=expected_returns.index)
            bl_cov = covariance_matrix
        else:
            # Black-Litterman adjustment with views
            P = np.zeros((len(views), len(expected_returns)))  # Picking matrix
            Q = np.zeros(len(views))  # View returns
            Omega = np.zeros((len(views), len(views)))  # View uncertainty matrix

            for i, (asset, view_return) in enumerate(views.items()):
                asset_idx = expected_returns.index.get_loc(asset)
                P[i, asset_idx] = 1.0
                Q[i] = view_return

                # View uncertainty (if not provided, use default)
                if view_uncertainties and asset in view_uncertainties:
                    Omega[i, i] = view_uncertainties[asset]
                else:
                    Omega[i, i] = tau * covariance_matrix.iloc[asset_idx, asset_idx]

            # Black-Litterman formulas
            tau_cov = tau * covariance_matrix.values

            # New expected returns
            M1 = np.linalg.inv(tau_cov)
            M2 = np.dot(P.T, np.dot(np.linalg.inv(Omega), P))
            M3 = np.dot(np.linalg.inv(tau_cov), implied_returns)
            M4 = np.dot(P.T, np.dot(np.linalg.inv(Omega), Q))

            bl_returns = np.dot(np.linalg.inv(M1 + M2), M3 + M4)
            bl_returns = pd.Series(bl_returns, index=expected_returns.index)

            # New covariance matrix
            bl_cov = np.linalg.inv(M1 + M2)
            bl_cov = pd.DataFrame(
                bl_cov, index=covariance_matrix.index, columns=covariance_matrix.columns
            )

        # Now optimize using mean-variance with BL inputs
        mv_optimizer = MeanVarianceOptimizer(self.constraints)
        allocation = mv_optimizer.optimize(bl_returns, bl_cov, risk_aversion)
        allocation.optimization_method = "black_litterman"

        return allocation


class CVaROptimizer(BaseOptimizer):
    """Conditional Value at Risk optimizer"""

    def optimize(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        scenarios: Optional[pd.DataFrame] = None,
        confidence_level: float = 0.95,
        **kwargs,
    ) -> PortfolioAllocation:
        """Optimize portfolio to minimize CVaR"""

        if scenarios is None:
            # Generate scenarios from normal distribution
            n_scenarios = 10000
            mean_returns = expected_returns.values
            cov_matrix = covariance_matrix.values

            scenarios = np.random.multivariate_normal(mean_returns, cov_matrix, n_scenarios)
            scenarios = pd.DataFrame(scenarios, columns=expected_returns.index)

        n_assets = len(expected_returns)
        n_scenarios = len(scenarios)

        # Decision variables
        w = cp.Variable(n_assets)  # Portfolio weights
        alpha = cp.Variable()  # VaR
        u = cp.Variable(n_scenarios, nonneg=True)  # Auxiliary variables for CVaR

        # Portfolio returns for each scenario
        portfolio_returns = scenarios.values @ w

        # CVaR objective
        cvar = alpha - cp.sum(u) / (n_scenarios * (1 - confidence_level))
        objective = cp.Maximize(cvar)

        # Constraints
        constraints = [
            cp.sum(w) == 1,  # Weights sum to 1
            w >= self.constraints.min_weight,
            w <= self.constraints.max_weight,
            u >= 0,
            u >= alpha - portfolio_returns,  # CVaR constraints
        ]

        if not self.constraints.allow_short:
            constraints.append(w >= 0)

        # Solve
        problem = cp.Problem(objective, constraints)
        problem.solve()

        if problem.status not in ["infeasible", "unbounded"]:
            optimal_weights = w.value
            weights_dict = dict(zip(expected_returns.index, optimal_weights))

            # Calculate metrics
            port_return, port_vol, sharpe = self._calculate_portfolio_metrics(
                optimal_weights, expected_returns, covariance_matrix
            )

            var_95, cvar_95 = self._calculate_var_cvar(
                optimal_weights, expected_returns, covariance_matrix
            )

            return PortfolioAllocation(
                weights=weights_dict,
                expected_return=port_return,
                expected_volatility=port_vol,
                sharpe_ratio=sharpe,
                var_95=var_95,
                cvar_95=cvar_95,
                concentration=np.sum(np.square(optimal_weights)),
                optimization_method="cvar",
            )
        else:
            raise ValueError(f"CVaR optimization failed with status: {problem.status}")


class KellyCriterionOptimizer(BaseOptimizer):
    """Kelly Criterion optimizer for growth-optimal portfolios"""

    def optimize(
        self, expected_returns: pd.Series, covariance_matrix: pd.DataFrame, **kwargs
    ) -> PortfolioAllocation:
        """Optimize using Kelly Criterion"""

        # Kelly optimal weights: w* = Σ^(-1) * μ
        # where μ is expected excess returns and Σ is covariance matrix

        try:
            inv_cov = np.linalg.inv(covariance_matrix.values)
            kelly_weights = np.dot(inv_cov, expected_returns.values)

            # Apply constraints
            if not self.constraints.allow_short:
                kelly_weights = np.maximum(kelly_weights, 0)

            kelly_weights = np.clip(
                kelly_weights, self.constraints.min_weight, self.constraints.max_weight
            )

            # Normalize to sum to 1
            if np.sum(kelly_weights) > 0:
                kelly_weights = kelly_weights / np.sum(kelly_weights)
            else:
                # Fall back to equal weights
                kelly_weights = np.ones(len(expected_returns)) / len(expected_returns)

            weights_dict = dict(zip(expected_returns.index, kelly_weights))

            # Calculate metrics
            port_return, port_vol, sharpe = self._calculate_portfolio_metrics(
                kelly_weights, expected_returns, covariance_matrix
            )

            var_95, cvar_95 = self._calculate_var_cvar(
                kelly_weights, expected_returns, covariance_matrix
            )

            return PortfolioAllocation(
                weights=weights_dict,
                expected_return=port_return,
                expected_volatility=port_vol,
                sharpe_ratio=sharpe,
                var_95=var_95,
                cvar_95=cvar_95,
                concentration=np.sum(np.square(kelly_weights)),
                optimization_method="kelly_criterion",
            )

        except np.linalg.LinAlgError:
            # Covariance matrix is singular, use regularization
            regularization = 1e-8 * np.eye(len(expected_returns))
            regularized_cov = covariance_matrix.values + regularization

            inv_cov = np.linalg.inv(regularized_cov)
            kelly_weights = np.dot(inv_cov, expected_returns.values)
            kelly_weights = kelly_weights / np.sum(np.abs(kelly_weights))

            weights_dict = dict(zip(expected_returns.index, kelly_weights))

            port_return, port_vol, sharpe = self._calculate_portfolio_metrics(
                kelly_weights, expected_returns, covariance_matrix
            )

            return PortfolioAllocation(
                weights=weights_dict,
                expected_return=port_return,
                expected_volatility=port_vol,
                sharpe_ratio=sharpe,
                optimization_method="kelly_criterion_regularized",
            )


class AdvancedPortfolioOptimizer:
    """Advanced portfolio optimization system"""

    def __init__(self, constraints: Optional[OptimizationConstraints] = None):
        self.constraints = constraints or OptimizationConstraints()

        # Initialize optimizers
        self.optimizers = {
            OptimizationObjective.MEAN_VARIANCE: MeanVarianceOptimizer(self.constraints),
            OptimizationObjective.RISK_PARITY: RiskParityOptimizer(self.constraints),
            OptimizationObjective.BLACK_LITTERMAN: BlackLittermanOptimizer(self.constraints),
            OptimizationObjective.CVaR: CVaROptimizer(self.constraints),
            OptimizationObjective.KELLY_CRITERION: KellyCriterionOptimizer(self.constraints),
        }

        self.optimization_history = []

    def optimize_portfolio(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        objective: OptimizationObjective = OptimizationObjective.MEAN_VARIANCE,
        **optimizer_kwargs,
    ) -> PortfolioAllocation:
        """Optimize portfolio using specified objective"""

        if objective not in self.optimizers:
            raise ValueError(f"Unsupported optimization objective: {objective}")

        optimizer = self.optimizers[objective]
        allocation = optimizer.optimize(expected_returns, covariance_matrix, **optimizer_kwargs)

        # Add additional metrics
        allocation = self._enhance_allocation_metrics(
            allocation, expected_returns, covariance_matrix
        )

        # Store in history
        self.optimization_history.append(allocation)

        return allocation

    def multi_objective_optimization(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        objectives: List[OptimizationObjective],
        weights: Optional[List[float]] = None,
    ) -> PortfolioAllocation:
        """Combine multiple optimization objectives"""

        if weights is None:
            weights = [1.0 / len(objectives)] * len(objectives)

        if len(weights) != len(objectives):
            raise ValueError("Number of weights must match number of objectives")

        # Get individual allocations
        allocations = []
        for obj in objectives:
            allocation = self.optimize_portfolio(expected_returns, covariance_matrix, obj)
            allocations.append(allocation)

        # Combine allocations using weights
        combined_weights = {}
        for asset in expected_returns.index:
            combined_weights[asset] = sum(
                w * alloc.weights.get(asset, 0) for w, alloc in zip(weights, allocations)
            )

        # Normalize
        total_weight = sum(combined_weights.values())
        if total_weight > 0:
            combined_weights = {k: v / total_weight for k, v in combined_weights.items()}

        # Calculate metrics for combined portfolio
        weights_array = np.array([combined_weights[asset] for asset in expected_returns.index])
        port_return, port_vol, sharpe = self.optimizers[objectives[0]]._calculate_portfolio_metrics(
            weights_array, expected_returns, covariance_matrix
        )

        var_95, cvar_95 = self.optimizers[objectives[0]]._calculate_var_cvar(
            weights_array, expected_returns, covariance_matrix
        )

        return PortfolioAllocation(
            weights=combined_weights,
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            var_95=var_95,
            cvar_95=cvar_95,
            concentration=np.sum(np.square(weights_array)),
            optimization_method=f"multi_objective_{'+'.join([obj.value for obj in objectives])}",
        )

    def efficient_frontier(
        self, expected_returns: pd.Series, covariance_matrix: pd.DataFrame, n_points: int = 20
    ) -> pd.DataFrame:
        """Generate efficient frontier"""

        min_vol_allocation = self.optimize_portfolio(
            expected_returns,
            covariance_matrix,
            OptimizationObjective.MEAN_VARIANCE,
            risk_aversion=1000,  # High risk aversion for min vol
        )

        max_return = expected_returns.max()
        min_return = min_vol_allocation.expected_return

        target_returns = np.linspace(min_return, max_return, n_points)

        frontier_data = []

        for target_return in target_returns:
            try:
                # Optimize for minimum variance given target return
                n_assets = len(expected_returns)
                w = cp.Variable(n_assets)

                portfolio_return = expected_returns.values.T @ w
                portfolio_variance = cp.quad_form(w, covariance_matrix.values)

                objective = cp.Minimize(portfolio_variance)
                constraints = [
                    cp.sum(w) == 1,
                    portfolio_return >= target_return,
                    w >= self.constraints.min_weight,
                    w <= self.constraints.max_weight,
                ]

                if not self.constraints.allow_short:
                    constraints.append(w >= 0)

                problem = cp.Problem(objective, constraints)
                problem.solve()

                if problem.status not in ["infeasible", "unbounded"]:
                    optimal_weights = w.value
                    port_return = np.dot(optimal_weights, expected_returns)
                    port_vol = np.sqrt(
                        np.dot(optimal_weights.T, np.dot(covariance_matrix.values, optimal_weights))
                    )

                    frontier_data.append(
                        {
                            "return": port_return,
                            "volatility": port_vol,
                            "sharpe": (port_return - 0.02) / port_vol if port_vol > 0 else 0,
                        }
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to compute efficient frontier point for return {target_return}: {e}"
                )
                continue

        return pd.DataFrame(frontier_data)

    def rebalance_portfolio(
        self,
        current_weights: Dict[str, float],
        target_allocation: PortfolioAllocation,
        rebalance_threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """Calculate rebalancing trades"""

        trades = {}
        total_deviation = 0

        for asset in target_allocation.weights:
            current_weight = current_weights.get(asset, 0)
            target_weight = target_allocation.weights[asset]
            deviation = abs(target_weight - current_weight)

            total_deviation += deviation

            if deviation > rebalance_threshold:
                trades[asset] = target_weight - current_weight

        transaction_cost = sum(
            abs(trade) * self.constraints.transaction_costs for trade in trades.values()
        )

        return {
            "trades": trades,
            "total_deviation": total_deviation,
            "transaction_cost": transaction_cost,
            "rebalance_needed": total_deviation > rebalance_threshold,
            "net_trades": sum(trades.values()),  # Should be close to 0
        }

    def _enhance_allocation_metrics(
        self,
        allocation: PortfolioAllocation,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
    ) -> PortfolioAllocation:
        """Add additional metrics to allocation"""

        weights_array = np.array(
            [allocation.weights.get(asset, 0) for asset in expected_returns.index]
        )

        # Calculate max drawdown (simplified)
        returns_series = expected_returns.values
        cumulative_returns = np.cumprod(1 + returns_series)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        allocation.max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0

        return allocation

    def plot_allocation(
        self, allocation: PortfolioAllocation, save_path: Optional[Path] = None
    ) -> None:
        """Plot portfolio allocation"""

        # Filter out zero weights
        non_zero_weights = {k: v for k, v in allocation.weights.items() if abs(v) > 0.001}

        if not non_zero_weights:
            logger.warning("No significant weights to plot")
            return

        plt.figure(figsize=(12, 8))

        # Pie chart of allocations
        plt.subplot(2, 2, 1)
        assets = list(non_zero_weights.keys())
        weights = list(non_zero_weights.values())

        plt.pie(weights, labels=assets, autopct="%1.1f%%", startangle=90)
        plt.title("Portfolio Allocation")

        # Bar chart of weights
        plt.subplot(2, 2, 2)
        plt.bar(range(len(assets)), weights)
        plt.xticks(range(len(assets)), assets, rotation=45)
        plt.ylabel("Weight")
        plt.title("Asset Weights")

        # Risk metrics
        plt.subplot(2, 2, 3)
        metrics = ["Expected Return", "Volatility", "Sharpe Ratio", "VaR 95%", "CVaR 95%"]
        values = [
            allocation.expected_return * 100,
            allocation.expected_volatility * 100,
            allocation.sharpe_ratio,
            allocation.var_95 * 100 if allocation.var_95 else 0,
            allocation.cvar_95 * 100 if allocation.cvar_95 else 0,
        ]

        plt.bar(metrics, values)
        plt.xticks(rotation=45)
        plt.ylabel("Value (%)")
        plt.title("Portfolio Metrics")

        # Summary text
        plt.subplot(2, 2, 4)
        plt.axis("off")
        summary_text = f"""
        Optimization Method: {allocation.optimization_method}
        Expected Return: {allocation.expected_return:.3f}
        Volatility: {allocation.expected_volatility:.3f}
        Sharpe Ratio: {allocation.sharpe_ratio:.3f}
        Concentration: {allocation.concentration:.3f}
        Number of Assets: {len(non_zero_weights)}
        """
        plt.text(0.1, 0.5, summary_text, fontsize=10, verticalalignment="center")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")

        plt.show()


# Example usage
if __name__ == "__main__":
    # Generate sample data
    np.random.seed(42)

    assets = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    n_assets = len(assets)

    # Expected returns (annual)
    expected_returns = pd.Series(np.random.uniform(0.05, 0.15, n_assets), index=assets)

    # Generate covariance matrix
    correlation_matrix = np.random.uniform(0.1, 0.7, (n_assets, n_assets))
    correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
    np.fill_diagonal(correlation_matrix, 1.0)

    volatilities = np.random.uniform(0.15, 0.35, n_assets)
    covariance_matrix = np.outer(volatilities, volatilities) * correlation_matrix
    covariance_matrix = pd.DataFrame(covariance_matrix, index=assets, columns=assets)

    # Initialize optimizer
    constraints = OptimizationConstraints(
        max_weight=0.4, transaction_costs=0.001, allow_short=False
    )

    optimizer = AdvancedPortfolioOptimizer(constraints)

    # Test different optimization methods
    objectives = [
        OptimizationObjective.MEAN_VARIANCE,
        OptimizationObjective.RISK_PARITY,
        OptimizationObjective.KELLY_CRITERION,
    ]

    results = {}

    for obj in objectives:
        try:
            allocation = optimizer.optimize_portfolio(expected_returns, covariance_matrix, obj)
            results[obj.value] = allocation

            print(f"\n{obj.value.upper()} Optimization:")
            print(f"Expected Return: {allocation.expected_return:.3f}")
            print(f"Volatility: {allocation.expected_volatility:.3f}")
            print(f"Sharpe Ratio: {allocation.sharpe_ratio:.3f}")
            print("Top 3 Holdings:")
            sorted_weights = sorted(
                allocation.weights.items(), key=lambda x: abs(x[1]), reverse=True
            )
            for asset, weight in sorted_weights[:3]:
                print(f"  {asset}: {weight:.3f}")

        except Exception as e:
            logger.error(f"Failed to optimize with {obj.value}: {e}")

    # Test multi-objective optimization
    try:
        multi_obj_allocation = optimizer.multi_objective_optimization(
            expected_returns,
            covariance_matrix,
            objectives=[OptimizationObjective.MEAN_VARIANCE, OptimizationObjective.RISK_PARITY],
            weights=[0.7, 0.3],
        )

        print(f"\nMULTI-OBJECTIVE Optimization:")
        print(f"Expected Return: {multi_obj_allocation.expected_return:.3f}")
        print(f"Volatility: {multi_obj_allocation.expected_volatility:.3f}")
        print(f"Sharpe Ratio: {multi_obj_allocation.sharpe_ratio:.3f}")

    except Exception as e:
        logger.error(f"Multi-objective optimization failed: {e}")

    # Generate efficient frontier
    try:
        frontier_df = optimizer.efficient_frontier(expected_returns, covariance_matrix, n_points=10)
        print(f"\nEfficient Frontier generated with {len(frontier_df)} points")
        print(f"Max Sharpe Ratio: {frontier_df['sharpe'].max():.3f}")

    except Exception as e:
        logger.error(f"Efficient frontier generation failed: {e}")

    logger.info("Advanced portfolio optimization demo completed")
