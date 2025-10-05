"""DVC integration for data versioning and pipeline management"""

import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


@dataclass
class DVCConfig:
    """DVC configuration"""

    project_root: Path = Path(".")
    remote_storage: str = "s3://my-bucket/dvc-storage"  # or local path
    cache_dir: Path = Path(".dvc/cache")
    auto_commit: bool = True
    verbose: bool = True


class DataVersionControl:
    """DVC wrapper for data versioning"""

    def __init__(self, config: DVCConfig):
        self.config = config
        self.project_root = config.project_root
        self._ensure_dvc_initialized()

    def _ensure_dvc_initialized(self):
        """Ensure DVC is initialized in project"""
        dvc_dir = self.project_root / ".dvc"

        if not dvc_dir.exists():
            logger.info("Initializing DVC...")
            self._run_command("dvc init")

            # Configure remote storage
            if self.config.remote_storage:
                self._run_command(f"dvc remote add -d storage {self.config.remote_storage}")

    def _run_command(self, command: str) -> str:
        """Run DVC command"""
        try:
            result = subprocess.run(
                command.split(), capture_output=True, text=True, cwd=self.project_root
            )

            if result.returncode != 0:
                logger.error(f"DVC command failed: {result.stderr}")
                raise RuntimeError(f"DVC command failed: {command}")

            if self.config.verbose:
                logger.debug(f"DVC: {command} -> {result.stdout}")

            return result.stdout
        except Exception as e:
            logger.error(f"Failed to run DVC command: {e}")
            raise

    def add_data(self, data_path: Union[str, Path], description: Optional[str] = None) -> str:
        """Add data file or directory to DVC tracking"""
        data_path = Path(data_path)

        if not data_path.exists():
            raise FileNotFoundError(f"Data path not found: {data_path}")

        # Add to DVC
        self._run_command(f"dvc add {data_path}")

        # Generate metadata
        metadata = self._generate_metadata(data_path, description)
        metadata_path = data_path.with_suffix(".meta.json")

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Commit if auto-commit enabled
        if self.config.auto_commit:
            self._commit_changes(f"Add data: {data_path.name}")

        logger.info(f"Added {data_path} to DVC tracking")
        return str(data_path) + ".dvc"

    def push_data(self):
        """Push data to remote storage"""
        logger.info("Pushing data to remote...")
        self._run_command("dvc push")

    def pull_data(self):
        """Pull data from remote storage"""
        logger.info("Pulling data from remote...")
        self._run_command("dvc pull")

    def checkout(self, version: Optional[str] = None):
        """Checkout specific data version"""
        if version:
            self._run_command(f"git checkout {version}")

        self._run_command("dvc checkout")
        logger.info(f"Checked out data version: {version or 'latest'}")

    def get_data_status(self) -> Dict[str, Any]:
        """Get status of tracked data"""
        status_output = self._run_command("dvc status")

        # Parse status
        status = {"modified": [], "not_in_cache": [], "deleted": []}

        for line in status_output.split("\n"):
            if "modified:" in line:
                status["modified"].append(line.split(":")[-1].strip())
            elif "not in cache:" in line:
                status["not_in_cache"].append(line.split(":")[-1].strip())
            elif "deleted:" in line:
                status["deleted"].append(line.split(":")[-1].strip())

        return status

    def _generate_metadata(
        self, data_path: Path, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate metadata for data file"""
        stat = data_path.stat()

        metadata = {
            "path": str(data_path),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "hash": self._calculate_hash(data_path),
            "description": description or "",
            "type": "directory" if data_path.is_dir() else "file",
        }

        # Add data-specific metadata
        if data_path.suffix in [".csv", ".parquet"]:
            try:
                df = (
                    pd.read_csv(data_path)
                    if data_path.suffix == ".csv"
                    else pd.read_parquet(data_path)
                )
                metadata["rows"] = len(df)
                metadata["columns"] = len(df.columns)
                metadata["column_names"] = df.columns.tolist()
            except:
                pass

        return metadata

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash"""
        if file_path.is_dir():
            return "directory"

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _commit_changes(self, message: str):
        """Commit changes to git"""
        subprocess.run(["git", "add", "-A"], cwd=self.project_root)
        subprocess.run(["git", "commit", "-m", message], cwd=self.project_root)


class DVCPipeline:
    """DVC pipeline management"""

    def __init__(self, config: DVCConfig):
        self.config = config
        self.dvc = DataVersionControl(config)
        self.pipeline_file = config.project_root / "dvc.yaml"
        self.params_file = config.project_root / "params.yaml"

    def create_pipeline(self, stages: List[Dict[str, Any]]):
        """Create DVC pipeline"""
        pipeline = {"stages": {}}

        for stage in stages:
            stage_name = stage["name"]
            pipeline["stages"][stage_name] = {
                "cmd": stage["cmd"],
                "deps": stage.get("deps", []),
                "params": stage.get("params", []),
                "outs": stage.get("outs", []),
                "metrics": stage.get("metrics", []),
                "plots": stage.get("plots", []),
            }

        # Save pipeline
        with open(self.pipeline_file, "w") as f:
            yaml.dump(pipeline, f, default_flow_style=False)

        logger.info(f"Created DVC pipeline with {len(stages)} stages")

    def add_stage(
        self,
        name: str,
        cmd: str,
        deps: Optional[List[str]] = None,
        params: Optional[List[str]] = None,
        outs: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
    ):
        """Add stage to pipeline"""
        stage_config = {
            "cmd": cmd,
            "deps": deps or [],
            "params": params or [],
            "outs": outs or [],
            "metrics": metrics or [],
        }

        # Load existing pipeline
        if self.pipeline_file.exists():
            with open(self.pipeline_file, "r") as f:
                pipeline = yaml.safe_load(f) or {"stages": {}}
        else:
            pipeline = {"stages": {}}

        # Add stage
        pipeline["stages"][name] = stage_config

        # Save pipeline
        with open(self.pipeline_file, "w") as f:
            yaml.dump(pipeline, f, default_flow_style=False)

        logger.info(f"Added stage '{name}' to pipeline")

    def run_pipeline(self, stage: Optional[str] = None):
        """Run DVC pipeline"""
        if stage:
            cmd = f"dvc repro {stage}"
        else:
            cmd = "dvc repro"

        logger.info(f"Running DVC pipeline: {cmd}")
        self.dvc._run_command(cmd)

    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics"""
        metrics_output = self.dvc._run_command("dvc metrics show")

        # Parse metrics (simplified)
        metrics = {}
        for line in metrics_output.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                try:
                    metrics[key.strip()] = float(value.strip())
                except:
                    metrics[key.strip()] = value.strip()

        return metrics

    def create_ml_pipeline(self):
        """Create standard ML pipeline"""
        stages = [
            {
                "name": "data_preparation",
                "cmd": "python src/prepare_data.py",
                "deps": ["data/raw"],
                "outs": ["data/processed"],
                "params": ["prepare.test_split", "prepare.seed"],
            },
            {
                "name": "feature_engineering",
                "cmd": "python src/featurize.py",
                "deps": ["data/processed"],
                "outs": ["data/features"],
                "params": ["featurize.max_features", "featurize.ngrams"],
            },
            {
                "name": "train",
                "cmd": "python src/train.py",
                "deps": ["data/features"],
                "outs": ["models/model.pkl"],
                "params": ["train.epochs", "train.learning_rate"],
                "metrics": [{"metrics.json": {"cache": False}}],
            },
            {
                "name": "evaluate",
                "cmd": "python src/evaluate.py",
                "deps": ["models/model.pkl", "data/features"],
                "metrics": [{"eval/metrics.json": {"cache": False}}],
                "plots": [{"eval/plots/roc.json": {"x": "fpr", "y": "tpr"}}],
            },
        ]

        self.create_pipeline(stages)

        # Create default params file
        params = {
            "prepare": {"test_split": 0.2, "seed": 42},
            "featurize": {"max_features": 100, "ngrams": 2},
            "train": {"epochs": 10, "learning_rate": 0.001},
        }

        with open(self.params_file, "w") as f:
            yaml.dump(params, f, default_flow_style=False)

        logger.info("Created ML pipeline with DVC")


class DataRegistry:
    """Central registry for versioned datasets"""

    def __init__(self, registry_path: Path = Path("data_registry.json")):
        self.registry_path = registry_path
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """Load data registry"""
        if self.registry_path.exists():
            with open(self.registry_path, "r") as f:
                return json.load(f)
        return {"datasets": {}}

    def _save_registry(self):
        """Save data registry"""
        with open(self.registry_path, "w") as f:
            json.dump(self.registry, f, indent=2)

    def register_dataset(self, name: str, path: str, version: str, metadata: Dict[str, Any]):
        """Register new dataset version"""
        if name not in self.registry["datasets"]:
            self.registry["datasets"][name] = {"versions": {}}

        self.registry["datasets"][name]["versions"][version] = {
            "path": path,
            "metadata": metadata,
            "registered": datetime.now().isoformat(),
        }

        self.registry["datasets"][name]["latest"] = version
        self._save_registry()

        logger.info(f"Registered dataset '{name}' version '{version}'")

    def get_dataset(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Get dataset information"""
        if name not in self.registry["datasets"]:
            raise ValueError(f"Dataset '{name}' not found")

        dataset = self.registry["datasets"][name]
        version = version or dataset["latest"]

        if version not in dataset["versions"]:
            raise ValueError(f"Version '{version}' not found for dataset '{name}'")

        return dataset["versions"][version]

    def list_datasets(self) -> List[str]:
        """List all registered datasets"""
        return list(self.registry["datasets"].keys())

    def list_versions(self, name: str) -> List[str]:
        """List all versions of a dataset"""
        if name not in self.registry["datasets"]:
            raise ValueError(f"Dataset '{name}' not found")

        return list(self.registry["datasets"][name]["versions"].keys())


def create_dvc_config():
    """Create DVC configuration files"""

    # Create .dvc/.gitignore
    dvc_gitignore = """
/config.local
/tmp
/cache
"""

    # Create .dvcignore
    dvcignore = """
# Python
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.coverage
htmlcov

# Jupyter
.ipynb_checkpoints
*.ipynb

# IDE
.vscode
.idea
*.swp
.DS_Store

# Temporary files
/tmp
/temp
*.tmp
"""

    # Create dvc.yaml template
    dvc_yaml = """
stages:
  prepare_data:
    cmd: python src/ml/preprocessing/prepare_data.py
    deps:
      - src/ml/preprocessing/prepare_data.py
      - data/raw
    outs:
      - data/processed
    params:
      - prepare.split_ratio
      - prepare.random_seed

  train_model:
    cmd: python src/ml/models/train.py
    deps:
      - src/ml/models/train.py
      - data/processed
    outs:
      - models/model.pkl
    params:
      - train.epochs
      - train.batch_size
      - train.learning_rate
    metrics:
      - metrics/train_metrics.json:
          cache: false

  evaluate:
    cmd: python src/ml/evaluate.py
    deps:
      - src/ml/evaluate.py
      - models/model.pkl
      - data/processed
    metrics:
      - metrics/eval_metrics.json:
          cache: false
    plots:
      - metrics/confusion_matrix.csv:
          template: confusion
          x: actual
          y: predicted
"""

    # Create params.yaml template
    params_yaml = """
prepare:
  split_ratio: 0.2
  random_seed: 42

train:
  epochs: 100
  batch_size: 32
  learning_rate: 0.001
  dropout_rate: 0.3

evaluate:
  confidence_threshold: 0.6
  metrics:
    - accuracy
    - precision
    - recall
    - f1_score
"""

    return {
        ".dvc/.gitignore": dvc_gitignore,
        ".dvcignore": dvcignore,
        "dvc.yaml": dvc_yaml,
        "params.yaml": params_yaml,
    }


# Example usage
if __name__ == "__main__":
    # Initialize DVC
    config = DVCConfig()
    dvc = DataVersionControl(config)

    # Create data registry
    registry = DataRegistry()

    # Add some data
    dvc.add_data("data/politician_trades.csv", "Politician trading data v1")

    # Register in registry
    registry.register_dataset(
        name="politician_trades",
        path="data/politician_trades.csv",
        version="v1.0",
        metadata={"source": "congress", "records": 10000},
    )

    # Create ML pipeline
    pipeline = DVCPipeline(config)
    pipeline.create_ml_pipeline()

    logger.info("DVC setup complete")
