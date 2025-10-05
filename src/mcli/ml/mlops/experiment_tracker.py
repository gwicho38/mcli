"""MLflow experiment tracking and model registry"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import mlflow
import mlflow.pytorch
import mlflow.sklearn
import numpy as np
import pandas as pd
import torch
from mlflow.models.signature import ModelSignature, infer_signature
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)


@dataclass
class MLflowConfig:
    """Configuration for MLflow tracking"""

    tracking_uri: str = "sqlite:///mlruns.db"
    experiment_name: str = "politician-trading-predictions"
    artifact_location: Optional[str] = None
    registry_uri: Optional[str] = None
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {
                "project": "politician-trading",
                "framework": "pytorch",
                "type": "stock-recommendation",
            }


@dataclass
class ExperimentRun:
    """Container for experiment run information"""

    run_id: str
    experiment_id: str
    run_name: str
    metrics: Dict[str, float]
    params: Dict[str, Any]
    artifacts: List[str]
    model_uri: Optional[str] = None
    status: str = "RUNNING"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ExperimentTracker:
    """MLflow experiment tracker for ML pipeline"""

    def __init__(self, config: MLflowConfig):
        self.config = config
        self.client = None
        self.current_run = None
        self.setup_mlflow()

    def setup_mlflow(self):
        """Initialize MLflow tracking"""
        mlflow.set_tracking_uri(self.config.tracking_uri)

        if self.config.registry_uri:
            mlflow.set_registry_uri(self.config.registry_uri)

        # Create or get experiment
        experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(
                self.config.experiment_name,
                artifact_location=self.config.artifact_location,
                tags=self.config.tags,
            )
        else:
            experiment_id = experiment.experiment_id

        mlflow.set_experiment(self.config.experiment_name)
        self.client = MlflowClient()
        self.experiment_id = experiment_id

        logger.info(f"MLflow tracking initialized at {self.config.tracking_uri}")
        logger.info(f"Experiment: {self.config.experiment_name} (ID: {experiment_id})")

    def start_run(self, run_name: str, tags: Optional[Dict[str, str]] = None) -> ExperimentRun:
        """Start a new MLflow run"""
        if self.current_run:
            self.end_run()

        # Merge tags
        all_tags = {**self.config.tags}
        if tags:
            all_tags.update(tags)

        # Start run
        run = mlflow.start_run(run_name=run_name, tags=all_tags)

        self.current_run = ExperimentRun(
            run_id=run.info.run_id,
            experiment_id=run.info.experiment_id,
            run_name=run_name,
            metrics={},
            params={},
            artifacts=[],
            start_time=datetime.now(),
        )

        logger.info(f"Started MLflow run: {run_name} (ID: {run.info.run_id})")
        return self.current_run

    def log_params(self, params: Dict[str, Any]):
        """Log parameters to current run"""
        if not self.current_run:
            raise ValueError("No active MLflow run. Call start_run() first.")

        for key, value in params.items():
            # Convert complex types to strings
            if isinstance(value, (list, dict, tuple)):
                value = json.dumps(value)
            elif not isinstance(value, (str, int, float, bool)):
                value = str(value)

            mlflow.log_param(key, value)
            self.current_run.params[key] = value

        logger.debug(f"Logged {len(params)} parameters")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log metrics to current run"""
        if not self.current_run:
            raise ValueError("No active MLflow run. Call start_run() first.")

        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)
            self.current_run.metrics[key] = value

        logger.debug(f"Logged {len(metrics)} metrics at step {step}")

    def log_artifact(self, artifact_path: Union[str, Path], artifact_type: Optional[str] = None):
        """Log artifact to current run"""
        if not self.current_run:
            raise ValueError("No active MLflow run. Call start_run() first.")

        artifact_path = Path(artifact_path)

        if artifact_path.is_file():
            mlflow.log_artifact(str(artifact_path))
        elif artifact_path.is_dir():
            mlflow.log_artifacts(str(artifact_path))
        else:
            raise ValueError(f"Artifact path does not exist: {artifact_path}")

        self.current_run.artifacts.append(str(artifact_path))
        logger.debug(f"Logged artifact: {artifact_path}")

    def log_model(
        self,
        model: Any,
        model_name: str,
        input_example: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        signature: Optional[ModelSignature] = None,
        conda_env: Optional[Dict] = None,
        pip_requirements: Optional[List[str]] = None,
    ):
        """Log model to current run"""
        if not self.current_run:
            raise ValueError("No active MLflow run. Call start_run() first.")

        # Infer signature if not provided
        if signature is None and input_example is not None:
            if isinstance(model, torch.nn.Module):
                model.eval()
                with torch.no_grad():
                    if isinstance(input_example, pd.DataFrame):
                        input_tensor = torch.FloatTensor(input_example.values)
                    else:
                        input_tensor = torch.FloatTensor(input_example)

                    output = model(input_tensor)
                    if isinstance(output, dict):
                        # Handle dictionary outputs
                        output_example = {k: v.numpy() for k, v in output.items()}
                    else:
                        output_example = output.numpy()

                    signature = infer_signature(input_example, output_example)
            else:
                # For sklearn models
                output_example = model.predict(input_example)
                signature = infer_signature(input_example, output_example)

        # Log model based on type
        if isinstance(model, torch.nn.Module):
            mlflow.pytorch.log_model(
                model,
                model_name,
                signature=signature,
                input_example=input_example,
                conda_env=conda_env,
                pip_requirements=pip_requirements,
            )
            framework = "pytorch"
        else:
            # Assume sklearn-compatible
            mlflow.sklearn.log_model(
                model,
                model_name,
                signature=signature,
                input_example=input_example,
                conda_env=conda_env,
                pip_requirements=pip_requirements,
            )
            framework = "sklearn"

        self.current_run.model_uri = f"runs:/{self.current_run.run_id}/{model_name}"

        logger.info(f"Logged {framework} model: {model_name}")
        return self.current_run.model_uri

    def log_figure(self, figure, artifact_name: str):
        """Log matplotlib figure"""
        if not self.current_run:
            raise ValueError("No active MLflow run. Call start_run() first.")

        mlflow.log_figure(figure, artifact_name)
        self.current_run.artifacts.append(artifact_name)
        logger.debug(f"Logged figure: {artifact_name}")

    def log_dict(self, dictionary: Dict, artifact_name: str):
        """Log dictionary as JSON artifact"""
        if not self.current_run:
            raise ValueError("No active MLflow run. Call start_run() first.")

        mlflow.log_dict(dictionary, artifact_name)
        self.current_run.artifacts.append(artifact_name)
        logger.debug(f"Logged dictionary: {artifact_name}")

    def end_run(self, status: str = "FINISHED"):
        """End current MLflow run"""
        if not self.current_run:
            return

        self.current_run.status = status
        self.current_run.end_time = datetime.now()

        mlflow.end_run(status=status)

        duration = (self.current_run.end_time - self.current_run.start_time).total_seconds()
        logger.info(
            f"Ended MLflow run {self.current_run.run_name} "
            f"(Duration: {duration:.2f}s, Status: {status})"
        )

        current_run = self.current_run
        self.current_run = None
        return current_run

    def get_run(self, run_id: str) -> mlflow.entities.Run:
        """Get run by ID"""
        return self.client.get_run(run_id)

    def search_runs(
        self, filter_string: str = "", max_results: int = 100
    ) -> List[mlflow.entities.Run]:
        """Search for runs in experiment"""
        return self.client.search_runs(
            experiment_ids=[self.experiment_id],
            filter_string=filter_string,
            max_results=max_results,
        )

    def compare_runs(self, run_ids: List[str], metrics: Optional[List[str]] = None) -> pd.DataFrame:
        """Compare multiple runs"""
        runs_data = []

        for run_id in run_ids:
            run = self.get_run(run_id)
            run_data = {
                "run_id": run_id,
                "run_name": run.data.tags.get("mlflow.runName", ""),
                "status": run.info.status,
            }

            # Add params
            for key, value in run.data.params.items():
                run_data[f"param_{key}"] = value

            # Add metrics
            if metrics:
                for metric in metrics:
                    if metric in run.data.metrics:
                        run_data[f"metric_{metric}"] = run.data.metrics[metric]
            else:
                for key, value in run.data.metrics.items():
                    run_data[f"metric_{key}"] = value

            runs_data.append(run_data)

        return pd.DataFrame(runs_data)


