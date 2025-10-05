"""A/B Testing framework for ML model experiments"""

import asyncio
import hashlib
import json
import logging
import random
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VariantType(Enum):
    CONTROL = "control"
    TREATMENT = "treatment"


@dataclass
class Variant:
    """A/B test variant configuration"""

    id: str
    name: str
    type: VariantType
    traffic_percentage: float
    model_config: Dict[str, Any] = field(default_factory=dict)
    feature_flags: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class Metric:
    """A/B test metric definition"""

    name: str
    type: str  # "binary", "continuous", "count"
    aggregation: str  # "mean", "sum", "count", "rate"
    goal: str  # "increase", "decrease", "maintain"
    statistical_power: float = 0.8
    min_detectable_effect: float = 0.05
    primary: bool = False


@dataclass
class ExperimentConfig:
    """A/B test experiment configuration"""

    id: str
    name: str
    description: str
    variants: List[Variant]
    metrics: List[Metric]

    # Traffic configuration
    traffic_percentage: float = 100.0  # Percentage of traffic to include

    # Duration configuration
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_duration_days: int = 7
    max_duration_days: int = 30

    # Statistical configuration
    significance_level: float = 0.05
    statistical_power: float = 0.8
    min_sample_size: int = 1000

    # Guardrail metrics
    guardrail_metrics: List[str] = field(default_factory=list)

    # Feature flags
    feature_flags: Dict[str, Any] = field(default_factory=dict)

    status: ExperimentStatus = ExperimentStatus.DRAFT


@dataclass
class UserAssignment:
    """User assignment to experiment variant"""

    user_id: str
    experiment_id: str
    variant_id: str
    assigned_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentResult:
    """Results of an A/B test experiment"""

    experiment_id: str
    variant_results: Dict[str, Dict[str, Any]]
    statistical_tests: Dict[str, Dict[str, Any]]
    confidence_intervals: Dict[str, Dict[str, tuple]]
    recommendations: List[str]
    created_at: datetime

    # Overall experiment stats
    total_users: int = 0
    duration_days: int = 0
    statistical_significance: bool = False
    winner_variant: Optional[str] = None


class TrafficSplitter:
    """Handle traffic splitting for A/B tests"""

    def __init__(self):
        self.assignments = {}

    def assign_variant(self, user_id: str, experiment: ExperimentConfig) -> str:
        """Assign user to experiment variant"""
        # Check if user already assigned
        cache_key = f"{user_id}:{experiment.id}"
        if cache_key in self.assignments:
            return self.assignments[cache_key]

        # Hash user ID for consistent assignment
        hash_input = f"{user_id}:{experiment.id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        hash_ratio = (hash_value % 10000) / 10000.0

        # Check if user should be included in experiment
        if hash_ratio * 100 > experiment.traffic_percentage:
            return "control"  # Not in experiment

        # Assign to variant based on traffic split
        cumulative_percentage = 0
        for variant in experiment.variants:
            cumulative_percentage += variant.traffic_percentage
            if hash_ratio * 100 <= cumulative_percentage:
                self.assignments[cache_key] = variant.id
                return variant.id

        # Default to control
        control_variant = next(
            (v for v in experiment.variants if v.type == VariantType.CONTROL),
            experiment.variants[0],
        )
        self.assignments[cache_key] = control_variant.id
        return control_variant.id

    def get_assignment(self, user_id: str, experiment_id: str) -> Optional[str]:
        """Get existing assignment"""
        cache_key = f"{user_id}:{experiment_id}"
        return self.assignments.get(cache_key)


