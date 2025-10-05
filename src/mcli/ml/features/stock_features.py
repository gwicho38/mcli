"""Stock-specific feature engineering for recommendation models"""

import logging
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class StockFeatureConfig:
    """Configuration for stock feature extraction"""

    # Technical indicator periods
    sma_periods: List[int] = None
    ema_periods: List[int] = None
    rsi_period: int = 14
    bollinger_period: int = 20
    bollinger_std: float = 2.0

    # Volatility features
    volatility_windows: List[int] = None
    return_windows: List[int] = None

    # Volume features
    volume_ma_periods: List[int] = None
    enable_volume_profile: bool = True

    # Market regime detection
    regime_lookback: int = 252  # 1 year
    volatility_threshold: float = 0.02

    def __post_init__(self):
        if self.sma_periods is None:
            self.sma_periods = [5, 10, 20, 50, 200]
        if self.ema_periods is None:
            self.ema_periods = [12, 26, 50]
        if self.volatility_windows is None:
            self.volatility_windows = [5, 10, 20, 60]
        if self.return_windows is None:
            self.return_windows = [1, 5, 10, 20, 60]
        if self.volume_ma_periods is None:
            self.volume_ma_periods = [10, 20, 50]


class StockRecommendationFeatures:
    """Core stock recommendation feature extractor"""

    def __init__(self, config: Optional[StockFeatureConfig] = None):
        self.config = config or StockFeatureConfig()

    def extract_features(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """Extract stock recommendation features"""
        logger.info("Extracting stock recommendation features")

        df = stock_data.copy()

        # Ensure required columns exist
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            logger.warning(f"Missing required columns: {missing_cols}")
            # Create synthetic data for missing columns if needed
            for col in missing_cols:
                if col == "volume":
                    df[col] = 1000000  # Default volume
                else:
                    df[col] = df.get("close", 100.0)  # Use close or default price

        # Sort by date to ensure chronological order
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)

        # Extract all feature categories
        df = self._extract_price_features(df)
        df = self._extract_volume_features(df)
        df = self._extract_volatility_features(df)
        df = self._extract_momentum_features(df)
        df = self._extract_trend_features(df)

        logger.info(f"Extracted {len(df.columns)} total features")
        return df

    def _extract_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract price-based features"""
        # Basic price relationships
        df["hl_ratio"] = (df["high"] - df["low"]) / df["close"]
        df["oc_ratio"] = (df["open"] - df["close"]) / df["close"]
        df["price_range"] = (df["high"] - df["low"]) / df["low"]

        # Price gaps
        df["gap_up"] = (df["open"] > df["close"].shift(1)).astype(int)
        df["gap_down"] = (df["open"] < df["close"].shift(1)).astype(int)
        df["gap_size"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)

        # Simple moving averages
        for period in self.config.sma_periods:
            df[f"sma_{period}"] = df["close"].rolling(window=period).mean()
            df[f"price_to_sma_{period}"] = df["close"] / df[f"sma_{period}"]
            df[f"sma_{period}_slope"] = (df[f"sma_{period}"] - df[f"sma_{period}"].shift(5)) / df[
                f"sma_{period}"
            ].shift(5)

        # Exponential moving averages
        for period in self.config.ema_periods:
            df[f"ema_{period}"] = df["close"].ewm(span=period).mean()
            df[f"price_to_ema_{period}"] = df["close"] / df[f"ema_{period}"]

        # Moving average crossovers
        if len(self.config.sma_periods) >= 2:
            short_ma = self.config.sma_periods[0]
            long_ma = self.config.sma_periods[-1]
            df["ma_crossover"] = (df[f"sma_{short_ma}"] > df[f"sma_{long_ma}"]).astype(int)
            df["ma_distance"] = (df[f"sma_{short_ma}"] - df[f"sma_{long_ma}"]) / df[
                f"sma_{long_ma}"
            ]

        return df

    def _extract_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract volume-based features"""
        # Volume moving averages
        for period in self.config.volume_ma_periods:
            df[f"volume_ma_{period}"] = df["volume"].rolling(window=period).mean()
            df[f"volume_ratio_{period}"] = df["volume"] / df[f"volume_ma_{period}"]

        # Volume price trend
        df["volume_price_trend"] = (
            ((df["close"] - df["close"].shift(1)) * df["volume"]).rolling(window=10).sum()
        )

        # On-balance volume
        df["price_change"] = df["close"] - df["close"].shift(1)
        df["obv_flow"] = np.where(
            df["price_change"] > 0,
            df["volume"],
            np.where(df["price_change"] < 0, -df["volume"], 0),
        )
        df["obv"] = df["obv_flow"].cumsum()

        # Volume accumulation
        df["accumulation"] = (
            np.where(df["close"] > (df["high"] + df["low"]) / 2, df["volume"], -df["volume"])
            .rolling(window=20)
            .sum()
        )

        # Volume spikes
        df["volume_spike"] = (df["volume"] > df["volume"].rolling(window=20).mean() * 2).astype(int)

        return df

    def _extract_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract volatility-based features"""
        # Calculate returns
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        # Rolling volatility
        for window in self.config.volatility_windows:
            df[f"volatility_{window}"] = df["returns"].rolling(window=window).std() * np.sqrt(252)
            df[f"volatility_{window}_rank"] = (
                df[f"volatility_{window}"].rolling(window=60).rank(pct=True)
            )

        # True Range and Average True Range
        df["true_range"] = np.maximum(
            np.maximum(
                df["high"] - df["low"],
                abs(df["high"] - df["close"].shift(1)),
            ),
            abs(df["low"] - df["close"].shift(1)),
        )
        df["atr_14"] = df["true_range"].rolling(window=14).mean()
        df["atr_ratio"] = df["true_range"] / df["atr_14"]

        # Bollinger Bands
        sma_bb = df["close"].rolling(window=self.config.bollinger_period).mean()
        bb_std = df["close"].rolling(window=self.config.bollinger_period).std()
        df["bb_upper"] = sma_bb + (bb_std * self.config.bollinger_std)
        df["bb_lower"] = sma_bb - (bb_std * self.config.bollinger_std)
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
        df["bb_squeeze"] = (df["bb_upper"] - df["bb_lower"]) / sma_bb

        # Volatility regime
        rolling_vol = df["returns"].rolling(window=20).std()
        vol_threshold = rolling_vol.rolling(window=60).quantile(0.7)
        df["high_vol_regime"] = (rolling_vol > vol_threshold).astype(int)

        return df

    def _extract_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract momentum-based features"""
        # RSI (Relative Strength Index)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_period).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi_overbought"] = (df["rsi"] > 70).astype(int)
        df["rsi_oversold"] = (df["rsi"] < 30).astype(int)

        # MACD
        ema_12 = df["close"].ewm(span=12).mean()
        ema_26 = df["close"].ewm(span=26).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]
        df["macd_bullish"] = (df["macd"] > df["macd_signal"]).astype(int)

        # Stochastic oscillator
        lowest_low = df["low"].rolling(window=14).min()
        highest_high = df["high"].rolling(window=14).max()
        df["stoch_k"] = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low)
        df["stoch_d"] = df["stoch_k"].rolling(window=3).mean()

        # Rate of Change
        for period in [5, 10, 20]:
            df[f"roc_{period}"] = (
                (df["close"] - df["close"].shift(period)) / df["close"].shift(period)
            ) * 100

        # Momentum
        for period in [5, 10, 20]:
            df[f"momentum_{period}"] = df["close"] / df["close"].shift(period)

        return df

    def _extract_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract trend-based features"""
        # Trend strength
        for window in [10, 20, 50]:
            # Linear regression slope
            df[f"trend_slope_{window}"] = (
                df["close"]
                .rolling(window=window)
                .apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=False)
            )

            # R-squared of trend
            def calculate_r_squared(prices):
                if len(prices) < 2:
                    return 0
                x = np.arange(len(prices))
                try:
                    slope, intercept = np.polyfit(x, prices, 1)
                    predicted = slope * x + intercept
                    ss_res = np.sum((prices - predicted) ** 2)
                    ss_tot = np.sum((prices - np.mean(prices)) ** 2)
                    return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                except:
                    return 0

            df[f"trend_strength_{window}"] = (
                df["close"].rolling(window=window).apply(calculate_r_squared, raw=False)
            )

        # Support and resistance levels
        df["support_level"] = df["low"].rolling(window=20).min()
        df["resistance_level"] = df["high"].rolling(window=20).max()
        df["support_distance"] = (df["close"] - df["support_level"]) / df["close"]
        df["resistance_distance"] = (df["resistance_level"] - df["close"]) / df["close"]

        # Price position within recent range
        df["range_position"] = (df["close"] - df["support_level"]) / (
            df["resistance_level"] - df["support_level"]
        )

        # Higher highs and lower lows
        df["higher_high"] = (df["high"] > df["high"].shift(1)).astype(int)
        df["lower_low"] = (df["low"] < df["low"].shift(1)).astype(int)
        df["higher_high_count"] = df["higher_high"].rolling(window=10).sum()
        df["lower_low_count"] = df["lower_low"].rolling(window=10).sum()

        return df


class TechnicalIndicatorFeatures:
    """Advanced technical indicator features"""

    def __init__(self, config: Optional[StockFeatureConfig] = None):
        self.config = config or StockFeatureConfig()

    def extract_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract advanced technical indicators"""
        df = df.copy()

        # Williams %R
        df["williams_r"] = self._williams_r(df)

        # Commodity Channel Index (CCI)
        df["cci"] = self._commodity_channel_index(df)

        # Money Flow Index (MFI)
        df["mfi"] = self._money_flow_index(df)

        # Aroon indicator
        df["aroon_up"], df["aroon_down"] = self._aroon_indicator(df)
        df["aroon_oscillator"] = df["aroon_up"] - df["aroon_down"]

        # Parabolic SAR
        df["psar"] = self._parabolic_sar(df)
        df["psar_bullish"] = (df["close"] > df["psar"]).astype(int)

        # Ichimoku Cloud components
        df = self._ichimoku_cloud(df)

        return df

    def _williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Williams %R oscillator"""
        highest_high = df["high"].rolling(window=period).max()
        lowest_low = df["low"].rolling(window=period).min()
        return -100 * (highest_high - df["close"]) / (highest_high - lowest_low)

    def _commodity_channel_index(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean())), raw=False
        )
        return (typical_price - sma_tp) / (0.015 * mad)

    def _money_flow_index(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Money Flow Index"""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        money_flow = typical_price * df["volume"]

        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()

        mfi = 100 - (100 / (1 + positive_mf / negative_mf))
        return mfi

    def _aroon_indicator(self, df: pd.DataFrame, period: int = 25) -> Tuple[pd.Series, pd.Series]:
        """Aroon Up and Aroon Down indicators"""
        aroon_up = (
            100 * (period - df["high"].rolling(window=period).apply(np.argmax, raw=False)) / period
        )
        aroon_down = (
            100 * (period - df["low"].rolling(window=period).apply(np.argmin, raw=False)) / period
        )
        return aroon_up, aroon_down

    def _parabolic_sar(self, df: pd.DataFrame) -> pd.Series:
        """Parabolic SAR indicator (simplified version)"""
        # Simplified PSAR implementation
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        psar = np.zeros(len(df))
        if len(df) > 0:
            psar[0] = low[0]

        for i in range(1, len(df)):
            # Very simplified version - just use previous close as approximation
            psar[i] = close[i - 1]

        return pd.Series(psar, index=df.index)

    def _ichimoku_cloud(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ichimoku Cloud components"""
        # Tenkan-sen (Conversion Line)
        tenkan_high = df["high"].rolling(window=9).max()
        tenkan_low = df["low"].rolling(window=9).min()
        df["tenkan_sen"] = (tenkan_high + tenkan_low) / 2

        # Kijun-sen (Base Line)
        kijun_high = df["high"].rolling(window=26).max()
        kijun_low = df["low"].rolling(window=26).min()
        df["kijun_sen"] = (kijun_high + kijun_low) / 2

        # Senkou Span A (Leading Span A)
        df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)

        # Senkou Span B (Leading Span B)
        senkou_high = df["high"].rolling(window=52).max()
        senkou_low = df["low"].rolling(window=52).min()
        df["senkou_span_b"] = ((senkou_high + senkou_low) / 2).shift(26)

        # Chikou Span (Lagging Span)
        df["chikou_span"] = df["close"].shift(-26)

        # Cloud thickness
        df["cloud_thickness"] = abs(df["senkou_span_a"] - df["senkou_span_b"])

        # Price relative to cloud
        cloud_top = np.maximum(df["senkou_span_a"], df["senkou_span_b"])
        cloud_bottom = np.minimum(df["senkou_span_a"], df["senkou_span_b"])

        df["above_cloud"] = (df["close"] > cloud_top).astype(int)
        df["below_cloud"] = (df["close"] < cloud_bottom).astype(int)
        df["in_cloud"] = ((df["close"] >= cloud_bottom) & (df["close"] <= cloud_top)).astype(int)

        return df


class MarketRegimeFeatures:
    """Market regime detection features"""

    def __init__(self, config: Optional[StockFeatureConfig] = None):
        self.config = config or StockFeatureConfig()

    def extract_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract market regime features"""
        df = df.copy()

        # Volatility regime
        df = self._volatility_regime(df)

        # Trend regime
        df = self._trend_regime(df)

        # Volume regime
        df = self._volume_regime(df)

        # Market stress indicators
        df = self._market_stress_indicators(df)

        return df

    def _volatility_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify volatility regimes"""
        returns = df["close"].pct_change()
        vol_20 = returns.rolling(window=20).std() * np.sqrt(252)

        # Regime classification based on volatility percentiles
        vol_percentiles = vol_20.rolling(window=self.config.regime_lookback).quantile([0.33, 0.67])

        df["vol_regime"] = pd.cut(
            vol_20,
            bins=[-np.inf, vol_percentiles.iloc[:, 0], vol_percentiles.iloc[:, 1], np.inf],
            labels=["low_vol", "medium_vol", "high_vol"],
        )

        # Volatility clustering
        df["vol_cluster"] = (vol_20 > vol_20.rolling(window=60).quantile(0.8)).astype(int)

        return df

    def _trend_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify trend regimes"""
        # Multiple timeframe trend analysis
        for window in [20, 50, 200]:
            sma = df["close"].rolling(window=window).mean()
            df[f"trend_{window}"] = np.where(
                df["close"] > sma, 1, np.where(df["close"] < sma, -1, 0)
            )

        # Composite trend score
        df["trend_score"] = df["trend_20"] * 0.5 + df["trend_50"] * 0.3 + df["trend_200"] * 0.2

        # Trend strength
        df["trend_strength"] = abs(df["trend_score"])

        # Trend regime classification
        df["trend_regime"] = pd.cut(
            df["trend_score"],
            bins=[-np.inf, -0.5, 0.5, np.inf],
            labels=["bearish", "sideways", "bullish"],
        )

        return df

    def _volume_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify volume regimes"""
        volume_ma = df["volume"].rolling(window=20).mean()
        volume_ratio = df["volume"] / volume_ma

        # Volume regime classification
        vol_high = volume_ratio.rolling(window=60).quantile(0.8)
        vol_low = volume_ratio.rolling(window=60).quantile(0.2)

        df["volume_regime"] = np.where(
            volume_ratio > vol_high,
            "high_volume",
            np.where(volume_ratio < vol_low, "low_volume", "normal_volume"),
        )

        # Volume trend
        df["volume_trend"] = (
            df["volume"].rolling(window=10).mean() / df["volume"].rolling(window=30).mean()
        )

        return df

    def _market_stress_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Market stress and fear indicators"""
        returns = df["close"].pct_change()

        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        df["drawdown"] = (cumulative - running_max) / running_max

        # Consecutive down days
        down_days = (returns < 0).astype(int)
        df["consecutive_down"] = down_days * (
            down_days.groupby((down_days != down_days.shift()).cumsum()).cumcount() + 1
        )

        # Volatility spikes
        vol_20 = returns.rolling(window=20).std()
        vol_spike_threshold = vol_20.rolling(window=60).quantile(0.95)
        df["vol_spike"] = (vol_20 > vol_spike_threshold).astype(int)

        # Gap analysis
        gaps = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)
        df["gap_stress"] = (abs(gaps) > 0.02).astype(int)

        return df


