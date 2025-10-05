"""End-to-end ML pipeline orchestrator"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import torch
from ml.features.ensemble_features import EnsembleFeatureBuilder
from ml.features.political_features import PoliticalInfluenceFeatures
from ml.features.recommendation_engine import RecommendationConfig as FeatureRecommendationConfig
from ml.features.recommendation_engine import (
    StockRecommendationEngine,
)
from ml.features.stock_features import StockRecommendationFeatures
from ml.models.ensemble_models import (
    DeepEnsembleModel,
    EnsembleConfig,
    EnsembleTrainer,
    ModelConfig,
)
from ml.models.recommendation_models import (
    RecommendationConfig,
    RecommendationTrainer,
    StockRecommendationModel,
)
from ml.preprocessing.data_processor import DataProcessor, ProcessingConfig

from .experiment_tracker import ExperimentTracker, MLflowConfig

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages"""

    DATA_INGESTION = "data_ingestion"
    DATA_PREPROCESSING = "data_preprocessing"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    MODEL_DEPLOYMENT = "model_deployment"


@dataclass
class PipelineStep:
    """Individual pipeline step configuration"""

    name: str
    stage: PipelineStage
    function: Callable
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    config: Optional[Dict[str, Any]] = None
    enabled: bool = True
    retry_count: int = 3
    timeout: Optional[int] = None  # seconds