class MetricsCollector:
    """Collect and store experiment metrics"""

    def __init__(self, storage_path: Path = Path("experiments/metrics")):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.metrics_buffer = []

    def record_metric(
        self,
        user_id: str,
        experiment_id: str,
        variant_id: str,
        metric_name: str,
        value: Union[float, int, bool],
        timestamp: Optional[datetime] = None,
    ):
        """Record a metric value for a user"""
        if timestamp is None:
            timestamp = datetime.now()

        metric_record = {
            "user_id": user_id,
            "experiment_id": experiment_id,
            "variant_id": variant_id,
            "metric_name": metric_name,
            "value": value,
            "timestamp": timestamp.isoformat(),
        }

        self.metrics_buffer.append(metric_record)

        # Flush buffer if it gets too large
        if len(self.metrics_buffer) >= 1000:
            self.flush_metrics()

    def flush_metrics(self):
        """Flush metrics buffer to storage"""
        if not self.metrics_buffer:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.storage_path / f"metrics_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.metrics_buffer, f, indent=2)

        logger.info(f"Flushed {len(self.metrics_buffer)} metrics to {filename}")
        self.metrics_buffer.clear()

    def get_experiment_metrics(self, experiment_id: str) -> pd.DataFrame:
        """Get all metrics for an experiment"""
        all_metrics = []

        # Load from all metric files
        for file_path in self.storage_path.glob("metrics_*.json"):
            with open(file_path, "r") as f:
                metrics = json.load(f)
                experiment_metrics = [m for m in metrics if m["experiment_id"] == experiment_id]
                all_metrics.extend(experiment_metrics)

        if not all_metrics:
            return pd.DataFrame()

        df = pd.DataFrame(all_metrics)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df


