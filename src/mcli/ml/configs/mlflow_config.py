"""MLflow Configuration for Stock Recommendation System"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import mlflow
from mlflow.tracking import MlflowClient


class MLflowConfig:
    """Configuration class for MLflow tracking and model registry"""

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        experiment_name: str = "politician-trading-stock-recommendations",
        artifact_root: Optional[str] = None,
    ):
        self.tracking_uri = tracking_uri or self._default_tracking_uri()
        self.experiment_name = experiment_name
        self.artifact_root = artifact_root or self._default_artifact_root()
        self._client = None

    def _default_tracking_uri(self) -> str:
        """Get default MLflow tracking URI"""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        return f"file://{project_root}/mlruns"

    def _default_artifact_root(self) -> str:
        """Get default artifact storage location"""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        return f"{project_root}/artifacts"

    def setup_tracking(self) -> None:
        """Initialize MLflow tracking configuration"""
        mlflow.set_tracking_uri(self.tracking_uri)

        # Create or get experiment
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(
                    name=self.experiment_name, artifact_location=self.artifact_root
                )
                print(f"Created new experiment: {self.experiment_name} (ID: {experiment_id})")
            else:
                experiment_id = experiment.experiment_id
                print(f"Using existing experiment: {self.experiment_name} (ID: {experiment_id})")

            mlflow.set_experiment(self.experiment_name)

        except Exception as e:
            print(f"Error setting up MLflow experiment: {e}")
            raise

    @property
    def client(self) -> MlflowClient:
        """Get MLflow client instance"""
        if self._client is None:
            self._client = MlflowClient(tracking_uri=self.tracking_uri)
        return self._client

    def get_model_registry_uri(self) -> str:
        """Get model registry URI"""
        return self.tracking_uri

    def log_model_metadata(self, run_id: str, metadata: Dict[str, Any]) -> None:
        """Log additional metadata for a model"""
        for key, value in metadata.items():
            self.client.log_param(run_id, key, value)

    def register_model(
        self,
        model_uri: str,
        model_name: str,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
    ) -> None:
        """Register a model in MLflow Model Registry"""
        try:
            model_version = mlflow.register_model(model_uri=model_uri, name=model_name, tags=tags)

            if description:
                self.client.update_model_version(
                    name=model_name, version=model_version.version, description=description
                )

            print(f"Registered model: {model_name}, version: {model_version.version}")
            return model_version

        except Exception as e:
            print(f"Error registering model: {e}")
            raise

    def transition_model_stage(
        self, model_name: str, version: str, stage: str, archive_existing_versions: bool = False
    ) -> None:
        """Transition model to a different stage"""
        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage,
                archive_existing_versions=archive_existing_versions,
            )
            print(f"Transitioned {model_name} v{version} to {stage}")

        except Exception as e:
            print(f"Error transitioning model stage: {e}")
            raise


# Global configuration instance
mlflow_config = MLflowConfig()


def get_mlflow_config() -> MLflowConfig:
    """Get the global MLflow configuration instance"""
    return mlflow_config


def setup_mlflow() -> None:
    """Setup MLflow tracking and experiment"""
    mlflow_config.setup_tracking()
    print(f"MLflow tracking URI: {mlflow_config.tracking_uri}")
    print(f"Artifact root: {mlflow_config.artifact_root}")


if __name__ == "__main__":
    setup_mlflow()
