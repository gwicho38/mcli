"""Model monitoring and drift detection for ML systems"""

import asyncio
import json
import logging
import pickle
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.metrics import ks_2samp
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class DriftType(Enum):
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    MODEL_DEGRADATION = "model_degradation"


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """Drift detection alert"""

    timestamp: datetime
    drift_type: DriftType
    severity: AlertSeverity
    metric_name: str
    value: float
    threshold: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelMetrics:
    """Model performance metrics"""

    timestamp: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: Optional[float] = None
    log_loss: Optional[float] = None
    mse: Optional[float] = None
    mae: Optional[float] = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class DataProfile:
    """Statistical profile of data"""

    feature_means: Dict[str, float]
    feature_stds: Dict[str, float]
    feature_mins: Dict[str, float]
    feature_maxs: Dict[str, float]
    feature_nulls: Dict[str, float]
    correlation_matrix: np.ndarray
    timestamp: datetime


class StatisticalDriftDetector:
    """Detect statistical drift in data distributions"""

    def __init__(
        self, reference_data: pd.DataFrame, significance_level: float = 0.05, min_samples: int = 100
    ):
        self.reference_data = reference_data
        self.reference_profile = self._create_data_profile(reference_data)
        self.significance_level = significance_level
        self.min_samples = min_samples

    def detect_drift(self, current_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect drift between reference and current data"""
        if len(current_data) < self.min_samples:
            return {"drift_detected": False, "message": "Insufficient samples"}

        drift_results = {}
        current_profile = self._create_data_profile(current_data)

        # Kolmogorov-Smirnov test for each feature
        ks_results = {}
        for feature in self.reference_data.columns:
            if feature in current_data.columns and pd.api.types.is_numeric_dtype(
                current_data[feature]
            ):
                ref_values = self.reference_data[feature].dropna()
                curr_values = current_data[feature].dropna()

                if len(ref_values) > 0 and len(curr_values) > 0:
                    ks_stat, p_value = ks_2samp(ref_values, curr_values)
                    ks_results[feature] = {
                        "ks_statistic": ks_stat,
                        "p_value": p_value,
                        "drift_detected": p_value < self.significance_level,
                    }

        # Population Stability Index (PSI)
        psi_results = self._calculate_psi(self.reference_data, current_data)

        # Feature distribution comparisons
        feature_comparisons = self._compare_feature_distributions(
            self.reference_profile, current_profile
        )

        drift_results = {
            "timestamp": datetime.now(),
            "ks_tests": ks_results,
            "psi_scores": psi_results,
            "feature_comparisons": feature_comparisons,
            "overall_drift_detected": any(
                result.get("drift_detected", False) for result in ks_results.values()
            )
            or any(score > 0.25 for score in psi_results.values()),
            "reference_profile": asdict(self.reference_profile),
            "current_profile": asdict(current_profile),
        }

        return drift_results

    def _create_data_profile(self, data: pd.DataFrame) -> DataProfile:
        """Create statistical profile of data"""
        numeric_data = data.select_dtypes(include=[np.number])

        return DataProfile(
            feature_means=numeric_data.mean().to_dict(),
            feature_stds=numeric_data.std().to_dict(),
            feature_mins=numeric_data.min().to_dict(),
            feature_maxs=numeric_data.max().to_dict(),
            feature_nulls=data.isnull().sum().to_dict(),
            correlation_matrix=(
                numeric_data.corr().values if len(numeric_data.columns) > 1 else np.array([])
            ),
            timestamp=datetime.now(),
        )

    def _calculate_psi(
        self, reference_data: pd.DataFrame, current_data: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate Population Stability Index for each feature"""
        psi_scores = {}

        for feature in reference_data.columns:
            if feature in current_data.columns and pd.api.types.is_numeric_dtype(
                reference_data[feature]
            ):
                ref_values = reference_data[feature].dropna()
                curr_values = current_data[feature].dropna()

                if len(ref_values) > 0 and len(curr_values) > 0:
                    psi_score = self._psi_score(ref_values, curr_values)
                    psi_scores[feature] = psi_score

        return psi_scores

    def _psi_score(self, reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
        """Calculate PSI score between two distributions"""
        try:
            # Create bins based on reference data
            ref_min, ref_max = reference.min(), reference.max()
            bin_edges = np.linspace(ref_min, ref_max, bins + 1)

            # Calculate frequencies
            ref_freq, _ = np.histogram(reference, bins=bin_edges)
            curr_freq, _ = np.histogram(current, bins=bin_edges)

            # Convert to proportions
            ref_prop = ref_freq / len(reference)
            curr_prop = curr_freq / len(current)

            # Add small epsilon to avoid log(0)
            epsilon = 1e-10
            ref_prop = np.maximum(ref_prop, epsilon)
            curr_prop = np.maximum(curr_prop, epsilon)

            # Calculate PSI
            psi = np.sum((curr_prop - ref_prop) * np.log(curr_prop / ref_prop))
            return psi

        except Exception as e:
            logger.warning(f"Failed to calculate PSI: {e}")
            return 0.0

    def _compare_feature_distributions(
        self, ref_profile: DataProfile, curr_profile: DataProfile
    ) -> Dict[str, Dict[str, float]]:
        """Compare feature distributions between profiles"""
        comparisons = {}

        for feature in ref_profile.feature_means.keys():
            if feature in curr_profile.feature_means:
                ref_mean = ref_profile.feature_means[feature]
                curr_mean = curr_profile.feature_means[feature]
                ref_std = ref_profile.feature_stds[feature]

                # Calculate z-score for mean shift
                z_score = abs(curr_mean - ref_mean) / ref_std if ref_std > 0 else 0

                # Calculate coefficient of variation change
                ref_cv = ref_std / ref_mean if ref_mean != 0 else 0
                curr_cv = curr_profile.feature_stds[feature] / curr_mean if curr_mean != 0 else 0
                cv_change = abs(curr_cv - ref_cv) / ref_cv if ref_cv > 0 else 0

                comparisons[feature] = {
                    "mean_z_score": z_score,
                    "cv_change": cv_change,
                    "mean_shift_detected": z_score > 2.0,
                    "variance_change_detected": cv_change > 0.5,
                }

        return comparisons


class ConceptDriftDetector:
    """Detect concept drift in model predictions"""

    def __init__(self, window_size: int = 1000, detection_threshold: float = 0.05):
        self.window_size = window_size
        self.detection_threshold = detection_threshold
        self.historical_metrics = []

    def add_batch_metrics(self, metrics: ModelMetrics):
        """Add batch metrics for drift detection"""
        self.historical_metrics.append(metrics)

        # Keep only recent metrics
        if len(self.historical_metrics) > self.window_size * 2:
            self.historical_metrics = self.historical_metrics[-self.window_size :]

    def detect_concept_drift(self) -> Dict[str, Any]:
        """Detect concept drift using model performance degradation"""
        if len(self.historical_metrics) < self.window_size:
            return {"drift_detected": False, "message": "Insufficient historical data"}

        # Split metrics into two windows
        mid_point = len(self.historical_metrics) // 2
        early_metrics = self.historical_metrics[:mid_point]
        recent_metrics = self.historical_metrics[mid_point:]

        # Calculate average performance for each window
        early_performance = self._calculate_average_performance(early_metrics)
        recent_performance = self._calculate_average_performance(recent_metrics)

        # Detect significant performance degradation
        drift_detected = False
        degraded_metrics = []

        for metric_name in ["accuracy", "precision", "recall", "f1_score"]:
            if metric_name in early_performance and metric_name in recent_performance:
                early_value = early_performance[metric_name]
                recent_value = recent_performance[metric_name]

                # Check for significant decrease
                if early_value > 0:
                    relative_change = (recent_value - early_value) / early_value
                    if relative_change < -self.detection_threshold:
                        drift_detected = True
                        degraded_metrics.append(
                            {
                                "metric": metric_name,
                                "early_value": early_value,
                                "recent_value": recent_value,
                                "relative_change": relative_change,
                            }
                        )

        return {
            "drift_detected": drift_detected,
            "degraded_metrics": degraded_metrics,
            "early_performance": early_performance,
            "recent_performance": recent_performance,
            "timestamp": datetime.now(),
        }

    def _calculate_average_performance(self, metrics_list: List[ModelMetrics]) -> Dict[str, float]:
        """Calculate average performance metrics"""
        if not metrics_list:
            return {}

        performance = {
            "accuracy": np.mean([m.accuracy for m in metrics_list]),
            "precision": np.mean([m.precision for m in metrics_list]),
            "recall": np.mean([m.recall for m in metrics_list]),
            "f1_score": np.mean([m.f1_score for m in metrics_list]),
        }

        # Add optional metrics if available
        auc_scores = [m.auc_roc for m in metrics_list if m.auc_roc is not None]
        if auc_scores:
            performance["auc_roc"] = np.mean(auc_scores)

        return performance


class OutlierDetector:
    """Detect outliers in incoming data"""

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.detector = None
        self.is_fitted = False

    def fit(self, reference_data: pd.DataFrame):
        """Fit outlier detector on reference data"""
        numeric_data = reference_data.select_dtypes(include=[np.number])

        if numeric_data.empty:
            logger.warning("No numeric features found for outlier detection")
            return

        self.detector = IsolationForest(contamination=self.contamination, random_state=42)
        self.detector.fit(numeric_data.fillna(0))
        self.is_fitted = True

    def detect_outliers(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect outliers in new data"""
        if not self.is_fitted:
            return {"outliers_detected": False, "message": "Detector not fitted"}

        numeric_data = data.select_dtypes(include=[np.number])

        if numeric_data.empty:
            return {"outliers_detected": False, "message": "No numeric features"}

        # Predict outliers
        outlier_scores = self.detector.decision_function(numeric_data.fillna(0))
        outlier_labels = self.detector.predict(numeric_data.fillna(0))

        outliers_mask = outlier_labels == -1
        outlier_ratio = np.mean(outliers_mask)

        return {
            "outliers_detected": outlier_ratio > self.contamination * 2,  # Alert if 2x expected
            "outlier_ratio": outlier_ratio,
            "outlier_scores": outlier_scores.tolist(),
            "outlier_indices": np.where(outliers_mask)[0].tolist(),
            "timestamp": datetime.now(),
        }


class ModelMonitor:
    """Comprehensive model monitoring system"""

    def __init__(self, model_name: str, storage_path: Path = Path("monitoring")):
        self.model_name = model_name
        self.storage_path = storage_path / model_name
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize detectors
        self.statistical_detector = None
        self.concept_detector = ConceptDriftDetector()
        self.outlier_detector = OutlierDetector()

        # Monitoring configuration
        self.thresholds = {
            "data_drift_psi": 0.25,
            "concept_drift_threshold": 0.05,
            "outlier_ratio_threshold": 0.2,
            "performance_degradation": 0.1,
        }

        # Alert handlers
        self.alert_handlers = []

        # Monitoring history
        self.monitoring_history = []

    def setup_reference_data(self, reference_data: pd.DataFrame):
        """Set up reference data for drift detection"""
        self.statistical_detector = StatisticalDriftDetector(reference_data)
        self.outlier_detector.fit(reference_data)

        # Save reference data profile
        self._save_reference_profile(reference_data)

    def monitor_batch(
        self,
        current_data: pd.DataFrame,
        predictions: np.ndarray,
        true_labels: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Monitor a batch of data and predictions"""
        monitoring_result = {
            "timestamp": datetime.now(),
            "batch_size": len(current_data),
            "alerts": [],
            "metrics": {},
        }

        # Data drift detection
        if self.statistical_detector:
            drift_result = self.statistical_detector.detect_drift(current_data)
            monitoring_result["data_drift"] = drift_result

            if drift_result.get("overall_drift_detected", False):
                alert = DriftAlert(
                    timestamp=datetime.now(),
                    drift_type=DriftType.DATA_DRIFT,
                    severity=AlertSeverity.MEDIUM,
                    metric_name="overall_data_drift",
                    value=1.0,
                    threshold=0.5,
                    description="Statistical drift detected in input features",
                    metadata=drift_result,
                )
                monitoring_result["alerts"].append(alert)

        # Outlier detection
        outlier_result = self.outlier_detector.detect_outliers(current_data)
        monitoring_result["outliers"] = outlier_result

        if outlier_result.get("outliers_detected", False):
            alert = DriftAlert(
                timestamp=datetime.now(),
                drift_type=DriftType.DATA_DRIFT,
                severity=AlertSeverity.LOW,
                metric_name="outlier_ratio",
                value=outlier_result["outlier_ratio"],
                threshold=self.thresholds["outlier_ratio_threshold"],
                description=f"High outlier ratio detected: {outlier_result['outlier_ratio']:.3f}",
                metadata=outlier_result,
            )
            monitoring_result["alerts"].append(alert)

        # Prediction drift analysis
        prediction_stats = self._analyze_predictions(predictions)
        monitoring_result["prediction_stats"] = prediction_stats

        # Model performance monitoring (if true labels available)
        if true_labels is not None:
            performance_metrics = self._calculate_performance_metrics(predictions, true_labels)
            monitoring_result["performance"] = performance_metrics

            # Add to concept drift detector
            self.concept_detector.add_batch_metrics(performance_metrics)

            # Check for concept drift
            concept_drift_result = self.concept_detector.detect_concept_drift()
            monitoring_result["concept_drift"] = concept_drift_result

            if concept_drift_result.get("drift_detected", False):
                alert = DriftAlert(
                    timestamp=datetime.now(),
                    drift_type=DriftType.CONCEPT_DRIFT,
                    severity=AlertSeverity.HIGH,
                    metric_name="model_performance",
                    value=performance_metrics.accuracy,
                    threshold=self.thresholds["performance_degradation"],
                    description="Model performance degradation detected",
                    metadata=concept_drift_result,
                )
                monitoring_result["alerts"].append(alert)

        # Process alerts
        for alert in monitoring_result["alerts"]:
            self._handle_alert(alert)

        # Save monitoring result
        self._save_monitoring_result(monitoring_result)

        return monitoring_result

    def add_alert_handler(self, handler: Callable[[DriftAlert], None]):
        """Add alert handler function"""
        self.alert_handlers.append(handler)

    def get_monitoring_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get monitoring summary for the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_results = [
            result for result in self.monitoring_history if result["timestamp"] >= cutoff_date
        ]

        if not recent_results:
            return {"message": "No monitoring data available"}

        # Count alerts by type and severity
        alert_counts = {}
        for result in recent_results:
            for alert in result.get("alerts", []):
                key = f"{alert.drift_type.value}_{alert.severity.value}"
                alert_counts[key] = alert_counts.get(key, 0) + 1

        # Calculate average metrics
        avg_metrics = {}
        if recent_results and "performance" in recent_results[0]:
            performance_data = [r["performance"] for r in recent_results if "performance" in r]
            if performance_data:
                avg_metrics = {
                    "avg_accuracy": np.mean([p.accuracy for p in performance_data]),
                    "avg_precision": np.mean([p.precision for p in performance_data]),
                    "avg_recall": np.mean([p.recall for p in performance_data]),
                    "avg_f1_score": np.mean([p.f1_score for p in performance_data]),
                }

        return {
            "period_days": days,
            "total_batches": len(recent_results),
            "alert_counts": alert_counts,
            "average_metrics": avg_metrics,
            "latest_timestamp": recent_results[-1]["timestamp"] if recent_results else None,
        }

    def _analyze_predictions(self, predictions: np.ndarray) -> Dict[str, Any]:
        """Analyze prediction distribution"""
        return {
            "mean": float(np.mean(predictions)),
            "std": float(np.std(predictions)),
            "min": float(np.min(predictions)),
            "max": float(np.max(predictions)),
            "unique_values": len(np.unique(predictions)),
        }

    def _calculate_performance_metrics(
        self, predictions: np.ndarray, true_labels: np.ndarray
    ) -> ModelMetrics:
        """Calculate model performance metrics"""
        # Convert to binary if needed
        if len(np.unique(true_labels)) == 2:
            # Binary classification
            pred_binary = (predictions > 0.5).astype(int)
            true_binary = true_labels.astype(int)

            tp = np.sum((pred_binary == 1) & (true_binary == 1))
            fp = np.sum((pred_binary == 1) & (true_binary == 0))
            tn = np.sum((pred_binary == 0) & (true_binary == 0))
            fn = np.sum((pred_binary == 0) & (true_binary == 1))

            accuracy = (tp + tn) / len(true_labels) if len(true_labels) > 0 else 0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1_score = (
                2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            )

            return ModelMetrics(
                timestamp=datetime.now(),
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1_score,
            )
        else:
            # Regression metrics
            mse = np.mean((predictions - true_labels) ** 2)
            mae = np.mean(np.abs(predictions - true_labels))

            return ModelMetrics(
                timestamp=datetime.now(),
                accuracy=0.0,  # Not applicable for regression
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                mse=mse,
                mae=mae,
            )

    def _handle_alert(self, alert: DriftAlert):
        """Handle drift alert"""
        logger.warning(
            f"DRIFT ALERT: {alert.description} "
            f"(Type: {alert.drift_type.value}, Severity: {alert.severity.value})"
        )

        # Call registered alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

    def _save_monitoring_result(self, result: Dict[str, Any]):
        """Save monitoring result to storage"""
        timestamp_str = result["timestamp"].strftime("%Y%m%d_%H%M%S")
        filename = self.storage_path / f"monitoring_{timestamp_str}.json"

        # Convert non-serializable objects
        serializable_result = self._make_serializable(result)

        with open(filename, "w") as f:
            json.dump(serializable_result, f, indent=2, default=str)

        self.monitoring_history.append(result)

        # Keep only recent history in memory
        if len(self.monitoring_history) > 1000:
            self.monitoring_history = self.monitoring_history[-500:]

    def _save_reference_profile(self, reference_data: pd.DataFrame):
        """Save reference data profile"""
        profile_file = self.storage_path / "reference_profile.pkl"

        with open(profile_file, "wb") as f:
            pickle.dump(reference_data, f)

    def _make_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, DriftAlert):
            return asdict(obj)
        elif isinstance(obj, ModelMetrics):
            return asdict(obj)
        elif isinstance(obj, (DriftType, AlertSeverity)):
            return obj.value
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        else:
            return obj


# Example alert handlers
def email_alert_handler(alert: DriftAlert):
    """Example email alert handler"""
    logger.info(f"EMAIL ALERT: {alert.description}")
    # In production, would send actual email


def slack_alert_handler(alert: DriftAlert):
    """Example Slack alert handler"""
    logger.info(f"SLACK ALERT: {alert.description}")
    # In production, would send to Slack


# Example usage
if __name__ == "__main__":
    # Generate sample data
    np.random.seed(42)
    reference_data = pd.DataFrame(
        {
            "feature1": np.random.normal(0, 1, 1000),
            "feature2": np.random.normal(5, 2, 1000),
            "feature3": np.random.uniform(0, 10, 1000),
        }
    )

    # Initialize monitor
    monitor = ModelMonitor("stock_recommendation_model")
    monitor.setup_reference_data(reference_data)

    # Add alert handlers
    monitor.add_alert_handler(email_alert_handler)
    monitor.add_alert_handler(slack_alert_handler)

    # Simulate monitoring batches
    for i in range(10):
        # Generate current data (with some drift)
        drift_factor = i * 0.1
        current_data = pd.DataFrame(
            {
                "feature1": np.random.normal(drift_factor, 1, 100),
                "feature2": np.random.normal(5 + drift_factor, 2, 100),
                "feature3": np.random.uniform(0, 10 + drift_factor, 100),
            }
        )

        # Generate predictions and labels
        predictions = np.random.uniform(0, 1, 100)
        true_labels = (predictions + np.random.normal(0, 0.1, 100) > 0.5).astype(int)

        # Monitor batch
        result = monitor.monitor_batch(current_data, predictions, true_labels)

        print(f"Batch {i}: {len(result['alerts'])} alerts generated")

    # Get monitoring summary
    summary = monitor.get_monitoring_summary(days=1)
    print(f"Monitoring Summary: {json.dumps(summary, indent=2, default=str)}")

    logger.info("Model monitoring demo completed")
