"""Unified MLOps Manager for Stock Recommendation System"""

import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import mlflow
import mlflow.pytorch
import mlflow.sklearn
from mlflow.tracking import MlflowClient

from .dvc_config import DVCConfig, get_dvc_config
from .mlflow_config import MLflowConfig, get_mlflow_config


class MLOpsManager:
    """Unified manager for MLflow and DVC operations"""

    def __init__(
        self, mlflow_config: Optional[MLflowConfig] = None, dvc_config: Optional[DVCConfig] = None
    ):
        self.mlflow_config = mlflow_config or get_mlflow_config()
        self.dvc_config = dvc_config or get_dvc_config()
        self._setup_completed = False

    def setup(self) -> None:
        """Initialize MLOps infrastructure"""
        if self._setup_completed:
            return

        print("Setting up MLOps infrastructure...")

        # Setup MLflow
        self.mlflow_config.setup_tracking()

        # Setup DVC
        self.dvc_config.setup_data_directories()

        self._setup_completed = True
        print("✅ MLOps infrastructure setup completed")

    def start_experiment_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
    ) -> str:
        """Start a new MLflow experiment run"""
        if not self._setup_completed:
            self.setup()

        run_tags = tags or {}
        if description:
            run_tags["description"] = description

        run = mlflow.start_run(run_name=run_name, tags=run_tags)
        print(f"Started MLflow run: {run.info.run_id}")
        return run.info.run_id

    def log_parameters(self, params: Dict[str, Any]) -> None:
        """Log parameters to MLflow"""
        for key, value in params.items():
            mlflow.log_param(key, value)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log metrics to MLflow"""
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)

    def log_artifacts(self, artifact_path: Path, artifact_name: Optional[str] = None) -> None:
        """Log artifacts to MLflow"""
        if artifact_path.is_file():
            mlflow.log_artifact(str(artifact_path), artifact_name)
        else:
            mlflow.log_artifacts(str(artifact_path), artifact_name)

    def save_and_log_model(
        self,
        model: Any,
        model_name: str,
        model_type: str = "pytorch",
        signature: Optional[Any] = None,
        input_example: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save model locally and log to MLflow"""
        # Create model directory
        model_dir = self.dvc_config.models_dir / model_type / model_name
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model based on type
        if model_type == "pytorch":
            import torch

            model_path = model_dir / "model.pt"
            torch.save(model.state_dict(), model_path)

            # Log to MLflow
            mlflow.pytorch.log_model(
                pytorch_model=model,
                artifact_path=f"models/{model_name}",
                signature=signature,
                input_example=input_example,
                extra_files=[str(model_path)] if model_path.exists() else None,
            )

        elif model_type == "sklearn":
            model_path = model_dir / "model.pkl"
            joblib.dump(model, model_path)

            # Log to MLflow
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path=f"models/{model_name}",
                signature=signature,
                input_example=input_example,
            )

        else:
            # Generic pickle save
            model_path = model_dir / "model.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # Log as generic artifact
            mlflow.log_artifact(str(model_path), f"models/{model_name}")

        # Save metadata
        if metadata:
            metadata_path = model_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
            mlflow.log_artifact(str(metadata_path), f"models/{model_name}")

        # Add to DVC tracking
        self.dvc_config.add_data_to_dvc(model_dir)

        print(f"Model saved and logged: {model_name} ({model_type})")
        return str(model_path)

    def register_model(
        self,
        model_name: str,
        stage: str = "Staging",
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Register model in MLflow Model Registry"""
        # Get the current run
        run = mlflow.active_run()
        if not run:
            raise Exception("No active MLflow run. Start a run first.")

        model_uri = f"runs:/{run.info.run_id}/models/{model_name}"

        # Register model
        model_version = self.mlflow_config.register_model(
            model_uri=model_uri, model_name=model_name, tags=tags, description=description
        )

        # Transition to requested stage
        if stage != "None":
            self.mlflow_config.transition_model_stage(
                model_name=model_name, version=model_version.version, stage=stage
            )

        return model_version.version

    def load_model(
        self, model_name: str, version: Optional[str] = None, stage: Optional[str] = None
    ) -> Any:
        """Load model from MLflow Model Registry"""
        if version:
            model_uri = f"models:/{model_name}/{version}"
        elif stage:
            model_uri = f"models:/{model_name}/{stage}"
        else:
            model_uri = f"models:/{model_name}/latest"

        return mlflow.pytorch.load_model(model_uri)

    def end_run(self, status: str = "FINISHED") -> None:
        """End the current MLflow run"""
        mlflow.end_run(status=status)

    def version_data(self, data_path: Path, message: Optional[str] = None) -> str:
        """Version data using DVC"""
        self.dvc_config.add_data_to_dvc(data_path, message)
        return self.dvc_config.get_data_version(data_path) or "unknown"

    def create_ml_pipeline_stage(
        self,
        stage_name: str,
        script_path: str,
        dependencies: List[str],
        outputs: List[str],
        parameters: Optional[List[str]] = None,
    ) -> None:
        """Create a DVC pipeline stage for ML workflow"""
        command = f"python {script_path}"

        self.dvc_config.create_pipeline_stage(
            stage_name=stage_name,
            command=command,
            dependencies=dependencies,
            outputs=outputs,
            parameters=parameters,
        )

    def run_ml_pipeline(self, stage_name: Optional[str] = None) -> None:
        """Run DVC ML pipeline"""
        self.dvc_config.run_pipeline(stage_name)

    def get_experiment_metrics(self, experiment_name: str) -> List[Dict[str, Any]]:
        """Get metrics from all runs in an experiment"""
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if not experiment:
            return []

        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        return runs.to_dict("records")

    def compare_models(
        self, model_names: List[str], metric_name: str = "accuracy"
    ) -> Dict[str, Any]:
        """Compare models by a specific metric"""
        comparison = {}

        for model_name in model_names:
            try:
                # Get latest version metrics
                latest_versions = self.mlflow_config.client.get_latest_versions(
                    model_name, stages=["Production", "Staging"]
                )

                if latest_versions:
                    version = latest_versions[0]
                    run = self.mlflow_config.client.get_run(version.run_id)
                    comparison[model_name] = {
                        "version": version.version,
                        "stage": version.current_stage,
                        "metric_value": run.data.metrics.get(metric_name, 0.0),
                        "run_id": version.run_id,
                    }
            except Exception as e:
                comparison[model_name] = {"error": str(e)}

        return comparison

    def cleanup_old_runs(self, days_old: int = 30) -> None:
        """Clean up old experiment runs"""
        # This would implement cleanup logic for old runs
        # For now, just a placeholder
        print(f"Cleanup of runs older than {days_old} days would be implemented here")

    def get_system_info(self) -> Dict[str, Any]:
        """Get MLOps system information"""
        return {
            "mlflow_tracking_uri": self.mlflow_config.tracking_uri,
            "mlflow_experiment": self.mlflow_config.experiment_name,
            "dvc_project_root": str(self.dvc_config.project_root),
            "data_directory": str(self.dvc_config.data_dir),
            "models_directory": str(self.dvc_config.models_dir),
            "setup_completed": self._setup_completed,
            "timestamp": datetime.now().isoformat(),
        }


# Global MLOps manager instance
mlops_manager = MLOpsManager()


def get_mlops_manager() -> MLOpsManager:
    """Get the global MLOps manager instance"""
    return mlops_manager


if __name__ == "__main__":
    # Test the MLOps setup
    manager = get_mlops_manager()
    manager.setup()

    print("\n" + "=" * 50)
    print("MLOPs System Information:")
    print("=" * 50)

    system_info = manager.get_system_info()
    for key, value in system_info.items():
        print(f"{key}: {value}")