class CrossAssetFeatures:
    """Cross-asset and correlation features"""

    def __init__(self):
        pass

    def extract_cross_asset_features(
        self, primary_df: pd.DataFrame, market_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Extract features based on relationships with other assets"""
        df = primary_df.copy()

        # Correlation with market indices
        for asset_name, asset_df in market_data.items():
            if "close" in asset_df.columns:
                # Price correlation
                corr_20 = (
                    df["close"].pct_change().rolling(window=20).corr(asset_df["close"].pct_change())
                )
                df[f"corr_{asset_name}_20"] = corr_20

                # Beta calculation
                market_returns = asset_df["close"].pct_change()
                stock_returns = df["close"].pct_change()

                # Rolling beta
                def calculate_beta(stock_ret, market_ret):
                    try:
                        covariance = np.cov(stock_ret, market_ret)[0][1]
                        market_variance = np.var(market_ret)
                        return covariance / market_variance if market_variance != 0 else 1.0
                    except:
                        return 1.0

                rolling_beta = pd.Series(index=df.index, dtype=float)
                for i in range(20, len(df)):
                    stock_window = stock_returns.iloc[i - 20 : i]
                    market_window = market_returns.iloc[i - 20 : i]
                    if len(stock_window) == 20 and len(market_window) == 20:
                        rolling_beta.iloc[i] = calculate_beta(stock_window, market_window)

                df[f"beta_{asset_name}"] = rolling_beta

                # Relative strength
                df[f"relative_strength_{asset_name}"] = (df["close"] / df["close"].shift(20)) / (
                    asset_df["close"] / asset_df["close"].shift(20)
                )

        return df