@dataclass
class PipelineConfig:
    """Complete pipeline configuration"""

    name: str = "politician-trading-ml-pipeline"
    version: str = "1.0.0"
    data_dir: Path = Path("data")
    model_dir: Path = Path("models")
    output_dir: Path = Path("outputs")
    cache_dir: Path = Path("cache")
    enable_mlflow: bool = True
    mlflow_config: Optional[MLflowConfig] = None
    enable_caching: bool = True
    parallel_execution: bool = False
    checkpoint_frequency: int = 5  # Save checkpoint every N steps
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        # Create directories
        for dir_path in [self.data_dir, self.model_dir, self.output_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        if self.enable_mlflow and not self.mlflow_config:
            self.mlflow_config = MLflowConfig()


class MLPipeline:
    """End-to-end ML pipeline orchestrator"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.steps: List[PipelineStep] = []
        self.artifacts: Dict[str, Any] = {}
        self.metrics: Dict[str, float] = {}
        self.experiment_tracker = None
        self.current_step = None

        if config.enable_mlflow:
            self.experiment_tracker = ExperimentTracker(config.mlflow_config)

        # Initialize components
        self.data_processor = None
        self.feature_extractors = {}
        self.model = None
        self.trainer = None

        self._setup_default_pipeline()

    def _setup_default_pipeline(self):
        """Setup default pipeline steps"""
        # Data ingestion
        self.add_step(
            PipelineStep(
                name="load_raw_data",
                stage=PipelineStage.DATA_INGESTION,
                function=self._load_raw_data,
                outputs=["raw_trading_data", "raw_stock_data"],
            )
        )

        # Data preprocessing
        self.add_step(
            PipelineStep(
                name="preprocess_data",
                stage=PipelineStage.DATA_PREPROCESSING,
                function=self._preprocess_data,
                inputs={"trading_data": "raw_trading_data", "stock_data": "raw_stock_data"},
                outputs=["processed_trading_data", "processed_stock_data"],
            )
        )

        # Feature engineering
        self.add_step(
            PipelineStep(
                name="extract_features",
                stage=PipelineStage.FEATURE_ENGINEERING,
                function=self._extract_features,
                inputs={
                    "trading_data": "processed_trading_data",
                    "stock_data": "processed_stock_data",
                },
                outputs=["feature_matrix", "feature_names", "labels"],
            )
        )

        # Model training
        self.add_step(
            PipelineStep(
                name="train_model",
                stage=PipelineStage.MODEL_TRAINING,
                function=self._train_model,
                inputs={"X": "feature_matrix", "y": "labels"},
                outputs=["trained_model", "training_metrics"],
            )
        )

        # Model evaluation
        self.add_step(
            PipelineStep(
                name="evaluate_model",
                stage=PipelineStage.MODEL_EVALUATION,
                function=self._evaluate_model,
                inputs={
                    "model": "trained_model",
                    "X_test": "test_features",
                    "y_test": "test_labels",
                },
                outputs=["evaluation_metrics", "predictions"],
            )
        )

        # Model deployment
        self.add_step(
            PipelineStep(
                name="deploy_model",
                stage=PipelineStage.MODEL_DEPLOYMENT,
                function=self._deploy_model,
                inputs={"model": "trained_model", "metrics": "evaluation_metrics"},
                outputs=["deployment_info"],
            )
        )

    def add_step(self, step: PipelineStep):
        """Add step to pipeline"""
        self.steps.append(step)
        logger.debug(f"Added pipeline step: {step.name}")

    def _load_raw_data(self) -> Dict[str, pd.DataFrame]:
        """Load raw data from sources"""
        logger.info("Loading raw data...")

        # Load politician trading data
        trading_data_path = self.config.data_dir / "politician_trades.csv"
        if trading_data_path.exists():
            trading_data = pd.read_csv(trading_data_path)
        else:
            # Generate mock data for testing
            trading_data = self._generate_mock_trading_data()

        # Load stock price data
        stock_data_path = self.config.data_dir / "stock_prices.csv"
        if stock_data_path.exists():
            stock_data = pd.read_csv(stock_data_path)
        else:
            # Generate mock data for testing
            stock_data = self._generate_mock_stock_data()

        logger.info(
            f"Loaded {len(trading_data)} trading records and {len(stock_data)} stock prices"
        )

        return {"raw_trading_data": trading_data, "raw_stock_data": stock_data}

    def _preprocess_data(
        self, trading_data: pd.DataFrame, stock_data: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """Preprocess raw data"""
        logger.info("Preprocessing data...")

        # Initialize data processor
        processing_config = ProcessingConfig()
        self.data_processor = DataProcessor(processing_config)

        # Process trading data
        processed_trading = self.data_processor.process_politician_trades(trading_data)

        # Process stock data (ensure proper format)
        processed_stock = stock_data.copy()
        if "date" in processed_stock.columns and processed_stock["date"].dtype == "object":
            processed_stock["date"] = pd.to_datetime(processed_stock["date"])

        # Clean and validate
        processed_trading = self.data_processor.clean_data(processed_trading)
        processed_stock = self.data_processor.clean_data(processed_stock)

        logger.info(f"Preprocessed {len(processed_trading)} trading records")

        return {
            "processed_trading_data": processed_trading,
            "processed_stock_data": processed_stock,
        }

    def _extract_features(
        self, trading_data: pd.DataFrame, stock_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Extract features from preprocessed data"""
        logger.info("Extracting features...")

        # Initialize feature extractors
        stock_extractor = StockRecommendationFeatures()
        political_extractor = PoliticalInfluenceFeatures()
        ensemble_builder = EnsembleFeatureBuilder()

        # Extract stock features
        stock_features = pd.DataFrame()
        if not stock_data.empty:
            try:
                stock_features = stock_extractor.extract_features(stock_data)
            except Exception as e:
                logger.warning(f"Could not extract stock features: {e}")

        # Extract political features
        political_features = political_extractor.extract_influence_features(trading_data)

        # Combine features
        if not stock_features.empty:
            feature_df = pd.concat([political_features, stock_features], axis=1)
        else:
            feature_df = political_features

        # Build ensemble features
        feature_df = ensemble_builder.build_ensemble_features(feature_df)

        # Create labels (simplified - would be based on actual returns)
        labels = np.random.randint(0, 2, len(feature_df))

        # Store feature names
        feature_names = feature_df.columns.tolist()

        logger.info(f"Extracted {len(feature_names)} features from {len(feature_df)} samples")

        return {
            "feature_matrix": feature_df.values,
            "feature_names": feature_names,
            "labels": labels,
        }

    def _train_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train ensemble model"""
        logger.info("Training model...")

        # Split data
        train_size = int(0.8 * len(X))
        X_train, X_val = X[:train_size], X[train_size:]
        y_train, y_val = y[:train_size], y[train_size:]

        # Store test data for evaluation
        self.artifacts["test_features"] = X_val
        self.artifacts["test_labels"] = y_val

        # Configure ensemble
        model_configs = [
            ModelConfig(
                model_type="mlp",
                hidden_dims=[256, 128],
                dropout_rate=0.3,
                learning_rate=0.001,
                weight_decay=1e-4,
                batch_size=32,
                epochs=10,
            ),
            ModelConfig(
                model_type="attention",
                hidden_dims=[128],
                dropout_rate=0.2,
                learning_rate=0.001,
                weight_decay=1e-4,
                batch_size=32,
                epochs=10,
            ),
        ]

        ensemble_config = EnsembleConfig(
            base_models=model_configs, ensemble_method="weighted_average"
        )

        recommendation_config = RecommendationConfig(
            ensemble_config=ensemble_config, risk_adjustment=True, confidence_threshold=0.6
        )

        # Create and train model
        input_dim = X.shape[1]
        self.model = StockRecommendationModel(input_dim, recommendation_config)

        # Generate mock risk and return labels for training
        returns_train = np.random.normal(0.05, 0.15, len(y_train))
        risk_labels_train = np.random.choice([0, 1, 2], len(y_train), p=[0.3, 0.5, 0.2])
        returns_val = np.random.normal(0.05, 0.15, len(y_val))
        risk_labels_val = np.random.choice([0, 1, 2], len(y_val), p=[0.3, 0.5, 0.2])

        # Train model
        trainer = RecommendationTrainer(self.model, recommendation_config)
        result = trainer.train(
            X_train,
            y_train,
            returns_train,
            risk_labels_train,
            X_val,
            y_val,
            returns_val,
            risk_labels_val,
            epochs=10,
            batch_size=32,
        )

        # Extract metrics
        training_metrics = {
            "train_accuracy": result.train_metrics.accuracy,
            "train_precision": result.train_metrics.precision,
            "train_recall": result.train_metrics.recall,
            "train_f1": result.train_metrics.f1_score,
            "val_accuracy": result.val_metrics.accuracy,
            "val_precision": result.val_metrics.precision,
            "val_recall": result.val_metrics.recall,
            "val_f1": result.val_metrics.f1_score,
        }

        logger.info(f"Model trained - Val accuracy: {training_metrics['val_accuracy']:.3f}")

        return {"trained_model": self.model, "training_metrics": training_metrics}

    def _evaluate_model(
        self, model: StockRecommendationModel, X_test: np.ndarray, y_test: np.ndarray
    ) -> Dict[str, Any]:
        """Evaluate trained model"""
        logger.info("Evaluating model...")

        # Generate predictions
        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)

        # Calculate metrics
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        evaluation_metrics = {
            "test_accuracy": accuracy_score(y_test, predictions),
            "test_precision": precision_score(
                y_test, predictions, average="weighted", zero_division=0
            ),
            "test_recall": recall_score(y_test, predictions, average="weighted", zero_division=0),
            "test_f1": f1_score(y_test, predictions, average="weighted", zero_division=0),
        }

        # Calculate AUC if binary classification
        if probabilities.shape[1] == 2:
            try:
                evaluation_metrics["test_auc"] = roc_auc_score(y_test, probabilities[:, 1])
            except:
                pass

        logger.info(f"Model evaluation - Test accuracy: {evaluation_metrics['test_accuracy']:.3f}")

        return {"evaluation_metrics": evaluation_metrics, "predictions": predictions}

    def _deploy_model(
        self, model: StockRecommendationModel, metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Deploy model (save to disk)"""
        logger.info("Deploying model...")

        # Save model
        model_path = self.config.model_dir / f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "metrics": metrics,
                "config": model.recommendation_config,
            },
            model_path,
        )

        deployment_info = {
            "model_path": str(model_path),
            "deployed_at": datetime.now().isoformat(),
            "metrics": metrics,
        }

        logger.info(f"Model deployed to {model_path}")
        return {"deployment_info": deployment_info}

    def run(
        self, start_step: Optional[str] = None, end_step: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute pipeline"""
        logger.info(f"Starting pipeline: {self.config.name} v{self.config.version}")

        # Start MLflow run if enabled
        if self.experiment_tracker:
            run_name = f"{self.config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.experiment_tracker.start_run(run_name, self.config.tags)

            # Log pipeline config
            self.experiment_tracker.log_params(
                {
                    "pipeline_name": self.config.name,
                    "pipeline_version": self.config.version,
                    "enable_caching": self.config.enable_caching,
                    "parallel_execution": self.config.parallel_execution,
                }
            )

        # Execute steps
        start_idx = 0
        end_idx = len(self.steps)

        if start_step:
            start_idx = next((i for i, s in enumerate(self.steps) if s.name == start_step), 0)
        if end_step:
            end_idx = next(
                (i + 1 for i, s in enumerate(self.steps) if s.name == end_step), len(self.steps)
            )

        for i, step in enumerate(self.steps[start_idx:end_idx], start=start_idx):
            if not step.enabled:
                logger.info(f"Skipping disabled step: {step.name}")
                continue

            self.current_step = step
            logger.info(f"Executing step {i+1}/{len(self.steps)}: {step.name}")

            try:
                # Prepare inputs
                kwargs = {}
                for param, artifact_key in step.inputs.items():
                    if artifact_key in self.artifacts:
                        kwargs[param] = self.artifacts[artifact_key]

                # Execute step
                result = step.function(**kwargs)

                # Store outputs
                if result and step.outputs:
                    if len(step.outputs) == 1:
                        self.artifacts[step.outputs[0]] = result
                    else:
                        for output_key, value in result.items():
                            if output_key in step.outputs:
                                self.artifacts[output_key] = value

                # Log to MLflow
                if self.experiment_tracker and "metrics" in str(result):
                    if isinstance(result, dict) and any("metric" in k for k in result.keys()):
                        metrics_dict = result.get(
                            "training_metrics", result.get("evaluation_metrics", {})
                        )
                        self.experiment_tracker.log_metrics(metrics_dict)

                # Checkpoint if needed
                if (i + 1) % self.config.checkpoint_frequency == 0:
                    self._save_checkpoint(i + 1)

            except Exception as e:
                logger.error(f"Step {step.name} failed: {e}")
                if self.experiment_tracker:
                    self.experiment_tracker.end_run(status="FAILED")
                raise

        # Log final model to MLflow
        if self.experiment_tracker and self.model:
            try:
                example_input = pd.DataFrame(
                    self.artifacts.get("feature_matrix", np.random.randn(5, 100))[:5]
                )
                self.experiment_tracker.log_model(
                    self.model, "recommendation_model", input_example=example_input
                )
            except Exception as e:
                logger.warning(f"Could not log model to MLflow: {e}")

        # End MLflow run
        if self.experiment_tracker:
            self.experiment_tracker.end_run(status="FINISHED")

        logger.info("Pipeline execution completed successfully")

        return {"artifacts": self.artifacts, "metrics": self.metrics, "model": self.model}

    def _save_checkpoint(self, step_number: int):
        """Save pipeline checkpoint"""
        checkpoint_path = self.config.cache_dir / f"checkpoint_step_{step_number}.pkl"

        checkpoint = {
            "step_number": step_number,
            "artifacts": {
                k: v
                for k, v in self.artifacts.items()
                if not isinstance(v, (torch.nn.Module, type))
            },
            "metrics": self.metrics,
            "timestamp": datetime.now(),
        }

        with open(checkpoint_path, "wb") as f:
            pickle.dump(checkpoint, f)

        logger.debug(f"Saved checkpoint at step {step_number}")

    def load_checkpoint(self, checkpoint_path: Path):
        """Load pipeline checkpoint"""
        with open(checkpoint_path, "rb") as f:
            checkpoint = pickle.load(f)

        self.artifacts.update(checkpoint["artifacts"])
        self.metrics.update(checkpoint["metrics"])

        logger.info(f"Loaded checkpoint from step {checkpoint['step_number']}")

    def _generate_mock_trading_data(self) -> pd.DataFrame:
        """Generate mock politician trading data for testing"""
        np.random.seed(42)
        n_records = 500

        politicians = ["Nancy Pelosi", "Mitch McConnell", "Chuck Schumer", "Kevin McCarthy"]
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

        data = []
        for _ in range(n_records):
            data.append(
                {
                    "politician_name_cleaned": np.random.choice(politicians),
                    "transaction_date_cleaned": pd.Timestamp.now()
                    - pd.Timedelta(days=np.random.randint(1, 365)),
                    "transaction_amount_cleaned": np.random.uniform(1000, 500000),
                    "transaction_type_cleaned": np.random.choice(["buy", "sell"]),
                    "ticker_cleaned": np.random.choice(tickers),
                }
            )

        return pd.DataFrame(data)

    def _generate_mock_stock_data(self) -> pd.DataFrame:
        """Generate mock stock price data for testing"""
        np.random.seed(42)
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100)

        data = []
        for ticker in tickers:
            base_price = np.random.uniform(100, 500)
            for date in dates:
                price = base_price * (1 + np.random.normal(0, 0.02))
                data.append(
                    {
                        "symbol": ticker,
                        "date": date,
                        "close": price,
                        "volume": np.random.randint(1000000, 10000000),
                        "open": price * 0.99,
                        "high": price * 1.01,
                        "low": price * 0.98,
                    }
                )

        return pd.DataFrame(data)


class PipelineExecutor:
    """Execute and manage multiple pipeline runs"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipelines: Dict[str, MLPipeline] = {}

    def create_pipeline(self, name: str) -> MLPipeline:
        """Create new pipeline instance"""
        pipeline = MLPipeline(self.config)
        self.pipelines[name] = pipeline
        return pipeline

    def run_pipeline(self, name: str, **kwargs) -> Dict[str, Any]:
        """Run specific pipeline"""
        if name not in self.pipelines:
            self.pipelines[name] = MLPipeline(self.config)

        return self.pipelines[name].run(**kwargs)

    def run_experiment(
        self, n_runs: int = 5, param_grid: Optional[Dict[str, List]] = None
    ) -> pd.DataFrame:
        """Run multiple experiments with different parameters"""
        results = []

        for i in range(n_runs):
            logger.info(f"Running experiment {i+1}/{n_runs}")

            # Create new pipeline for each run
            pipeline_name = f"experiment_{i}"
            pipeline = self.create_pipeline(pipeline_name)

            # Modify parameters if grid provided
            if param_grid:
                # Simple parameter modification (would be more sophisticated in practice)
                pass

            # Run pipeline
            result = pipeline.run()

            # Collect metrics
            run_metrics = {"run_id": i, "pipeline_name": pipeline_name, **result.get("metrics", {})}
            results.append(run_metrics)

        return pd.DataFrame(results)
