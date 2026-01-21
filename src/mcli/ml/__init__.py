"""MCLI Machine Learning Module for Stock Recommendation System."""

from .configs.dvc_config import get_dvc_config, setup_dvc
from .configs.mlflow_config import get_mlflow_config, setup_mlflow
from .configs.mlops_manager import MLOpsManager, get_mlops_manager

__version__ = "0.1.0"

__all__ = [
    "get_mlops_manager",
    "MLOpsManager",
    "get_mlflow_config",
    "setup_mlflow",
    "get_dvc_config",
    "setup_dvc",
]
