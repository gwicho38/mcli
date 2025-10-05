"""Stock recommendation engine that combines all feature engineering components"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd

from .ensemble_features import (
    DynamicFeatureSelector,
    EnsembleFeatureBuilder,
    FeatureInteractionEngine,
)
from .political_features import (
    CongressionalTrackingFeatures,
    PolicyImpactFeatures,
    PoliticalInfluenceFeatures,
)
from .stock_features import (
    MarketRegimeFeatures,
    StockRecommendationFeatures,
    TechnicalIndicatorFeatures,
)

logger = logging.getLogger(__name__)


@dataclass
class RecommendationConfig:
    """Configuration for stock recommendation engine"""

    # Feature engineering components
    enable_technical_features: bool = True
    enable_political_features: bool = True
    enable_ensemble_features: bool = True
    enable_interaction_features: bool = True

    # Recommendation scoring
    recommendation_weights: Dict[str, float] = None
    risk_adjustment_factor: float = 0.1
    confidence_threshold: float = 0.6

    # Time horizons for recommendations
    short_term_days: int = 7
    medium_term_days: int = 30
    long_term_days: int = 90

    # Feature selection
    max_features: int = 200
    feature_selection_methods: List[str] = None

    # Output settings
    output_format: str = "detailed"  # "simple", "detailed", "full"
    save_feature_importance: bool = True

    def __post_init__(self):
        if self.recommendation_weights is None:
            self.recommendation_weights = {
                "technical_score": 0.3,
                "political_influence_score": 0.25,
                "market_regime_score": 0.2,
                "ensemble_score": 0.15,
                "risk_adjustment": 0.1,
            }

        if self.feature_selection_methods is None:
            self.feature_selection_methods = ["correlation", "mutual_info", "variance"]


@dataclass
class RecommendationResult:
    """Result from stock recommendation engine"""

    # Basic information
    ticker: str
    company_name: str
    recommendation_score: float
    confidence: float
    risk_level: str

    # Detailed scores
    technical_score: float
    political_influence_score: float
    market_regime_score: float
    ensemble_score: float

    # Time horizon predictions
    short_term_outlook: str
    medium_term_outlook: str
    long_term_outlook: str

    # Supporting information
    key_features: List[str]
    feature_importance: Dict[str, float]
    recommendation_reason: str
    warnings: List[str]

    # Metadata
    generated_at: datetime
    model_version: str


class StockRecommendationEngine:
    """Comprehensive stock recommendation engine"""

    def __init__(self, config: Optional[RecommendationConfig] = None):
        self.config = config or RecommendationConfig()

        # Initialize feature engineering components
        self.stock_features = StockRecommendationFeatures()
        self.technical_features = TechnicalIndicatorFeatures()
        self.market_regime_features = MarketRegimeFeatures()
        self.political_features = PoliticalInfluenceFeatures()
        self.congressional_features = CongressionalTrackingFeatures()
        self.policy_features = PolicyImpactFeatures()
        self.ensemble_builder = EnsembleFeatureBuilder()
        self.interaction_engine = FeatureInteractionEngine()
        self.feature_selector = DynamicFeatureSelector()

        # Cache for feature importance and model artifacts
        self.feature_importance_cache = {}
        self.model_artifacts = {}

    def generate_recommendation(
        self,
        trading_data: pd.DataFrame,
        stock_price_data: Optional[pd.DataFrame] = None,
        politician_metadata: Optional[pd.DataFrame] = None,
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> List[RecommendationResult]:
        """Generate stock recommendations based on politician trading data"""

        logger.info("Starting stock recommendation generation")

        # Extract comprehensive features
        features_df = self._extract_all_features(
            trading_data, stock_price_data, politician_metadata, market_data
        )

        # Generate recommendations for each stock
        recommendations = []
        stocks = features_df["ticker_cleaned"].dropna().unique()

        logger.info(f"Generating recommendations for {len(stocks)} stocks")

        for ticker in stocks:
            try:
                stock_data = features_df[features_df["ticker_cleaned"] == ticker].copy()
                if len(stock_data) == 0:
                    continue

                recommendation = self._generate_stock_recommendation(stock_data, ticker)
                if recommendation:
                    recommendations.append(recommendation)

            except Exception as e:
                logger.error(f"Failed to generate recommendation for {ticker}: {e}")

        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations

    def _extract_all_features(
        self,
        trading_data: pd.DataFrame,
        stock_price_data: Optional[pd.DataFrame],
        politician_metadata: Optional[pd.DataFrame],
        market_data: Optional[Dict[str, pd.DataFrame]],
    ) -> pd.DataFrame:
        """Extract all features for recommendation generation"""

        logger.info("Extracting comprehensive feature set")
        df = trading_data.copy()

        # Technical features (if stock price data available)
        if self.config.enable_technical_features and stock_price_data is not None:
            df = self._add_technical_features(df, stock_price_data)

        # Political influence features
        if self.config.enable_political_features:
            df = self._add_political_features(df, politician_metadata)

        # Market regime features
        if stock_price_data is not None:
            df = self._add_market_regime_features(df, stock_price_data, market_data)

        # Ensemble features
        if self.config.enable_ensemble_features:
            df = self._add_ensemble_features(df)

        # Feature interactions
        if self.config.enable_interaction_features:
            df = self._add_interaction_features(df)

        # Feature selection
        df = self._perform_feature_selection(df)

        logger.info(f"Final feature set: {len(df.columns)} features")
        return df

    def _add_technical_features(
        self, df: pd.DataFrame, stock_price_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Add technical analysis features"""
        logger.info("Adding technical features")

        # Merge stock price data
        if "ticker_cleaned" in df.columns and "symbol" in stock_price_data.columns:
            # Group by ticker and add technical features
            enhanced_df = []

            for ticker in df["ticker_cleaned"].dropna().unique():
                ticker_trading_data = df[df["ticker_cleaned"] == ticker].copy()
                ticker_price_data = stock_price_data[stock_price_data["symbol"] == ticker].copy()

                if len(ticker_price_data) > 0:
                    # Extract technical features
                    price_features = self.stock_features.extract_features(ticker_price_data)
                    technical_features = self.technical_features.extract_advanced_indicators(
                        price_features
                    )

                    # Merge with trading data based on date
                    if (
                        "transaction_date_dt" in ticker_trading_data.columns
                        and "date" in technical_features.columns
                    ):
                        merged = pd.merge_asof(
                            ticker_trading_data.sort_values("transaction_date_dt"),
                            technical_features.sort_values("date"),
                            left_on="transaction_date_dt",
                            right_on="date",
                            direction="backward",
                        )
                        enhanced_df.append(merged)
                    else:
                        # Use latest technical features for all trades
                        latest_features = technical_features.iloc[-1:]
                        for col in technical_features.columns:
                            if col not in ["date", "symbol"]:
                                ticker_trading_data[col] = latest_features[col].iloc[0]
                        enhanced_df.append(ticker_trading_data)
                else:
                    enhanced_df.append(ticker_trading_data)

            if enhanced_df:
                df = pd.concat(enhanced_df, ignore_index=True)

        return df

    def _add_political_features(
        self, df: pd.DataFrame, politician_metadata: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        """Add political influence features"""
        logger.info("Adding political features")

        # Political influence features
        df = self.political_features.extract_influence_features(df, politician_metadata)

        # Congressional tracking features
        df = self.congressional_features.extract_disclosure_features(df)
        df = self.congressional_features.extract_reporting_patterns(df)

        # Policy impact features
        df = self.policy_features.extract_policy_timing_features(df)

        return df

    def _add_market_regime_features(
        self,
        df: pd.DataFrame,
        stock_price_data: pd.DataFrame,
        market_data: Optional[Dict[str, pd.DataFrame]],
    ) -> pd.DataFrame:
        """Add market regime features"""
        logger.info("Adding market regime features")

        # Add market regime features from stock price data
        regime_features = self.market_regime_features.extract_regime_features(stock_price_data)

        # Merge regime features
        if "ticker_cleaned" in df.columns and "symbol" in regime_features.columns:
            df = pd.merge(
                df,
                regime_features[["symbol", "vol_regime", "trend_regime", "volume_regime"]],
                left_on="ticker_cleaned",
                right_on="symbol",
                how="left",
            )

        return df

    def _add_ensemble_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ensemble features"""
        logger.info("Adding ensemble features")

        # Build ensemble features
        df = self.ensemble_builder.build_ensemble_features(
            df,
            target_column=None,  # No specific target for feature generation
            include_interactions=False,  # Will be added separately
            include_clustering=True,
            include_rolling=True,
        )

        return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add feature interactions"""
        logger.info("Adding interaction features")

        # Get important feature pairs (mock implementation)
        numerical_features = [
            col
            for col in df.columns
            if df[col].dtype in ["int64", "float64"] and not col.startswith("target_")
        ]

        if len(numerical_features) >= 2:
            # Select top features for interactions (limit to avoid explosion)
            top_features = numerical_features[:15]
            feature_pairs = [
                (top_features[i], top_features[j])
                for i in range(len(top_features))
                for j in range(i + 1, len(top_features))
            ][:20]

            df = self.interaction_engine.generate_advanced_interactions(df, feature_pairs)

        return df

    def _perform_feature_selection(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform feature selection"""
        logger.info("Performing feature selection")

        # Create a synthetic target for feature selection if none exists
        if "target_recommendation_score" not in df.columns:
            # Create synthetic target based on transaction patterns
            df["synthetic_target"] = (
                np.log1p(df.get("transaction_amount_cleaned", 0)) * 0.3
                + df.get("total_influence", 0.5) * 0.4
                + np.random.random(len(df)) * 0.3
            )
            target_col = "synthetic_target"
        else:
            target_col = "target_recommendation_score"

        # Apply feature selection if we have enough features
        feature_cols = [
            col for col in df.columns if col not in [target_col] and not col.startswith("target_")
        ]

        if len(feature_cols) > self.config.max_features:
            try:
                selected_df, selection_info = self.feature_selector.select_features(
                    df, target_col, self.config.feature_selection_methods
                )

                # Keep original non-feature columns
                non_feature_cols = [col for col in df.columns if col not in feature_cols]
                final_df = pd.concat(
                    [
                        df[non_feature_cols],
                        selected_df.drop(
                            columns=[target_col] if target_col in selected_df.columns else []
                        ),
                    ],
                    axis=1,
                )

                logger.info(
                    f"Selected {len(selected_df.columns)-1} features from {len(feature_cols)}"
                )
                return final_df
            except Exception as e:
                logger.warning(f"Feature selection failed: {e}")

        # Remove synthetic target if we created it
        if "synthetic_target" in df.columns:
            df = df.drop(columns=["synthetic_target"])

        return df

    def _generate_stock_recommendation(
        self, stock_data: pd.DataFrame, ticker: str
    ) -> Optional[RecommendationResult]:
        """Generate recommendation for a specific stock"""

        try:
            # Calculate component scores
            technical_score = self._calculate_technical_score(stock_data)
            political_score = self._calculate_political_score(stock_data)
            regime_score = self._calculate_regime_score(stock_data)
            ensemble_score = self._calculate_ensemble_score(stock_data)

            # Combine scores using weights
            weights = self.config.recommendation_weights
            final_score = (
                technical_score * weights.get("technical_score", 0.3)
                + political_score * weights.get("political_influence_score", 0.25)
                + regime_score * weights.get("market_regime_score", 0.2)
                + ensemble_score * weights.get("ensemble_score", 0.15)
            )

            # Risk adjustment
            risk_level = self._assess_risk_level(stock_data)
            risk_multiplier = 1.0 - (
                self.config.risk_adjustment_factor * self._risk_to_numeric(risk_level)
            )
            final_score *= risk_multiplier

            # Calculate confidence
            confidence = self._calculate_confidence(stock_data, final_score)

            # Generate outlooks
            short_outlook, medium_outlook, long_outlook = self._generate_outlooks(
                stock_data, final_score
            )

            # Get key features and explanations
            key_features, feature_importance = self._get_key_features(stock_data)
            recommendation_reason = self._generate_explanation(
                stock_data, final_score, key_features
            )

            # Generate warnings
            warnings = self._generate_warnings(stock_data, final_score)

            # Get company name
            company_name = (
                stock_data.get("asset_name_cleaned", {}).iloc[0] if len(stock_data) > 0 else ticker
            )

            return RecommendationResult(
                ticker=ticker,
                company_name=str(company_name),
                recommendation_score=round(final_score, 3),
                confidence=round(confidence, 3),
                risk_level=risk_level,
                technical_score=round(technical_score, 3),
                political_influence_score=round(political_score, 3),
                market_regime_score=round(regime_score, 3),
                ensemble_score=round(ensemble_score, 3),
                short_term_outlook=short_outlook,
                medium_term_outlook=medium_outlook,
                long_term_outlook=long_outlook,
                key_features=key_features,
                feature_importance=feature_importance,
                recommendation_reason=recommendation_reason,
                warnings=warnings,
                generated_at=datetime.now(),
                model_version="1.0.0",
            )

        except Exception as e:
            logger.error(f"Failed to generate recommendation for {ticker}: {e}")
            return None

    def _calculate_technical_score(self, stock_data: pd.DataFrame) -> float:
        """Calculate technical analysis score"""
        try:
            technical_indicators = []

            # RSI score
            if "rsi" in stock_data.columns:
                rsi = stock_data["rsi"].mean()
                if 30 <= rsi <= 70:
                    technical_indicators.append(0.7)  # Neutral zone
                elif rsi < 30:
                    technical_indicators.append(0.9)  # Oversold - buy signal
                else:
                    technical_indicators.append(0.3)  # Overbought - sell signal

            # MACD score
            if "macd_bullish" in stock_data.columns:
                macd_bullish = stock_data["macd_bullish"].mean()
                technical_indicators.append(macd_bullish)

            # Trend score
            if "trend_strength_20" in stock_data.columns:
                trend_strength = stock_data["trend_strength_20"].mean()
                technical_indicators.append(max(0, min(1, trend_strength)))

            # Volume score
            if "volume_ratio_20" in stock_data.columns:
                volume_ratio = stock_data["volume_ratio_20"].mean()
                volume_score = min(1.0, max(0.0, volume_ratio / 2))
                technical_indicators.append(volume_score)

            return np.mean(technical_indicators) if technical_indicators else 0.5

        except Exception as e:
            logger.warning(f"Failed to calculate technical score: {e}")
            return 0.5

    def _calculate_political_score(self, stock_data: pd.DataFrame) -> float:
        """Calculate political influence score"""
        try:
            political_factors = []

            # Total influence
            if "total_influence" in stock_data.columns:
                influence = stock_data["total_influence"].mean()
                political_factors.append(min(1.0, influence))

            # Committee alignment
            if "committee_sector_alignment" in stock_data.columns:
                alignment = stock_data["committee_sector_alignment"].mean()
                political_factors.append(alignment)

            # Trading frequency score
            if "trading_frequency_score" in stock_data.columns:
                frequency = stock_data["trading_frequency_score"].mean()
                political_factors.append(min(1.0, frequency))

            # Policy relevance
            if "policy_relevant_trade" in stock_data.columns:
                policy_relevance = stock_data["policy_relevant_trade"].mean()
                political_factors.append(policy_relevance)

            return np.mean(political_factors) if political_factors else 0.5

        except Exception as e:
            logger.warning(f"Failed to calculate political score: {e}")
            return 0.5

    def _calculate_regime_score(self, stock_data: pd.DataFrame) -> float:
        """Calculate market regime score"""
        try:
            regime_factors = []

            # Volatility regime
            if "vol_regime" in stock_data.columns:
                vol_regime = (
                    stock_data["vol_regime"].mode().iloc[0] if len(stock_data) > 0 else "medium_vol"
                )
                vol_score = {"low_vol": 0.8, "medium_vol": 0.6, "high_vol": 0.4}.get(
                    vol_regime, 0.5
                )
                regime_factors.append(vol_score)

            # Trend regime
            if "trend_regime" in stock_data.columns:
                trend_regime = (
                    stock_data["trend_regime"].mode().iloc[0] if len(stock_data) > 0 else "sideways"
                )
                trend_score = {"bullish": 0.9, "sideways": 0.5, "bearish": 0.2}.get(
                    trend_regime, 0.5
                )
                regime_factors.append(trend_score)

            # Volume regime
            if "volume_regime" in stock_data.columns:
                volume_regime = (
                    stock_data["volume_regime"].mode().iloc[0]
                    if len(stock_data) > 0
                    else "normal_volume"
                )
                volume_score = {"high_volume": 0.7, "normal_volume": 0.6, "low_volume": 0.4}.get(
                    volume_regime, 0.5
                )
                regime_factors.append(volume_score)

            return np.mean(regime_factors) if regime_factors else 0.5

        except Exception as e:
            logger.warning(f"Failed to calculate regime score: {e}")
            return 0.5

    def _calculate_ensemble_score(self, stock_data: pd.DataFrame) -> float:
        """Calculate ensemble model score"""
        try:
            # Use cluster-based scoring as proxy for ensemble
            ensemble_factors = []

            if "cluster_distance" in stock_data.columns:
                # Lower distance = more typical pattern = higher score
                distance = stock_data["cluster_distance"].mean()
                normalized_distance = min(1.0, distance / 10)  # Normalize
                score = 1.0 - normalized_distance
                ensemble_factors.append(score)

            # Use polynomial features if available
            poly_cols = [col for col in stock_data.columns if col.startswith("poly_")]
            if poly_cols:
                poly_score = abs(stock_data[poly_cols].mean().mean())
                ensemble_factors.append(min(1.0, poly_score))

            return np.mean(ensemble_factors) if ensemble_factors else 0.5

        except Exception as e:
            logger.warning(f"Failed to calculate ensemble score: {e}")
            return 0.5

    def _assess_risk_level(self, stock_data: pd.DataFrame) -> str:
        """Assess risk level for the stock"""
        try:
            risk_factors = []

            # Volatility risk
            if "volatility_20" in stock_data.columns:
                volatility = stock_data["volatility_20"].mean()
                risk_factors.append(min(1.0, volatility * 10))

            # Trading concentration risk
            if "total_influence" in stock_data.columns:
                influence = stock_data["total_influence"].mean()
                risk_factors.append(min(1.0, influence))

            # Policy risk
            if "policy_relevant_trade" in stock_data.columns:
                policy_exposure = stock_data["policy_relevant_trade"].mean()
                risk_factors.append(policy_exposure)

            avg_risk = np.mean(risk_factors) if risk_factors else 0.5

            if avg_risk < 0.3:
                return "low"
            elif avg_risk < 0.7:
                return "medium"
            else:
                return "high"

        except Exception as e:
            logger.warning(f"Failed to assess risk level: {e}")
            return "medium"

    def _risk_to_numeric(self, risk_level: str) -> float:
        """Convert risk level to numeric value"""
        return {"low": 0.2, "medium": 0.5, "high": 0.8}.get(risk_level, 0.5)

    def _calculate_confidence(self, stock_data: pd.DataFrame, final_score: float) -> float:
        """Calculate confidence in the recommendation"""
        try:
            confidence_factors = []

            # Data completeness
            non_null_ratio = stock_data.notna().mean().mean()
            confidence_factors.append(non_null_ratio)

            # Number of data points
            data_points_factor = min(1.0, len(stock_data) / 10)
            confidence_factors.append(data_points_factor)

            # Score consistency (how far from neutral)
            score_confidence = abs(final_score - 0.5) * 2
            confidence_factors.append(score_confidence)

            return np.mean(confidence_factors)

        except Exception as e:
            logger.warning(f"Failed to calculate confidence: {e}")
            return 0.5

    def _generate_outlooks(
        self, stock_data: pd.DataFrame, final_score: float
    ) -> Tuple[str, str, str]:
        """Generate short, medium, and long-term outlooks"""

        def score_to_outlook(score):
            if score >= 0.7:
                return "bullish"
            elif score >= 0.3:
                return "neutral"
            else:
                return "bearish"

        # Base outlook on final score with some variation
        short_term = score_to_outlook(final_score + np.random.normal(0, 0.1))
        medium_term = score_to_outlook(final_score + np.random.normal(0, 0.05))
        long_term = score_to_outlook(final_score)

        return short_term, medium_term, long_term

    def _get_key_features(self, stock_data: pd.DataFrame) -> Tuple[List[str], Dict[str, float]]:
        """Get key features and their importance"""
        try:
            # Get numerical features
            numerical_features = [
                col
                for col in stock_data.columns
                if stock_data[col].dtype in ["int64", "float64"]
                and not col.startswith("target_")
                and stock_data[col].notna().sum() > 0
            ]

            # Calculate feature importance based on variance and mean values
            feature_importance = {}
            for feature in numerical_features[:10]:  # Top 10 features
                try:
                    value = abs(stock_data[feature].mean())
                    variance = stock_data[feature].var()
                    importance = value * (1 + variance)
                    feature_importance[feature] = importance
                except:
                    feature_importance[feature] = 0

            # Sort by importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            key_features = [f[0] for f in sorted_features[:5]]

            # Normalize importance scores
            max_importance = max(feature_importance.values()) if feature_importance else 1
            normalized_importance = {k: v / max_importance for k, v in feature_importance.items()}

            return key_features, normalized_importance

        except Exception as e:
            logger.warning(f"Failed to get key features: {e}")
            return [], {}

    def _generate_explanation(
        self, stock_data: pd.DataFrame, final_score: float, key_features: List[str]
    ) -> str:
        """Generate human-readable explanation for the recommendation"""

        try:
            if final_score >= 0.7:
                base_sentiment = "Strong buy signal"
            elif final_score >= 0.3:
                base_sentiment = "Neutral outlook"
            else:
                base_sentiment = "Caution advised"

            # Add key drivers
            drivers = []
            if "total_influence" in key_features:
                drivers.append("high political influence")
            if "rsi" in key_features:
                drivers.append("favorable technical indicators")
            if "committee_sector_alignment" in key_features:
                drivers.append("strong committee-sector alignment")

            if drivers:
                explanation = f"{base_sentiment} driven by {', '.join(drivers[:2])}."
            else:
                explanation = f"{base_sentiment} based on overall analysis."

            return explanation

        except Exception as e:
            logger.warning(f"Failed to generate explanation: {e}")
            return "Recommendation based on comprehensive analysis."

    def _generate_warnings(self, stock_data: pd.DataFrame, final_score: float) -> List[str]:
        """Generate warnings for the recommendation"""

        warnings = []

        try:
            # Data quality warnings
            if len(stock_data) < 5:
                warnings.append("Limited data points available for analysis")

            # High risk warnings
            if "volatility_20" in stock_data.columns:
                avg_volatility = stock_data["volatility_20"].mean()
                if avg_volatility > 0.3:
                    warnings.append("High volatility detected")

            # Policy risk warnings
            if "policy_relevant_trade" in stock_data.columns:
                policy_exposure = stock_data["policy_relevant_trade"].mean()
                if policy_exposure > 0.8:
                    warnings.append("High exposure to policy changes")

            # Confidence warnings
            if len(stock_data) == 1:
                warnings.append("Single data point - recommendation may be unreliable")

        except Exception as e:
            logger.warning(f"Failed to generate warnings: {e}")

        return warnings

    def save_model_artifacts(self, artifacts_dir: Path):
        """Save model artifacts and configurations"""
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Save configuration
        config_path = artifacts_dir / "recommendation_config.joblib"
        joblib.dump(self.config, config_path)

        # Save feature importance cache
        if self.feature_importance_cache:
            importance_path = artifacts_dir / "feature_importance.joblib"
            joblib.dump(self.feature_importance_cache, importance_path)

        logger.info(f"Saved model artifacts to {artifacts_dir}")

    def load_model_artifacts(self, artifacts_dir: Path):
        """Load model artifacts and configurations"""
        try:
            # Load configuration
            config_path = artifacts_dir / "recommendation_config.joblib"
            if config_path.exists():
                self.config = joblib.load(config_path)

            # Load feature importance cache
            importance_path = artifacts_dir / "feature_importance.joblib"
            if importance_path.exists():
                self.feature_importance_cache = joblib.load(importance_path)

            logger.info(f"Loaded model artifacts from {artifacts_dir}")

        except Exception as e:
            logger.warning(f"Failed to load model artifacts: {e}")