class ModelRegistry:
    """MLflow model registry for model versioning and deployment"""

    def __init__(self, config: MLflowConfig):
        self.config = config
        self.client = MlflowClient()
        mlflow.set_tracking_uri(config.tracking_uri)

        if config.registry_uri:
            mlflow.set_registry_uri(config.registry_uri)

    def register_model(
        self, model_uri: str, model_name: str, tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Register model in MLflow registry"""
        try:
            # Create registered model if it doesn't exist
            self.client.create_registered_model(
                model_name, tags=tags or {}, description=f"Model for {model_name}"
            )
        except Exception as e:
            logger.debug(f"Model {model_name} already exists: {e}")

        # Register model version
        model_version = self.client.create_model_version(
            name=model_name,
            source=model_uri,
            run_id=model_uri.split("/")[1] if "runs:/" in model_uri else None,
            tags=tags or {},
        )

        logger.info(f"Registered model {model_name} version {model_version.version}")
        return f"models:/{model_name}/{model_version.version}"

    def transition_model_stage(
        self, model_name: str, version: int, stage: str, archive_existing: bool = True
    ):
        """Transition model version to new stage"""
        self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing,
        )

        logger.info(f"Transitioned {model_name} v{version} to {stage}")

    def load_model(
        self, model_name: str, version: Optional[int] = None, stage: Optional[str] = None
    ) -> Any:
        """Load model from registry"""
        if version:
            model_uri = f"models:/{model_name}/{version}"
        elif stage:
            model_uri = f"models:/{model_name}/{stage}"
        else:
            model_uri = f"models:/{model_name}/latest"

        model = mlflow.pytorch.load_model(model_uri)
        logger.info(f"Loaded model from {model_uri}")
        return model

    def get_model_version(self, model_name: str, version: int):
        """Get specific model version details"""
        return self.client.get_model_version(model_name, version)

    def get_latest_versions(self, model_name: str, stages: Optional[List[str]] = None):
        """Get latest model versions for given stages"""
        return self.client.get_latest_versions(model_name, stages=stages)

    def delete_model_version(self, model_name: str, version: int):
        """Delete model version"""
        self.client.delete_model_version(model_name, version)
        logger.info(f"Deleted {model_name} version {version}")

    def search_models(self, filter_string: str = "") -> List:
        """Search registered models"""
        return self.client.search_registered_models(filter_string=filter_string)
