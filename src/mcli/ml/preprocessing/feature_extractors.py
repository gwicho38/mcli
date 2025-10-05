"""Feature extraction utilities for ML preprocessing"""

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureExtractionStats:
    """Statistics about feature extraction operations"""

    total_records: int
    features_extracted: int
    failed_extractions: int
    feature_counts: Dict[str, int]
    extraction_time: float


class PoliticianFeatureExtractor:
    """Extracts features related to politicians"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.politician_cache = {}
        self.party_mapping = {
            "democrat": "D",
            "democratic": "D",
            "republican": "R",
            "independent": "I",
            "libertarian": "L",
        }

    def extract_politician_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract politician-related features"""
        df_features = df.copy()

        # Basic politician features
        df_features = self._extract_name_features(df_features)
        df_features = self._extract_trading_patterns(df_features)
        df_features = self._extract_frequency_features(df_features)
        df_features = self._extract_timing_features(df_features)

        return df_features

    def _extract_name_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features from politician names"""
        if "politician_name_cleaned" not in df.columns:
            return df

        # Name length and word count
        df["politician_name_length"] = df["politician_name_cleaned"].str.len()
        df["politician_name_word_count"] = df["politician_name_cleaned"].str.split().str.len()

        # Common prefixes/suffixes
        df["has_jr_sr"] = df["politician_name_cleaned"].str.contains(
            r"\b(Jr|Sr|III|IV|II)\b", case=False
        )
        df["has_hyphen"] = df["politician_name_cleaned"].str.contains("-")

        # Name frequency encoding (politician trading frequency)
        name_counts = df["politician_name_cleaned"].value_counts()
        df["politician_trading_frequency"] = df["politician_name_cleaned"].map(name_counts)

        return df

    def _extract_trading_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract trading pattern features for each politician"""
        if "politician_name_cleaned" not in df.columns:
            return df

        # Group by politician to calculate patterns
        politician_stats = (
            df.groupby("politician_name_cleaned")
            .agg(
                {
                    "transaction_amount_cleaned": ["count", "sum", "mean", "std", "min", "max"],
                    "transaction_type_cleaned": lambda x: x.value_counts().to_dict(),
                }
            )
            .reset_index()
        )

        # Flatten column names
        politician_stats.columns = [
            "politician_name_cleaned",
            "total_transactions",
            "total_volume",
            "avg_transaction_size",
            "transaction_size_std",
            "min_transaction_size",
            "max_transaction_size",
            "transaction_type_dist",
        ]

        # Calculate buy/sell ratios
        def extract_buy_sell_ratio(type_dist):
            if not isinstance(type_dist, dict):
                return 0.5, 0, 0

            buys = type_dist.get("buy", 0)
            sells = type_dist.get("sell", 0)
            total = buys + sells

            if total == 0:
                return 0.5, 0, 0

            buy_ratio = buys / total
            return buy_ratio, buys, sells

        politician_stats[["buy_ratio", "total_buys", "total_sells"]] = pd.DataFrame(
            politician_stats["transaction_type_dist"].apply(extract_buy_sell_ratio).tolist()
        )

        # Risk tolerance (std/mean of transaction sizes)
        politician_stats["transaction_volatility"] = (
            politician_stats["transaction_size_std"] / politician_stats["avg_transaction_size"]
        ).fillna(0)

        # Merge back to main dataframe
        feature_cols = [
            "total_transactions",
            "total_volume",
            "avg_transaction_size",
            "transaction_size_std",
            "min_transaction_size",
            "max_transaction_size",
            "buy_ratio",
            "total_buys",
            "total_sells",
            "transaction_volatility",
        ]

        df = df.merge(
            politician_stats[["politician_name_cleaned"] + feature_cols],
            on="politician_name_cleaned",
            how="left",
        )

        return df

    def _extract_frequency_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract trading frequency features"""
        if not all(
            col in df.columns for col in ["politician_name_cleaned", "transaction_date_cleaned"]
        ):
            return df

        # Convert date to datetime
        df["transaction_date_dt"] = pd.to_datetime(df["transaction_date_cleaned"])

        # Sort by politician and date
        df = df.sort_values(["politician_name_cleaned", "transaction_date_dt"])

        # Calculate days between trades for each politician
        df["days_since_last_trade"] = (
            df.groupby("politician_name_cleaned")["transaction_date_dt"].diff().dt.days
        )

        # Trading frequency metrics
        politician_freq = (
            df.groupby("politician_name_cleaned")
            .agg({"days_since_last_trade": ["mean", "std", "min", "max"]})
            .reset_index()
        )

        politician_freq.columns = [
            "politician_name_cleaned",
            "avg_days_between_trades",
            "days_between_trades_std",
            "min_days_between_trades",
            "max_days_between_trades",
        ]

        # Calculate trading consistency
        politician_freq["trading_consistency"] = 1 / (
            1 + politician_freq["days_between_trades_std"].fillna(0)
        )

        df = df.merge(politician_freq, on="politician_name_cleaned", how="left")

        return df

    def _extract_timing_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract timing-related features"""
        if "transaction_date_dt" not in df.columns:
            return df

        # Day of week (Monday=0, Sunday=6)
        df["transaction_day_of_week"] = df["transaction_date_dt"].dt.dayofweek

        # Month
        df["transaction_month"] = df["transaction_date_dt"].dt.month

        # Quarter
        df["transaction_quarter"] = df["transaction_date_dt"].dt.quarter

        # Year
        df["transaction_year"] = df["transaction_date_dt"].dt.year

        # Is weekend
        df["is_weekend"] = df["transaction_day_of_week"].isin([5, 6])

        # Is end of month
        df["is_end_of_month"] = df["transaction_date_dt"].dt.day >= 25

        # Is end of quarter
        df["is_end_of_quarter"] = (
            df["transaction_date_dt"].dt.month.isin([3, 6, 9, 12]) & df["is_end_of_month"]
        )

        return df


