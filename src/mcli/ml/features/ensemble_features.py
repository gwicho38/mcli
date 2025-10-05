"""Ensemble feature engineering and feature interaction systems"""

import logging
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import combinations
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
from sklearn.preprocessing import PolynomialFeatures

logger = logging.getLogger(__name__)


@dataclass
class EnsembleFeatureConfig:
    """Configuration for ensemble feature engineering"""

    # Feature interaction settings
    max_interaction_degree: int = 2
    max_features_for_interactions: int = 50
    interaction_selection_method: str = "mutual_info"  # "mutual_info", "f_test", "correlation"

    # Polynomial feature settings
    enable_polynomial_features: bool = True
    polynomial_degree: int = 2
    include_bias: bool = False

    # Clustering features
    enable_clustering_features: bool = True
    n_clusters: int = 5
    clustering_features: List[str] = None

    # Feature selection settings
    feature_selection_k: int = 100
    selection_score_func: str = "f_regression"  # "f_regression", "mutual_info"

    # Rolling feature aggregations
    rolling_windows: List[int] = None
    rolling_functions: List[str] = None

    def __post_init__(self):
        if self.clustering_features is None:
            self.clustering_features = [
                "total_influence",
                "transaction_amount_cleaned",
                "trading_frequency_score",
                "volatility_20",
                "rsi",
            ]

        if self.rolling_windows is None:
            self.rolling_windows = [5, 10, 20, 50]

        if self.rolling_functions is None:
            self.rolling_functions = ["mean", "std", "min", "max", "skew"]