class StatisticalAnalyzer:
    """Perform statistical analysis on A/B test results"""

    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level

    def analyze_experiment(
        self, experiment: ExperimentConfig, metrics_df: pd.DataFrame
    ) -> ExperimentResult:
        """Analyze experiment results"""
        if metrics_df.empty:
            return self._empty_result(experiment.id)

        # Group metrics by variant
        variant_data = {}
        for variant in experiment.variants:
            variant_metrics = metrics_df[metrics_df["variant_id"] == variant.id]
            variant_data[variant.id] = self._analyze_variant_metrics(
                variant_metrics, experiment.metrics
            )

        # Perform statistical tests
        statistical_tests = {}
        confidence_intervals = {}

        control_variant = next(
            (v for v in experiment.variants if v.type == VariantType.CONTROL), None
        )
        if control_variant:
            for variant in experiment.variants:
                if variant.type == VariantType.TREATMENT:
                    tests, intervals = self._compare_variants(
                        metrics_df, control_variant.id, variant.id, experiment.metrics
                    )
                    statistical_tests[variant.id] = tests
                    confidence_intervals[variant.id] = intervals

        # Generate recommendations
        recommendations = self._generate_recommendations(
            variant_data, statistical_tests, experiment.metrics
        )

        # Determine winner
        winner = self._determine_winner(statistical_tests, experiment.metrics)

        return ExperimentResult(
            experiment_id=experiment.id,
            variant_results=variant_data,
            statistical_tests=statistical_tests,
            confidence_intervals=confidence_intervals,
            recommendations=recommendations,
            created_at=datetime.now(),
            total_users=len(metrics_df["user_id"].unique()),
            duration_days=(
                (datetime.now() - experiment.start_date).days if experiment.start_date else 0
            ),
            statistical_significance=any(
                test.get("significant", False) for test in statistical_tests.values()
            ),
            winner_variant=winner,
        )

    def _analyze_variant_metrics(
        self, variant_df: pd.DataFrame, metrics_config: List[Metric]
    ) -> Dict[str, Any]:
        """Analyze metrics for a single variant"""
        if variant_df.empty:
            return {}

        results = {}
        for metric in metrics_config:
            metric_data = variant_df[variant_df["metric_name"] == metric.name]["value"]

            if metric_data.empty:
                continue

            if metric.type == "binary":
                results[metric.name] = {
                    "count": len(metric_data),
                    "success_rate": metric_data.mean(),
                    "std": metric_data.std(),
                    "confidence_interval": self._binary_confidence_interval(metric_data),
                }
            elif metric.type == "continuous":
                results[metric.name] = {
                    "count": len(metric_data),
                    "mean": metric_data.mean(),
                    "std": metric_data.std(),
                    "median": metric_data.median(),
                    "confidence_interval": self._continuous_confidence_interval(metric_data),
                }
            elif metric.type == "count":
                results[metric.name] = {
                    "count": len(metric_data),
                    "sum": metric_data.sum(),
                    "mean": metric_data.mean(),
                    "rate_per_user": metric_data.sum() / len(variant_df["user_id"].unique()),
                }

        return results

    def _compare_variants(
        self,
        metrics_df: pd.DataFrame,
        control_id: str,
        treatment_id: str,
        metrics_config: List[Metric],
    ) -> tuple:
        """Compare treatment variant against control"""
        tests = {}
        intervals = {}

        for metric in metrics_config:
            control_data = metrics_df[
                (metrics_df["variant_id"] == control_id)
                & (metrics_df["metric_name"] == metric.name)
            ]["value"]

            treatment_data = metrics_df[
                (metrics_df["variant_id"] == treatment_id)
                & (metrics_df["metric_name"] == metric.name)
            ]["value"]

            if control_data.empty or treatment_data.empty:
                continue

            if metric.type == "binary":
                test_result = self._binary_test(control_data, treatment_data)
            elif metric.type == "continuous":
                test_result = self._continuous_test(control_data, treatment_data)
            else:
                test_result = self._count_test(control_data, treatment_data)

            tests[metric.name] = test_result

            # Calculate effect size confidence interval
            if metric.type == "binary":
                intervals[metric.name] = self._binary_effect_interval(control_data, treatment_data)
            else:
                intervals[metric.name] = self._continuous_effect_interval(
                    control_data, treatment_data
                )

        return tests, intervals

    def _binary_test(self, control: pd.Series, treatment: pd.Series) -> Dict[str, Any]:
        """Perform statistical test for binary metric"""
        control_success = control.sum()
        control_total = len(control)
        treatment_success = treatment.sum()
        treatment_total = len(treatment)

        # Chi-square test
        observed = [
            [control_success, control_total - control_success],
            [treatment_success, treatment_total - treatment_success],
        ]

        chi2, p_value, _, _ = stats.chi2_contingency(observed)

        # Effect size (difference in rates)
        control_rate = control_success / control_total
        treatment_rate = treatment_success / treatment_total
        effect_size = treatment_rate - control_rate

        return {
            "test_type": "chi_square",
            "statistic": chi2,
            "p_value": p_value,
            "significant": p_value < self.significance_level,
            "effect_size": effect_size,
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
        }

    def _continuous_test(self, control: pd.Series, treatment: pd.Series) -> Dict[str, Any]:
        """Perform statistical test for continuous metric"""
        # Two-sample t-test
        statistic, p_value = stats.ttest_ind(treatment, control)

        # Effect size (Cohen's d)
        pooled_std = np.sqrt(
            ((len(control) - 1) * control.std() ** 2 + (len(treatment) - 1) * treatment.std() ** 2)
            / (len(control) + len(treatment) - 2)
        )

        cohens_d = (treatment.mean() - control.mean()) / pooled_std if pooled_std > 0 else 0

        return {
            "test_type": "t_test",
            "statistic": statistic,
            "p_value": p_value,
            "significant": p_value < self.significance_level,
            "effect_size": cohens_d,
            "control_mean": control.mean(),
            "treatment_mean": treatment.mean(),
            "relative_change": (
                (treatment.mean() - control.mean()) / control.mean() if control.mean() != 0 else 0
            ),
        }

    def _count_test(self, control: pd.Series, treatment: pd.Series) -> Dict[str, Any]:
        """Perform statistical test for count metric"""
        # Poisson test (approximated with normal for large samples)
        control_sum = control.sum()
        treatment_sum = treatment.sum()

        # Rate comparison
        control_rate = control_sum / len(control)
        treatment_rate = treatment_sum / len(treatment)

        # Use two-sample Poisson test approximation
        if control_rate > 0 and treatment_rate > 0:
            statistic, p_value = stats.ttest_ind(treatment, control)
        else:
            statistic, p_value = 0, 1

        return {
            "test_type": "poisson_approximation",
            "statistic": statistic,
            "p_value": p_value,
            "significant": p_value < self.significance_level,
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
            "rate_ratio": treatment_rate / control_rate if control_rate > 0 else float("inf"),
        }

    def _binary_confidence_interval(self, data: pd.Series, confidence: float = 0.95) -> tuple:
        """Calculate confidence interval for binary metric"""
        n = len(data)
        p = data.mean()
        z = stats.norm.ppf(1 - (1 - confidence) / 2)
        margin = z * np.sqrt(p * (1 - p) / n) if n > 0 else 0
        return (max(0, p - margin), min(1, p + margin))

    def _continuous_confidence_interval(self, data: pd.Series, confidence: float = 0.95) -> tuple:
        """Calculate confidence interval for continuous metric"""
        n = len(data)
        mean = data.mean()
        sem = data.std() / np.sqrt(n) if n > 0 else 0
        t_value = stats.t.ppf(1 - (1 - confidence) / 2, n - 1) if n > 1 else 0
        margin = t_value * sem
        return (mean - margin, mean + margin)

    def _binary_effect_interval(self, control: pd.Series, treatment: pd.Series) -> tuple:
        """Calculate confidence interval for binary effect size"""
        p1 = control.mean()
        p2 = treatment.mean()
        n1 = len(control)
        n2 = len(treatment)

        diff = p2 - p1
        se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2) if n1 > 0 and n2 > 0 else 0
        z = stats.norm.ppf(0.975)
        margin = z * se

        return (diff - margin, diff + margin)

    def _continuous_effect_interval(self, control: pd.Series, treatment: pd.Series) -> tuple:
        """Calculate confidence interval for continuous effect size"""
        diff = treatment.mean() - control.mean()
        n1 = len(control)
        n2 = len(treatment)

        if n1 > 1 and n2 > 1:
            pooled_var = ((n1 - 1) * control.var() + (n2 - 1) * treatment.var()) / (n1 + n2 - 2)
            se = np.sqrt(pooled_var * (1 / n1 + 1 / n2))
            t_value = stats.t.ppf(0.975, n1 + n2 - 2)
            margin = t_value * se
        else:
            margin = 0

        return (diff - margin, diff + margin)

    def _generate_recommendations(
        self, variant_data: Dict, statistical_tests: Dict, metrics_config: List[Metric]
    ) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []

        primary_metrics = [m for m in metrics_config if m.primary]

        for variant_id, tests in statistical_tests.items():
            significant_improvements = []
            significant_degradations = []

            for metric_name, test in tests.items():
                if test.get("significant", False):
                    metric_config = next((m for m in metrics_config if m.name == metric_name), None)

                    if metric_config:
                        if metric_config.goal == "increase":
                            if test.get("effect_size", 0) > 0:
                                significant_improvements.append(metric_name)
                            else:
                                significant_degradations.append(metric_name)
                        elif metric_config.goal == "decrease":
                            if test.get("effect_size", 0) < 0:
                                significant_improvements.append(metric_name)
                            else:
                                significant_degradations.append(metric_name)

            if significant_improvements:
                recommendations.append(
                    f"Variant {variant_id} shows significant improvement in: {', '.join(significant_improvements)}"
                )

            if significant_degradations:
                recommendations.append(
                    f"Variant {variant_id} shows significant degradation in: {', '.join(significant_degradations)}"
                )

        if not any(
            test.get("significant", False)
            for tests in statistical_tests.values()
            for test in tests.values()
        ):
            recommendations.append(
                "No statistically significant differences detected. Consider running experiment longer."
            )

        return recommendations

    def _determine_winner(
        self, statistical_tests: Dict, metrics_config: List[Metric]
    ) -> Optional[str]:
        """Determine winning variant based on primary metrics"""
        primary_metrics = [m for m in metrics_config if m.primary]

        if not primary_metrics:
            return None

        variant_scores = {}

        for variant_id, tests in statistical_tests.items():
            score = 0

            for metric in primary_metrics:
                test = tests.get(metric.name)
                if test and test.get("significant", False):
                    effect_size = test.get("effect_size", 0)

                    if metric.goal == "increase" and effect_size > 0:
                        score += 1
                    elif metric.goal == "decrease" and effect_size < 0:
                        score += 1
                    else:
                        score -= 1

            variant_scores[variant_id] = score

        if variant_scores:
            winner = max(variant_scores.items(), key=lambda x: x[1])
            return winner[0] if winner[1] > 0 else None

        return None

    def _empty_result(self, experiment_id: str) -> ExperimentResult:
        """Return empty result for experiments with no data"""
        return ExperimentResult(
            experiment_id=experiment_id,
            variant_results={},
            statistical_tests={},
            confidence_intervals={},
            recommendations=["No data available for analysis"],
            created_at=datetime.now(),
        )