class MarketFeatureExtractor:
    """Extracts market-related features"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.sector_mapping = self._load_sector_mapping()

    def extract_market_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract market-related features"""
        df_features = df.copy()

        # Asset features
        df_features = self._extract_asset_features(df_features)
        df_features = self._extract_ticker_features(df_features)
        df_features = self._extract_market_cap_features(df_features)

        return df_features

    def _extract_asset_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features from asset names"""
        if "asset_name_cleaned" not in df.columns:
            return df

        # Asset name characteristics
        df["asset_name_length"] = df["asset_name_cleaned"].str.len()
        df["asset_name_word_count"] = df["asset_name_cleaned"].str.split().str.len()

        # Common asset types
        df["is_tech_stock"] = df["asset_name_cleaned"].str.contains(
            r"\b(tech|software|computer|data|digital|cyber|internet|online|cloud)\b", case=False
        )

        df["is_bank_stock"] = df["asset_name_cleaned"].str.contains(
            r"\b(bank|financial|credit|capital|trust|investment)\b", case=False
        )

        df["is_pharma_stock"] = df["asset_name_cleaned"].str.contains(
            r"\b(pharma|biotech|medical|health|drug|therapeutic)\b", case=False
        )

        df["is_energy_stock"] = df["asset_name_cleaned"].str.contains(
            r"\b(energy|oil|gas|petroleum|renewable|solar|wind)\b", case=False
        )

        # Asset popularity (trading frequency)
        asset_counts = df["asset_name_cleaned"].value_counts()
        df["asset_trading_frequency"] = df["asset_name_cleaned"].map(asset_counts)

        return df

    def _extract_ticker_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features from stock tickers"""
        if "ticker_cleaned" not in df.columns:
            return df

        # Ticker characteristics
        df["ticker_length"] = df["ticker_cleaned"].str.len()
        df["ticker_has_numbers"] = df["ticker_cleaned"].str.contains(r"\d")

        # Ticker popularity
        ticker_counts = df["ticker_cleaned"].value_counts()
        df["ticker_trading_frequency"] = df["ticker_cleaned"].map(ticker_counts)

        # Map to sectors (simplified)
        df["estimated_sector"] = df["ticker_cleaned"].map(self.sector_mapping).fillna("unknown")

        return df

    def _extract_market_cap_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract market cap related features (placeholder)"""
        # This would typically connect to external APIs
        # For now, create estimated features based on transaction amounts

        if "transaction_amount_cleaned" not in df.columns:
            return df

        # Estimate market cap tier based on typical trading amounts
        def estimate_market_cap_tier(amount):
            if amount < 10000:
                return "large_cap"  # Large institutions trade large caps in smaller amounts
            elif amount < 50000:
                return "mid_cap"
            else:
                return "small_cap"  # Large amounts might indicate smaller, riskier stocks

        df["estimated_market_cap_tier"] = df["transaction_amount_cleaned"].apply(
            estimate_market_cap_tier
        )

        return df

    def _load_sector_mapping(self) -> Dict[str, str]:
        """Load ticker to sector mapping (simplified)"""
        # This would typically be loaded from a data file or API
        return {
            "AAPL": "technology",
            "MSFT": "technology",
            "GOOGL": "technology",
            "GOOG": "technology",
            "AMZN": "consumer_discretionary",
            "TSLA": "consumer_discretionary",
            "META": "technology",
            "JPM": "financials",
            "BAC": "financials",
            "WFC": "financials",
            "XOM": "energy",
            "CVX": "energy",
            "JNJ": "healthcare",
            "PFE": "healthcare",
            "UNH": "healthcare",
        }


class TemporalFeatureExtractor:
    """Extracts temporal features for time series analysis"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.lookback_periods = config.get("lookback_periods", [7, 30, 90, 365])

    def extract_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract temporal features"""
        df_features = df.copy()

        if "transaction_date_dt" not in df.columns:
            return df_features

        # Sort by date
        df_features = df_features.sort_values("transaction_date_dt")

        # Rolling features
        df_features = self._extract_rolling_features(df_features)
        df_features = self._extract_lag_features(df_features)
        df_features = self._extract_trend_features(df_features)

        return df_features

    def _extract_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract rolling window features"""
        # Set date as index temporarily
        df_indexed = df.set_index("transaction_date_dt")

        for period in self.lookback_periods:
            # Rolling transaction counts
            df[f"transactions_last_{period}d"] = (
                df_indexed.groupby("politician_name_cleaned")
                .rolling(f"{period}D")["transaction_amount_cleaned"]
                .count()
                .reset_index(level=0, drop=True)
            )

            # Rolling volume
            df[f"volume_last_{period}d"] = (
                df_indexed.groupby("politician_name_cleaned")
                .rolling(f"{period}D")["transaction_amount_cleaned"]
                .sum()
                .reset_index(level=0, drop=True)
            )

            # Rolling average transaction size
            df[f"avg_transaction_last_{period}d"] = (
                df_indexed.groupby("politician_name_cleaned")
                .rolling(f"{period}D")["transaction_amount_cleaned"]
                .mean()
                .reset_index(level=0, drop=True)
            )

        return df

    def _extract_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract lagged features"""
        lag_periods = [1, 7, 30]

        for lag in lag_periods:
            # Lag transaction amounts
            df[f"transaction_amount_lag_{lag}"] = df.groupby("politician_name_cleaned")[
                "transaction_amount_cleaned"
            ].shift(lag)

            # Lag transaction types
            df[f"transaction_type_lag_{lag}"] = df.groupby("politician_name_cleaned")[
                "transaction_type_cleaned"
            ].shift(lag)

        return df

    def _extract_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract trend features"""
        # Calculate percentage changes
        df["amount_pct_change_1d"] = df.groupby("politician_name_cleaned")[
            "transaction_amount_cleaned"
        ].pct_change()

        df["amount_pct_change_7d"] = df.groupby("politician_name_cleaned")[
            "transaction_amount_cleaned"
        ].pct_change(periods=7)

        # Moving averages
        df["amount_ma_7"] = (
            df.groupby("politician_name_cleaned")["transaction_amount_cleaned"]
            .rolling(window=7, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )

        df["amount_ma_30"] = (
            df.groupby("politician_name_cleaned")["transaction_amount_cleaned"]
            .rolling(window=30, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )

        # Trend indicators
        df["amount_above_ma_7"] = df["transaction_amount_cleaned"] > df["amount_ma_7"]
        df["amount_above_ma_30"] = df["transaction_amount_cleaned"] > df["amount_ma_30"]

        return df


class SentimentFeatureExtractor:
    """Extracts sentiment and text-based features"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.positive_words = ["gain", "profit", "up", "rise", "bull", "growth", "strong"]
        self.negative_words = ["loss", "down", "bear", "decline", "weak", "fall", "drop"]

    def extract_sentiment_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract sentiment features from text fields"""
        df_features = df.copy()

        # Asset name sentiment
        if "asset_name_cleaned" in df.columns:
            df_features = self._extract_text_sentiment(
                df_features, "asset_name_cleaned", "asset_name"
            )

        # News sentiment (placeholder for future news integration)
        df_features["news_sentiment_score"] = 0.0  # Neutral baseline
        df_features["news_volume"] = 0  # No news volume baseline

        return df_features

    def _extract_text_sentiment(
        self, df: pd.DataFrame, text_column: str, prefix: str
    ) -> pd.DataFrame:
        """Extract sentiment from text column"""
        if text_column not in df.columns:
            return df

        text_series = df[text_column].fillna("").str.lower()

        # Count positive and negative words
        positive_count = text_series.apply(
            lambda x: sum(1 for word in self.positive_words if word in x)
        )
        negative_count = text_series.apply(
            lambda x: sum(1 for word in self.negative_words if word in x)
        )

        # Calculate sentiment score
        total_sentiment_words = positive_count + negative_count
        sentiment_score = np.where(
            total_sentiment_words > 0, (positive_count - negative_count) / total_sentiment_words, 0
        )

        df[f"{prefix}_positive_words"] = positive_count
        df[f"{prefix}_negative_words"] = negative_count
        df[f"{prefix}_sentiment_score"] = sentiment_score

        return df