class EnsembleFeatureBuilder:
    """Builds comprehensive feature sets for ensemble models"""

    def __init__(self, config: Optional[EnsembleFeatureConfig] = None):
        self.config = config or EnsembleFeatureConfig()
        self.feature_importance_cache = {}
        self.interaction_cache = {}

    def build_ensemble_features(
        self,
        base_features: pd.DataFrame,
        target_column: Optional[str] = None,
        include_interactions: bool = True,
        include_clustering: bool = True,
        include_rolling: bool = True,
    ) -> pd.DataFrame:
        """Build comprehensive feature set for ensemble models"""

        logger.info("Building ensemble features")
        df = base_features.copy()

        # Get numerical features for processing
        numerical_features = self._get_numerical_features(df)
        logger.info(f"Processing {len(numerical_features)} numerical features")

        # Add rolling aggregations
        if include_rolling and len(numerical_features) > 0:
            df = self._add_rolling_features(df, numerical_features)

        # Add interaction features
        if include_interactions and len(numerical_features) > 0:
            df = self._add_interaction_features(df, numerical_features, target_column)

        # Add polynomial features (subset)
        if self.config.enable_polynomial_features and len(numerical_features) > 0:
            df = self._add_polynomial_features(
                df, numerical_features[:10]
            )  # Limit to avoid explosion

        # Add clustering features
        if include_clustering and self.config.enable_clustering_features:
            df = self._add_clustering_features(df)

        # Add statistical features
        df = self._add_statistical_features(df, numerical_features)

        # Add rank features
        df = self._add_rank_features(df, numerical_features)

        logger.info(f"Final feature count: {len(df.columns)}")
        return df

    def _get_numerical_features(self, df: pd.DataFrame) -> List[str]:
        """Get list of numerical feature columns"""
        numerical_features = []
        for col in df.columns:
            if (
                df[col].dtype in ["int64", "float64"]
                and not col.startswith("target_")
                and not col.endswith("_id")
                and col not in ["index"]
                and df[col].notna().sum() > 0
            ):
                numerical_features.append(col)
        return numerical_features

    def _add_rolling_features(
        self, df: pd.DataFrame, numerical_features: List[str]
    ) -> pd.DataFrame:
        """Add rolling window aggregation features"""
        logger.info("Adding rolling aggregation features")

        # Ensure we have date column for time-based rolling
        if "transaction_date_dt" not in df.columns:
            # Create synthetic time index if no date column
            df["synthetic_time_index"] = range(len(df))
            time_col = "synthetic_time_index"
        else:
            df = df.sort_values("transaction_date_dt")
            time_col = "transaction_date_dt"

        # Select top features for rolling (avoid too many features)
        features_for_rolling = numerical_features[:20]

        for window in self.config.rolling_windows:
            if window >= len(df):
                continue

            for feature in features_for_rolling:
                if feature not in df.columns:
                    continue

                try:
                    # Basic rolling aggregations
                    df[f"{feature}_rolling_{window}_mean"] = (
                        df[feature].rolling(window=window, min_periods=1).mean()
                    )
                    df[f"{feature}_rolling_{window}_std"] = (
                        df[feature].rolling(window=window, min_periods=1).std()
                    )

                    # Rolling rank (percentile within window)
                    df[f"{feature}_rolling_{window}_rank"] = (
                        df[feature].rolling(window=window, min_periods=1).rank(pct=True)
                    )

                    # Rolling z-score
                    rolling_mean = df[feature].rolling(window=window, min_periods=1).mean()
                    rolling_std = df[feature].rolling(window=window, min_periods=1).std()
                    df[f"{feature}_rolling_{window}_zscore"] = (df[feature] - rolling_mean) / (
                        rolling_std + 1e-8
                    )

                except Exception as e:
                    logger.warning(f"Failed to create rolling features for {feature}: {e}")

        return df

    def _add_interaction_features(
        self, df: pd.DataFrame, numerical_features: List[str], target_column: Optional[str]
    ) -> pd.DataFrame:
        """Add feature interaction terms"""
        logger.info("Adding feature interaction terms")

        # Limit features to avoid combinatorial explosion
        if len(numerical_features) > self.config.max_features_for_interactions:
            # Select top features based on correlation with target or variance
            if target_column and target_column in df.columns:
                feature_scores = []
                for feature in numerical_features:
                    try:
                        corr = abs(df[feature].corr(df[target_column]))
                        feature_scores.append((feature, corr))
                    except:
                        feature_scores.append((feature, 0))

                feature_scores.sort(key=lambda x: x[1], reverse=True)
                selected_features = [
                    f[0] for f in feature_scores[: self.config.max_features_for_interactions]
                ]
            else:
                # Select by variance
                feature_vars = []
                for feature in numerical_features:
                    try:
                        var = df[feature].var()
                        feature_vars.append((feature, var))
                    except:
                        feature_vars.append((feature, 0))

                feature_vars.sort(key=lambda x: x[1], reverse=True)
                selected_features = [
                    f[0] for f in feature_vars[: self.config.max_features_for_interactions]
                ]
        else:
            selected_features = numerical_features

        # Create pairwise interactions
        interaction_count = 0
        max_interactions = 200  # Limit total interactions

        for feature1, feature2 in combinations(selected_features, 2):
            if interaction_count >= max_interactions:
                break

            if feature1 not in df.columns or feature2 not in df.columns:
                continue

            try:
                # Multiplicative interaction
                df[f"{feature1}_x_{feature2}"] = df[feature1] * df[feature2]

                # Ratio interaction (avoid division by zero)
                df[f"{feature1}_div_{feature2}"] = df[feature1] / (abs(df[feature2]) + 1e-8)

                # Difference interaction
                df[f"{feature1}_minus_{feature2}"] = df[feature1] - df[feature2]

                interaction_count += 3

                # Add some conditional interactions for key features
                if "influence" in feature1.lower() or "influence" in feature2.lower():
                    # Conditional interactions based on influence
                    high_influence = df[feature1] > df[feature1].quantile(0.7)
                    df[f"{feature2}_when_high_{feature1}"] = np.where(
                        high_influence, df[feature2], 0
                    )
                    interaction_count += 1

            except Exception as e:
                logger.warning(f"Failed to create interaction {feature1} x {feature2}: {e}")

        logger.info(f"Created {interaction_count} interaction features")
        return df

    def _add_polynomial_features(
        self, df: pd.DataFrame, selected_features: List[str]
    ) -> pd.DataFrame:
        """Add polynomial features for key variables"""
        logger.info("Adding polynomial features")

        # Limit to top features to avoid memory issues
        features_for_poly = selected_features[:5]

        try:
            # Create polynomial features
            poly = PolynomialFeatures(
                degree=self.config.polynomial_degree,
                include_bias=self.config.include_bias,
                interaction_only=False,
            )

            # Prepare data (handle missing values)
            poly_data = df[features_for_poly].fillna(0)

            if len(poly_data) > 0 and len(features_for_poly) > 0:
                poly_features = poly.fit_transform(poly_data)

                # Get feature names
                poly_feature_names = poly.get_feature_names_out(features_for_poly)

                # Add polynomial features to dataframe (skip original features)
                start_idx = len(features_for_poly)
                for i, name in enumerate(poly_feature_names[start_idx:], start_idx):
                    df[f"poly_{name}"] = poly_features[:, i]

                logger.info(
                    f"Added {len(poly_feature_names) - len(features_for_poly)} polynomial features"
                )

        except Exception as e:
            logger.warning(f"Failed to create polynomial features: {e}")

        return df

    def _add_clustering_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add clustering-based features"""
        logger.info("Adding clustering features")

        # Select features for clustering
        clustering_features = []
        for feature in self.config.clustering_features:
            if feature in df.columns:
                clustering_features.append(feature)

        if len(clustering_features) < 2:
            logger.warning("Insufficient features for clustering")
            return df

        try:
            # Prepare clustering data
            cluster_data = df[clustering_features].fillna(0)

            # Apply K-means clustering
            kmeans = KMeans(n_clusters=self.config.n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(cluster_data)

            df["cluster_label"] = cluster_labels

            # Add distance to cluster centers
            cluster_centers = kmeans.cluster_centers_
            distances = []

            for i, row in cluster_data.iterrows():
                center = cluster_centers[cluster_labels[i]]
                distance = np.sqrt(np.sum((row.values - center) ** 2))
                distances.append(distance)

            df["cluster_distance"] = distances

            # Add cluster-based features
            for cluster_id in range(self.config.n_clusters):
                df[f"is_cluster_{cluster_id}"] = (df["cluster_label"] == cluster_id).astype(int)

            # Cluster statistics
            cluster_stats = df.groupby("cluster_label")[clustering_features].agg(["mean", "std"])

            for feature in clustering_features:
                for stat in ["mean", "std"]:
                    cluster_stat_dict = cluster_stats[(feature, stat)].to_dict()
                    df[f"cluster_{feature}_{stat}"] = df["cluster_label"].map(cluster_stat_dict)

            logger.info(f"Added clustering features with {self.config.n_clusters} clusters")

        except Exception as e:
            logger.warning(f"Failed to create clustering features: {e}")

        return df

    def _add_statistical_features(
        self, df: pd.DataFrame, numerical_features: List[str]
    ) -> pd.DataFrame:
        """Add statistical transformation features"""
        logger.info("Adding statistical features")

        # Select subset of features for statistical transforms
        stat_features = numerical_features[:15]

        for feature in stat_features:
            if feature not in df.columns:
                continue

            try:
                feature_data = df[feature].fillna(0)

                # Log transform (for positive values)
                if (feature_data > 0).all():
                    df[f"{feature}_log"] = np.log1p(feature_data)

                # Square root transform
                if (feature_data >= 0).all():
                    df[f"{feature}_sqrt"] = np.sqrt(feature_data)

                # Inverse transform (avoid division by zero)
                df[f"{feature}_inv"] = 1 / (abs(feature_data) + 1e-8)

                # Standardized (z-score)
                mean_val = feature_data.mean()
                std_val = feature_data.std()
                if std_val > 0:
                    df[f"{feature}_zscore"] = (feature_data - mean_val) / std_val

                # Binned features
                df[f"{feature}_binned"] = pd.cut(feature_data, bins=5, labels=False)

            except Exception as e:
                logger.warning(f"Failed to create statistical features for {feature}: {e}")

        return df

    def _add_rank_features(self, df: pd.DataFrame, numerical_features: List[str]) -> pd.DataFrame:
        """Add rank-based features"""
        logger.info("Adding rank features")

        # Select subset for ranking
        rank_features = numerical_features[:10]

        for feature in rank_features:
            if feature not in df.columns:
                continue

            try:
                # Percentile rank
                df[f"{feature}_pct_rank"] = df[feature].rank(pct=True)

                # Quantile binning
                df[f"{feature}_quantile"] = pd.qcut(
                    df[feature], q=10, labels=False, duplicates="drop"
                )

            except Exception as e:
                logger.warning(f"Failed to create rank features for {feature}: {e}")

        return df


class FeatureInteractionEngine:
    """Advanced feature interaction discovery and generation"""

    def __init__(self, config: Optional[EnsembleFeatureConfig] = None):
        self.config = config or EnsembleFeatureConfig()

    def discover_interactions(
        self, df: pd.DataFrame, target_column: str, max_interactions: int = 50
    ) -> List[Tuple[str, str, float]]:
        """Discover important feature interactions based on target correlation"""

        numerical_features = self._get_numerical_features(df)
        interactions = []

        logger.info(f"Discovering interactions among {len(numerical_features)} features")

        for feature1, feature2 in combinations(numerical_features, 2):
            if feature1 not in df.columns or feature2 not in df.columns:
                continue

            try:
                # Create interaction term
                interaction_term = df[feature1] * df[feature2]

                # Calculate correlation with target
                correlation = abs(interaction_term.corr(df[target_column]))

                if not np.isnan(correlation) and correlation > 0.1:
                    interactions.append((feature1, feature2, correlation))

            except Exception as e:
                continue

        # Sort by correlation strength
        interactions.sort(key=lambda x: x[2], reverse=True)

        logger.info(f"Discovered {len(interactions)} significant interactions")
        return interactions[:max_interactions]

    def _get_numerical_features(self, df: pd.DataFrame) -> List[str]:
        """Get numerical features for interaction discovery"""
        return [
            col
            for col in df.columns
            if df[col].dtype in ["int64", "float64"]
            and not col.startswith("target_")
            and df[col].notna().sum() > 0
        ]

    def generate_advanced_interactions(
        self, df: pd.DataFrame, feature_pairs: List[Tuple[str, str]]
    ) -> pd.DataFrame:
        """Generate advanced interaction terms for discovered feature pairs"""

        df_enhanced = df.copy()

        for feature1, feature2 in feature_pairs:
            if feature1 not in df.columns or feature2 not in df.columns:
                continue

            try:
                # Conditional interactions
                df_enhanced[f"{feature1}_when_high_{feature2}"] = np.where(
                    df[feature2] > df[feature2].median(), df[feature1], 0
                )

                df_enhanced[f"{feature2}_when_high_{feature1}"] = np.where(
                    df[feature1] > df[feature1].median(), df[feature2], 0
                )

                # Non-linear interactions
                df_enhanced[f"{feature1}_squared_x_{feature2}"] = (df[feature1] ** 2) * df[feature2]

                # Min/max interactions
                df_enhanced[f"min_{feature1}_{feature2}"] = np.minimum(df[feature1], df[feature2])
                df_enhanced[f"max_{feature1}_{feature2}"] = np.maximum(df[feature1], df[feature2])

            except Exception as e:
                logger.warning(
                    f"Failed to create advanced interactions for {feature1}, {feature2}: {e}"
                )

        return df_enhanced


class DynamicFeatureSelector:
    """Dynamic feature selection based on multiple criteria"""

    def __init__(self, config: Optional[EnsembleFeatureConfig] = None):
        self.config = config or EnsembleFeatureConfig()

    def select_features(
        self,
        df: pd.DataFrame,
        target_column: str,
        selection_methods: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Select features using multiple criteria"""

        if selection_methods is None:
            selection_methods = ["variance", "correlation", "mutual_info"]

        feature_scores = {}
        selected_features = set()

        # Get feature columns (exclude target)
        feature_columns = [
            col for col in df.columns if col != target_column and not col.startswith("target_")
        ]

        logger.info(f"Selecting from {len(feature_columns)} features")

        # Apply different selection methods
        for method in selection_methods:
            method_features = self._apply_selection_method(
                df[feature_columns], df[target_column], method
            )
            feature_scores[method] = method_features
            selected_features.update(method_features[:50])  # Top 50 from each method

        # Combine selections
        final_features = list(selected_features)[: self.config.feature_selection_k]

        # Create result dataframe
        result_df = df[[target_column] + final_features].copy()

        selection_info = {
            "original_feature_count": len(feature_columns),
            "selected_feature_count": len(final_features),
            "selection_methods": selection_methods,
            "feature_scores": feature_scores,
            "selected_features": final_features,
        }

        logger.info(
            f"Selected {len(final_features)} features from {len(feature_columns)} original features"
        )

        return result_df, selection_info

    def _apply_selection_method(self, X: pd.DataFrame, y: pd.Series, method: str) -> List[str]:
        """Apply specific feature selection method"""

        try:
            if method == "variance":
                # Variance-based selection
                variances = X.var()
                feature_scores = variances.sort_values(ascending=False)
                return feature_scores.index.tolist()

            elif method == "correlation":
                # Correlation-based selection
                correlations = X.corrwith(y).abs()
                feature_scores = correlations.sort_values(ascending=False)
                return feature_scores.dropna().index.tolist()

            elif method == "mutual_info":
                # Mutual information selection
                X_filled = X.fillna(0)
                y_filled = y.fillna(0)

                # Use a subset to avoid memory issues
                if len(X.columns) > 100:
                    selected_cols = X.columns[:100]
                    X_subset = X_filled[selected_cols]
                else:
                    X_subset = X_filled

                mi_scores = mutual_info_regression(X_subset, y_filled, random_state=42)
                feature_scores = pd.Series(mi_scores, index=X_subset.columns)
                feature_scores = feature_scores.sort_values(ascending=False)
                return feature_scores.index.tolist()

            elif method == "f_test":
                # F-test based selection
                X_filled = X.fillna(0)
                y_filled = y.fillna(0)

                selector = SelectKBest(score_func=f_regression, k=min(50, len(X.columns)))
                selector.fit(X_filled, y_filled)

                selected_indices = selector.get_support(indices=True)
                return X.columns[selected_indices].tolist()

        except Exception as e:
            logger.warning(f"Feature selection method {method} failed: {e}")
            return []

        return []
