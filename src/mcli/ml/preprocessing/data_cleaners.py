"""Data cleaning utilities for ML preprocessing"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CleaningStats:
    """Statistics about data cleaning operations"""

    total_records: int
    cleaned_records: int
    removed_records: int
    cleaning_operations: Dict[str, int]
    outliers_detected: int
    missing_values_filled: int


class TradingDataCleaner:
    """Cleans and standardizes politician trading data for ML"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.cleaning_stats = CleaningStats(
            total_records=0,
            cleaned_records=0,
            removed_records=0,
            cleaning_operations={},
            outliers_detected=0,
            missing_values_filled=0,
        )

    def clean_trading_records(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], CleaningStats]:
        """Clean a batch of trading records"""
        self.cleaning_stats.total_records = len(records)
        cleaned_records = []

        for record in records:
            cleaned_record = self._clean_single_record(record)
            if cleaned_record is not None:
                cleaned_records.append(cleaned_record)
                self.cleaning_stats.cleaned_records += 1
            else:
                self.cleaning_stats.removed_records += 1

        return cleaned_records, self.cleaning_stats

    def _clean_single_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single trading record"""
        try:
            cleaned = record.copy()

            # Clean politician name
            cleaned = self._clean_politician_name(cleaned)

            # Clean transaction amount
            cleaned = self._clean_transaction_amount(cleaned)

            # Clean transaction date
            cleaned = self._clean_transaction_date(cleaned)

            # Clean asset name/ticker
            cleaned = self._clean_asset_info(cleaned)

            # Clean transaction type
            cleaned = self._clean_transaction_type(cleaned)

            # Validate required fields exist
            if not self._validate_required_fields(cleaned):
                return None

            return cleaned

        except Exception as e:
            logger.warning(f"Failed to clean record: {e}")
            return None

    def _clean_politician_name(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize politician names"""
        name_fields = ["politician_name", "name", "representative_name", "senator_name"]

        for field in name_fields:
            if field in record and record[field]:
                name = str(record[field]).strip()

                # Remove titles and suffixes
                name = re.sub(
                    r"\b(Hon\.|Dr\.|Mr\.|Mrs\.|Ms\.|Sen\.|Rep\.)\s+", "", name, flags=re.IGNORECASE
                )
                name = re.sub(r"\s+(Jr\.?|Sr\.?|III|IV|II)$", "", name, flags=re.IGNORECASE)

                # Title case
                name = name.title()

                # Handle special cases
                name = re.sub(r"\bMc([a-z])", r"Mc\1", name)
                name = re.sub(r"\bO\'([a-z])", r"O'\1", name)

                record["politician_name_cleaned"] = name
                self._increment_cleaning_operation("politician_name_cleaned")
                break

        return record

    def _clean_transaction_amount(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize transaction amounts"""
        amount_fields = ["transaction_amount", "amount", "value", "transaction_value"]

        for field in amount_fields:
            if field in record and record[field] is not None:
                amount_str = str(record[field]).strip()

                # Remove currency symbols and commas
                amount_str = re.sub(r"[$,\s]", "", amount_str)

                # Handle ranges (take midpoint)
                if " - " in amount_str or " to " in amount_str:
                    range_parts = re.split(r"\s*(?:-|to)\s*", amount_str)
                    if len(range_parts) == 2:
                        try:
                            min_val = float(re.sub(r"[^\d.]", "", range_parts[0]))
                            max_val = float(re.sub(r"[^\d.]", "", range_parts[1]))
                            amount_str = str((min_val + max_val) / 2)
                            self._increment_cleaning_operation("amount_range_midpoint")
                        except ValueError:
                            continue

                # Convert to float
                try:
                    amount = float(amount_str)
                    if amount >= 0:  # Only positive amounts
                        record["transaction_amount_cleaned"] = amount
                        self._increment_cleaning_operation("transaction_amount_cleaned")
                        break
                except ValueError:
                    continue

        return record

    def _clean_transaction_date(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize transaction dates"""
        date_fields = ["transaction_date", "date", "trade_date", "disclosure_date"]

        for field in date_fields:
            if field in record and record[field]:
                date_str = str(record[field]).strip()

                # Try multiple date formats
                date_formats = [
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%m-%d-%Y",
                    "%Y/%m/%d",
                    "%B %d, %Y",
                    "%b %d, %Y",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                ]

                for fmt in date_formats:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        record["transaction_date_cleaned"] = date_obj.strftime("%Y-%m-%d")
                        self._increment_cleaning_operation("transaction_date_cleaned")
                        break
                    except ValueError:
                        continue
                else:
                    # Try pandas parsing as fallback
                    try:
                        import pandas as pd

                        date_obj = pd.to_datetime(date_str)
                        record["transaction_date_cleaned"] = date_obj.strftime("%Y-%m-%d")
                        self._increment_cleaning_operation("transaction_date_cleaned")
                    except:
                        continue

                if "transaction_date_cleaned" in record:
                    break

        return record

    def _clean_asset_info(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize asset information"""
        asset_fields = ["asset_name", "stock_symbol", "ticker", "security_name"]

        # Clean ticker/symbol
        for field in ["stock_symbol", "ticker", "symbol"]:
            if field in record and record[field]:
                ticker = str(record[field]).strip().upper()

                # Remove common prefixes/suffixes
                ticker = re.sub(r"\s*(NYSE:|NASDAQ:|AMEX:)\s*", "", ticker)
                ticker = re.sub(r"\s*\(.*\)\s*", "", ticker)

                # Validate ticker format (letters and numbers only, 1-5 chars typically)
                if re.match(r"^[A-Z0-9]{1,10}$", ticker):
                    record["ticker_cleaned"] = ticker
                    self._increment_cleaning_operation("ticker_cleaned")
                    break

        # Clean asset name
        for field in ["asset_name", "security_name", "company_name"]:
            if field in record and record[field]:
                name = str(record[field]).strip()

                # Remove common suffixes
                name = re.sub(
                    r"\s+(Inc\.?|Corp\.?|Co\.?|Ltd\.?|LLC|LP)$", "", name, flags=re.IGNORECASE
                )

                # Title case
                name = name.title()

                record["asset_name_cleaned"] = name
                self._increment_cleaning_operation("asset_name_cleaned")
                break

        return record

    def _clean_transaction_type(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize transaction types"""
        type_fields = ["transaction_type", "type", "action", "trade_type"]

        for field in type_fields:
            if field in record and record[field]:
                transaction_type = str(record[field]).strip().lower()

                # Standardize transaction types
                if any(word in transaction_type for word in ["buy", "purchase", "acquired"]):
                    standardized_type = "buy"
                elif any(word in transaction_type for word in ["sell", "sale", "sold", "disposed"]):
                    standardized_type = "sell"
                elif any(word in transaction_type for word in ["exchange", "swap"]):
                    standardized_type = "exchange"
                else:
                    standardized_type = "other"

                record["transaction_type_cleaned"] = standardized_type
                self._increment_cleaning_operation("transaction_type_cleaned")
                break

        return record

    def _validate_required_fields(self, record: Dict[str, Any]) -> bool:
        """Validate that required fields exist after cleaning"""
        required_fields = [
            "politician_name_cleaned",
            "transaction_date_cleaned",
            "transaction_type_cleaned",
        ]

        # At least one amount or asset field should exist
        amount_or_asset = any(
            field in record
            for field in ["transaction_amount_cleaned", "ticker_cleaned", "asset_name_cleaned"]
        )

        has_required = all(field in record for field in required_fields)

        return has_required and amount_or_asset

    def _increment_cleaning_operation(self, operation: str):
        """Track cleaning operations"""
        if operation not in self.cleaning_stats.cleaning_operations:
            self.cleaning_stats.cleaning_operations[operation] = 0
        self.cleaning_stats.cleaning_operations[operation] += 1


class OutlierDetector:
    """Detects and handles outliers in trading data"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.outlier_thresholds = {
            "transaction_amount": {
                "min": 1,  # Minimum $1
                "max": 50_000_000,  # Maximum $50M
                "z_score": 3.0,
            },
            "days_to_disclosure": {
                "min": 0,
                "max": 365,  # More than 1 year is suspicious
                "z_score": 3.0,
            },
        }

    def detect_outliers(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Detect outliers in the dataset"""
        outlier_info = {"total_outliers": 0, "outliers_by_field": {}, "outlier_indices": set()}

        # Amount-based outliers
        if "transaction_amount_cleaned" in df.columns:
            amount_outliers = self._detect_amount_outliers(df)
            outlier_info["outliers_by_field"]["amount"] = len(amount_outliers)
            outlier_info["outlier_indices"].update(amount_outliers)

        # Date-based outliers
        if "transaction_date_cleaned" in df.columns:
            date_outliers = self._detect_date_outliers(df)
            outlier_info["outliers_by_field"]["date"] = len(date_outliers)
            outlier_info["outlier_indices"].update(date_outliers)

        # Statistical outliers
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col.endswith("_cleaned"):
                col_outliers = self._detect_statistical_outliers(df, col)
                outlier_info["outliers_by_field"][col] = len(col_outliers)
                outlier_info["outlier_indices"].update(col_outliers)

        outlier_info["total_outliers"] = len(outlier_info["outlier_indices"])

        # Mark outliers in dataframe
        df["is_outlier"] = df.index.isin(outlier_info["outlier_indices"])

        return df, outlier_info

    def _detect_amount_outliers(self, df: pd.DataFrame) -> List[int]:
        """Detect amount-based outliers"""
        outliers = []
        amount_col = "transaction_amount_cleaned"

        if amount_col not in df.columns:
            return outliers

        thresholds = self.outlier_thresholds["transaction_amount"]

        # Hard limits
        outliers.extend(df[df[amount_col] < thresholds["min"]].index.tolist())
        outliers.extend(df[df[amount_col] > thresholds["max"]].index.tolist())

        return list(set(outliers))

    def _detect_date_outliers(self, df: pd.DataFrame) -> List[int]:
        """Detect date-based outliers"""
        outliers = []
        date_col = "transaction_date_cleaned"

        if date_col not in df.columns:
            return outliers

        # Convert to datetime
        df[date_col] = pd.to_datetime(df[date_col])

        # Future dates
        future_dates = df[df[date_col] > datetime.now()].index.tolist()
        outliers.extend(future_dates)

        # Very old dates (before 1990)
        old_dates = df[df[date_col] < datetime(1990, 1, 1)].index.tolist()
        outliers.extend(old_dates)

        return list(set(outliers))

    def _detect_statistical_outliers(self, df: pd.DataFrame, column: str) -> List[int]:
        """Detect statistical outliers using Z-score"""
        outliers = []

        if column not in df.columns or df[column].dtype not in [np.number, "float64", "int64"]:
            return outliers

        # Calculate Z-scores
        mean_val = df[column].mean()
        std_val = df[column].std()

        if std_val == 0:  # No variation
            return outliers

        z_scores = np.abs((df[column] - mean_val) / std_val)
        threshold = self.outlier_thresholds.get(column, {}).get("z_score", 3.0)

        outliers = df[z_scores > threshold].index.tolist()

        return outliers


class MissingValueHandler:
    """Handles missing values in trading data"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.fill_strategies = {
            "transaction_amount_cleaned": "median",
            "transaction_date_cleaned": "forward_fill",
            "politician_name_cleaned": "drop",
            "transaction_type_cleaned": "mode",
            "ticker_cleaned": "drop",
            "asset_name_cleaned": "unknown",
        }

    def handle_missing_values(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Handle missing values according to strategies"""
        missing_info = {
            "original_shape": df.shape,
            "missing_counts": df.isnull().sum().to_dict(),
            "filled_counts": {},
            "dropped_rows": 0,
        }

        df_processed = df.copy()

        for column, strategy in self.fill_strategies.items():
            if column in df_processed.columns:
                original_missing = df_processed[column].isnull().sum()

                if strategy == "median" and df_processed[column].dtype in [
                    np.number,
                    "float64",
                    "int64",
                ]:
                    df_processed[column].fillna(df_processed[column].median(), inplace=True)
                elif strategy == "mean" and df_processed[column].dtype in [
                    np.number,
                    "float64",
                    "int64",
                ]:
                    df_processed[column].fillna(df_processed[column].mean(), inplace=True)
                elif strategy == "mode":
                    mode_val = df_processed[column].mode()
                    if not mode_val.empty:
                        df_processed[column].fillna(mode_val[0], inplace=True)
                elif strategy == "forward_fill":
                    df_processed[column].fillna(method="ffill", inplace=True)
                elif strategy == "backward_fill":
                    df_processed[column].fillna(method="bfill", inplace=True)
                elif strategy == "unknown":
                    df_processed[column].fillna("unknown", inplace=True)
                elif strategy == "drop":
                    # Drop rows with missing values in this column
                    rows_before = len(df_processed)
                    df_processed = df_processed.dropna(subset=[column])
                    missing_info["dropped_rows"] += rows_before - len(df_processed)

                new_missing = df_processed[column].isnull().sum()
                missing_info["filled_counts"][column] = original_missing - new_missing

        missing_info["final_shape"] = df_processed.shape
        missing_info["final_missing_counts"] = df_processed.isnull().sum().to_dict()

        return df_processed, missing_info
