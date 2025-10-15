"""Risk management module for trading portfolios"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from mcli.ml.trading.models import Portfolio, Position, RiskLevel, TradingOrder
from mcli.ml.trading.trading_service import TradingService

logger = logging.getLogger(__name__)


class RiskManager:
    """Risk management system for trading portfolios"""

    def __init__(self, trading_service: TradingService):
        self.trading_service = trading_service
        self.db = trading_service.db

    def calculate_portfolio_risk(self, portfolio_id: UUID) -> Dict:
        """Calculate comprehensive risk metrics for a portfolio"""
        try:
            portfolio = self.trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                return {}

            positions = self.trading_service.get_portfolio_positions(portfolio_id)

            if not positions:
                return {
                    "total_risk": 0.0,
                    "concentration_risk": 0.0,
                    "var_95": 0.0,
                    "cvar_95": 0.0,
                    "max_position_risk": 0.0,
                    "portfolio_beta": 1.0,
                    "risk_score": 0.0,
                }

            # Calculate individual position risks
            position_risks = []
            total_market_value = sum(pos.market_value for pos in positions)

            for position in positions:
                position_risk = self._calculate_position_risk(position, total_market_value)
                position_risks.append(position_risk)

            # Calculate portfolio-level risk metrics
            portfolio_risk = self._calculate_portfolio_risk_metrics(positions, position_risks)

            return portfolio_risk

        except Exception as e:
            logger.error(f"Failed to calculate portfolio risk: {e}")
            return {}

    def _calculate_position_risk(self, position: Position, total_market_value: float) -> Dict:
        """Calculate risk metrics for an individual position"""
        try:
            # Position size as percentage of portfolio
            position_size_pct = (position.market_value / total_market_value) * 100

            # Volatility estimate (simplified - in practice, use historical data)
            volatility = self._estimate_volatility(position.symbol)

            # Value at Risk (simplified calculation)
            var_95 = position.market_value * volatility * 1.645  # 95% VaR

            # Position risk score (combination of size and volatility)
            risk_score = position_size_pct * volatility * 100

            return {
                "symbol": position.symbol,
                "position_size_pct": position_size_pct,
                "volatility": volatility,
                "var_95": var_95,
                "risk_score": risk_score,
                "market_value": position.market_value,
            }

        except Exception as e:
            logger.error(f"Failed to calculate position risk for {position.symbol}: {e}")
            return {}

    def _estimate_volatility(self, symbol: str, days: int = 30) -> float:
        """Estimate volatility for a symbol (simplified)"""
        try:
            # In practice, you would calculate historical volatility
            # For now, use a simplified approach based on market cap and sector
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            data = ticker.history(period=f"{days}d")

            if not data.empty and len(data) > 1:
                returns = data["Close"].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized
                return min(volatility, 1.0)  # Cap at 100%

            # Default volatility based on symbol characteristics
            if symbol in ["AAPL", "MSFT", "GOOGL", "AMZN"]:
                return 0.25  # Large cap tech
            elif symbol in ["TSLA", "NVDA", "AMD"]:
                return 0.45  # High volatility tech
            else:
                return 0.30  # Default

        except Exception as e:
            logger.error(f"Failed to estimate volatility for {symbol}: {e}")
            return 0.30  # Default volatility

    def _calculate_portfolio_risk_metrics(
        self, positions: List, position_risks: List[Dict]
    ) -> Dict:
        """Calculate portfolio-level risk metrics"""
        try:
            if not positions or not position_risks:
                return {}

            # Total portfolio risk (sum of individual position risks)
            total_risk = sum(risk["risk_score"] for risk in position_risks)

            # Concentration risk (Herfindahl-Hirschman Index)
            weights = [pos.weight for pos in positions]
            concentration_risk = sum(w**2 for w in weights) * 100

            # Portfolio Value at Risk (simplified)
            portfolio_var = sum(risk["var_95"] for risk in position_risks)

            # Conditional Value at Risk (simplified)
            portfolio_cvar = portfolio_var * 1.3  # Rough approximation

            # Maximum position risk
            max_position_risk = (
                max(risk["risk_score"] for risk in position_risks) if position_risks else 0
            )

            # Portfolio beta (simplified - assume equal weight)
            portfolio_beta = np.mean([self._estimate_beta(pos.symbol) for pos in positions])

            # Overall risk score (0-100)
            risk_score = min(total_risk + concentration_risk, 100)

            return {
                "total_risk": total_risk,
                "concentration_risk": concentration_risk,
                "var_95": portfolio_var,
                "cvar_95": portfolio_cvar,
                "max_position_risk": max_position_risk,
                "portfolio_beta": portfolio_beta,
                "risk_score": risk_score,
                "num_positions": len(positions),
            }

        except Exception as e:
            logger.error(f"Failed to calculate portfolio risk metrics: {e}")
            return {}

    def _estimate_beta(self, symbol: str) -> float:
        """Estimate beta for a symbol (simplified)"""
        try:
            # In practice, calculate beta against market index
            # For now, use simplified estimates
            beta_estimates = {
                "AAPL": 1.2,
                "MSFT": 1.1,
                "GOOGL": 1.3,
                "AMZN": 1.4,
                "TSLA": 2.0,
                "NVDA": 1.8,
                "AMD": 1.6,
                "META": 1.5,
                "JPM": 1.3,
                "BAC": 1.4,
                "WMT": 0.5,
                "JNJ": 0.7,
            }
            return beta_estimates.get(symbol, 1.0)
        except Exception as e:
            logger.error(f"Failed to estimate beta for {symbol}: {e}")
            return 1.0

    def check_risk_limits(self, portfolio_id: UUID, new_order: Dict) -> Tuple[bool, List[str]]:
        """Check if a new order would violate risk limits"""
        try:
            portfolio = self.trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                return False, ["Portfolio not found"]

            warnings = []

            # Get current positions
            positions = self.trading_service.get_portfolio_positions(portfolio_id)

            # Calculate new position size
            symbol = new_order["symbol"]
            quantity = new_order["quantity"]
            side = new_order["side"]

            # Estimate order value (simplified)
            order_value = self._estimate_order_value(symbol, quantity)
            new_position_size_pct = (order_value / float(portfolio.current_value)) * 100

            # Check position size limits
            max_position_size = 10.0  # 10% default
            if new_position_size_pct > max_position_size:
                warnings.append(
                    f"Position size ({new_position_size_pct:.1f}%) exceeds limit ({max_position_size}%)"
                )

            # Check if adding to existing position
            existing_position = next((pos for pos in positions if pos.symbol == symbol), None)
            if existing_position:
                if side == "buy":
                    new_total_size = (
                        (existing_position.market_value + order_value)
                        / float(portfolio.current_value)
                    ) * 100
                    if new_total_size > max_position_size:
                        warnings.append(
                            f"Total position size ({new_total_size:.1f}%) would exceed limit"
                        )

            # Check portfolio concentration
            if len(positions) >= 10:  # Max 10 positions
                warnings.append("Portfolio already has maximum number of positions")

            # Check buying power
            if side == "buy" and order_value > float(portfolio.cash_balance):
                warnings.append("Insufficient buying power for this order")

            # Check risk level compliance
            risk_level = getattr(portfolio, "risk_level", RiskLevel.MODERATE)
            if risk_level == RiskLevel.CONSERVATIVE and new_position_size_pct > 5.0:
                warnings.append("Position size too large for conservative risk level")
            elif risk_level == RiskLevel.AGGRESSIVE and new_position_size_pct > 20.0:
                warnings.append("Position size too large for aggressive risk level")

            return len(warnings) == 0, warnings

        except Exception as e:
            logger.error(f"Failed to check risk limits: {e}")
            return False, [f"Risk check failed: {e}"]

    def _estimate_order_value(self, symbol: str, quantity: int) -> float:
        """Estimate the value of an order"""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                price = float(data["Close"].iloc[-1])
                return price * quantity
            return 0.0
        except Exception as e:
            logger.error(f"Failed to estimate order value for {symbol}: {e}")
            return 0.0

    def calculate_position_size(
        self,
        portfolio_id: UUID,
        symbol: str,
        signal_strength: float,
        risk_level: RiskLevel = RiskLevel.MODERATE,
    ) -> float:
        """Calculate recommended position size based on signal strength and risk level"""
        try:
            portfolio = self.trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                return 0.0

            # Base position size based on risk level
            base_sizes = {
                RiskLevel.CONSERVATIVE: 0.02,  # 2%
                RiskLevel.MODERATE: 0.05,  # 5%
                RiskLevel.AGGRESSIVE: 0.10,  # 10%
            }
            base_size = base_sizes.get(risk_level, 0.05)

            # Adjust based on signal strength
            signal_multiplier = min(signal_strength * 2, 2.0)  # Cap at 2x

            # Calculate recommended position size
            recommended_size = base_size * signal_multiplier

            # Cap at maximum position size
            max_position_size = 0.20  # 20% max
            recommended_size = min(recommended_size, max_position_size)

            # Convert to dollar amount
            position_value = float(portfolio.current_value) * recommended_size

            return position_value

        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return 0.0

    def generate_risk_report(self, portfolio_id: UUID) -> Dict:
        """Generate comprehensive risk report for a portfolio"""
        try:
            portfolio = self.trading_service.get_portfolio(portfolio_id)
            if not portfolio:
                return {}

            # Get risk metrics
            risk_metrics = self.calculate_portfolio_risk(portfolio_id)

            # Get performance data
            performance_df = self.trading_service.get_portfolio_performance(portfolio_id, days=30)

            # Calculate additional metrics
            max_drawdown = 0.0
            if not performance_df.empty:
                cumulative_returns = (1 + performance_df["daily_return_pct"] / 100).cumprod()
                running_max = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns - running_max) / running_max
                max_drawdown = abs(drawdown.min()) * 100

            # Risk assessment
            risk_level = "LOW"
            if risk_metrics.get("risk_score", 0) > 70:
                risk_level = "HIGH"
            elif risk_metrics.get("risk_score", 0) > 40:
                risk_level = "MEDIUM"

            # Generate recommendations
            recommendations = self._generate_risk_recommendations(risk_metrics, max_drawdown)

            return {
                "portfolio_id": str(portfolio_id),
                "risk_level": risk_level,
                "risk_score": risk_metrics.get("risk_score", 0),
                "max_drawdown": max_drawdown,
                "concentration_risk": risk_metrics.get("concentration_risk", 0),
                "var_95": risk_metrics.get("var_95", 0),
                "cvar_95": risk_metrics.get("cvar_95", 0),
                "portfolio_beta": risk_metrics.get("portfolio_beta", 1.0),
                "num_positions": risk_metrics.get("num_positions", 0),
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate risk report: {e}")
            return {}

    def _generate_risk_recommendations(self, risk_metrics: Dict, max_drawdown: float) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []

        # Concentration risk
        if risk_metrics.get("concentration_risk", 0) > 50:
            recommendations.append("Consider diversifying portfolio - concentration risk is high")

        # Position count
        if risk_metrics.get("num_positions", 0) < 5:
            recommendations.append("Consider adding more positions for better diversification")
        elif risk_metrics.get("num_positions", 0) > 15:
            recommendations.append("Consider reducing number of positions for better focus")

        # Risk score
        if risk_metrics.get("risk_score", 0) > 70:
            recommendations.append("Portfolio risk is high - consider reducing position sizes")

        # Drawdown
        if max_drawdown > 20:
            recommendations.append("Maximum drawdown is high - consider risk management strategies")

        # Beta
        if risk_metrics.get("portfolio_beta", 1.0) > 1.5:
            recommendations.append("Portfolio beta is high - consider adding defensive positions")
        elif risk_metrics.get("portfolio_beta", 1.0) < 0.5:
            recommendations.append("Portfolio beta is low - consider adding growth positions")

        if not recommendations:
            recommendations.append("Portfolio risk profile looks good - no immediate concerns")

        return recommendations


def create_risk_manager(db_session: Session) -> RiskManager:
    """Create a risk manager instance"""
    trading_service = TradingService(db_session)
    return RiskManager(trading_service)