class ABTestingFramework:
    """Main A/B testing framework orchestrator"""

    def __init__(self, storage_path: Path = Path("experiments")):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.traffic_splitter = TrafficSplitter()
        self.metrics_collector = MetricsCollector(storage_path / "metrics")
        self.analyzer = StatisticalAnalyzer()

        self.experiments = {}
        self.load_experiments()

    def create_experiment(self, config: ExperimentConfig) -> str:
        """Create new A/B test experiment"""
        # Validate configuration
        self._validate_experiment_config(config)

        # Generate ID if not provided
        if not config.id:
            config.id = str(uuid.uuid4())

        # Set start date if not provided
        if not config.start_date:
            config.start_date = datetime.now()

        # Store experiment
        self.experiments[config.id] = config
        self.save_experiment(config)

        logger.info(f"Created experiment: {config.name} ({config.id})")
        return config.id

    def start_experiment(self, experiment_id: str):
        """Start an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_date = datetime.now()

        self.save_experiment(experiment)
        logger.info(f"Started experiment: {experiment.name}")

    def stop_experiment(self, experiment_id: str):
        """Stop an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_date = datetime.now()

        self.save_experiment(experiment)
        logger.info(f"Stopped experiment: {experiment.name}")

    def assign_user(self, user_id: str, experiment_id: str) -> str:
        """Assign user to experiment variant"""
        if experiment_id not in self.experiments:
            return "control"

        experiment = self.experiments[experiment_id]

        # Check experiment status
        if experiment.status != ExperimentStatus.RUNNING:
            return "control"

        # Check date range
        now = datetime.now()
        if experiment.start_date and now < experiment.start_date:
            return "control"
        if experiment.end_date and now > experiment.end_date:
            return "control"

        return self.traffic_splitter.assign_variant(user_id, experiment)

    def record_metric(
        self, user_id: str, experiment_id: str, metric_name: str, value: Union[float, int, bool]
    ):
        """Record metric for user"""
        # Get user's variant assignment
        variant_id = self.traffic_splitter.get_assignment(user_id, experiment_id)
        if not variant_id:
            variant_id = self.assign_user(user_id, experiment_id)

        # Record metric
        self.metrics_collector.record_metric(user_id, experiment_id, variant_id, metric_name, value)

    def analyze_experiment(self, experiment_id: str) -> ExperimentResult:
        """Analyze experiment results"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]
        metrics_df = self.metrics_collector.get_experiment_metrics(experiment_id)

        return self.analyzer.analyze_experiment(experiment, metrics_df)

    def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment summary"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]
        metrics_df = self.metrics_collector.get_experiment_metrics(experiment_id)

        summary = {
            "experiment": asdict(experiment),
            "total_users": len(metrics_df["user_id"].unique()) if not metrics_df.empty else 0,
            "total_events": len(metrics_df) if not metrics_df.empty else 0,
            "variant_distribution": (
                metrics_df["variant_id"].value_counts().to_dict() if not metrics_df.empty else {}
            ),
        }

        return summary

    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments"""
        return [
            {
                "id": exp.id,
                "name": exp.name,
                "status": exp.status.value,
                "start_date": exp.start_date.isoformat() if exp.start_date else None,
                "end_date": exp.end_date.isoformat() if exp.end_date else None,
                "variants": len(exp.variants),
                "metrics": len(exp.metrics),
            }
            for exp in self.experiments.values()
        ]

    def save_experiment(self, experiment: ExperimentConfig):
        """Save experiment to storage"""
        experiment_file = self.storage_path / f"experiment_{experiment.id}.json"

        # Convert to dict and handle non-serializable types
        experiment_dict = asdict(experiment)

        # Convert datetime objects to ISO strings
        if experiment_dict.get("start_date"):
            experiment_dict["start_date"] = experiment.start_date.isoformat()
        if experiment_dict.get("end_date"):
            experiment_dict["end_date"] = experiment.end_date.isoformat()

        # Convert enums to strings
        experiment_dict["status"] = experiment.status.value
        for variant in experiment_dict["variants"]:
            variant["type"] = (
                variant["type"].value if hasattr(variant["type"], "value") else variant["type"]
            )

        with open(experiment_file, "w") as f:
            json.dump(experiment_dict, f, indent=2)

    def load_experiments(self):
        """Load experiments from storage"""
        for experiment_file in self.storage_path.glob("experiment_*.json"):
            try:
                with open(experiment_file, "r") as f:
                    experiment_dict = json.load(f)

                # Convert back from dict to objects
                experiment = self._dict_to_experiment(experiment_dict)
                self.experiments[experiment.id] = experiment

            except Exception as e:
                logger.error(f"Failed to load experiment from {experiment_file}: {e}")

    def _dict_to_experiment(self, experiment_dict: Dict) -> ExperimentConfig:
        """Convert dictionary back to ExperimentConfig"""
        # Convert datetime strings back to objects
        if experiment_dict.get("start_date"):
            experiment_dict["start_date"] = datetime.fromisoformat(experiment_dict["start_date"])
        if experiment_dict.get("end_date"):
            experiment_dict["end_date"] = datetime.fromisoformat(experiment_dict["end_date"])

        # Convert status string back to enum
        experiment_dict["status"] = ExperimentStatus(experiment_dict["status"])

        # Convert variants
        variants = []
        for variant_dict in experiment_dict["variants"]:
            variant_dict["type"] = VariantType(variant_dict["type"])
            variants.append(Variant(**variant_dict))
        experiment_dict["variants"] = variants

        # Convert metrics
        metrics = []
        for metric_dict in experiment_dict["metrics"]:
            metrics.append(Metric(**metric_dict))
        experiment_dict["metrics"] = metrics

        return ExperimentConfig(**experiment_dict)

    def _validate_experiment_config(self, config: ExperimentConfig):
        """Validate experiment configuration"""
        # Check traffic percentages sum to 100%
        total_traffic = sum(v.traffic_percentage for v in config.variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"Variant traffic percentages must sum to 100%, got {total_traffic}")

        # Check at least one control variant
        control_variants = [v for v in config.variants if v.type == VariantType.CONTROL]
        if not control_variants:
            raise ValueError("At least one control variant is required")

        # Check at least one primary metric
        primary_metrics = [m for m in config.metrics if m.primary]
        if not primary_metrics:
            logger.warning("No primary metrics defined")


# Example usage
if __name__ == "__main__":
    # Initialize framework
    framework = ABTestingFramework(Path("experiments"))

    # Create experiment configuration
    config = ExperimentConfig(
        id="model_comparison_v1",
        name="Stock Recommendation Model A/B Test",
        description="Compare ensemble model vs single model performance",
        variants=[
            Variant(
                id="control",
                name="Single Model",
                type=VariantType.CONTROL,
                traffic_percentage=50.0,
                model_config={"model_type": "single_mlp"},
            ),
            Variant(
                id="treatment",
                name="Ensemble Model",
                type=VariantType.TREATMENT,
                traffic_percentage=50.0,
                model_config={"model_type": "ensemble"},
            ),
        ],
        metrics=[
            Metric(
                name="prediction_accuracy",
                type="continuous",
                aggregation="mean",
                goal="increase",
                primary=True,
            ),
            Metric(
                name="recommendation_click_rate",
                type="binary",
                aggregation="mean",
                goal="increase",
                primary=True,
            ),
            Metric(name="portfolio_return", type="continuous", aggregation="mean", goal="increase"),
        ],
        min_sample_size=1000,
    )

    # Create and start experiment
    experiment_id = framework.create_experiment(config)
    framework.start_experiment(experiment_id)

    # Simulate user assignments and metrics
    for i in range(100):
        user_id = f"user_{i}"
        variant = framework.assign_user(user_id, experiment_id)

        # Simulate metrics
        framework.record_metric(
            user_id, experiment_id, "prediction_accuracy", random.uniform(0.6, 0.9)
        )
        framework.record_metric(
            user_id, experiment_id, "recommendation_click_rate", random.choice([0, 1])
        )
        framework.record_metric(
            user_id, experiment_id, "portfolio_return", random.uniform(-0.1, 0.15)
        )

    # Analyze results
    results = framework.analyze_experiment(experiment_id)

    print(f"Experiment Results:")
    print(f"Total Users: {results.total_users}")
    print(f"Statistical Significance: {results.statistical_significance}")
    print(f"Winner: {results.winner_variant}")
    print(f"Recommendations: {results.recommendations}")

    logger.info("A/B testing framework demo completed")
